from pathlib import Path
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Base directory for read-only resources (works for dev and PyInstaller)
def get_resource_path(relative_path: str = "") -> Path:
    try:
        import sys
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(__file__).parent.parent
    return (base_path / relative_path).resolve()

BASE_DIR = get_resource_path("")

# Persistent Data directory (lives next to EXE in production)
if getattr(sys, 'frozen', False):
    PERSISTENT_ROOT = Path(sys.executable).parent
else:
    PERSISTENT_ROOT = Path(__file__).parent.parent

DATA_DIR = PERSISTENT_ROOT / "data"
DB_PATH = DATA_DIR / "sheratan.db"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

def _f(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))

def _i(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))

class PortsConfig:
    """Core Perception Ports."""
    CORE_API = _i("SHERATAN_CORE_PORT", 8001)


