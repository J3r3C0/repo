# repo/tools/size_report.py
import json
import os
from pathlib import Path
from time import time

DEFAULT_DIST = Path("dist/sheratan_core")
OUT = Path("build/reports/size_report.json")

def dir_stats(root: Path) -> dict:
    total = 0
    files = 0
    biggest = []  # (size, relpath)

    for p in root.rglob("*"):
        if p.is_file():
            try:
                s = p.stat().st_size
            except OSError:
                continue
            total += s
            files += 1
            rel = str(p.relative_to(root)).replace("\\", "/")
            biggest.append((s, rel))

    biggest.sort(reverse=True)
    top = [{"bytes": s, "path": rel} for s, rel in biggest[:30]]

    return {
        "root": str(root).replace("\\", "/"),
        "bytes_total": total,
        "files_total": files,
        "top_30_files": top,
    }

def main():
    dist = Path(os.environ.get("SHERATAN_DIST", str(DEFAULT_DIST)))
    t0 = time()
    report = {
        "generated_at_unix": int(time()),
        "elapsed_ms": int((time() - t0) * 1000),
        "stats": dir_stats(dist),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[SIZE] wrote {OUT}")

if __name__ == "__main__":
    main()
