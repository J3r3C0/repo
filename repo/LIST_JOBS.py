import sqlite3
import json

def list_recent_jobs():
    conn = sqlite3.connect('data/sheratan.db')
    cur = conn.cursor()
    cur.execute('SELECT id, status, payload, created_at FROM jobs ORDER BY created_at DESC LIMIT 5')
    for row in cur.fetchall():
        try:
            kind = json.loads(row[2]).get('kind')
        except:
            kind = 'N/A'
        print(f"ID: {row[0][:8]} | Status: {row[1]} | Kind: {kind} | Created: {row[3]}")
    conn.close()

if __name__ == "__main__":
    list_recent_jobs()
