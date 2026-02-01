#!/usr/bin/env python
"""
scripts/ingest_draft_sdk.py

Reference ingest script migrated to sheratan-sdk.
- Creates Mission → Task → Job using Core-aligned schemas.
- Avoids legacy /api/job/submit to eliminate 405 drift.

Usage:
  python scripts/ingest_draft_sdk.py --title "Demo" --description "..." --kind read_file --param path=core/main.py
  python scripts/ingest_draft_sdk.py --title "Demo" --task-name "T1" --kind walk_tree --param path=.

Params:
  --param key=value  (repeatable)
"""
from __future__ import annotations

import argparse
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
    ap.add_argument("--title", required=True)
    ap.add_argument("--description", default="")
    ap.add_argument("--meta", action="append", default=[], help="metadata key=value (repeatable)")

    ap.add_argument("--task-name", default="task-1")
    ap.add_argument("--kind", required=True, help="task kind (e.g., read_file, agent_plan, walk_tree)")
    ap.add_argument("--param", action="append", default=[], help="task params key=value (repeatable)")

    ap.add_argument("--job-priority", type=int, default=0)
    ap.add_argument("--job-payload", action="append", default=[], help="job payload key=value (repeatable)")
    ap.add_argument("--depends-on", action="append", default=[], help="depends_on job ids (repeatable)")

    args = ap.parse_args()

    metadata = parse_kv(args.meta)
    params = parse_kv(args.param)
    payload = parse_kv(args.job_payload)

    c = SheratanClient()

    mission = c.create_mission(title=args.title, description=args.description, metadata=metadata)
    mission_id = mission.get("id") or mission.get("mission_id") or mission.get("uuid")
    if not mission_id:
        raise RuntimeError(f"Could not find mission id in response: {mission}")

    task = c.create_task(mission_id=mission_id, name=args.task_name, kind=args.kind, params=params)
    task_id = task.get("id") or task.get("task_id") or task.get("uuid")
    if not task_id:
        raise RuntimeError(f"Could not find task id in response: {task}")

    job = c.create_job(task_id=task_id, payload=payload, priority=args.job_priority, depends_on=args.depends_on)
    print("MISSION:", mission_id)
    print("TASK:", task_id)
    print("JOB:", job.get("id") or job.get("job_id") or job)

if __name__ == "__main__":
    main()
