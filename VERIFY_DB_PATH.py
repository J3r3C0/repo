from core.config import DB_PATH
import os
print(f"DB_PATH_ABS: {os.path.abspath(DB_PATH)}")
print(f"DB_EXISTS: {os.path.exists(DB_PATH)}")
