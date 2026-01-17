# repo/core/store.py
import json
import sqlite3
import os
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

from core import config, models
from core.database import get_db, init_db

# ------------------------------------------------------------------------------
# UTILS
# ------------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat() + "Z"

def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def _json_loads(s: str) -> Any:
    return json.loads(s) if s else None

# ------------------------------------------------------------------------------
# INITIALIZATION
# ------------------------------------------------------------------------------

def initialize():
    """Initializes DB and directories."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    init_db()

# ------------------------------------------------------------------------------
# MISSIONS
# ------------------------------------------------------------------------------

def create_mission(mission: models.Mission, conn: Optional[sqlite3.Connection] = None) -> models.Mission:
    if conn:
        conn.execute("""
            INSERT INTO missions (id, title, description, user_id, status, metadata, tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (mission.id, mission.title, mission.description, mission.user_id, mission.status, 
              _json_dumps(mission.metadata), _json_dumps(mission.tags), mission.created_at))
    else:
        with get_db() as c:
            c.execute("""
                INSERT INTO missions (id, title, description, user_id, status, metadata, tags, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (mission.id, mission.title, mission.description, mission.user_id, mission.status, 
                  _json_dumps(mission.metadata), _json_dumps(mission.tags), mission.created_at))
            c.commit()
    return mission

def get_mission(mission_id: str) -> Optional[models.Mission]:
    with get_db() as conn:
        r = conn.execute("SELECT * FROM missions WHERE id = ?", (mission_id,)).fetchone()
        if not r: return None
        return models.Mission(
            id=r['id'], title=r['title'], description=r['description'],
            user_id=r['user_id'], status=r['status'],
            metadata=_json_loads(r['metadata']), tags=_json_loads(r['tags']),
            created_at=r['created_at']
        )

def get_all_missions() -> List[models.Mission]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM missions ORDER BY created_at DESC").fetchall()
        return [
            models.Mission(
                id=r['id'], title=r['title'], description=r['description'],
                user_id=r['user_id'], status=r['status'],
                metadata=_json_loads(r['metadata']), tags=_json_loads(r['tags']),
                created_at=r['created_at']
            ) for r in rows
        ]

# ------------------------------------------------------------------------------
# TASKS
# ------------------------------------------------------------------------------

def create_task(task: models.Task, conn: Optional[sqlite3.Connection] = None) -> models.Task:
    if conn:
        conn.execute("""
            INSERT INTO tasks (id, mission_id, name, description, kind, params, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (task.id, task.mission_id, task.name, task.description, task.kind, 
              _json_dumps(task.params), task.created_at))
    else:
        with get_db() as c:
            c.execute("""
                INSERT INTO tasks (id, mission_id, name, description, kind, params, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (task.id, task.mission_id, task.name, task.description, task.kind, 
                  _json_dumps(task.params), task.created_at))
            c.commit()
    return task

def get_task(task_id: str) -> Optional[models.Task]:
    with get_db() as conn:
        r = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not r: return None
        return models.Task(
            id=r['id'], mission_id=r['mission_id'], name=r['name'],
            description=r['description'], kind=r['kind'],
            params=_json_loads(r['params']), created_at=r['created_at']
        )

# ------------------------------------------------------------------------------
# JOBS
# ------------------------------------------------------------------------------

def create_job(job: models.Job, conn: Optional[sqlite3.Connection] = None) -> models.Job:
    def _do_insert(c):
        c.execute("""
            INSERT INTO jobs (id, task_id, payload, status, result, retry_count, idempotency_key, 
                             idempotency_hash, completed_result, idempotency_first_seen_utc, 
                             meta, result_hash, result_hash_alg, result_canonical, priority, 
                             timeout_seconds, depends_on, lease_owner, lease_until_utc, 
                             next_retry_utc, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job.id, job.task_id, _json_dumps(job.payload), job.status, 
            _json_dumps(job.result) if job.result else None, job.retry_count,
            job.idempotency_key, job.idempotency_hash, 
            _json_dumps(job.completed_result) if job.completed_result else None,
            job.idempotency_first_seen_utc, _json_dumps(job.meta),
            job.result_hash, job.result_hash_alg, job.result_canonical,
            job.priority, job.timeout_seconds, _json_dumps(job.depends_on),
            job.lease_owner, job.lease_until_utc, job.next_retry_utc,
            job.created_at, job.updated_at
        ))

    if conn:
        _do_insert(conn)
    else:
        with get_db() as c:
            _do_insert(c)
            c.commit()
    
    # --- SOUL: TRACE INTEGRATION ---
    try:
        from core.trace import trace_logger
        trace_logger.log_node(
            trace_id=f"job-init-{job.id}",
            intent="job_created",
            build_id=os.getenv("SHERATAN_BUILD_ID", "evolution-v1"),
            job_id=job.id,
            state={"payload_kind": job.payload.get("kind") if isinstance(job.payload, dict) else "raw"},
            action={"type": "EXECUTE", "params": {"job_id": job.id}},
            result={"status": "success"}
        )
    except Exception as e:
        print(f"[store] Trace warning: {e}")

    return job

def update_job(job: models.Job) -> None:
    now = _now_iso()
    with get_db() as conn:
        conn.execute("""
            UPDATE jobs SET 
                status=?, result=?, retry_count=?, lease_owner=?, lease_until_utc=?, 
                next_retry_utc=?, updated_at=?, completed_result=?, result_hash=?, 
                result_hash_alg=?, result_canonical=?, meta=?
            WHERE id=?
        """, (
            job.status, _json_dumps(job.result) if job.result else None, job.retry_count,
            job.lease_owner, job.lease_until_utc, job.next_retry_utc, now,
            _json_dumps(job.completed_result) if job.completed_result else None,
            job.result_hash, job.result_hash_alg, job.result_canonical,
            _json_dumps(job.meta), job.id
        ))
        conn.commit()
    
    # --- SOUL: TRACE INTEGRATION ---
    if job.status in ["completed", "failed"]:
        try:
            from core.trace import trace_logger
            trace_logger.log_node(
                trace_id=f"job-{job.id}",
                intent="job_finalized",
                build_id=os.getenv("SHERATAN_BUILD_ID", "evolution-v1"),
                job_id=job.id,
                state={"status": job.status},
                action={"type": "EXECUTE", "params": {"job_id": job.id}},
                result={"status": "success" if job.status == "completed" else "failed"}
            )
        except Exception as e:
            print(f"[store] Trace warning: {e}")

def lease_next_job(worker_id: str, lease_sec: int) -> Optional[models.Job]:
    now = _now_iso()
    lease_until = (datetime.now(timezone.utc) + timedelta(seconds=lease_sec)).isoformat() + "Z"
    
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("""
                SELECT id FROM jobs 
                WHERE status = 'pending' 
                  AND (next_retry_utc IS NULL OR next_retry_utc <= ?)
                ORDER BY created_at ASC LIMIT 1
            """, (now,)).fetchone()
            
            if not row:
                conn.execute("COMMIT")
                return None
            
            job_id = row[0]
            conn.execute("""
                UPDATE jobs SET status = 'working', lease_owner = ?, lease_until_utc = ?, updated_at = ?
                WHERE id = ?
            """, (worker_id, lease_until, now, job_id))
            conn.commit()
            
            # Re-fetch full model
            r = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            return models.Job(**{k: (r[k] if k not in ["payload", "result", "completed_result", "meta", "depends_on"] 
                                     else _json_loads(r[k])) for k in r.keys()})
        except Exception:
            conn.execute("ROLLBACK")
            raise

# ------------------------------------------------------------------------------
# CHAIN CONTEXT
# ------------------------------------------------------------------------------

def get_chain_context(conn, chain_id: str) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM chain_context WHERE chain_id=?", (chain_id,)).fetchone()
    if not row: return None
    return {
        "chain_id": row["chain_id"], "task_id": row["task_id"], "state": row["state"],
        "limits": _json_loads(row["limits_json"]), "artifacts": _json_loads(row["artifacts_json"]),
        "error": _json_loads(row["error_json"]), "needs_tick": bool(row["needs_tick"])
    }

def ensure_chain_context(
    conn,
    chain_id: str,
    task_id: str,
    limits: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Idempotent: creates chain_context row if not exists."""
    limits = limits or {
        "max_files": 50,
        "max_total_bytes": 200_000,
        "max_bytes_per_file": 50_000,
    }
    now = _now_iso()
    conn.execute(
        """
        INSERT OR IGNORE INTO chain_context
        (chain_id, task_id, state, limits_json, artifacts_json, error_json, needs_tick, created_at, updated_at)
        VALUES (?, ?, 'running', ?, ?, NULL, 0, ?, ?)
        """,
        (chain_id, task_id, _json_dumps(limits), _json_dumps({}), now, now),
    )
    # Note: caller should commit if needed
    return get_chain_context(conn, chain_id)

def set_chain_needs_tick(conn, chain_id: str, needs_tick: bool) -> None:
    """Set needs_tick flag for chain runner."""
    now = _now_iso()
    conn.execute(
        "UPDATE chain_context SET needs_tick=?, updated_at=? WHERE chain_id=?",
        (1 if needs_tick else 0, now, chain_id),
    )

def append_chain_specs(
    conn,
    chain_id: str,
    task_id: str,
    root_job_id: str,
    parent_job_id: str,
    specs: List[Dict[str, Any]],
) -> List[str]:
    """Inserts specs as pending; dedupe via UNIQUE(chain_id, dedupe_key)."""
    now = _now_iso()
    inserted: List[str] = []

    for s in specs:
        kind = s.get("kind") or s.get("type")
        params = s.get("params") if isinstance(s.get("params"), dict) else {k: v for k, v in s.items() if k not in ("kind", "type")}
        
        # Dedupe key: chain_id + kind + hash of params
        raw = _json_dumps({"parent_job_id": parent_job_id, "kind": kind, "params": params}).encode("utf-8")
        dedupe_key = hashlib.sha256(raw).hexdigest()

        spec_id = s.get("spec_id") or uuid.uuid4().hex

        try:
            conn.execute(
                """
                INSERT INTO chain_specs
                (spec_id, chain_id, task_id, root_job_id, parent_job_id, kind, params_json,
                 resolved_params_json, resolved, status, dedupe_key, dispatched_job_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 0, 'pending', ?, NULL, ?, ?)
                """,
                (spec_id, chain_id, task_id, root_job_id, parent_job_id, kind, _json_dumps(params), dedupe_key, now, now),
            )
            inserted.append(spec_id)
        except Exception:
            continue
    return inserted

def list_chains_needing_tick(conn, limit: int = 20) -> List[str]:
    rows = conn.execute(
        "SELECT chain_id FROM chain_context WHERE needs_tick=1 AND state='running' LIMIT ?",
        (limit,)
    ).fetchall()
    return [r[0] for r in rows]

def claim_next_pending_spec(conn, chain_id: str, lease_seconds: int = 60) -> Optional[Dict[str, Any]]:
    """Atomically pick and lease the oldest pending spec."""
    now_iso = _now_iso()
    now_dt = datetime.now(timezone.utc)
    expires_iso = (now_dt + timedelta(seconds=lease_seconds)).isoformat() + "Z"
    claim_id = str(uuid.uuid4())

    row = conn.execute(
        """
        SELECT spec_id FROM chain_specs
        WHERE chain_id=? AND status='pending'
          AND (claimed_until IS NULL OR claimed_until < ?)
        ORDER BY created_at ASC LIMIT 1
        """,
        (chain_id, now_iso),
    ).fetchone()

    if not row: return None
    spec_id = row[0]

    conn.execute(
        """
        UPDATE chain_specs
        SET claim_id=?, claimed_until=?, updated_at=?
        WHERE spec_id=? AND status='pending'
          AND (claimed_until IS NULL OR claimed_until < ?)
        """,
        (claim_id, expires_iso, now_iso, spec_id, now_iso),
    )
    
    if conn.total_changes == 0: return None

    # Load full spec
    r = conn.execute(
        """
        SELECT spec_id, task_id, root_job_id, parent_job_id, kind, params_json, resolved_params_json, resolved, status, dedupe_key, claim_id, claimed_until, dispatched_job_id
        FROM chain_specs WHERE spec_id=?
        """,
        (spec_id,),
    ).fetchone()
    
    return {
        "spec_id": r[0], "chain_id": chain_id, "task_id": r[1],
        "root_job_id": r[2], "parent_job_id": r[3], "kind": r[4],
        "params": _json_loads(r[5]) or {},
        "resolved_params": _json_loads(r[6]) if r[6] else None,
        "resolved": bool(r[7]), "status": r[8], "dedupe_key": r[9],
        "claim_id": r[10], "claimed_until": r[11], "dispatched_job_id": r[12],
    }

def mark_chain_spec_dispatched(conn, chain_id: str, spec_id: str, job_id: str) -> None:
    now = _now_iso()
    conn.execute(
        "UPDATE chain_specs SET status='dispatched', dispatched_job_id=?, updated_at=? WHERE chain_id=? AND spec_id=?",
        (job_id, now, chain_id, spec_id),
    )

def set_chain_artifact(conn, chain_id: str, key: str, value: Any, meta: Optional[dict] = None) -> None:
    ctx = get_chain_context(conn, chain_id)
    if not ctx: return
    artifacts = ctx["artifacts"]
    artifacts[key] = {"value": value, "meta": meta or {}}
    conn.execute("UPDATE chain_context SET artifacts_json=?, updated_at=? WHERE chain_id=?",
                 (_json_dumps(artifacts), _now_iso(), chain_id))
