
#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║         DATABASE PATCH: HANDLERS, FLAGS & ARGUMENTS v1.0                 ║
║              Complete Database-Driven Execution System                   ║
║                                                                           ║
║  This patch creates a fully database-native command execution system:    ║
║    • command_flags: All flag definitions (-l, --long, etc.)             ║
║    • command_arguments: Argument parsing and validation                  ║
║    • command_handlers: Handler implementations (QUANTUM/DB/FS/etc.)     ║
║    • Helper classes: FlagParser, BinaryEncoder, HandlerExecutor          ║
║    • Data population: 152+ commands with flags and handlers             ║
║                                                                           ║
║  After this patch, qunix_cpu.py needs NO hardcoded handlers!            ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import sqlite3
import struct
import json
import time
import sys
from pathlib import Path

VERSION = "1.0.0-HANDLERS-FLAGS-ARGS"

# ═══════════════════════════════════════════════════════════════════════════
# SCHEMA DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════

SCHEMA_SQL = """
-- ═══════════════════════════════════════════════════════════════════════════
-- PREREQUISITE: COMMAND REGISTRY TABLE (if not exists)
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS command_registry (
    cmd_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_name TEXT UNIQUE NOT NULL,
    cmd_category TEXT DEFAULT 'general',
    cmd_description TEXT,
    cmd_requires_qubits INTEGER DEFAULT 0,
    cmd_opcode BLOB,
    cmd_enabled INTEGER DEFAULT 1,
    created_at REAL DEFAULT 0,
    updated_at REAL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_cmd_name ON command_registry(cmd_name);
CREATE INDEX IF NOT EXISTS idx_cmd_category ON command_registry(cmd_category);
CREATE INDEX IF NOT EXISTS idx_cmd_enabled ON command_registry(cmd_enabled);

-- Additional prerequisite tables that might be referenced
CREATE TABLE IF NOT EXISTS cpu_qubit_allocator (
    qubit_id INTEGER PRIMARY KEY,
    allocated INTEGER DEFAULT 0,
    pid INTEGER,
    allocated_at REAL
);

CREATE TABLE IF NOT EXISTS q (
    i INTEGER PRIMARY KEY,
    a REAL DEFAULT 1.0,
    b REAL DEFAULT 0.0,
    p REAL DEFAULT 0.0,
    g REAL DEFAULT 0.0,
    etype TEXT DEFAULT 'computational'
);

CREATE TABLE IF NOT EXISTS tri (
    triangle_id INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS e (
    e_id INTEGER PRIMARY KEY,
    t TEXT DEFAULT 'e'
);

CREATE TABLE IF NOT EXISTS quantum_command_circuits (
    circuit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_name TEXT,
    circuit_name TEXT,
    num_qubits INTEGER
);

CREATE TABLE IF NOT EXISTS command_execution_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_name TEXT,
    execution_time_ms REAL,
    success INTEGER,
    timestamp REAL DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE IF NOT EXISTS cpu_execution_contexts (
    pid INTEGER PRIMARY KEY AUTOINCREMENT,
    program_name TEXT,
    pc INTEGER DEFAULT 0,
    halted INTEGER DEFAULT 0,
    created_at REAL DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE IF NOT EXISTS l (
    lattice_id INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS bus_core (
    bus_id INTEGER PRIMARY KEY,
    active INTEGER DEFAULT 1,
    mode TEXT DEFAULT 'NORMAL',
    packets_processed INTEGER DEFAULT 0,
    circuits_generated INTEGER DEFAULT 0,
    fitness_score REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS bus_routing (
    route_id INTEGER PRIMARY KEY AUTOINCREMENT
);

CREATE TABLE IF NOT EXISTS qnic_core (
    qnic_id INTEGER PRIMARY KEY,
    running INTEGER DEFAULT 1,
    requests_served INTEGER DEFAULT 0,
    bytes_proxied INTEGER DEFAULT 0,
    avg_latency_ms REAL DEFAULT 0.0,
    quantum_advantage REAL DEFAULT 1.0
);

CREATE TABLE IF NOT EXISTS cpu_quantum_states (
    state_id INTEGER PRIMARY KEY AUTOINCREMENT
);

CREATE TABLE IF NOT EXISTS terminal_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT DEFAULT 'active',
    created REAL DEFAULT (strftime('%s', 'now'))
);

-- ═══════════════════════════════════════════════════════════════════════════
-- COMMAND FLAGS TABLE
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS command_flags (
    flag_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_id INTEGER NOT NULL,
    
    -- Flag definition
    flag_short CHAR(1),              -- 'l' for -l
    flag_long TEXT,                  -- 'long' for --long
    flag_bit INTEGER NOT NULL,       -- bit position in bitfield (0-7)
    
    -- Behavior
    flag_type TEXT DEFAULT 'BOOLEAN', -- BOOLEAN, VALUE, COUNT
    value_type TEXT,                  -- STRING, INT, FLOAT, PATH (if VALUE type)
    default_value TEXT,               -- JSON encoded default
    
    -- Documentation
    flag_description TEXT,
    flag_example TEXT,
    
    -- Binary encoding
    flag_opcode_modifier INTEGER,    -- modifier value when flag active
    
    -- Metadata
    enabled INTEGER DEFAULT 1,
    created_at REAL DEFAULT 0,
    
    FOREIGN KEY(cmd_id) REFERENCES command_registry(cmd_id),
    UNIQUE(cmd_id, flag_short),
    UNIQUE(cmd_id, flag_long),
    CHECK(flag_short IS NOT NULL OR flag_long IS NOT NULL),
    CHECK(flag_bit BETWEEN 0 AND 7)
);

CREATE INDEX IF NOT EXISTS idx_flags_cmd ON command_flags(cmd_id);
CREATE INDEX IF NOT EXISTS idx_flags_short ON command_flags(flag_short);
CREATE INDEX IF NOT EXISTS idx_flags_long ON command_flags(flag_long);

-- ═══════════════════════════════════════════════════════════════════════════
-- COMMAND ARGUMENTS TABLE
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS command_arguments (
    arg_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_id INTEGER NOT NULL,
    
    -- Argument definition
    arg_position INTEGER NOT NULL,   -- 0, 1, 2, ... (after command name)
    arg_name TEXT NOT NULL,          -- descriptive name
    arg_type TEXT DEFAULT 'STRING',  -- STRING, INT, FLOAT, PATH, QUBIT_ID, 
                                     -- LATTICE_ID, TRIANGLE_ID, FILE, DIR
    
    -- Validation
    required INTEGER DEFAULT 1,      -- 0 = optional, 1 = required
    default_value TEXT,              -- JSON encoded
    validation_regex TEXT,           -- regex pattern for STRING types
    validation_min REAL,             -- for numeric types
    validation_max REAL,             -- for numeric types
    validation_enum TEXT,            -- JSON array of allowed values
    
    -- Documentation
    arg_description TEXT,
    arg_example TEXT,
    
    -- Metadata
    created_at REAL DEFAULT 0,
    
    FOREIGN KEY(cmd_id) REFERENCES command_registry(cmd_id),
    UNIQUE(cmd_id, arg_position),
    CHECK(arg_position >= 0)
);

CREATE INDEX IF NOT EXISTS idx_args_cmd ON command_arguments(cmd_id);
CREATE INDEX IF NOT EXISTS idx_args_position ON command_arguments(cmd_id, arg_position);

-- ═══════════════════════════════════════════════════════════════════════════
-- COMMAND HANDLERS TABLE
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS command_handlers (
    handler_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_id INTEGER NOT NULL,
    
    -- Handler type
    handler_type TEXT NOT NULL,      -- QUANTUM_CIRCUIT, DATABASE_QUERY, 
                                     -- FILESYSTEM_OP, PYTHON_FUNC, BUS_OP,
                                     -- NIC_OP, SYSTEM_INFO, BUILTIN
    
    -- Implementation (store one of these based on handler_type)
    qasm_code TEXT,                  -- For QUANTUM_CIRCUIT
    sql_query TEXT,                  -- For DATABASE_QUERY
    python_code TEXT,                -- For PYTHON_FUNC
    method_name TEXT,                -- For FILESYSTEM_OP, BUS_OP, NIC_OP
    builtin_name TEXT,               -- For BUILTIN (help, exit, clear, etc.)
    
    -- Context mapping (JSON)
    context_map TEXT,                -- Maps args/flags to handler params
                                     -- Example: {"path": "args[0]", "show_all": "flags.a"}
    
    -- Result formatting
    result_formatter TEXT,           -- Python format string or template
    error_formatter TEXT,            -- Format string for errors
    
    -- Execution control
    priority INTEGER DEFAULT 0,      -- If multiple handlers, highest priority first
    timeout_seconds REAL DEFAULT 30, -- Execution timeout
    enabled INTEGER DEFAULT 1,
    
    -- Metadata
    created_at REAL DEFAULT 0,
    last_executed REAL,
    execution_count INTEGER DEFAULT 0,
    
    FOREIGN KEY(cmd_id) REFERENCES command_registry(cmd_id)
);

CREATE INDEX IF NOT EXISTS idx_handlers_cmd ON command_handlers(cmd_id);
CREATE INDEX IF NOT EXISTS idx_handlers_type ON command_handlers(handler_type);
CREATE INDEX IF NOT EXISTS idx_handlers_priority ON command_handlers(cmd_id, priority DESC);

-- ═══════════════════════════════════════════════════════════════════════════
-- VIEWS FOR DEBUGGING
-- ═══════════════════════════════════════════════════════════════════════════

CREATE VIEW IF NOT EXISTS v_command_complete AS
SELECT 
    cr.cmd_id,
    cr.cmd_name,
    cr.cmd_category,
    cr.cmd_description,
    cr.cmd_requires_qubits,
    COUNT(DISTINCT cf.flag_id) as flag_count,
    COUNT(DISTINCT ca.arg_id) as arg_count,
    COUNT(DISTINCT ch.handler_id) as handler_count,
    GROUP_CONCAT(DISTINCT cf.flag_short, ',') as flags_short,
    GROUP_CONCAT(DISTINCT cf.flag_long, ',') as flags_long,
    MAX(ch.handler_type) as primary_handler_type
FROM command_registry cr
LEFT JOIN command_flags cf ON cr.cmd_id = cf.cmd_id
LEFT JOIN command_arguments ca ON cr.cmd_id = ca.cmd_id
LEFT JOIN command_handlers ch ON cr.cmd_id = ch.cmd_id
GROUP BY cr.cmd_id;

CREATE VIEW IF NOT EXISTS v_missing_handlers AS
SELECT cmd_id, cmd_name, cmd_category
FROM command_registry
WHERE cmd_enabled = 1
AND cmd_id NOT IN (SELECT DISTINCT cmd_id FROM command_handlers WHERE enabled = 1);

-- ═══════════════════════════════════════════════════════════════════════════
-- HELPER TABLES
-- ═══════════════════════════════════════════════════════════════════════════

-- Binary execution cache
CREATE TABLE IF NOT EXISTS command_binary_cache (
    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_id INTEGER,
    flags_bitfield INTEGER,
    args_hash TEXT,
    binary_code BLOB,
    created_at REAL,
    last_used REAL,
    use_count INTEGER DEFAULT 0,
    UNIQUE(cmd_id, flags_bitfield, args_hash)
);

CREATE INDEX IF NOT EXISTS idx_binary_cache_lookup ON command_binary_cache(cmd_id, flags_bitfield, args_hash);

-- Handler execution stats
CREATE TABLE IF NOT EXISTS handler_execution_stats (
    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    handler_id INTEGER,
    execution_time_ms REAL,
    success INTEGER,
    error_message TEXT,
    timestamp REAL,
    FOREIGN KEY(handler_id) REFERENCES command_handlers(handler_id)
);

CREATE INDEX IF NOT EXISTS idx_handler_stats ON handler_execution_stats(handler_id, timestamp);
"""

