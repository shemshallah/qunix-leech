#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                           ║
║              QUNIX COMPLETE DATABASE PATCH v1.0.0-EXECUTION-CHAIN                         ║
║                                                                                           ║
║   Pure database patch providing complete execution infrastructure for:                    ║
║     • qunix_cpu.py - Quantum CPU with Qiskit mandatory execution                         ║
║     • qunix_fs.py  - Database filesystem interface                                       ║
║                                                                                           ║
║   Execution Chain:                                                                        ║
║   ═══════════════════════════════════════════════════════════════════════════════════    ║
║   1. Terminal Input → command_registry lookup → cpu_opcodes (binary opcode)              ║
║   2. Opcode → cpu_microcode_sequences → micro_primitives                                 ║
║   3. Micro_primitives → quantum_command_circuits → QASM code                             ║
║   4. QASM → Qiskit QuantumCircuit → AerSimulator → Statevector                          ║
║   5. Statevector → q table update (logical qubit states)                                 ║
║   6. q table → measurement_results → classical output                                    ║
║                                                                                           ║
║   Binary Calculation Flow:                                                                ║
║   ═══════════════════════════════════════════════════════════════════════════════════    ║
║   • Logical qubits: Abstract computation units (q.i maps to lattice l.i)                ║
║   • Pseudo-physical qubits: Database state in q table (a,b,p = alpha,beta,phase)        ║
║   • Manifold mapping: q.l → l.i → 24D Leech coordinates (via Klein bottle)              ║
║   • Error correction: Golay [24,12,8] via LeechASIC                                      ║
║                                                                                           ║
║   This is a DATABASE PATCH ONLY - no embedded Python classes in SQL                      ║
║                                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════════════════════╝
"""

import sqlite3
import json
import time
import struct
import hashlib
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from math import pi

VERSION = "1.0.0-EXECUTION-CHAIN"

# ═══════════════════════════════════════════════════════════════════════════════════════════
# ANSI COLORS
# ═══════════════════════════════════════════════════════════════════════════════════════════

class C:
    G = '\033[92m'; R = '\033[91m'; Y = '\033[93m'; C = '\033[96m'
    M = '\033[35m'; B = '\033[94m'; W = '\033[97m'
    BOLD = '\033[1m'; DIM = '\033[2m'; GRAY = '\033[90m'
    E = '\033[0m'


# ═══════════════════════════════════════════════════════════════════════════════════════════
# PART 1: CORE SCHEMA - CPU EXECUTION INFRASTRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════════════════

SCHEMA_CPU_CORE = """
-- ═══════════════════════════════════════════════════════════════════════════
-- CPU OPCODES - Binary instruction encoding
-- ═══════════════════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS cpu_opcodes;

CREATE TABLE cpu_opcodes (
    opcode INTEGER PRIMARY KEY,
    mnemonic TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    subcategory TEXT,
    description TEXT,
    operand_count INTEGER DEFAULT 0,
    operand_types TEXT,
    operand_constraints TEXT,
    cycles_min INTEGER DEFAULT 1,
    cycles_max INTEGER DEFAULT 1,
    qasm_template TEXT,
    hardware_impl BLOB,
    composition_deps TEXT,
    flags_affected TEXT,
    complexity_class TEXT DEFAULT 'O(1)',
    is_quantum INTEGER DEFAULT 1,
    is_composite INTEGER DEFAULT 0,
    requires_ecc INTEGER DEFAULT 0,
    lattice_operation TEXT,
    created_at REAL DEFAULT (strftime('%s', 'now')),
    CHECK(opcode >= 0 AND opcode <= 0xFFFFFFFF)
);

-- ═══════════════════════════════════════════════════════════════════════════
-- MICROCODE TRANSLATION LAYER
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS cpu_microcode_sequences (
    sequence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    opcode INTEGER NOT NULL,
    sequence_order INTEGER NOT NULL,
    micro_opcode INTEGER NOT NULL,
    micro_operands TEXT,
    conditional TEXT,
    description TEXT,
    UNIQUE(opcode, sequence_order)
);

CREATE TABLE IF NOT EXISTS cpu_micro_primitives (
    primitive_id INTEGER PRIMARY KEY AUTOINCREMENT,
    primitive_name TEXT UNIQUE NOT NULL,
    operation_type TEXT NOT NULL,
    qiskit_method TEXT,
    parameters TEXT,
    cycles INTEGER DEFAULT 1,
    description TEXT
);

-- ═══════════════════════════════════════════════════════════════════════════
-- QUANTUM COMMAND CIRCUITS - QASM code storage
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS quantum_command_circuits (
    circuit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_name TEXT NOT NULL,
    circuit_name TEXT NOT NULL,
    num_qubits INTEGER NOT NULL,
    num_clbits INTEGER DEFAULT 0,
    qasm_code TEXT NOT NULL,
    gate_sequence TEXT,
    created_at REAL DEFAULT (strftime('%s', 'now')),
    UNIQUE(cmd_name, circuit_name)
);

-- ═══════════════════════════════════════════════════════════════════════════
-- COMMAND REGISTRY - Terminal command to opcode mapping
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS command_registry (
    cmd_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_name TEXT NOT NULL UNIQUE,
    cmd_opcode BLOB,
    cmd_category TEXT,
    cmd_description TEXT,
    cmd_requires_qubits INTEGER DEFAULT 0,
    cmd_enabled INTEGER DEFAULT 1,
    cmd_created_at REAL DEFAULT (strftime('%s', 'now')),
    gate_name TEXT
);

CREATE TABLE IF NOT EXISTS command_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alias_name TEXT UNIQUE NOT NULL,
    canonical_cmd_name TEXT NOT NULL
);

-- ═══════════════════════════════════════════════════════════════════════════
-- QUBIT ALLOCATOR - Track qubit usage
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS cpu_qubit_allocator (
    qubit_id INTEGER PRIMARY KEY,
    allocated INTEGER DEFAULT 0,
    allocated_to_pid INTEGER,
    allocation_time REAL,
    last_used REAL,
    last_allocated REAL,
    usage_count INTEGER DEFAULT 0,
    current_state_id INTEGER
);

-- ═══════════════════════════════════════════════════════════════════════════
-- EXECUTION LOGGING
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS command_execution_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_name TEXT NOT NULL,
    arguments TEXT,
    qubits_allocated TEXT,
    execution_time_ms REAL,
    success INTEGER DEFAULT 1,
    return_value TEXT,
    timestamp REAL DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE IF NOT EXISTS command_performance_stats (
    cmd_name TEXT PRIMARY KEY,
    execution_count INTEGER DEFAULT 0,
    total_time_ms REAL DEFAULT 0,
    last_executed REAL
);

CREATE TABLE IF NOT EXISTS cpu_measurement_results (
    measurement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    qubit_ids TEXT,
    measurement_basis TEXT DEFAULT 'Z',
    outcome_bitstring TEXT,
    outcome_counts TEXT,
    probability REAL,
    state_vector BLOB,
    timestamp REAL DEFAULT (strftime('%s', 'now'))
);

-- ═══════════════════════════════════════════════════════════════════════════
-- BUS & NIC CORE STATUS
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS bus_core (
    bus_id INTEGER PRIMARY KEY DEFAULT 1,
    active INTEGER DEFAULT 1,
    mode TEXT DEFAULT 'KLEIN_BRIDGE',
    packets_processed INTEGER DEFAULT 0,
    circuits_generated INTEGER DEFAULT 0,
    fitness_score REAL DEFAULT 0,
    last_updated REAL
);

