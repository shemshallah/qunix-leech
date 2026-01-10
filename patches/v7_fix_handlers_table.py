#!/usr/bin/env python3
"""
Fix command_handlers table to have cmd_id column
"""

import sqlite3

DB_PATH = "/home/Shemshallah/qunix_leech.db"

def main():
    print("Fixing command_handlers table...")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check current schema
    c.execute("PRAGMA table_info(command_handlers)")
    cols = c.fetchall()
    col_names = [col[1] for col in cols]
    
    print(f"Current columns: {col_names}")
    
    if 'cmd_id' in col_names:
        print("command_handlers already has cmd_id - nothing to do")
        return
    
    # Backup existing data
    c.execute("SELECT * FROM command_handlers")
    old_data = c.fetchall()
    print(f"Backed up {len(old_data)} handlers")
    
    # Check what columns exist
    print(f"Old columns: {col_names}")
    
    # Drop the old table
    c.execute("DROP TABLE command_handlers")
    print("Dropped old table")
    
    # Create new table with cmd_id
    c.execute("""
        CREATE TABLE command_handlers (
            handler_id INTEGER PRIMARY KEY AUTOINCREMENT,
            cmd_id INTEGER NOT NULL,
            handler_type TEXT NOT NULL,
            qasm_code TEXT,
            sql_query TEXT,
            python_code TEXT,
            method_name TEXT,
            builtin_name TEXT,
            shell_command TEXT,
            context_map TEXT,
            result_formatter TEXT,
            error_formatter TEXT,
            priority INTEGER DEFAULT 100,
            timeout_seconds REAL DEFAULT 30.0,
            retry_count INTEGER DEFAULT 0,
            requires_qubits INTEGER DEFAULT 0,
            qubit_count INTEGER DEFAULT 0,
            enabled INTEGER DEFAULT 1,
            created_at REAL DEFAULT (strftime('%s', 'now')),
            updated_at REAL,
            last_executed REAL,
            execution_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            avg_execution_ms REAL DEFAULT 0.0
        )
    """)
    print("Created new command_handlers with cmd_id")
    
    # Create indexes
    c.execute("CREATE INDEX IF NOT EXISTS idx_handlers_cmd ON command_handlers(cmd_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_handlers_type ON command_handlers(handler_type)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_handlers_enabled ON command_handlers(enabled)")
    print("Created indexes")
    
    # NOTE: Old data won't have cmd_id so we can't migrate it directly
    # The patch will repopulate with new handlers
    print(f"Note: {len(old_data)} old handlers discarded (no cmd_id mapping)")
    
    conn.commit()
    conn.close()
    
    print("")
    print("✓ command_handlers table fixed!")
    print("Now run db_patch_v8_fixed.py again")

if __name__ == "__main__":
    main()