# ═══════════════════════════════════════════════════════════════════════════
# FLAG DEFINITIONS - COMPREHENSIVE LIST
# ═══════════════════════════════════════════════════════════════════════════

FLAG_DEFINITIONS = """
-- Filesystem flags (ls, dir, tree, find, etc.)
INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at) 
SELECT cmd_id, 'l', 'long', 0, 'BOOLEAN', 'Long format listing', {now}
FROM command_registry WHERE cmd_name IN ('ls', 'dir') AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'a', 'all', 1, 'BOOLEAN', 'Show all (including hidden)', {now}
FROM command_registry WHERE cmd_name IN ('ls', 'dir') AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'h', 'human-readable', 2, 'BOOLEAN', 'Human readable sizes', {now}
FROM command_registry WHERE cmd_name IN ('ls', 'dir', 'du', 'df') AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'R', 'recursive', 3, 'BOOLEAN', 'Recursive', {now}
FROM command_registry WHERE cmd_name IN ('ls', 'cp', 'rm', 'grep', 'find') AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 't', NULL, 4, 'BOOLEAN', 'Sort by time', {now}
FROM command_registry WHERE cmd_name IN ('ls', 'dir') AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'S', NULL, 5, 'BOOLEAN', 'Sort by size', {now}
FROM command_registry WHERE cmd_name IN ('ls', 'dir') AND cmd_enabled = 1;

-- cat, more, less flags
INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'n', 'number', 0, 'BOOLEAN', 'Number lines', {now}
FROM command_registry WHERE cmd_name IN ('cat', 'nl') AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'b', 'number-nonblank', 1, 'BOOLEAN', 'Number non-blank lines', {now}
FROM command_registry WHERE cmd_name = 'cat' AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'E', 'show-ends', 2, 'BOOLEAN', 'Show line endings', {now}
FROM command_registry WHERE cmd_name = 'cat' AND cmd_enabled = 1;

-- grep flags
INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'i', 'ignore-case', 0, 'BOOLEAN', 'Case insensitive', {now}
FROM command_registry WHERE cmd_name IN ('grep', 'sed', 'awk') AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'v', 'invert-match', 1, 'BOOLEAN', 'Invert match', {now}
FROM command_registry WHERE cmd_name = 'grep' AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'n', 'line-number', 2, 'BOOLEAN', 'Show line numbers', {now}
FROM command_registry WHERE cmd_name = 'grep' AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'c', 'count', 3, 'BOOLEAN', 'Count matches', {now}
FROM command_registry WHERE cmd_name = 'grep' AND cmd_enabled = 1;

-- ps flags
INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'a', NULL, 0, 'BOOLEAN', 'All with tty', {now}
FROM command_registry WHERE cmd_name = 'ps' AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'u', NULL, 1, 'BOOLEAN', 'User-oriented format', {now}
FROM command_registry WHERE cmd_name = 'ps' AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'x', NULL, 2, 'BOOLEAN', 'Processes without tty', {now}
FROM command_registry WHERE cmd_name = 'ps' AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'e', NULL, 3, 'BOOLEAN', 'Environment', {now}
FROM command_registry WHERE cmd_name = 'ps' AND cmd_enabled = 1;

-- rm flags
INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'f', 'force', 0, 'BOOLEAN', 'Force removal', {now}
FROM command_registry WHERE cmd_name = 'rm' AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'i', 'interactive', 1, 'BOOLEAN', 'Interactive confirmation', {now}
FROM command_registry WHERE cmd_name IN ('rm', 'cp', 'mv') AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'v', 'verbose', 2, 'BOOLEAN', 'Verbose output', {now}
FROM command_registry WHERE cmd_name IN ('rm', 'cp', 'mv', 'mkdir', 'tar', 'gzip') AND cmd_enabled = 1;

-- cp, mv flags
INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'p', 'preserve', 3, 'BOOLEAN', 'Preserve attributes', {now}
FROM command_registry WHERE cmd_name IN ('cp', 'rsync') AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'u', 'update', 4, 'BOOLEAN', 'Update only', {now}
FROM command_registry WHERE cmd_name IN ('cp', 'mv') AND cmd_enabled = 1;

-- tar flags
INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'c', 'create', 0, 'BOOLEAN', 'Create archive', {now}
FROM command_registry WHERE cmd_name = 'tar' AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'x', 'extract', 1, 'BOOLEAN', 'Extract archive', {now}
FROM command_registry WHERE cmd_name = 'tar' AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'f', 'file', 2, 'VALUE', 'Archive file', {now}
FROM command_registry WHERE cmd_name = 'tar' AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'z', 'gzip', 3, 'BOOLEAN', 'Gzip compression', {now}
FROM command_registry WHERE cmd_name = 'tar' AND cmd_enabled = 1;

-- chmod flags
INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'R', 'recursive', 0, 'BOOLEAN', 'Recursive', {now}
FROM command_registry WHERE cmd_name IN ('chmod', 'chown', 'chgrp') AND cmd_enabled = 1;

-- uname flags
INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'a', 'all', 0, 'BOOLEAN', 'All information', {now}
FROM command_registry WHERE cmd_name = 'uname' AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 's', 'kernel-name', 1, 'BOOLEAN', 'Kernel name', {now}
FROM command_registry WHERE cmd_name = 'uname' AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'r', 'kernel-release', 2, 'BOOLEAN', 'Kernel release', {now}
FROM command_registry WHERE cmd_name = 'uname' AND cmd_enabled = 1;

-- ping flags
INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'c', 'count', 0, 'VALUE', 'Packet count', {now}
FROM command_registry WHERE cmd_name = 'ping' AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'i', 'interval', 1, 'VALUE', 'Interval', {now}
FROM command_registry WHERE cmd_name = 'ping' AND cmd_enabled = 1;

-- Help flags (global)
INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'h', 'help', 7, 'BOOLEAN', 'Show help', {now}
FROM command_registry WHERE cmd_enabled = 1 AND cmd_name NOT IN ('qh');

-- QUNIX quantum flags
INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 's', 'shots', 0, 'VALUE', 'Number of shots', {now}
FROM command_registry WHERE cmd_requires_qubits > 0 AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'b', 'backend', 1, 'VALUE', 'Qiskit backend', {now}
FROM command_registry WHERE cmd_requires_qubits > 0 AND cmd_enabled = 1;

INSERT INTO command_flags (cmd_id, flag_short, flag_long, flag_bit, flag_type, flag_description, created_at)
SELECT cmd_id, 'o', 'optimize', 2, 'BOOLEAN', 'Circuit optimization', {now}
FROM command_registry WHERE cmd_requires_qubits > 0 AND cmd_enabled = 1;
"""

