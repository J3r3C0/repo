import sqlite3
import json

DB_PATH = 'data/sheratan.db'

def debug_query():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check all jobs with chain hints
    print("\nAll jobs with chain hints in DB:")
    cur.execute(
        """
        SELECT jobs.id, status, json_extract(json_each.value, '$.chain_id') 
        FROM jobs, json_each(payload) 
        WHERE json_each.key = '_chain_hint'
        """
    )
    rows = cur.fetchall()
    if not rows:
        print("No jobs with chain hints found.")
        return

    for r in rows:
        print(f"  {r[0][:8]} | status: {r[1]} | chain_id: {r[2][:8] if r[2] else 'None'}")
    
    # Use the first chain_id found
    chain_id = rows[0][2]
    print(f"\nTesting count_active_chain_activity for Chain ID: {chain_id}")
    
    # Test the spec count
    spec_count = cur.execute(
        "SELECT COUNT(*) FROM chain_specs WHERE chain_id=? AND status='pending'",
        (chain_id,)
    ).fetchone()[0]
    print(f"Spec Count (pending): {spec_count}")
    
    # Test the fixed job count query
    job_count = cur.execute(
        """
        SELECT COUNT(*) FROM jobs 
        WHERE status NOT IN ('completed', 'failed')
          AND id IN (
            SELECT jobs.id FROM jobs, json_each(payload) 
            WHERE json_each.key = '_chain_hint' 
              AND json_extract(json_each.value, '$.chain_id') = ?
          )
        """,
        (chain_id,)
    ).fetchone()[0]
    print(f"Job Count (active): {job_count}")
    
    print(f"Total Active: {spec_count + job_count}")
            
    conn.close()

if __name__ == "__main__":
    debug_query()
