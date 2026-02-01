from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional

@dataclass(frozen=True)
class Phase1Status:
    status: str  # "OK" | "BLOCKED"
    reason: Optional[str]
    policy_id: Optional[str]
    policy_version: Optional[str]
    policy_hash: Optional[str]
    deterministic_mode: Optional[bool]
    strict: bool
    checked_at: str  # ISO timestamp
    build_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
