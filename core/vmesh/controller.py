# core/vmesh/controller.py
from __future__ import annotations
from enum import Enum
from typing import Dict, Any, Optional
from core.vmesh.stability import StabilityEvaluator, VMeshState
from core.vmesh.complexity import ComplexityTracker
from core.vmesh.sync import SynchronizationLayer

class PolicyMode(Enum):
    NORMAL = "NORMAL"
    THROTTLE = "THROTTLE"
    READONLY = "READONLY"
    DEGRADED = "DEGRADED"
    SAFE_MODE = "SAFE_MODE"

class VMeshController:
    """
    Router as Control Policy (Module E)
    The decision function u(t) = pi(x(t)).
    Integrates Stability, Complexity, and Sync to choose the optimal mode.
    """
    def __init__(
        self,
        evaluator: StabilityEvaluator,
        complexity: ComplexityTracker,
        sync: SynchronizationLayer
    ):
        self.evaluator = evaluator
        self.complexity = complexity
        self.sync = sync
        self.current_mode = PolicyMode.NORMAL

    def decide_mode(self, x_t: VMeshState) -> PolicyMode:
        """
        Optimal policy decision based on the system state vector.
        """
        s_score = self.evaluator.calculate_score(x_t)
        sync_score = self.sync.get_global_sync()
        complexity_status = self.complexity.get_status()
        
        # 1. Critical Failure -> SAFE_MODE
        if s_score < 0.3 or x_t.error_rate > 0.5:
            self.current_mode = PolicyMode.SAFE_MODE
            return self.current_mode
            
        # 2. Significant Degradation or Low Sync -> DEGRADED
        if s_score < 0.6 or sync_score < 0.5:
            self.current_mode = PolicyMode.DEGRADED
            return self.current_mode
            
        # 3. High Latency or Budget Overrun -> THROTTLE
        if s_score < 0.85 or complexity_status["status"] == "OVER_BUDGET":
            self.current_mode = PolicyMode.THROTTLE
            return self.current_mode
            
        # 4. Default -> NORMAL
        self.current_mode = PolicyMode.NORMAL
        return self.current_mode

    def get_control_status(self) -> Dict[str, Any]:
        return {
            "mode": self.current_mode.value,
            "stability_s": self.evaluator._last_score,
            "sync_score": self.sync.get_global_sync(),
            "complexity": self.complexity.get_status()
        }
