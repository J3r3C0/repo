import os
import shutil
from pathlib import Path

files_to_move = [
    "anomaly_detector.py", "attestation.py", "chain_index.py", "chain_runner.py",
    "context_updaters.py", "core_heartbeat.py", "decision_trace.py", "envelope.py",
    "gateway_middleware.py", "heartbeat_monitor.py", "idempotency.py", "job_chain_manager.py",
    "lcp_actions.py", "metrics_client.py", "rate_limiter.py", "robust_parser.py",
    "self_diagnostics.py", "state_machine.py", "template_resolver.py", "webrelay_bridge.py",
    "webrelay_http_client.py", "webrelay_llm_client.py", "why_api.py", "why_api_test.py",
    "database.py", "models.py", "storage.py", "candidate_schema.py", "health.py"
]

repo_root = Path(os.getcwd())
core_dir = repo_root / "core"
hub_dir = repo_root / "hub"

hub_dir.mkdir(exist_ok=True)

for f in files_to_move:
    src = core_dir / f
    dst = hub_dir / f
    if src.exists():
        print(f"Moving {f} to hub/")
        shutil.move(str(src), str(dst))
    else:
        print(f"Skipping {f}, not found in core/")
