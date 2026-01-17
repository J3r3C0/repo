# repo/core/config.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def get_resource_path(relative_path: str = "") -> Path:
    """Robust path resolution for both dev and frozen (PyInstaller) states."""
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        # Assuming we are in repo/core/
        base_path = Path(__file__).parent.parent
    return (base_path / relative_path).resolve()

BASE_DIR = get_resource_path("")

# Persistent Data Management
DATA_DIR = Path(os.getenv("SHERATAN_DATA_DIR", "data")).resolve()
if getattr(sys, 'frozen', False):
    # In production, default next to EXE unless env is set
    DATA_DIR = Path(os.getenv("SHERATAN_DATA_DIR", str(Path(sys.executable).parent / "data"))).resolve()

DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "sheratan.db"

# Core Start Time
import time
CORE_START_TIME = time.time()
