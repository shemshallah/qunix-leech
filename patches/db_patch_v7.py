#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║                    QUNIX DATABASE PATCH v8.0.0-COMPLETE                       ║
║                Complete Database-Driven Execution System                       ║
║                                                                               ║
║  PART 1 OF 3: First 70 Command Handlers                                       ║
║                                                                               ║
║  This patch creates a fully database-native command execution system:         ║
║    • Safe schema migration with cmd_id support                                ║
║    • command_flags: All flag definitions (-l, --long, etc.)                   ║
║    • command_arguments: Argument parsing and validation                       ║
║    • command_handlers: Handler implementations (QUANTUM/SQL/PYTHON/etc.)     ║
║    • Complete execution chain linkages                                        ║
║                                                                               ║
║  EXECUTION CHAIN:                                                             ║
║    User Input → Parser → command_registry → command_flags →                   ║
║    command_arguments → command_handlers → Execute → Format → Output           ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import sqlite3
import struct
import json
import time
import sys
import os
from pathlib import Path
from datetime import datetime

VERSION = "8.0.0-COMPLETE-PART1"
DB_PATH = "/home/Shemshallah/qunix_leech.db"

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: SCHEMA DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

SCHEMA_PHASE1 = """
-- ═══════════════════════════════════════════════════════════════════════════
-- NOTE: command_registry is handled separately by migrate_command_registry()
-- This schema only creates the supporting tables
-- ═══════════════════════════════════════════════════════════════════════════

-- ═══════════════════════════════════════════════════════════════════════════
-- COMMAND FLAGS TABLE
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS command_flags (
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
);

CREATE INDEX IF NOT EXISTS idx_flags_cmd ON command_flags(cmd_id);
CREATE INDEX IF NOT EXISTS idx_flags_short ON command_flags(flag_short);
CREATE INDEX IF NOT EXISTS idx_flags_long ON command_flags(flag_long);
CREATE INDEX IF NOT EXISTS idx_flags_enabled ON command_flags(enabled);

-- ═══════════════════════════════════════════════════════════════════════════
-- COMMAND ARGUMENTS TABLE
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS command_arguments (
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
);

CREATE INDEX IF NOT EXISTS idx_args_cmd ON command_arguments(cmd_id);
CREATE INDEX IF NOT EXISTS idx_args_position ON command_arguments(cmd_id, arg_position);

-- ═══════════════════════════════════════════════════════════════════════════
-- COMMAND HANDLERS TABLE - THE CORE EXECUTION ENGINE
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS command_handlers (
    handler_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_id INTEGER NOT NULL,
    handler_type TEXT NOT NULL,
    
    -- Implementation fields (one or more populated based on type)
    qasm_code TEXT,
    sql_query TEXT,
    python_code TEXT,
    method_name TEXT,
    builtin_name TEXT,
    shell_command TEXT,
    
    -- Context and formatting
    context_map TEXT,
    result_formatter TEXT,
    error_formatter TEXT,
    
    -- Execution control
    priority INTEGER DEFAULT 100,
    timeout_seconds REAL DEFAULT 30.0,
    retry_count INTEGER DEFAULT 0,
    requires_qubits INTEGER DEFAULT 0,
    qubit_count INTEGER DEFAULT 0,
    
    -- State tracking
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
);

CREATE INDEX IF NOT EXISTS idx_handlers_cmd ON command_handlers(cmd_id);
CREATE INDEX IF NOT EXISTS idx_handlers_type ON command_handlers(handler_type);
CREATE INDEX IF NOT EXISTS idx_handlers_priority ON command_handlers(cmd_id, priority DESC);
CREATE INDEX IF NOT EXISTS idx_handlers_enabled ON command_handlers(enabled);

-- ═══════════════════════════════════════════════════════════════════════════
-- HANDLER DEPENDENCIES (for COMPOSITE handlers)
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS handler_dependencies (
    dep_id INTEGER PRIMARY KEY AUTOINCREMENT,
    handler_id INTEGER NOT NULL,
    depends_on_handler_id INTEGER NOT NULL,
    execution_order INTEGER DEFAULT 0,
    pass_output INTEGER DEFAULT 1,
    condition TEXT,
    FOREIGN KEY(handler_id) REFERENCES command_handlers(handler_id),
    FOREIGN KEY(depends_on_handler_id) REFERENCES command_handlers(handler_id),
    UNIQUE(handler_id, depends_on_handler_id)
);

-- ═══════════════════════════════════════════════════════════════════════════
-- COMMAND ALIASES
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS command_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alias_name TEXT UNIQUE NOT NULL,
    target_cmd_id INTEGER NOT NULL,
    alias_args TEXT,
    enabled INTEGER DEFAULT 1,
    created_at REAL DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_aliases_name ON command_aliases(alias_name);
CREATE INDEX IF NOT EXISTS idx_aliases_target ON command_aliases(target_cmd_id);

-- ═══════════════════════════════════════════════════════════════════════════
-- EXECUTION CHAIN LOGGING
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS command_execution_log (
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
);

CREATE INDEX IF NOT EXISTS idx_exec_log_session ON command_execution_log(session_id);
CREATE INDEX IF NOT EXISTS idx_exec_log_cmd ON command_execution_log(cmd_id);
CREATE INDEX IF NOT EXISTS idx_exec_log_time ON command_execution_log(timestamp);

-- ═══════════════════════════════════════════════════════════════════════════
-- HANDLER EXECUTION STATISTICS
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS handler_execution_stats (
    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    handler_id INTEGER,
    execution_time_ms REAL,
    memory_used_bytes INTEGER,
    qubits_used INTEGER,
    success INTEGER,
    error_message TEXT,
    timestamp REAL DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY(handler_id) REFERENCES command_handlers(handler_id)
);

CREATE INDEX IF NOT EXISTS idx_handler_stats ON handler_execution_stats(handler_id, timestamp);

-- ═══════════════════════════════════════════════════════════════════════════
-- BINARY COMMAND CACHE
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS command_binary_cache (
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
);

CREATE INDEX IF NOT EXISTS idx_binary_cache_lookup ON command_binary_cache(cmd_id, flags_bitfield, args_hash);

-- ═══════════════════════════════════════════════════════════════════════════
-- SYSTEM PYTHON MODULES (stored code)
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS system_python_modules (
    module_id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_name TEXT UNIQUE NOT NULL,
    module_code TEXT NOT NULL,
    module_description TEXT,
    module_version TEXT DEFAULT '1.0.0',
    dependencies TEXT,
    created_at REAL DEFAULT (strftime('%s', 'now')),
    updated_at REAL
);

CREATE INDEX IF NOT EXISTS idx_modules_name ON system_python_modules(module_name);

-- ═══════════════════════════════════════════════════════════════════════════
-- QUANTUM CIRCUIT TEMPLATES
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS quantum_circuit_templates (
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
);

CREATE INDEX IF NOT EXISTS idx_circuit_templates_name ON quantum_circuit_templates(template_name);
CREATE INDEX IF NOT EXISTS idx_circuit_templates_cat ON quantum_circuit_templates(template_category);
"""

# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA PHASE 2: VIEWS AND TRIGGERS (must run AFTER command_registry has cmd_id)
# ═══════════════════════════════════════════════════════════════════════════════

SCHEMA_VIEWS_TRIGGERS = """
-- ═══════════════════════════════════════════════════════════════════════════
-- VIEWS FOR DEBUGGING AND ANALYSIS
-- ═══════════════════════════════════════════════════════════════════════════

DROP VIEW IF EXISTS v_command_complete;
CREATE VIEW v_command_complete AS
SELECT 
    cr.cmd_id,
    cr.cmd_name,
    cr.cmd_opcode,
    cr.cmd_category,
    cr.cmd_description,
    cr.cmd_requires_qubits,
    cr.cmd_enabled,
    COUNT(DISTINCT cf.flag_id) as flag_count,
    COUNT(DISTINCT ca.arg_id) as arg_count,
    COUNT(DISTINCT ch.handler_id) as handler_count,
    GROUP_CONCAT(DISTINCT cf.flag_short) as flags_short,
    GROUP_CONCAT(DISTINCT cf.flag_long) as flags_long,
    MAX(ch.handler_type) as primary_handler_type,
    MAX(ch.priority) as max_priority
FROM command_registry cr
LEFT JOIN command_flags cf ON cr.cmd_id = cf.cmd_id AND cf.enabled = 1
LEFT JOIN command_arguments ca ON cr.cmd_id = ca.cmd_id
LEFT JOIN command_handlers ch ON cr.cmd_id = ch.cmd_id AND ch.enabled = 1
GROUP BY cr.cmd_id;

DROP VIEW IF EXISTS v_missing_handlers;
CREATE VIEW v_missing_handlers AS
SELECT cr.cmd_id, cr.cmd_name, cr.cmd_category
FROM command_registry cr
WHERE cr.cmd_enabled = 1 
AND cr.cmd_id NOT IN (SELECT DISTINCT cmd_id FROM command_handlers WHERE enabled = 1);

DROP VIEW IF EXISTS v_handler_stats;
CREATE VIEW v_handler_stats AS
SELECT 
    ch.handler_id,
    cr.cmd_name,
    ch.handler_type,
    ch.execution_count,
    ch.success_count,
    ch.error_count,
    CASE WHEN ch.execution_count > 0 
         THEN ROUND(100.0 * ch.success_count / ch.execution_count, 2)
         ELSE 0 END as success_rate,
    ch.avg_execution_ms
FROM command_handlers ch
JOIN command_registry cr ON ch.cmd_id = cr.cmd_id
WHERE ch.enabled = 1
ORDER BY ch.execution_count DESC;

DROP VIEW IF EXISTS v_execution_chain;
CREATE VIEW v_execution_chain AS
SELECT 
    cr.cmd_name,
    cr.cmd_opcode,
    GROUP_CONCAT(DISTINCT cf.flag_short || ':' || cf.flag_bit) as flag_bits,
    GROUP_CONCAT(DISTINCT ca.arg_position || ':' || ca.arg_name || ':' || ca.arg_type) as args,
    ch.handler_type,
    ch.handler_id,
    ch.priority
FROM command_registry cr
LEFT JOIN command_flags cf ON cr.cmd_id = cf.cmd_id
LEFT JOIN command_arguments ca ON cr.cmd_id = ca.cmd_id
LEFT JOIN command_handlers ch ON cr.cmd_id = ch.cmd_id
WHERE cr.cmd_enabled = 1 AND (ch.enabled = 1 OR ch.enabled IS NULL)
GROUP BY cr.cmd_id, ch.handler_id
ORDER BY cr.cmd_name, ch.priority DESC;

-- ═══════════════════════════════════════════════════════════════════════════
-- TRIGGERS FOR AUTOMATIC MAINTENANCE
-- ═══════════════════════════════════════════════════════════════════════════

DROP TRIGGER IF EXISTS trg_handler_execution_update;
CREATE TRIGGER trg_handler_execution_update
AFTER INSERT ON command_execution_log
BEGIN
    UPDATE command_handlers
    SET 
        execution_count = execution_count + 1,
        success_count = success_count + NEW.success,
        error_count = error_count + (1 - NEW.success),
        last_executed = NEW.timestamp,
        avg_execution_ms = (avg_execution_ms * (execution_count - 1) + NEW.execution_time_ms) / execution_count
    WHERE handler_id = NEW.handler_id;
    
    UPDATE command_registry
    SET 
        cmd_use_count = cmd_use_count + 1,
        cmd_last_used = NEW.timestamp
    WHERE cmd_id = NEW.cmd_id;
END;

DROP TRIGGER IF EXISTS trg_handler_update_timestamp;
CREATE TRIGGER trg_handler_update_timestamp
AFTER UPDATE ON command_handlers
BEGIN
    UPDATE command_handlers SET updated_at = strftime('%s', 'now') WHERE handler_id = NEW.handler_id;
END;
"""

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: COMMAND REGISTRY MIGRATION
# ═══════════════════════════════════════════════════════════════════════════════

def migrate_command_registry(conn):
    """Ensure command_registry exists with cmd_id column - bulletproof version"""
    c = conn.cursor()
    
    # Check if command_registry exists at all
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='command_registry'")
    table_exists = c.fetchone() is not None
    
    if not table_exists:
        # No table - create fresh with cmd_id
        print("      Creating new command_registry table...")
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
        conn.commit()
        return 0
    
    # Table exists - check if it has cmd_id
    c.execute("PRAGMA table_info(command_registry)")
    columns = {row[1]: row for row in c.fetchall()}
    
    if 'cmd_id' in columns:
        # Already has cmd_id - we're good
        c.execute("SELECT COUNT(*) FROM command_registry")
        count = c.fetchone()[0]
        print(f"      command_registry already has cmd_id ({count} commands)")
        return count
    
    # Table exists but NO cmd_id column - need to rebuild
    print("      Rebuilding command_registry with cmd_id column...")
    
    # Get existing column names
    existing_cols = list(columns.keys())
    print(f"      Existing columns: {existing_cols}")
    
    # Backup existing data
    c.execute("SELECT * FROM command_registry")
    old_data = c.fetchall()
    old_count = len(old_data)
    print(f"      Backing up {old_count} existing commands...")
    
    # Drop and recreate
    c.execute("DROP TABLE command_registry")
    
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
    
    # Map old data to new schema
    # Figure out which columns we can migrate
    new_cols = ['cmd_name', 'cmd_opcode', 'cmd_category', 'cmd_description', 
                'cmd_usage', 'cmd_requires_qubits', 'cmd_quantum_advantage',
                'cmd_enabled', 'cmd_use_count', 'cmd_last_used']
    
    migrated = 0
    for row in old_data:
        row_dict = dict(zip(existing_cols, row))
        
        # Must have cmd_name
        if 'cmd_name' not in row_dict or not row_dict['cmd_name']:
            continue
        
        # Build insert
        insert_cols = []
        insert_vals = []
        for col in new_cols:
            if col in row_dict and row_dict[col] is not None:
                insert_cols.append(col)
                insert_vals.append(row_dict[col])
        
        if insert_cols:
            placeholders = ','.join(['?' for _ in insert_vals])
            cols_str = ','.join(insert_cols)
            try:
                c.execute(f"INSERT INTO command_registry ({cols_str}) VALUES ({placeholders})", insert_vals)
                migrated += 1
            except sqlite3.IntegrityError as e:
                print(f"      Skip duplicate: {row_dict.get('cmd_name', '?')}")
    
    conn.commit()
    print(f"      Migrated {migrated}/{old_count} commands")
    return migrated
    


# ═══════════════════════════════════════════════════════════════════════════════

