"""
tests/smoke_e2e_sdk.py

Deterministic smoke test using sheratan-sdk only.
Exit codes:
  0 PASS
  1 WARN (worker not running / still pending)
  2 FAIL
"""
from __future__ import annotations

import argparse
import time
from typing import Dict, Any

from sheratan_sdk import SheratanClient


def parse_kv(items) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for it in items or []:
        if "=" not in it:
            raise SystemExit(f"--param must be key=value, got: {it}")
        k, v = it.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="sdk-smoke")
    ap.add_argument("--description", default="sdk smoke test")
    ap.add_argument("--kind", required=True)
    ap.add_argument("--task-name", default="smoke-task")
    ap.add_argument("--param", action="append", default=[])
    ap.add_argument("--wait-s", type=int, default=15)
    args = ap.parse_args()

    params = parse_kv(args.param)

    c = SheratanClient()

    mission = c.create_mission(args.title, args.description, metadata={"type": "smoke"})
    mission_id = mission.get("id") or mission.get("mission_id") or mission.get("uuid")

    task = c.create_task(mission_id, name=args.task_name, kind=args.kind, params=params)
    task_id = task.get("id") or task.get("task_id") or task.get("uuid")

    job = c.create_job(task_id, payload={"intent": "smoke"}, priority=0, depends_on=[])
    job_id = job.get("id") or job.get("job_id") or job.get("uuid")

    if not job_id:
        raise RuntimeError(f"Could not find job id in response: {job}")

    print(f"[SMOKE] mission={mission_id} task={task_id} job={job_id}")
    deadline = time.time() + args.wait_s
    last_status = None

    while time.time() < deadline:
        j = c.get_job(job_id)
        last_status = (j.get("status") or j.get("state") or "").lower()
        print(f"[SMOKE] status={last_status}")
        if last_status == "completed":
            print("[SMOKE] ✅ PASS")
            raise SystemExit(0)
        if last_status == "failed":
            print("[SMOKE] ❌ FAIL (job failed)")
            raise SystemExit(2)
        time.sleep(1.0)

    if last_status in ("pending", "working", "", None):
        print("[SMOKE] ⚠️  WARN (worker not running or still processing)")
        raise SystemExit(1)

    print("[SMOKE] ❌ FAIL (unexpected status)")
    raise SystemExit(2)


if __name__ == "__main__":
    main()
