import traceback
import sys
import os

sys.path.insert(0, os.getcwd())

try:
    print("Pre-import Core modules:", [m for m in sys.modules if m.startswith('core')])
    import core
    print("Core file:", core.__file__)
    print("Core dir contents:", dir(core))
    
    print("\nTesting 'from hub import main'...")
    from hub import main
    print("SUCCESS: Hub Import OK")
except Exception:
    print("\n--- TRACEBACK START ---")
    traceback.print_exc()
    print("--- TRACEBACK END ---\n")
    print("\nPost-import sys.modules for 'core':", [m for m in sys.modules if m.startswith('core')])
