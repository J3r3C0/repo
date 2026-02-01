"""
Heartbeat Monitoring System
Services send pings every 20s, dashboard alerts if >30s silent
"""
import time
import threading
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

@dataclass
class ServiceHeartbeat:
    name: str
    file_location: str
    last_ping: float = field(default_factory=time.time)
    last_exception: Optional[str] = None
    exception_time: Optional[float] = None
    status: str = "ok"  # ok, warn, error
    
    def is_alive(self, timeout_sec: int = 30) -> bool:
        """Check if service pinged within timeout"""
        return (time.time() - self.last_ping) < timeout_sec
    
    def seconds_since_ping(self) -> int:
        return int(time.time() - self.last_ping)

class HeartbeatMonitor:
    """Central heartbeat tracker for all services"""
    
    def __init__(self, timeout_sec: int = 30):
        self.timeout_sec = timeout_sec
        self.services: Dict[str, ServiceHeartbeat] = {}
        self._lock = threading.Lock()
        
        # Register known services
        self._register_services()
    
    def _register_services(self):
        """Pre-register expected services"""
        services = [
            ("core", "core/main.py"),
            ("webrelay", "external/webrelay/index.ts"),
            ("broker", "mesh/offgrid/broker/main.py"),
            ("node-a", "mesh/offgrid/host/basic/node_a.py"),
            ("chrome", "Chrome Debug Port 9222"),
            ("chainrunner", "core/chain_runner.py")
        ]
        
        with self._lock:
            for name, location in services:
                self.services[name] = ServiceHeartbeat(name=name, file_location=location)
    
    def ping(self, service_name: str, file_location: Optional[str] = None):
        """Record service heartbeat"""
        with self._lock:
            if service_name not in self.services:
                if file_location:
                    self.services[service_name] = ServiceHeartbeat(
                        name=service_name,
                        file_location=file_location
                    )
                else:
                    return  # Unknown service without location
            
            service = self.services[service_name]
            service.last_ping = time.time()
            service.status = "ok"
    
    def log_exception(self, service_name: str, exception_msg: str):
        """Log service exception"""
        with self._lock:
            if service_name in self.services:
                service = self.services[service_name]
                service.last_exception = exception_msg
                service.exception_time = time.time()
                service.status = "error"
    
    def get_status(self) -> Dict:
        """Get all service statuses"""
        with self._lock:
            result = {
                "timestamp": time.time(),
                "timeout_sec": self.timeout_sec,
                "services": []
            }
            
            for service in self.services.values():
                is_alive = service.is_alive(self.timeout_sec)
                seconds_silent = service.seconds_since_ping()
                
                status = {
                    "name": service.name,
                    "file_location": service.file_location,
                    "alive": is_alive,
                    "status": "offline" if not is_alive else service.status,
                    "seconds_since_ping": seconds_silent,
                    "last_ping_iso": datetime.fromtimestamp(service.last_ping).isoformat(),
                    "last_exception": service.last_exception if service.exception_time and (time.time() - service.exception_time) < 300 else None
                }
                
                result["services"].append(status)
            
            return result
    
    def get_critical_failures(self) -> list:
        """Get services that are offline or have exceptions"""
        with self._lock:
            failures = []
            for service in self.services.values():
                if not service.is_alive(self.timeout_sec):
                    failures.append({
                        "name": service.name,
                        "file_location": service.file_location,
                        "reason": f"No heartbeat for {service.seconds_since_ping()}s"
                    })
                elif service.last_exception and service.exception_time and (time.time() - service.exception_time) < 60:
                    failures.append({
                        "name": service.name,
                        "file_location": service.file_location,
                        "reason": service.last_exception
                    })
            return failures
