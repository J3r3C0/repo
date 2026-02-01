import os
import shutil
from pathlib import Path

files_to_move = [
    "governance.py", "ledger_journal.py", "performance_baseline.py", 
    "replay_engine.py", "result_integrity.py", "result_ref.py", 
    "scoring.py", "sdk_client.py", "why_reader.py", "journal_cli.py"
]

repo_root = Path(os.getcwd())
core_dir = repo_root / "core"
hub_dir = repo_root / "hub"

hub_dir.mkdir(exist_ok=True)

for f in files_to_move:
    src = core_dir / f
    dst = hub_dir / f
    if src.exists():
        print(f"Moving {f} to hub/")
        shutil.move(str(src), str(dst))
    else:
        print(f"Skipping {f}, not found in core/")
