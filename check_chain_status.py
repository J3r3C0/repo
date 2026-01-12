import requests

jobs = requests.get('http://localhost:8001/api/jobs').json()

# Find the latest chain (by looking for walk_tree jobs)
walk_tree_jobs = [j for j in jobs if j.get('payload', {}).get('kind') == 'walk_tree']
if not walk_tree_jobs:
    print("No walk_tree jobs found")
    exit()

# Get the latest walk_tree job
latest_walk = walk_tree_jobs[-1]
task_id = latest_walk.get('task_id')

# Get all jobs for this task
task_jobs = [j for j in jobs if j.get('task_id') == task_id]
task_jobs.sort(key=lambda x: x.get('created_at', ''))

print(f"Chain for task {task_id[:12]}:")
print("=" * 80)
for j in task_jobs:
    kind = j.get('payload', {}).get('kind', 'unknown')
    status = j.get('status', 'unknown')
    result = j.get('result', {})
    
    # Extract key info from result
    if isinstance(result, dict):
        if 'files' in result:
            info = f"{len(result['files'])} files"
        elif 'ok' in result:
            info = f"ok={result['ok']}"
        elif 'error' in result:
            info = f"ERROR: {result['error'][:50]}"
        else:
            info = str(result)[:50]
    else:
        info = str(result)[:50]
    
    print(f"{j['id'][:12]} | {kind:20s} | {status:10s} | {info}")
