# sheratan_core_v2/webrelay_http_client.py
"""
HTTP client for WebRelay API.
Replaces file-based communication with direct HTTP calls.

MIGRATION NOTE: This module can optionally use sheratan-sdk for capability routing.
Set USE_SDK=true to enable SDK-based routing (avoids hardcoded URLs).
"""

import requests
import os
from typing import Optional, Dict, Any
from datetime import datetime

from hub import storage, models

# Optional: Use SDK if available and enabled
USE_SDK = os.getenv("USE_SDK", "false").lower() == "true"

if USE_SDK:
    try:
        from sheratan_sdk import SheratanClient, SheratanHTTPError
        _sdk_client = None
        
        def _get_sdk_client():
            global _sdk_client
            if _sdk_client is None:
                _sdk_client = SheratanClient()
            return _sdk_client
    except ImportError:
        USE_SDK = False
        print("[webrelay_http_client] SDK not available, falling back to direct requests")


class WebRelayHTTPClient:
    """HTTP client for WebRelay API."""
    
    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url.rstrip('/')
    
    def submit_job(self, job: models.Job, task: models.Task, mission: models.Mission) -> Optional[Dict[str, Any]]:
        """
        Submit a job to WebRelay via HTTP API.
        
        Args:
            job: Job object
            task: Task object  
            mission: Mission object
            
        Returns:
            Response from WebRelay or None on error
        """
        # Build unified job payload
        unified_job = {
            "job_id": job.id,
            "kind": task.kind or "llm_call",
            "session_id": f"core_v2_{mission.id}",
            "created_at": job.created_at,
            "payload": {
                "response_format": "lcp",
                "mission": mission.to_dict(),
                "task": task.to_dict(),
                "params": job.payload,
            },
        }
        
        try:
            if USE_SDK:
                # SDK-based submission (with capability routing)
                client = _get_sdk_client()
                try:
                    # Try legacy endpoint first (WebRelay specific)
                    result = client.submit_job_legacy(unified_job)
                except RuntimeError as e:
                    # Fallback to direct request if SDK doesn't support legacy endpoint
                    print(f"[webrelay_http_client] SDK fallback: {e}")
                    result = self._submit_direct(unified_job)
            else:
                # Direct request (legacy)
                result = self._submit_direct(unified_job)
            
            # Update job with result
            job.result = result
            if result.get("ok", False):
                job.status = "completed"
            else:
                job.status = "failed"
            job.updated_at = datetime.utcnow().isoformat() + "Z"
            storage.update_job(job)
            
            return result
            
        except requests.exceptions.Timeout:
            job.status = "failed"
            job.result = {"ok": False, "error": "WebRelay timeout"}
            job.updated_at = datetime.utcnow().isoformat() + "Z"
            storage.update_job(job)
            return None
            
        except Exception as e:
            job.status = "failed"
            job.result = {"ok": False, "error": str(e)}
            job.updated_at = datetime.utcnow().isoformat() + "Z"
            storage.update_job(job)
            return None
    
    def _submit_direct(self, unified_job: Dict[str, Any]) -> Dict[str, Any]:
        """Direct HTTP submission (no SDK)."""
        response = requests.post(
            f"{self.base_url}/api/job/submit",
            json=unified_job,
            timeout=120  # 2 minutes for LLM response
        )
        response.raise_for_status()
        return response.json()
    
    def health_check(self) -> bool:
        """Check if WebRelay is available."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
