#!/usr/bin/env python3
"""
QUNIX QUICK FIX - Add missing columns to command_registry
Fixes: sqlite3.OperationalError: no such column: gate_name
"""

import sqlite3
import sys
from pathlib import Path

def quick_fix(db_path):
    print(f"\n🔧 QUNIX Quick Fix for {db_path}\n")
    
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    
    # Get current columns
    c.execute("PRAGMA table_info(command_registry)")
    existing_cols = {row[1] for row in c.fetchall()}
    
    print("Current columns in command_registry:")
    for col in sorted(existing_cols):
        print(f"  ✓ {col}")
    
    print("\nAdding missing columns...")
    
    # Add missing columns
    columns_to_add = {
        'gate_name': 'TEXT',
        'cmd_description': 'TEXT', 
        'cmd_requires_qubits': 'INTEGER DEFAULT 0',
        'cmd_enabled': 'INTEGER DEFAULT 1',
        'cmd_category': "TEXT DEFAULT 'SYSTEM'",
        'cmd_opcode': 'BLOB',
        'cmd_use_count': 'INTEGER DEFAULT 0',
        'cmd_last_used': 'REAL',
    }
    
    added = 0
    for col_name, col_def in columns_to_add.items():
        if col_name not in existing_cols:
            try:
                c.execute(f"ALTER TABLE command_registry ADD COLUMN {col_name} {col_def}")
                print(f"  ✓ Added: {col_name}")
                added += 1
            except sqlite3.OperationalError as e:
                print(f"  ⚠ Failed to add {col_name}: {e}")
        else:
            print(f"  ⏭ Already exists: {col_name}")
    
    # Create essential tables if missing
    print("\nCreating essential tables...")
    
    # command_handlers
    c.execute("""
        CREATE TABLE IF NOT EXISTS command_handlers (
            handler_id INTEGER PRIMARY KEY AUTOINCREMENT,
            cmd_id INTEGER NOT NULL,
            handler_type TEXT NOT NULL,
            qasm_code TEXT,
            sql_query TEXT,
            python_code TEXT,
            method_name TEXT,
            context_map TEXT,
            result_formatter TEXT,
            priority INTEGER DEFAULT 100,
            enabled INTEGER DEFAULT 1
        )
    """)
    print("  ✓ command_handlers")
    
    # quantum_command_circuits
    c.execute("""
        CREATE TABLE IF NOT EXISTS quantum_command_circuits (
            circuit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            cmd_name TEXT NOT NULL,
            circuit_name TEXT,
            num_qubits INTEGER NOT NULL,
            qasm_code TEXT NOT NULL
        )
    """)
    print("  ✓ quantum_command_circuits")
    
    # cpu_qubit_allocator
    c.execute("""
        CREATE TABLE IF NOT EXISTS cpu_qubit_allocator (
            qubit_id INTEGER PRIMARY KEY,
            allocated INTEGER DEFAULT 0,
            allocated_to_pid INTEGER,
            allocation_time REAL,
            usage_count INTEGER DEFAULT 0
        )
    """)
    print("  ✓ cpu_qubit_allocator")
    
    # Populate cpu_qubit_allocator if empty
    c.execute("SELECT COUNT(*) FROM cpu_qubit_allocator")
    if c.fetchone()[0] == 0:
        try:
            c.execute("INSERT INTO cpu_qubit_allocator (qubit_id) SELECT i FROM q")
            c.execute("SELECT COUNT(*) FROM cpu_qubit_allocator")
            count = c.fetchone()[0]
            print(f"  ✓ Populated with {count:,} qubits from q table")
        except:
            print(f"  ⚠ Could not populate cpu_qubit_allocator")
    
    # Update NULL values
    print("\nUpdating NULL values...")
    c.execute("""
        UPDATE command_registry 
        SET cmd_enabled = 1 
        WHERE cmd_enabled IS NULL
    """)
    c.execute("""
        UPDATE command_registry 
        SET cmd_category = 'SYSTEM' 
        WHERE cmd_category IS NULL
    """)
    c.execute("""
        UPDATE command_registry 
        SET cmd_requires_qubits = 0 
        WHERE cmd_requires_qubits IS NULL
    """)
    
    conn.commit()
    
    # Verify fix
    print("\nVerifying fix...")
    try:
        c.execute("""
            SELECT cmd_id, cmd_name, cmd_opcode, cmd_category, 
                   cmd_requires_qubits, gate_name
            FROM command_registry 
            WHERE cmd_name = 'help'
        """)
        row = c.fetchone()
        if row:
            print(f"  ✓ Query works! Found 'help' command (id={row[0]})")
        else:
            print(f"  ⚠ Query works but 'help' not found")
        
        # Count enabled commands
        c.execute("SELECT COUNT(*) FROM command_registry WHERE cmd_enabled = 1")
        count = c.fetchone()[0]
        print(f"  ✓ {count} enabled commands in registry")
        
    except sqlite3.OperationalError as e:
        print(f"  ✗ Still broken: {e}")
        conn.close()
        return False
    
    conn.close()
    
    print(f"\n✅ FIX COMPLETE!\n")
    print(f"Added {added} missing columns")
    print(f"Database is now compatible with qunix_db_executor.py\n")
    print(f"Try running: python qunix_cpu.py --db {db_path}\n")
    
    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("\nUsage: python qunix_quick_fix.py <database_path>\n")
        sys.exit(1)
    
    db_path = Path(sys.argv[1])
    if not db_path.exists():
        print(f"\n✗ Database not found: {db_path}\n")
        sys.exit(1)
    
    success = quick_fix(db_path)
    sys.exit(0 if success else 1)