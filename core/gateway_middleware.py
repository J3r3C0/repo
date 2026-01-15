"""
Gateway Middleware for Sheratan Core API

Enforces G0-G4 security gates on all job creation requests.
Bridges the Core API (FastAPI) with the Mesh Gates implementation.
"""

from pathlib import Path
from typing import Dict, Any, List
from dataclasses import asdict
import json
import sys

# Ensure mesh package is importable (add repo root to path)
_repo_root = Path(__file__).parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from mesh.core.gates.pipeline import run_gates_v1, final_decision
from mesh.core.gates.config import GateConfig, default_gate_config
from mesh.core.gates.models import GateReport, GateStatus, NextAction


class GatewayViolation(Exception):
    """Raised when a job fails gateway enforcement."""
    
    def __init__(self, overall_status: str, reports: List[GateReport]):
        self.overall_status = overall_status
        self.reports = reports
        self.message = f"Gateway enforcement failed: {overall_status}"
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict for API response."""
        return {
            "error": "gateway_violation",
            "status": self.overall_status,
            "message": self.message,
            "reports": [asdict(r) for r in self.reports],
            "blocked_reasons": [
                {
                    "gate": r.gate_id,
                    "status": r.status.value,
                    "reasons": [asdict(reason) for reason in r.reasons]
                }
                for r in self.reports if r.status in [GateStatus.FAIL, GateStatus.PAUSE]
            ]
        }


class GatewayEnforcer:
    """Gateway enforcement engine for Core API."""
    
    def __init__(self, config_path: Path = None):
        """
        Initialize gateway enforcer.
        
        Args:
            config_path: Optional path to gateway_config.json
        """
        self.project_root = Path(__file__).parent.parent
        self.config_path = config_path or (self.project_root / "config" / "gateway_config.json")
        self.gate_config = self._load_gate_config()
        self.runtime_config = self._load_runtime_config()
    
    def _load_gate_config(self) -> GateConfig:
        """Load gate configuration (allowlists, forbidden kinds, etc.)."""
        return default_gate_config(self.project_root)
    
    def _load_runtime_config(self) -> Dict[str, Any]:
        """Load runtime configuration (enabled, enforcement mode, etc.)."""
        if self.config_path.exists():
            try:
                return json.loads(self.config_path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"[gateway] Warning: Failed to load config from {self.config_path}: {e}")
        
        # Default configuration
        return {
            "enabled": True,
            "enforce_on_api": True,
            "enforcement_mode": "soft",  # "soft" (WARN only) or "hard" (FAIL blocks)
            "allowed_kinds": [
                "llm_call",
                "agent_plan",
                "read_file",
                "write_file",
                "walk_tree",
                "read_file_batch"
            ],
            "require_provenance": True,
            "log_all_decisions": True
        }
    
    def enforce(self, job_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run G0-G4 gates on job payload.
        
        Args:
            job_dict: Job payload to validate
        
        Returns:
            Gate enforcement result with:
            - overall_status: PASS/WARN/FAIL/PAUSE
            - enforcement_mode: soft/hard
            - allowed: bool (True if job creation allowed)
            - reports: list of gate reports
        
        Raises:
            GatewayViolation: If gates fail and enforcement_mode is "hard"
        """
        # Check if enforcement is enabled
        if not self.runtime_config.get("enabled", True):
            return {
                "overall_status": "BYPASS",
                "enforcement_mode": "disabled",
                "allowed": True,
                "reason": "enforcement_disabled"
            }
        
        # Ensure provenance exists
        if "provenance" not in job_dict:
            job_dict["provenance"] = {}
        
        # Set source_zone for API-created jobs
        if "source_zone" not in job_dict["provenance"]:
            job_dict["provenance"]["source_zone"] = "api"
        
        # Extract context for logging
        source_zone = job_dict.get("provenance", {}).get("source_zone", "unknown")
        task_id = job_dict.get("task_id")
        
        # Run gate pipeline
        reports = run_gates_v1(job_dict, self.gate_config)
        overall, next_action = final_decision(reports)
        
        # Determine enforcement mode
        enforcement_mode = self.runtime_config.get("enforcement_mode", "soft")
        
        # Determine if job is allowed
        if enforcement_mode == "hard":
            # Hard mode: Block on FAIL/PAUSE
            allowed = overall not in ["FAIL", "PAUSE"]
        else:
            # Soft mode: Always allow, just warn
            allowed = True
        
        # Log decision if enabled
        if self.runtime_config.get("log_all_decisions", True):
            self._log_decision(
                job_id=job_dict.get("job_id", "unknown"),
                task_id=task_id,
                overall=overall,
                enforcement_mode=enforcement_mode,
                allowed=allowed,
                source_zone=source_zone,
                reports=reports
            )
        
        # Build result
        result = {
            "overall_status": overall,
            "enforcement_mode": enforcement_mode,
            "allowed": allowed,
            "next_action": next_action.value,
            "reports": [asdict(r) for r in reports]
        }
        
        # Enforce based on mode
        if enforcement_mode == "hard" and not allowed:
            # Hard enforcement: FAIL and PAUSE block job creation
            raise GatewayViolation(overall, reports)
        elif enforcement_mode == "soft" and not allowed:
            # This should never happen in soft mode, but log for safety
            print(f"[gateway] WARNING: Soft mode with allowed=False (should not happen)")
        
        if overall in ["FAIL", "PAUSE"] and allowed:
            print(f"[gateway] SOFT ENFORCEMENT: Job allowed despite {overall} (would block in hard mode)")
        
        return result
    
    def _log_decision(
        self,
        job_id: str,
        task_id: str,
        overall: str,
        enforcement_mode: str,
        allowed: bool,
        source_zone: str,
        reports: List[GateReport]
    ):
        """Log gateway decision to JSONL file with full context."""
        log_dir = self.project_root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "gateway_enforcement.jsonl"
        
        from datetime import datetime
        
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "job_id": job_id,
            "task_id": task_id,
            "overall_status": overall,
            "enforcement_mode": enforcement_mode,
            "allowed": allowed,
            "source_zone": source_zone,
            "reports": [
                {
                    "gate_id": r.gate_id,
                    "status": r.status.value,
                    "severity": r.severity.value,
                    "reasons": [asdict(reason) for reason in r.reasons]
                }
                for r in reports
            ]
        }
        
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"[gateway] Warning: Failed to log decision: {e}")


