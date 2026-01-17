# repo/plugins/read_file.py
from pathlib import Path

def handle(params: dict) -> dict:
    path = params.get("path")
    if not path:
        return {"ok": False, "error": "Missing path"}
    p = Path(path)
    if not p.exists():
        return {"ok": False, "error": "File not found"}
    return {"ok": True, "content": p.read_text(encoding="utf-8", errors="replace")}
