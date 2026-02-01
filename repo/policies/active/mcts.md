 # --- MCTS LOGGING (CONDITIONAL) ---
    mcts_trace = job.payload.get("mcts_trace")
    if mcts_trace:
        try:
            from core.scoring import compute_score_v1
            from core.mcts_light import mcts
            from core.decision_trace import trace_logger
            
            # 1. Compute Score
            success = 1.0 if job.status == "completed" else 0.0
            # Heuristics for quality/reliability/risk for now
            quality = job.result.get("quality", 1.0) if job.result else 1.0
            reliability = 1.0 if job.retry_count == 0 else (1.0 / (job.retry_count + 1))
            
            # Get metrics from result if available
            metrics = job.result.get("metrics", {})
            latency_ms = metrics.get("latency_ms", worker_latency_ms)
            cost = metrics.get("cost", job.payload.get("mesh", {}).get("cost", 0))
            tokens = metrics.get("tokens", 0)
            risk = metrics.get("risk", 0.0)
            
            score_bd = compute_score_v1(
                success=success,
                quality=quality,
                reliability=reliability,
                latency_ms=latency_ms,
                cost=cost,
                risk=risk
            )
            
            # 2. Update Policy
            chosen_id = mcts_trace.get("chosen_action_id")
            chosen_action = next((c for c in mcts_trace.get("candidates", []) if c.get("action_id") == chosen_id), None)
            if chosen_action:
                mcts.update_policy(
                    intent=mcts_trace["intent"],
                    action_key=chosen_action["action_key"],
                    score=score_bd["score"]
                )
            
            # 3. Log Trace Node
            trace_logger.log_node(
                trace_id=mcts_trace["trace_id"],
                intent=mcts_trace["intent"],
                build_id=mcts_trace.get("build_id", "main-v2"),
                job_id=job_id,
                state=normalize_trace_state({
                    "context_refs": [f"job:{job_id}", f"chain:{job.payload.get('_chain_hint', {}).get('chain_id')}"],
                    "constraints": {"budget_remaining": 100, "risk_level": "low"}
                }),
                action=normalize_trace_action(chosen_action),
                result=normalize_trace_result({
                    "status": "success" if job.status == "completed" else "failed",
                    "metrics": {
                        "latency_ms": latency_ms,
                        "cost": cost,
                        "tokens": tokens,
                        "retries": job.retry_count,
                        "risk": risk,
                        "quality": quality
                    },
                    "score": score_bd["score"]
                })
            )
        except Exception as te:
            print(f"[main] Warning: MCTS logging failed: {te}")