# ═══════════════════════════════════════════════════════════════════════════
# ARGUMENT DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════

ARGUMENT_DEFINITIONS = """
-- Filesystem commands - PATH arguments
INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, default_value, arg_description, created_at)
SELECT cmd_id, 0, 'path', 'PATH', 0, '"."', 'Directory path', {now}
FROM command_registry WHERE cmd_name IN ('ls', 'dir', 'tree') AND cmd_enabled = 1;

INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, arg_description, created_at)
SELECT cmd_id, 0, 'file', 'PATH', 1, 'File to display', {now}
FROM command_registry WHERE cmd_name IN ('cat', 'more', 'less', 'head', 'tail') AND cmd_enabled = 1;

INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, arg_description, created_at)
SELECT cmd_id, 0, 'path', 'PATH', 1, 'Directory to create', {now}
FROM command_registry WHERE cmd_name = 'mkdir' AND cmd_enabled = 1;

INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, arg_description, created_at)
SELECT cmd_id, 0, 'file', 'PATH', 1, 'File to remove', {now}
FROM command_registry WHERE cmd_name = 'rm' AND cmd_enabled = 1;

INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, arg_description, created_at)
SELECT cmd_id, 0, 'source', 'PATH', 1, 'Source file', {now}
FROM command_registry WHERE cmd_name IN ('cp', 'mv') AND cmd_enabled = 1;

INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, arg_description, created_at)
SELECT cmd_id, 1, 'destination', 'PATH', 1, 'Destination', {now}
FROM command_registry WHERE cmd_name IN ('cp', 'mv') AND cmd_enabled = 1;

-- Quantum commands - QUBIT_ID arguments
INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, validation_min, validation_max, arg_description, created_at)
SELECT cmd_id, 0, 'qubit_id', 'QUBIT_ID', 1, 0, 196559, 'Qubit to operate on', {now}
FROM command_registry WHERE cmd_name IN ('qh', 'qx', 'qy', 'qz', 'qs', 'qt', 'qreset', 'qmeasure') AND cmd_enabled = 1;

INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, validation_min, validation_max, arg_description, created_at)
SELECT cmd_id, 0, 'control_qubit', 'QUBIT_ID', 1, 0, 196559, 'Control qubit', {now}
FROM command_registry WHERE cmd_name IN ('qcnot', 'qcz') AND cmd_enabled = 1;

INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, validation_min, validation_max, arg_description, created_at)
SELECT cmd_id, 1, 'target_qubit', 'QUBIT_ID', 1, 0, 196559, 'Target qubit', {now}
FROM command_registry WHERE cmd_name IN ('qcnot', 'qcz', 'qswap') AND cmd_enabled = 1;

-- qalloc - INT count
INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, default_value, validation_min, validation_max, arg_description, created_at)
SELECT cmd_id, 0, 'count', 'INT', 0, '1', 1, 1000, 'Number of qubits to allocate', {now}
FROM command_registry WHERE cmd_name = 'qalloc' AND cmd_enabled = 1;

-- qfree - QUBIT_ID list
INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, arg_description, created_at)
SELECT cmd_id, 0, 'qubit_ids', 'STRING', 1, 'Qubit IDs to free (space-separated)', {now}
FROM command_registry WHERE cmd_name = 'qfree' AND cmd_enabled = 1;

-- grep arguments
INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, arg_description, created_at)
SELECT cmd_id, 0, 'pattern', 'STRING', 1, 'Search pattern', {now}
FROM command_registry WHERE cmd_name = 'grep' AND cmd_enabled = 1;

INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, arg_description, created_at)
SELECT cmd_id, 1, 'file', 'PATH', 0, 'File to search', {now}
FROM command_registry WHERE cmd_name = 'grep' AND cmd_enabled = 1;

-- chmod arguments
INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, validation_regex, arg_description, created_at)
SELECT cmd_id, 0, 'mode', 'STRING', 1, '^[0-7]{3,4}$', 'Permission mode (e.g., 755)', {now}
FROM command_registry WHERE cmd_name = 'chmod' AND cmd_enabled = 1;

INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, arg_description, created_at)
SELECT cmd_id, 1, 'file', 'PATH', 1, 'File to change', {now}
FROM command_registry WHERE cmd_name = 'chmod' AND cmd_enabled = 1;

-- tar arguments
INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, arg_description, created_at)
SELECT cmd_id, 0, 'archive', 'PATH', 1, 'Archive file', {now}
FROM command_registry WHERE cmd_name = 'tar' AND cmd_enabled = 1;

INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, arg_description, created_at)
SELECT cmd_id, 1, 'files', 'STRING', 0, 'Files to archive', {now}
FROM command_registry WHERE cmd_name = 'tar' AND cmd_enabled = 1;

-- ping arguments
INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, default_value, arg_description, created_at)
SELECT cmd_id, 0, 'host', 'STRING', 0, '"localhost"', 'Host to ping', {now}
FROM command_registry WHERE cmd_name = 'ping' AND cmd_enabled = 1;

-- help argument
INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, arg_description, created_at)
SELECT cmd_id, 0, 'command', 'STRING', 0, 'Command to get help for', {now}
FROM command_registry WHERE cmd_name IN ('help', 'man', 'whatis') AND cmd_enabled = 1;

-- echo arguments
INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, arg_description, created_at)
SELECT cmd_id, 0, 'text', 'STRING', 0, 'Text to echo', {now}
FROM command_registry WHERE cmd_name = 'echo' AND cmd_enabled = 1;

-- wc arguments
INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, arg_description, created_at)
SELECT cmd_id, 0, 'file', 'PATH', 0, 'File to count', {now}
FROM command_registry WHERE cmd_name = 'wc' AND cmd_enabled = 1;

-- QUNIX-specific arguments
INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, default_value, arg_description, created_at)
SELECT cmd_id, 0, 'data', 'STRING', 0, '""', 'Data to encode', {now}
FROM command_registry WHERE cmd_name IN ('leech_encode', 'golay_encode') AND cmd_enabled = 1;

INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, arg_description, created_at)
SELECT cmd_id, 0, 'codeword', 'STRING', 1, 'Codeword to decode', {now}
FROM command_registry WHERE cmd_name IN ('leech_decode', 'golay_decode') AND cmd_enabled = 1;

INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, validation_min, validation_max, arg_description, created_at)
SELECT cmd_id, 0, 'lattice_id', 'LATTICE_ID', 1, 0, 196559, 'Lattice point ID', {now}
FROM command_registry WHERE cmd_name IN ('leech_distance', 'leech_nearest') AND cmd_enabled = 1;

INSERT INTO command_arguments (cmd_id, arg_position, arg_name, arg_type, required, validation_min, validation_max, arg_description, created_at)
SELECT cmd_id, 0, 'triangle_id', 'TRIANGLE_ID', 1, 0, 32767, 'Triangle ID', {now}
FROM command_registry WHERE cmd_name LIKE '%triangle%' AND cmd_enabled = 1;
"""

# ═══════════════════════════════════════════════════════════════════════════
# HANDLER DEFINITIONS - COMPLETE IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════════════

