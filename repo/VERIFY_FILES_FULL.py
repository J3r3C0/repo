import sqlite3
import json

def verify():
    conn = sqlite3.connect('data/sheratan.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT result FROM jobs WHERE id LIKE '02c7d33c%'")
    row = cur.fetchone()
    if not row or not row['result']:
        print("Job result not found")
        return
    
    res = json.loads(row['result'])
    files = res.get('result', {}).get('files', [])
    print(f"Total files in result: {len(files)}")
    for f in files:
        print(f" - {f}")
    
    conn.close()

if __name__ == "__main__":
    verify()
