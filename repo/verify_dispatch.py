import requests
import time
import json
import uuid

BASE_URL = "http://localhost:8001"

def test_dispatch():
    # 1. Create a mission
    print("Creating mission...")
    resp = requests.post(f"{BASE_URL}/api/missions", json={
        "title": "Verification Mission",
        "description": "Verify HTTP dispatch",
        "user_id": "jerre", # Valid user_id
        "status": "active"
    })
    resp.raise_for_status()
    mission = resp.json()
    mission_id = mission["id"]
    print(f"Mission created: {mission_id}")

    # 2. Create a task
    print(f"Creating task for mission {mission_id}...")
    resp = requests.post(f"{BASE_URL}/api/missions/{mission_id}/tasks", json={
        "name": "Verify Physical Dispatch",
        "description": "List files in core/",
        "kind": "list_files",
        "params": {"path": "core/"}
    })
    resp.raise_for_status()
    task = resp.json()
    task_id = task["id"]
    print(f"Task created: {task_id}")

    # 3. Create a job
    print(f"Creating job for task {task_id}...")
    resp = requests.post(f"{BASE_URL}/api/tasks/{task_id}/jobs", json={
        "payload": {"kind": "list_files", "params": {"path": "core/"}}
    })
    resp.raise_for_status()
    job = resp.json()
    job_id = job["id"]
    print(f"Job created: {job_id}")

    # 4. Wait for dispatch and completion
    print("Waiting for dispatch/completion...")
    for _ in range(30):
        time.sleep(2)
        resp = requests.get(f"{BASE_URL}/api/jobs/{job_id}")
        job = resp.json()
        status = job.get("status")
        print(f"Current status: {status}")
        if status == "completed":
            print("Job completed successfully!")
            print("Result Summary:", job.get("result", {}).get("summary"))
            return True
        if status == "failed":
            print("Job failed!")
            print("Result:", job.get("result"))
            return False
    
    print("Timed out waiting for job completion.")
    return False

if __name__ == "__main__":
    test_dispatch()