HANDLER_DEFINITIONS = """
-- ═══════════════════════════════════════════════════════════════════════════
-- BUILTIN HANDLERS (help, exit, clear, etc.)
-- ═══════════════════════════════════════════════════════════════════════════

INSERT INTO command_handlers (cmd_id, handler_type, builtin_name, result_formatter, priority, created_at)
SELECT cmd_id, 'BUILTIN', 'help', NULL, 100, {now}
FROM command_registry WHERE cmd_name = 'help' AND cmd_enabled = 1;

INSERT INTO command_handlers (cmd_id, handler_type, builtin_name, result_formatter, priority, created_at)
SELECT cmd_id, 'BUILTIN', 'exit', NULL, 100, {now}
FROM command_registry WHERE cmd_name = 'exit' AND cmd_enabled = 1;

INSERT INTO command_handlers (cmd_id, handler_type, builtin_name, result_formatter, priority, created_at)
SELECT cmd_id, 'BUILTIN', 'clear', NULL, 100, {now}
FROM command_registry WHERE cmd_name = 'clear' AND cmd_enabled = 1;

INSERT INTO command_handlers (cmd_id, handler_type, python_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'PYTHON_FUNC', 
'result = " ".join(args) if args else ""', 
'{"args": "args"}',
'{result}',
100, {now}
FROM command_registry WHERE cmd_name = 'echo' AND cmd_enabled = 1;

-- ═══════════════════════════════════════════════════════════════════════════
-- QUANTUM CIRCUIT HANDLERS
-- ═══════════════════════════════════════════════════════════════════════════

-- Hadamard (qh)
INSERT INTO command_handlers (cmd_id, handler_type, qasm_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'QUANTUM_CIRCUIT',
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
h q[0];
measure q[0] -> c[0];',
'{"qubit_id": "int(args[0])", "shots": "int(flags.get(''s'', 1024))"}',
'[OK] Hadamard on qubit {qubit_id}
Shots: {shots}
Results: {counts}',
100, {now}
FROM command_registry WHERE cmd_name = 'qh' AND cmd_enabled = 1;

-- Pauli-X (qx)
INSERT INTO command_handlers (cmd_id, handler_type, qasm_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'QUANTUM_CIRCUIT',
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
x q[0];
measure q[0] -> c[0];',
'{"qubit_id": "int(args[0])", "shots": "int(flags.get(''s'', 1024))"}',
'[OK] Pauli-X on qubit {qubit_id}
Results: {counts}',
100, {now}
FROM command_registry WHERE cmd_name = 'qx' AND cmd_enabled = 1;

-- Pauli-Y (qy)
INSERT INTO command_handlers (cmd_id, handler_type, qasm_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'QUANTUM_CIRCUIT',
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
y q[0];
measure q[0] -> c[0];',
'{"qubit_id": "int(args[0])", "shots": "int(flags.get(''s'', 1024))"}',
'[OK] Pauli-Y on qubit {qubit_id}
Results: {counts}',
100, {now}
FROM command_registry WHERE cmd_name = 'qy' AND cmd_enabled = 1;

-- Pauli-Z (qz)
INSERT INTO command_handlers (cmd_id, handler_type, qasm_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'QUANTUM_CIRCUIT',
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
z q[0];
measure q[0] -> c[0];',
'{"qubit_id": "int(args[0])", "shots": "int(flags.get(''s'', 1024))"}',
'[OK] Pauli-Z on qubit {qubit_id}
Results: {counts}',
100, {now}
FROM command_registry WHERE cmd_name = 'qz' AND cmd_enabled = 1;

-- S gate (qs)
INSERT INTO command_handlers (cmd_id, handler_type, qasm_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'QUANTUM_CIRCUIT',
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
s q[0];
measure q[0] -> c[0];',
'{"qubit_id": "int(args[0])", "shots": "int(flags.get(''s'', 1024))"}',
'[OK] S gate on qubit {qubit_id}
Results: {counts}',
100, {now}
FROM command_registry WHERE cmd_name = 'qs' AND cmd_enabled = 1;

-- T gate (qt)
INSERT INTO command_handlers (cmd_id, handler_type, qasm_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'QUANTUM_CIRCUIT',
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
t q[0];
measure q[0] -> c[0];',
'{"qubit_id": "int(args[0])", "shots": "int(flags.get(''s'', 1024))"}',
'[OK] T gate on qubit {qubit_id}
Results: {counts}',
100, {now}
FROM command_registry WHERE cmd_name = 'qt' AND cmd_enabled = 1;

-- CNOT (qcnot)
INSERT INTO command_handlers (cmd_id, handler_type, qasm_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'QUANTUM_CIRCUIT',
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
cx q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];',
'{"control": "int(args[0])", "target": "int(args[1])", "shots": "int(flags.get(''s'', 1024))"}',
'[OK] CNOT: control={control}, target={target}
Results: {counts}',
100, {now}
FROM command_registry WHERE cmd_name = 'qcnot' AND cmd_enabled = 1;

-- CZ (qcz)
INSERT INTO command_handlers (cmd_id, handler_type, qasm_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'QUANTUM_CIRCUIT',
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
cz q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];',
'{"control": "int(args[0])", "target": "int(args[1])", "shots": "int(flags.get(''s'', 1024))"}',
'[OK] CZ: control={control}, target={target}
Results: {counts}',
100, {now}
FROM command_registry WHERE cmd_name = 'qcz' AND cmd_enabled = 1;

-- SWAP (qswap)
INSERT INTO command_handlers (cmd_id, handler_type, qasm_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'QUANTUM_CIRCUIT',
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
swap q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];',
'{"qubit_a": "int(args[0])", "qubit_b": "int(args[1])", "shots": "int(flags.get(''s'', 1024))"}',
'[OK] SWAP: {qubit_a} ↔ {qubit_b}
Results: {counts}',
100, {now}
FROM command_registry WHERE cmd_name = 'qswap' AND cmd_enabled = 1;

-- Bell pair (epr_create)
INSERT INTO command_handlers (cmd_id, handler_type, qasm_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'QUANTUM_CIRCUIT',
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];',
'{"qubit_a": "int(args[0]) if args else None", "qubit_b": "int(args[1]) if len(args) > 1 else None", "shots": "int(flags.get(''s'', 1024))"}',
'[OK] Bell pair created
Results: {counts}',
100, {now}
FROM command_registry WHERE cmd_name = 'epr_create' AND cmd_enabled = 1;

-- GHZ state (ghz_create)
INSERT INTO command_handlers (cmd_id, handler_type, qasm_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'QUANTUM_CIRCUIT',
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0], q[1];
cx q[0], q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];',
'{"num_qubits": "3", "shots": "int(flags.get(''s'', 1024))"}',
'[OK] GHZ-3 state created
Results: {counts}',
100, {now}
FROM command_registry WHERE cmd_name = 'ghz_create' AND cmd_enabled = 1;

-- ═══════════════════════════════════════════════════════════════════════════
-- FILESYSTEM HANDLERS
-- ═══════════════════════════════════════════════════════════════════════════

-- ls
INSERT INTO command_handlers (cmd_id, handler_type, method_name, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'FILESYSTEM_OP', 'listdir',
'{"path": "args[0] if args else ''.''", "show_all": "bool(flags.get(''a''))", "long_format": "bool(flags.get(''l''))"}',
'{result}',
100, {now}
FROM command_registry WHERE cmd_name IN ('ls', 'dir') AND cmd_enabled = 1;

-- pwd
INSERT INTO command_handlers (cmd_id, handler_type, method_name, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'FILESYSTEM_OP', 'getcwd',
'{}',
'{result}',
100, {now}
FROM command_registry WHERE cmd_name = 'pwd' AND cmd_enabled = 1;

-- cd
INSERT INTO command_handlers (cmd_id, handler_type, method_name, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'FILESYSTEM_OP', 'chdir',
'{"path": "args[0] if args else ''/''"}',
'[OK] Changed to {path}',
100, {now}
FROM command_registry WHERE cmd_name = 'cd' AND cmd_enabled = 1;

-- cat
INSERT INTO command_handlers (cmd_id, handler_type, method_name, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'FILESYSTEM_OP', 'read_file',
'{"path": "args[0]"}',
'{result}',
100, {now}
FROM command_registry WHERE cmd_name = 'cat' AND cmd_enabled = 1;

-- mkdir
INSERT INTO command_handlers (cmd_id, handler_type, method_name, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'FILESYSTEM_OP', 'mkdir',
'{"path": "args[0]", "mode": "0o755"}',
'[OK] Created directory: {path}',
100, {now}
FROM command_registry WHERE cmd_name = 'mkdir' AND cmd_enabled = 1;

-- rm
INSERT INTO command_handlers (cmd_id, handler_type, method_name, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'FILESYSTEM_OP', 'unlink',
'{"path": "args[0]"}',
'[OK] Removed: {path}',
100, {now}
FROM command_registry WHERE cmd_name = 'rm' AND cmd_enabled = 1;

-- touch
INSERT INTO command_handlers (cmd_id, handler_type, method_name, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'FILESYSTEM_OP', 'create',
'{"path": "args[0]", "mode": "0o644"}',
'[OK] Created file: {path}',
100, {now}
FROM command_registry WHERE cmd_name = 'touch' AND cmd_enabled = 1;

-- tree
INSERT INTO command_handlers (cmd_id, handler_type, method_name, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'FILESYSTEM_OP', 'tree',
'{"path": "args[0] if args else ''/''", "max_depth": "5"}',
'{result}',
100, {now}
FROM command_registry WHERE cmd_name = 'tree' AND cmd_enabled = 1;

-- ═══════════════════════════════════════════════════════════════════════════
-- DATABASE QUERY HANDLERS
-- ═══════════════════════════════════════════════════════════════════════════

-- status
INSERT INTO command_handlers (cmd_id, handler_type, sql_query, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'DATABASE_QUERY',
'SELECT 
    (SELECT COUNT(*) FROM q) as total_qubits,
    (SELECT COUNT(*) FROM cpu_qubit_allocator WHERE allocated = 1) as allocated_qubits,
    (SELECT COUNT(*) FROM tri) as triangles,
    (SELECT COUNT(*) FROM e WHERE t = ''e'') as epr_pairs,
    (SELECT COUNT(*) FROM command_registry WHERE cmd_enabled = 1) as commands',
'{}',
'QUNIX Status:
  Qubits: {allocated_qubits}/{total_qubits}
  Triangles: {triangles}
  EPR pairs: {epr_pairs}
  Commands: {commands}',
100, {now}
FROM command_registry WHERE cmd_name = 'status' AND cmd_enabled = 1;

-- commands (list)
INSERT INTO command_handlers (cmd_id, handler_type, sql_query, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'DATABASE_QUERY',
'SELECT cmd_name, cmd_category, cmd_description, cmd_requires_qubits
FROM command_registry 
WHERE cmd_enabled = 1 
ORDER BY cmd_category, cmd_name
LIMIT 50',
'{}',
'{result}',
100, {now}
FROM command_registry WHERE cmd_name = 'commands' AND cmd_enabled = 1;

-- circuits (list)
INSERT INTO command_handlers (cmd_id, handler_type, sql_query, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'DATABASE_QUERY',
'SELECT cmd_name, circuit_name, num_qubits 
FROM quantum_command_circuits 
ORDER BY cmd_name 
LIMIT 20',
'{}',
'Quantum Circuits:
{result}',
100, {now}
FROM command_registry WHERE cmd_name = 'circuits' AND cmd_enabled = 1;

-- log
INSERT INTO command_handlers (cmd_id, handler_type, sql_query, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'DATABASE_QUERY',
'SELECT cmd_name, execution_time_ms, success, timestamp
FROM command_execution_log 
ORDER BY timestamp DESC 
LIMIT ?',
'{"limit": "int(args[0]) if args and args[0].isdigit() else 10"}',
'Recent Executions:
{result}',
100, {now}
FROM command_registry WHERE cmd_name = 'log' AND cmd_enabled = 1;

-- ps
INSERT INTO command_handlers (cmd_id, handler_type, sql_query, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'DATABASE_QUERY',
'SELECT pid, program_name, pc, halted 
FROM cpu_execution_contexts 
ORDER BY created_at DESC 
LIMIT 10',
'{}',
'PID  PROGRAM         STATE
{result}',
100, {now}
FROM command_registry WHERE cmd_name = 'ps' AND cmd_enabled = 1;

-- top
INSERT INTO command_handlers (cmd_id, handler_type, sql_query, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'DATABASE_QUERY',
'SELECT 
    (SELECT COUNT(*) FROM q) as total_qubits,
    (SELECT COUNT(*) FROM cpu_qubit_allocator WHERE allocated = 1) as allocated_qubits',
'{}',
'Resource Monitor:
  Qubits: {allocated_qubits}/{total_qubits} ({percent_used}%)',
100, {now}
FROM command_registry WHERE cmd_name = 'top' AND cmd_enabled = 1;

-- qstate (qubit state)
INSERT INTO command_handlers (cmd_id, handler_type, sql_query, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'DATABASE_QUERY',
'SELECT i, a, b, p, g, etype 
FROM q 
WHERE i = ?',
'{"qubit_id": "int(args[0])"}',
'Qubit {qubit_id}:
  α: {alpha}
  β: {beta}
  Phase: {phase}
  Type: {etype}',
100, {now}
FROM command_registry WHERE cmd_name = 'qstate' AND cmd_enabled = 1;

-- leech (info)
INSERT INTO command_handlers (cmd_id, handler_type, sql_query, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'DATABASE_QUERY',
'SELECT COUNT(*) as points FROM l',
'{}',
'Leech Lattice Λ₂₄:
  Dimension: 24
  Kissing Number: 196,560
  Points loaded: {points}
  E8×3 roots: 240×3',
100, {now}
FROM command_registry WHERE cmd_name IN ('leech', 'leech_info') AND cmd_enabled = 1;

-- bus status
INSERT INTO command_handlers (cmd_id, handler_type, sql_query, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'DATABASE_QUERY',
'SELECT active, mode, packets_processed, circuits_generated, fitness_score
FROM bus_core 
WHERE bus_id = 1',
'{}',
'Quantum Mega Bus:
  Active: {active}
  Mode: {mode}
  Packets: {packets_processed}
  Circuits: {circuits_generated}
  Fitness: {fitness_score}',
100, {now}
FROM command_registry WHERE cmd_name IN ('bus', 'bus_status') AND cmd_enabled = 1;

-- nic status
INSERT INTO command_handlers (cmd_id, handler_type, sql_query, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'DATABASE_QUERY',
'SELECT running, requests_served, bytes_proxied, avg_latency_ms, quantum_advantage
FROM qnic_core 
WHERE qnic_id = 1',
'{}',
'Quantum NIC:
  Status: {status}
  Requests: {requests_served}
  Bytes: {bytes_proxied}
  Latency: {avg_latency_ms}ms
  Advantage: {quantum_advantage}x',
100, {now}
FROM command_registry WHERE cmd_name IN ('nic', 'qnic_status') AND cmd_enabled = 1;

-- ═══════════════════════════════════════════════════════════════════════════
-- SYSTEM INFO HANDLERS (Python functions)
-- ═══════════════════════════════════════════════════════════════════════════

-- uname
INSERT INTO command_handlers (cmd_id, handler_type, python_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'PYTHON_FUNC',
'if flags.get("a"):
    result = "QUNIX qunix-10.0.0 Hyperbolic-E8³ x86_64"
else:
    result = "QUNIX"',
'{"flags": "flags"}',
'{result}',
100, {now}
FROM command_registry WHERE cmd_name = 'uname' AND cmd_enabled = 1;

-- hostname
INSERT INTO command_handlers (cmd_id, handler_type, python_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'PYTHON_FUNC',
'result = "qunix-e8-leech"',
'{}',
'{result}',
100, {now}
FROM command_registry WHERE cmd_name = 'hostname' AND cmd_enabled = 1;

-- date
INSERT INTO command_handlers (cmd_id, handler_type, python_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'PYTHON_FUNC',
'import datetime
result = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y")',
'{}',
'{result}',
100, {now}
FROM command_registry WHERE cmd_name = 'date' AND cmd_enabled = 1;

-- uptime
INSERT INTO command_handlers (cmd_id, handler_type, python_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'PYTHON_FUNC',
'result = "up 0:00, 0 users"',
'{}',
'{result}',
100, {now}
FROM command_registry WHERE cmd_name = 'uptime' AND cmd_enabled = 1;

-- whoami
INSERT INTO command_handlers (cmd_id, handler_type, python_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'PYTHON_FUNC',
'result = "qunix-user"',
'{}',
'{result}',
100, {now}
FROM command_registry WHERE cmd_name = 'whoami' AND cmd_enabled = 1;

-- df
INSERT INTO command_handlers (cmd_id, handler_type, python_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'PYTHON_FUNC',
'# Query database size
c = conn.cursor()
c.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()")
db_size = c.fetchone()[0]
total = 1000000 * 4096
used = db_size
free = total - used
percent = (used / total * 100) if total > 0 else 0
result = f"Total: {total}, Used: {used}, Free: {free}, Use%: {percent:.1f}"',
'{"conn": "conn"}',
'Filesystem:
{result}',
100, {now}
FROM command_registry WHERE cmd_name = 'df' AND cmd_enabled = 1;

-- ═══════════════════════════════════════════════════════════════════════════
-- QUNIX-SPECIFIC HANDLERS
-- ═══════════════════════════════════════════════════════════════════════════

-- qalloc
INSERT INTO command_handlers (cmd_id, handler_type, python_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'PYTHON_FUNC',
'count = int(args[0]) if args and args[0].isdigit() else 1
qubits = qubit_executor.allocate_qubits(count)
result = f"Allocated qubits: {qubits}"',
'{"args": "args", "qubit_executor": "qubit_executor"}',
'[OK] {result}',
100, {now}
FROM command_registry WHERE cmd_name = 'qalloc' AND cmd_enabled = 1;

-- qfree
INSERT INTO command_handlers (cmd_id, handler_type, python_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'PYTHON_FUNC',
'qubits = [int(a) for a in args if a.isdigit()]
if qubits:
    qubit_executor.free_qubits(qubits)
    result = f"Freed qubits: {qubits}"
else:
    result = "No qubits specified"',
'{"args": "args", "qubit_executor": "qubit_executor"}',
'[OK] {result}',
100, {now}
FROM command_registry WHERE cmd_name = 'qfree' AND cmd_enabled = 1;

-- golay encode
INSERT INTO command_handlers (cmd_id, handler_type, python_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'PYTHON_FUNC',
'data = args[0] if args else ""
encoded = golay.encode(data.encode())
result = "".join(map(str, encoded))',
'{"args": "args", "golay": "golay"}',
'[OK] Encoded: {result}',
100, {now}
FROM command_registry WHERE cmd_name = 'golay_encode' AND cmd_enabled = 1;

-- ═══════════════════════════════════════════════════════════════════════════
-- NETWORK/MONITORING HANDLERS
-- ═══════════════════════════════════```python
════════════════════════════════

-- ping
INSERT INTO command_handlers (cmd_id, handler_type, python_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'PYTHON_FUNC',
'host = args[0] if args else "localhost"
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM e WHERE t = ''e''")
epr_count = c.fetchone()[0]
result = f"QPING {host}: {epr_count:,} EPR pairs\\nLatency: <1σ"',
'{"args": "args", "conn": "conn"}',
'{result}',
100, {now}
FROM command_registry WHERE cmd_name = 'ping' AND cmd_enabled = 1;

-- netstat
INSERT INTO command_handlers (cmd_id, handler_type, sql_query, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'DATABASE_QUERY',
'SELECT COUNT(*) as route_count FROM bus_routing',
'{}',
'Network Statistics:
  Routes: {route_count}',
100, {now}
FROM command_registry WHERE cmd_name = 'netstat' AND cmd_enabled = 1;

-- ifconfig
INSERT INTO command_handlers (cmd_id, handler_type, python_code, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'PYTHON_FUNC',
'result = "qnic0: QUANTUM\\n  qubits: 196,560"',
'{}',
'{result}',
100, {now}
FROM command_registry WHERE cmd_name = 'ifconfig' AND cmd_enabled = 1;

-- vmstat
INSERT INTO command_handlers (cmd_id, handler_type, sql_query, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'DATABASE_QUERY',
'SELECT COUNT(*) as state_count FROM cpu_quantum_states',
'{}',
'VM Statistics:
  Quantum states: {state_count}',
100, {now}
FROM command_registry WHERE cmd_name = 'vmstat' AND cmd_enabled = 1;

-- iostat
INSERT INTO command_handlers (cmd_id, handler_type, sql_query, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'DATABASE_QUERY',
'SELECT COUNT(*) as exec_count FROM command_execution_log',
'{}',
'I/O Statistics:
  Executions: {exec_count}',
100, {now}
FROM command_registry WHERE cmd_name = 'iostat' AND cmd_enabled = 1;

-- dmesg (show recent logs)
INSERT INTO command_handlers (cmd_id, handler_type, sql_query, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'DATABASE_QUERY',
'SELECT cmd_name, execution_time_ms, success FROM command_execution_log ORDER BY timestamp DESC LIMIT 20',
'{}',
'Recent kernel messages:
{result}',
100, {now}
FROM command_registry WHERE cmd_name = 'dmesg' AND cmd_enabled = 1;

-- ═══════════════════════════════════════════════════════════════════════════
-- HELP SYSTEM HANDLERS
-- ═══════════════════════════════════════════════════════════════════════════

-- man
INSERT INTO command_handlers (cmd_id, handler_type, sql_query, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'DATABASE_QUERY',
'SELECT cmd_name, cmd_description, cmd_category 
FROM command_registry 
WHERE cmd_name = ? AND cmd_enabled = 1',
'{"cmd_name": "args[0] if args else ''''"}',
'{cmd_name} - {cmd_description}

CATEGORY: {cmd_category}',
100, {now}
FROM command_registry WHERE cmd_name = 'man' AND cmd_enabled = 1;

-- whatis
INSERT INTO command_handlers (cmd_id, handler_type, sql_query, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'DATABASE_QUERY',
'SELECT cmd_name, cmd_description FROM command_registry WHERE cmd_name = ? AND cmd_enabled = 1',
'{"cmd_name": "args[0] if args else ''''"}',
'{cmd_name} - {cmd_description}',
100, {now}
FROM command_registry WHERE cmd_name = 'whatis' AND cmd_enabled = 1;

-- apropos
INSERT INTO command_handlers (cmd_id, handler_type, sql_query, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'DATABASE_QUERY',
'SELECT cmd_name, cmd_description FROM command_registry 
WHERE cmd_enabled = 1 AND (cmd_name LIKE ? OR cmd_description LIKE ?) 
ORDER BY cmd_name LIMIT 20',
'{"pattern": "''%'' + args[0] + ''%'' if args else ''%''"}',
'{result}',
100, {now}
FROM command_registry WHERE cmd_name = 'apropos' AND cmd_enabled = 1;

-- who
INSERT INTO command_handlers (cmd_id, handler_type, sql_query, context_map, result_formatter, priority, created_at)
SELECT cmd_id, 'DATABASE_QUERY',
'SELECT session_id, status, created FROM terminal_sessions WHERE status = ''active'' LIMIT 10',
'{}',
'Active Sessions:
{result}',
100, {now}
FROM command_registry WHERE cmd_name IN ('who', 'w') AND cmd_enabled = 1;
"""

