import sqlite3
import json
from core.job_chain_manager import JobChainManager
from core.chain_index import ChainIndex
from core import storage
from pathlib import Path

# Setup Manager
DATA_DIR = Path('data')
chain_dir = DATA_DIR / "chains"
chain_index_path = DATA_DIR / "chain_index.json"
chain_index = ChainIndex(str(chain_index_path))

manager = JobChainManager(
    chain_dir=str(chain_dir),
    chain_index=chain_index,
    storage=storage,
    agent_plan_kind="agent_plan"
)

def recover():
    conn = sqlite3.connect('data/sheratan.db')
    cur = conn.cursor()
    
    # 1. Find all completed jobs with chain hints
    cur.execute("""
        SELECT jobs.id, result 
        FROM jobs, json_each(payload) 
        WHERE json_each.key = '_chain_hint' 
          AND status = 'completed'
    """)
    jobs = cur.fetchall()
    
    print(f"Found {len(jobs)} completed jobs in chains. Ticking manager...")
    
    for jid, result_str in jobs:
        try:
            result = json.loads(result_str)
            print(f"  Ticking job {jid[:8]}...")
            manager.on_job_complete(job_id=jid, result=result)
        except Exception as e:
            print(f"  Error ticking job {jid}: {e}")
            
    conn.close()

if __name__ == "__main__":
    recover()
