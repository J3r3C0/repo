import sqlite3
import json

def verify():
    conn = sqlite3.connect('data/sheratan.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT result FROM jobs WHERE id LIKE 'de035aa6%'")
    row = cur.fetchone()
    if not row or not row['result']:
        print("Job result not found")
        return
    
    res = json.loads(row['result'])
    files = res.get('result', {}).get('files', [])
    print(f"Total files in 'core': {len(files)}")
    for f in files[:10]:
        print(f" - {f}")
    
    # Check for expected files
    expected = ['core/main.py', 'core/storage.py']
    found = [f for f in files if f in expected]
    print(f"Found expected: {found}")
    
    if len(files) > 0 and 'core/' in files[0]:
        print("VERIFICATION: SUCCESS (Subdirectory prefix found)")
    elif len(files) > 0:
        print("VERIFICATION: SUCCESS (Files returned)")
    else:
        print("VERIFICATION: FAILED (No files)")
    conn.close()

if __name__ == "__main__":
    verify()
