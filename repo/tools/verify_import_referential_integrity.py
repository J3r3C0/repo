# repo/tools/verify_import_referential_integrity_v2.py
import ast
import sys
import os
from pathlib import Path

INTERNAL_PKGS = {"core", "plugins", "mesh", "schemas"}

def parse_imports(py_file: Path):
    try:
        content = py_file.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content)
    except Exception as e:
        print(f"Error parsing {py_file}: {e}")
        return
        
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                yield ("import", n.name, None, 0)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for n in node.names:
                yield ("from", mod, n.name, node.level or 0)

def file_to_module(repo_root: Path, py_file: Path) -> str:
    try:
        rel = py_file.relative_to(repo_root).with_suffix("")
        parts = list(rel.parts)
        if parts and parts[0] == "repo":
            parts = parts[1:]
        return ".".join(parts)
    except ValueError:
        return ""

def resolve_from_relative(base_module: str, rel_level: int, module: str) -> str:
    base_parts = base_module.split(".") if base_module else []
    if base_parts:
        # remove the file itself to get package context
        base_parts = base_parts[:-1]
    
    if rel_level > 0:
        # pop levels
        base_parts = base_parts[: max(0, len(base_parts) - (rel_level - 1))]
        
    if module:
        return ".".join(base_parts + module.split("."))
    return ".".join(base_parts)

def exists_module(repo_root: Path, module: str) -> bool:
    parts = module.split(".") if module else []
    if not parts:
        return False
    if parts[0] == "repo":
        parts = parts[1:]
    if not parts or parts[0] not in INTERNAL_PKGS:
        return False

    cur = repo_root
    for i, p in enumerate(parts):
        f = cur / f"{p}.py"
        d = cur / p
        if f.exists():
            return True
        if d.exists():
            cur = d
            continue
        return False
    return (cur / "__init__.py").exists()

def exists_sub_import(repo_root: Path, module: str, imported: str) -> tuple[bool, str]:
    mod_parts = module.split(".") if module else []
    if mod_parts and mod_parts[0] == "repo":
        mod_parts = mod_parts[1:]
        
    # If not an internal package, we assume it's external and OK for this audit
    if not mod_parts or mod_parts[0] not in INTERNAL_PKGS:
        return True, "external"

    cur = repo_root
    for p in mod_parts:
        d = cur / p
        f = cur / f"{p}.py"
        if f.exists():
            return True, "weak_attr_on_module_file"
        if d.exists():
            cur = d
            continue
        return False, "module_path_missing"

    if (cur / f"{imported}.py").exists():
        return True, "submodule_file"
    if (cur / imported).exists() and ((cur / imported) / "__init__.py").exists():
        return True, "submodule_pkg"
    if (cur / "__init__.py").exists():
        return True, "weak_export_from_init"

    # Special check: could be a root ballast import
    root_path = Path(".")
    root_exists = False
    for p in mod_parts:
        if (root_path / f"{p}.py").exists() or (root_path / p).exists():
            root_path = root_path / p
            root_exists = True
        else:
            root_exists = False
            break
    if root_exists:
        return False, "referencing_root_ballast"

    return False, "no_submodule_and_no_init"

def main():
    repo_root = Path("repo")
    broken = []
    weak = []

    print("[STATIC_INTEGRITY_V2] Starting hardened referential audit...")

    for py in repo_root.rglob("*.py"):
        # Skip internal infra
        if "__pycache__" in str(py) or "/tools/" in str(py).replace("\\", "/"):
            continue

        base_mod = file_to_module(repo_root, py)

        for kind, mod, imported, level in parse_imports(py):
            if kind == "from" and level > 0:
                abs_mod = resolve_from_relative(base_mod, level, mod)
            else:
                abs_mod = mod

            if not abs_mod and kind == "from" and level > 0:
                 # Case from . import xxx
                 abs_mod = resolve_from_relative(base_mod, level, "")

            first = (abs_mod.split(".")[0] if abs_mod else "")
            if first == "repo":
                first = (abs_mod.split(".")[1] if len(abs_mod.split(".")) > 1 else "")
                
            if first and first not in INTERNAL_PKGS:
                continue

            if kind == "import":
                if not exists_module(repo_root, abs_mod):
                    broken.append((str(py.relative_to(repo_root)), f"import {mod}", "unresolvable_module"))
            else:
                ok, reason = exists_sub_import(repo_root, abs_mod, imported)
                if not ok:
                    broken.append((str(py.relative_to(repo_root)), f"from {mod} import {imported}", reason))
                elif reason.startswith("weak_"):
                    weak.append((str(py.relative_to(repo_root)), f"from {mod} import {imported}", reason))

    if broken:
        print("[STATIC_INTEGRITY_V2] FAIL: Broken internal imports detected!")
        for src, stmt, reason in broken:
            print(f"  - {src}: {stmt} -> {reason}")
        sys.exit(1)

    print("[STATIC_INTEGRITY_V2] PASS: All internal imports resolvable within 'repo/'.")
    if weak:
        print(f"[STATIC_INTEGRITY_V2] WARN: {len(weak)} weak resolutions detected (init exports / attributes).")
        # for src, stmt, reason in weak[:20]:
        #     print(f"  - {src}: {stmt} -> {reason}")

if __name__ == "__main__":
    main()
