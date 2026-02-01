import sqlite3
import json

def list_jobs():
    conn = sqlite3.connect('data/sheratan.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, status, payload, created_at FROM jobs ORDER BY created_at DESC")
    for row in cur.fetchall():
        try:
            payload = json.loads(row['payload'])
            if payload.get('kind') == 'list_files':
                params = payload.get('params')
                print(f"ID: {row['id'][:8]} | Status: {row['status']:10} | Created: {row['created_at']} | Params: {params}")
        except:
            pass
    conn.close()

if __name__ == "__main__":
    list_jobs()
