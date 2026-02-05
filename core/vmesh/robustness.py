# core/vmesh/robustness.py
from __future__ import annotations
import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
from core.vmesh.stability import StabilityEvaluator, VMeshState

class RobustnessHarness:
    """
    RobustnessTestHarness (Module B)
    Operationalizes sensitivity minimization ||dS/dw|| via Chaos Profiles.
    """
    def __init__(self, evaluator: StabilityEvaluator):
        self.evaluator = evaluator
        self.reports: List[Dict[str, Any]] = []

    async def run_chaos_profile(self, name: str, profile_fn: Callable[[], Any]) -> Dict[str, Any]:
        """
        Executes a chaos profile and measures the system's reaction.
        """
        s_baseline = self.evaluator._last_score
        start_t = time.time()

        # Inject disturbance
        await profile_fn()
        
        # Observation phase (simplified simulation of metric collection)
        # In a live system, this would wait for the next evaluator tick.
        await asyncio.sleep(1.0) 
        
        s_disturbed = self.evaluator._last_score
        
        # Calculate Delta J / Delta w (approximated)
        # Sensitivity = |S_baseline - S_disturbed|
        sensitivity = abs(s_baseline - s_disturbed)
        
        # KPIs
        report = {
            "profile_name": name,
            "s_baseline": s_baseline,
            "s_disturbed": s_disturbed,
            "sensitivity": sensitivity,
            "mttr_sec": None, # Will be filled if recovery occurs
            "robustness_score": 1.0 - sensitivity,
            "timestamp": time.time()
        }
        
        self.reports.append(report)
        return report

    def get_robustness_scorecard(self) -> Dict[str, Any]:
        """Returns a summary of all chaos tests."""
        if not self.reports:
            return {"status": "no_data"}
            
        avg_sensitivity = sum(r["sensitivity"] for r in self.reports) / len(self.reports)
        return {
            "avg_sensitivity": avg_sensitivity,
            "overall_robustness": 1.0 - avg_sensitivity,
            "test_count": len(self.reports),
            "last_report": self.reports[-1] if self.reports else None
        }
