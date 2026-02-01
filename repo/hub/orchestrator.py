from core.engine import SheratanEngine
from hub.scoring import compute_score_v1
from hub.mcts_light import mcts
from hub.decision_trace import trace_logger
from hub.candidate_schema import Candidate, candidates_to_dicts
from core.determinism import compute_input_hash, compute_output_hash
import time
import uuid

class SheratanOrchestrator:
    def __init__(self, config):
        self.engine = SheratanEngine(config)
        self.config = config

    def process_event(self, event):
        # 1. Pure Core Processing
        state, res = self.engine.process_event(event)

        # 2. Agency Layer: Scoring (Phase 4-5 Extension)
        best_sim = state.last_similarity if hasattr(state, 'last_similarity') else 1.0
        
        score_data = compute_score_v1(
            success=min(1.0, state.weight / 10.0),
            quality=best_sim,
            reliability=1.0,
            latency_ms=0.0,
            cost=0.0,
            risk=0.0
        )
        state.current_score = score_data["score"]

        # 3. Agency Layer: MCTS Action Selection
        intent = "perceptual_focus"
        candidates = [
            {"type": "focus_increase", "params": {"state_id": state.state_id}, "risk_gate": True},
            {"type": "monitor_stable", "params": {"state_id": state.state_id}, "risk_gate": True}
        ]
        
        best_action, _ = mcts.select_action(intent, candidates)
        state.recommended_action = best_action

        return state, res

    def dispatch_job(self, job_id, bridge, intent="dispatch_job", build_id="main", kind="llm_call"):
        """
        Agency-level dispatch with MCTS selection and decision tracing.
        Replaces direct bridge.enqueue_job with an agentic choice.
        """
        # 1. Build candidates
        candidates = self._build_dispatch_candidates(job_id, bridge, kind)
        candidate_dicts = candidates_to_dicts(candidates)
        
        # 2. MCTS selection
        chosen_dict, scored_dicts = mcts.select_action(intent, candidate_dicts)
        
        # 3. Execution
        start_time = time.time()
        try:
            if chosen_dict["type"] == "ROUTE":
                bridge.enqueue_job(job_id)
                result_status = "success"
                result_error = None
            elif chosen_dict["type"] == "SKIP":
                result_status = "skipped"
                result_error = None
            else:
                result_status = "failed"
                result_error = {"code": "UNKNOWN_ACTION", "message": f"Unknown type: {chosen_dict['type']}"}
        except Exception as e:
            result_status = "failed"
            result_error = {"code": "DISPATCH_ERROR", "message": str(e)}
        
        latency_ms = (time.time() - start_time) * 1000
        
        # 4. Scoring & Tracing
        score_breakdown = compute_score_v1(
            success=1.0 if result_status == "success" else 0.0,
            quality=0.8,
            reliability=0.9,
            latency_ms=latency_ms,
            cost=0.0,
            risk=chosen_dict.get("risk_penalty", 0.0)
        )
        
        node_id = trace_logger.log_node(
            trace_id=str(uuid.uuid4()),
            intent=intent,
            build_id=build_id,
            state={"context_refs": [f"job:{job_id}"], "constraints": {"risk_level": "low"}},
            action=chosen_dict,
            result={"status": result_status, "score": score_breakdown["score"], "metrics": {"latency_ms": latency_ms}},
            job_id=job_id
        )
        
        if node_id:
            mcts.update_policy(intent, chosen_dict["prior_key"], score_breakdown["score"])
            
        return {"success": result_status == "success", "node_id": node_id, "score": score_breakdown["score"]}

    def _build_dispatch_candidates(self, job_id, bridge, kind):
        candidates = []
        if bridge.registry:
            workers = bridge.registry.find_workers_for_kind(kind)
            for worker in workers:
                is_eligible = bridge.registry.is_eligible(worker.worker_id)
                candidates.append(Candidate(
                    action_id=f"route_{worker.worker_id}_{job_id[:8]}",
                    type="ROUTE", mode="execute",
                    params={"target": "worker", "worker_id": worker.worker_id, "kind": kind},
                    risk_gate=is_eligible,
                    risk_penalty=0.0 if is_eligible else 0.5
                ))
        if bridge.settings and bridge.settings.relay_out_dir:
            candidates.append(Candidate(
                action_id=f"route_webrelay_{job_id[:8]}",
                type="ROUTE", mode="execute",
                params={"target": "webrelay"},
                risk_gate=True, risk_penalty=0.1
            ))
        candidates.append(Candidate(
            action_id=f"skip_{job_id[:8]}",
            type="SKIP", mode="simulate",
            params={}, risk_gate=False, risk_penalty=1.0
        ))
        return candidates
