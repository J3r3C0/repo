# repo/plugins/write_file.py
from pathlib import Path

def handle(params: dict) -> dict:
    path = params.get("path")
    content = params.get("content", "")
    if not path:
        return {"ok": False, "error": "Missing path"}
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(p)}
