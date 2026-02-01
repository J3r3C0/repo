# repo/tools/import_trace.py
import atexit
import os
import sys
import time
from pathlib import Path

DEFAULT_OUT = Path("build/reports/imports_used.txt")

def install_import_tracer(out_path: str = str(DEFAULT_OUT)) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    start = time.time()

    def _write_report() -> None:
        mods = sorted(m for m in sys.modules.keys() if m and not m.startswith("_"))
        dur_ms = int((time.time() - start) * 1000)

        lines = [
            "# sheratan import trace (observed)",
            f"# python: {sys.version.replace(os.linesep,' ')}",
            f"# runtime_ms: {dur_ms}",
            f"# modules_count: {len(mods)}",
            "",
            *mods,
            "",
        ]
        out.write_text("\n".join(lines), encoding="utf-8")

    import threading

    def _periodic_write() -> None:
        while True:
            _write_report()
            time.sleep(5)

    t = threading.Thread(target=_periodic_write, daemon=True)
    t.start()
    atexit.register(_write_report)
