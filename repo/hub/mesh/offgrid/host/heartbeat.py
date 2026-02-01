import asyncio
from typing import Optional
import time
import httpx
import os
from datetime import datetime

class HeartbeatClient:
    """Sends periodic status updates to Sheratan Core."""
    
    def __init__(self, core_url: str, host_id: str, endpoint: Optional[str] = None, interval: int = 10):
        self.core_url = core_url
        self.host_id = host_id
        self.endpoint = endpoint
        self.interval = interval
        self._running = False
        
        # Track A4: Load/Generate persistent identity
        try:
            from node.identity import get_or_generate_identity
            self.priv_key, self.pub_key = get_or_generate_identity()
            print(f"[heartbeat] Identity loaded. PubKey: {self.pub_key[:8]}...")
        except Exception as e:
            self.priv_key = self.pub_key = None
            print(f"[heartbeat] WARNING: Failed to load identity: {e}")

    async def start(self):
        self._running = True
        asyncio.create_task(self._loop())
        print(f"[heartbeat] Started for host {self.host_id} (interval: {self.interval}s)")

    async def stop(self):
        self._running = False

    async def _loop(self):
        token = os.getenv("SHERATAN_HUB_TOKEN", "shared-secret")
        headers = {
            "X-Sheratan-Token": token,
            "Authorization": f"Bearer {token}"
        }
        
        # Track A4: Identity signing logic
        from node.identity import sign_heartbeat
        
        async with httpx.AsyncClient(headers=headers) as client:
            while self._running:
                try:
                    # Gather attestation signals (Track A2)
                    # For now using static/placeholder values for build_id and capabilities
                    payload = {
                        "host_id": self.host_id,
                        "status": "online",
                        "endpoint": self.endpoint,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "public_key": self.pub_key,
                        "attestation": {
                            "build_id": "sheratan-v2.8-prod",
                            "capabilities": ["compute", "list_files", "write_file", "read_file", "ping"],
                            "capability_hash": "a4b4e9185ee3062f3f1f7259d7e3397d9fe5d41c5de2a0d0a7f43b83a0d0a7f4" 
                        }
                    }
                    
                    # Sign the payload (Track A4)
                    if self.priv_key:
                        payload["signature"] = sign_heartbeat(payload, self.priv_key)
                        
                    # Heartbeat ALWAYS goes to 8001 Control Plane
                    response = await client.post(f"{self.core_url}/api/hosts/heartbeat", json=payload, timeout=5.0)
                    if response.status_code == 401 or response.status_code == 403:
                        print(f"[heartbeat] AUTH_FAIL: Hub rejected token (HTTP {response.status_code})")
                    elif response.status_code != 200:
                        print(f"[heartbeat] Error: Hub returned {response.status_code}")
                except Exception as e:
                    print(f"[heartbeat] Failed: {e}")
                
                await asyncio.sleep(self.interval)
