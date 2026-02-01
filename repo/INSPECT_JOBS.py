import sqlite3
import json

def inspect():
    conn = sqlite3.connect('data/sheratan.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('SELECT id, status, payload, created_at FROM jobs ORDER BY created_at DESC LIMIT 10')
    for row in cur.fetchall():
        try:
            payload = json.loads(row['payload'])
            hint = payload.get('_chain_hint', {})
            depth = hint.get('depth', 'N/A')
            role = hint.get('role', 'N/A')
            kind = payload.get('kind', 'N/A')
            print(f"ID: {row['id'][:8]} | Status: {row['status']:10} | Kind: {kind:12} | Depth: {depth} | Role: {role}")
        except Exception as e:
            print(f"ID: {row['id'][:8]} | Error: {e}")
    conn.close()

if __name__ == "__main__":
    inspect()
