"""
Core Self-Ping Thread
Sends heartbeat to /api/system/heartbeat every 20s
"""
import threading
import time
import requests
from pathlib import Path

class CoreHeartbeat:
    """Self-ping thread for Core service"""
    
    def __init__(self, core_url: str = "http://127.0.0.1:8001", interval_sec: int = 20):
        self.core_url = core_url
        self.interval_sec = interval_sec
        self._stop_event = threading.Event()
        self._thread = None
    
    def start(self):
        """Start heartbeat thread"""
        if self._thread and self._thread.is_alive():
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True, name="CoreHeartbeat")
        self._thread.start()
        print(f"[heartbeat] Core self-ping started ({self.interval_sec}s interval)")
    
    def stop(self):
        """Stop heartbeat thread"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
    
    def _heartbeat_loop(self):
        """Heartbeat loop - ping every interval_sec"""
        while not self._stop_event.is_set():
            try:
                response = requests.post(
                    f"{self.core_url}/api/system/heartbeat",
                    json={
                        "service": "core",
                        "file_location": "core/main.py"
                    },
                    timeout=2
                )
                
                if response.status_code == 200:
                    print(f"[heartbeat] Core ping OK")
                else:
                    print(f"[heartbeat] Core ping failed: {response.status_code}")
                    
            except Exception as e:
                print(f"[heartbeat] Core ping error: {e}")
            
            # Wait interval
            self._stop_event.wait(self.interval_sec)
    
    def ping_now(self):
        """Manual ping (for testing)"""
        try:
            response = requests.post(
                f"{self.core_url}/api/system/heartbeat",
                json={
                    "service": "core",
                    "file_location": "core/main.py"
                },
                timeout=2
            )
            return response.status_code == 200
        except:
            return False
