from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable


FORBIDDEN_IMPORTS = [
    ("core.engine", "core.observability"),
    ("core.engine", "core.observability.decision_trace"),
    ("core", "hub"),
    ("core", "decision"),
]


def _module_of_file(py_file: Path, repo_root: Path) -> str:
    rel = py_file.relative_to(repo_root).with_suffix("")
    return ".".join(rel.parts)


def _iter_py_files(root: Path) -> Iterable[Path]:
    yield from root.rglob("*.py")


def check_import_directions(repo_root: Path) -> list[str]:
    errors: list[str] = []
    for py in _iter_py_files(repo_root / "core"):
        mod = _module_of_file(py, repo_root)

        try:
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        except Exception as e:
            errors.append(f"Failed to parse {py}: {e}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    for src, forbidden in FORBIDDEN_IMPORTS:
                        if mod.startswith(src) and name.startswith(forbidden):
                            errors.append(f"{py}: forbidden import '{name}' from module '{mod}'")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    name = node.module
                    for src, forbidden in FORBIDDEN_IMPORTS:
                        if mod.startswith(src) and name.startswith(forbidden):
                            errors.append(f"{py}: forbidden from-import '{name}' from module '{mod}'")
    return errors

if __name__ == "__main__":
    import sys
    root = Path(__file__).resolve().parents[1]
    errs = check_import_directions(root)
    if errs:
        for e in errs:
            print(f" - {e}")
        sys.exit(1)
    print("Import guard: OK")
    sys.exit(0)