# Global enforcer instance
_enforcer = None

def get_enforcer() -> GatewayEnforcer:
    """Get or create the global gateway enforcer instance."""
    global _enforcer
    if _enforcer is None:
        _enforcer = GatewayEnforcer()
    return _enforcer


def enforce_gateway(job_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to enforce gateway on a job payload.
    
    Args:
        job_dict: Job payload to validate
    
    Returns:
        Gate enforcement result
    
    Raises:
        GatewayViolation: If gates fail and enforcement is enabled
    """
    return get_enforcer().enforce(job_dict)


def get_gateway_stats() -> Dict[str, Any]:
    """
    Get gateway statistics and configuration for healthcheck/debugging.
    
    Returns:
        Dict with config, stats, and recent decisions
    """
    enforcer = get_enforcer()
    
    # Read log file for stats
    log_file = enforcer.project_root / "logs" / "gateway_enforcement.jsonl"
    
    stats = {
        "decisions_total": 0,
        "decisions_today": 0,
        "last_5_decisions": []
    }
    
    if log_file.exists():
        try:
            from datetime import datetime, date
            today = date.today()
            
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                stats["decisions_total"] = len(lines)
                
                # Count today's decisions and collect last 5
                recent = []
                for line in reversed(lines[-100:]):  # Check last 100
                    try:
                        entry = json.loads(line)
                        timestamp_str = entry.get("timestamp", "")
                        if timestamp_str:
                            entry_date = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")).date()
                            if entry_date == today:
                                stats["decisions_today"] += 1
                        
                        if len(recent) < 5:
                            recent.append({
                                "timestamp": entry.get("timestamp"),
                                "job_id": entry.get("job_id"),
                                "task_id": entry.get("task_id"),
                                "overall_status": entry.get("overall_status"),
                                "allowed": entry.get("allowed"),
                                "enforcement_mode": entry.get("enforcement_mode")
                            })
                    except:
                        continue
                
                stats["last_5_decisions"] = recent
        except Exception as e:
            stats["error"] = f"Failed to read log: {e}"
    
    return {
        "config": {
            "config_file": str(enforcer.config_path),
            "config_exists": enforcer.config_path.exists(),
            "enforcement_mode": enforcer.runtime_config.get("enforcement_mode", "soft"),
            "enabled": enforcer.runtime_config.get("enabled", True),
            "log_all_decisions": enforcer.runtime_config.get("log_all_decisions", True),
            "allowed_kinds": enforcer.runtime_config.get("allowed_kinds", []),
            "forbidden_kinds": list(enforcer.gate_config.forbidden_kinds)
        },
        "stats": stats
    }
