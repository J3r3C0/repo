# repo/tools/fix_soul_imports.py
import os
from pathlib import Path

MAPPINGS = {
    "core.storage": "core.store",
    "core.decision_trace": "core.trace",
    "core.state_machine": "core.policy",
    "core.policy_engine": "core.policy",
    "core.why_reader": "core.why",
    "core.why_api": "core.why",
    "from core import storage": "from core import store as storage",
    "import storage": "from core import store as storage"
}

def main():
    repo_core = Path("repo/core")
    
    for f in repo_core.glob("*.py"):
        content = f.read_text(encoding="utf-8")
        original = content
        
        for old, new in MAPPINGS.items():
            content = content.replace(old, new)
            
        if content != original:
            print(f"Fixed imports in {f.name}")
            f.write_text(content, encoding="utf-8")

if __name__ == "__main__":
    main()
