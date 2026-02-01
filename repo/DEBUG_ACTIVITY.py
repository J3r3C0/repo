import sqlite3
import json

DB_PATH = 'data/sheratan.db'

def debug_activity():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Target Chain ID from previous index check
    chain_id = "bdb3b4bb-1187-489d-870c-e6c630d46b55"
    print(f"Analyzing Chain ID: {chain_id}")
    
    # 1. Spec count breakdown
    cur.execute("SELECT spec_id, status FROM chain_specs WHERE chain_id=?", (chain_id,))
    specs = cur.fetchall()
    print(f"\nSpecs ({len(specs)}):")
    for sid, status in specs:
        print(f"  {sid[:8]} | status: {status}")
        
    pending_specs = [s for s in specs if s[1] == 'pending']
    print(f"Pending Spec Count: {len(pending_specs)}")
    
    # 2. Job count breakdown
    cur.execute("""
        SELECT jobs.id, status, json_extract(json_each.value, '$.chain_id') 
        FROM jobs, json_each(payload) 
        WHERE json_each.key = '_chain_hint'
    """)
    jobs = cur.fetchall()
    print(f"\nJobs with Chain Hint ({len(jobs)}):")
    active_jobs = 0
    for jid, status, j_chain_id in jobs:
        if j_chain_id == chain_id:
            is_active = status not in ('completed', 'failed')
            if is_active: active_jobs += 1
            print(f"  {jid[:8]} | status: {status} | matches_chain: True | is_active: {is_active}")
        else:
            print(f"  {jid[:8]} | status: {status} | matches_chain: False (is {j_chain_id[:8]})")
            
    print(f"\nActive Job Count for this chain: {active_jobs}")
    print(f"TOTAL ACTIVE: {len(pending_specs) + active_jobs}")
    
    conn.close()

if __name__ == "__main__":
    debug_activity()
