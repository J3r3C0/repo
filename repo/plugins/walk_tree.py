# repo/plugins/walk_tree.py
import os
from pathlib import Path

def handle(params: dict) -> dict:
    path = params.get("path", ".")
    p = Path(path)
    if not p.is_dir():
        return {"ok": False, "error": "Not a directory"}
    
    files = []
    for root, dirs, filenames in os.walk(p):
        for f in filenames:
            files.append(os.path.relpath(os.path.join(root, f), p))
    return {"ok": True, "files": files[:100]} # Limit to 100 for exercise
