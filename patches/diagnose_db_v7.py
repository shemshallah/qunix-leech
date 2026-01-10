#!/usr/bin/env python3
"""
QUNIX Database Diagnostic Tool
Outputs detailed log to /home/Shemshallah/db_diagnostic.log
"""

import sqlite3
import os
import sys
from datetime import datetime

DB_PATH = "/home/Shemshallah/qunix_leech.db"
LOG_PATH = "/home/Shemshallah/db_diagnostic.log"

def log(msg):
    """Write to both console and log file"""
    print(msg)
    with open(LOG_PATH, 'a') as f:
        f.write(msg + '\n')

def main():
    # Clear/create log file
    with open(LOG_PATH, 'w') as f:
        f.write(f"=== QUNIX DB DIAGNOSTIC ===\n")
        f.write(f"Time: {datetime.now()}\n")
        f.write(f"DB Path: {DB_PATH}\n\n")
    
    log(f"Database: {DB_PATH}")
    log(f"Exists: {os.path.exists(DB_PATH)}")
    
    if not os.path.exists(DB_PATH):
        log("ERROR: Database file does not exist!")
        return
    
    log(f"File size: {os.path.getsize(DB_PATH)} bytes")
    log("")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 1. List ALL tables
        log("=" * 60)
        log("ALL TABLES IN DATABASE:")
        log("=" * 60)
        c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in c.fetchall()]
        for t in tables:
            c.execute(f"SELECT COUNT(*) FROM [{t}]")
            count = c.fetchone()[0]
            log(f"  {t}: {count} rows")
        log("")
        
        # 2. Check command_registry specifically
        log("=" * 60)
        log("COMMAND_REGISTRY ANALYSIS:")
        log("=" * 60)
        
        if 'command_registry' not in tables:
            log("  TABLE DOES NOT EXIST!")
        else:
            # Get schema
            c.execute("PRAGMA table_info(command_registry)")
            cols = c.fetchall()
            log(f"Columns ({len(cols)}):")
            col_names = []
            for col in cols:
                pk = " [PRIMARY KEY]" if col[5] else ""
                nn = " NOT NULL" if col[3] else ""
                log(f"  {col[0]:2d}. {col[1]:30s} {col[2]:15s}{pk}{nn}")
                col_names.append(col[1])
            
            log("")
            log(f"Has 'cmd_id': {'YES' if 'cmd_id' in col_names else 'NO <<<< PROBLEM!'}")
            log("")
            
            # Sample data
            log("Sample rows (first 5):")
            c.execute("SELECT * FROM command_registry LIMIT 5")
            rows = c.fetchall()
            for i, row in enumerate(rows):
                log(f"  Row {i}: {row}")
        
        log("")
        
        # 3. Check other related tables
        log("=" * 60)
        log("RELATED TABLES CHECK:")
        log("=" * 60)
        
        related = ['command_flags', 'command_arguments', 'command_handlers', 
                   'command_aliases', 'command_execution_log']
        for table in related:
            if table in tables:
                c.execute(f"PRAGMA table_info({table})")
                cols = [row[1] for row in c.fetchall()]
                has_cmd_id = 'cmd_id' in cols
                c.execute(f"SELECT COUNT(*) FROM {table}")
                count = c.fetchone()[0]
                log(f"  {table}: {count} rows, has cmd_id: {has_cmd_id}")
            else:
                log(f"  {table}: DOES NOT EXIST")
        
        log("")
        
        # 4. Try the actual query that's failing
        log("=" * 60)
        log("TEST QUERIES:")
        log("=" * 60)
        
        test_queries = [
            ("SELECT cmd_id FROM command_registry LIMIT 1", "Get cmd_id"),
            ("SELECT cmd_name FROM command_registry LIMIT 1", "Get cmd_name"),
            ("SELECT * FROM command_registry LIMIT 1", "Get all columns"),
        ]
        
        for query, desc in test_queries:
            try:
                c.execute(query)
                result = c.fetchone()
                log(f"  ✓ {desc}: {result}")
            except Exception as e:
                log(f"  ✗ {desc}: ERROR - {e}")
        
        log("")
        
        # 5. Check views
        log("=" * 60)
        log("VIEWS:")
        log("=" * 60)
        c.execute("SELECT name FROM sqlite_master WHERE type='view'")
        views = [row[0] for row in c.fetchall()]
        if views:
            for v in views:
                log(f"  {v}")
        else:
            log("  No views defined")
        
        log("")
        
        # 6. Attempt migration fix
        log("=" * 60)
        log("ATTEMPTING FIX:")
        log("=" * 60)
        
        if 'command_registry' in tables and 'cmd_id' not in col_names:
            log("command_registry exists but NO cmd_id - attempting rebuild...")
            
            # Backup data
            c.execute("SELECT * FROM command_registry")
            old_data = c.fetchall()
            log(f"  Backed up {len(old_data)} rows")
            
            # Get old column names
            c.execute("PRAGMA table_info(command_registry)")
            old_cols = [row[1] for row in c.fetchall()]
            log(f"  Old columns: {old_cols}")
            
            # Drop old table
            c.execute("DROP TABLE command_registry")
            log("  Dropped old table")
            
            # Create new table
            c.execute("""
                CREATE TABLE command_registry (
                    cmd_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cmd_name TEXT UNIQUE NOT NULL,
                    cmd_opcode INTEGER UNIQUE,
                    cmd_category TEXT DEFAULT 'general',
                    cmd_description TEXT,
                    cmd_usage TEXT,
                    cmd_requires_qubits INTEGER DEFAULT 0,
                    cmd_quantum_advantage REAL DEFAULT 0.0,
                    cmd_enabled INTEGER DEFAULT 1,
                    cmd_use_count INTEGER DEFAULT 0,
                    cmd_last_used REAL,
                    cmd_created_at REAL DEFAULT (strftime('%s', 'now')),
                    cmd_binary_template BLOB,
                    cmd_min_args INTEGER DEFAULT 0,
                    cmd_max_args INTEGER DEFAULT -1,
                    cmd_execution_timeout REAL DEFAULT 30.0
                )
            """)
            log("  Created new table with cmd_id")
            
            # Migrate data
            migrated = 0
            for row in old_data:
                row_dict = dict(zip(old_cols, row))
                if 'cmd_name' in row_dict and row_dict['cmd_name']:
                    # Only migrate columns that exist in both
                    new_cols = ['cmd_name', 'cmd_opcode', 'cmd_category', 'cmd_description',
                               'cmd_usage', 'cmd_requires_qubits', 'cmd_quantum_advantage',
                               'cmd_enabled', 'cmd_use_count', 'cmd_last_used']
                    
                    ins_cols = []
                    ins_vals = []
                    for nc in new_cols:
                        if nc in row_dict and row_dict[nc] is not None:
                            ins_cols.append(nc)
                            ins_vals.append(row_dict[nc])
                    
                    if ins_cols:
                        try:
                            placeholders = ','.join(['?' for _ in ins_vals])
                            c.execute(f"INSERT INTO command_registry ({','.join(ins_cols)}) VALUES ({placeholders})", ins_vals)
                            migrated += 1
                        except sqlite3.IntegrityError:
                            pass
            
            conn.commit()
            log(f"  Migrated {migrated} rows")
            
            # Verify
            c.execute("PRAGMA table_info(command_registry)")
            new_col_names = [row[1] for row in c.fetchall()]
            log(f"  New columns: {new_col_names}")
            log(f"  Has cmd_id now: {'cmd_id' in new_col_names}")
            
            c.execute("SELECT COUNT(*) FROM command_registry")
            log(f"  Total rows now: {c.fetchone()[0]}")
            
            log("")
            log("✓ FIX APPLIED - Run db_patch_v8_fixed.py again!")
        
        elif 'command_registry' not in tables:
            log("No command_registry table - patch should create it fresh")
        
        else:
            log("command_registry already has cmd_id - no fix needed")
            log("If still getting errors, the problem is elsewhere")
        
        conn.close()
        
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        import traceback
        log(traceback.format_exc())
    
    log("")
    log("=" * 60)
    log(f"Log saved to: {LOG_PATH}")
    log("=" * 60)

if __name__ == "__main__":
    main()
