#!/usr/bin/env python3
"""
Fix ALL tables that need cmd_id columns
"""

import sqlite3
import time

DB_PATH = "/home/Shemshallah/qunix_leech.db"

def fix_table(conn, table_name, new_schema, indexes=None):
    """Drop and recreate a table with new schema"""
    c = conn.cursor()
    
    # Check if table exists
    c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    if c.fetchone():
        c.execute(f"SELECT COUNT(*) FROM {table_name}")
        old_count = c.fetchone()[0]
        c.execute(f"DROP TABLE {table_name}")
        print(f"  Dropped {table_name} ({old_count} rows)")
    else:
        print(f"  {table_name} didn't exist")
    
    # Create new table
    c.execute(new_schema)
    print(f"  Created {table_name}")
    
    # Create indexes
    if indexes:
        for idx in indexes:
            c.execute(idx)
        print(f"  Created {len(indexes)} indexes")

def main():
    print("=" * 60)
    print("FIXING ALL TABLES WITH cmd_id COLUMNS")
    print("=" * 60)
    print(f"Database: {DB_PATH}")
    print()
    
    conn = sqlite3.connect(DB_PATH)
    
    # 1. command_flags
    print("1. Fixing command_flags...")
    fix_table(conn, 'command_flags', """
        CREATE TABLE command_flags (
            flag_id INTEGER PRIMARY KEY AUTOINCREMENT,
            cmd_id INTEGER NOT NULL,
            flag_short CHAR(1),
            flag_long TEXT,
            flag_bit INTEGER NOT NULL DEFAULT 0,
            flag_type TEXT DEFAULT 'BOOLEAN',
            value_type TEXT DEFAULT 'STRING',
            default_value TEXT,
            flag_description TEXT,
            flag_example TEXT,
            flag_opcode_modifier INTEGER DEFAULT 0,
            flag_group TEXT,
            mutually_exclusive TEXT,
            enabled INTEGER DEFAULT 1,
            created_at REAL DEFAULT (strftime('%s', 'now')),
            UNIQUE(cmd_id, flag_short),
            UNIQUE(cmd_id, flag_long),
            CHECK(flag_short IS NOT NULL OR flag_long IS NOT NULL),
            CHECK(flag_bit BETWEEN 0 AND 31)
        )
    """, [
        "CREATE INDEX idx_flags_cmd ON command_flags(cmd_id)",
        "CREATE INDEX idx_flags_short ON command_flags(flag_short)",
        "CREATE INDEX idx_flags_long ON command_flags(flag_long)",
        "CREATE INDEX idx_flags_enabled ON command_flags(enabled)"
    ])
    
    # 2. command_arguments
    print("2. Fixing command_arguments...")
    fix_table(conn, 'command_arguments', """
        CREATE TABLE command_arguments (
            arg_id INTEGER PRIMARY KEY AUTOINCREMENT,
            cmd_id INTEGER NOT NULL,
            arg_position INTEGER NOT NULL,
            arg_name TEXT NOT NULL,
            arg_type TEXT DEFAULT 'STRING',
            required INTEGER DEFAULT 1,
            default_value TEXT,
            validation_regex TEXT,
            validation_min REAL,
            validation_max REAL,
            validation_enum TEXT,
            arg_description TEXT,
            arg_example TEXT,
            transform_func TEXT,
            created_at REAL DEFAULT (strftime('%s', 'now')),
            UNIQUE(cmd_id, arg_position),
            CHECK(arg_position >= 0)
        )
    """, [
        "CREATE INDEX idx_args_cmd ON command_arguments(cmd_id)",
        "CREATE INDEX idx_args_position ON command_arguments(cmd_id, arg_position)"
    ])
    
    # 3. command_handlers
    print("3. Fixing command_handlers...")
    fix_table(conn, 'command_handlers', """
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
            avg_execution_ms REAL DEFAULT 0.0,
            CHECK(handler_type IN ('QUANTUM_CIRCUIT', 'SQL_QUERY', 'PYTHON_METHOD', 
                                   'BUILTIN', 'FILESYSTEM', 'NETWORK', 'TEXT_PROCESSOR', 
                                   'ARCHIVE', 'SYSTEM', 'ALIAS', 'COMPOSITE', 'EXTERNAL'))
        )
    """, [
        "CREATE INDEX idx_handlers_cmd ON command_handlers(cmd_id)",
        "CREATE INDEX idx_handlers_type ON command_handlers(handler_type)",
        "CREATE INDEX idx_handlers_priority ON command_handlers(cmd_id, priority DESC)",
        "CREATE INDEX idx_handlers_enabled ON command_handlers(enabled)"
    ])
    
    # 4. command_aliases
    print("4. Fixing command_aliases...")
    fix_table(conn, 'command_aliases', """
        CREATE TABLE command_aliases (
            alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
            alias_name TEXT UNIQUE NOT NULL,
            target_cmd_id INTEGER NOT NULL,
            alias_args TEXT,
            enabled INTEGER DEFAULT 1,
            created_at REAL DEFAULT (strftime('%s', 'now'))
        )
    """, [
        "CREATE INDEX idx_aliases_name ON command_aliases(alias_name)",
        "CREATE INDEX idx_aliases_target ON command_aliases(target_cmd_id)"
    ])
    
    # 5. handler_dependencies
    print("5. Fixing handler_dependencies...")
    fix_table(conn, 'handler_dependencies', """
        CREATE TABLE handler_dependencies (
            dep_id INTEGER PRIMARY KEY AUTOINCREMENT,
            handler_id INTEGER NOT NULL,
            depends_on_handler_id INTEGER NOT NULL,
            execution_order INTEGER DEFAULT 0,
            pass_output INTEGER DEFAULT 1,
            condition TEXT,
            UNIQUE(handler_id, depends_on_handler_id)
        )
    """)
    
    # 6. command_execution_log
    print("6. Fixing command_execution_log...")
    fix_table(conn, 'command_execution_log', """
        CREATE TABLE command_execution_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            cmd_id INTEGER,
            cmd_line TEXT,
            handler_id INTEGER,
            handler_type TEXT,
            parsed_args TEXT,
            parsed_flags TEXT,
            context_data TEXT,
            result_data TEXT,
            error_message TEXT,
            execution_time_ms REAL,
            qubit_ids TEXT,
            success INTEGER DEFAULT 1,
            timestamp REAL DEFAULT (strftime('%s', 'now'))
        )
    """, [
        "CREATE INDEX idx_exec_log_session ON command_execution_log(session_id)",
        "CREATE INDEX idx_exec_log_cmd ON command_execution_log(cmd_id)",
        "CREATE INDEX idx_exec_log_time ON command_execution_log(timestamp)"
    ])
    
    # 7. handler_execution_stats
    print("7. Fixing handler_execution_stats...")
    fix_table(conn, 'handler_execution_stats', """
        CREATE TABLE handler_execution_stats (
            stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            handler_id INTEGER,
            execution_time_ms REAL,
            memory_used_bytes INTEGER,
            qubits_used INTEGER,
            success INTEGER,
            error_message TEXT,
            timestamp REAL DEFAULT (strftime('%s', 'now'))
        )
    """, [
        "CREATE INDEX idx_handler_stats ON handler_execution_stats(handler_id, timestamp)"
    ])
    
    # 8. command_binary_cache
    print("8. Fixing command_binary_cache...")
    fix_table(conn, 'command_binary_cache', """
        CREATE TABLE command_binary_cache (
            cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
            cmd_id INTEGER,
            flags_bitfield INTEGER DEFAULT 0,
            args_hash TEXT,
            binary_code BLOB,
            qasm_compiled TEXT,
            circuit_depth INTEGER,
            gate_count INTEGER,
            created_at REAL DEFAULT (strftime('%s', 'now')),
            last_used REAL,
            use_count INTEGER DEFAULT 0,
            UNIQUE(cmd_id, flags_bitfield, args_hash)
        )
    """, [
        "CREATE INDEX idx_binary_cache_lookup ON command_binary_cache(cmd_id, flags_bitfield, args_hash)"
    ])
    
    # 9. system_python_modules
    print("9. Fixing system_python_modules...")
    fix_table(conn, 'system_python_modules', """
        CREATE TABLE system_python_modules (
            module_id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_name TEXT UNIQUE NOT NULL,
            module_code TEXT NOT NULL,
            module_description TEXT,
            module_version TEXT DEFAULT '1.0.0',
            dependencies TEXT,
            created_at REAL DEFAULT (strftime('%s', 'now')),
            updated_at REAL
        )
    """, [
        "CREATE INDEX idx_modules_name ON system_python_modules(module_name)"
    ])
    
    # 10. quantum_circuit_templates
    print("10. Fixing quantum_circuit_templates...")
    fix_table(conn, 'quantum_circuit_templates', """
        CREATE TABLE quantum_circuit_templates (
            template_id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_name TEXT UNIQUE NOT NULL,
            template_category TEXT DEFAULT 'gate',
            qasm_template TEXT NOT NULL,
            num_qubits INTEGER NOT NULL,
            num_parameters INTEGER DEFAULT 0,
            parameter_names TEXT,
            parameter_defaults TEXT,
            description TEXT,
            complexity_class TEXT DEFAULT 'O(1)',
            created_at REAL DEFAULT (strftime('%s', 'now'))
        )
    """, [
        "CREATE INDEX idx_circuit_templates_name ON quantum_circuit_templates(template_name)",
        "CREATE INDEX idx_circuit_templates_cat ON quantum_circuit_templates(template_category)"
    ])
    
    # Commit all changes
    conn.commit()
    conn.close()
    
    print()
    print("=" * 60)
    print("✓ ALL TABLES FIXED!")
    print("=" * 60)
    print()
    print("Now run: python3 db_patch_v8_fixed.py")

if __name__ == "__main__":
    main()
