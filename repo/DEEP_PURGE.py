import sqlite3
import os
import shutil

DB_PATH = 'data/sheratan.db'
CHAINS_DIR = 'data/chains'

def purge():
    print(f"Connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # List of tables to clear
    tables = [
        'jobs', 'tasks', 'missions', 'chain_specs', 'chains', 
        'sync_queue', 'decision_trace', 'mesh_workers'
    ]
    
    for table in tables:
        try:
            cur.execute(f"DELETE FROM {table}")
            print(f"Purged table: {table}")
        except sqlite3.OperationalError as e:
            print(f"Could not purge table {table}: {e}")
            
    conn.commit()
    conn.close()
    
    # Clear chain files
    if os.path.exists(CHAINS_DIR):
        print(f"Clearing {CHAINS_DIR}...")
        for f in os.listdir(CHAINS_DIR):
            fpath = os.path.join(CHAINS_DIR, f)
            try:
                if os.path.isfile(fpath):
                    os.remove(fpath)
                elif os.path.isdir(fpath):
                    shutil.rmtree(fpath)
            except Exception as e:
                print(f"Error removing {fpath}: {e}")
                
    # Clear chain_index.json
    idx_path = 'data/chain_index.json'
    if os.path.exists(idx_path):
        os.remove(idx_path)
        print("Removed chain_index.json")

if __name__ == "__main__":
    purge()
    print("DONE")
