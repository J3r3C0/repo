import sqlite3
import os
from pathlib import Path

def check_db(path):
    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM missions")
        count = cursor.fetchone()[0]
        cursor.execute("SELECT id, title, created_at FROM missions ORDER BY created_at DESC LIMIT 1")
        last = cursor.fetchone()
        print(f"DB: {path} | Missions: {count} | Last: {last}")
        conn.close()
    except Exception as e:
        print(f"DB: {path} | Error: {e}")

root = Path("c:/neuer ordner für allgemein github pulls")
for p in root.rglob("*.db"):
    check_db(str(p))