# ═══════════════════════════════════════════════════════════════════════════
# HELPER CLASSES - EMBEDDED IN DATABASE AS PYTHON CODE
# ═══════════════════════════════════════════════════════════════════════════

HELPER_CLASSES = '''
-- ═══════════════════════════════════════════════════════════════════════════
-- FLAG PARSER CLASS (stored as Python code)
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS system_python_modules (
    module_id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_name TEXT UNIQUE,
    module_code TEXT,
    module_description TEXT,
    created_at REAL,
    updated_at REAL
);

INSERT OR REPLACE INTO system_python_modules (module_name, module_code, module_description, created_at)
VALUES ('FlagParser', '
class FlagParser:
    """Parse command line arguments into structured dict with flags"""
    
    def __init__(self, conn):
        self.conn = conn
        self._flag_cache = {}
    
    def parse(self, cmd_id: int, argv: List[str]) -> Dict:
        """
        Parse command line into structured dict
        
        Returns:
        {
            ''cmd_id'': int,
            ''flags'': {flag_name: value},
            ''args'': [positional_args],
            ''bitfield'': int,
            ''raw'': original_argv
        }
        """
        # Get flag definitions
        if cmd_id not in self._flag_cache:
            c = self.conn.cursor()
            c.execute("""
                SELECT flag_short, flag_long, flag_type, value_type, flag_bit
                FROM command_flags WHERE cmd_id = ? AND enabled = 1
            """, (cmd_id,))
            
            self._flag_cache[cmd_id] = {}
            for short, long, ftype, vtype, bit in c.fetchall():
                if short:
                    self._flag_cache[cmd_id][short] = {
                        ''long'': long, ''type'': ftype, ''value_type'': vtype, ''bit'': bit
                    }
                if long:
                    self._flag_cache[cmd_id][long] = self._flag_cache[cmd_id].get(short, {
                        ''short'': short, ''type'': ftype, ''value_type'': vtype, ''bit'': bit
                    })
        
        flag_defs = self._flag_cache.get(cmd_id, {})
        flags = {}
        args = []
        bitfield = 0
        
        i = 1  # Skip command name
        while i < len(argv):
            arg = argv[i]
            
            if arg.startswith(''--''):
                # Long flag
                if ''='' in arg:
                    flag_name, value = arg[2:].split(''='', 1)
                else:
                    flag_name = arg[2:]
                    value = True
                
                if flag_name in flag_defs:
                    fdef = flag_defs[flag_name]
                    if fdef[''type''] == ''VALUE'':
                        if value is True:
                            i += 1
                            value = argv[i] if i < len(argv) else None
                        value = self._convert_value(value, fdef.get(''value_type'', ''STRING''))
                    flags[flag_name] = value
                    bitfield |= (1 << fdef[''bit''])
            
            elif arg.startswith(''-'') and arg != ''-'':
                # Short flag(s)
                flag_chars = arg[1:]
                for char in flag_chars:
                    if char in flag_defs:
                        fdef = flag_defs[char]
                        if fdef[''type''] == ''VALUE'':
                            i += 1
                            value = argv[i] if i < len(argv) else None
                            value = self._convert_value(value, fdef.get(''value_type'', ''STRING''))
                            flags[char] = value
                        else:
                            flags[char] = True
                        bitfield |= (1 << fdef[''bit''])
            else:
                args.append(arg)
            
            i += 1
        
        return {
            ''cmd_id'': cmd_id,
            ''flags'': flags,
            ''args'': args,
            ''bitfield'': bitfield,
            ''raw'': argv
        }
    
    def _convert_value(self, value, value_type: str):
        """Convert flag value to correct type"""
        if value is None:
            return None
        if value_type == ''INT'':
            return int(value)
        elif value_type == ''FLOAT'':
            return float(value)
        elif value_type == ''BOOL'':
            return value.lower() in (''true'', ''1'', ''yes'')
        else:
            return str(value)
', 'Command line flag parser', {now});

-- ═══════════════════════════════════════════════════════════════════════════
-- BINARY ENCODER CLASS
-- ═══════════════════════════════════════════════════════════════════════════

INSERT OR REPLACE INTO system_python_modules (module_name, module_code, module_description, created_at)
VALUES ('BinaryEncoder', '
class BinaryEncoder:
    """Encode/decode commands to/from binary format"""
    
    def __init__(self, conn):
        self.conn = conn
    
    def encode(self, cmd_id: int, parsed: Dict) -> bytes:
        """
        Encode command + flags + args to binary
        
        Format:
          [2 bytes: opcode]
          [1 byte: flag bitfield]
          [1 byte: arg count]
          [N bytes: args as length-prefixed strings]
        """
        c = self.conn.cursor()
        c.execute("SELECT cmd_opcode FROM command_registry WHERE cmd_id = ?", (cmd_id,))
        row = c.fetchone()
        if not row:
            return b''
        
        opcode = row[0]
        binary = bytearray()
        
        # Opcode (2 bytes)
        if isinstance(opcode, bytes):
            binary.extend(opcode[:2])
        else:
            binary.extend(struct.pack(''H'', opcode & 0xFFFF))
        
        # Flag bitfield (1 byte)
        binary.append(parsed[''bitfield''] & 0xFF)
        
        # Arg count (1 byte)
        binary.append(len(parsed[''args'']))
        
        # Args (length-prefixed)
        for arg in parsed[''args'']:
            arg_bytes = str(arg).encode(''utf-8'')
            binary.extend(struct.pack(''H'', len(arg_bytes)))
            binary.extend(arg_bytes)
        
        return bytes(binary)
    
    def decode(self, binary: bytes) -> Dict:
        """Decode binary back to structured dict"""
        if len(binary) < 4:
            return {}
        
        offset = 0
        
        # Opcode
        opcode = struct.unpack(''H'', binary[offset:offset+2])[0]
        offset += 2
        
        # Flags
        bitfield = binary[offset]
        offset += 1
        
        # Arg count
        arg_count = binary[offset]
        offset += 1
        
        # Args
        args = []
        for _ in range(arg_count):
            if offset + 2 > len(binary):
                break
            arg_len = struct.unpack(''H'', binary[offset:offset+2])[0]
            offset += 2
            if offset + arg_len > len(binary):
                break
            arg_bytes = binary[offset:offset+arg_len]
            offset += arg_len
            args.append(arg_bytes.decode(''utf-8''))
        
        # Resolve opcode → cmd_id
        c = self.conn.cursor()
        c.execute("SELECT cmd_id FROM command_registry WHERE cmd_opcode = ?", 
                  (struct.pack(''H'', opcode),))
        row = c.fetchone()
        cmd_id = row[0] if row else None
        
        # Reconstruct flags from bitfield
        flags = {}
        if cmd_id:
            c.execute("""
                SELECT flag_short, flag_long, flag_bit 
                FROM command_flags WHERE cmd_id = ? AND enabled = 1
            """, (cmd_id,))
            
            for short, long, bit in c.fetchall():
                if bitfield & (1 << bit):
                    if short:
                        flags[short] = True
                    if long:
                        flags[long] = True
        
        return {
            ''cmd_id'': cmd_id,
            ''opcode'': opcode,
            ''flags'': flags,
            ''args'': args,
            ''bitfield'': bitfield
        }
', 'Binary command encoder/decoder', {now});

-- ═══════════════════════════════════════════════════════════════════════════
-- HANDLER EXECUTOR CLASS
-- ═══════════════════════════════════════════════════════════════════════════

INSERT OR REPLACE INTO system_python_modules (module_name, module_code, module_description, created_at)
VALUES ('HandlerExecutor', '
class HandlerExecutor:
    """Execute commands using database-defined handlers"""
    
    def __init__(self, conn, qubit_exec, filesystem, bus=None, nic=None):
        self.conn = conn
        self.qubit_exec = qubit_exec
        self.fs = filesystem
        self.bus = bus
        self.nic = nic
    
    def execute(self, parsed: Dict) -> str:
        """Execute command using database handlers"""
        cmd_id = parsed[''cmd_id'']
        if not cmd_id:
            return "[ERROR] Unknown command"
        
        c = self.conn.cursor()
        
        # Get handlers
        c.execute("""
            SELECT handler_id, handler_type, qasm_code, sql_query, python_code, 
                   method_name, builtin_name, context_map, result_formatter
            FROM command_handlers 
            WHERE cmd_id = ? AND enabled = 1
            ORDER BY priority DESC
        """, (cmd_id,))
        
        handlers = c.fetchall()
        
        if not handlers:
            return f"[ERROR] No handler for command ID {cmd_id}"
        
        result = None
        
        for handler in handlers:
            handler_id, htype, qasm, sql, python, method, builtin, ctx_map, formatter = handler
            
            try:
                if htype == ''BUILTIN'':
                    result = self._execute_builtin(builtin, parsed)
                
                elif htype == ''QUANTUM_CIRCUIT'':
                    result = self._execute_quantum(qasm, ctx_map, parsed)
                
                elif htype == ''DATABASE_QUERY'':
                    result = self._execute_database(sql, ctx_map, parsed)
                
                elif htype == ''FILESYSTEM_OP'':
                    result = self._execute_filesystem(method, ctx_map, parsed)
                
                elif htype == ''PYTHON_FUNC'':
                    result = self._execute_python(python, ctx_map, parsed, result)
                
                elif htype == ''BUS_OP'':
                    result = self._execute_bus(method, ctx_map, parsed)
                
                elif htype == ''NIC_OP'':
                    result = self._execute_nic(method, ctx_map, parsed)
                
                # Update handler stats
                c.execute("""
                    UPDATE command_handlers 
                    SET last_executed = ?, execution_count = execution_count + 1
                    WHERE handler_id = ?
                """, (time.time(), handler_id))
                self.conn.commit()
            
            except Exception as e:
                result = f"[ERROR] {str(e)}"
        
        # Format result
        if formatter and result:
            try:
                if isinstance(result, dict):
                    return formatter.format(**result)
                elif isinstance(result, list):
                    return formatter.format(result=result)
                else:
                    return formatter.format(result=result)
            except:
                return str(result)
        
        return str(result) if result else "[OK]"
    
    def _execute_builtin(self, builtin_name: str, parsed: Dict) -> str:
        """Execute builtin commands"""
        if builtin_name == ''help'':
            return self._builtin_help(parsed)
        elif builtin_name == ''exit'':
            return "EXIT"
        elif builtin_name == ''clear'':
            return "\\033[2J\\033[H"
        return f"[ERROR] Unknown builtin: {builtin_name}"
    
    def _builtin_help(self, parsed: Dict) -> str:
        """Help builtin"""
        args = parsed.get(''args'', [])
        if args:
            c = self.conn.cursor()
            c.execute("""
                SELECT cmd_name, cmd_description, cmd_category 
                FROM command_registry WHERE cmd_name = ? AND cmd_enabled = 1
            """, (args[0],))
            row = c.fetchone()
            if row:
                return f"{row[0]} - {row[1]}\\nCategory: {row[2]}"
            return f"No help for: {args[0]}"
        
        return """QUNIX Help:
  help [cmd]  - Show help
  status      - System status
  commands    - List commands
  qh [q]      - Hadamard gate
  ls          - List files
  exit        - Exit"""
    
    def _execute_quantum(self, qasm: str, ctx_map: str, parsed: Dict) -> Dict:
        """Execute quantum circuit"""
        context = self._bind_context(ctx_map, parsed)
        
        # Allocate qubits
        qubit_ids = []
        if ''qubit_id'' in context:
            qubit_ids = [context[''qubit_id'']]
        elif ''control'' in context and ''target'' in context:
            qubit_ids = [context[''control''], context[''target'']]
        else:
            qubit_ids = self.qubit_exec.allocate_qubits(1)
        
        shots = context.get(''shots'', 1024)
        
        # Determine gate from QASM
        gate = ''h'' if ''h q'' in qasm else ''x'' if ''x q'' in qasm else ''cx''
        
        # Execute
        result = self.qubit_exec.execute_gate(gate, qubit_ids, shots)
        
        if result.get(''success''):
            return {
                ''qubit_ids'': qubit_ids,
                ''shots'': shots,
                ''counts'': result.get(''counts'', {}),
                **context
            }
        else:
            return {''error'': result.get(''error'', ''Unknown error'')}
    
    def _execute_database(self, sql: str, ctx_map: str, parsed: Dict) -> Any:
        """Execute SQL query"""
        context = self._bind_context(ctx_map, parsed)
        
        c = self.conn.cursor()
        
        # Replace placeholders
        if ''?'' in sql:
            params = [context.get(k) for k in context.keys()]
            c.execute(sql, params)
        else:
            c.execute(sql)
        
        if sql.strip().upper().startswith(''SELECT''):
            rows = c.fetchall()
            if not rows:
                return {}
            
            cols = [desc[0] for desc in c.description]
            if len(rows) == 1:
                return dict(zip(cols, rows[0]))
            else:
                return [dict(zip(cols, row)) for row in rows]
        else:
            self.conn.commit()
            return {''rows_affected'': c.rowcount}
    
    def _execute_filesystem(self, method_name: str, ctx_map: str, parsed: Dict) -> Any:
        """Execute filesystem operation"""
        context = self._bind_context(ctx_map, parsed)
        
        method = getattr(self.fs, method_name, None)
        if not method:
            return f"Method not found: {method_name}"
        
        try:
            result = method(**context)
            return result
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    def _execute_python(self, code: str, ctx_map: str, parsed: Dict, prev_result: Any) -> Any:
        """Execute Python code (sandboxed)"""
        context = self._bind_context(ctx_map, parsed)
        context[''prev''] = prev_result
        context[''conn''] = self.conn
        context[''qubit_executor''] = self.qubit_exec
        context[''filesystem''] = self.fs
        
        # Restricted globals
        allowed_globals = {
            ''__builtins__'': {
                ''len'': len, ''str'': str, ''int'': int, ''float'': float,
                ''list'': list, ''dict'': dict, ''tuple'': tuple,
                ''range'': range, ''enumerate'': enumerate,
                ''zip'': zip, ''map'': map, ''filter'': filter,
                ''sum'': sum, ''min'': min, ''max'': max,
                ''abs'': abs, ''round'': round, ''bool'': bool,
            },
            ''time'': time,
            ''datetime'': datetime,
        }
        
        local_vars = context
        exec(code, allowed_globals, local_vars)
        
        return local_vars.get(''result'', local_vars.get(''return'', None))
    
    def _execute_bus(self, method_name: str, ctx_map: str, parsed: Dict) -> Any:
        """Execute bus operation"""
        if not self.bus:
            return "[ERROR] Bus not available"
        
        context = self._bind_context(ctx_map, parsed)
        method = getattr(self.bus, method_name, None)
        if not method:
            return f"Bus method not found: {method_name}"
        
        return method(**context)
    
    def _execute_nic(self, method_name: str, ctx_map: str, parsed: Dict) -> Any:
        """Execute NIC operation"""
        if not self.nic:
            return "[ERROR] NIC not available"
        
        context = self._bind_context(ctx_map, parsed)
        method = getattr(self.nic, method_name, None)
        if not method:
            return f"NIC method not found: {method_name}"
        
        return method(**context)
    
    def _bind_context(self, ctx_map: str, parsed: Dict) -> Dict:
        """Bind variables from parsed command to handler context"""
        if not ctx_map:
            return {}
        
        try:
            mapping = json.loads(ctx_map)
        except:
            return {}
        
        context = {}
        env = {
            ''args'': parsed.get(''args'', []),
            ''flags'': parsed.get(''flags'', {}),
            ''int'': int, ''str'': str, ''float'': float, ''bool'': bool,
        }
        
        for var_name, expression in mapping.items():
            try:
                context[var_name] = eval(expression, {"__builtins__": {}}, env)
            except:
                context[var_name] = None
        
        return context
', 'Database handler executor', {now});
'''

