import asyncio
import time
import httpx
import os
from datetime import datetime

class HeartbeatClient:
    """Sends periodic status updates to Sheratan Core."""
    
    def __init__(self, core_url: str, host_id: str, interval: int = 10):
        self.core_url = core_url
        self.host_id = host_id
        self.interval = interval
        self._running = False

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
        async with httpx.AsyncClient(headers=headers) as client:
            while self._running:
                try:
                    payload = {
                        "host_id": self.host_id,
                        "status": "online",
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                    # Heartbeat ALWAYS goes to 8787 Control Plane
                    response = await client.post(f"{self.core_url}/api/hosts/heartbeat", json=payload, timeout=5.0)
                    if response.status_code == 401 or response.status_code == 403:
                        print(f"[heartbeat] AUTH_FAIL: Hub rejected token (HTTP {response.status_code})")
                    elif response.status_code != 200:
                        print(f"[heartbeat] Error: Hub returned {response.status_code}")
                except Exception as e:
                    print(f"[heartbeat] Failed: {e}")
                
                await asyncio.sleep(self.interval)
