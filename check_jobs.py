import sqlite3
conn = sqlite3.connect('data/sheratan.db')
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, status, updated_at FROM jobs ORDER BY updated_at DESC LIMIT 20").fetchall()
for r in rows:
    print(f"{r['id']} | {r['status']} | {r['updated_at']}")
