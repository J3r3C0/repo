from core import storage
import json

jobs = storage.list_jobs()
print(f"DEBUG: Found {len(jobs)} total jobs.")
jobs.sort(key=lambda j: j.created_at, reverse=True)

for j in jobs[:10]:
    print(f"--- Job {j.id} ---")
    print(f"  Task: {j.task_id}")
    print(f"  Status: {j.status}")
    print(f"  Created: {j.created_at}")
    print(f"  Kind: {j.payload.get('kind', 'unknown')}")
