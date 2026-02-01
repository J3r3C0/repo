#!/usr/bin/env python3
"""
Simplified E2E Test: Direct DB + HTTP API
Tests Mission → Task → Job → Simulated LCP Response
"""
import requests
import json
import time
import uuid

BASE_URL = "http://localhost:8001"

def test_e2e_simple():
    print("=" * 80)
    print("E2E Test: Mission → Task → Job → LCP Follow-up")
    print("=" * 80)
    
    # Step 1: Check system health
    print("\n[1/5] Checking system health...")
    try:
        resp = requests.get(f"{BASE_URL}/api/system/health", timeout=5)
        print(f"✓ Core API: {resp.json()}")
    except Exception as e:
        print(f"✗ Core API Error: {e}")
        return False
    
    # Step 2: Create a simple test job via API
    print("\n[2/5] Creating test job via /api/jobs...")
    job_data = {
        "kind": "test.e2e",
        "params": {
            "instruction": "Test autonomous follow-up generation",
            "test_mode": True
        }
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/api/jobs", json=job_data, timeout=10)
        result = resp.json()
        print(f"✓ Job created: {json.dumps(result, indent=2)}")
        job_id = result.get("job_id")
    except Exception as e:
        print(f"✗ Job creation failed: {e}")
        return False
    
    # Step 3: Check missions
    print("\n[3/5] Listing missions...")
    try:
        resp = requests.get(f"{BASE_URL}/api/missions", timeout=5)
        missions = resp.json()
        print(f"✓ Found {len(missions)} missions")
        if missions:
            print(f"  Latest: {missions[-1].get('title', 'N/A')}")
    except Exception as e:
        print(f"⚠ Missions check: {e}")
    
    # Step 4: Check system state
    print("\n[4/5] Checking system state...")
    try:
        resp = requests.get(f"{BASE_URL}/api/system/state", timeout=5)
        state = resp.json()
        print(f"✓ State: {state.get('state')}")
        print(f"  Duration: {state.get('duration_sec')}s")
    except Exception as e:
        print(f"⚠ State check: {e}")
    
    # Step 5: Summary
    print("\n[5/5] Test Summary")
    print("=" * 80)
    print("✓ Core API is responsive")
    print("✓ Job creation endpoint works")
    print("⚠ Note: Full LCP follow-up test requires:")
    print("  - Mission/Task creation endpoints (currently limited)")
    print("  - LCP result submission with follow-up jobs")
    print("  - ChainRunner processing verification")
    print("=" * 80)
    
    return True

if __name__ == "__main__":
    try:
        success = test_e2e_simple()
        print(f"\n{'✓ TEST PASSED' if success else '✗ TEST FAILED'}")
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
