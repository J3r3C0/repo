#!/usr/bin/env python
"""Sheratan Schema Linter

Validates job/result JSON files against the canonical envelope schemas.

- Primary: JSON Schema validation using `jsonschema` if available.
- Fallback: structural validation (required keys + types) if `jsonschema` isn't installed.

Usage:
  python tools/schema_linter.py --path relay_requests --path relay_responses --path jobs --report build/reports/schema_lint_report.json

Exit codes:
  0 = no errors (warnings allowed)
  1 = errors found
  2 = linter internal failure
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Finding:
    severity: str  # ERROR|WARN|INFO
    file: str
    message: str
    code: str


def _load_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8", errors="replace"))


def _try_import_jsonschema():
    try:
        import jsonschema  # type: ignore

        return jsonschema
    except Exception:
        return None


def _schema_paths(repo_root: Path) -> Tuple[Path, Path]:
    sj = repo_root / "schemas" / "job_envelope_v1.json"
    sr = repo_root / "schemas" / "result_envelope_v1.json"
    return sj, sr


def _detect_kind(obj: Any) -> str:
    if not isinstance(obj, dict):
        return "unknown"
    sv = obj.get("schema_version")
    if sv == "job_envelope_v1":
        return "job_envelope_v1"
    if sv == "result_envelope_v1":
        return "result_envelope_v1"
    # legacy heuristics
    if "ok" in obj and ("result" in obj or "error" in obj) and "job_id" in obj:
        return "legacy_result"
    if "job_id" in obj and ("kind" in obj or "payload" in obj or "action" in obj):
        return "legacy_job"
    return "unknown"


def _fallback_validate_job(obj: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    # minimal required keys for job_envelope_v1
    if obj.get("schema_version") != "job_envelope_v1":
        errs.append("schema_version != job_envelope_v1")
    for k in ["job_id", "intent", "action", "provenance", "policy_context"]:
        if k not in obj:
            errs.append(f"missing required key: {k}")
    action = obj.get("action")
    if not isinstance(action, dict):
        errs.append("action must be object")
    else:
        if "kind" not in action:
            errs.append("action.kind missing")
        if "params" in action and not isinstance(action.get("params"), dict):
            errs.append("action.params must be object")
    prov = obj.get("provenance")
    if not isinstance(prov, dict):
        errs.append("provenance must be object")
    else:
        if "source_zone" not in prov:
            errs.append("provenance.source_zone missing")
    return errs


def _fallback_validate_result(obj: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    if obj.get("schema_version") != "result_envelope_v1":
        errs.append("schema_version != result_envelope_v1")
    for k in ["job_id", "ok", "status", "timing"]:
        if k not in obj:
            errs.append(f"missing required key: {k}")
    if not isinstance(obj.get("timing"), dict):
        errs.append("timing must be object")
    if "result" in obj and obj["result"] is not None and not isinstance(obj["result"], dict):
        errs.append("result must be object")
    if "error" in obj and obj["error"] is not None and not isinstance(obj["error"], dict):
        errs.append("error must be object")
    return errs


def _jsonschema_validate(jsonschema_mod, schema: Dict[str, Any], instance: Any) -> List[str]:
    try:
        jsonschema_mod.validate(instance=instance, schema=schema)
        return []
    except Exception as e:
        return [str(e)]


def _iter_json_files(paths: List[Path]) -> List[Path]:
    out: List[Path] = []
    for base in paths:
        if base.is_file() and base.suffix.lower() == ".json":
            out.append(base)
        elif base.is_dir():
            out.extend([p for p in base.rglob("*.json") if p.is_file()])
    # stable order
    return sorted(set(out))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", action="append", default=[], help="File or directory to scan (repeatable)")
    ap.add_argument("--repo-root", default=".", help="Repo root (default: .)")
    ap.add_argument("--report", default="build/reports/schema_lint_report.json", help="Where to write report")
    ap.add_argument("--fail-on-warn", action="store_true", help="Exit nonzero if warnings exist")
    ap.add_argument("--max-findings", type=int, default=5000)

    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    scan_paths = [Path(p).resolve() for p in args.path] if args.path else [repo_root / "relay_requests", repo_root / "relay_responses", repo_root / "jobs"]

    files = _iter_json_files([p for p in scan_paths if p.exists()])

    jsonschema_mod = _try_import_jsonschema()
    sj_path, sr_path = _schema_paths(repo_root)

    schema_job: Optional[Dict[str, Any]] = None
    schema_res: Optional[Dict[str, Any]] = None
    if sj_path.exists() and sr_path.exists():
        try:
            schema_job = _load_json(sj_path)
            schema_res = _load_json(sr_path)
        except Exception:
            # schemas missing or invalid - will fallback
            schema_job = None
            schema_res = None

    findings: List[Finding] = []
    counts = {"scanned": 0, "job_envelope_v1": 0, "result_envelope_v1": 0, "legacy_job": 0, "legacy_result": 0, "unknown": 0}

    for fp in files:
        counts["scanned"] += 1
        rel = str(fp.relative_to(repo_root)) if fp.is_relative_to(repo_root) else str(fp)
        try:
            obj = _load_json(fp)
        except Exception as e:
            findings.append(Finding("ERROR", rel, f"Invalid JSON: {e}", "E_JSON_PARSE"))
            continue

        kind = _detect_kind(obj)
        counts[kind] = counts.get(kind, 0) + 1

        if kind == "job_envelope_v1":
            if jsonschema_mod and schema_job is not None:
                errs = _jsonschema_validate(jsonschema_mod, schema_job, obj)
            else:
                errs = _fallback_validate_job(obj)
            for msg in errs:
                findings.append(Finding("ERROR", rel, msg, "E_JOB_SCHEMA"))

        elif kind == "result_envelope_v1":
            if jsonschema_mod and schema_res is not None:
                errs = _jsonschema_validate(jsonschema_mod, schema_res, obj)
            else:
                errs = _fallback_validate_result(obj)
            for msg in errs:
                findings.append(Finding("ERROR", rel, msg, "E_RESULT_SCHEMA"))

        elif kind in ("legacy_job", "legacy_result"):
            findings.append(
                Finding(
                    "WARN",
                    rel,
                    f"Legacy format detected ({kind}). Recommend upgrading to job_envelope_v1/result_envelope_v1.",
                    "W_LEGACY_FORMAT",
                )
            )
        else:
            findings.append(Finding("WARN", rel, "Unknown JSON shape (not a job/result envelope).", "W_UNKNOWN_JSON"))

        if len(findings) >= args.max_findings:
            findings.append(Finding("WARN", "*", f"Findings truncated at max_findings={args.max_findings}", "W_TRUNCATED"))
            break

    # Summaries
    errors = [f for f in findings if f.severity == "ERROR"]
    warns = [f for f in findings if f.severity == "WARN"]

    report_path = (repo_root / args.report).resolve() if not os.path.isabs(args.report) else Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "schema_version": "schema_lint_report_v1",
        "repo_root": str(repo_root),
        "scan_paths": [str(p) for p in scan_paths],
        "counts": counts,
        "summary": {
            "errors": len(errors),
            "warnings": len(warns),
            "ok": len(errors) == 0 and (not args.fail_on_warn or len(warns) == 0),
            "jsonschema_available": bool(jsonschema_mod),
        },
        "findings": [f.__dict__ for f in findings],
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # Console output
    print("[SCHEMA_LINTER] scanned:", counts["scanned"], "errors:", len(errors), "warnings:", len(warns))
    print("[SCHEMA_LINTER] report:", str(report_path))

    if errors:
        return 1
    if args.fail_on_warn and warns:
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print("[SCHEMA_LINTER] INTERNAL ERROR:", e)
        raise SystemExit(2)
