# repo/tools/verify_import_referential_integrity.py
import ast
import os
import sys
from pathlib import Path

def get_imports(file_path):
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content)
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.append(n.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports

def check_path_exists(parts, repo_root):
    # Try to resolve a list of package parts [core, utils, atomic_io] 
    # as a file in repo/
    # If first part is 'repo', skip it
    if parts[0] == "repo":
        parts = parts[1:]
    
    current = repo_root
    for i, p in enumerate(parts):
        # Could be a file or a directory
        potential_file = current / f"{p}.py"
        potential_dir = current / p
        
        if potential_file.exists():
            return True, None
        if potential_dir.exists():
            current = potential_dir
            continue
        
        # If we are at the last part, maybe it's a member of an __init__.py
        if i == len(parts) - 1 and (current / "__init__.py").exists():
            return True, None
            
        return False, f"Missing {p} in path {current}"
    return True, None

def main():
    repo_root = Path("repo")
    core_dir = repo_root / "core"
    plugins_dir = repo_root / "plugins"
    mesh_dir = repo_root / "mesh"
    
    # Internal packages we care about
    INTERNAL_PKGS = ["core", "plugins", "mesh", "schemas"]
    
    broken = []
    
    # Scan all py files in repo/core and repo/plugins
    for f in repo_root.rglob("*.py"):
        # Skip pycache and tools
        if "__pycache__" in str(f) or "tools" in str(f):
             continue
        
        module_imports = get_imports(f)
        for imp in module_imports:
            parts = imp.split('.')
            if parts[0] in INTERNAL_PKGS or (parts[0] == "repo" and len(parts) > 1 and parts[1] in INTERNAL_PKGS):
                exists, reason = check_path_exists(parts, repo_root)
                if not exists:
                    # Special check: is it in the ROOT but not in REPO?
                    root_check_parts = parts[1:] if parts[0] == "repo" else parts
                    root_path = Path(".")
                    root_exists = False
                    for p in root_check_parts:
                        if (root_path / f"{p}.py").exists() or (root_path / p).exists():
                            root_path = root_path / p
                            root_exists = True
                        else:
                            root_exists = False
                            break
                    
                    if root_exists:
                         broken.append((str(f.relative_to(repo_root)), imp, "Referencing ROOT instead of REPO (Ballast Dependency)"))
                    else:
                         broken.append((str(f.relative_to(repo_root)), imp, f"Dangling reference: {reason}"))

    if broken:
        print("[STATIC_INTEGRITY] FAIL: Found broken or dangling internal imports!")
        for src, imp, reason in broken:
            print(f"  - {src}: '{imp}' -> {reason}")
        sys.exit(1)
    else:
        print("[STATIC_INTEGRITY] PASS: All internal references in synthesized modules are resolvable within 'repo/'.")

if __name__ == "__main__":
    main()
