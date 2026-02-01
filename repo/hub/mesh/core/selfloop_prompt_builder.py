from __future__ import annotations
from typing import Any, Dict, List, Optional

def build_selfloop_job_payload(
    goal: str,
    initial_context: str = "",
    max_iterations: int = 10,
    constraints: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Builds the payload for a Sheratan Self-Loop job.
    Optimized for collaborative co-thinking between Brain and Body.
    """
    return {
        "job_type": "sheratan_selfloop",
        "kind": "self_loop",
        "goal": goal,
        "loop_state": {
            "iteration": 1,
            "max_iterations": max_iterations,
            "context": initial_context,
            "history": []
        },
        "constraints": constraints or [
            {"type": "budget", "value": 100},
            {"type": "risk", "value": "low"}
        ]
    }

def build_selfloop_prompt(goal: str, context: str, iteration: int) -> str:
    """
    Builds the MCTS-Light system prompt for self-loop iterations.
    """
    return f"GOAL: {goal}\nCONTEXT: {context}\nITERATION: {iteration}\nAnalyze the current state and propose the next action."
