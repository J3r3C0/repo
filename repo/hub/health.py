# core/health.py
import asyncio
import time
import psutil
import socket
from datetime import datetime
from typing import Dict, Any, List, Optional
from hub import storage
from core.config import RobustnessConfig, CORE_START_TIME

class HealthManager:
    """
    Centralized health monitoring for Sheratan.
    Unifies legacy HealthTab requirements and modern OpsTab / StateMachine needs.
    """
    
    SERVICES = [
        {"name": "Core API", "port": 8001, "critical": True, "type": "core"},
        {"name": "WebRelay", "port": 3000, "critical": True, "type": "relay"},
        {"name": "Broker", "port": 9000, "critical": False, "type": "engine"},
        {"name": "Host-A", "port": 8081, "critical": False, "type": "engine"},
        {"name": "Host-B", "port": 8082, "critical": False, "type": "engine"},
        {"name": "Dashboard", "port": 3001, "critical": False, "type": "ui"}
    ]

    @staticmethod
    async def check_port(port: int, timeout: float = 0.5) -> bool:
        if port == 8001:
            return True # We are the Core API
        
        targets = ['127.0.0.1', 'localhost']
        for target in targets:
            try:
                # Use socket for synchronous-ish quick check or loop.run_in_executor
                # But here we are in an async context, so let's stick to asyncio if possible
                # or just use a simple socket check with timeout for speed.
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(target, port),
                    timeout=timeout
                )
                writer.close()
                await writer.wait_closed()
                return True
            except:
                continue
        return False

    @classmethod
    async def evaluate_full_health(cls) -> Dict[str, Any]:
        """Unified health assessment for StateMachine and OpsTab."""
        results = {}
        service_list = []
        critical_down = []
        
        for s in cls.SERVICES:
            is_up = await cls.check_port(s["port"])
            status = "active" if is_up else "down"
            results[s["name"]] = status
            
            # For Legacy HealthTab compatibility
            service_list.append({
                "id": s["name"].lower().replace(" ", "-"),
                "name": s["name"],
                "status": "up" if is_up else "down",
                "port": s["port"],
                "type": s["type"],
                "lastCheck": datetime.utcnow().isoformat() + "Z"
            })
            
            if not is_up and s["critical"]:
                critical_down.append(s["name"])

        # DB Check
        db_ok = True
        try:
            with storage.get_db() as conn:
                conn.execute("SELECT 1")
        except:
            db_ok = False
            critical_down.append("Database")

        overall = "operational"
        if critical_down:
            overall = "degraded"
        
        return {
            "overall": overall,
            "services": results,
            "service_list": service_list,
            "critical_down": critical_down,
            "db_ok": db_ok
        }

    @staticmethod
    def get_system_metrics() -> Dict[str, Any]:
        """Gather system-level metrics."""
        return {
            "uptime_sec": int(time.time() - CORE_START_TIME),
            "cpu_pct": psutil.cpu_percent(),
            "memory": dict(psutil.virtual_memory()._asdict()),
            "process": {
                "cpu_pct": psutil.Process().cpu_percent(),
                "memory_rss": psutil.Process().memory_info().rss
            },
            "storage": {
                "queue_depth": storage.count_pending_jobs(),
                "inflight": storage.count_inflight_jobs(),
                "ready_to_dispatch": storage.count_ready_jobs(datetime.utcnow().isoformat() + "Z")
            }
        }

health_manager = HealthManager()