CREATE TABLE IF NOT EXISTS bus_routing (
    route_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address TEXT,
    port INTEGER,
    endpoint_hash BLOB,
    packets_routed INTEGER DEFAULT 0,
    last_used REAL,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS bus_klein_topology (
    topology_id INTEGER PRIMARY KEY AUTOINCREMENT,
    classical_x REAL,
    classical_y REAL,
    classical_z REAL,
    lattice_point_id INTEGER,
    lattice_coords BLOB,
    twist_angle REAL,
    mobius_flip INTEGER,
    traversals INTEGER DEFAULT 0,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS nic_core (
    nic_id INTEGER PRIMARY KEY DEFAULT 1,
    running INTEGER DEFAULT 0,
    requests_processed INTEGER DEFAULT 0,
    cache_hits INTEGER DEFAULT 0,
    quantum_advantage REAL DEFAULT 1.0,
    last_updated REAL
);
"""


# ═══════════════════════════════════════════════════════════════════════════════════════════
# PART 2: FILESYSTEM SCHEMA
# ═══════════════════════════════════════════════════════════════════════════════════════════

SCHEMA_FILESYSTEM = """
-- ═══════════════════════════════════════════════════════════════════════════
-- INODE & DENTRY - Core filesystem
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS fs_inodes (
    inode_id INTEGER PRIMARY KEY AUTOINCREMENT,
    inode_type CHAR(1) NOT NULL DEFAULT 'f',
    mode INTEGER DEFAULT 420,
    uid INTEGER DEFAULT 0,
    gid INTEGER DEFAULT 0,
    size INTEGER DEFAULT 0,
    nlink INTEGER DEFAULT 1,
    atime REAL,
    mtime REAL,
    ctime REAL,
    crtime REAL,
    quantum_encoded INTEGER DEFAULT 0,
    lattice_point_id INTEGER,
    CHECK(inode_type IN ('f', 'd', 'l'))
);

CREATE TABLE IF NOT EXISTS fs_dentries (
    dentry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_inode INTEGER NOT NULL,
    child_inode INTEGER NOT NULL,
    name TEXT NOT NULL,
    file_type CHAR(1) DEFAULT 'f',
    created_at REAL,
    UNIQUE(parent_inode, name)
);

CREATE TABLE IF NOT EXISTS fs_blocks (
    block_id INTEGER PRIMARY KEY AUTOINCREMENT,
    inode_id INTEGER NOT NULL,
    block_index INTEGER NOT NULL,
    data BLOB,
    data_size INTEGER DEFAULT 0,
    compressed INTEGER DEFAULT 0,
    checksum BLOB,
    created_at REAL,
    modified_at REAL,
    UNIQUE(inode_id, block_index)
);

CREATE TABLE IF NOT EXISTS fs_cwd (
    session_id TEXT PRIMARY KEY,
    cwd_inode INTEGER DEFAULT 1,
    cwd_path TEXT DEFAULT '/',
    updated_at REAL
);

-- ═══════════════════════════════════════════════════════════════════════════
-- EXTERNAL MOUNT SYSTEM - Bridge to Linux filesystem
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS fs_external_mounts (
    mount_id INTEGER PRIMARY KEY AUTOINCREMENT,
    db_path TEXT UNIQUE NOT NULL,
    linux_path TEXT NOT NULL,
    mount_type TEXT DEFAULT 'bind',
    readonly INTEGER DEFAULT 0,
    permissions TEXT DEFAULT 'rwx',
    automount INTEGER DEFAULT 1,
    enabled INTEGER DEFAULT 1,
    priority INTEGER DEFAULT 0,
    created_at REAL DEFAULT (strftime('%s', 'now')),
    last_verified REAL,
    CHECK(db_path LIKE '/%' AND linux_path LIKE '/%')
);

CREATE TABLE IF NOT EXISTS fs_mount_state (
    mount_id INTEGER PRIMARY KEY,
    active INTEGER DEFAULT 0,
    mount_time REAL,
    access_count INTEGER DEFAULT 0,
    last_access REAL,
    error_count INTEGER DEFAULT 0,
    last_error TEXT
);

-- ═══════════════════════════════════════════════════════════════════════════
-- SPECIAL PATH HANDLERS
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS fs_special_paths (
    path TEXT PRIMARY KEY,
    handler_type TEXT NOT NULL,
    handler_function TEXT NOT NULL,
    description TEXT,
    enabled INTEGER DEFAULT 1
) WITHOUT ROWID;

-- ═══════════════════════════════════════════════════════════════════════════
-- LOCATE INDEX (for fast searching)
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS fs_locate_index (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL,
    filename TEXT NOT NULL,
    basename TEXT NOT NULL,
    extension TEXT,
    source_type TEXT NOT NULL,
    source_mount INTEGER,
    inode_id INTEGER,
    is_directory INTEGER DEFAULT 0,
    size INTEGER,
    mtime REAL,
    indexed_at REAL DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE IF NOT EXISTS fs_locate_meta (
    meta_key TEXT PRIMARY KEY,
    meta_value TEXT,
    updated_at REAL DEFAULT (strftime('%s', 'now'))
) WITHOUT ROWID;

-- ═══════════════════════════════════════════════════════════════════════════
-- PATH RESOLUTION CACHE
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS fs_path_resolver_cache (
    path TEXT PRIMARY KEY,
    resolved_type TEXT NOT NULL,
    resolved_target TEXT,
    mount_id INTEGER,
    is_directory INTEGER,
    cached_at REAL DEFAULT (strftime('%s', 'now')),
    expires_at REAL,
    hit_count INTEGER DEFAULT 0
) WITHOUT ROWID;
"""


# ═══════════════════════════════════════════════════════════════════════════════════════════
# PART 3: INDICES FOR PERFORMANCE
# ═══════════════════════════════════════════════════════════════════════════════════════════

SCHEMA_INDICES = """
-- CPU indices
CREATE INDEX IF NOT EXISTS idx_cpu_opcodes_mnemonic ON cpu_opcodes(mnemonic);
CREATE INDEX IF NOT EXISTS idx_cpu_opcodes_category ON cpu_opcodes(category);
CREATE INDEX IF NOT EXISTS idx_cmd_registry_name ON command_registry(cmd_name);
CREATE INDEX IF NOT EXISTS idx_cmd_registry_opcode ON command_registry(cmd_opcode);
CREATE INDEX IF NOT EXISTS idx_qubit_alloc_allocated ON cpu_qubit_allocator(allocated);
CREATE INDEX IF NOT EXISTS idx_microcode_opcode ON cpu_microcode_sequences(opcode);
CREATE INDEX IF NOT EXISTS idx_qcircuits_cmd ON quantum_command_circuits(cmd_name);

-- Filesystem indices
CREATE INDEX IF NOT EXISTS idx_fs_dentries_parent ON fs_dentries(parent_inode);
CREATE INDEX IF NOT EXISTS idx_fs_dentries_name ON fs_dentries(name);
CREATE INDEX IF NOT EXISTS idx_fs_blocks_inode ON fs_blocks(inode_id);
CREATE INDEX IF NOT EXISTS idx_fs_mounts_path ON fs_external_mounts(db_path);
CREATE INDEX IF NOT EXISTS idx_fs_locate_basename ON fs_locate_index(basename);
CREATE INDEX IF NOT EXISTS idx_fs_locate_path ON fs_locate_index(path);

-- Execution indices
CREATE INDEX IF NOT EXISTS idx_exec_log_cmd ON command_execution_log(cmd_name);
CREATE INDEX IF NOT EXISTS idx_exec_log_ts ON command_execution_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_measurement_ts ON cpu_measurement_results(timestamp);
"""


# ═══════════════════════════════════════════════════════════════════════════════════════════
# PART 4: VIEWS FOR CONVENIENT ACCESS
# ═══════════════════════════════════════════════════════════════════════════════════════════

SCHEMA_VIEWS = """
-- Active commands view
CREATE VIEW IF NOT EXISTS v_commands AS
SELECT 
    cr.cmd_name,
    cr.cmd_category,
    cr.cmd_description,
    cr.cmd_requires_qubits,
    COALESCE(qc.num_qubits, 0) as circuit_qubits,
    o.mnemonic as opcode_mnemonic,
    o.category as opcode_category
FROM command_registry cr
LEFT JOIN quantum_command_circuits qc ON cr.cmd_name = qc.cmd_name
LEFT JOIN cpu_opcodes o ON cr.cmd_opcode = (SELECT cmd_opcode FROM command_registry WHERE cmd_name = cr.cmd_name)
WHERE cr.cmd_enabled = 1
ORDER BY cr.cmd_category, cr.cmd_name;

-- Qubit status view
CREATE VIEW IF NOT EXISTS v_qubit_status AS
SELECT 
    (SELECT COUNT(*) FROM cpu_qubit_allocator WHERE allocated = 0) as free_qubits,
    (SELECT COUNT(*) FROM cpu_qubit_allocator WHERE allocated = 1) as allocated_qubits,
    (SELECT COUNT(*) FROM q) as total_qubits,
    (SELECT COUNT(*) FROM tri) as triangles,
    (SELECT COUNT(*) FROM e WHERE t = 'e') as epr_pairs;

-- Filesystem tree view
CREATE VIEW IF NOT EXISTS v_fs_tree AS
SELECT 
    d.parent_inode,
    d.child_inode,
    d.name,
    i.inode_type,
    i.size,
    i.mode
FROM fs_dentries d
JOIN fs_inodes i ON d.child_inode = i.inode_id
WHERE d.name NOT IN ('.', '..')
ORDER BY d.parent_inode, d.name;

-- Active mounts view
CREATE VIEW IF NOT EXISTS v_active_mounts AS
SELECT 
    em.mount_id,
    em.db_path,
    em.linux_path,
    em.mount_type,
    em.readonly,
    COALESCE(ms.active, 0) as active,
    COALESCE(ms.access_count, 0) as access_count
FROM fs_external_mounts em
LEFT JOIN fs_mount_state ms ON em.mount_id = ms.mount_id
WHERE em.enabled = 1
ORDER BY em.priority DESC;

-- Execution chain view (shows command → opcode → microcode → circuit flow)
CREATE VIEW IF NOT EXISTS v_execution_chain AS
SELECT 
    cr.cmd_name,
    o.opcode,
    o.mnemonic,
    ms.sequence_order,
    mp.primitive_name,
    mp.qiskit_method,
    qc.qasm_code
FROM command_registry cr
LEFT JOIN cpu_opcodes o ON 
    (CASE WHEN length(cr.cmd_opcode) >= 4 
     THEN (cr.cmd_opcode & 0xFF) | ((cr.cmd_opcode >> 8) & 0xFF00)
     ELSE NULL END) = o.opcode
LEFT JOIN cpu_microcode_sequences ms ON o.opcode = ms.opcode
LEFT JOIN cpu_micro_primitives mp ON ms.micro_opcode = mp.primitive_id
LEFT JOIN quantum_command_circuits qc ON cr.cmd_name = qc.cmd_name
WHERE cr.cmd_enabled = 1;
"""


# ═══════════════════════════════════════════════════════════════════════════════════════════
# PART 5: TRIGGERS FOR AUTOMATIC MAINTENANCE
# ═══════════════════════════════════════════════════════════════════════════════════════════

SCHEMA_TRIGGERS = """
-- Update execution stats on command log
CREATE TRIGGER IF NOT EXISTS tr_update_cmd_stats
AFTER INSERT ON command_execution_log
BEGIN
    INSERT INTO command_performance_stats (cmd_name, execution_count, total_time_ms, last_executed)
    VALUES (NEW.cmd_name, 1, NEW.execution_time_ms, NEW.timestamp)
    ON CONFLICT(cmd_name) DO UPDATE SET
        execution_count = execution_count + 1,
        total_time_ms = total_time_ms + NEW.execution_time_ms,
        last_executed = NEW.timestamp;
END;

-- Auto-update qubit allocation time
CREATE TRIGGER IF NOT EXISTS tr_qubit_alloc_time
AFTER UPDATE OF allocated ON cpu_qubit_allocator
WHEN NEW.allocated = 1
BEGIN
    UPDATE cpu_qubit_allocator 
    SET allocation_time = strftime('%s', 'now'),
        last_allocated = strftime('%s', 'now'),
        usage_count = usage_count + 1
    WHERE qubit_id = NEW.qubit_id;
END;

-- Update filesystem modification times
CREATE TRIGGER IF NOT EXISTS tr_fs_mtime_update
AFTER UPDATE ON fs_blocks
BEGIN
    UPDATE fs_inodes 
    SET mtime = strftime('%s', 'now')
    WHERE inode_id = NEW.inode_id;
END;

-- Update mount access stats
CREATE TRIGGER IF NOT EXISTS tr_mount_access
AFTER UPDATE OF active ON fs_mount_state
WHEN NEW.active = 1
BEGIN
    UPDATE fs_mount_state 
    SET access_count = access_count + 1,
        last_access = strftime('%s', 'now'),
        mount_time = strftime('%s', 'now')
    WHERE mount_id = NEW.mount_id;
END;

-- Expire path cache
CREATE TRIGGER IF NOT EXISTS tr_expire_path_cache
AFTER INSERT ON fs_path_resolver_cache
BEGIN
    DELETE FROM fs_path_resolver_cache
    WHERE expires_at IS NOT NULL 
    AND expires_at < strftime('%s', 'now')
    AND path != NEW.path;
END;
"""


# ═══════════════════════════════════════════════════════════════════════════════════════════
# QUANTUM GATE QASM TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════════════════

QASM_TEMPLATES = {
    'hadamard': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
h q[0];
measure q[0] -> c[0];''',
    
    'pauli_x': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
x q[0];
measure q[0] -> c[0];''',
    
    'pauli_y': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
y q[0];
measure q[0] -> c[0];''',
    
    'pauli_z': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
z q[0];
measure q[0] -> c[0];''',
    
    's_gate': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
s q[0];
measure q[0] -> c[0];''',
    
    't_gate': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
t q[0];
measure q[0] -> c[0];''',
    
    'cnot': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
cx q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];''',
    
    'cz': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
cz q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];''',
    
    'swap': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
swap q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];''',
    
    'toffoli': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
ccx q[0], q[1], q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];''',
    
    'bell_pair': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];''',
    
    'ghz_3': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0], q[1];
cx q[0], q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];''',
    
    'wstate_3': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
ry(1.2310) q[0];
cx q[0], q[1];
x q[0];
cx q[0], q[2];
x q[0];
ry(0.7854) q[1];
cx q[1], q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];''',
    
    'grover_8': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0]; h q[1]; h q[2]; h q[3]; h q[4]; h q[5]; h q[6]; h q[7];
barrier q;
h q[0]; h q[1]; h q[2]; h q[3]; h q[4]; h q[5]; h q[6]; h q[7];
x q[0]; x q[1]; x q[2]; x q[3]; x q[4]; x q[5]; x q[6]; x q[7];
h q[7];
ccx q[0], q[1], q[2];
ccx q[2], q[3], q[4];
ccx q[4], q[5], q[6];
cx q[6], q[7];
ccx q[4], q[5], q[6];
ccx q[2], q[3], q[4];
ccx q[0], q[1], q[2];
h q[7];
x q[0]; x q[1]; x q[2]; x q[3]; x q[4]; x q[5]; x q[6]; x q[7];
h q[0]; h q[1]; h q[2]; h q[3]; h q[4]; h q[5]; h q[6]; h q[7];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
measure q[3] -> c[3];
measure q[4] -> c[4];
measure q[5] -> c[5];
measure q[6] -> c[6];
measure q[7] -> c[7];''',
    
    'quantum_walk_10': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[10];
h q[0]; h q[1]; h q[2];
h q[8]; h q[9];
cx q[8], q[0];
cx q[9], q[1];
h q[3]; h q[4];
cx q[3], q[5];
cx q[4], q[6];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
measure q[3] -> c[3];
measure q[4] -> c[4];
measure q[5] -> c[5];
measure q[6] -> c[6];
measure q[7] -> c[7];
measure q[8] -> c[8];
measure q[9] -> c[9];''',
    
    'find_search_12': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[12];
creg c[12];
h q[0]; h q[1]; h q[2]; h q[3]; h q[4]; h q[5]; h q[6]; h q[7];
h q[8]; h q[9];
cz q[0], q[8];
cz q[1], q[9];
h q[0]; h q[1]; h q[2]; h q[3]; h q[4]; h q[5]; h q[6]; h q[7];
x q[0]; x q[1]; x q[2]; x q[3]; x q[4]; x q[5]; x q[6]; x q[7];
h q[7];
ccx q[0], q[1], q[10];
ccx q[10], q[2], q[11];
cx q[11], q[7];
ccx q[10], q[2], q[11];
ccx q[0], q[1], q[10];
h q[7];
x q[0]; x q[1]; x q[2]; x q[3]; x q[4]; x q[5]; x q[6]; x q[7];
h q[0]; h q[1]; h q[2]; h q[3]; h q[4]; h q[5]; h q[6]; h q[7];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
measure q[3] -> c[3];
measure q[4] -> c[4];
measure q[5] -> c[5];
measure q[6] -> c[6];
measure q[7] -> c[7];
measure q[8] -> c[8];
measure q[9] -> c[9];
measure q[10] -> c[10];
measure q[11] -> c[11];''',
    
    'locate_amplify_6': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0]; h q[1]; h q[2]; h q[3]; h q[4]; h q[5];
barrier q;
h q[0]; h q[1]; h q[2]; h q[3]; h q[4]; h q[5];
x q[0]; x q[1]; x q[2]; x q[3]; x q[4]; x q[5];
h q[5];
ccx q[0], q[1], q[3];
ccx q[3], q[2], q[4];
cx q[4], q[5];
ccx q[3], q[2], q[4];
ccx q[0], q[1], q[3];
h q[5];
x q[0]; x q[1]; x q[2]; x q[3]; x q[4]; x q[5];
h q[0]; h q[1]; h q[2]; h q[3]; h q[4]; h q[5];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
measure q[3] -> c[3];
measure q[4] -> c[4];
measure q[5] -> c[5];''',
}


# ═══════════════════════════════════════════════════════════════════════════════════════════
# OPCODE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════════════════

def get_opcodes() -> List[Tuple]:
    """Returns complete opcode definitions."""
    return [
        # Single-qubit gates (0x01 - 0x0F)
        (0x01, 'QH', 'QUANTUM', 'SINGLE', 'Hadamard gate', 1, 'qubit', 'hadamard', 1, 'O(1)', 'ROTATE'),
        (0x02, 'QX', 'QUANTUM', 'SINGLE', 'Pauli-X gate', 1, 'qubit', 'pauli_x', 1, 'O(1)', 'FLIP_X'),
        (0x03, 'QY', 'QUANTUM', 'SINGLE', 'Pauli-Y gate', 1, 'qubit', 'pauli_y', 1, 'O(1)', 'FLIP_Y'),
        (0x04, 'QZ', 'QUANTUM', 'SINGLE', 'Pauli-Z gate', 1, 'qubit', 'pauli_z', 1, 'O(1)', 'FLIP_Z'),
        (0x05, 'QS', 'QUANTUM', 'SINGLE', 'S gate', 1, 'qubit', 's_gate', 1, 'O(1)', 'PHASE_S'),
        (0x06, 'QT', 'QUANTUM', 'SINGLE', 'T gate', 1, 'qubit', 't_gate', 1, 'O(1)', 'PHASE_T'),
        # Two-qubit gates (0x10 - 0x1F)
        (0x10, 'QCNOT', 'QUANTUM', 'TWO', 'CNOT gate', 2, 'control,target', 'cnot', 1, 'O(1)', 'ENTANGLE'),
        (0x11, 'QCZ', 'QUANTUM', 'TWO', 'CZ gate', 2, 'control,target', 'cz', 1, 'O(1)', 'ENTANGLE'),
        (0x12, 'QSWAP', 'QUANTUM', 'TWO', 'Swap gate', 2, 'qubit1,qubit2', 'swap', 1, 'O(1)', 'SWAP'),
        # Three-qubit gates (0x20 - 0x2F)
        (0x20, 'QTOFF', 'QUANTUM', 'THREE', 'Toffoli gate', 3, 'c1,c2,target', 'toffoli', 1, 'O(1)', 'ENTANGLE'),
        (0x21, 'QFRED', 'QUANTUM', 'THREE', 'Fredkin gate', 3, 'control,t1,t2', 'toffoli', 1, 'O(1)', 'CSWAP'),
        # Entanglement (0x30 - 0x3F)
        (0x30, 'EPR', 'QUANTUM', 'ENTANGLE', 'Create Bell pair', 2, 'qubit1,qubit2', 'bell_pair', 1, 'O(1)', 'BELL_CREATE'),
        (0x31, 'GHZ', 'QUANTUM', 'ENTANGLE', 'Create GHZ state', 3, 'qubits', 'ghz_3', 1, 'O(n)', 'GHZ_CREATE'),
        (0x32, 'WSTATE', 'QUANTUM', 'ENTANGLE', 'Create W state', 3, 'qubits', 'wstate_3', 1, 'O(n)', 'W_CREATE'),
        # Rotation (0x40 - 0x4F)
        (0x40, 'QRX', 'QUANTUM', 'ROTATION', 'Rotate X', 2, 'qubit,angle', 'hadamard', 1, 'O(1)', 'ROTATE_X'),
        (0x41, 'QRY', 'QUANTUM', 'ROTATION', 'Rotate Y', 2, 'qubit,angle', 'hadamard', 1, 'O(1)', 'ROTATE_Y'),
        (0x42, 'QRZ', 'QUANTUM', 'ROTATION', 'Rotate Z', 2, 'qubit,angle', 'hadamard', 1, 'O(1)', 'ROTATE_Z'),
        # Measurement (0x50 - 0x5F)
        (0x50, 'QMEAS', 'QUANTUM', 'MEASURE', 'Measure qubit', 1, 'qubit', 'hadamard', 1, 'O(1)', 'MEASURE_Z'),
        (0x53, 'QRESET', 'QUANTUM', 'MEASURE', 'Reset qubit', 1, 'qubit', 'hadamard', 1, 'O(1)', 'RESET'),
        # Classical (0x80 - 0x8F)
        (0x80, 'NOP', 'CLASSICAL', 'CONTROL', 'No operation', 0, None, None, 0, 'O(1)', None),
        (0x81, 'HALT', 'CLASSICAL', 'CONTROL', 'Halt execution', 0, None, None, 0, 'O(1)', None),
        # System (0xF0 - 0xFF)
        (0xF0, 'HELP', 'SYSTEM', 'HELP', 'Display help', 0, None, None, 0, 'O(1)', None),
        (0xF1, 'STATUS', 'SYSTEM', 'INFO', 'System status', 0, None, None, 0, 'O(1)', None),
        (0xF2, 'LS', 'SYSTEM', 'FILESYSTEM', 'List directory', 1, 'path', 'grover_8', 1, 'O(sqrt(n))', 'GROVER'),
        (0xF3, 'PWD', 'SYSTEM', 'FILESYSTEM', 'Print working dir', 0, None, None, 0, 'O(1)', None),
        (0xF4, 'CD', 'SYSTEM', 'FILESYSTEM', 'Change directory', 1, 'path', None, 0, 'O(1)', None),
        (0xF5, 'CAT', 'SYSTEM', 'FILESYSTEM', 'Display file', 1, 'path', None, 0, 'O(n)', None),
        (0xF6, 'TREE', 'SYSTEM', 'FILESYSTEM', 'Directory tree', 1, 'path', 'quantum_walk_10', 1, 'O(sqrt(n))', 'QWALK'),
        (0xF7, 'FIND', 'SYSTEM', 'FILESYSTEM', 'Find files', 2, 'path,pattern', 'find_search_12', 1, 'O(sqrt(n))', 'GROVER'),
        (0xF8, 'LOCATE', 'SYSTEM', 'FILESYSTEM', 'Fast search', 1, 'pattern', 'locate_amplify_6', 1, 'O(sqrt(n))', 'AMPLIFY'),
    ]


# ═══════════════════════════════════════════════════════════════════════════════════════════
# COMMAND DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════════════════

def get_commands() -> List[Tuple]:
    """Returns command definitions."""
    return [
        # Quantum gates
        ('qh', 0x01, 'QUANTUM', 'Hadamard gate', 1, 'h'),
        ('qx', 0x02, 'QUANTUM', 'Pauli-X gate', 1, 'x'),
        ('qy', 0x03, 'QUANTUM', 'Pauli-Y gate', 1, 'y'),
        ('qz', 0x04, 'QUANTUM', 'Pauli-Z gate', 1, 'z'),
        ('qs', 0x05, 'QUANTUM', 'S gate', 1, 's'),
        ('qt', 0x06, 'QUANTUM', 'T gate', 1, 't'),
        ('qcnot', 0x10, 'QUANTUM', 'CNOT gate', 2, 'cx'),
        ('qcz', 0x11, 'QUANTUM', 'CZ gate', 2, 'cz'),
        ('qswap', 0x12, 'QUANTUM', 'Swap gate', 2, 'swap'),
        ('qtoffoli', 0x20, 'QUANTUM', 'Toffoli gate', 3, 'ccx'),
        ('epr_create', 0x30, 'QUANTUM', 'Create Bell pair', 2, 'bell'),
        ('ghz_create', 0x31, 'QUANTUM', 'Create GHZ state', 3, 'ghz'),
        ('w_create', 0x32, 'QUANTUM', 'Create W state', 3, 'wstate'),
        # System
        ('help', 0xF0, 'HELP', 'Show help', 0, None),
        ('status', 0xF1, 'SYSTEM', 'System status', 0, None),
        ('qcpu_status', 0xF1, 'QUNIX', 'CPU status', 0, None),
        ('bus_status', 0xF1, 'QUNIX', 'Bus status', 0, None),
        # Filesystem
        ('ls', 0xF2, 'FILESYSTEM', 'List directory', 0, 'grover'),
        ('dir', 0xF2, 'FILESYSTEM', 'List directory', 0, 'grover'),
        ('pwd', 0xF3, 'FILESYSTEM', 'Print working dir', 0, None),
        ('cd', 0xF4, 'FILESYSTEM', 'Change directory', 0, None),
        ('cat', 0xF5, 'FILESYSTEM', 'Display file', 0, None),
        ('tree', 0xF6, 'FILESYSTEM', 'Directory tree', 0, 'qwalk'),
        ('find', 0xF7, 'FILESYSTEM', 'Find files', 0, 'grover'),
        ('locate', 0xF8, 'FILESYSTEM', 'Fast search', 0, 'amplify'),
        ('mkdir', 0xF9, 'FILESYSTEM', 'Create directory', 0, None),
        ('rm', 0xFA, 'FILESYSTEM', 'Remove file', 0, None),
        # Monitoring
        ('ps', 0xE0, 'SYSTEM', 'Process status', 0, None),
        ('top', 0xE1, 'MONITORING', 'Resource monitor', 0, None),
        ('uname', 0xE2, 'SYSTEM', 'System info', 0, None),
        ('uptime', 0xE3, 'SYSTEM', 'Uptime', 0, None),
        ('date', 0xE4, 'SYSTEM', 'Date/time', 0, None),
        # Help
        ('man', 0xD0, 'HELP', 'Manual pages', 0, None),
        ('cmd-list', 0xD3, 'HELP', 'List commands', 0, None),
        # Leech
        ('leech_encode', 0xB0, 'QUNIX', 'Leech encode', 0, None),
        ('leech_decode', 0xB1, 'QUNIX', 'Leech decode', 0, None),
        ('hroute', 0xB3, 'QUNIX', 'Hyperbolic route', 0, None),
    ]


# ═══════════════════════════════════════════════════════════════════════════════════════════
# MICROCODE PRIMITIVES
# ═══════════════════════════════════════════════════════════════════════════════════════════

def get_micro_primitives() -> List[Tuple]:
    """Returns microcode primitive definitions."""
    return [
        ('FETCH_QUBIT', 'MEMORY', 'None', '{"qubit_id": "int"}', 1, 'Fetch qubit from q table'),
        ('STORE_QUBIT', 'MEMORY', 'None', '{"qubit_id": "int"}', 1, 'Store qubit to q table'),
        ('APPLY_H', 'GATE', 'h', '{"qubit": 0}', 1, 'Apply Hadamard'),
        ('APPLY_X', 'GATE', 'x', '{"qubit": 0}', 1, 'Apply Pauli-X'),
        ('APPLY_Y', 'GATE', 'y', '{"qubit": 0}', 1, 'Apply Pauli-Y'),
        ('APPLY_Z', 'GATE', 'z', '{"qubit": 0}', 1, 'Apply Pauli-Z'),
        ('APPLY_S', 'GATE', 's', '{"qubit": 0}', 1, 'Apply S gate'),
        ('APPLY_T', 'GATE', 't', '{"qubit": 0}', 1, 'Apply T gate'),
        ('APPLY_CX', 'GATE', 'cx', '{"control": 0, "target": 1}', 2, 'Apply CNOT'),
        ('APPLY_CZ', 'GATE', 'cz', '{"control": 0, "target": 1}', 2, 'Apply CZ'),
        ('APPLY_SWAP', 'GATE', 'swap', '{"qubit1": 0, "qubit2": 1}', 3, 'Apply SWAP'),
        ('APPLY_CCX', 'GATE', 'ccx', '{"c1": 0, "c2": 1, "target": 2}', 6, 'Apply Toffoli'),
        ('APPLY_RY', 'GATE', 'ry', '{"qubit": 0, "theta": "float"}', 1, 'Apply RY'),
        ('MEASURE_Z', 'MEASURE', 'measure', '{"qubit": 0}', 1, 'Measure in Z'),
        ('MEASURE_ALL', 'MEASURE', 'measure_all', '{}', 1, 'Measure all'),
        ('BARRIER', 'CONTROL', 'barrier', '{}', 0, 'Insert barrier'),
        ('ALLOCATE_QUBIT', 'ALLOC', 'None', '{"count": 1}', 1, 'Allocate qubit'),
        ('FREE_QUBIT', 'ALLOC', 'None', '{"qubit_id": "int"}', 1, 'Free qubit'),
        ('BUILD_CIRCUIT', 'COMPILE', 'None', '{"num_qubits": "int"}', 2, 'Create circuit'),
        ('EXECUTE_CIRCUIT', 'EXECUTE', 'None', '{"shots": 1024}', 10, 'Execute on Qiskit'),
        ('PARSE_RESULTS', 'PROCESS', 'None', '{}', 1, 'Parse counts'),
        ('UPDATE_DB', 'MEMORY', 'None', '{}', 1, 'Update database'),
    ]


# ═══════════════════════════════════════════════════════════════════════════════════════════
# MICROCODE SEQUENCES
# ═══════════════════════════════════════════════════════════════════════════════════════════

def get_microcode_sequences() -> List[Tuple]:
    """Returns microcode sequences for opcodes."""
    sequences = []
    
    # Hadamard (0x01)
    sequences.extend([
        (0x01, 0, 'ALLOCATE_QUBIT', '{"count": 1}', None, 'Allocate qubit'),
        (0x01, 1, 'FETCH_QUBIT', '{"qubit_id": "$0"}', None, 'Load state'),
        (0x01, 2, 'BUILD_CIRCUIT', '{"num_qubits": 1}', None, 'Create circuit'),
        (0x01, 3, 'APPLY_H', '{"qubit": 0}', None, 'Apply H'),
        (0x01, 4, 'MEASURE_Z', '{"qubit": 0}', None, 'Measure'),
        (0x01, 5, 'EXECUTE_CIRCUIT', '{"shots": 1024}', None, 'Run Qiskit'),
        (0x01, 6, 'PARSE_RESULTS', '{}', None, 'Parse'),
        (0x01, 7, 'STORE_QUBIT', '{"qubit_id": "$0"}', None, 'Store'),
    ])
    
    # CNOT (0x10)
    sequences.extend([
        (0x10, 0, 'ALLOCATE_QUBIT', '{"count": 2}', None, 'Allocate 2'),
        (0x10, 1, 'BUILD_CIRCUIT', '{"num_qubits": 2}', None, 'Create circuit'),
        (0x10, 2, 'APPLY_CX', '{"control": 0, "target": 1}', None, 'Apply CNOT'),
        (0x10, 3, 'MEASURE_ALL', '{}', None, 'Measure all'),
        (0x10, 4, 'EXECUTE_CIRCUIT', '{"shots": 1024}', None, 'Run Qiskit'),
        (0x10, 5, 'PARSE_RESULTS', '{}', None, 'Parse'),
    ])
    
    # Bell pair (0x30)
    sequences.extend([
        (0x30, 0, 'ALLOCATE_QUBIT', '{"count": 2}', None, 'Allocate 2'),
        (0x30, 1, 'BUILD_CIRCUIT', '{"num_qubits": 2}', None, 'Create circuit'),
        (0x30, 2, 'APPLY_H', '{"qubit": 0}', None, 'H first'),
        (0x30, 3, 'APPLY_CX', '{"control": 0, "target": 1}', None, 'CNOT entangle'),
        (0x30, 4, 'MEASURE_ALL', '{}', None, 'Measure Bell'),
        (0x30, 5, 'EXECUTE_CIRCUIT', '{"shots": 1024}', None, 'Run'),
        (0x30, 6, 'UPDATE_DB', '{"table": "e", "type": "bell"}', None, 'Record'),
    ])
    
    # GHZ (0x31)
    sequences.extend([
        (0x31, 0, 'ALLOCATE_QUBIT', '{"count": 3}', None, 'Allocate 3'),
        (0x31, 1, 'BUILD_CIRCUIT', '{"num_qubits": 3}', None, 'Create circuit'),
        (0x31, 2, 'APPLY_H', '{"qubit": 0}', None, 'H first'),
        (0x31, 3, 'APPLY_CX', '{"control": 0, "target": 1}', None, 'CNOT 0->1'),
        (0x31, 4, 'APPLY_CX', '{"control": 0, "target": 2}', None, 'CNOT 0->2'),
        (0x31, 5, 'MEASURE_ALL', '{}', None, 'Measure GHZ'),
        (0x31, 6, 'EXECUTE_CIRCUIT', '{"shots": 1024}', None, 'Run'),
    ])
    
    # ls (0xF2) - Grover search
    sequences.extend([
        (0xF2, 0, 'ALLOCATE_QUBIT', '{"count": 8}', None, 'Allocate 8 for Grover'),
        (0xF2, 1, 'BUILD_CIRCUIT', '{"num_qubits": 8}', None, 'Create 8-qubit circuit'),
        (0xF2, 2, 'APPLY_H', '{"qubit": "all"}', None, 'Superposition'),
        (0xF2, 3, 'BARRIER', '{}', None, 'Sync'),
        (0xF2, 4, 'EXECUTE_CIRCUIT', '{"shots": 1024}', None, 'Run Grover'),
        (0xF2, 5, 'PARSE_RESULTS', '{}', None, 'Parse results'),
    ])
    
    return sequences


# ═══════════════════════════════════════════════════════════════════════════════════════════
# DATABASE PATCHER CLASS
# ═══════════════════════════════════════════════════════════════════════════════════════════

class QunixDatabasePatcher:
    """Applies complete database patch for QUNIX CPU and filesystem."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.stats = {
            'tables_created': 0, 'opcodes_inserted': 0, 'commands_inserted': 0,
            'circuits_inserted': 0, 'primitives_inserted': 0, 'sequences_inserted': 0,
            'indices_created': 0, 'views_created': 0, 'triggers_created': 0,
        }
    
    def connect(self):
        print(f"{C.C}Connecting to: {self.db_path}{C.E}")
        self.conn = sqlite3.connect(str(self.db_path), timeout=60.0)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        print(f"{C.G}✓ Connected{C.E}")
    
    def apply_schema(self):
        print(f"\n{C.BOLD}{C.C}Phase 1: Applying Schema{C.E}")
        
        # Apply schemas - errors on existing tables are OK
        for schema_name, schema_sql in [
            ("CPU Core", SCHEMA_CPU_CORE),
            ("Filesystem", SCHEMA_FILESYSTEM),
            ("Indices", SCHEMA_INDICES),
            ("Views", SCHEMA_VIEWS),
            ("Triggers", SCHEMA_TRIGGERS),
        ]:
            try:
                self.conn.executescript(schema_sql)
                self.conn.commit()
                print(f"  {C.G}✓{C.E} {schema_name}")
            except sqlite3.OperationalError as e:
                if "already exists" in str(e):
                    print(f"  {C.Y}⚠{C.E} {schema_name} (tables exist, continuing)")
                else:
                    print(f"  {C.Y}⚠{C.E} {schema_name}: {e}")
        
        # Ensure all required columns exist (ALTER TABLE for missing columns)
        self._ensure_columns()
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        self.stats['tables_created'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'")
        self.stats['indices_created'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='view'")
        self.stats['views_created'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger'")
        self.stats['triggers_created'] = cursor.fetchone()[0]
        
        print(f"{C.G}✓ Schema: {self.stats['tables_created']} tables, "
              f"{self.stats['indices_created']} indices{C.E}")
    
    def _ensure_columns(self):
        """Ensure all required columns exist in tables (handles schema migrations)"""
        cursor = self.conn.cursor()
        
        # Define required columns for each table
        required_columns = {
            'cpu_microcode_sequences': [
                ('description', 'TEXT'),
                ('conditional', 'TEXT'),
                ('micro_operands', 'TEXT'),
            ],
            'cpu_micro_primitives': [
                ('description', 'TEXT'),
                ('parameters', 'TEXT'),
                ('cycles', 'INTEGER DEFAULT 1'),
            ],
            'cpu_opcodes': [
                ('lattice_operation', 'TEXT'),
                ('complexity_class', 'TEXT DEFAULT "O(1)"'),
            ],
            'command_registry': [
                ('gate_name', 'TEXT'),
            ],
            'quantum_command_circuits': [
                ('gate_sequence', 'TEXT'),
            ],
        }
        
        for table, columns in required_columns.items():
            # Check if table exists
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not cursor.fetchone():
                continue
            
            # Get existing columns
            cursor.execute(f"PRAGMA table_info({table})")
            existing = {row[1] for row in cursor.fetchall()}
            
            # Add missing columns
            for col_name, col_type in columns:
                if col_name not in existing:
                    try:
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                        print(f"  {C.C}+{C.E} Added {table}.{col_name}")
                    except sqlite3.OperationalError:
                        pass  # Column might already exist
        
        self.conn.commit()
    
    def insert_opcodes(self):
        print(f"\n{C.BOLD}{C.C}Phase 2: Inserting Opcodes{C.E}")
        opcodes = get_opcodes()
        cursor = self.conn.cursor()
        for op in opcodes:
            cursor.execute("""
                INSERT OR REPLACE INTO cpu_opcodes 
                (opcode, mnemonic, category, subcategory, description, operand_count,
                 operand_types, qasm_template, is_quantum, complexity_class, lattice_operation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, op)
        self.conn.commit()
        self.stats['opcodes_inserted'] = len(opcodes)
        print(f"{C.G}✓ Inserted {len(opcodes)} opcodes{C.E}")
    
    def insert_commands(self):
        print(f"\n{C.BOLD}{C.C}Phase 3: Inserting Commands{C.E}")
        commands = get_commands()
        cursor = self.conn.cursor()
        now = time.time()
        for cmd_name, opcode, category, description, requires_qubits, gate_name in commands:
            opcode_bytes = struct.pack('<I', opcode)
            cursor.execute("""
                INSERT OR REPLACE INTO command_registry 
                (cmd_name, cmd_opcode, cmd_category, cmd_description, 
                 cmd_requires_qubits, cmd_enabled, cmd_created_at, gate_name)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """, (cmd_name, opcode_bytes, category, description, requires_qubits, now, gate_name))
        self.conn.commit()
        self.stats['commands_inserted'] = len(commands)
        print(f"{C.G}✓ Inserted {len(commands)} commands{C.E}")
    
    def insert_circuits(self):
        print(f"\n{C.BOLD}{C.C}Phase 4: Inserting Circuits{C.E}")
        cursor = self.conn.cursor()
        now = time.time()
        mappings = [
            ('qh', 'hadamard_gate', 1, 1, 'hadamard', 'H,MEASURE'),
            ('qx', 'pauli_x_gate', 1, 1, 'pauli_x', 'X,MEASURE'),
            ('qcnot', 'cnot_gate', 2, 2, 'cnot', 'CX,MEASURE'),
            ('qtoffoli', 'toffoli_gate', 3, 3, 'toffoli', 'CCX,MEASURE'),
            ('epr_create', 'bell_pair', 2, 2, 'bell_pair', 'H,CX,MEASURE'),
            ('ghz_create', 'ghz_state', 3, 3, 'ghz_3', 'H,CX,CX,MEASURE'),
            ('w_create', 'w_state', 3, 3, 'wstate_3', 'RY,CX,X,CX,X,RY,CX,MEASURE'),
            ('ls', 'grover_search', 8, 8, 'grover_8', 'H8,GROVER,MEASURE'),
            ('tree', 'quantum_walk', 10, 10, 'quantum_walk_10', 'H,CX,MEASURE'),
            ('find', 'manifold_search', 12, 12, 'find_search_12', 'H,CZ,GROVER,MEASURE'),
            ('locate', 'amplitude_amp', 6, 6, 'locate_amplify_6', 'H6,GROVER,MEASURE'),
        ]
        for cmd, cname, nq, nc, template, seq in mappings:
            qasm = QASM_TEMPLATES.get(template, QASM_TEMPLATES['hadamard'])
            cursor.execute("""
                INSERT OR REPLACE INTO quantum_command_circuits 
                (cmd_name, circuit_name, num_qubits, num_clbits, qasm_code, gate_sequence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (cmd, cname, nq, nc, qasm, seq, now))
        self.conn.commit()
        self.stats['circuits_inserted'] = len(mappings)
        print(f"{C.G}✓ Inserted {len(mappings)} circuits{C.E}")
    
    def insert_primitives(self):
        print(f"\n{C.BOLD}{C.C}Phase 5: Inserting Primitives{C.E}")
        primitives = get_micro_primitives()
        cursor = self.conn.cursor()
        for p in primitives:
            cursor.execute("""
                INSERT OR REPLACE INTO cpu_micro_primitives 
                (primitive_name, operation_type, qiskit_method, parameters, cycles, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, p)
        self.conn.commit()
        self.stats['primitives_inserted'] = len(primitives)
        print(f"{C.G}✓ Inserted {len(primitives)} primitives{C.E}")
    
    def insert_microcode_sequences(self):
        print(f"\n{C.BOLD}{C.C}Phase 6: Inserting Microcode Sequences{C.E}")
        sequences = get_microcode_sequences()
        cursor = self.conn.cursor()
        
        # Check if description column exists, add if missing
        cursor.execute("PRAGMA table_info(cpu_microcode_sequences)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'description' not in columns:
            print(f"  {C.Y}Adding missing 'description' column...{C.E}")
            cursor.execute("ALTER TABLE cpu_microcode_sequences ADD COLUMN description TEXT")
            self.conn.commit()
        
        cursor.execute("SELECT primitive_name, primitive_id FROM cpu_micro_primitives")
        pmap = {n: p for n, p in cursor.fetchall()}
        for opcode, seq_order, prim_name, operands, conditional, description in sequences:
            prim_id = pmap.get(prim_name, 0)
            cursor.execute("""
                INSERT OR REPLACE INTO cpu_microcode_sequences 
                (opcode, sequence_order, micro_opcode, micro_operands, conditional, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (opcode, seq_order, prim_id, operands, conditional, description))
        self.conn.commit()
        self.stats['sequences_inserted'] = len(sequences)
        print(f"{C.G}✓ Inserted {len(sequences)} sequences{C.E}")
    
    def init_qubit_allocator(self):
        print(f"\n{C.BOLD}{C.C}Phase 7: Initializing Qubit Allocator{C.E}")
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='q'")
        if not cursor.fetchone():
            print(f"{C.Y}⚠ q table not found - creating minimal allocator{C.E}")
            for i in range(1000):
                cursor.execute("INSERT OR IGNORE INTO cpu_qubit_allocator (qubit_id, allocated) VALUES (?, 0)", (i,))
        else:
            cursor.execute("INSERT OR IGNORE INTO cpu_qubit_allocator (qubit_id, allocated) SELECT i, 0 FROM q")
        self.conn.commit()
        cursor.execute("SELECT COUNT(*) FROM cpu_qubit_allocator")
        count = cursor.fetchone()[0]
        print(f"{C.G}✓ Initialized {count:,} qubits{C.E}")
    
    def init_filesystem(self):
        print(f"\n{C.BOLD}{C.C}Phase 8: Initializing Filesystem{C.E}")
        cursor = self.conn.cursor()
        now = time.time()
        
        # Root inode
        cursor.execute("""
            INSERT OR IGNORE INTO fs_inodes 
            (inode_id, inode_type, mode, nlink, atime, mtime, ctime, crtime)
            VALUES (1, 'd', 493, 2, ?, ?, ?, ?)
        """, (now, now, now, now))
        
        # Standard dirs
        for i, name in enumerate(['home', 'quantum', 'sys', 'proc', 'dev', 'tmp', 'var', 'etc', 'bin'], start=2):
            cursor.execute("""
                INSERT OR IGNORE INTO fs_inodes 
                (inode_id, inode_type, mode, nlink, atime, mtime, ctime, crtime)
                VALUES (?, 'd', 493, 2, ?, ?, ?, ?)
            """, (i, now, now, now, now))
            cursor.execute("""
                INSERT OR IGNORE INTO fs_dentries (parent_inode, child_inode, name, file_type, created_at)
                VALUES (1, ?, ?, 'd', ?)
            """, (i, name, now))
        
        # Mounts
        cursor.execute("""
            INSERT OR IGNORE INTO fs_external_mounts (db_path, linux_path, mount_type, priority, enabled)
            VALUES ('/home', '/home/Shemshallah/mysite', 'bind', 100, 1)
        """)
        cursor.execute("""
            INSERT OR IGNORE INTO fs_external_mounts (db_path, linux_path, mount_type, priority, enabled)
            VALUES ('/data', '/home/Shemshallah', 'bind', 90, 1)
        """)
        cursor.execute("INSERT OR IGNORE INTO fs_mount_state (mount_id, active) SELECT mount_id, 0 FROM fs_external_mounts")
        
        # Special paths
        for path, htype, hfunc, desc in [
            ('/db', 'db_introspect', 'handle_db_introspect', 'Database introspection'),
            ('/quantum', 'quantum_state', 'handle_quantum_state', 'Quantum state viewer'),
            ('/sys', 'system_info', 'handle_system_info', 'System info'),
        ]:
            cursor.execute("INSERT OR IGNORE INTO fs_special_paths VALUES (?, ?, ?, ?, 1)", (path, htype, hfunc, desc))
        
        # Locate meta
        for k, v in [('last_full_index', '0'), ('index_version', '1.0'), ('total_entries', '0'), ('index_status', 'empty')]:
            cursor.execute("INSERT OR IGNORE INTO fs_locate_meta (meta_key, meta_value) VALUES (?, ?)", (k, v))
        
        # Bus/NIC core
        cursor.execute("INSERT OR IGNORE INTO bus_core (bus_id, active, mode, last_updated) VALUES (1, 1, 'KLEIN_BRIDGE', ?)", (now,))
        cursor.execute("INSERT OR IGNORE INTO nic_core (nic_id, running, last_updated) VALUES (1, 0, ?)", (now,))
        
        self.conn.commit()
        cursor.execute("SELECT COUNT(*) FROM fs_inodes")
        inodes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM fs_external_mounts")
        mounts = cursor.fetchone()[0]
        print(f"{C.G}✓ Filesystem: {inodes} inodes, {mounts} mounts{C.E}")
    
    def verify_patch(self) -> bool:
        print(f"\n{C.BOLD}{C.C}Phase 9: Verification{C.E}")
        cursor = self.conn.cursor()
        checks = [
            ("cpu_opcodes", "Opcodes"), ("command_registry", "Commands"),
            ("quantum_command_circuits", "Circuits"), ("cpu_micro_primitives", "Primitives"),
            ("cpu_microcode_sequences", "Sequences"), ("cpu_qubit_allocator", "Qubits"),
            ("fs_inodes", "Inodes"), ("fs_external_mounts", "Mounts"),
        ]
        all_ok = True
        for table, name in checks:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            status = f"{C.G}✓{C.E}" if count > 0 else f"{C.R}✗{C.E}"
            print(f"  {status} {name:<20} {count:>10,} rows")
            if count == 0:
                all_ok = False
        return all_ok
    
    def print_summary(self):
        print(f"\n{C.BOLD}{'═'*70}{C.E}")
        print(f"{C.BOLD}{C.G}QUNIX DATABASE PATCH COMPLETE{C.E}")
        print(f"{C.BOLD}{'═'*70}{C.E}\n")
        print(f"{C.C}Statistics:{C.E}")
        for k, v in self.stats.items():
            print(f"  {k.replace('_', ' ').title():<25} {C.G}{v}{C.E}")
        db_size_mb = self.db_path.stat().st_size / (1024*1024)
        print(f"\n{C.C}Database size: {db_size_mb:.1f} MB{C.E}")
        print(f"\n{C.BOLD}{C.G}✓ Execution chain complete!{C.E}")
        print(f"\n{C.C}Flow: Terminal → command_registry → cpu_opcodes → microcode → QASM → Qiskit → q table{C.E}")
        print(f"\n{C.C}Next: python qunix_cpu.py --db {self.db_path}{C.E}\n")
    
    def close(self):
        if self.conn:
            self.conn.commit()
            self.conn.close()


# ═══════════════════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description='QUNIX Complete Database Patch')
    parser.add_argument('db', type=str, help='Path to QUNIX database')
    parser.add_argument('--verify-only', action='store_true', help='Only verify')
    args = parser.parse_args()
    
    db_path = Path(args.db).expanduser()
    if not db_path.exists():
        print(f"\n{C.R}✗ Database not found: {db_path}{C.E}")
        print(f"{C.C}Build with: python qunix_leech_builder.py --output {db_path}{C.E}\n")
        return 1
    
    print(f"\n{C.BOLD}{C.M}╔══════════════════════════════════════════════════════════════╗{C.E}")
    print(f"{C.BOLD}{C.M}║  QUNIX DATABASE PATCH v{VERSION}       ║{C.E}")
    print(f"{C.BOLD}{C.M}╚══════════════════════════════════════════════════════════════╝{C.E}")
    
    patcher = QunixDatabasePatcher(db_path)
    
    try:
        patcher.connect()
        if args.verify_only:
            patcher.verify_patch()
            return 0
        
        start = time.time()
        patcher.apply_schema()
        patcher.insert_opcodes()
        patcher.insert_commands()
        patcher.insert_circuits()
        patcher.insert_primitives()
        patcher.insert_microcode_sequences()
        patcher.init_qubit_allocator()
        patcher.init_filesystem()
        
        if patcher.verify_patch():
            print(f"\n{C.G}✓ Patch completed in {time.time()-start:.1f}s{C.E}")
            patcher.print_summary()
            return 0
        else:
            print(f"\n{C.Y}⚠ Some components missing{C.E}\n")
            return 1
    except Exception as e:
        print(f"\n{C.R}✗ Patch failed: {e}{C.E}\n")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        patcher.close()


if __name__ == '__main__':
    sys.exit(main())
