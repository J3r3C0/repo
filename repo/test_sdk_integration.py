"""
SDK Integration Test - Capability Routing Demo

Demonstrates:
1. SDK capability discovery (Hub vs Core)
2. Automatic routing to correct service
3. Mission/Task/Job creation via SDK
"""

import os
import sys

# Set environment for testing
os.environ["SHERATAN_CORE_URL"] = "http://127.0.0.1:8001"  # Core API (actual port)
os.environ["SHERATAN_HUB_URL"] = "http://127.0.0.1:8787"   # Hub (if running)
os.environ["SHERATAN_PREFER"] = "auto"

from sheratan_sdk import SheratanClient, SheratanHTTPError

def main():
    print("=" * 70)
    print("Sheratan SDK Integration Test - Capability Routing")
    print("=" * 70)
    
    try:
        # Create client
        print("\n[1] Creating SDK client...")
        client = SheratanClient()
        print("✓ Client created")
        
        # Discover capabilities
        print("\n[2] Discovering service capabilities...")
        caps = client.debug_caps()
        
        for service_name, info in caps.items():
            print(f"\n{service_name.upper()}:")
            print(f"  URL: {info['base_url']}")
            print(f"  Reachable: {'✓' if info['reachable'] else '✗'}")
            if info['reachable']:
                print(f"  Health endpoint: {info['health_path']}")
                print(f"  Supported operations:")
                for op, supported in info['supports'].items():
                    status = "✓" if supported else "✗"
                    print(f"    {status} {op}")
        
        # Test mission creation
        print("\n[3] Testing mission creation (SDK auto-routes)...")
        mission = client.create_mission(
            "sdk-integration-test",
            description="Testing SDK capability routing",
            metadata={"source": "sdk_test", "timestamp": "2026-01-22"}
        )
        mission_id = mission.get("id", "unknown")
        print(f"✓ Mission created: {mission_id[:8] if len(mission_id) > 8 else mission_id}")
        
        # Test task creation
        print("\n[4] Testing task creation...")
        task = client.create_task(
            mission_id,
            "read-file-task",
            kind="read_file",
            params={"path": "README.md"}
        )
        task_id = task.get("id", "unknown")
        print(f"✓ Task created: {task_id[:8] if len(task_id) > 8 else task_id}")
        
        # Test job creation
        print("\n[5] Testing job creation...")
        job = client.create_job(
            task_id,
            payload={"kind": "read_file", "params": {"path": "README.md"}},
            depends_on=[]
        )
        job_id = job.get("id", "unknown")
        print(f"✓ Job created: {job_id[:8] if len(job_id) > 8 else job_id}")
        
        # Get job status
        print("\n[6] Testing job retrieval...")
        job_status = client.get_job(job_id)
        print(f"✓ Job status: {job_status.get('status', 'unknown')}")
        
        print("\n" + "=" * 70)
        print("✓ SDK Integration Test PASSED")
        print("=" * 70)
        print("\nKey Benefits:")
        print("  • No hardcoded URLs")
        print("  • Automatic service discovery")
        print("  • Deterministic routing (no 405 errors)")
        print("  • Retry logic built-in")
        print("=" * 70)
        
        return 0
        
    except SheratanHTTPError as e:
        print(f"\n✗ HTTP Error: {e}")
        print(f"  Status: {e.status_code}")
        print(f"  Method: {e.method}")
        print(f"  URL: {e.url}")
        if e.body:
            print(f"  Response: {e.body}")
        return 1
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
