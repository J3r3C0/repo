# repo/core/policy.py
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Literal

from core import config

logger = logging.getLogger(__name__)

# --- GLOBAL SYSTEM STATES ---

class SystemState(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    DEGRADED = "DEGRADED"
    REFLECTIVE = "REFLECTIVE"
    RECOVERY = "RECOVERY"
    PAUSED = "PAUSED"

@dataclass(frozen=True)
class TransitionEvent:
    event_id: str
    ts: float
    prev_state: str
    next_state: str
    reason: str
    actor: str = "system"
    meta: Dict[str, Any] = None

    def to_json(self) -> str:
        d = asdict(self)
        if d["meta"] is None: d["meta"] = {}
        return json.dumps(d, ensure_ascii=False, sort_keys=True)

class SystemStateMachine:
    def __init__(self):
        self.load_path = config.DATA_DIR / "system_state.json"
        self.log_path = config.DATA_DIR / "state_transitions.jsonl"
        self._snapshot = None
        
    def load_or_init(self):
        if self.load_path.exists():
            try:
                with open(self.load_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._snapshot = data
                    return data
            except Exception: pass
            
        initial = {
            "state": SystemState.PAUSED.value,
            "since_ts": time.time(),
            "health": {},
            "counters": {}
        }
        self._snapshot = initial
        self._persist()
        return initial

    def snapshot(self):
        if self._snapshot is None:
            return self.load_or_init()
        return self._snapshot

    def _persist(self):
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.load_path, "w", encoding="utf-8") as f:
            json.dump(self._snapshot, f, indent=2)

    def transition(self, next_state: SystemState, reason: str, meta: dict = None):
        prev = self._snapshot["state"]
        if prev == next_state.value: return
        
        event = TransitionEvent(
            event_id=str(uuid.uuid4()), ts=time.time(),
            prev_state=prev, next_state=next_state.value,
            reason=reason, meta=meta or {}
        )
        
        self._snapshot["state"] = next_state.value
        self._snapshot["since_ts"] = event.ts
        self._snapshot["last_transition"] = asdict(event)
        self._persist()
        
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(event.to_json() + "\n")
        return event

# --- NODE POLICY ENGINE ---

PolicyState = Literal["NORMAL", "WARN", "QUARANTINED"]
PolicyReason = Literal["NONE", "DRIFT", "SPOOF_SUSPECT", "ADMIN"]

@dataclass(frozen=True)
class PolicyDecision:
    state: PolicyState
    reason: PolicyReason
    until_utc: Optional[str]
    actions: Tuple[str, ...]
    defer_ms: Optional[int] = None

class PolicyEngine:
    def decide(self, host: Dict[str, Any], status: str) -> PolicyDecision:
        status = status.upper()
        if status == "SPOOF_SUSPECT":
            until = (datetime.utcnow() + timedelta(minutes=10)).isoformat() + "Z"
            return PolicyDecision("QUARANTINED", "SPOOF_SUSPECT", until, ("AUDIT", "THROTTLE"), 2000)
        if status == "DRIFT":
            return PolicyDecision("WARN", "DRIFT", None, ("AUDIT", "ALERT"))
        return PolicyDecision("NORMAL", "NONE", None, ())

# --- GLOBAL INSTANCES ---
state_machine = SystemStateMachine()
policy_engine = PolicyEngine()
