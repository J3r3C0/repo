import sqlite3
import json

def inspect_job(jid_prefix):
    conn = sqlite3.connect('data/sheratan.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, status, payload, result FROM jobs WHERE id LIKE ?", (jid_prefix + '%',))
    row = cur.fetchone()
    if row:
        print(f"ID: {row['id']}")
        print(f"Status: {row['status']}")
        try:
            payload = json.loads(row['payload'])
            print(f"Payload Kind: {payload.get('kind')}")
            print(f"Payload Params: {payload.get('params')}")
        except:
            print("Payload: (raw) " + row['payload'])
        
        if row['result']:
            try:
                res = json.loads(row['result'])
                print(f"Result (keys): {list(res.keys()) if isinstance(res, dict) else type(res)}")
                if isinstance(res, dict) and 'ok' in res:
                    print(f"Result OK: {res['ok']}")
                print(f"Result Snippet: {str(res)[:1000]}")
            except:
                print("Result: (raw) " + row['result'])
        else:
            print("Result: None")
    else:
        print(f"Job {jid_prefix} not found")
    conn.close()

if __name__ == "__main__":
    import sys
    jid = sys.argv[1] if len(sys.argv) > 1 else 'ed021bb9'
    inspect_job(jid)
