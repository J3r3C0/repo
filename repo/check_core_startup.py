"""
Quick Core Startup Diagnostic
Checks all imports and dependencies before starting Core
"""
import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

print("[DIAGNOSTIC] Checking Core startup dependencies...")
print(f"[DIAGNOSTIC] PYTHONPATH: {repo_root}")
print()

errors = []
warnings = []

# Test critical imports
critical_imports = [
    ("core.config", "BASE_DIR"),
    ("core.database", "init_db"),
    ("core.models", None),
    ("core.storage", None),
    ("core.why_api", "router"),
    ("core.gateway_middleware", "enforce_gateway"),
    ("core.metrics_client", "record_module_call"),
    ("core.health", "health_manager"),
]

print("[1/3] Testing critical imports...")
for module_name, attr in critical_imports:
    try:
        module = __import__(module_name, fromlist=[attr] if attr else [])
        if attr and not hasattr(module, attr):
            errors.append(f"  ✗ {module_name}.{attr} not found")
        else:
            print(f"  ✓ {module_name}" + (f".{attr}" if attr else ""))
    except Exception as e:
        errors.append(f"  ✗ {module_name}: {e}")

print()
print("[2/3] Checking required directories...")
required_dirs = ["runtime", "logs", "data", "config"]
for dirname in required_dirs:
    dirpath = repo_root / dirname
    if dirpath.exists():
        print(f"  ✓ {dirname}/")
    else:
        warnings.append(f"  ! {dirname}/ missing (will be created)")
        dirpath.mkdir(parents=True, exist_ok=True)
        print(f"  + Created {dirname}/")

print()
print("[3/3] Checking database...")
try:
    from core.database import init_db, get_db
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"  ✓ Database OK ({len(tables)} tables)")
except Exception as e:
    errors.append(f"  ✗ Database error: {e}")

print()
print("=" * 60)
if errors:
    print(f"[FAILED] {len(errors)} error(s) found:")
    for err in errors:
        print(err)
    sys.exit(1)
elif warnings:
    print(f"[WARNING] {len(warnings)} warning(s):")
    for warn in warnings:
        print(warn)
    print()
    print("[READY] Core can start (with warnings)")
    sys.exit(0)
else:
    print("[SUCCESS] All checks passed - Core ready to start!")
    sys.exit(0)