COMMANDS = [
    # (cmd_name, opcode, category, description, usage, requires_qubits)
    # FILESYSTEM COMMANDS (20)
    ('ls', 0x4000, 'filesystem', 'List directory contents', 'ls [-la] [path]', 0),
    ('dir', 0x4001, 'filesystem', 'List directory contents (alias)', 'dir [path]', 0),
    ('pwd', 0x4002, 'filesystem', 'Print working directory', 'pwd', 0),
    ('cd', 0x4003, 'filesystem', 'Change directory', 'cd [path]', 0),
    ('cat', 0x4004, 'filesystem', 'Display file contents', 'cat [-n] file', 0),
    ('mkdir', 0x4005, 'filesystem', 'Create directory', 'mkdir [-p] dir', 0),
    ('rmdir', 0x4006, 'filesystem', 'Remove empty directory', 'rmdir dir', 0),
    ('rm', 0x4007, 'filesystem', 'Remove files', 'rm [-rf] file', 0),
    ('cp', 0x4008, 'filesystem', 'Copy files', 'cp [-r] src dest', 0),
    ('mv', 0x4009, 'filesystem', 'Move files', 'mv src dest', 0),
    ('touch', 0x400A, 'filesystem', 'Create empty file', 'touch file', 0),
    ('ln', 0x400B, 'filesystem', 'Create link', 'ln [-s] target link', 0),
    ('stat', 0x400C, 'filesystem', 'Display file status', 'stat file', 0),
    ('file', 0x400D, 'filesystem', 'Determine file type', 'file file', 0),
    ('chmod', 0x400E, 'filesystem', 'Change file mode', 'chmod mode file', 0),
    ('chown', 0x400F, 'filesystem', 'Change file owner', 'chown owner file', 0),
    ('chgrp', 0x4010, 'filesystem', 'Change file group', 'chgrp group file', 0),
    ('umask', 0x4011, 'filesystem', 'Set file creation mask', 'umask [mask]', 0),
    ('df', 0x4012, 'filesystem', 'Disk space usage', 'df [-h]', 0),
    ('du', 0x4013, 'filesystem', 'Directory space usage', 'du [-sh] [path]', 0),
    
    # TEXT PROCESSING COMMANDS (15)
    ('head', 0x4100, 'text', 'Output first part of files', 'head [-n] file', 0),
    ('tail', 0x4101, 'text', 'Output last part of files', 'tail [-n] file', 0),
    ('grep', 0x4102, 'text', 'Search for patterns', 'grep [-i] pattern file', 0),
    ('sed', 0x4103, 'text', 'Stream editor', 'sed script file', 0),
    ('awk', 0x4104, 'text', 'Pattern scanning', 'awk script file', 0),
    ('cut', 0x4105, 'text', 'Remove sections', 'cut -d: -f1 file', 0),
    ('paste', 0x4106, 'text', 'Merge lines of files', 'paste file1 file2', 0),
    ('sort', 0x4107, 'text', 'Sort lines', 'sort [-r] file', 0),
    ('uniq', 0x4108, 'text', 'Report unique lines', 'uniq [-c] file', 0),
    ('wc', 0x4109, 'text', 'Word, line, byte counts', 'wc [-lwc] file', 0),
    ('tr', 0x410A, 'text', 'Translate characters', 'tr set1 set2', 0),
    ('diff', 0x410B, 'text', 'Compare files', 'diff file1 file2', 0),
    ('patch', 0x410C, 'text', 'Apply diff patches', 'patch < file.patch', 0),
    ('more', 0x410D, 'text', 'Page through text', 'more file', 0),
    ('less', 0x410E, 'text', 'Page through text (enhanced)', 'less file', 0),
    
    # SYSTEM COMMANDS (20)
    ('ps', 0x4200, 'system', 'Report process status', 'ps [-aux]', 0),
    ('top', 0x4201, 'system', 'Display processes', 'top', 0),
    ('kill', 0x4202, 'system', 'Send signal to process', 'kill [-9] pid', 0),
    ('killall', 0x4203, 'system', 'Kill processes by name', 'killall name', 0),
    ('nice', 0x4204, 'system', 'Run with modified priority', 'nice -n 10 cmd', 0),
    ('renice', 0x4205, 'system', 'Alter process priority', 'renice -n 10 pid', 0),
    ('jobs', 0x4206, 'system', 'List active jobs', 'jobs', 0),
    ('bg', 0x4207, 'system', 'Resume job in background', 'bg %1', 0),
    ('fg', 0x4208, 'system', 'Resume job in foreground', 'fg %1', 0),
    ('uname', 0x4209, 'system', 'Print system information', 'uname [-a]', 0),
    ('hostname', 0x420A, 'system', 'Show/set hostname', 'hostname', 0),
    ('uptime', 0x420B, 'system', 'System uptime', 'uptime', 0),
    ('date', 0x420C, 'system', 'Display date/time', 'date', 0),
    ('time', 0x420D, 'system', 'Time a command', 'time cmd', 0),
    ('who', 0x420E, 'system', 'Show who is logged in', 'who', 0),
    ('w', 0x420F, 'system', 'Show who is logged in (detailed)', 'w', 0),
    ('whoami', 0x4210, 'system', 'Print effective user', 'whoami', 0),
    ('id', 0x4211, 'system', 'Print user identity', 'id', 0),
    ('env', 0x4212, 'system', 'Display environment', 'env', 0),
    ('export', 0x4213, 'system', 'Set environment variable', 'export VAR=val', 0),
    
    # NETWORK COMMANDS (15)
    ('ping', 0x4300, 'network', 'Send ICMP packets', 'ping [-c n] host', 0),
    ('traceroute', 0x4301, 'network', 'Trace packet route', 'traceroute host', 0),
    ('netstat', 0x4302, 'network', 'Network statistics', 'netstat [-an]', 0),
    ('ifconfig', 0x4303, 'network', 'Configure interface', 'ifconfig [iface]', 0),
    ('ip', 0x4304, 'network', 'Show/manipulate routing', 'ip addr', 0),
    ('route', 0x4305, 'network', 'Show routing table', 'route', 0),
    ('ss', 0x4306, 'network', 'Socket statistics', 'ss -tuln', 0),
    ('curl', 0x4307, 'network', 'Transfer URL', 'curl url', 0),
    ('wget', 0x4308, 'network', 'Download files', 'wget url', 0),
    ('ssh', 0x4309, 'network', 'Secure shell', 'ssh user@host', 0),
    ('scp', 0x430A, 'network', 'Secure copy', 'scp file user@host:path', 0),
    ('ftp', 0x430B, 'network', 'File transfer', 'ftp host', 0),
    ('telnet', 0x430C, 'network', 'Telnet protocol', 'telnet host port', 0),
    ('nslookup', 0x430D, 'network', 'DNS lookup', 'nslookup domain', 0),
    ('dig', 0x430E, 'network', 'DNS lookup (detailed)', 'dig domain', 0),
    
    # ARCHIVE COMMANDS (10)
    ('tar', 0x4400, 'archive', 'Tape archive', 'tar [-cxf] file', 0),
    ('gzip', 0x4401, 'archive', 'Compress files', 'gzip file', 0),
    ('gunzip', 0x4402, 'archive', 'Decompress files', 'gunzip file.gz', 0),
    ('bzip2', 0x4403, 'archive', 'Bzip2 compress', 'bzip2 file', 0),
    ('bunzip2', 0x4404, 'archive', 'Bzip2 decompress', 'bunzip2 file.bz2', 0),
    ('xz', 0x4405, 'archive', 'XZ compress', 'xz file', 0),
    ('unxz', 0x4406, 'archive', 'XZ decompress', 'unxz file.xz', 0),
    ('zip', 0x4407, 'archive', 'Zip compress', 'zip archive.zip file', 0),
    ('unzip', 0x4408, 'archive', 'Zip decompress', 'unzip archive.zip', 0),
    ('zcat', 0x4409, 'archive', 'View compressed file', 'zcat file.gz', 0),
    
    # QUANTUM GATE COMMANDS (20)
    ('qh', 0x0100, 'quantum', 'Hadamard gate', 'qh qubit_id', 1),
    ('qx', 0x0101, 'quantum', 'Pauli-X gate', 'qx qubit_id', 1),
    ('qy', 0x0102, 'quantum', 'Pauli-Y gate', 'qy qubit_id', 1),
    ('qz', 0x0103, 'quantum', 'Pauli-Z gate', 'qz qubit_id', 1),
    ('qs', 0x0104, 'quantum', 'S gate (sqrt Z)', 'qs qubit_id', 1),
    ('qt', 0x0105, 'quantum', 'T gate (sqrt S)', 'qt qubit_id', 1),
    ('qrx', 0x0106, 'quantum', 'Rotation-X gate', 'qrx qubit_id theta', 1),
    ('qry', 0x0107, 'quantum', 'Rotation-Y gate', 'qry qubit_id theta', 1),
    ('qrz', 0x0108, 'quantum', 'Rotation-Z gate', 'qrz qubit_id theta', 1),
    ('qcnot', 0x0200, 'quantum', 'CNOT gate', 'qcnot ctrl target', 2),
    ('qcz', 0x0201, 'quantum', 'CZ gate', 'qcz ctrl target', 2),
    ('qcy', 0x0202, 'quantum', 'CY gate', 'qcy ctrl target', 2),
    ('qswap', 0x0203, 'quantum', 'SWAP gate', 'qswap q1 q2', 2),
    ('qiswap', 0x0204, 'quantum', 'iSWAP gate', 'qiswap q1 q2', 2),
    ('qccnot', 0x0300, 'quantum', 'Toffoli gate', 'qccnot c1 c2 target', 3),
    ('qcswap', 0x0301, 'quantum', 'Fredkin gate', 'qcswap ctrl q1 q2', 3),
    ('qmeasure', 0x0400, 'quantum', 'Measure qubit', 'qmeasure qubit_id', 1),
    ('qreset', 0x0500, 'quantum', 'Reset qubit', 'qreset qubit_id', 1),
    ('qbarrier', 0x0600, 'quantum', 'Quantum barrier', 'qbarrier q1 q2 ...', 1),
    ('qphase', 0x0109, 'quantum', 'Phase gate', 'qphase qubit_id phi', 1),
    
    # QUANTUM MANAGEMENT COMMANDS (15)
    ('qalloc', 0x0700, 'quantum_mgmt', 'Allocate qubits', 'qalloc [count]', 1),
    ('qfree', 0x0701, 'quantum_mgmt', 'Free qubits', 'qfree qubit_ids', 1),
    ('qlist', 0x0702, 'quantum_mgmt', 'List allocated qubits', 'qlist', 1),
    ('qstate', 0x0703, 'quantum_mgmt', 'Show qubit state', 'qstate qubit_id', 1),
    ('qstat', 0x0704, 'quantum_mgmt', 'Quantum system status', 'qstat', 1),
    ('qinit', 0x0705, 'quantum_mgmt', 'Initialize qubit', 'qinit qubit_id [state]', 1),
    ('epr_create', 0x0800, 'quantum_mgmt', 'Create EPR pair', 'epr_create q1 q2', 2),
    ('ghz_create', 0x0801, 'quantum_mgmt', 'Create GHZ state', 'ghz_create q1 q2 q3', 3),
    ('w_create', 0x0802, 'quantum_mgmt', 'Create W state', 'w_create q1 q2 q3', 3),
    ('teleport', 0x0803, 'quantum_mgmt', 'Quantum teleport', 'teleport src dest', 2),
    ('entangle', 0x0804, 'quantum_mgmt', 'Entangle qubits', 'entangle q1 q2', 2),
    ('qft', 0x0900, 'quantum_mgmt', 'Quantum Fourier Transform', 'qft qubits...', 4),
    ('iqft', 0x0901, 'quantum_mgmt', 'Inverse QFT', 'iqft qubits...', 4),
    ('grover', 0x0902, 'quantum_mgmt', 'Grover search', 'grover oracle target', 4),
    ('vqe', 0x0903, 'quantum_mgmt', 'VQE algorithm', 'vqe hamiltonian', 4),
    
    # QUNIX SPECIAL COMMANDS (25)
    ('leech', 0x1000, 'qunix', 'Leech lattice info', 'leech [point_id]', 0),
    ('leech_encode', 0x1001, 'qunix', 'Encode with Leech lattice', 'leech_encode data', 1),
    ('leech_decode', 0x1002, 'qunix', 'Decode Leech lattice', 'leech_decode data', 1),
    ('golay_encode', 0x1003, 'qunix', 'Golay encode', 'golay_encode data', 1),
    ('golay_decode', 0x1004, 'qunix', 'Golay decode', 'golay_decode data', 1),
    ('bus', 0x1100, 'qunix', 'Quantum bus status', 'bus', 0),
    ('bus_status', 0x1101, 'qunix', 'Quantum bus status (alias)', 'bus_status', 0),
    ('bus_send', 0x1102, 'qunix', 'Send via bus', 'bus_send dest data', 1),
    ('bus_recv', 0x1103, 'qunix', 'Receive from bus', 'bus_recv', 1),
    ('nic', 0x1200, 'qunix', 'Quantum NIC status', 'nic', 0),
    ('qnic_status', 0x1201, 'qunix', 'QNIC status (alias)', 'qnic_status', 0),
    ('qnic_connect', 0x1202, 'qunix', 'QNIC connect', 'qnic_connect addr', 1),
    ('qnic_listen', 0x1203, 'qunix', 'QNIC listen', 'qnic_listen port', 0),
    ('lattice_point', 0x1300, 'qunix', 'Lattice point info', 'lattice_point id', 0),
    ('triangle', 0x1301, 'qunix', 'Triangle (W-state) info', 'triangle id', 1),
    ('epr_pair', 0x1302, 'qunix', 'EPR pair info', 'epr_pair id', 1),
    ('moonshine', 0x1400, 'qunix', 'Moonshine j-invariant', 'moonshine q', 1),
    ('e8_split', 0x1401, 'qunix', 'E8 lattice split', 'e8_split point_id', 1),
    ('hyperbolic', 0x1402, 'qunix', 'Hyperbolic distance', 'hyperbolic p1 p2', 1),
    ('circuit_run', 0x1500, 'qunix', 'Run circuit', 'circuit_run circuit_name', 1),
    ('circuit_list', 0x1501, 'qunix', 'List circuits', 'circuit_list', 0),
    ('circuit_show', 0x1502, 'qunix', 'Show circuit', 'circuit_show name', 0),
    ('circuit_save', 0x1503, 'qunix', 'Save circuit', 'circuit_save name qasm', 1),
    ('opcode', 0x1600, 'qunix', 'Execute opcode', 'opcode hex_code', 0),
    ('binary', 0x1601, 'qunix', 'Execute binary', 'binary hex_string', 0),
    
    # SHELL BUILTIN COMMANDS (20)
    ('help', 0xF000, 'builtin', 'Display help', 'help [command]', 0),
    ('man', 0xF001, 'builtin', 'Manual pages', 'man command', 0),
    ('whatis', 0xF002, 'builtin', 'Brief description', 'whatis command', 0),
    ('apropos', 0xF003, 'builtin', 'Search manual', 'apropos keyword', 0),
    ('info', 0xF004, 'builtin', 'Info documentation', 'info command', 0),
    ('echo', 0xF010, 'builtin', 'Display text', 'echo text', 0),
    ('printf', 0xF011, 'builtin', 'Format output', 'printf format args', 0),
    ('clear', 0xF012, 'builtin', 'Clear screen', 'clear', 0),
    ('reset', 0xF013, 'builtin', 'Reset terminal', 'reset', 0),
    ('exit', 0xF014, 'builtin', 'Exit shell', 'exit [code]', 0),
    ('logout', 0xF015, 'builtin', 'Logout', 'logout', 0),
    ('history', 0xF016, 'builtin', 'Command history', 'history [n]', 0),
    ('alias', 0xF017, 'builtin', 'Define alias', 'alias name=value', 0),
    ('unalias', 0xF018, 'builtin', 'Remove alias', 'unalias name', 0),
    ('type', 0xF019, 'builtin', 'Command type', 'type command', 0),
    ('which', 0xF01A, 'builtin', 'Locate command', 'which command', 0),
    ('source', 0xF01B, 'builtin', 'Execute file', 'source file', 0),
    ('exec', 0xF01C, 'builtin', 'Execute command', 'exec command', 0),
    ('eval', 0xF01D, 'builtin', 'Evaluate arguments', 'eval args', 0),
    ('set', 0xF01E, 'builtin', 'Set shell options', 'set [-x]', 0),
    
    # MISC COMMANDS (12)
    ('tree', 0x4500, 'misc', 'Display directory tree', 'tree [path]', 0),
    ('find', 0x4501, 'misc', 'Find files', 'find path -name pattern', 0),
    ('locate', 0x4502, 'misc', 'Locate files', 'locate pattern', 0),
    ('whereis', 0x4503, 'misc', 'Locate binary', 'whereis command', 0),
    ('cal', 0x4504, 'misc', 'Display calendar', 'cal [month year]', 0),
    ('bc', 0x4505, 'misc', 'Calculator', 'bc', 0),
    ('expr', 0x4506, 'misc', 'Evaluate expression', 'expr 1 + 2', 0),
    ('yes', 0x4507, 'misc', 'Output string repeatedly', 'yes [string]', 0),
    ('sleep', 0x4508, 'misc', 'Delay execution', 'sleep seconds', 0),
    ('true', 0x4509, 'misc', 'Return success', 'true', 0),
    ('false', 0x450A, 'misc', 'Return failure', 'false', 0),
    ('test', 0x450B, 'misc', 'Evaluate expression', 'test expression', 0),
    
    # STATUS COMMAND
    ('status', 0xF100, 'builtin', 'System status', 'status', 0),
    ('commands', 0xF101, 'builtin', 'List all commands', 'commands', 0),
]


