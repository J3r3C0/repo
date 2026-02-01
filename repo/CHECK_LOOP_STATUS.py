import sqlite3
import json
import os

DB_PATH = 'data/sheratan.db'
LOG_PATH = 'core_stdout.log'

def check_status():
    print(f"--- DATABASE STATUS ---")
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check missions
    cur.execute("SELECT id, status FROM missions ORDER BY created_at DESC LIMIT 1")
    mission = cur.fetchone()
    if mission:
        print(f"Active Mission: {mission[0]} ({mission[1]})")
    
    # Check jobs
    print(f"\nLast 5 Jobs:")
    cur.execute("SELECT id, status, payload FROM jobs ORDER BY created_at DESC LIMIT 5")
    for row in cur.fetchall():
        try:
            kind = json.loads(row[2]).get('kind', 'N/A')
        except:
            kind = 'N/A'
        print(f"ID: {row[0][:8]} | Status: {row[1]} | Kind: {kind}")
        
    # Check chain specs
    print(f"\nActive Chain Specs (Pending/Dispatched):")
    cur.execute("SELECT spec_id, chain_id, status, kind FROM chain_specs WHERE status NOT IN ('done', 'failed')")
    for row in cur.fetchall():
        print(f"Spec: {row[0][:8]} | Chain: {row[1][:8]} | Status: {row[2]} | Kind: {row[3]}")
        
    # Check Chain Context
    print(f"\nChain Context Needs Tick:")
    cur.execute("SELECT chain_id, needs_tick, state FROM chain_context")
    for row in cur.fetchall():
        print(f"Chain: {row[0][:8]} | Needs Tick: {row[1]} | State: {row[2]}")
        
    conn.close()
    
    print(f"\n--- LOG SNIPPETS ---")
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[-20:]:
                if "Loop" in line or "on_job_complete" in line or "error" in line.lower():
                    print(line.strip())
    else:
        print(f"Error: {LOG_PATH} not found.")

if __name__ == "__main__":
    check_status()