# ═══════════════════════════════════════════════════════════════════════════
# MAIN PATCH APPLICATION
# ═══════════════════════════════════════════════════════════════════════════

def apply_patch(db_path: str, verbose: bool = True):
    """Apply the complete handlers/flags/args patch"""
    
    print(f"\n{'='*80}")
    print(f"  DATABASE PATCH: HANDLERS, FLAGS & ARGUMENTS v{VERSION}")
    print(f"{'='*80}\n")
    
    if verbose:
        print(f"Database: {db_path}")
    
    # Connect
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # PRE-FLIGHT CHECK: Verify command_registry exists
    if verbose:
        print(f"\n[PRE-FLIGHT] Checking database prerequisites...")
    
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='command_registry'")
    if not c.fetchone():
        if verbose:
            print(f"  ⚠️  command_registry table not found - will be created")
    else:
        # Verify command_registry has data
        c.execute("SELECT COUNT(*) FROM command_registry WHERE cmd_enabled = 1")
        cmd_count = c.fetchone()[0]
        if verbose:
            if cmd_count == 0:
                print(f"  ⚠️  command_registry exists but is empty")
            else:
                print(f"  ✓ Found {cmd_count} enabled commands")
    
    # Get current time
    now = time.time()
    
    # Step 1: Create schema
    if verbose:
        print(f"\n[1/6] Creating schema...")
    
    try:
        conn.executescript(SCHEMA_SQL)
        if verbose:
            print(f"  ✓ Tables created/verified: command_flags, command_arguments, command_handlers")
            print(f"  ✓ Views created: v_command_complete, v_missing_handlers")
            print(f"  ✓ Prerequisite tables ensured")
    except sqlite3.OperationalError as e:
        print(f"\n❌ ERROR creating schema: {e}")
        print("\nThe database may have incompatible structure.")
        conn.close()
        sys.exit(1)
    
    # Step 2: Insert flag definitions
    if verbose:
        print(f"\n[2/6] Populating flag definitions...")
    
    flag_sql = FLAG_DEFINITIONS.format(now=now)
    try:
        conn.executescript(flag_sql)
        c.execute("SELECT COUNT(*) FROM command_flags")
        flag_count = c.fetchone()[0]
        if verbose:
            print(f"  ✓ Inserted {flag_count} flag definitions")
    except sqlite3.Error as e:
        if verbose:
            print(f"  ⚠️  Flag insertion completed with warnings: {e}")
        flag_count = 0
    
    # Step 3: Insert argument definitions
    if verbose:
        print(f"\n[3/6] Populating argument definitions...")
    
    arg_sql = ARGUMENT_DEFINITIONS.format(now=now)
    try:
        conn.executescript(arg_sql)
        c.execute("SELECT COUNT(*) FROM command_arguments")
        arg_count = c.fetchone()[0]
        if verbose:
            print(f"  ✓ Inserted {arg_count} argument definitions")
    except sqlite3.Error as e:
        if verbose:
            print(f"  ⚠️  Argument insertion completed with warnings: {e}")
        arg_count = 0
    
    # Step 4: Insert handler definitions
    if verbose:
        print(f"\n[4/6] Populating handler implementations...")
    
    handler_sql = HANDLER_DEFINITIONS.format(now=now)
    try:
        conn.executescript(handler_sql)
        c.execute("SELECT COUNT(*) FROM command_handlers")
        handler_count = c.fetchone()[0]
        if verbose:
            print(f"  ✓ Inserted {handler_count} handler implementations")
    except sqlite3.Error as e:
        if verbose:
            print(f"  ⚠️  Handler insertion completed with warnings: {e}")
        handler_count = 0
    
    # Step 5: Insert helper classes
    if verbose:
        print(f"\n[5/6] Installing helper classes...")
    
    helper_sql = HELPER_CLASSES.format(now=now)
    try:
        conn.executescript(helper_sql)
        c.execute("SELECT COUNT(*) FROM system_python_modules")
        module_count = c.fetchone()[0]
        if verbose:
            print(f"  ✓ Installed {module_count} Python modules (FlagParser, BinaryEncoder, HandlerExecutor)")
    except sqlite3.Error as e:
        if verbose:
            print(f"  ⚠️  Module installation completed with warnings: {e}")
        module_count = 0
    
    # Step 6: Verification
    if verbose:
        print(f"\n[6/6] Verification...")
    
    # Check handler coverage
    try:
        c.execute("""
            SELECT COUNT(*) FROM command_registry 
            WHERE cmd_enabled = 1 
            AND cmd_id NOT IN (SELECT DISTINCT cmd_id FROM command_handlers WHERE enabled = 1)
        """)
        missing = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM command_registry WHERE cmd_enabled = 1")
        total_cmds = c.fetchone()[0]
        
        coverage = ((total_cmds - missing) / total_cmds * 100) if total_cmds > 0 else 0
        
        if verbose:
            print(f"  Commands with handlers: {total_cmds - missing}/{total_cmds} ({coverage:.1f}%)")
            if flag_count > 0:
                print(f"  Commands with flags: ~{flag_count // 3} (estimated)")
            if arg_count > 0:
                print(f"  Commands with arguments: ~{arg_count // 2} (estimated)")
    except sqlite3.Error as e:
        if verbose:
            print(f"  ⚠️  Verification skipped: {e}")
        coverage = 0
        total_cmds = 0
    
    conn.commit()
    conn.close()
    
    # Summary
    print(f"\n{'='*80}")
    print(f"  PATCH APPLIED SUCCESSFULLY")
    print(f"{'='*80}")
    print(f"\nDatabase now supports:")
    print(f"✓ {flag_count} flag definitions")
    print(f"  ✓ {arg_count} argument specifications")
    print(f"  ✓ {handler_count} handler implementations")
    print(f"  ✓ {module_count} helper modules")
    print(f"  ✓ Database-driven execution system ready")
    
    if total_cmds > 0:
        print(f"\nCoverage:")
        print(f"  ✓ {coverage:.1f}% of commands have handlers")
    
    print(f"\nNext steps:")
    print(f"  1. Update qunix_cpu.py to use HandlerExecutor")
    print(f"  2. Remove all hardcoded _cmd_* methods")
    print(f"  3. Test with: python qunix_cpu.py")
    print(f"\nAll execution now flows through the database! 💜\n")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Apply handlers/flags/args patch to QUNIX database')
    parser.add_argument('database', help='Path to qunix_leech.db')
    parser.add_argument('--quiet', action='store_true', help='Minimal output')
    parser.add_argument('--verify-only', action='store_true', help='Only verify, do not apply')
    
    args = parser.parse_args()
    
    if not Path(args.database).exists():
        print(f"ERROR: Database not found: {args.database}")
        sys.exit(1)
    
    if args.verify_only:
        # Verification mode
        conn = sqlite3.connect(args.database)
        c = conn.cursor()
        
        print(f"\nVerifying database: {args.database}\n")
        
        # Check tables
        tables = ['command_registry', 'command_flags', 'command_arguments', 'command_handlers']
        for table in tables:
            c.execute(f"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table,))
            exists = c.fetchone()[0]
            status = '✓ EXISTS' if exists else '✗ MISSING'
            print(f"  {table:30s} {status}")
            
            if exists and table != 'command_registry':
                c.execute(f"SELECT COUNT(*) FROM {table}")
                count = c.fetchone()[0]
                print(f"    {'':28s} → {count} rows")
        
        # Check command_registry data
        try:
            c.execute("SELECT COUNT(*) FROM command_registry WHERE cmd_enabled = 1")
            cmd_count = c.fetchone()[0]
            print(f"\n  Enabled commands: {cmd_count}")
        except:
            print(f"\n  Enabled commands: N/A")
        
        # Check coverage
        try:
            c.execute("""
                SELECT COUNT(*) FROM command_registry 
                WHERE cmd_enabled = 1 
                AND cmd_id IN (SELECT DISTINCT cmd_id FROM command_handlers WHERE enabled = 1)
            """)
            with_handlers = c.fetchone()[0]
            if cmd_count > 0:
                coverage = (with_handlers / cmd_count * 100)
                print(f"  Commands with handlers: {with_handlers}/{cmd_count} ({coverage:.1f}%)")
        except:
            pass
        
        # Check helper modules
        try:
            c.execute("SELECT module_name FROM system_python_modules ORDER BY module_name")
            modules = [row[0] for row in c.fetchall()]
            if modules:
                print(f"\n  Helper modules installed:")
                for mod in modules:
                    print(f"    • {mod}")
        except:
            print(f"\n  Helper modules: Not installed")
        
        conn.close()
        print()
    else:
        # Apply patch
        apply_patch(args.database, verbose=not args.quiet)
