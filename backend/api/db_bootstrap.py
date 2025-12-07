"""Database bootstrap for adding ApiKey quota columns to existing databases"""
from sqlalchemy import inspect, text
from backend.database import engine


def ensure_apikey_quota_columns():
    """
    Add monthly_call_limit, calls_used, and cycle_start columns to api_keys table if missing.
    Safe for both new and existing databases.
    """
    with engine.begin() as conn:
        insp = inspect(conn)
        
        # Check if table exists
        if 'api_keys' not in insp.get_table_names():
            # Table doesn't exist yet, skip migration
            return
        
        cols = {c['name'] for c in insp.get_columns('api_keys')}
        add = []
        
        if 'monthly_call_limit' not in cols:
            add.append("ADD COLUMN monthly_call_limit INTEGER NOT NULL DEFAULT 10000")
        if 'calls_used' not in cols:
            add.append("ADD COLUMN calls_used INTEGER NOT NULL DEFAULT 0")
        if 'cycle_start' not in cols:
            add.append("ADD COLUMN cycle_start TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")
        
        for stmt in add:
            conn.execute(text(f"ALTER TABLE api_keys {stmt}"))
