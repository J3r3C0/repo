# core/vmesh/runtime.py
from __future__ import annotations
from typing import Optional
from core.vmesh.controller import PolicyMode

class VMeshRuntime:
    """
    Global runtime state for V-Mesh Enforcement.
    Synchronizes the mode decision from the Control-Plane to the Data-Plane.
    """
    _instance: Optional[VMeshRuntime] = None
    
    def __init__(self):
        self.current_mode: PolicyMode = PolicyMode.NORMAL
        self.last_update_ts: float = 0.0
        self.stability_s: float = 1.0
        self.sync_score: float = 1.0

    @classmethod
    def get_instance(cls) -> VMeshRuntime:
        if cls._instance is None:
            cls._instance = VMeshRuntime()
        return cls._instance

vmesh_runtime = VMeshRuntime.get_instance()

def check_vmesh_action(action: str) -> bool:
    """
    Returns True if the action is allowed in the current V-Mesh PolicyMode.
    Helper for API and Internal Logic.
    """
    mode = vmesh_runtime.current_mode
    
    if mode == PolicyMode.SAFE_MODE:
        # Only allow diagnostic/read actions
        return action in ["read", "health", "diag"]
        
    if mode == PolicyMode.READONLY:
        return action in ["read", "health", "diag"]
        
    if mode == PolicyMode.DEGRADED:
        # Disallow high-risk or low-priority mutations if needed
        return True # Default allow for now
        
    return True
