# repo/core/database.py
import sqlite3
import json
from contextlib import contextmanager
from core.config import DB_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()
    
    # Missions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS missions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            user_id TEXT NOT NULL,
            status TEXT DEFAULT 'planned',
            metadata TEXT DEFAULT '{}',
            tags TEXT DEFAULT '[]',
            created_at TEXT NOT NULL
        )
    """)
    
    # Tasks
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            mission_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            kind TEXT NOT NULL,
            params TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (mission_id) REFERENCES missions (id) ON DELETE CASCADE
        )
    """)
    
    # Jobs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            payload TEXT DEFAULT '{}',
            status TEXT DEFAULT 'pending',
            result TEXT,
            retry_count INTEGER DEFAULT 0,
            priority TEXT DEFAULT 'normal',
            timeout_seconds INTEGER DEFAULT 300,
            depends_on TEXT DEFAULT '[]',
            idempotency_key TEXT UNIQUE,
            idempotency_hash TEXT,
            completed_result TEXT,
            idempotency_first_seen_utc TEXT,
            meta TEXT DEFAULT '{}',
            result_hash TEXT,
            result_hash_alg TEXT DEFAULT 'sha256',
            result_canonical TEXT,
            lease_owner TEXT,
            lease_until_utc TEXT,
            next_retry_utc TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
        )
    """)
    
    # Chain Context
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chain_context (
            chain_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'running',
            limits_json TEXT NOT NULL,
            artifacts_json TEXT NOT NULL,
            error_json TEXT,
            needs_tick INTEGER NOT NULL DEFAULT 0,
            last_tick_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    # Chain Specs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chain_specs (
            spec_id TEXT PRIMARY KEY,
            chain_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            root_job_id TEXT NOT NULL,
            parent_job_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            params_json TEXT NOT NULL,
            resolved_params_json TEXT,
            resolved INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            dedupe_key TEXT NOT NULL,
            dispatched_job_id TEXT,
            claim_id TEXT,
            claimed_until TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(chain_id, dedupe_key)
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chain_specs_chain_status ON chain_specs(chain_id, status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chain_specs_claimed ON chain_specs(chain_id, status, claimed_until)")

    # Rate Limit
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rate_limit_config (
            source TEXT PRIMARY KEY,
            max_jobs_per_minute INTEGER NOT NULL,
            max_concurrent_jobs INTEGER NOT NULL,
            current_count INTEGER DEFAULT 0,
            window_start TEXT NOT NULL
        )
    """)
    
    # Hosts (Attestation)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hosts (
            id TEXT PRIMARY KEY,
            status TEXT,
            health TEXT DEFAULT 'GREEN',
            last_seen TEXT,
            attestation_json TEXT DEFAULT '{}',
            metadata_json TEXT DEFAULT '{}',
            policy_state TEXT NOT NULL DEFAULT 'NORMAL',
            policy_reason TEXT,
            policy_until_utc TEXT,
            policy_hits INTEGER NOT NULL DEFAULT 0,
            policy_updated_utc TEXT,
            policy_by TEXT,
            public_key TEXT,
            key_first_seen_utc TEXT
        )
    """)

    conn.commit()
    conn.close()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