def insert_commands(conn):
    """Insert all command definitions"""
    c = conn.cursor()
    now = time.time()
    
    inserted = 0
    updated = 0
    
    for cmd_name, opcode, category, description, usage, requires_qubits in COMMANDS:
        c.execute("SELECT cmd_id FROM command_registry WHERE cmd_name = ?", (cmd_name,))
        row = c.fetchone()
        
        if row:
            c.execute("""
                UPDATE command_registry 
                SET cmd_opcode = ?, cmd_category = ?, cmd_description = ?, 
                    cmd_usage = ?, cmd_requires_qubits = ?
                WHERE cmd_name = ?
            """, (opcode, category, description, usage, requires_qubits, cmd_name))
            updated += 1
        else:
            c.execute("""
                INSERT INTO command_registry 
                (cmd_name, cmd_opcode, cmd_category, cmd_description, cmd_usage, 
                 cmd_requires_qubits, cmd_created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (cmd_name, opcode, category, description, usage, requires_qubits, now))
            inserted += 1
    
    conn.commit()
    return inserted, updated

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: FLAG DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

FLAGS = [
    # (cmd_name, flag_short, flag_long, flag_bit, flag_type, value_type, description)
    # ls flags
    ('ls', 'l', 'long', 0, 'BOOLEAN', None, 'Long format listing'),
    ('ls', 'a', 'all', 1, 'BOOLEAN', None, 'Show all including hidden'),
    ('ls', 'h', 'human-readable', 2, 'BOOLEAN', None, 'Human readable sizes'),
    ('ls', 'R', 'recursive', 3, 'BOOLEAN', None, 'Recursive listing'),
    ('ls', 't', None, 4, 'BOOLEAN', None, 'Sort by modification time'),
    ('ls', 'S', None, 5, 'BOOLEAN', None, 'Sort by size'),
    ('ls', 'r', 'reverse', 6, 'BOOLEAN', None, 'Reverse sort order'),
    ('ls', '1', None, 7, 'BOOLEAN', None, 'One entry per line'),
    ('ls', 'i', 'inode', 8, 'BOOLEAN', None, 'Show inode numbers'),
    ('ls', 'd', 'directory', 9, 'BOOLEAN', None, 'List directories themselves'),
    # cat flags
    ('cat', 'n', 'number', 0, 'BOOLEAN', None, 'Number all lines'),
    ('cat', 'b', 'number-nonblank', 1, 'BOOLEAN', None, 'Number non-blank lines'),
    ('cat', 'E', 'show-ends', 2, 'BOOLEAN', None, 'Display $ at end of lines'),
    ('cat', 'T', 'show-tabs', 3, 'BOOLEAN', None, 'Display TAB as ^I'),
    ('cat', 's', 'squeeze-blank', 4, 'BOOLEAN', None, 'Squeeze blank lines'),
    ('cat', 'A', 'show-all', 5, 'BOOLEAN', None, 'Equivalent to -vET'),
    # rm flags
    ('rm', 'f', 'force', 0, 'BOOLEAN', None, 'Force removal'),
    ('rm', 'i', 'interactive', 1, 'BOOLEAN', None, 'Prompt before removal'),
    ('rm', 'r', 'recursive', 2, 'BOOLEAN', None, 'Remove recursively'),
    ('rm', 'R', None, 2, 'BOOLEAN', None, 'Remove recursively (alias)'),
    ('rm', 'v', 'verbose', 3, 'BOOLEAN', None, 'Verbose output'),
    ('rm', 'd', 'dir', 4, 'BOOLEAN', None, 'Remove empty directories'),
    # cp flags
    ('cp', 'r', 'recursive', 0, 'BOOLEAN', None, 'Copy recursively'),
    ('cp', 'R', None, 0, 'BOOLEAN', None, 'Copy recursively (alias)'),
    ('cp', 'p', 'preserve', 1, 'BOOLEAN', None, 'Preserve attributes'),
    ('cp', 'i', 'interactive', 2, 'BOOLEAN', None, 'Prompt before overwrite'),
    ('cp', 'v', 'verbose', 3, 'BOOLEAN', None, 'Verbose output'),
    ('cp', 'u', 'update', 4, 'BOOLEAN', None, 'Copy only newer files'),
    ('cp', 'l', 'link', 5, 'BOOLEAN', None, 'Create hard links'),
    ('cp', 's', 'symbolic-link', 6, 'BOOLEAN', None, 'Create symbolic links'),
    # mv flags
    ('mv', 'f', 'force', 0, 'BOOLEAN', None, 'Force overwrite'),
    ('mv', 'i', 'interactive', 1, 'BOOLEAN', None, 'Prompt before overwrite'),
    ('mv', 'v', 'verbose', 2, 'BOOLEAN', None, 'Verbose output'),
    ('mv', 'u', 'update', 3, 'BOOLEAN', None, 'Move only newer files'),
    ('mv', 'n', 'no-clobber', 4, 'BOOLEAN', None, 'Do not overwrite'),
    # mkdir flags
    ('mkdir', 'p', 'parents', 0, 'BOOLEAN', None, 'Create parent directories'),
    ('mkdir', 'v', 'verbose', 1, 'BOOLEAN', None, 'Verbose output'),
    ('mkdir', 'm', 'mode', 2, 'VALUE', 'STRING', 'Set permission mode'),
    # chmod flags
    ('chmod', 'R', 'recursive', 0, 'BOOLEAN', None, 'Change recursively'),
    ('chmod', 'v', 'verbose', 1, 'BOOLEAN', None, 'Verbose output'),
    ('chmod', 'c', 'changes', 2, 'BOOLEAN', None, 'Report only changes'),
    # chown flags
    ('chown', 'R', 'recursive', 0, 'BOOLEAN', None, 'Change recursively'),
    ('chown', 'v', 'verbose', 1, 'BOOLEAN', None, 'Verbose output'),
    ('chown', 'h', 'no-dereference', 2, 'BOOLEAN', None, 'Affect symlinks'),
    # df flags
    ('df', 'h', 'human-readable', 0, 'BOOLEAN', None, 'Human readable sizes'),
    ('df', 'k', None, 1, 'BOOLEAN', None, 'Use 1K blocks'),
    ('df', 'T', 'print-type', 2, 'BOOLEAN', None, 'Print filesystem type'),
    ('df', 'a', 'all', 3, 'BOOLEAN', None, 'Include pseudo filesystems'),
    ('df', 'i', 'inodes', 4, 'BOOLEAN', None, 'Show inode information'),
    # du flags
    ('du', 'h', 'human-readable', 0, 'BOOLEAN', None, 'Human readable sizes'),
    ('du', 's', 'summarize', 1, 'BOOLEAN', None, 'Show only total'),
    ('du', 'a', 'all', 2, 'BOOLEAN', None, 'Show all files'),
    ('du', 'c', 'total', 3, 'BOOLEAN', None, 'Produce grand total'),
    ('du', 'd', 'max-depth', 4, 'VALUE', 'INTEGER', 'Maximum depth'),
    # grep flags
    ('grep', 'i', 'ignore-case', 0, 'BOOLEAN', None, 'Case insensitive'),
    ('grep', 'v', 'invert-match', 1, 'BOOLEAN', None, 'Invert match'),
    ('grep', 'n', 'line-number', 2, 'BOOLEAN', None, 'Show line numbers'),
    ('grep', 'c', 'count', 3, 'BOOLEAN', None, 'Count matches only'),
    ('grep', 'l', 'files-with-matches', 4, 'BOOLEAN', None, 'Show filenames only'),
    ('grep', 'r', 'recursive', 5, 'BOOLEAN', None, 'Recursive search'),
    ('grep', 'R', None, 5, 'BOOLEAN', None, 'Recursive search (alias)'),
    ('grep', 'w', 'word-regexp', 6, 'BOOLEAN', None, 'Match whole words'),
    ('grep', 'x', 'line-regexp', 7, 'BOOLEAN', None, 'Match whole lines'),
    ('grep', 'E', 'extended-regexp', 8, 'BOOLEAN', None, 'Extended regex'),
    ('grep', 'F', 'fixed-strings', 9, 'BOOLEAN', None, 'Fixed strings'),
    # head/tail flags
    ('head', 'n', 'lines', 0, 'VALUE', 'INTEGER', 'Number of lines'),
    ('head', 'c', 'bytes', 1, 'VALUE', 'INTEGER', 'Number of bytes'),
    ('head', 'q', 'quiet', 2, 'BOOLEAN', None, 'Never print headers'),
    ('head', 'v', 'verbose', 3, 'BOOLEAN', None, 'Always print headers'),
    ('tail', 'n', 'lines', 0, 'VALUE', 'INTEGER', 'Number of lines'),
    ('tail', 'c', 'bytes', 1, 'VALUE', 'INTEGER', 'Number of bytes'),
    ('tail', 'f', 'follow', 2, 'BOOLEAN', None, 'Follow file'),
    ('tail', 'F', None, 3, 'BOOLEAN', None, 'Follow and retry'),
    ('tail', 'q', 'quiet', 4, 'BOOLEAN', None, 'Never print headers'),
    # wc flags
    ('wc', 'l', 'lines', 0, 'BOOLEAN', None, 'Print line count'),
    ('wc', 'w', 'words', 1, 'BOOLEAN', None, 'Print word count'),
    ('wc', 'c', 'bytes', 2, 'BOOLEAN', None, 'Print byte count'),
    ('wc', 'm', 'chars', 3, 'BOOLEAN', None, 'Print character count'),
    ('wc', 'L', 'max-line-length', 4, 'BOOLEAN', None, 'Print max line length'),
    # sort flags
    ('sort', 'r', 'reverse', 0, 'BOOLEAN', None, 'Reverse order'),
    ('sort', 'n', 'numeric-sort', 1, 'BOOLEAN', None, 'Numeric sort'),
    ('sort', 'u', 'unique', 2, 'BOOLEAN', None, 'Output unique lines'),
    ('sort', 'k', 'key', 3, 'VALUE', 'STRING', 'Sort key'),
    ('sort', 't', 'field-separator', 4, 'VALUE', 'STRING', 'Field separator'),
    # uniq flags
    ('uniq', 'c', 'count', 0, 'BOOLEAN', None, 'Prefix with count'),
    ('uniq', 'd', 'repeated', 1, 'BOOLEAN', None, 'Only print duplicates'),
    ('uniq', 'u', 'unique', 2, 'BOOLEAN', None, 'Only print unique'),
    ('uniq', 'i', 'ignore-case', 3, 'BOOLEAN', None, 'Ignore case'),
    # ps flags
    ('ps', 'a', None, 0, 'BOOLEAN', None, 'All with tty'),
    ('ps', 'u', None, 1, 'BOOLEAN', None, 'User-oriented format'),
    ('ps', 'x', None, 2, 'BOOLEAN', None, 'Without controlling tty'),
    ('ps', 'e', None, 3, 'BOOLEAN', None, 'All processes'),
    ('ps', 'f', None, 4, 'BOOLEAN', None, 'Full format'),
    ('ps', 'l', None, 5, 'BOOLEAN', None, 'Long format'),
    # uname flags
    ('uname', 'a', 'all', 0, 'BOOLEAN', None, 'Print all information'),
    ('uname', 's', 'kernel-name', 1, 'BOOLEAN', None, 'Print kernel name'),
    ('uname', 'n', 'nodename', 2, 'BOOLEAN', None, 'Print network node name'),
    ('uname', 'r', 'kernel-release', 3, 'BOOLEAN', None, 'Print kernel release'),
    ('uname', 'v', 'kernel-version', 4, 'BOOLEAN', None, 'Print kernel version'),
    ('uname', 'm', 'machine', 5, 'BOOLEAN', None, 'Print machine hardware'),
    ('uname', 'p', 'processor', 6, 'BOOLEAN', None, 'Print processor type'),
    ('uname', 'o', 'operating-system', 7, 'BOOLEAN', None, 'Print OS'),
    # kill flags
    ('kill', 's', 'signal', 0, 'VALUE', 'STRING', 'Signal to send'),
    ('kill', 'l', 'list', 1, 'BOOLEAN', None, 'List signal names'),
    ('kill', '9', None, 2, 'BOOLEAN', None, 'SIGKILL'),
    # ping flags
    ('ping', 'c', 'count', 0, 'VALUE', 'INTEGER', 'Stop after count'),
    ('ping', 'i', 'interval', 1, 'VALUE', 'FLOAT', 'Wait interval'),
    ('ping', 'q', 'quiet', 2, 'BOOLEAN', None, 'Quiet output'),
    ('ping', 'v', 'verbose', 3, 'BOOLEAN', None, 'Verbose output'),
    ('ping', 'W', 'timeout', 4, 'VALUE', 'INTEGER', 'Timeout seconds'),
    # netstat flags
    ('netstat', 'a', 'all', 0, 'BOOLEAN', None, 'Show all sockets'),
    ('netstat', 'n', 'numeric', 1, 'BOOLEAN', None, 'Numeric addresses'),
    ('netstat', 't', 'tcp', 2, 'BOOLEAN', None, 'TCP connections'),
    ('netstat', 'u', 'udp', 3, 'BOOLEAN', None, 'UDP connections'),
    ('netstat', 'l', 'listening', 4, 'BOOLEAN', None, 'Listening sockets'),
    ('netstat', 'p', 'programs', 5, 'BOOLEAN', None, 'Show PID/program'),
    # tar flags
    ('tar', 'c', 'create', 0, 'BOOLEAN', None, 'Create archive'),
    ('tar', 'x', 'extract', 1, 'BOOLEAN', None, 'Extract archive'),
    ('tar', 't', 'list', 2, 'BOOLEAN', None, 'List contents'),
    ('tar', 'f', 'file', 3, 'VALUE', 'STRING', 'Archive file'),
    ('tar', 'v', 'verbose', 4, 'BOOLEAN', None, 'Verbose output'),
    ('tar', 'z', 'gzip', 5, 'BOOLEAN', None, 'Gzip compression'),
    ('tar', 'j', 'bzip2', 6, 'BOOLEAN', None, 'Bzip2 compression'),
    ('tar', 'J', 'xz', 7, 'BOOLEAN', None, 'XZ compression'),
    # quantum flags
    ('qh', 's', 'shots', 0, 'VALUE', 'INTEGER', 'Number of shots'),
    ('qx', 's', 'shots', 0, 'VALUE', 'INTEGER', 'Number of shots'),
    ('qy', 's', 'shots', 0, 'VALUE', 'INTEGER', 'Number of shots'),
    ('qz', 's', 'shots', 0, 'VALUE', 'INTEGER', 'Number of shots'),
    ('qmeasure', 's', 'shots', 0, 'VALUE', 'INTEGER', 'Number of shots'),
    ('qmeasure', 'b', 'basis', 1, 'VALUE', 'STRING', 'Measurement basis'),
    ('qalloc', 'e', 'entangled', 0, 'BOOLEAN', None, 'Pre-entangle qubits'),
    ('qalloc', 't', 'type', 1, 'VALUE', 'STRING', 'Allocation type'),
    ('qstate', 'v', 'verbose', 0, 'BOOLEAN', None, 'Verbose output'),
    ('qstat', 'v', 'verbose', 0, 'BOOLEAN', None, 'Verbose output'),
    # builtin flags
    ('help', 'a', 'all', 0, 'BOOLEAN', None, 'Show all commands'),
    ('help', 'v', 'verbose', 1, 'BOOLEAN', None, 'Verbose help'),
    ('echo', 'n', None, 0, 'BOOLEAN', None, 'No trailing newline'),
    ('echo', 'e', None, 1, 'BOOLEAN', None, 'Enable escapes'),
    ('echo', 'E', None, 2, 'BOOLEAN', None, 'Disable escapes'),
    ('history', 'c', 'clear', 0, 'BOOLEAN', None, 'Clear history'),
    ('history', 'w', 'write', 1, 'BOOLEAN', None, 'Write to file'),
    ('history', 'r', 'read', 2, 'BOOLEAN', None, 'Read from file'),
    # find flags
    ('find', 'n', 'name', 0, 'VALUE', 'STRING', 'Name pattern'),
    ('find', 't', 'type', 1, 'VALUE', 'STRING', 'File type'),
    ('find', 's', 'size', 2, 'VALUE', 'STRING', 'File size'),
    ('find', 'm', 'mtime', 3, 'VALUE', 'INTEGER', 'Modified time'),
    ('find', 'x', 'exec', 4, 'VALUE', 'STRING', 'Execute command'),
    # tree flags
    ('tree', 'd', 'directories', 0, 'BOOLEAN', None, 'Directories only'),
    ('tree', 'a', 'all', 1, 'BOOLEAN', None, 'All files'),
    ('tree', 'L', 'level', 2, 'VALUE', 'INTEGER', 'Max depth'),
]


def insert_flags(conn):
    """Insert all flag definitions"""
    c = conn.cursor()
    now = time.time()
    inserted = 0
    for cmd_name, short, long_name, bit, ftype, val_type, desc in FLAGS:
        c.execute("SELECT cmd_id FROM command_registry WHERE cmd_name = ?", (cmd_name,))
        row = c.fetchone()
        if not row:
            continue
        cmd_id = row[0]
        try:
            c.execute("""
                INSERT OR REPLACE INTO command_flags 
                (cmd_id, flag_short, flag_long, flag_bit, flag_type, value_type, flag_description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (cmd_id, short, long_name, bit, ftype, val_type, desc, now))
            inserted += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    return inserted


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5: ARGUMENT DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

ARGUMENTS = [
    # (cmd_name, position, arg_name, arg_type, required, default, vmin, vmax, desc)
    # FILESYSTEM
    ('cd', 0, 'path', 'PATH', 0, '~', None, None, 'Directory path'),
    ('cat', 0, 'file', 'PATH', 1, None, None, None, 'File to display'),
    ('rm', 0, 'file', 'PATH', 1, None, None, None, 'File to remove'),
    ('cp', 0, 'source', 'PATH', 1, None, None, None, 'Source file'),
    ('cp', 1, 'dest', 'PATH', 1, None, None, None, 'Destination'),
    ('mv', 0, 'source', 'PATH', 1, None, None, None, 'Source file'),
    ('mv', 1, 'dest', 'PATH', 1, None, None, None, 'Destination'),
    ('mkdir', 0, 'dir', 'PATH', 1, None, None, None, 'Directory to create'),
    ('touch', 0, 'file', 'PATH', 1, None, None, None, 'File to create/update'),
    ('ln', 0, 'target', 'PATH', 1, None, None, None, 'Link target'),
    ('ln', 1, 'link', 'PATH', 1, None, None, None, 'Link name'),
    ('stat', 0, 'file', 'PATH', 1, None, None, None, 'File to stat'),
    ('chmod', 0, 'mode', 'STRING', 1, None, None, None, 'Permission mode'),
    ('chmod', 1, 'file', 'PATH', 1, None, None, None, 'File to modify'),
    ('chown', 0, 'owner', 'STRING', 1, None, None, None, 'New owner'),
    ('chown', 1, 'file', 'PATH', 1, None, None, None, 'File to modify'),
    # TEXT
    ('head', 0, 'file', 'PATH', 1, None, None, None, 'File to display'),
    ('tail', 0, 'file', 'PATH', 1, None, None, None, 'File to display'),
    ('grep', 0, 'pattern', 'STRING', 1, None, None, None, 'Search pattern'),
    ('grep', 1, 'file', 'PATH', 0, None, None, None, 'File to search'),
    ('sed', 0, 'script', 'STRING', 1, None, None, None, 'Sed script'),
    ('sed', 1, 'file', 'PATH', 0, None, None, None, 'Input file'),
    ('awk', 0, 'program', 'STRING', 1, None, None, None, 'Awk program'),
    ('awk', 1, 'file', 'PATH', 0, None, None, None, 'Input file'),
    ('wc', 0, 'file', 'PATH', 0, None, None, None, 'File to count'),
    ('sort', 0, 'file', 'PATH', 0, None, None, None, 'File to sort'),
    ('uniq', 0, 'file', 'PATH', 0, None, None, None, 'Input file'),
    ('diff', 0, 'file1', 'PATH', 1, None, None, None, 'First file'),
    ('diff', 1, 'file2', 'PATH', 1, None, None, None, 'Second file'),
    # SYSTEM
    ('kill', 0, 'pid', 'INTEGER', 1, None, 1, None, 'Process ID'),
    ('killall', 0, 'name', 'STRING', 1, None, None, None, 'Process name'),
    ('nice', 0, 'command', 'STRING', 1, None, None, None, 'Command to run'),
    ('renice', 0, 'priority', 'INTEGER', 1, None, -20, 19, 'New priority'),
    ('renice', 1, 'pid', 'INTEGER', 1, None, 1, None, 'Process ID'),
    ('sleep', 0, 'seconds', 'FLOAT', 1, None, 0, None, 'Sleep duration'),
    ('export', 0, 'assignment', 'STRING', 1, None, None, None, 'VAR=value'),
    # NETWORK
    ('ping', 0, 'host', 'STRING', 1, 'localhost', None, None, 'Host to ping'),
    ('traceroute', 0, 'host', 'STRING', 1, None, None, None, 'Host to trace'),
    ('curl', 0, 'url', 'STRING', 1, None, None, None, 'URL to fetch'),
    ('wget', 0, 'url', 'STRING', 1, None, None, None, 'URL to download'),
    ('ssh', 0, 'destination', 'STRING', 1, None, None, None, 'user@host'),
    ('scp', 0, 'source', 'STRING', 1, None, None, None, 'Source'),
    ('scp', 1, 'dest', 'STRING', 1, None, None, None, 'Destination'),
    ('telnet', 0, 'host', 'STRING', 1, None, None, None, 'Host'),
    ('telnet', 1, 'port', 'INTEGER', 0, '23', 1, 65535, 'Port'),
    ('nslookup', 0, 'name', 'STRING', 1, None, None, None, 'Name to lookup'),
    ('dig', 0, 'name', 'STRING', 1, None, None, None, 'Name to lookup'),
    # ARCHIVE
    ('tar', 0, 'archive', 'PATH', 0, None, None, None, 'Archive file'),
    ('gzip', 0, 'file', 'PATH', 1, None, None, None, 'File to compress'),
    ('gunzip', 0, 'file', 'PATH', 1, None, None, None, 'File to decompress'),
    ('zip', 0, 'archive', 'PATH', 1, None, None, None, 'Archive to create'),
    ('zip', 1, 'files', 'PATH', 1, None, None, None, 'Files to add'),
    ('unzip', 0, 'archive', 'PATH', 1, None, None, None, 'Archive to extract'),
    # QUANTUM
    ('qh', 0, 'qubit_id', 'QUBIT_ID', 1, None, 0, 196559, 'Target qubit'),
    ('qx', 0, 'qubit_id', 'QUBIT_ID', 1, None, 0, 196559, 'Target qubit'),
    ('qy', 0, 'qubit_id', 'QUBIT_ID', 1, None, 0, 196559, 'Target qubit'),
    ('qz', 0, 'qubit_id', 'QUBIT_ID', 1, None, 0, 196559, 'Target qubit'),
    ('qs', 0, 'qubit_id', 'QUBIT_ID', 1, None, 0, 196559, 'Target qubit'),
    ('qt', 0, 'qubit_id', 'QUBIT_ID', 1, None, 0, 196559, 'Target qubit'),
    ('qrx', 0, 'qubit_id', 'QUBIT_ID', 1, None, 0, 196559, 'Target qubit'),
    ('qrx', 1, 'theta', 'FLOAT', 1, None, None, None, 'Rotation angle'),
    ('qry', 0, 'qubit_id', 'QUBIT_ID', 1, None, 0, 196559, 'Target qubit'),
    ('qry', 1, 'theta', 'FLOAT', 1, None, None, None, 'Rotation angle'),
    ('qrz', 0, 'qubit_id', 'QUBIT_ID', 1, None, 0, 196559, 'Target qubit'),
    ('qrz', 1, 'theta', 'FLOAT', 1, None, None, None, 'Rotation angle'),
    ('qcnot', 0, 'control', 'QUBIT_ID', 1, None, 0, 196559, 'Control qubit'),
    ('qcnot', 1, 'target', 'QUBIT_ID', 1, None, 0, 196559, 'Target qubit'),
    ('qcz', 0, 'control', 'QUBIT_ID', 1, None, 0, 196559, 'Control qubit'),
    ('qcz', 1, 'target', 'QUBIT_ID', 1, None, 0, 196559, 'Target qubit'),
    ('qswap', 0, 'qubit1', 'QUBIT_ID', 1, None, 0, 196559, 'First qubit'),
    ('qswap', 1, 'qubit2', 'QUBIT_ID', 1, None, 0, 196559, 'Second qubit'),
    ('qccnot', 0, 'control1', 'QUBIT_ID', 1, None, 0, 196559, 'First control'),
    ('qccnot', 1, 'control2', 'QUBIT_ID', 1, None, 0, 196559, 'Second control'),
    ('qccnot', 2, 'target', 'QUBIT_ID', 1, None, 0, 196559, 'Target qubit'),
    ('qmeasure', 0, 'qubit_id', 'QUBIT_ID', 1, None, 0, 196559, 'Qubit to measure'),
    ('qreset', 0, 'qubit_id', 'QUBIT_ID', 1, None, 0, 196559, 'Qubit to reset'),
    ('qalloc', 0, 'count', 'INTEGER', 0, '1', 1, 1000, 'Number of qubits'),
    ('qfree', 0, 'qubit_ids', 'STRING', 1, None, None, None, 'Qubit IDs to free'),
    ('qstate', 0, 'qubit_id', 'QUBIT_ID', 1, None, 0, 196559, 'Qubit to inspect'),
    ('qinit', 0, 'qubit_id', 'QUBIT_ID', 1, None, 0, 196559, 'Qubit to initialize'),
    ('qinit', 1, 'state', 'STRING', 0, '0', None, None, 'Initial state'),
    ('epr_create', 0, 'qubit1', 'QUBIT_ID', 1, None, 0, 196559, 'First qubit'),
    ('epr_create', 1, 'qubit2', 'QUBIT_ID', 1, None, 0, 196559, 'Second qubit'),
    ('ghz_create', 0, 'qubit1', 'QUBIT_ID', 1, None, 0, 196559, 'First qubit'),
    ('ghz_create', 1, 'qubit2', 'QUBIT_ID', 1, None, 0, 196559, 'Second qubit'),
    ('ghz_create', 2, 'qubit3', 'QUBIT_ID', 1, None, 0, 196559, 'Third qubit'),
    # QUNIX
    ('leech', 0, 'point_id', 'INTEGER', 0, None, 0, 196559, 'Lattice point ID'),
    ('leech_encode', 0, 'data', 'STRING', 1, None, None, None, 'Data to encode'),
    ('leech_decode', 0, 'data', 'STRING', 1, None, None, None, 'Data to decode'),
    ('golay_encode', 0, 'data', 'STRING', 1, None, None, None, 'Data to encode'),
    ('golay_decode', 0, 'data', 'STRING', 1, None, None, None, 'Data to decode'),
    ('bus_send', 0, 'dest', 'STRING', 1, None, None, None, 'Destination'),
    ('bus_send', 1, 'data', 'STRING', 1, None, None, None, 'Data to send'),
    ('qnic_connect', 0, 'address', 'STRING', 1, None, None, None, 'Quantum address'),
    ('qnic_listen', 0, 'port', 'INTEGER', 0, '8080', 1, 65535, 'Listen port'),
    ('lattice_point', 0, 'id', 'INTEGER', 1, None, 0, 196559, 'Point ID'),
    ('triangle', 0, 'id', 'INTEGER', 1, None, 0, 65535, 'Triangle ID'),
    ('epr_pair', 0, 'id', 'INTEGER', 1, None, 0, None, 'EPR pair ID'),
    ('circuit_run', 0, 'name', 'STRING', 1, None, None, None, 'Circuit name'),
    ('circuit_show', 0, 'name', 'STRING', 1, None, None, None, 'Circuit name'),
    ('circuit_save', 0, 'name', 'STRING', 1, None, None, None, 'Circuit name'),
    ('circuit_save', 1, 'qasm', 'STRING', 1, None, None, None, 'QASM code'),
    ('opcode', 0, 'code', 'STRING', 1, None, None, None, 'Hex opcode'),
    ('binary', 0, 'hex', 'STRING', 1, None, None, None, 'Hex binary string'),
    # BUILTIN
    ('help', 0, 'command', 'STRING', 0, None, None, None, 'Command name'),
    ('man', 0, 'command', 'STRING', 1, None, None, None, 'Command name'),
    ('whatis', 0, 'command', 'STRING', 1, None, None, None, 'Command name'),
    ('apropos', 0, 'keyword', 'STRING', 1, None, None, None, 'Search keyword'),
    ('echo', 0, 'text', 'STRING', 0, '', None, None, 'Text to display'),
    ('exit', 0, 'code', 'INTEGER', 0, '0', 0, 255, 'Exit code'),
    ('history', 0, 'count', 'INTEGER', 0, '20', 1, 1000, 'Number of entries'),
    ('alias', 0, 'definition', 'STRING', 0, None, None, None, 'name=value'),
    ('unalias', 0, 'name', 'STRING', 1, None, None, None, 'Alias name'),
    ('type', 0, 'command', 'STRING', 1, None, None, None, 'Command name'),
    ('which', 0, 'command', 'STRING', 1, None, None, None, 'Command name'),
    ('source', 0, 'file', 'PATH', 1, None, None, None, 'Script file'),
    # MISC
    ('tree', 0, 'path', 'PATH', 0, '.', None, None, 'Directory path'),
    ('find', 0, 'path', 'PATH', 0, '.', None, None, 'Starting path'),
    ('locate', 0, 'pattern', 'STRING', 1, None, None, None, 'Search pattern'),
    ('whereis', 0, 'command', 'STRING', 1, None, None, None, 'Command name'),
    ('cal', 0, 'month', 'INTEGER', 0, None, 1, 12, 'Month'),
    ('cal', 1, 'year', 'INTEGER', 0, None, 1, 9999, 'Year'),
    ('expr', 0, 'expression', 'STRING', 1, None, None, None, 'Expression'),
    ('yes', 0, 'string', 'STRING', 0, 'y', None, None, 'String to repeat'),
    ('test', 0, 'expression', 'STRING', 1, None, None, None, 'Test expression'),
]


def insert_arguments(conn):
    """Insert all argument definitions"""
    c = conn.cursor()
    now = time.time()
    inserted = 0
    for cmd_name, pos, arg_name, arg_type, required, default, vmin, vmax, desc in ARGUMENTS:
        c.execute("SELECT cmd_id FROM command_registry WHERE cmd_name = ?", (cmd_name,))
        row = c.fetchone()
        if not row:
            continue
        cmd_id = row[0]
        try:
            c.execute("""
                INSERT OR REPLACE INTO command_arguments 
                (cmd_id, arg_position, arg_name, arg_type, required, default_value,
                 validation_min, validation_max, arg_description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (cmd_id, pos, arg_name, arg_type, required, default, vmin, vmax, desc, now))
            inserted += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    return inserted


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6: HANDLER DEFINITIONS (First 70 Commands)
# ═══════════════════════════════════════════════════════════════════════════════

HANDLERS = [
    # ─────────────────────────────────────────────────────────────────────────────
    # QUANTUM CIRCUIT HANDLERS (Single Qubit Gates)
    # ─────────────────────────────────────────────────────────────────────────────
    {
        'cmd_name': 'qh',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
h q[0];
measure q[0] -> c[0];''',
        'context_map': '{"qubit_id": "args.qubit_id", "shots": "flags.s or 1024"}',
        'result_formatter': '{"type": "histogram", "title": "Hadamard Gate |+⟩", "qubit": "{qubit_id}"}',
        'requires_qubits': 1,
        'qubit_count': 1,
        'priority': 100
    },
    {
        'cmd_name': 'qx',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
x q[0];
measure q[0] -> c[0];''',
        'context_map': '{"qubit_id": "args.qubit_id", "shots": "flags.s or 1024"}',
        'result_formatter': '{"type": "histogram", "title": "Pauli-X Gate |1⟩", "qubit": "{qubit_id}"}',
        'requires_qubits': 1,
        'qubit_count': 1,
        'priority': 100
    },
    {
        'cmd_name': 'qy',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
y q[0];
measure q[0] -> c[0];''',
        'context_map': '{"qubit_id": "args.qubit_id", "shots": "flags.s or 1024"}',
        'result_formatter': '{"type": "histogram", "title": "Pauli-Y Gate", "qubit": "{qubit_id}"}',
        'requires_qubits': 1,
        'qubit_count': 1,
        'priority': 100
    },
    {
        'cmd_name': 'qz',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
z q[0];
measure q[0] -> c[0];''',
        'context_map': '{"qubit_id": "args.qubit_id", "shots": "flags.s or 1024"}',
        'result_formatter': '{"type": "histogram", "title": "Pauli-Z Gate", "qubit": "{qubit_id}"}',
        'requires_qubits': 1,
        'qubit_count': 1,
        'priority': 100
    },
    {
        'cmd_name': 'qs',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
s q[0];
measure q[0] -> c[0];''',
        'context_map': '{"qubit_id": "args.qubit_id", "shots": "flags.s or 1024"}',
        'result_formatter': '{"type": "histogram", "title": "S Gate (√Z)", "qubit": "{qubit_id}"}',
        'requires_qubits': 1,
        'qubit_count': 1,
        'priority': 100
    },
    {
        'cmd_name': 'qt',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
t q[0];
measure q[0] -> c[0];''',
        'context_map': '{"qubit_id": "args.qubit_id", "shots": "flags.s or 1024"}',
        'result_formatter': '{"type": "histogram", "title": "T Gate (√S)", "qubit": "{qubit_id}"}',
        'requires_qubits': 1,
        'qubit_count': 1,
        'priority': 100
    },
    # ─────────────────────────────────────────────────────────────────────────────
    # QUANTUM CIRCUIT HANDLERS (Two Qubit Gates)
    # ─────────────────────────────────────────────────────────────────────────────
    {
        'cmd_name': 'qcnot',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
cx q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];''',
        'context_map': '{"control": "args.control", "target": "args.target", "shots": "flags.s or 1024"}',
        'result_formatter': '{"type": "histogram", "title": "CNOT Gate", "qubits": ["{control}", "{target}"]}',
        'requires_qubits': 1,
        'qubit_count': 2,
        'priority': 100
    },
    {
        'cmd_name': 'qcz',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
cz q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];''',
        'context_map': '{"control": "args.control", "target": "args.target", "shots": "flags.s or 1024"}',
        'result_formatter': '{"type": "histogram", "title": "CZ Gate", "qubits": ["{control}", "{target}"]}',
        'requires_qubits': 1,
        'qubit_count': 2,
        'priority': 100
    },
    {
        'cmd_name': 'qswap',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
swap q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];''',
        'context_map': '{"qubit1": "args.qubit1", "qubit2": "args.qubit2", "shots": "flags.s or 1024"}',
        'result_formatter': '{"type": "histogram", "title": "SWAP Gate", "qubits": ["{qubit1}", "{qubit2}"]}',
        'requires_qubits': 1,
        'qubit_count': 2,
        'priority': 100
    },
    {
        'cmd_name': 'qmeasure',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
measure q[0] -> c[0];''',
        'context_map': '{"qubit_id": "args.qubit_id", "shots": "flags.s or 1024", "basis": "flags.b or \'Z\'"}',
        'result_formatter': '{"type": "measurement", "title": "Measurement", "qubit": "{qubit_id}", "basis": "{basis}"}',
        'requires_qubits': 1,
        'qubit_count': 1,
        'priority': 100
    },
    {
        'cmd_name': 'qreset',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
reset q[0];
measure q[0] -> c[0];''',
        'context_map': '{"qubit_id": "args.qubit_id"}',
        'result_formatter': '{"type": "status", "title": "Reset", "qubit": "{qubit_id}", "state": "|0⟩"}',
        'requires_qubits': 1,
        'qubit_count': 1,
        'priority': 100
    },
    # ─────────────────────────────────────────────────────────────────────────────
    # QUANTUM ENTANGLEMENT HANDLERS
    # ─────────────────────────────────────────────────────────────────────────────
    {
        'cmd_name': 'epr_create',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];''',
        'context_map': '{"qubit1": "args.qubit1", "qubit2": "args.qubit2", "shots": "1024"}',
        'result_formatter': '{"type": "entanglement", "title": "EPR Pair |Φ+⟩", "state": "(|00⟩ + |11⟩)/√2", "qubits": ["{qubit1}", "{qubit2}"]}',
        'requires_qubits': 1,
        'qubit_count': 2,
        'priority': 100
    },
    {
        'cmd_name': 'ghz_create',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0], q[1];
cx q[1], q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];''',
        'context_map': '{"qubit1": "args.qubit1", "qubit2": "args.qubit2", "qubit3": "args.qubit3", "shots": "1024"}',
        'result_formatter': '{"type": "entanglement", "title": "GHZ State", "state": "(|000⟩ + |111⟩)/√2", "qubits": ["{qubit1}", "{qubit2}", "{qubit3}"]}',
        'requires_qubits': 1,
        'qubit_count': 3,
        'priority': 100
    },
    {
        'cmd_name': 'w_create',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
ry(1.9106332362490186) q[0];
cx q[0], q[1];
ry(pi/4) q[1];
cx q[1], q[2];
ry(pi/4) q[2];
cx q[0], q[1];
cx q[1], q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];''',
        'context_map': '{"qubit1": "args.qubit1", "qubit2": "args.qubit2", "qubit3": "args.qubit3", "shots": "1024"}',
        'result_formatter': '{"type": "entanglement", "title": "W State", "state": "(|001⟩ + |010⟩ + |100⟩)/√3", "qubits": ["{qubit1}", "{qubit2}", "{qubit3}"]}',
        'requires_qubits': 1,
        'qubit_count': 3,
        'priority': 100
    },
    # ─────────────────────────────────────────────────────────────────────────────
    # SQL QUERY HANDLERS (Quantum Management)
    # ─────────────────────────────────────────────────────────────────────────────
    {
        'cmd_name': 'qalloc',
        'handler_type': 'SQL_QUERY',
        'sql_query': '''INSERT INTO qubit_allocation (qubit_id, allocated_at, status) 
SELECT value, strftime('%s','now'), 'ALLOCATED' 
FROM (WITH RECURSIVE cnt(x) AS (
    SELECT (SELECT COALESCE(MAX(qubit_id)+1, 0) FROM qubit_allocation)
    UNION ALL SELECT x+1 FROM cnt WHERE x < (SELECT COALESCE(MAX(qubit_id)+1, 0) FROM qubit_allocation) + {count} - 1
) SELECT x as value FROM cnt) 
WHERE NOT EXISTS (SELECT 1 FROM qubit_allocation WHERE qubit_id = value);
SELECT qubit_id FROM qubit_allocation WHERE allocated_at = (SELECT MAX(allocated_at) FROM qubit_allocation);''',
        'context_map': '{"count": "args.count or 1"}',
        'result_formatter': 'Allocated {count} qubit(s): {result}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'qfree',
        'handler_type': 'SQL_QUERY',
        'sql_query': '''DELETE FROM qubit_allocation WHERE qubit_id IN ({qubit_ids});
SELECT changes() as freed;''',
        'context_map': '{"qubit_ids": "args.qubit_ids"}',
        'result_formatter': 'Freed {freed} qubit(s)',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'qlist',
        'handler_type': 'SQL_QUERY',
        'sql_query': '''SELECT qubit_id, status, datetime(allocated_at, 'unixepoch') as allocated 
FROM qubit_allocation ORDER BY qubit_id LIMIT 100;''',
        'context_map': '{}',
        'result_formatter': '{"type": "table", "title": "Allocated Qubits", "columns": ["ID", "Status", "Allocated"]}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'qstat',
        'handler_type': 'SQL_QUERY',
        'sql_query': '''SELECT 
    (SELECT COUNT(*) FROM qubit_allocation) as allocated_qubits,
    (SELECT COUNT(*) FROM qubit_allocation WHERE status='ENTANGLED') as entangled,
    196560 as total_lattice_points,
    (SELECT COUNT(*) FROM epr_pairs WHERE active=1) as active_epr_pairs,
    (SELECT COUNT(*) FROM w_triangles WHERE active=1) as active_triangles;''',
        'context_map': '{}',
        'result_formatter': '''╔═══════════════════════════════════════╗
║         QUNIX QUANTUM STATUS          ║
╠═══════════════════════════════════════╣
║  Allocated Qubits: {allocated_qubits:>8}          ║
║  Entangled:        {entangled:>8}          ║
║  Lattice Points:   {total_lattice_points:>8}          ║
║  Active EPR Pairs: {active_epr_pairs:>8}          ║
║  Active Triangles: {active_triangles:>8}          ║
╚═══════════════════════════════════════╝''',
        'requires_qubits': 0,
        'priority': 100
    },
    # ─────────────────────────────────────────────────────────────────────────────
    # SQL QUERY HANDLERS (System Information)
    # ─────────────────────────────────────────────────────────────────────────────
    {
        'cmd_name': 'ps',
        'handler_type': 'SQL_QUERY',
        'sql_query': '''SELECT 
    process_id as PID,
    process_name as NAME,
    status as STAT,
    quantum_threads as QTH,
    memory_qubits as QMEM,
    datetime(start_time, 'unixepoch') as STARTED
FROM quantum_processes 
WHERE active = 1 
ORDER BY process_id;''',
        'context_map': '{}',
        'result_formatter': '{"type": "table", "title": "Quantum Processes", "columns": ["PID", "NAME", "STAT", "QTH", "QMEM", "STARTED"]}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'uptime',
        'handler_type': 'SQL_QUERY',
        'sql_query': '''SELECT 
    datetime('now') as current_time,
    CAST((strftime('%s','now') - boot_time) / 86400 AS INTEGER) || 'd ' ||
    CAST(((strftime('%s','now') - boot_time) % 86400) / 3600 AS INTEGER) || 'h ' ||
    CAST(((strftime('%s','now') - boot_time) % 3600) / 60 AS INTEGER) || 'm' as uptime,
    (SELECT COUNT(*) FROM quantum_sessions WHERE active=1) as users,
    quantum_load_1 || ', ' || quantum_load_5 || ', ' || quantum_load_15 as load_avg
FROM system_state LIMIT 1;''',
        'context_map': '{}',
        'result_formatter': '{current_time} up {uptime}, {users} users, load average: {load_avg}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'history',
        'handler_type': 'SQL_QUERY',
        'sql_query': '''SELECT rowid as num, command, datetime(timestamp, 'unixepoch') as time 
FROM command_history ORDER BY rowid DESC LIMIT {count};''',
        'context_map': '{"count": "args.count or 20"}',
        'result_formatter': '{"type": "history", "title": "Command History"}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'bus',
        'handler_type': 'SQL_QUERY',
        'sql_query': '''SELECT 
    bus_id, bus_name, status, bandwidth_qbps,
    connected_nodes, active_transfers,
    error_rate, datetime(last_activity, 'unixepoch') as last_active
FROM quantum_bus ORDER BY bus_id;''',
        'context_map': '{}',
        'result_formatter': '{"type": "table", "title": "Quantum Bus Status", "columns": ["ID", "Name", "Status", "BW(qbps)", "Nodes", "Transfers", "Errors", "Last Active"]}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'nic',
        'handler_type': 'SQL_QUERY',
        'sql_query': '''SELECT 
    nic_id, nic_name, mac_address, status,
    entangled_pairs, fidelity,
    packets_tx, packets_rx
FROM quantum_nic ORDER BY nic_id;''',
        'context_map': '{}',
        'result_formatter': '{"type": "table", "title": "Quantum NIC Status", "columns": ["ID", "Name", "MAC", "Status", "EPR Pairs", "Fidelity", "TX", "RX"]}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'df',
        'handler_type': 'SQL_QUERY',
        'sql_query': '''SELECT 
    filesystem, 
    total_qubits as total,
    used_qubits as used,
    available_qubits as avail,
    CAST(100.0 * used_qubits / total_qubits AS INTEGER) || '%' as use_pct,
    mount_point
FROM quantum_filesystems ORDER BY mount_point;''',
        'context_map': '{}',
        'result_formatter': '{"type": "table", "title": "Quantum Filesystem Usage", "columns": ["Filesystem", "Total", "Used", "Avail", "Use%", "Mounted on"]}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'whoami',
        'handler_type': 'SQL_QUERY',
        'sql_query': '''SELECT username FROM quantum_sessions WHERE session_id = '{session_id}' AND active = 1;''',
        'context_map': '{"session_id": "context.session_id"}',
        'result_formatter': '{username}',
        'requires_qubits': 0,
        'priority': 100
    },
    # ─────────────────────────────────────────────────────────────────────────────
    # PYTHON METHOD HANDLERS (Filesystem)
    # ─────────────────────────────────────────────────────────────────────────────
    {
        'cmd_name': 'ls',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    import os
    from datetime import datetime
    path = args.get('path', context.get('cwd', '/'))
    if path == '~':
        path = context.get('home', '/home/quantum')
    
    try:
        entries = os.listdir(path)
    except:
        c = conn.cursor()
        c.execute("SELECT name, type, size, permissions, modified FROM quantum_fs WHERE parent_path = ?", (path,))
        rows = c.fetchall()
        entries = [{'name': r[0], 'type': r[1], 'size': r[2], 'perms': r[3], 'mtime': r[4]} for r in rows]
    
    if not flags.get('a'):
        entries = [e for e in entries if not (isinstance(e, str) and e.startswith('.')) and not (isinstance(e, dict) and e['name'].startswith('.'))]
    
    if flags.get('l'):
        result = []
        for e in entries:
            if isinstance(e, dict):
                result.append(f"{e['perms']} {e['size']:>8} {e['name']}")
            else:
                result.append(e)
        return '\\n'.join(result)
    else:
        if isinstance(entries[0], dict) if entries else False:
            return '  '.join(e['name'] for e in entries)
        return '  '.join(entries)
''',
        'context_map': '{"path": "args.path or \'.\'"}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'pwd',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    return context.get('cwd', '/home/quantum')
''',
        'context_map': '{}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'cd',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    import os
    path = args.get('path', '~')
    if path == '~':
        path = context.get('home', '/home/quantum')
    elif path == '-':
        path = context.get('oldpwd', context.get('cwd', '/'))
    elif not path.startswith('/'):
        path = os.path.join(context.get('cwd', '/'), path)
    
    path = os.path.normpath(path)
    context['oldpwd'] = context.get('cwd', '/')
    context['cwd'] = path
    return ''
''',
        'context_map': '{"path": "args.path"}',
        'result_formatter': '',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'cat',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    filepath = args.get('file')
    if not filepath:
        return 'cat: missing operand'
    
    c = conn.cursor()
    c.execute("SELECT content FROM quantum_fs WHERE path = ?", (filepath,))
    row = c.fetchone()
    if not row:
        return f'cat: {filepath}: No such file'
    
    content = row[0]
    if flags.get('n'):
        lines = content.split('\\n')
        content = '\\n'.join(f'{i+1:>6}  {line}' for i, line in enumerate(lines))
    return content
''',
        'context_map': '{"file": "args.file"}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'echo',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    text = args.get('text', '')
    if flags.get('e'):
        text = text.replace('\\\\n', '\\n').replace('\\\\t', '\\t')
    if flags.get('n'):
        return text
    return text + '\\n'
''',
        'context_map': '{"text": "args.text"}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'mkdir',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    import os
    dirname = args.get('dir')
    if not dirname:
        return 'mkdir: missing operand'
    
    c = conn.cursor()
    now = __import__('time').time()
    
    if flags.get('p'):
        parts = dirname.strip('/').split('/')
        current = ''
        for part in parts:
            current = current + '/' + part
            c.execute("INSERT OR IGNORE INTO quantum_fs (path, name, type, parent_path, created, modified) VALUES (?, ?, 'dir', ?, ?, ?)",
                     (current, part, os.path.dirname(current) or '/', now, now))
    else:
        parent = os.path.dirname(dirname) or '/'
        name = os.path.basename(dirname)
        c.execute("INSERT INTO quantum_fs (path, name, type, parent_path, created, modified) VALUES (?, ?, 'dir', ?, ?, ?)",
                 (dirname, name, parent, now, now))
    
    conn.commit()
    return '' if not flags.get('v') else f'mkdir: created directory \\'{dirname}\\''
''',
        'context_map': '{"dir": "args.dir"}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'rm',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    filepath = args.get('file')
    if not filepath:
        return 'rm: missing operand'
    
    c = conn.cursor()
    
    if flags.get('r') or flags.get('R'):
        c.execute("DELETE FROM quantum_fs WHERE path LIKE ? OR path = ?", (filepath + '/%', filepath))
    else:
        c.execute("SELECT type FROM quantum_fs WHERE path = ?", (filepath,))
        row = c.fetchone()
        if row and row[0] == 'dir':
            if not flags.get('d'):
                return f'rm: cannot remove \\'{filepath}\\': Is a directory'
        c.execute("DELETE FROM quantum_fs WHERE path = ?", (filepath,))
    
    conn.commit()
    deleted = c.rowcount
    if flags.get('v'):
        return f'removed \\'{filepath}\\''
    return ''
''',
        'context_map': '{"file": "args.file"}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'touch',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    import os
    filepath = args.get('file')
    if not filepath:
        return 'touch: missing operand'
    
    c = conn.cursor()
    now = __import__('time').time()
    
    c.execute("SELECT path FROM quantum_fs WHERE path = ?", (filepath,))
    if c.fetchone():
        c.execute("UPDATE quantum_fs SET modified = ? WHERE path = ?", (now, filepath))
    else:
        parent = os.path.dirname(filepath) or '/'
        name = os.path.basename(filepath)
        c.execute("INSERT INTO quantum_fs (path, name, type, parent_path, size, content, created, modified) VALUES (?, ?, 'file', ?, 0, '', ?, ?)",
                 (filepath, name, parent, now, now))
    
    conn.commit()
    return ''
''',
        'context_map': '{"file": "args.file"}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    # ─────────────────────────────────────────────────────────────────────────────
    # PYTHON METHOD HANDLERS (Text Processing)
    # ─────────────────────────────────────────────────────────────────────────────
    {
        'cmd_name': 'grep',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    import re
    pattern = args.get('pattern')
    filepath = args.get('file')
    
    if not pattern:
        return 'grep: missing pattern'
    
    c = conn.cursor()
    c.execute("SELECT content FROM quantum_fs WHERE path = ?", (filepath,))
    row = c.fetchone()
    content = row[0] if row else ''
    
    regex_flags = re.IGNORECASE if flags.get('i') else 0
    lines = content.split('\\n')
    matches = []
    
    for i, line in enumerate(lines, 1):
        match = re.search(pattern, line, regex_flags)
        if (match and not flags.get('v')) or (not match and flags.get('v')):
            if flags.get('n'):
                matches.append(f'{i}:{line}')
            else:
                matches.append(line)
    
    if flags.get('c'):
        return str(len(matches))
    
    return '\\n'.join(matches)
''',
        'context_map': '{"pattern": "args.pattern", "file": "args.file"}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'head',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    filepath = args.get('file')
    if not filepath:
        return 'head: missing operand'
    
    c = conn.cursor()
    c.execute("SELECT content FROM quantum_fs WHERE path = ?", (filepath,))
    row = c.fetchone()
    if not row:
        return f'head: {filepath}: No such file'
    
    lines = row[0].split('\\n')
    n = int(flags.get('n', 10))
    return '\\n'.join(lines[:n])
''',
        'context_map': '{"file": "args.file"}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'tail',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    filepath = args.get('file')
    if not filepath:
        return 'tail: missing operand'
    
    c = conn.cursor()
    c.execute("SELECT content FROM quantum_fs WHERE path = ?", (filepath,))
    row = c.fetchone()
    if not row:
        return f'tail: {filepath}: No such file'
    
    lines = row[0].split('\\n')
    n = int(flags.get('n', 10))
    return '\\n'.join(lines[-n:])
''',
        'context_map': '{"file": "args.file"}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'wc',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    filepath = args.get('file')
    
    c = conn.cursor()
    c.execute("SELECT content FROM quantum_fs WHERE path = ?", (filepath,))
    row = c.fetchone()
    content = row[0] if row else ''
    
    lines = len(content.split('\\n'))
    words = len(content.split())
    chars = len(content)
    
    parts = []
    if flags.get('l') or not any(flags.get(f) for f in 'lwc'):
        parts.append(f'{lines:>8}')
    if flags.get('w') or not any(flags.get(f) for f in 'lwc'):
        parts.append(f'{words:>8}')
    if flags.get('c') or not any(flags.get(f) for f in 'lwc'):
        parts.append(f'{chars:>8}')
    
    result = ''.join(parts)
    if filepath:
        result += f' {filepath}'
    return result
''',
        'context_map': '{"file": "args.file"}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    # ─────────────────────────────────────────────────────────────────────────────
    # PYTHON METHOD HANDLERS (Utilities)
    # ─────────────────────────────────────────────────────────────────────────────
    {
        'cmd_name': 'tree',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    path = args.get('path', '.')
    max_depth = int(flags.get('L', 3))
    
    c = conn.cursor()
    c.execute("""
        WITH RECURSIVE tree AS (
            SELECT path, name, type, 0 as depth, path as sort_path
            FROM quantum_fs WHERE parent_path = ? OR path = ?
            UNION ALL
            SELECT f.path, f.name, f.type, t.depth + 1, t.sort_path || '/' || f.name
            FROM quantum_fs f JOIN tree t ON f.parent_path = t.path
            WHERE t.depth < ?
        )
        SELECT path, name, type, depth FROM tree ORDER BY sort_path
    """, (path, path, max_depth))
    
    rows = c.fetchall()
    result = [path]
    dirs = files = 0
    
    for row in rows:
        if row[3] == 0:
            continue
        indent = '│   ' * (row[3] - 1) + '├── '
        result.append(f'{indent}{row[1]}')
        if row[2] == 'dir':
            dirs += 1
        else:
            files += 1
    
    result.append(f'\\n{dirs} directories, {files} files')
    return '\\n'.join(result)
''',
        'context_map': '{"path": "args.path or \'.\'"}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'find',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    path = args.get('path', '.')
    name_pattern = flags.get('n', '%')
    type_filter = flags.get('t')
    
    c = conn.cursor()
    sql = "SELECT path FROM quantum_fs WHERE path LIKE ? AND name LIKE ?"
    params = [path + '%', name_pattern.replace('*', '%')]
    
    if type_filter:
        sql += " AND type = ?"
        params.append('dir' if type_filter == 'd' else 'file')
    
    c.execute(sql, params)
    return '\\n'.join(row[0] for row in c.fetchall())
''',
        'context_map': '{"path": "args.path"}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'clear',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    return '\\033[2J\\033[H'
''',
        'context_map': '{}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    # ─────────────────────────────────────────────────────────────────────────────
    # PYTHON METHOD HANDLERS (Help System)
    # ─────────────────────────────────────────────────────────────────────────────
    {
        'cmd_name': 'help',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    cmd = args.get('command')
    c = conn.cursor()
    
    if cmd:
        c.execute("""
            SELECT cmd_name, cmd_description, cmd_usage, cmd_category,
                   (SELECT GROUP_CONCAT('-' || flag_short || ', --' || COALESCE(flag_long, '') || ': ' || flag_description, '\\n')
                    FROM command_flags WHERE cmd_id = cr.cmd_id) as flags
            FROM command_registry cr WHERE cmd_name = ?
        """, (cmd,))
        row = c.fetchone()
        if row:
            result = f"""
{row[0].upper()} - {row[1]}

USAGE: {row[2]}

CATEGORY: {row[3]}
"""
            if row[4]:
                result += f"\\nFLAGS:\\n{row[4]}"
            return result
        return f'help: no help for {cmd}'
    
    if flags.get('a'):
        c.execute("SELECT cmd_name, cmd_description FROM command_registry WHERE cmd_enabled = 1 ORDER BY cmd_category, cmd_name")
        return '\\n'.join(f'{row[0]:15} {row[1]}' for row in c.fetchall())
    
    return """QUNIX Shell Help
Type 'help <command>' for specific help
Type 'help -a' for all commands
Type 'commands' to list available commands"""
''',
        'context_map': '{"command": "args.command"}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'man',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    cmd = args.get('command')
    if not cmd:
        return 'What manual page do you want?'
    
    c = conn.cursor()
    c.execute("""
        SELECT cr.cmd_name, cr.cmd_description, cr.cmd_usage, cr.cmd_category,
               cr.cmd_requires_qubits, cr.cmd_opcode
        FROM command_registry cr WHERE cmd_name = ?
    """, (cmd,))
    row = c.fetchone()
    
    if not row:
        return f'No manual entry for {cmd}'
    
    c.execute("SELECT flag_short, flag_long, flag_description FROM command_flags WHERE cmd_id = (SELECT cmd_id FROM command_registry WHERE cmd_name = ?)", (cmd,))
    flags_rows = c.fetchall()
    
    c.execute("SELECT arg_name, arg_type, required, arg_description FROM command_arguments WHERE cmd_id = (SELECT cmd_id FROM command_registry WHERE cmd_name = ?)", (cmd,))
    args_rows = c.fetchall()
    
    manual = f"""
{'=' * 60}
{row[0].upper()}(1)                 QUNIX Manual                {row[0].upper()}(1)
{'=' * 60}

NAME
    {row[0]} - {row[1]}

SYNOPSIS
    {row[2]}

DESCRIPTION
    Category: {row[3]}
    Requires Qubits: {'Yes' if row[4] else 'No'}
    Opcode: 0x{row[5]:04X}
"""
    
    if flags_rows:
        manual += "\\nOPTIONS\\n"
        for fr in flags_rows:
            short = f'-{fr[0]}' if fr[0] else ''
            long_f = f'--{fr[1]}' if fr[1] else ''
            sep = ', ' if short and long_f else ''
            manual += f"    {short}{sep}{long_f}\\n        {fr[2]}\\n"
    
    if args_rows:
        manual += "\\nARGUMENTS\\n"
        for ar in args_rows:
            req = '[required]' if ar[2] else '[optional]'
            manual += f"    {ar[0]} ({ar[1]}) {req}\\n        {ar[3]}\\n"
    
    manual += f"\\n{'=' * 60}"
    return manual
''',
        'context_map': '{"command": "args.command"}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    # ─────────────────────────────────────────────────────────────────────────────
    # PYTHON METHOD HANDLERS (System)
    # ─────────────────────────────────────────────────────────────────────────────
    {
        'cmd_name': 'uname',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    info = {
        's': 'QUNIX',
        'n': 'leech-node-0',
        'r': '8.0.0-quantum',
        'v': '#1 SMP PREEMPT_QUANTUM',
        'm': 'leech_lattice_196560',
        'p': 'quantum_processor',
        'o': 'QUNIX/Leech'
    }
    
    if flags.get('a'):
        return ' '.join(info.values())
    
    parts = []
    for key in 'snrvmpo':
        if flags.get(key):
            parts.append(info[key])
    
    return ' '.join(parts) if parts else info['s']
''',
        'context_map': '{}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'date',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    from datetime import datetime
    return datetime.now().strftime('%a %b %d %H:%M:%S %Z %Y')
''',
        'context_map': '{}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'hostname',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    c = conn.cursor()
    c.execute("SELECT value FROM system_config WHERE key = 'hostname'")
    row = c.fetchone()
    return row[0] if row else 'leech-node-0'
''',
        'context_map': '{}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'who',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    c = conn.cursor()
    c.execute("""
        SELECT username, terminal, datetime(login_time, 'unixepoch'), host 
        FROM quantum_sessions WHERE active = 1
    """)
    rows = c.fetchall()
    return '\\n'.join(f'{r[0]:12} {r[1]:8} {r[2]} ({r[3]})' for r in rows)
''',
        'context_map': '{}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'id',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    c = conn.cursor()
    c.execute("""
        SELECT user_id, username, group_id, group_name 
        FROM quantum_sessions s 
        JOIN quantum_users u ON s.user_id = u.id
        JOIN quantum_groups g ON u.primary_group = g.id
        WHERE s.session_id = ? AND s.active = 1
    """, (context.get('session_id', ''),))
    row = c.fetchone()
    if row:
        return f'uid={row[0]}({row[1]}) gid={row[2]}({row[3]})'
    return 'uid=0(quantum) gid=0(quantum)'
''',
        'context_map': '{}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'env',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    env_vars = {
        'HOME': context.get('home', '/home/quantum'),
        'USER': context.get('username', 'quantum'),
        'SHELL': '/bin/qsh',
        'PWD': context.get('cwd', '/'),
        'PATH': '/bin:/usr/bin:/usr/local/bin:/quantum/bin',
        'QUNIX_VERSION': '8.0.0',
        'LEECH_POINTS': '196560',
        'QUANTUM_BACKEND': 'leech_lattice'
    }
    return '\\n'.join(f'{k}={v}' for k, v in env_vars.items())
''',
        'context_map': '{}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    # ─────────────────────────────────────────────────────────────────────────────
    # QUNIX SPECIAL HANDLERS
    # ─────────────────────────────────────────────────────────────────────────────
    {
        'cmd_name': 'leech',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    point_id = args.get('point_id')
    
    if point_id is None:
        return """Leech Lattice Λ₂₄
═══════════════════════════════════════
Dimension:        24
Kissing Number:   196,560
Covering Radius:  √2
Minimum Norm:     4
Automorphisms:    Co₀ (Conway group)
Points Available: 196,560 qubits

Use 'leech <point_id>' for specific point info"""
    
    point_id = int(point_id)
    if point_id < 0 or point_id >= 196560:
        return f'leech: invalid point_id {point_id} (0-196559)'
    
    shell = point_id // 8190
    position = point_id % 8190
    
    c = conn.cursor()
    c.execute("SELECT * FROM lattice_points WHERE point_id = ?", (point_id,))
    row = c.fetchone()
    
    return f"""Lattice Point #{point_id}
═══════════════════════════════════════
Shell:            {shell}
Position:         {position}
Norm:             4
Coordinates:      [24-dimensional vector]
Neighbors:        4600 (avg)
Qubit Status:     {'Allocated' if row else 'Available'}"""
''',
        'context_map': '{"point_id": "args.point_id"}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'circuit_list',
        'handler_type': 'SQL_QUERY',
        'sql_query': '''SELECT template_name, template_category, num_qubits, description 
FROM quantum_circuit_templates ORDER BY template_category, template_name;''',
        'context_map': '{}',
        'result_formatter': '{"type": "table", "title": "Circuit Templates", "columns": ["Name", "Category", "Qubits", "Description"]}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'circuit_show',
        'handler_type': 'SQL_QUERY',
        'sql_query': '''SELECT template_name, qasm_template, num_qubits, num_parameters, 
parameter_names, description FROM quantum_circuit_templates WHERE template_name = '{name}';''',
        'context_map': '{"name": "args.name"}',
        'result_formatter': '''Circuit: {template_name}
Qubits: {num_qubits}
Parameters: {num_parameters} ({parameter_names})

{qasm_template}

{description}''',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'exit',
        'handler_type': 'BUILTIN',
        'builtin_name': 'exit',
        'context_map': '{"code": "args.code or 0"}',
        'result_formatter': 'Exiting QUNIX with code {code}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'status',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM command_registry WHERE cmd_enabled = 1")
    cmds = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM command_handlers WHERE enabled = 1")
    handlers = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM qubit_allocation")
    qubits = c.fetchone()[0]
    
    return f"""
╔═══════════════════════════════════════════════════════════════╗
║                    QUNIX v8.0.0 STATUS                        ║
╠═══════════════════════════════════════════════════════════════╣
║  Commands Registered:    {cmds:>6}                              ║
║  Handlers Active:        {handlers:>6}                              ║
║  Qubits Allocated:       {qubits:>6}                              ║
║  Lattice Points:         196560                              ║
║  Database: OK                                                 ║
║  Execution Engine: READY                                      ║
╚═══════════════════════════════════════════════════════════════╝"""
''',
        'context_map': '{}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
    {
        'cmd_name': 'commands',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    c = conn.cursor()
    c.execute("""
        SELECT cmd_category, GROUP_CONCAT(cmd_name, ', ')
        FROM command_registry 
        WHERE cmd_enabled = 1 
        GROUP BY cmd_category
        ORDER BY cmd_category
    """)
    
    result = ['Available Commands by Category:', '=' * 40]
    for row in c.fetchall():
        result.append(f'\\n[{row[0].upper()}]')
        result.append(row[1])
    
    return '\\n'.join(result)
''',
        'context_map': '{}',
        'result_formatter': '{result}',
        'requires_qubits': 0,
        'priority': 100
    },
]


def insert_handlers(conn):
    """Insert all handler definitions"""
    c = conn.cursor()
    now = time.time()
    inserted = 0
    
    for h in HANDLERS:
        c.execute("SELECT cmd_id FROM command_registry WHERE cmd_name = ?", (h['cmd_name'],))
        row = c.fetchone()
        if not row:
            print(f"    Warning: Command '{h['cmd_name']}' not found, skipping handler")
            continue
        
        cmd_id = row[0]
        
        try:
            c.execute("""
                INSERT OR REPLACE INTO command_handlers 
                (cmd_id, handler_type, qasm_code, sql_query, python_code, 
                 builtin_name, context_map, result_formatter, 
                 requires_qubits, qubit_count, priority, created_at, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                cmd_id,
                h['handler_type'],
                h.get('qasm_code'),
                h.get('sql_query'),
                h.get('python_code'),
                h.get('builtin_name'),
                h.get('context_map', '{}'),
                h.get('result_formatter', '{result}'),
                h.get('requires_qubits', 0),
                h.get('qubit_count', 0),
                h.get('priority', 100),
                now
            ))
            inserted += 1
        except sqlite3.Error as e:
            print(f"    Error inserting handler for '{h['cmd_name']}': {e}")
    
    conn.commit()
    return inserted


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 7: CIRCUIT TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

CIRCUIT_TEMPLATES = [
    {
        'template_name': 'hadamard',
        'template_category': 'gate',
        'qasm_template': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
h q[0];
measure q[0] -> c[0];''',
        'num_qubits': 1,
        'num_parameters': 0,
        'parameter_names': None,
        'parameter_defaults': None,
        'description': 'Single qubit Hadamard gate creating superposition',
        'complexity_class': 'O(1)'
    },
    {
        'template_name': 'bell_pair',
        'template_category': 'entanglement',
        'qasm_template': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];''',
        'num_qubits': 2,
        'num_parameters': 0,
        'parameter_names': None,
        'parameter_defaults': None,
        'description': 'Creates Bell state |Φ+⟩ = (|00⟩ + |11⟩)/√2',
        'complexity_class': 'O(1)'
    },
    {
        'template_name': 'ghz_3',
        'template_category': 'entanglement',
        'qasm_template': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0], q[1];
cx q[1], q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];''',
        'num_qubits': 3,
        'num_parameters': 0,
        'parameter_names': None,
        'parameter_defaults': None,
        'description': 'Creates 3-qubit GHZ state (|000⟩ + |111⟩)/√2',
        'complexity_class': 'O(n)'
    },
    {
        'template_name': 'w_state_3',
        'template_category': 'entanglement',
        'qasm_template': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
ry(1.9106332362490186) q[0];
cx q[0], q[1];
ry(pi/4) q[1];
cx q[1], q[2];
ry(pi/4) q[2];
cx q[0], q[1];
cx q[1], q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];''',
        'num_qubits': 3,
        'num_parameters': 0,
        'parameter_names': None,
        'parameter_defaults': None,
        'description': 'Creates 3-qubit W state (|001⟩ + |010⟩ + |100⟩)/√3',
        'complexity_class': 'O(n)'
    },
    {
        'template_name': 'qft_4',
        'template_category': 'algorithm',
        'qasm_template': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0];
