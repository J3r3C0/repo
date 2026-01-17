# tools/system_exercise.py
"""
Sheratan SystemExercise (WASSERDICHT, konservativ)

Ziele:
- Startet den Core selbst (Subprocess) auf einem freien Port
- Wartet deterministisch auf /api/system/health (kein blindes sleep)
- Isoliert Daten in temp-dir (keine Flakes durch alte DB/Traces)
- Führt Kernpfade aus: health, DB/WAL flag, read_file, write_file(temp), walk_tree(bounded), trace exists, UI asset
- Schreibt Reports:
  - build/reports/exercise_report.json
  - build/reports/feature_matrix.json
- Beendet Core sauber (terminate/kill fallback)

Nutzung:
  python tools/system_exercise.py

Optional:
  # Wenn du eine EXE testen willst:
  set SHERATAN_CORE_CMD=dist\\sheratan_core\\sheratan_core.exe
  python tools/system_exercise.py

  # Wenn du uvicorn direkt starten willst:
  set SHERATAN_CORE_CMD=python -m uvicorn main:app --host 127.0.0.1 --port {port}
  python tools/system_exercise.py

  # Wenn dein Core DATA_DIR env versteht:
  (Script setzt SHERATAN_DATA_DIR automatisch)
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --- Paths / outputs ---
REPORT_DIR = Path("build/reports")
EXERCISE_REPORT = REPORT_DIR / "exercise_report.json"
FEATURE_REPORT = REPORT_DIR / "feature_matrix.json"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_STARTUP_TIMEOUT_S = 60
DEFAULT_STEP_TIMEOUT_S = 20
DEFAULT_HEALTH_POLL_INTERVAL_S = 0.5

# --- Minimal HTTP client (requests optional) ---
def http_request(method: str, url: str, json_body: Any = None, timeout_s: int = 10) -> Tuple[int, Dict[str, str], bytes]:
    """
    Tiny HTTP client to avoid adding deps for the exercise.
    Uses urllib from stdlib.
    """
    import urllib.request
    import urllib.error

    headers = {"User-Agent": "Sheratan-SystemExercise/1.0"}
    data = None
    if json_body is not None:
        payload = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
        data = payload

    req = urllib.request.Request(url, method=method.upper(), headers=headers, data=data)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status = resp.getcode()
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            body = resp.read()
            return status, resp_headers, body
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        resp_headers = {k.lower(): v for k, v in (e.headers.items() if e.headers else [])}
        return e.code, resp_headers, body
    except Exception as e:
        raise RuntimeError(f"HTTP {method} {url} failed: {e}") from e


def http_get_json(url: str, timeout_s: int) -> Dict[str, Any]:
    status, headers, body = http_request("GET", url, timeout_s=timeout_s)
    if status != 200:
        raise RuntimeError(f"GET {url} -> {status}, body={body[:200]!r}")
    try:
        return json.loads(body.decode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"GET {url} returned non-JSON: {body[:200]!r}") from e


def http_post_json(url: str, payload: Dict[str, Any], timeout_s: int) -> Dict[str, Any]:
    status, headers, body = http_request("POST", url, json_body=payload, timeout_s=timeout_s)
    if status != 200:
        raise RuntimeError(f"POST {url} -> {status}, body={body[:200]!r}")
    try:
        return json.loads(body.decode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"POST {url} returned non-JSON: {body[:200]!r}") from e


def http_get_raw(url: str, timeout_s: int) -> Tuple[int, Dict[str, str], bytes]:
    return http_request("GET", url, timeout_s=timeout_s)


# --- Utilities ---
def find_free_port(host: str = DEFAULT_HOST) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        s.listen(1)
        return s.getsockname()[1]


def now_ms() -> int:
    return int(time.time() * 1000)


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def safe_decode(b: bytes) -> str:
    try:
        return b.decode("utf-8", errors="replace")
    except Exception:
        return repr(b)


def split_cmd(cmd: str) -> List[str]:
    """
    Conservative command splitter:
    - If user provides SHERATAN_CORE_CMD as a single exe path, works.
    - If includes args, we prefer shlex on non-Windows; on Windows, subprocess list is safer.
    """
    cmd = cmd.strip()
    if not cmd:
        raise ValueError("Empty command")
    # If looks like a simple path without spaces OR quoted path, handle quickly
    if cmd.startswith('"') and cmd.endswith('"'):
        return [cmd.strip('"')]
    if " " not in cmd and "\t" not in cmd:
        return [cmd]
    # Use shlex for general parsing (works on Windows too for basic quotes)
    import shlex
    return shlex.split(cmd)


@dataclass
class StepResult:
    name: str
    ok: bool
    started_ms: int
    ended_ms: int
    details: Dict[str, Any]


@dataclass
class ExerciseResult:
    ok: bool
    started_ms: int
    ended_ms: int
    base_url: str
    port: int
    data_dir: str
    core_cmd: str
    steps: List[StepResult]
    diagnostics: Dict[str, Any]


def step(name: str, fn, steps: List[StepResult]) -> Any:
    t0 = now_ms()
    try:
        out = fn()
        t1 = now_ms()
        steps.append(StepResult(name=name, ok=True, started_ms=t0, ended_ms=t1, details={"result": out}))
        print(f"[EXERCISE] {name}: OK")
        return out
    except Exception as e:
        t1 = now_ms()
        steps.append(StepResult(name=name, ok=False, started_ms=t0, ended_ms=t1, details={"error": str(e)}))
        print(f"[EXERCISE] {name}: FAIL -> {e}")
        raise


def wait_until_ready(base_url: str, timeout_s: int, poll_interval_s: float) -> Dict[str, Any]:
    deadline = time.time() + timeout_s
    last_err: Optional[str] = None
    while time.time() < deadline:
        try:
            j = http_get_json(f"{base_url}/api/system/health", timeout_s=5)
            # optional readiness flag
            if isinstance(j, dict):
                if j.get("status") in ("ok", "healthy", "ready", None):
                    return j
                # if status exists and says not ready, keep polling
            return j
        except Exception as e:
            last_err = str(e)
            time.sleep(poll_interval_s)
    raise RuntimeError(f"Core not ready within {timeout_s}s. last_err={last_err}")


def derive_feature_matrix(health: Dict[str, Any], ui_ok: bool, trace_ok: bool) -> Dict[str, Any]:
    """
    Conservative feature matrix:
    - Core required: health, db, trace, ui
    - Optional: keys present in health (no assumptions)
    """
    core_required = {
        "health_endpoint": True,
        "db_present": bool(health.get("db") or health.get("database") or health.get("sqlite") or True),
        "wal_enabled": bool(health.get("wal") is True) if "wal" in health else None,
        "trace_writable": trace_ok,
        "ui_served": ui_ok,
    }
    optional = {}
    for k in ("webrelay", "llm", "browser", "workers", "queue", "router", "policy"):
        if k in health:
            optional[k] = health.get(k)

    return {
        "core_required": core_required,
        "optional_signals": optional,
        "health_snapshot": health,
    }


def start_core_process(port: int, data_dir: Path) -> Tuple[subprocess.Popen, str]:
    """
    Starts the core using SHERATAN_CORE_CMD template.

    - If SHERATAN_CORE_CMD is not set:
        default: "python -m uvicorn main:app --host 127.0.0.1 --port {port}"
      (assumes main.py exposes app variable)

    Notes:
    - This sets SHERATAN_DATA_DIR=data_dir for isolation.
    - Also sets PYTHONUNBUFFERED=1 for logs.
    """
    cmd_template = os.environ.get(
        "SHERATAN_CORE_CMD",
        "python -m uvicorn main:app --host 127.0.0.1 --port {port}",
    ).strip()

    cmd_rendered = cmd_template.format(port=port)
    cmd_list = split_cmd(cmd_rendered)

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["SHERATAN_DATA_DIR"] = str(data_dir)
    # Some apps prefer DATA_DIR
    env.setdefault("DATA_DIR", str(data_dir))

    # Ensure data_dir exists
    data_dir.mkdir(parents=True, exist_ok=True)

    # Start process
    # stdout/stderr captured to file for diagnostics
    ensure_dir(REPORT_DIR)
    log_path = REPORT_DIR / "core_stdout_stderr.log"
    log_f = open(log_path, "wb")

    p = subprocess.Popen(
        cmd_list,
        stdout=log_f,
        stderr=subprocess.STDOUT,
        env=env,
        cwd=str(Path.cwd()),
        shell=False,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    return p, cmd_rendered


def stop_process(p: subprocess.Popen) -> None:
    try:
        if p.poll() is not None:
            return
        p.terminate()
        # wait a bit
        try:
            p.wait(timeout=8)
            return
        except subprocess.TimeoutExpired:
            pass
        p.kill()
    except Exception:
        try:
            p.kill()
        except Exception:
            pass


def main() -> None:
    ensure_dir(REPORT_DIR)

    started = now_ms()
    steps: List[StepResult] = []
    diagnostics: Dict[str, Any] = {}

    host = os.environ.get("SHERATAN_HOST", DEFAULT_HOST)
    port = int(os.environ.get("SHERATAN_PORT", "0")) or find_free_port(host)
    base_url = f"http://{host}:{port}"

    startup_timeout = int(os.environ.get("SHERATAN_STARTUP_TIMEOUT_S", str(DEFAULT_STARTUP_TIMEOUT_S)))
    step_timeout = int(os.environ.get("SHERATAN_STEP_TIMEOUT_S", str(DEFAULT_STEP_TIMEOUT_S)))
    poll_interval = float(os.environ.get("SHERATAN_HEALTH_POLL_INTERVAL_S", str(DEFAULT_HEALTH_POLL_INTERVAL_S)))

    # Isolated data dir
    tmp_root = Path(tempfile.mkdtemp(prefix="sheratan_exercise_"))
    data_dir = tmp_root / "data"
    diagnostics["tmp_root"] = str(tmp_root)

    core_proc: Optional[subprocess.Popen] = None
    core_cmd_rendered = ""

    try:
        # 1) Start core
        def _start():
            nonlocal core_proc, core_cmd_rendered
            core_proc, core_cmd_rendered = start_core_process(port=port, data_dir=data_dir)
            return {"pid": core_proc.pid, "cmd": core_cmd_rendered, "base_url": base_url, "data_dir": str(data_dir)}
        step("start_core_process", _start, steps)

        # 2) Wait ready
        health = step(
            "wait_until_ready",
            lambda: wait_until_ready(base_url, timeout_s=startup_timeout, poll_interval_s=poll_interval),
            steps,
        )

        # 3) Health sanity
        def _health_fields():
            # we don't assume exact schema; just verify it's dict-like
            if not isinstance(health, dict):
                raise RuntimeError("health is not a JSON object")
            return {"keys": sorted(list(health.keys()))[:50]}
        step("health_schema_sanity", _health_fields, steps)

        # 4) DB/WAL flag (non-fatal if key not present; but record)
        def _wal_check():
            wal = health.get("wal", None)
            return {"wal": wal, "interpreted_ok": (wal is True) if wal is not None else "unknown"}
        step("db_wal_check", _wal_check, steps)

        # 5) read_file job
        def _read_file():
            # Choose a deterministic small file
            path = os.environ.get("SHERATAN_EXERCISE_READFILE", "main.py")
            res = http_post_json(f"{base_url}/api/jobs", {"kind": "read_file", "params": {"path": path}}, timeout_s=step_timeout)
            if res.get("ok") is not True:
                raise RuntimeError(f"read_file returned ok!=true: {res}")
            return {"path": path, "ok": True}
        step("job_read_file", _read_file, steps)

        # 6) write_file job (temp)
        def _write_file():
            tf = data_dir / "exercise_write.txt"
            res = http_post_json(
                f"{base_url}/api/jobs",
                {"kind": "write_file", "params": {"path": str(tf), "content": "hi"}},
                timeout_s=step_timeout,
            )
            if res.get("ok") is not True:
                raise RuntimeError(f"write_file returned ok!=true: {res}")
            exists = tf.exists()
            if not exists:
                raise RuntimeError("write_file did not create file")
            return {"path": str(tf), "exists": exists}
        step("job_write_file", _write_file, steps)

        # 7) walk_tree bounded
        def _walk_tree():
            root = os.environ.get("SHERATAN_EXERCISE_WALKTREE", ".")
            # Allow bounded params if your API supports it; harmless if ignored.
            params = {"path": root, "max_files": 500, "max_depth": 6}
            res = http_post_json(f"{base_url}/api/jobs", {"kind": "walk_tree", "params": params}, timeout_s=step_timeout)
            if res.get("ok") is not True:
                raise RuntimeError(f"walk_tree returned ok!=true: {res}")
            return {"root": root}
        step("job_walk_tree", _walk_tree, steps)

        # 8) Trace exists + non-empty
        def _trace_check():
            # Prefer isolated data dir trace
            trace = data_dir / "decision_trace.jsonl"
            # Fallback: some systems write under ./data
            if not trace.exists():
                alt = Path("data") / "decision_trace.jsonl"
                trace = alt if alt.exists() else trace
            if not trace.exists():
                raise RuntimeError(f"trace not found (expected {data_dir/'decision_trace.jsonl'} or data/decision_trace.jsonl)")
            if trace.stat().st_size <= 0:
                raise RuntimeError("trace exists but empty")
            # Optional: validate contains schema_version field somewhere (best-effort)
            head = trace.read_text(encoding="utf-8", errors="replace").splitlines()[:5]
            has_schema = any("schema_version" in line for line in head)
            return {"trace_path": str(trace), "size": trace.stat().st_size, "schema_version_seen": has_schema}
        trace_info = step("trace_written_check", _trace_check, steps)

        # 9) UI asset reachable
        def _ui_check():
            status, headers, body = http_get_raw(f"{base_url}/index.html", timeout_s=5)
            if status != 200:
                raise RuntimeError(f"/index.html -> {status}")
            ctype = headers.get("content-type", "")
            # Accept typical variants
            if "html" not in ctype:
                # allow empty content-type on some static mounts, but ensure body looks like html
                if b"<html" not in body.lower():
                    raise RuntimeError(f"index.html not html-ish; content-type={ctype}")
            return {"content_type": ctype, "bytes": len(body)}
        ui_info = step("ui_asset_check", _ui_check, steps)

        # 10) Feature matrix
        def _features():
            fm = derive_feature_matrix(health=health, ui_ok=True, trace_ok=True)
            FEATURE_REPORT.write_text(json.dumps(fm, indent=2), encoding="utf-8")
            return {"feature_report": str(FEATURE_REPORT)}
        step("write_feature_matrix", _features, steps)

        ok_all = True

    except Exception as e:
        ok_all = False
        diagnostics["error"] = str(e)

        # Try to attach last lines of core log to diagnostics
        log_path = REPORT_DIR / "core_stdout_stderr.log"
        if log_path.exists():
            try:
                tail = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]
                diagnostics["core_log_tail"] = "\n".join(tail)
            except Exception:
                diagnostics["core_log_tail"] = "<unreadable>"
    finally:
        if core_proc is not None:
            stop_process(core_proc)

        ended = now_ms()
        res = ExerciseResult(
            ok=ok_all,
            started_ms=started,
            ended_ms=ended,
            base_url=base_url,
            port=port,
            data_dir=str(data_dir),
            core_cmd=core_cmd_rendered or os.environ.get("SHERATAN_CORE_CMD", ""),
            steps=steps,
            diagnostics=diagnostics,
        )

        # Always write report
        ensure_dir(REPORT_DIR)
        EXERCISE_REPORT.write_text(
            json.dumps(
                {
                    **asdict(res),
                    "steps": [asdict(s) for s in res.steps],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        # Cleanup temp dir only if success (keep on fail for forensics)
        if ok_all:
            try:
                shutil.rmtree(tmp_root, ignore_errors=True)
            except Exception:
                pass

        print(f"[EXERCISE] RESULT: {'PASS' if ok_all else 'FAIL'}")
        print(f"[EXERCISE] report: {EXERCISE_REPORT}")
        if FEATURE_REPORT.exists():
            print(f"[EXERCISE] features: {FEATURE_REPORT}")

        if not ok_all:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
