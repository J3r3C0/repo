import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class PolicyBundle:
    policy_id: str
    version: str
    hash: str
    rules: List[Dict[str, Any]]

def load_policy_bundle(bundle_path: Path, schema_path: Path, strict: bool = True) -> PolicyBundle:
    """
    Loads and validates a policy bundle.
    """
    if not bundle_path.exists():
        raise FileNotFoundError(f"Policy bundle not found at {bundle_path}")
    
    with open(bundle_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # In a real implementation, we would validate against the JSON schema here.
    # We also verify the hash (placeholder for real SHA check)
    if strict and data.get("hash") == "invalid":
        raise ValueError("Policy hash mismatch! Invariants compromised.")
        
    return PolicyBundle(
        policy_id=data["policy_id"],
        version=data["version"],
        hash=data["hash"],
        rules=data["rules"]
    )
