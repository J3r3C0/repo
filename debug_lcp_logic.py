
import sys
import os
import json
from typing import Any, Dict, List

# Add current dir to path
sys.path.append(os.getcwd())

from core.lcp_actions import is_lcp_message, parse_lcp, normalize_job_specs

def test_lcp():
    result = {
        "ok": True,
        "action": "create_followup_jobs",
        "commentary": "Es wird ein Job geplant, der rekursiv alle Python-Dateien im core-Verzeichnis sucht.",
        "new_jobs": [
            {
                "name": "discover_core_py_files",
                "kind": "walk_tree",
                "params": {"root": "/workspace/project/core", "pattern": "*.py"},
                "auto_dispatch": True
            }
        ]
    }
    
    print(f"Is LCP? {is_lcp_message(result)}")
    
    followup, final = parse_lcp(result, default_chain_id="test_job_id")
    
    if followup:
        print(f"Followup detected! Chain ID: {followup.chain_id}")
        print(f"Jobs: {json.dumps(followup.jobs, indent=2)}")
        
        # Test normalization directly
        normalized = normalize_job_specs(result.get("new_jobs", []))
        print(f"Normalized specs: {json.dumps(normalized, indent=2)}")
    else:
        print("No followup detected.")

if __name__ == "__main__":
    test_lcp()
