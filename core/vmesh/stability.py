# core/vmesh/stability.py
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

@dataclass
class StabilityConfig:
    # Weights for the Stability Score S
    alpha: float = 0.25  # Latency P95 weight
    beta: float = 0.25   # Error Rate weight
    gamma: float = 0.20  # Queue Age P95 weight
    delta: float = 0.15  # Ledger Conflicts weight
    epsilon: float = 0.15 # Fallback Cascade Depth weight

    # Normalization thresholds
    latency_p95_threshold_ms: float = 5000.0
    error_rate_threshold: float = 0.10
    queue_age_p95_threshold_sec: float = 300.0
    ledger_conflicts_threshold: int = 10
    fallback_depth_threshold: int = 5

@dataclass
class VMeshState:
    """Mathematical state vector x_t of the Sheratan system."""
    latency_p95_ms: float = 0.0
    error_rate: float = 0.0
    queue_age_p95_sec: float = 0.0
    ledger_conflicts: int = 0
    fallback_cascade_depth: int = 0
    timestamp: float = field(default_factory=time.time)

class StabilityEvaluator:
    """
    StabilityEvaluator (Module A)
    Calculates the Stability Score S(x_t) and Recovery Half-Life R.
    """
    def __init__(self, config: Optional[StabilityConfig] = None):
        self.config = config or StabilityConfig()
        self.history: List[VMeshState] = []
        self._last_score: float = 1.0

    def calculate_score(self, state: VMeshState) -> float:
        """Calculates S(x_t) \in [0, 1]."""
        norm_lat = min(1.0, state.latency_p95_ms / self.config.latency_p95_threshold_ms)
        norm_err = min(1.0, state.error_rate / self.config.error_rate_threshold)
        norm_queue = min(1.0, state.queue_age_p95_sec / self.config.queue_age_p95_threshold_sec)
        norm_ledger = min(1.0, state.ledger_conflicts / self.config.ledger_conflicts_threshold)
        norm_fallback = min(1.0, state.fallback_cascade_depth / self.config.fallback_depth_threshold)

        penalty = (
            self.config.alpha * norm_lat +
            self.config.beta * norm_err +
            self.config.gamma * norm_queue +
            self.config.delta * norm_ledger +
            self.config.epsilon * norm_fallback
        )
        
        score = 1.0 - penalty
        return max(0.0, min(1.0, score))

    def evaluate(self, state: VMeshState) -> Dict[str, Any]:
        """Performs a full evaluation cycle."""
        score = self.calculate_score(state)
        delta_s = score - self._last_score
        self._last_score = score
        
        self.history.append(state)
        if len(self.history) > 1000:
            self.history.pop(0)

        return {
            "stability_score_s": score,
            "delta_s": delta_s,
            "timestamp": datetime.fromtimestamp(state.timestamp, tz=timezone.utc).isoformat(),
            "state_vector": {
                "q": state.queue_age_p95_sec,
                "l": state.ledger_conflicts,
                "e": state.error_rate,
                "r": state.fallback_cascade_depth,
                "s": state.latency_p95_ms
            }
        }

    def estimate_recovery_half_life(self, target_s: float = 0.85) -> Optional[float]:
        """
        Estimates the time R until the system recovers to target_s.
        Simplified estimation based on recent trend.
        """
        if len(self.history) < 2:
            return None
        
        # Very naive linear extrapolation for now
        # R = RecoveryHalfLife(S)
        recent = self.history[-1]
        prev = self.history[-2]
        
        current_s = self.calculate_score(recent)
        prev_s = self.calculate_score(prev)
        
        if current_s >= target_s:
            return 0.0
            
        rate_of_improvement = (current_s - prev_s) / (recent.timestamp - prev.timestamp)
        if rate_of_improvement <= 0:
            return float('inf') # Not recovering
            
        time_to_target = (target_s - current_s) / rate_of_improvement
        return time_to_target
