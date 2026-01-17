# repo/core/trace.py
import json
import uuid
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import jsonschema

from core import config

class DecisionTraceLogger:
    """
    Hard schema-validating logger for MCTS decision traces.
    
    Rules:
    - Valid events → DATA_DIR/decision_trace.jsonl
    - Invalid events → DATA_DIR/decision_trace_breaches.jsonl (separate)
    - No invalid events ever pollute the main stream
    """
    
    def __init__(self, schema_path: Path):
        self.log_path = config.DATA_DIR / "decision_trace.jsonl"
        self.breach_path = config.DATA_DIR / "decision_trace_breaches.jsonl"
        self.schema_path = schema_path
        
        with open(schema_path, "r", encoding="utf-8") as f:
            self.schema = json.load(f)
            
    def _now_iso(self) -> str:
        return datetime.utcnow().isoformat() + "Z"
    
    def _log_breach(self, entry: Dict[str, Any], validation_error: 'jsonschema.ValidationError'):
        """Log schema validation breach to separate file."""
        error_info = {
            "message": str(validation_error.message),
            "validator": validation_error.validator,
            "path": "/" + "/".join(str(p) for p in validation_error.absolute_path) if validation_error.absolute_path else "/"
        }
        
        raw_str = json.dumps(entry)
        raw_truncated = raw_str[:4000] + "..." if len(raw_str) > 4000 else raw_str
        
        breach_entry = {
            "timestamp": self._now_iso(),
            "schema_version": "decision_trace_v1",
            "error": error_info,
            "raw_event_truncated": raw_truncated
        }
        
        with open(self.breach_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(breach_entry) + "\n")
        
        print(f"[BREACH] Schema validation failed: {error_info['message']} at {error_info['path']}", file=sys.stderr)

    def _normalize_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        s = dict(state or {})
        s.setdefault("context_refs", [])
        s.setdefault("constraints", {
            "budget_remaining": 100.0,
            "time_remaining_ms": 300000.0,
            "readonly": False,
            "risk_level": "low"
        })
        return s

    def _normalize_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        a = dict(action or {})
        a.setdefault("action_id", str(uuid.uuid4()))
        a.setdefault("type", "EXECUTE") # ROUTE, EXECUTE, RETRY, etc.
        a.setdefault("mode", "execute")
        a.setdefault("params", {})
        a.setdefault("select_score", 1.0)
        a.setdefault("risk_gate", True)
        return a

    def _normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        r = dict(result or {})
        r.setdefault("status", "success")
        r.setdefault("metrics", {"latency_ms": 0.0, "cost": 0.0, "tokens": 0.0, "retries": 0.0, "risk": 0.0, "quality": 1.0})
        r.setdefault("score", 1.0)
        return r

    def log_node(
        self,
        trace_id: str,
        intent: str,
        build_id: str,
        state: Dict[str, Any],
        action: Dict[str, Any],
        result: Dict[str, Any],
        job_id: Optional[str] = None,
        parent_node_id: Optional[str] = None,
        depth: int = 0
    ) -> str:
        """Log a decision node. Returns node_id on success, raises on validation failure."""
        node_id = str(uuid.uuid4())
        
        entry = {
            "schema_version": "decision_trace_v1",
            "timestamp": self._now_iso(),
            "trace_id": trace_id,
            "node_id": node_id,
            "parent_node_id": parent_node_id,
            "build_id": build_id,
            "job_id": job_id,
            "intent": intent,
            "depth": depth,
            "state": self._normalize_state(state),
            "action": self._normalize_action(action),
            "result": self._normalize_result(result)
        }
        
        try:
            jsonschema.validate(instance=entry, schema=self.schema)
        except jsonschema.ValidationError as e:
            self._log_breach(entry, e)
            raise ValueError(f"Schema breach: {e.message}")
        
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
            
        return node_id

# Instantiate global logger
SCHEMA_FILE = config.BASE_DIR / "schemas" / "decision_trace_v1.json"

if not SCHEMA_FILE.exists():
    fallback = Path(__file__).parent.parent / "schemas" / "decision_trace_v1.json"
    if fallback.exists():
        SCHEMA_FILE = fallback

if SCHEMA_FILE.exists():
    trace_logger = DecisionTraceLogger(SCHEMA_FILE)
else:
    print(f"[trace] WARNING: Schema file not found at {SCHEMA_FILE}. Decision tracing will be limited.")
    class DummyLogger:
        def log_node(self, *args, **kwargs): return "missing-schema-node"
    trace_logger = DummyLogger()
