# core/vmesh/complexity.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

@dataclass
class ComplexityBudget:
    """
    MDL / Complexity Budget (Module C)
    Tracks system complexity C to ensure Delta S / Delta C > 0.
    """
    lambda_branches: float = 1.0
    lambda_rules: float = 5.0
    lambda_formats: float = 10.0
    lambda_flags: float = 2.0

    max_budget: float = 1000.0

class ComplexityTracker:
    def __init__(self, budget: Optional[ComplexityBudget] = None):
        self.budget = budget or ComplexityBudget()
        self._current_c: float = 0.0

    def calculate_complexity(
        self, 
        branch_count: int, 
        rule_count: int, 
        format_count: int, 
        flag_count: int
    ) -> float:
        """Calculates Kolmogorov/MDL proxy C."""
        b = self.budget
        c = (b.lambda_branches * branch_count + 
             b.lambda_rules * rule_count + 
             b.lambda_formats * format_count + 
             b.lambda_flags * flag_count)
        self._current_c = c
        return c

    def get_status(self) -> Dict[str, Any]:
        return {
            "current_complexity_c": self._current_c,
            "budget_limit": self.budget.max_budget,
            "utilization": self._current_c / self.budget.max_budget if self.budget.max_budget > 0 else 0,
            "status": "OVER_BUDGET" if self._current_c > self.budget.max_budget else "OK"
        }

    def evaluate_change(self, delta_s: float, delta_c: float) -> bool:
        """
        Hard Implementation of "Verbessern = Entfernen".
        If delta_c is positive (Complexity increases), delta_s must be positive.
        """
        if delta_c > 0 and delta_s <= 0:
            return False # Complexity increased without stability gain
        return True