cp(pi/2) q[1], q[0];
cp(pi/4) q[2], q[0];
cp(pi/8) q[3], q[0];
h q[1];
cp(pi/2) q[2], q[1];
cp(pi/4) q[3], q[1];
h q[2];
cp(pi/2) q[3], q[2];
h q[3];
swap q[0], q[3];
swap q[1], q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
measure q[3] -> c[3];''',
        'num_qubits': 4,
        'num_parameters': 0,
        'parameter_names': None,
        'parameter_defaults': None,
        'description': '4-qubit Quantum Fourier Transform',
        'complexity_class': 'O(n²)'
    },
    {
        'template_name': 'grover_2',
        'template_category': 'algorithm',
        'qasm_template': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
// Initialize superposition
h q[0];
h q[1];
// Oracle for |11⟩
cz q[0], q[1];
// Diffusion operator
h q[0];
h q[1];
x q[0];
x q[1];
cz q[0], q[1];
x q[0];
x q[1];
h q[0];
h q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];''',
        'num_qubits': 2,
        'num_parameters': 0,
        'parameter_names': None,
        'parameter_defaults': None,
        'description': '2-qubit Grover search (oracle marks |11⟩)',
        'complexity_class': 'O(√N)'
    },
    {
        'template_name': 'teleportation',
        'template_category': 'protocol',
        'qasm_template': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
// q[0] = state to teleport
// q[1], q[2] = entangled pair
// Create Bell pair between q[1] and q[2]
h q[1];
cx q[1], q[2];
// Bell measurement on q[0], q[1]
cx q[0], q[1];
h q[0];
measure q[0] -> c[0];
measure q[1] -> c[1];
// Conditional corrections (classical controlled)
// if c[1] == 1: x q[2]
// if c[0] == 1: z q[2]
measure q[2] -> c[2];''',
        'num_qubits': 3,
        'num_parameters': 0,
        'parameter_names': None,
        'parameter_defaults': None,
        'description': 'Quantum teleportation protocol',
        'complexity_class': 'O(1)'
    },
]


def insert_circuit_templates(conn):
    """Insert circuit templates"""
    c = conn.cursor()
    now = time.time()
    inserted = 0
    
    for t in CIRCUIT_TEMPLATES:
        try:
            c.execute("""
                INSERT OR REPLACE INTO quantum_circuit_templates
                (template_name, template_category, qasm_template, num_qubits,
                 num_parameters, parameter_names, parameter_defaults,
                 description, complexity_class, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                t['template_name'],
                t['template_category'],
                t['qasm_template'],
                t['num_qubits'],
                t['num_parameters'],
                t['parameter_names'],
                t['parameter_defaults'],
                t['description'],
                t['complexity_class'],
                now
            ))
            inserted += 1
        except sqlite3.Error as e:
            print(f"    Error inserting template '{t['template_name']}': {e}")
    
    conn.commit()
    return inserted


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 8: PYTHON MODULES
# ═══════════════════════════════════════════════════════════════════════════════

PYTHON_MODULES = [
    {
        'module_name': 'flag_parser',
        'module_code': '''
class FlagParser:
    """Parse command line flags from command_flags table"""
    
    @staticmethod
    def parse(cmd_id, argv, conn):
        """
        Parse argv into (args_dict, flags_dict)
        
        Args:
            cmd_id: Command ID
            argv: List of arguments (excluding command name)
            conn: Database connection
            
        Returns:
            (args_dict, flags_dict) tuple
        """
        c = conn.cursor()
        
        # Get flag definitions
        c.execute("""
            SELECT flag_short, flag_long, flag_type, value_type, default_value
            FROM command_flags WHERE cmd_id = ? AND enabled = 1
        """, (cmd_id,))
        flag_defs = {row[0]: row for row in c.fetchall()}
        flag_defs_long = {row[1]: row for row in c.fetchall() if row[1]}
        
        # Get argument definitions
        c.execute("""
            SELECT arg_position, arg_name, arg_type, required, default_value
            FROM command_arguments WHERE cmd_id = ? ORDER BY arg_position
        """, (cmd_id,))
        arg_defs = list(c.fetchall())
        
        flags_dict = {}
        args_list = []
        i = 0
        
        while i < len(argv):
            arg = argv[i]
            
            if arg.startswith('--'):
                # Long flag
                if '=' in arg:
                    flag_name, value = arg[2:].split('=', 1)
                else:
                    flag_name = arg[2:]
                    value = True
                
                if flag_name in flag_defs_long:
                    fdef = flag_defs_long[flag_name]
                    if fdef[2] == 'VALUE' and value is True:
                        i += 1
                        value = argv[i] if i < len(argv) else None
                    flags_dict[flag_name] = value
                    if fdef[0]:  # Also set short flag key
                        flags_dict[fdef[0]] = value
                        
            elif arg.startswith('-') and len(arg) > 1 and not arg[1].isdigit():
                # Short flag(s)
                for j, char in enumerate(arg[1:]):
                    if char in flag_defs:
                        fdef = flag_defs[char]
                        if fdef[2] == 'VALUE':
                            # Value flag - rest of arg or next arg is value
                            if j < len(arg) - 2:
                                value = arg[j+2:]
                            else:
                                i += 1
                                value = argv[i] if i < len(argv) else None
                            flags_dict[char] = value
                            break
                        else:
                            flags_dict[char] = True
            else:
                # Positional argument
                args_list.append(arg)
            
            i += 1
        
        # Map positional args to names
        args_dict = {}
        for j, adef in enumerate(arg_defs):
            if j < len(args_list):
                args_dict[adef[1]] = args_list[j]
            elif adef[4]:  # Has default
                args_dict[adef[1]] = adef[4]
            elif adef[3]:  # Required but missing
                args_dict[adef[1]] = None  # Will fail validation
        
        return args_dict, flags_dict
''',
        'module_description': 'Command line flag and argument parser',
        'module_version': '1.0.0',
        'dependencies': None
    },
    {
        'module_name': 'handler_executor',
        'module_code': '''
import json

class HandlerExecutor:
    """Execute command handlers"""
    
    @staticmethod
    def execute(handler_row, args_dict, flags_dict, context):
        """
        Execute a handler and return result
        
        Args:
            handler_row: Row from command_handlers table
            args_dict: Parsed arguments
            flags_dict: Parsed flags
            context: Execution context (session info, cwd, etc.)
            
        Returns:
            (success, result_or_error)
        """
        handler_type = handler_row['handler_type']
        
        try:
            if handler_type == 'SQL_QUERY':
                return HandlerExecutor._execute_sql(handler_row, args_dict, flags_dict, context)
            elif handler_type == 'PYTHON_METHOD':
                return HandlerExecutor._execute_python(handler_row, args_dict, flags_dict, context)
            elif handler_type == 'QUANTUM_CIRCUIT':
                return HandlerExecutor._execute_quantum(handler_row, args_dict, flags_dict, context)
            elif handler_type == 'BUILTIN':
                return HandlerExecutor._execute_builtin(handler_row, args_dict, flags_dict, context)
            else:
                return False, f"Unknown handler type: {handler_type}"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def _execute_sql(handler_row, args_dict, flags_dict, context):
        """Execute SQL query handler"""
        sql = handler_row['sql_query']
        context_map = json.loads(handler_row['context_map'] or '{}')
        
        # Build parameters from context_map
        params = {}
        for key, expr in context_map.items():
            if expr.startswith('args.'):
                params[key] = args_dict.get(expr[5:])
            elif expr.startswith('flags.'):
                params[key] = flags_dict.get(expr[6:])
            elif expr.startswith('context.'):
                params[key] = context.get(expr[8:])
            else:
                params[key] = eval(expr, {'args': args_dict, 'flags': flags_dict, 'context': context})
        
        # Format SQL with parameters
        for key, value in params.items():
            sql = sql.replace('{' + key + '}', str(value) if value else '')
        
        c = context['conn'].cursor()
        c.execute(sql)
        
        if sql.strip().upper().startswith('SELECT'):
            rows = c.fetchall()
            columns = [d[0] for d in c.description] if c.description else []
            return True, {'rows': rows, 'columns': columns, 'params': params}
        else:
            context['conn'].commit()
            return True, {'affected': c.rowcount, 'params': params}
    
    @staticmethod
    def _execute_python(handler_row, args_dict, flags_dict, context):
        """Execute Python method handler"""
        code = handler_row['python_code']
        
        # Create execution namespace
        namespace = {
            'args': args_dict,
            'flags': flags_dict,
            'context': context,
            'conn': context.get('conn'),
            '__builtins__': __builtins__
        }
        
        # Execute the code to define handler function
        exec(code, namespace)
        
        # Call the handler function
        if 'handler' in namespace:
            result = namespace['handler'](args_dict, flags_dict, context, context.get('conn'))
            return True, result
        else:
            return False, "No handler function defined"
    
    @staticmethod
    def _execute_quantum(handler_row, args_dict, flags_dict, context):
        """Execute quantum circuit handler"""
        qasm = handler_row['qasm_code']
        context_map = json.loads(handler_row['context_map'] or '{}')
        
        # Get shots from context
        shots = 1024
        for key, expr in context_map.items():
            if key == 'shots':
                if expr.startswith('flags.'):
                    shots = int(flags_dict.get(expr[6:].split()[0], 1024))
        
        try:
            from qiskit import QuantumCircuit
            from qiskit_aer import AerSimulator
            
            circuit = QuantumCircuit.from_qasm_str(qasm)
            simulator = AerSimulator()
            job = simulator.run(circuit, shots=shots)
            result = job.result()
            counts = result.get_counts()
            
            return True, {'counts': counts, 'shots': shots, 'qasm': qasm}
        except ImportError:
            # Fallback simulation
            import random
            num_bits = qasm.count('creg')
            fake_counts = {}
            for _ in range(shots):
                outcome = ''.join(str(random.randint(0, 1)) for _ in range(max(1, num_bits)))
                fake_counts[outcome] = fake_counts.get(outcome, 0) + 1
            return True, {'counts': fake_counts, 'shots': shots, 'qasm': qasm, 'simulated': True}
    
    @staticmethod
    def _execute_builtin(handler_row, args_dict, flags_dict, context):
        """Execute builtin handler"""
        builtin_name = handler_row['builtin_name']
        formatter = handler_row['result_formatter'] or '{result}'
        
        result = formatter.format(**args_dict, **flags_dict, **context)
        return True, result
''',
        'module_description': 'Command handler execution engine',
        'module_version': '1.0.0',
        'dependencies': 'json'
    },
    {
        'module_name': 'argument_validator',
        'module_code': '''
import re

class ArgumentValidator:
    """Validate command arguments"""
    
    TYPE_VALIDATORS = {
        'INTEGER': lambda v: int(v),
        'FLOAT': lambda v: float(v),
        'STRING': lambda v: str(v),
        'PATH': lambda v: str(v),
        'QUBIT_ID': lambda v: ArgumentValidator._validate_qubit_id(v),
    }
    
    @staticmethod
    def _validate_qubit_id(value):
        """Validate qubit ID is in Leech lattice range"""
        qid = int(value)
        if qid < 0 or qid >= 196560:
            raise ValueError(f"Qubit ID {qid} out of range (0-196559)")
        return qid
    
    @staticmethod
    def validate(arg_spec, value):
        """
        Validate a single argument
        
        Args:
            arg_spec: Row from command_arguments table
            value: Value to validate
            
        Returns:
            (valid, converted_value_or_error)
        """
        arg_name = arg_spec['arg_name']
        arg_type = arg_spec['arg_type']
        required = arg_spec['required']
        default = arg_spec['default_value']
        vmin = arg_spec.get('validation_min')
        vmax = arg_spec.get('validation_max')
        pattern = arg_spec.get('validation_regex')
        enum_values = arg_spec.get('validation_enum')
        
        # Handle missing value
        if value is None:
            if required:
                return False, f"Missing required argument: {arg_name}"
            return True, default
        
        # Type conversion
        try:
            validator = ArgumentValidator.TYPE_VALIDATORS.get(arg_type, str)
            converted = validator(value)
        except (ValueError, TypeError) as e:
            return False, f"Invalid {arg_type} for {arg_name}: {value}"
        
        # Range validation
        if vmin is not None and converted < vmin:
            return False, f"{arg_name} must be >= {vmin}"
        if vmax is not None and converted > vmax:
            return False, f"{arg_name} must be <= {vmax}"
        
        # Pattern validation
        if pattern and not re.match(pattern, str(value)):
            return False, f"{arg_name} does not match pattern {pattern}"
        
        # Enum validation
        if enum_values:
            allowed = enum_values.split(',')
            if str(value) not in allowed:
                return False, f"{arg_name} must be one of: {enum_values}"
        
        return True, converted
    
    @staticmethod
    def validate_all(cmd_id, args_dict, conn):
        """
        Validate all arguments for a command
        
        Returns:
            (all_valid, validated_args_or_first_error)
        """
        c = conn.cursor()
        c.execute("""
            SELECT arg_position, arg_name, arg_type, required, default_value,
                   validation_min, validation_max, validation_regex, validation_enum
            FROM command_arguments WHERE cmd_id = ? ORDER BY arg_position
        """, (cmd_id,))
        
        validated = {}
        for row in c.fetchall():
            spec = {
                'arg_name': row[1],
                'arg_type': row[2],
                'required': row[3],
                'default_value': row[4],
                'validation_min': row[5],
                'validation_max': row[6],
                'validation_regex': row[7],
                'validation_enum': row[8]
            }
            
            value = args_dict.get(row[1])
            valid, result = ArgumentValidator.validate(spec, value)
            
            if not valid:
                return False, result
            validated[row[1]] = result
        
        return True, validated
''',
        'module_description': 'Command argument validation',
        'module_version': '1.0.0',
        'dependencies': 're'
    },
]


def insert_python_modules(conn):
    """Insert Python modules"""
    c = conn.cursor()
    now = time.time()
    inserted = 0
    
    for m in PYTHON_MODULES:
        try:
            c.execute("""
                INSERT OR REPLACE INTO system_python_modules
                (module_name, module_code, module_description, module_version, dependencies, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                m['module_name'],
                m['module_code'],
                m['module_description'],
                m['module_version'],
                m['dependencies'],
                now
            ))
            inserted += 1
        except sqlite3.Error as e:
            print(f"    Error inserting module '{m['module_name']}': {e}")
    
    conn.commit()
    return inserted


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 9: MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

def apply_patch(db_path=None):
    """Apply the complete database patch"""
    if db_path is None:
        db_path = DB_PATH
    
    print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║                    QUNIX DATABASE PATCH v{VERSION}                    ║
║                                                                               ║
║                    Part 1: First 70 Command Handlers                          ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    print(f"Target database: {db_path}")
    print()
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        # Phase 1: Ensure command_registry exists with cmd_id column FIRST
        print("Phase 1: Migrating command_registry...")
        migrated = migrate_command_registry(conn)
        print(f"         ✓ Migration complete ({migrated} existing commands)")
        
        # Phase 2: Create supporting schema (flags, args, handlers tables)
        print("Phase 2: Creating supporting schema...")
        c = conn.cursor()
        c.executescript(SCHEMA_PHASE1)
        conn.commit()
        print("         ✓ Schema created")
        
        # Phase 3: Commands
        print("Phase 3: Inserting commands...")
        inserted, updated = insert_commands(conn)
        print(f"         ✓ Commands: {inserted} inserted, {updated} updated")
        
        # Phase 4: Flags
        print("Phase 4: Inserting flags...")
        flags_count = insert_flags(conn)
        print(f"         ✓ Flags: {flags_count} inserted")
        
        # Phase 5: Arguments
        print("Phase 5: Inserting arguments...")
        args_count = insert_arguments(conn)
        print(f"         ✓ Arguments: {args_count} inserted")
        
        # Phase 6: Handlers
        print("Phase 6: Inserting handlers...")
        handlers_count = insert_handlers(conn)
        print(f"         ✓ Handlers: {handlers_count} inserted")
        
        # Phase 7: Circuit Templates
        print("Phase 7: Inserting circuit templates...")
        templates_count = insert_circuit_templates(conn)
        print(f"         ✓ Templates: {templates_count} inserted")
        
        # Phase 8: Python Modules
        print("Phase 8: Inserting Python modules...")
        modules_count = insert_python_modules(conn)
        print(f"         ✓ Modules: {modules_count} inserted")
        
        # Phase 9: Create views and triggers (AFTER command_registry has cmd_id)
        print("Phase 9: Creating views and triggers...")
        c = conn.cursor()
        c.executescript(SCHEMA_VIEWS_TRIGGERS)
        conn.commit()
        print("         ✓ Views and triggers created")
        
        # Phase 10: Verification
        print("Phase 10: Verifying installation...")
        print()
        
        c = conn.cursor()
        
        # Count totals
        c.execute("SELECT COUNT(*) FROM command_registry WHERE cmd_enabled = 1")
        total_cmds = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM command_flags WHERE enabled = 1")
        total_flags = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM command_arguments")
        total_args = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM command_handlers WHERE enabled = 1")
        total_handlers = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM quantum_circuit_templates")
        total_templates = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM system_python_modules")
        total_modules = c.fetchone()[0]
        
        # Handler types breakdown
        c.execute("""
            SELECT handler_type, COUNT(*) as cnt 
            FROM command_handlers WHERE enabled = 1 
            GROUP BY handler_type ORDER BY cnt DESC
        """)
        handler_types = c.fetchall()
        
        # Missing handlers
        c.execute("""
            SELECT cmd_name FROM command_registry 
            WHERE cmd_enabled = 1 
            AND cmd_id NOT IN (SELECT DISTINCT cmd_id FROM command_handlers WHERE enabled = 1)
            ORDER BY cmd_category, cmd_name
        """)
        missing = [row[0] for row in c.fetchall()]
        
        print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                           VERIFICATION REPORT                                 ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  Total Commands:           {total_cmds:>6}                                         ║
║  Total Flags:              {total_flags:>6}                                         ║
║  Total Arguments:          {total_args:>6}                                         ║
║  Total Handlers:           {total_handlers:>6}                                         ║
║  Circuit Templates:        {total_templates:>6}                                         ║
║  Python Modules:           {total_modules:>6}                                         ║
║                                                                               ║
║  Handler Types:                                                               ║""")
        
        for ht in handler_types:
            print(f"║    {ht[0]:20} {ht[1]:>6}                                         ║")
        
        print(f"""║                                                                               ║
║  Commands Missing Handlers: {len(missing):>6}                                         ║
║  (These will be added in Part 2)                                              ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
        """)
        
        if missing:
            print("\nCommands awaiting handlers (Part 2):")
            print("─" * 60)
            for i in range(0, len(missing), 6):
                row = missing[i:i+6]
                print("  " + ", ".join(row))
        
        # Test execution chain
        print("\n" + "═" * 60)
        print("EXECUTION CHAIN TEST: 'qh 0 -s 2048'")
        print("═" * 60)
        
        c.execute("""
            SELECT cr.cmd_id, cr.cmd_name, cr.cmd_opcode, ch.handler_type, ch.handler_id
            FROM command_registry cr
            JOIN command_handlers ch ON cr.cmd_id = ch.cmd_id
            WHERE cr.cmd_name = 'qh' AND ch.enabled = 1
        """)
        qh_row = c.fetchone()
        
        if qh_row:
            print(f"  1. Command lookup: qh -> cmd_id={qh_row[0]}, opcode=0x{qh_row[2]:04X}")
            print(f"  2. Handler found: type={qh_row[3]}, handler_id={qh_row[4]}")
            
            c.execute("SELECT flag_short, flag_bit FROM command_flags WHERE cmd_id = ?", (qh_row[0],))
            flags = c.fetchall()
            print(f"  3. Flags loaded: {[(f[0], f[1]) for f in flags]}")
            
            c.execute("SELECT arg_name, arg_type FROM command_arguments WHERE cmd_id = ?", (qh_row[0],))
            args = c.fetchall()
            print(f"  4. Arguments loaded: {[(a[0], a[1]) for a in args]}")
            
            print("  5. Execution chain: READY ✓")
        else:
            print("  ERROR: qh command not found!")
        
        print("\n" + "═" * 60)
        print("PATCH APPLIED SUCCESSFULLY")
        print("═" * 60)
        
        print("""
Test commands:
  SELECT * FROM v_command_complete WHERE cmd_name = 'qh';
  SELECT * FROM v_execution_chain WHERE cmd_name = 'ls';
  SELECT * FROM v_handler_stats LIMIT 10;
  SELECT * FROM v_missing_handlers;
        """)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
        
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = DB_PATH
    
    success = apply_patch(db_path)
    sys.exit(0 if success else 1)
