# core/lcp_actions.py
"""
LCP (LLM Control Protocol) Actions Parser
Handles parsing of LLM responses for job chaining (Phase 9).
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
<<<<<<< HEAD:core/lcp_actions.py
=======
import json
from hub.robust_parser import extract_json_from_text
>>>>>>> 0d05299baf01209327a7b0a1e6eb7b526f866bcb:hub/lcp_actions.py


@dataclass
class FollowupJobs:
    """Represents a request for follow-up jobs from LLM."""
    chain_id: str
    jobs: List[Dict[str, Any]]


@dataclass
class FinalAnswer:
    """Represents a final answer from LLM (chain complete)."""
    chain_id: str
    answer: Dict[str, Any]


def is_lcp_message(result: Dict[str, Any]) -> bool:
    """
    Return True if result looks like an LCP envelope (v1 or legacy).
    """
    if not isinstance(result, dict):
        return False
    
    # v1 format or v2.x 'lcp' marker
    if "lcp_version" in result or result.get("type") == "lcp":
        return True
    
    # legacy format / explicit actions
    if result.get("action") in ["create_followup_jobs", "analysis_result", "final_answer"]:
        return True
    
    # check for presence of jobs or new_jobs
    if "jobs" in result or "new_jobs" in result:
        return True
        
    return False


def parse_lcp(result: Dict[str, Any], *, default_chain_id: str) -> Tuple[Optional[FollowupJobs], Optional[FinalAnswer]]:
    """
    Parse LCP envelope from result.
    """
<<<<<<< HEAD:core/lcp_actions.py
    if not is_lcp_message(result):
=======
    if isinstance(result, str):
        extracted = extract_json_from_text(result)
        if extracted:
            result = extracted
        else:
            return (None, None)

    if not isinstance(result, dict) or not is_lcp_message(result):
>>>>>>> 0d05299baf01209327a7b0a1e6eb7b526f866bcb:hub/lcp_actions.py
        return (None, None)
    
    # Get chain_id (with fallback)
    chain_id = result.get("chain_id") or result.get("chain", {}).get("chain_id") or default_chain_id
    
    # 1. Determine if it's a follow-up Turn
    jobs = result.get("jobs") or result.get("new_jobs")
    if jobs is not None:
        normalized = normalize_job_specs(jobs)
        return (FollowupJobs(chain_id=chain_id, jobs=normalized), None)
        
    # 2. Determine if it's a final answer
    if result.get("type") == "final_answer" or result.get("action") == "analysis_result" or "answer" in result:
        answer = result.get("answer") or result
        return (None, FinalAnswer(chain_id=chain_id, answer=answer))
    
    return (None, None)


def normalize_job_specs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ensure each spec has: {kind: str, params: dict}
    Supports both v1 (kind/params) and variant (action/args/name) formats.
    """
    normalized = []
    for spec in jobs:
        if not isinstance(spec, dict):
            continue
        
        # Determine Kind: kind > action > name
        kind = spec.get("kind") or spec.get("action") or spec.get("name")
        if not kind:
            continue
        
        # Determine Params: params > args > remaining fields
        params = spec.get("params") or spec.get("args")
        if not isinstance(params, dict):
            # If no explicit params/args dict, treat other top-level fields as params
            params = {k: v for k, v in spec.items() if k not in ("kind", "action", "name", "job_name", "args", "params")}
        
        normalized.append({
            "kind": str(kind),
            "params": params
        })
    
    return normalized


# Legacy LCPActionInterpreter class (kept for backward compatibility)
class LCPActionInterpreter:
    """
    Legacy LCP handler - kept for backward compatibility.
    Phase 9 uses parse_lcp() directly in Core.
    """
    
    def __init__(self, bridge):
        self.bridge = bridge
    
    def handle_job_result(self, job):
        """
        Handle job result - placeholder for compatibility.
        Phase 9: Actual LCP handling is done in Core's sync_job endpoint.
        """
        pass
