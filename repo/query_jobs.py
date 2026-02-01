import sqlite3
import json
import sys

def query_job(partial_id):
    conn = sqlite3.connect('data/sheratan.db')
    cur = conn.cursor()
    cur.execute("SELECT id, status, payload, result FROM jobs WHERE id LIKE ?", (f"{partial_id}%",))
    rows = cur.fetchall()
    if not rows:
        print(f"No job found starting with {partial_id}")
        return
    
    for row in rows:
        jid, status, payload, result = row
        p_json = {}
        try:
            p_json = json.loads(payload)
        except: pass
        kind = p_json.get("kind") or p_json.get("type") or "unknown"
        
        print(f"=== JOB: {jid} ===")
        print(f"Kind: {kind}")
        print(f"Status: {status}")
        try:
            print("Payload:", json.dumps(json.loads(payload), indent=2)[:500], "...")
        except:
            print("Payload (raw):", payload[:200])
        try:
            print("Result:", json.dumps(json.loads(result), indent=2))
        except:
            print("Result (raw):", result)
        print("-" * 20)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query_job(sys.argv[1])
    else:
        # Query for both IDs from screenshot
        print("Searching for ae971c55...")
        query_job("ae971c55")
        print("\nSearching for 9c85dfbc...")
        query_job("9c85dfbc")
