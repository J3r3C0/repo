# core/vmesh/sync.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

@dataclass
class ReferenceState:
    """The 'Sheratan-Reference' vector r."""
    slo_latency_p95: float = 2000.0
    budget_cap: float = 100.0
    schema_version: str = "v2.1"
    policy_hash: str = "default"

class SynchronizationLayer:
    """
    SynchronizationLayer (Module D)
    Detects drift from the reference state r. Implements Kuramoto-style 
    alignment goals.
    """
    def __init__(self, target: Optional[ReferenceState] = None):
        self.target = target or ReferenceState()
        self.node_states: Dict[str, Dict[str, Any]] = {}

    def update_node(self, node_id: str, state: Dict[str, Any]) -> float:
        """Updates node state and returns drift score."""
        self.node_states[node_id] = state
        drift = self._calculate_drift(state)
        return drift

    def _calculate_drift(self, state: Dict[str, Any]) -> float:
        """
        Calculates drift D = 1[p_i != p_ref] + 1[h_i != h_ref] + norm(|T_i - T_ref|).
        """
        d_policy = 1.0 if state.get("policy_hash") != self.target.policy_hash else 0.0
        d_schema = 1.0 if state.get("schema_version") != self.target.schema_version else 0.0
        
        lat = state.get("latency_p95", 0.0)
        t_ref = self.target.slo_latency_p95
        d_slo = min(1.0, abs(lat - t_ref) / t_ref) if t_ref > 0 else 1.0
        
        # Total drift (max is 3.0)
        return d_policy + d_schema + d_slo

    def get_global_sync(self) -> float:
        """
        Global Synchronization Score \in [0, 1].
        sync = 1 - mean(drifts) / complexity_factor
        """
        if not self.node_states:
            return 1.0
            
        total_drift = sum(self._calculate_drift(s) for s in self.node_states.values())
        avg_drift = total_drift / len(self.node_states)
        
        # Scale to [0, 1]
        sync = 1.0 - (avg_drift / 3.0)
        return max(0.0, sync)
