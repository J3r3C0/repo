#!/usr/bin/env python3
# tools/verify_phase1.py
"""
Phase-1/Perception-Core Purity Verifier

Goal:
- core/ is deterministic perception kernel: no agentic logic, no orchestration, no hub imports.
- enforce strict boundaries by static scanning (AST + regex) with clear fail messages.

Usage:
  python -m tools.verify_phase1
Exit codes:
  0 OK
  2 Violations found
"""

from __future__ import annotations

import ast
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_DIR = REPO_ROOT / "core"

# ----------------------------
# Configuration (tight by default)
# ----------------------------

# 1) Forbidden substrings/keywords in core/ (case-insensitive)
FORBIDDEN_KEYWORDS = [
    # agentic / planning / orchestration
    r"\bmcts\b",
    r"\borchestrator\b",
    r"\brecommend_action\b",
    r"\baction_selection\b",
    r"\bplan\b",                 # optional: tighten if it false-positives too often
    r"\bdispatch\b",
    r"\bdispatcher\b",
    r"\bscheduler\b",
    r"\bmission\b",
    r"\btask\b",
    r"\bjob\b",
    r"\bwebrelay\b",
    r"\bmesh\b",
    r"\bbroker\b",
    r"\bregistry\b",
    r"\bgateway\b",
    r"\bpolicy_enforce\b",
    r"\benforce_policy\b",
    r"\brate_limit\b",
    r"\bquota\b",
    # network/UI
    # r"\bfastapi\b",              # Disabled by default as Core uses FastAPI for endpoints
    # r"\buvicorn\b",
    r"\breact\b",
    r"\bdashboard\b",
]

# 2) Forbidden stdlib modules in core/ for determinism
FORBIDDEN_MODULES = {
    "time",          # disallow time.time(), etc.
    "random",        # disallow random.* (unless you inject deterministic RNG explicitly)
}

# 3) Forbidden import prefixes (core must never import these)
FORBIDDEN_IMPORT_PREFIXES = (
    "hub",
    "mesh",
    "dashboard",
    "ui",
)

# 4) Allowed import prefixes for core/
ALLOWED_THIRD_PARTY = {
    "numpy",
    "pydantic",
    "cupy",
    "scipy",
    "fastapi",
    "uvicorn",
    "starlette",
}

# 5) Files to ignore (generated, vendored, etc.)
IGNORE_GLOBS = [
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    "**/*.pyc",
]

ALLOW_CLOCK_MODULE = False

# ----------------------------
# Helpers
# ----------------------------

@dataclass
class Violation:
    path: Path
    line: int
    kind: str
    detail: str

def iter_python_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*.py"):
        s = str(p)
        if any(Path(s).match(glob) for glob in IGNORE_GLOBS):
            continue
        yield p

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")

def module_name_from_import(node: ast.AST) -> list[str]:
    mods: list[str] = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            mods.append(alias.name)
    elif isinstance(node, ast.ImportFrom):
        if node.module:
            mods.append(node.module)
    return mods

def is_third_party(mod: str) -> bool:
    top = mod.split(".", 1)[0]
    if top == "core":
        return False
    if top in FORBIDDEN_IMPORT_PREFIXES:
        return False
    return top in ALLOWED_THIRD_PARTY

def main() -> int:
    if not CORE_DIR.exists():
        print(f"[verify_phase1] ERROR: core/ not found at {CORE_DIR}")
        return 2

    violations: list[Violation] = []
    keyword_regexes = [re.compile(pat, re.IGNORECASE) for pat in FORBIDDEN_KEYWORDS]

    for pyfile in iter_python_files(CORE_DIR):
        txt = read_text(pyfile)

        # A) Keyword scan
        for rx in keyword_regexes:
            m = rx.search(txt)
            if m:
                line = txt[: m.start()].count("\n") + 1
                violations.append(
                    Violation(pyfile, line, "FORBIDDEN_KEYWORD", f"Matched: {rx.pattern}")
                )

        # B) AST import scan
        try:
            tree = ast.parse(txt, filename=str(pyfile))
        except SyntaxError as e:
            violations.append(Violation(pyfile, getattr(e, "lineno", 1) or 1, "SYNTAX_ERROR", str(e)))
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mods = module_name_from_import(node)
                for mod in mods:
                    top = mod.split(".", 1)[0]

                    if top in FORBIDDEN_IMPORT_PREFIXES:
                        violations.append(
                            Violation(pyfile, getattr(node, "lineno", 1) or 1, "FORBIDDEN_IMPORT",
                                      f"core imports forbidden prefix '{top}' via '{mod}'")
                        )

                    if top in FORBIDDEN_MODULES:
                        if ALLOW_CLOCK_MODULE and top == "time" and pyfile.name == "clock.py":
                            continue
                        violations.append(
                            Violation(pyfile, getattr(node, "lineno", 1) or 1, "FORBIDDEN_MODULE",
                                      f"core imports '{top}' (determinism violation)")
                        )

    # C) Function-call scan for time.time()/random.*
    call_bans = [
        (r"\btime\.time\s*\(", "CALL_TIME_TIME"),
        (r"\brandom\.", "CALL_RANDOM"),
    ]
    for pat, kind in call_bans:
        for pyfile in iter_python_files(CORE_DIR):
             txt = read_text(pyfile)
             m = re.search(pat, txt)
             if m:
                 line = txt[: m.start()].count("\n") + 1
                 violations.append(Violation(pyfile, line, kind, f"Matched: {pat}"))

    # D) Structural check
    banned_filenames = {"orchestrator.py", "dispatcher.py", "mcts_light.py"}
    for fname in banned_filenames:
        p = CORE_DIR / fname
        if p.exists():
            violations.append(Violation(p, 1, "FORBIDDEN_FILE", f"Remove '{fname}' from core/"))

    if violations:
        print("[verify_phase1] FAIL: violations found\n")
        # Deduplicate and sort
        seen = set()
        unique_violations = []
        for v in violations:
            key = (str(v.path), v.line, v.kind)
            if key not in seen:
                seen.add(key)
                unique_violations.append(v)
        
        for v in sorted(unique_violations, key=lambda x: (str(x.path), x.line, x.kind)):
            try:
                rel = v.path.relative_to(REPO_ROOT)
            except ValueError:
                rel = v.path
            print(f"- {rel}:{v.line} [{v.kind}] {v.detail}")
        print("\n[verify_phase1] Hint: Move agent/orchestration logic to hub/. Core must stay perception-only.")
        return 2

    print("[verify_phase1] PASS: core purity ok")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

