from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Dict


def canonical_no_hash(bundle: Dict[str, Any]) -> bytes:
    clone = dict(bundle)
    clone.pop("hash", None)
    return json.dumps(clone, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    active_dir = repo_root / "policies" / "active"
    active_dir.mkdir(parents=True, exist_ok=True)

    import sys
    if len(sys.argv) < 2:
        print("Usage: python tools/policy_apply.py <draft_policy.json>")
        return 2

    draft_path = Path(sys.argv[1]).resolve()
    if not draft_path.exists():
        print(f"Draft not found: {draft_path}")
        return 2
        
    raw = json.loads(draft_path.read_text(encoding="utf-8"))

    raw["hash"] = "sha256:" + sha256_hex(canonical_no_hash(raw))

    out_path = active_dir / f"{raw['policy_id']}.policy.json"
    out_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    print(f"Applied policy bundle → {out_path}")
    print(f"hash = {raw['hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
