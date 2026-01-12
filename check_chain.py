import requests
jobs = requests.get('http://localhost:8001/api/jobs').json()
task_jobs = [j for j in jobs if j.get('task_id') == '98288416-5521-4373-b5b6-54a21c44c7b8']
for j in task_jobs:
    kind = j.get('payload', {}).get('kind', 'unknown')
    status = j.get('status')
    print(f"{j['id'][:12]} - {kind:20s} - {status}")
