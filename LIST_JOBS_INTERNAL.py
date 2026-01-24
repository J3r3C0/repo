from core import storage
import json

jobs = storage.list_jobs()
print(f"TOTAL_JOBS: {len(jobs)}")

# Sort by created_at DESC
jobs.sort(key=lambda j: j.created_at, reverse=True)

for j in jobs[:5]:
    print(f"ID: {j.id} | TASK: {j.task_id} | STATUS: {j.status} | CREATED: {j.created_at}")
