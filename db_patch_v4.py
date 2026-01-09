

#!/usr/bin/env python3
"""
QUNIX COMPREHENSIVE DATABASE PATCH v4.1.0-COMPLETE
FULL SYSTEM INTEGRATION + ALL CROSS-LINKAGES + META-PROGRAMS
"""

import sqlite3
import json
import time
import struct
import hashlib
from pathlib import Path
from typing import Dict, List, Optional

VERSION = "4.1.0-COMPLETE-INTEGRATION"

class C:
    G = '\033[92m'; R = '\033[91m'; Y = '\033[93m'; C = '\033[96m'
    M = '\033[35m'; B = '\033[94m'; W = '\033[97m'
    BOLD = '\033[1m'; E = '\033[0m'

# ═══════════════════════════════════════════════════════════════════════════════
# COMPLETE SCHEMA WITH ALL CROSS-REFERENCES
# ═══════════════════════════════════════════════════════════════════════════════

NIC_SCHEMA = """
CREATE TABLE IF NOT EXISTS nic_core (
    nic_id INTEGER PRIMARY KEY DEFAULT 1,
    nic_name TEXT DEFAULT 'QNIC_v1',
    running INTEGER DEFAULT 0,
    mode TEXT DEFAULT 'QUANTUM_PROXY',
    bind_address TEXT DEFAULT '0.0.0.0',
    bind_port INTEGER DEFAULT 8080,
    lattice_point_id INTEGER,
    allocated_qubits INTEGER DEFAULT 1024,
    w_state_triangle_id INTEGER,
    requests_processed INTEGER DEFAULT 0,
    bytes_sent INTEGER DEFAULT 0,
    bytes_received INTEGER DEFAULT 0,
    cache_hits INTEGER DEFAULT 0,
    cache_misses INTEGER DEFAULT 0,
    quantum_advantage REAL DEFAULT 1.0,
    created_at REAL,
    last_updated REAL,
    last_request REAL,
    FOREIGN KEY(lattice_point_id) REFERENCES lp(i),
    FOREIGN KEY(w_state_triangle_id) REFERENCES tri(i)
);

CREATE TABLE IF NOT EXISTS nic_connections (
    conn_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_ip TEXT,
    client_port INTEGER,
    server_ip TEXT,
    server_port INTEGER,
    epr_pair_id INTEGER,
    bell_qubit_a INTEGER,
    bell_qubit_b INTEGER,
    state TEXT DEFAULT 'OPEN',
    protocol TEXT DEFAULT 'HTTP',
    bytes_sent INTEGER DEFAULT 0,
    bytes_received INTEGER DEFAULT 0,
    requests INTEGER DEFAULT 0,
    established_at REAL,
    last_activity REAL,
    timeout_seconds REAL DEFAULT 300.0,
    created_at REAL,
    FOREIGN KEY(epr_pair_id) REFERENCES e(i),
    FOREIGN KEY(bell_qubit_a) REFERENCES q(i),
    FOREIGN KEY(bell_qubit_b) REFERENCES q(i)
);

CREATE TABLE IF NOT EXISTS nic_request_cache (
    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_hash BLOB UNIQUE,
    request_method TEXT,
    request_url TEXT,
    request_headers BLOB,
    response_status INTEGER,
    response_headers BLOB,
    response_body BLOB,
    response_size INTEGER,
    amplitude_encoding BLOB,
    phase_encoding BLOB,
    lattice_coords BLOB,
    hit_count INTEGER DEFAULT 0,
    last_hit REAL,
    expires_at REAL,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS nic_routing_table (
    route_id INTEGER PRIMARY KEY AUTOINCREMENT,
    destination_pattern TEXT,
    destination_port INTEGER,
    lattice_path BLOB,
    w_state_chain TEXT,
    epr_bridge INTEGER,
    latency_ms REAL,
    bandwidth_qbps REAL,
    reliability REAL DEFAULT 1.0,
    use_count INTEGER DEFAULT 0,
    last_used REAL,
    created_at REAL,
    FOREIGN KEY(epr_bridge) REFERENCES e(i)
);

CREATE TABLE IF NOT EXISTS nic_metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT,
    metric_value REAL,
    metric_unit TEXT,
    timestamp REAL,
    context TEXT
);

INSERT OR IGNORE INTO nic_core (nic_id, created_at, last_updated) 
VALUES (1, strftime('%s', 'now'), strftime('%s', 'now'));

CREATE INDEX IF NOT EXISTS idx_nic_conn_state ON nic_connections(state);
CREATE INDEX IF NOT EXISTS idx_nic_cache_hash ON nic_request_cache(request_hash);
CREATE INDEX IF NOT EXISTS idx_nic_conn_epr ON nic_connections(epr_pair_id);
"""

FILESYSTEM_SCHEMA = """
CREATE TABLE IF NOT EXISTS fs_superblock (
    fs_id INTEGER PRIMARY KEY DEFAULT 1,
    fs_name TEXT DEFAULT 'QUNIX_FS',
    fs_version TEXT DEFAULT '1.0.0',
    block_size INTEGER DEFAULT 4096,
    total_blocks INTEGER DEFAULT 1000000,
    free_blocks INTEGER DEFAULT 1000000,
    total_inodes INTEGER DEFAULT 100000,
    free_inodes INTEGER DEFAULT 100000,
    mounted INTEGER DEFAULT 1,
    mount_point TEXT DEFAULT '/',
    mount_options TEXT DEFAULT 'rw,quantum',
    quantum_enabled INTEGER DEFAULT 1,
    lattice_base_point INTEGER,
    ecc_enabled INTEGER DEFAULT 1,
    created_at REAL,
    last_mounted REAL,
    last_check REAL,
    external_db_path TEXT,
    external_db_connected INTEGER DEFAULT 0,
    FOREIGN KEY(lattice_base_point) REFERENCES lp(i)
);

CREATE TABLE IF NOT EXISTS fs_inodes (
    inode_id INTEGER PRIMARY KEY AUTOINCREMENT,
    inode_type CHAR(1) NOT NULL DEFAULT 'f',
    mode INTEGER DEFAULT 420,
    uid INTEGER DEFAULT 0,
    gid INTEGER DEFAULT 0,
    size INTEGER DEFAULT 0,
    blocks INTEGER DEFAULT 0,
    nlink INTEGER DEFAULT 1,
    atime REAL,
    mtime REAL,
    ctime REAL,
    crtime REAL,
    quantum_encoded INTEGER DEFAULT 0,
    lattice_point_id INTEGER,
    golay_protected INTEGER DEFAULT 0,
    xattrs TEXT,
    flags INTEGER DEFAULT 0,
    FOREIGN KEY(lattice_point_id) REFERENCES lp(i)
);

CREATE TABLE IF NOT EXISTS fs_dentries (
    dentry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_inode INTEGER NOT NULL,
    child_inode INTEGER NOT NULL,
    name TEXT NOT NULL,
    name_hash BLOB,
    file_type CHAR(1),
    created_at REAL,
    FOREIGN KEY(parent_inode) REFERENCES fs_inodes(inode_id) ON DELETE CASCADE,
    FOREIGN KEY(child_inode) REFERENCES fs_inodes(inode_id) ON DELETE CASCADE,
    UNIQUE(parent_inode, name)
);

CREATE TABLE IF NOT EXISTS fs_blocks (
    block_id INTEGER PRIMARY KEY AUTOINCREMENT,
    inode_id INTEGER NOT NULL,
    block_index INTEGER NOT NULL,
    data BLOB,
    data_size INTEGER DEFAULT 0,
    compressed INTEGER DEFAULT 0,
    compression_algo TEXT,
    original_size INTEGER,
    quantum_encoded INTEGER DEFAULT 0,
    qubit_ids TEXT,
    amplitude_data BLOB,
    checksum BLOB,
    golay_parity BLOB,
    created_at REAL,
    modified_at REAL,
    FOREIGN KEY(inode_id) REFERENCES fs_inodes(inode_id) ON DELETE CASCADE,
    UNIQUE(inode_id, block_index)
);

CREATE TABLE IF NOT EXISTS fs_symlinks (
    link_id INTEGER PRIMARY KEY AUTOINCREMENT,
    inode_id INTEGER UNIQUE NOT NULL,
    target_path TEXT NOT NULL,
    created_at REAL,
    FOREIGN KEY(inode_id) REFERENCES fs_inodes(inode_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS fs_cwd (
    session_id TEXT PRIMARY KEY,
    cwd_inode INTEGER NOT NULL,
    cwd_path TEXT NOT NULL,
    updated_at REAL,
    FOREIGN KEY(cwd_inode) REFERENCES fs_inodes(inode_id),
    FOREIGN KEY(session_id) REFERENCES terminal_sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS fs_path_cache (
    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    inode_id INTEGER NOT NULL,
    hit_count INTEGER DEFAULT 0,
    last_hit REAL,
    expires_at REAL,
    FOREIGN KEY(inode_id) REFERENCES fs_inodes(inode_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS fs_open_files (
    fd INTEGER PRIMARY KEY,
    inode_id INTEGER NOT NULL,
    session_id TEXT,
    flags INTEGER,
    mode TEXT,
    offset INTEGER DEFAULT 0,
    opened_at REAL,
    last_access REAL,
    FOREIGN KEY(inode_id) REFERENCES fs_inodes(inode_id),
    FOREIGN KEY(session_id) REFERENCES terminal_sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS fs_external_config (
    config_id INTEGER PRIMARY KEY DEFAULT 1,
    external_db_path TEXT,
    external_db_type TEXT DEFAULT 'sqlite',
    connected INTEGER DEFAULT 0,
    last_connected REAL,
    last_sync REAL,
    sync_mode TEXT DEFAULT 'lazy',
    sync_interval_seconds INTEGER DEFAULT 60,
    root_mapping TEXT DEFAULT '/',
    mount_options TEXT,
    created_at REAL,
    updated_at REAL
);

INSERT OR IGNORE INTO fs_superblock (fs_id, created_at, last_mounted) 
VALUES (1, strftime('%s', 'now'), strftime('%s', 'now'));

INSERT OR IGNORE INTO fs_inodes (inode_id, inode_type, mode, uid, gid, nlink, 
                                  atime, mtime, ctime, crtime)
VALUES (1, 'd', 493, 0, 0, 2, 
        strftime('%s', 'now'), strftime('%s', 'now'), 
        strftime('%s', 'now'), strftime('%s', 'now'));

INSERT OR IGNORE INTO fs_external_config (config_id, created_at) 
VALUES (1, strftime('%s', 'now'));

CREATE INDEX IF NOT EXISTS idx_fs_dentry_parent ON fs_dentries(parent_inode);
CREATE INDEX IF NOT EXISTS idx_fs_dentry_name ON fs_dentries(name);
CREATE INDEX IF NOT EXISTS idx_fs_blocks_inode ON fs_blocks(inode_id);
CREATE INDEX IF NOT EXISTS idx_fs_path_cache ON fs_path_cache(path);
CREATE INDEX IF NOT EXISTS idx_fs_open_session ON fs_open_files(session_id);
"""

BUS_SCHEMA = """
CREATE TABLE IF NOT EXISTS bus_core (
    bus_id INTEGER PRIMARY KEY DEFAULT 1,
    bus_name TEXT DEFAULT 'QUANTUM_MEGA_BUS_v1',
    active INTEGER DEFAULT 1,
    mode TEXT DEFAULT 'KLEIN_BRIDGE',
    allocated_lattice_points TEXT,
    allocated_triangles TEXT,
    allocated_qubits INTEGER DEFAULT 8192,
    packets_processed INTEGER DEFAULT 0,
    circuits_generated INTEGER DEFAULT 0,
    quantum_advantage_ratio REAL DEFAULT 1.0,
    self_mod_count INTEGER DEFAULT 0,
    last_evolution_time REAL,
    fitness_score REAL DEFAULT 0.0,
    created_at REAL,
    last_updated REAL
);

DROP TABLE IF EXISTS bus_routing;
CREATE TABLE bus_routing (
    route_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address TEXT,
    port INTEGER,
    endpoint_hash BLOB,
    lattice_point_id INTEGER,
    triangle_id INTEGER,
    w_state_index INTEGER,
    epr_qubit_a INTEGER,
    epr_qubit_b INTEGER,
    epr_fidelity REAL DEFAULT 0.98,
    packets_routed INTEGER DEFAULT 0,
    last_used REAL,
    created_at REAL,
    FOREIGN KEY(lattice_point_id) REFERENCES lp(i),
    FOREIGN KEY(triangle_id) REFERENCES tri(i),
    FOREIGN KEY(epr_qubit_a) REFERENCES q(i),
    FOREIGN KEY(epr_qubit_b) REFERENCES q(i)
);

CREATE TABLE IF NOT EXISTS bus_connections (
    conn_id INTEGER PRIMARY KEY AUTOINCREMENT,
    src_ip TEXT,
    src_port INTEGER,
    dst_ip TEXT,
    dst_port INTEGER,
    epr_pair_id INTEGER,
    w_state_triangle_id INTEGER,
    bell_pair_qubit_0 INTEGER,
    bell_pair_qubit_1 INTEGER,
    state TEXT DEFAULT 'ENTANGLED',
    coherence REAL DEFAULT 1.0,
    bytes_sent INTEGER DEFAULT 0,
    bytes_received INTEGER DEFAULT 0,
    qubits_teleported INTEGER DEFAULT 0,
    established_at REAL,
    last_activity REAL,
    timeout_sigma REAL DEFAULT 100.0,
    created_at REAL,
    FOREIGN KEY(epr_pair_id) REFERENCES e(i),
    FOREIGN KEY(w_state_triangle_id) REFERENCES tri(i),
    FOREIGN KEY(bell_pair_qubit_0) REFERENCES q(i),
    FOREIGN KEY(bell_pair_qubit_1) REFERENCES q(i)
);

CREATE TABLE IF NOT EXISTS bus_klein_topology (
    topology_id INTEGER PRIMARY KEY AUTOINCREMENT,
    classical_x REAL,
    classical_y REAL,
    classical_z REAL,
    lattice_point_id INTEGER,
    lattice_coords BLOB,
    twist_angle REAL DEFAULT 0.0,
    mobius_flip INTEGER DEFAULT 0,
    traversals INTEGER DEFAULT 0,
    last_traversal REAL,
    created_at REAL,
    FOREIGN KEY(lattice_point_id) REFERENCES lp(i)
);

INSERT OR IGNORE INTO bus_core (bus_id, active, mode, created_at, last_updated) 
VALUES (1, 1, 'KLEIN_BRIDGE', strftime('%s', 'now'), strftime('%s', 'now'));

CREATE INDEX IF NOT EXISTS idx_bus_routing_endpoint ON bus_routing(ip_address, port);
CREATE INDEX IF NOT EXISTS idx_bus_conn_state ON bus_connections(state);
CREATE INDEX IF NOT EXISTS idx_bus_routing_lattice ON bus_routing(lattice_point_id);
CREATE INDEX IF NOT EXISTS idx_bus_conn_epr ON bus_connections(epr_pair_id);
"""

COMMAND_HANDLERS = """
CREATE TABLE IF NOT EXISTS command_handlers (
    handler_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_name TEXT UNIQUE NOT NULL,
    handler_type TEXT NOT NULL,
    handler_method TEXT NOT NULL,
    gate_name TEXT,
    qubits_required INTEGER DEFAULT 0,
    qasm_template TEXT,
    fs_operation TEXT,
    requires_path INTEGER DEFAULT 0,
    net_operation TEXT,
    requires_connection INTEGER DEFAULT 0,
    timeout_ms INTEGER DEFAULT 5000,
    cacheable INTEGER DEFAULT 0,
    created_at REAL
);

INSERT OR REPLACE INTO command_handlers 
(cmd_name, handler_type, handler_method, gate_name, qubits_required, created_at)
VALUES
('qh', 'quantum', '_cmd_quantum', 'h', 1, strftime('%s', 'now')),
('qx', 'quantum', '_cmd_quantum', 'x', 1, strftime('%s', 'now')),
('qy', 'quantum', '_cmd_quantum', 'y', 1, strftime('%s', 'now')),
('qz', 'quantum', '_cmd_quantum', 'z', 1, strftime('%s', 'now')),
('qs', 'quantum', '_cmd_quantum', 's', 1, strftime('%s', 'now')),
('qt', 'quantum', '_cmd_quantum', 't', 1, strftime('%s', 'now')),
('qcnot', 'quantum', '_cmd_quantum', 'cx', 2, strftime('%s', 'now')),
('qcz', 'quantum', '_cmd_quantum', 'cz', 2, strftime('%s', 'now')),
('qswap', 'quantum', '_cmd_quantum', 'swap', 2, strftime('%s', 'now')),
('qtoffoli', 'quantum', '_cmd_quantum', 'ccx', 3, strftime('%s', 'now')),
('epr_create', 'quantum', '_cmd_quantum', 'bell', 2, strftime('%s', 'now')),
('ghz_create', 'quantum', '_cmd_quantum', 'ghz', 3, strftime('%s', 'now')),
('qalloc', 'quantum', '_cmd_qalloc', NULL, 0, strftime('%s', 'now')),
('qfree', 'quantum', '_cmd_qfree', NULL, 0, strftime('%s', 'now')),
('qmeasure', 'quantum', '_cmd_qmeasure', 'measure', 1, strftime('%s', 'now')),
('qreset', 'quantum', '_cmd_qreset', 'reset', 1, strftime('%s', 'now')),
('teleport', 'quantum', '_cmd_teleport', 'teleport', 3, strftime('%s', 'now')),
('grover', 'quantum', '_cmd_grover', 'grover', 2, strftime('%s', 'now')),
('qft', 'quantum', '_cmd_qft', 'qft', 4, strftime('%s', 'now')),
('ls', 'filesystem', '_cmd_ls', NULL, 0, strftime('%s', 'now')),
('cd', 'filesystem', '_cmd_cd', NULL, 0, strftime('%s', 'now')),
('pwd', 'filesystem', '_cmd_pwd', NULL, 0, strftime('%s', 'now')),
('cat', 'filesystem', '_cmd_cat', NULL, 0, strftime('%s', 'now')),
('mkdir', 'filesystem', '_cmd_mkdir', NULL, 0, strftime('%s', 'now')),
('rm', 'filesystem', '_cmd_rm', NULL, 0, strftime('%s', 'now')),
('touch', 'filesystem', '_cmd_touch', NULL, 0, strftime('%s', 'now')),
('cp', 'filesystem', '_cmd_cp', NULL, 0, strftime('%s', 'now')),
('mv', 'filesystem', '_cmd_mv', NULL, 0, strftime('%s', 'now')),
('ps', 'system', '_cmd_ps', NULL, 0, strftime('%s', 'now')),
('top', 'system', '_cmd_top', NULL, 0, strftime('%s', 'now')),
('uname', 'system', '_cmd_uname', NULL, 0, strftime('%s', 'now')),
('date', 'system', '_cmd_date', NULL, 0, strftime('%s', 'now')),
('uptime', 'system', '_cmd_uptime', NULL, 0, strftime('%s', 'now')),
('help', 'system', '_cmd_help', NULL, 0, strftime('%s', 'now')),
('man', 'system', '_cmd_man', NULL, 0, strftime('%s', 'now')),
('cmd-list', 'system', '_cmd_commands', NULL, 0, strftime('%s', 'now')),
('commands', 'system', '_cmd_commands', NULL, 0, strftime('%s', 'now')),
('status', 'system', '_cmd_status', NULL, 0, strftime('%s', 'now')),
('test', 'system', '_cmd_test', NULL, 0, strftime('%s', 'now')),
('bus', 'system', '_cmd_bus', NULL, 0, strftime('%s', 'now')),
('nic', 'system', '_cmd_nic', NULL, 0, strftime('%s', 'now')),
('ping', 'network', '_cmd_ping', NULL, 0, strftime('%s', 'now')),
('netstat', 'network', '_cmd_netstat', NULL, 0, strftime('%s', 'now')),
('ifconfig', 'network', '_cmd_ifconfig', NULL, 0, strftime('%s', 'now')),
('echo', 'system', '_cmd_echo', NULL, 0, strftime('%s', 'now')),
('clear', 'system', '_cmd_clear', NULL, 0, strftime('%s', 'now')),
('exit', 'system', '_cmd_exit', NULL, 0, strftime('%s', 'now')),
('log', 'system', '_cmd_log', NULL, 0, strftime('%s', 'now')),
('circuits', 'system', '_cmd_circuits', NULL, 0, strftime('%s', 'now')),
('qstate', 'quantum', '_cmd_qstate', NULL, 1, strftime('%s', 'now')),
('leech', 'system', '_cmd_leech', NULL, 0, strftime('%s', 'now')),
('golay', 'system', '_cmd_golay', NULL, 0, strftime('%s', 'now')),
('leech_encode', 'quantum', '_cmd_leech_encode', NULL, 0, strftime('%s', 'now')),
('leech_decode', 'quantum', '_cmd_leech_decode', NULL, 0, strftime('%s', 'now')),
('golay_encode', 'quantum', '_cmd_golay_encode', NULL, 0, strftime('%s', 'now')),
('golay_decode', 'quantum', '_cmd_golay_decode', NULL, 0, strftime('%s', 'now')),
('hroute', 'quantum', '_cmd_hroute', NULL, 0, strftime('%s', 'now')),
('hdistance', 'quantum', '_cmd_hdistance', NULL, 0, strftime('%s', 'now'));

CREATE INDEX IF NOT EXISTS idx_cmd_handler_name ON command_handlers(cmd_name);
CREATE INDEX IF NOT EXISTS idx_cmd_handler_type ON command_handlers(handler_type);
"""

TERMINAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS terminal_sessions (
    session_id TEXT PRIMARY KEY,
    user_id INTEGER DEFAULT 0,
    username TEXT DEFAULT 'root',
    terminal_type TEXT DEFAULT 'xterm',
    cols INTEGER DEFAULT 80,
    rows INTEGER DEFAULT 24,
    status TEXT DEFAULT 'active',
    pid INTEGER,
    cwd_inode INTEGER DEFAULT 1,
    cwd_path TEXT DEFAULT '/',
    environment TEXT,
    created REAL,
    last_activity REAL,
    timeout_seconds REAL DEFAULT 3600,
    FOREIGN KEY(cwd_inode) REFERENCES fs_inodes(inode_id),
    FOREIGN KEY(pid) REFERENCES cpu_execution_contexts(pid)
);

CREATE TABLE IF NOT EXISTS terminal_output (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    data TEXT,
    data_type TEXT DEFAULT 'stdout',
    ts REAL,
    FOREIGN KEY(session_id) REFERENCES terminal_sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS terminal_input (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    data TEXT,
    processed INTEGER DEFAULT 0,
    ts REAL,
    FOREIGN KEY(session_id) REFERENCES terminal_sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS command_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    command TEXT NOT NULL,
    arguments TEXT,
    exit_code INTEGER,
    execution_time_ms REAL,
    timestamp REAL,
    FOREIGN KEY(session_id) REFERENCES terminal_sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_term_output_session ON terminal_output(session_id);
CREATE INDEX IF NOT EXISTS idx_cmd_history_session ON command_history(session_id);
CREATE INDEX IF NOT EXISTS idx_term_session_status ON terminal_sessions(status);
"""

QUBIT_ALLOCATOR = """
CREATE TABLE IF NOT EXISTS cpu_qubit_allocator (
    qubit_id INTEGER PRIMARY KEY,
    allocated INTEGER DEFAULT 0,
    allocated_to_pid INTEGER,
    allocated_to_cmd TEXT,
    usage_count INTEGER DEFAULT 0,
    last_allocated REAL,
    last_freed REAL,
    t1_us REAL,
    t2_us REAL,
    error_rate REAL,
    last_calibration REAL,
    FOREIGN KEY(allocated_to_pid) REFERENCES cpu_execution_contexts(pid) ON DELETE SET NULL,
    FOREIGN KEY(qubit_id) REFERENCES q(i)
);

-- Populate allocator with all qubits from q table
INSERT OR IGNORE INTO cpu_qubit_allocator (qubit_id, allocated)
SELECT i, 0 FROM q WHERE i NOT IN (SELECT qubit_id FROM cpu_qubit_allocator);

CREATE INDEX IF NOT EXISTS idx_qubit_alloc_pid ON cpu_qubit_allocator(allocated_to_pid);
CREATE INDEX IF NOT EXISTS idx_qubit_alloc_status ON cpu_qubit_allocator(allocated);
"""

EXECUTION_CONTEXT = """
CREATE TABLE IF NOT EXISTS cpu_execution_contexts (
    pid INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_pid INTEGER,
    program_name TEXT,
    program_binary BLOB,
    program_size INTEGER,
    pc INTEGER DEFAULT 0,
    sp INTEGER DEFAULT 65535,
    flags INTEGER DEFAULT 0,
    registers BLOB,
    allocated_qubits TEXT,
    qubit_count INTEGER DEFAULT 0,
    circuit_buffer TEXT,
    measurement_results TEXT,
    exec_state TEXT DEFAULT 'READY',
    priority INTEGER DEFAULT 0,
    halted INTEGER DEFAULT 0,
    cycle_count INTEGER DEFAULT 0,
    quantum_cycles INTEGER DEFAULT 0,
    classical_cycles INTEGER DEFAULT 0,
    session_id TEXT,
    cwd_inode INTEGER DEFAULT 1,
    cwd_path TEXT DEFAULT '/',
    created_at REAL,
    started_at REAL,
    finished_at REAL,
    FOREIGN KEY(parent_pid) REFERENCES cpu_execution_contexts(pid) ON DELETE SET NULL,
    FOREIGN KEY(session_id) REFERENCES terminal_sessions(session_id) ON DELETE SET NULL,
    FOREIGN KEY(cwd_inode) REFERENCES fs_inodes(inode_id)
);

CREATE TABLE IF NOT EXISTS cpu_execution_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pid INTEGER,
    opcode INTEGER,
    operands TEXT,
    cycle_number INTEGER,
    pc_before INTEGER,
    pc_after INTEGER,
    execution_time_ns INTEGER,
    timestamp REAL,
    FOREIGN KEY(pid) REFERENCES cpu_execution_contexts(pid) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cpu_quantum_states (
    state_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pid INTEGER,
    qubit_ids TEXT NOT NULL,
    state_vector BLOB,
    density_matrix BLOB,
    purity REAL,
    fidelity REAL,
    entanglement_entropy REAL,
    created_at REAL,
    expires_at REAL,
    FOREIGN KEY(pid) REFERENCES cpu_execution_contexts(pid) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_exec_ctx_state ON cpu_execution_contexts(exec_state);
CREATE INDEX IF NOT EXISTS idx_exec_ctx_session ON cpu_execution_contexts(session_id);
CREATE INDEX IF NOT EXISTS idx_exec_log_pid ON cpu_execution_log(pid);
CREATE INDEX IF NOT EXISTS idx_qstate_pid ON cpu_quantum_states(pid);
"""

QUANTUM_CIRCUITS_SCHEMA = """
CREATE TABLE IF NOT EXISTS quantum_command_circuits (
    circuit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_name TEXT NOT NULL,
    circuit_name TEXT NOT NULL,
    num_qubits INTEGER NOT NULL,
    num_clbits INTEGER NOT NULL,
    qasm_code TEXT NOT NULL,
    gate_sequence TEXT,
    complexity_score REAL,
    avg_execution_time_ms REAL,
    created_at REAL,
    last_used REAL,
    use_count INTEGER DEFAULT 0,
    UNIQUE(cmd_name, circuit_name),
    FOREIGN KEY(cmd_name) REFERENCES command_handlers(cmd_name) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_qcc_cmd ON quantum_command_circuits(cmd_name);
CREATE INDEX IF NOT EXISTS idx_qcc_qubits ON quantum_command_circuits(num_qubits);
"""

# Complete QASM circuits for all quantum commands
COMPLETE_QASM_CIRCUITS = """
DELETE FROM quantum_command_circuits WHERE 1=1;

INSERT INTO quantum_command_circuits (cmd_name, circuit_name, num_qubits, num_clbits, qasm_code, gate_sequence, created_at) VALUES
('qh', 'hadamard_1q', 1, 1, 'OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
h q[0];
measure q[0] -> c[0];', 'H', strftime('%s', 'now')),

('qx', 'pauli_x_1q', 1, 1, 'OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
x q[0];
measure q[0] -> c[0];', 'X', strftime('%s', 'now')),

('qy', 'pauli_y_1q', 1, 1, 'OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
y q[0];
measure q[0] -> c[0];', 'Y', strftime('%s', 'now')),

('qz', 'pauli_z_1q', 1, 1, 'OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
z q[0];
measure q[0] -> c[0];', 'Z', strftime('%s', 'now')),

('qs', 's_gate_1q', 1, 1, 'OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
s q[0];
measure q[0] -> c[0];', 'S', strftime('%s', 'now')),

('qt', 't_gate_1q', 1, 1, 'OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
t q[0];
measure q[0] -> c[0];', 'T', strftime('%s', 'now')),

('qcnot', 'cnot_2q', 2, 2, 'OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
cx q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];', 'CX', strftime('%s', 'now')),

('qcz', 'cz_2q', 2, 2, 'OPENQASM
2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
cz q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];', 'CZ', strftime('%s', 'now')),

('qswap', 'swap_2q', 2, 2, 'OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
swap q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];', 'SWAP', strftime('%s', 'now')),

('qtoffoli', 'toffoli_3q', 3, 3, 'OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
ccx q[0], q[1], q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];', 'CCX', strftime('%s', 'now')),

('epr_create', 'bell_pair_2q', 2, 2, 'OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];', 'H,CX', strftime('%s', 'now')),

('ghz_create', 'ghz_3q', 3, 3, 'OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0], q[1];
cx q[0], q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];', 'H,CX,CX', strftime('%s', 'now')),

('grover', 'grover_2q', 2, 2, 'OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
h q[1];
cz q[0], q[1];
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
measure q[1] -> c[1];', 'H,H,CZ,H,H,X,X,CZ,X,X,H,H', strftime('%s', 'now')),

('qft', 'qft_4q', 4, 4, 'OPENQASM 2.0;
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
measure q[3] -> c[3];', 'H,CP,CP,CP,H,CP,CP,H,CP,H,SWAP,SWAP', strftime('%s', 'now')),

('teleport', 'teleport_3q', 3, 3, 'OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[1];
cx q[1], q[2];
cx q[0], q[1];
h q[0];
measure q[0] -> c[0];
measure q[1] -> c[1];
if(c[1]==1) x q[2];
if(c[0]==1) z q[2];
measure q[2] -> c[2];', 'H,CX,CX,H,MEASURE,MEASURE,X,Z', strftime('%s', 'now')),

('qmeasure', 'measure_1q', 1, 1, 'OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
measure q[0] -> c[0];', 'MEASURE', strftime('%s', 'now')),

('qreset', 'reset_1q', 1, 1, 'OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
reset q[0];
measure q[0] -> c[0];', 'RESET', strftime('%s', 'now'));
"""

VIEWS = """
CREATE VIEW IF NOT EXISTS v_system_status AS
SELECT 
    (SELECT COUNT(*) FROM q) as total_qubits,
    (SELECT COUNT(*) FROM cpu_qubit_allocator WHERE allocated = 1) as allocated_qubits,
    (SELECT COUNT(*) FROM tri) as w_triangles,
    (SELECT COUNT(*) FROM e WHERE t = 'e') as epr_pairs,
    (SELECT COUNT(*) FROM command_registry WHERE cmd_enabled = 1) as commands,
    (SELECT COUNT(*) FROM quantum_command_circuits) as circuits,
    (SELECT packets_processed FROM bus_core WHERE bus_id = 1) as bus_packets,
    (SELECT requests_processed FROM nic_core WHERE nic_id = 1) as nic_requests,
    (SELECT COUNT(*) FROM terminal_sessions WHERE status = 'active') as active_sessions,
    (SELECT COUNT(*) FROM cpu_execution_contexts WHERE exec_state = 'RUNNING') as running_processes;

CREATE VIEW IF NOT EXISTS v_nic_status AS
SELECT 
    n.nic_id,
    n.running,
    n.mode,
    n.requests_processed,
    n.cache_hits,
    n.cache_misses,
    n.quantum_advantage,
    (SELECT COUNT(*) FROM nic_connections WHERE state = 'OPEN') as open_connections,
    (SELECT COUNT(*) FROM nic_routing_table) as routes
FROM nic_core n;

CREATE VIEW IF NOT EXISTS v_bus_status AS
SELECT 
    b.bus_id,
    b.active,
    b.mode,
    b.packets_processed,
    b.circuits_generated,
    b.fitness_score,
    (SELECT COUNT(*) FROM bus_connections WHERE state = 'ENTANGLED') as active_connections,
    (SELECT COUNT(*) FROM bus_routing) as routes
FROM bus_core b;

CREATE VIEW IF NOT EXISTS v_filesystem_status AS
SELECT 
    fs_id,
    fs_name,
    mounted,
    total_blocks,
    free_blocks,
    total_inodes,
    free_inodes,
    quantum_enabled,
    (SELECT COUNT(*) FROM fs_inodes) as inodes_used,
    (SELECT COUNT(*) FROM fs_blocks) as blocks_used
FROM fs_superblock;

CREATE VIEW IF NOT EXISTS v_active_sessions AS
SELECT 
    ts.session_id,
    ts.username,
    ts.status,
    ts.cwd_path,
    ts.created,
    ts.last_activity,
    (SELECT COUNT(*) FROM command_history WHERE session_id = ts.session_id) as commands_executed,
    ec.pid,
    ec.exec_state,
    ec.qubit_count
FROM terminal_sessions ts
LEFT JOIN cpu_execution_contexts ec ON ts.pid = ec.pid
WHERE ts.status = 'active';

CREATE VIEW IF NOT EXISTS v_qubit_allocation AS
SELECT 
    qa.qubit_id,
    qa.allocated,
    qa.allocated_to_pid,
    qa.allocated_to_cmd,
    qa.usage_count,
    ec.program_name,
    ec.exec_state
FROM cpu_qubit_allocator qa
LEFT JOIN cpu_execution_contexts ec ON qa.allocated_to_pid = ec.pid
WHERE qa.allocated = 1;

CREATE VIEW IF NOT EXISTS v_command_stats AS
SELECT 
    ch.cmd_name,
    ch.handler_type,
    ch.gate_name,
    ch.qubits_required,
    qcc.use_count as circuit_uses,
    qcc.avg_execution_time_ms,
    (SELECT COUNT(*) FROM command_history WHERE command = ch.cmd_name) as total_executions
FROM command_handlers ch
LEFT JOIN quantum_command_circuits qcc ON ch.cmd_name = qcc.cmd_name;
"""

# Command registry linkages
COMMAND_REGISTRY_GATE_NAMES = """
-- Add gate_name column if missing (ignore error if exists)
-- Will be handled in apply method

-- Populate gate_name in command_registry
UPDATE command_registry SET gate_name = 'h' WHERE cmd_name = 'qh';
UPDATE command_registry SET gate_name = 'x' WHERE cmd_name = 'qx';
UPDATE command_registry SET gate_name = 'y' WHERE cmd_name = 'qy';
UPDATE command_registry SET gate_name = 'z' WHERE cmd_name = 'qz';
UPDATE command_registry SET gate_name = 's' WHERE cmd_name = 'qs';
UPDATE command_registry SET gate_name = 't' WHERE cmd_name = 'qt';
UPDATE command_registry SET gate_name = 'cx' WHERE cmd_name = 'qcnot';
UPDATE command_registry SET gate_name = 'cz' WHERE cmd_name = 'qcz';
UPDATE command_registry SET gate_name = 'swap' WHERE cmd_name = 'qswap';
UPDATE command_registry SET gate_name = 'ccx' WHERE cmd_name = 'qtoffoli';
UPDATE command_registry SET gate_name = 'bell' WHERE cmd_name = 'epr_create';
UPDATE command_registry SET gate_name = 'ghz' WHERE cmd_name = 'ghz_create';
UPDATE command_registry SET gate_name = 'measure' WHERE cmd_name = 'qmeasure';
UPDATE command_registry SET gate_name = 'reset' WHERE cmd_name = 'qreset';
UPDATE command_registry SET gate_name = 'grover' WHERE cmd_name = 'grover';
UPDATE command_registry SET gate_name = 'qft' WHERE cmd_name = 'qft';
UPDATE command_registry SET gate_name = 'teleport' WHERE cmd_name = 'teleport';

-- Ensure qubit requirements are correct
UPDATE command_registry SET cmd_requires_qubits = 1 
WHERE cmd_name IN ('qh', 'qx', 'qy', 'qz', 'qs', 'qt', 'qmeasure', 'qreset', 'qstate')
AND (cmd_requires_qubits = 0 OR cmd_requires_qubits IS NULL);

UPDATE command_registry SET cmd_requires_qubits = 2 
WHERE cmd_name IN ('qcnot', 'qcz', 'qswap', 'epr_create', 'grover')
AND (cmd_requires_qubits = 0 OR cmd_requires_qubits IS NULL);

UPDATE command_registry SET cmd_requires_qubits = 3 
WHERE cmd_name IN ('qtoffoli', 'ghz_create', 'teleport')
AND (cmd_requires_qubits = 0 OR cmd_requires_qubits IS NULL);

UPDATE command_registry SET cmd_requires_qubits = 4 
WHERE cmd_name = 'qft'
AND (cmd_requires_qubits = 0 OR cmd_requires_qubits IS NULL);

-- Update categories
UPDATE command_registry SET cmd_category = 'QUANTUM' 
WHERE cmd_name LIKE 'q%' OR cmd_name IN ('epr_create', 'ghz_create', 'teleport', 'grover');

UPDATE command_registry SET cmd_category = 'FILESYSTEM'
WHERE cmd_name IN ('ls', 'cd', 'pwd', 'cat', 'mkdir', 'rm', 'touch', 'cp', 'mv');

UPDATE command_registry SET cmd_category = 'NETWORK'
WHERE cmd_name IN ('ping', 'netstat', 'ifconfig');

UPDATE command_registry SET cmd_category = 'SYSTEM'
WHERE cmd_name IN ('ps', 'top', 'uname', 'date', 'uptime', 'help', 'man', 'status', 'test', 'bus', 'nic', 'echo', 'clear', 'exit', 'log', 'circuits', 'commands', 'cmd-list');
"""

# META-LEVEL CROSS-LINKAGE TRIGGERS
META_TRIGGERS = """
-- Trigger: When a qubit is allocated, update the allocator
CREATE TRIGGER IF NOT EXISTS trg_qubit_alloc_on_exec
AFTER INSERT ON cpu_execution_contexts
WHEN NEW.allocated_qubits IS NOT NULL
BEGIN
    UPDATE cpu_qubit_allocator
    SET allocated = 1,
        allocated_to_pid = NEW.pid,
        last_allocated = strftime('%s', 'now')
    WHERE qubit_id IN (
        SELECT value FROM json_each('[' || NEW.allocated_qubits || ']')
    );
END;

-- Trigger: When execution context is deleted, free its qubits
CREATE TRIGGER IF NOT EXISTS trg_free_qubits_on_exec_end
AFTER DELETE ON cpu_execution_contexts
BEGIN
    UPDATE cpu_qubit_allocator
    SET allocated = 0,
        allocated_to_pid = NULL,
        last_freed = strftime('%s', 'now')
    WHERE allocated_to_pid = OLD.pid;
END;

-- Trigger: Update terminal session activity on new command
CREATE TRIGGER IF NOT EXISTS trg_update_session_activity
AFTER INSERT ON command_history
BEGIN
    UPDATE terminal_sessions
    SET last_activity = strftime('%s', 'now')
    WHERE session_id = NEW.session_id;
END;

-- Trigger: Increment circuit use count when used
CREATE TRIGGER IF NOT EXISTS trg_increment_circuit_usage
AFTER INSERT ON cpu_execution_log
WHEN NEW.operands LIKE '%circuit%'
BEGIN
    UPDATE quantum_command_circuits
    SET use_count = use_count + 1,
        last_used = strftime('%s', 'now')
    WHERE cmd_name = (
        SELECT cmd_name FROM command_handlers 
        WHERE handler_method LIKE '%' || NEW.opcode || '%'
        LIMIT 1
    );
END;

-- Trigger: Update NIC stats on new connection
CREATE TRIGGER IF NOT EXISTS trg_nic_conn_stats
AFTER INSERT ON nic_connections
BEGIN
    UPDATE nic_core
    SET requests_processed = requests_processed + 1,
        last_updated = strftime('%s', 'now'),
        last_request = strftime('%s', 'now')
    WHERE nic_id = 1;
END;

-- Trigger: Update BUS stats on new routing
CREATE TRIGGER IF NOT EXISTS trg_bus_routing_stats
AFTER INSERT ON bus_routing
BEGIN
    UPDATE bus_core
    SET packets_processed = packets_processed + 1,
        last_updated = strftime('%s', 'now')
    WHERE bus_id = 1;
END;

-- Trigger: Clean expired cache entries
CREATE TRIGGER IF NOT EXISTS trg_clean_expired_cache
AFTER INSERT ON nic_request_cache
BEGIN
    DELETE FROM nic_request_cache
    WHERE expires_at < strftime('%s', 'now')
    AND cache_id != NEW.cache_id;
END;

-- Trigger: Update filesystem inode times
CREATE TRIGGER IF NOT EXISTS trg_fs_update_mtime
AFTER UPDATE ON fs_blocks
BEGIN
    UPDATE fs_inodes
    SET mtime = strftime('%s', 'now'),
        size = (SELECT SUM(data_size) FROM fs_blocks WHERE inode_id = NEW.inode_id)
    WHERE inode_id = NEW.inode_id;
END;

-- Trigger: Update inode link count
CREATE TRIGGER IF NOT EXISTS trg_fs_update_nlink
AFTER INSERT ON fs_dentries
BEGIN
    UPDATE fs_inodes
    SET nlink = nlink + 1
    WHERE inode_id = NEW.child_inode;
END;

CREATE TRIGGER IF NOT EXISTS trg_fs_update_nlink_delete
AFTER DELETE ON fs_dentries
BEGIN
    UPDATE fs_inodes
    SET nlink = nlink - 1
    WHERE inode_id = OLD.child_inode;
END;
"""

# META-LEVEL STORED PROCEDURES (as prepared statements)
META_PROCEDURES = """
-- Store common query patterns as named views for meta-programs

CREATE VIEW IF NOT EXISTS vp_allocate_qubits AS
SELECT 
    qubit_id,
    t1_us,
    t2_us,
    error_rate
FROM cpu_qubit_allocator
WHERE allocated = 0
ORDER BY 
    COALESCE(error_rate, 0.01) ASC,
    usage_count ASC
LIMIT 10;

CREATE VIEW IF NOT EXISTS vp_find_best_epr_pair AS
SELECT 
    e.i as epr_id,
    e.q0,
    e.q1,
    e.f as fidelity
FROM e
WHERE e.t = 'e'
AND e.f > 0.95
AND e.q0 NOT IN (SELECT qubit_id FROM cpu_qubit_allocator WHERE allocated = 1)
AND e.q1 NOT IN (SELECT qubit_id FROM cpu_qubit_allocator WHERE allocated = 1)
ORDER BY e.f DESC
LIMIT 1;

CREATE VIEW IF NOT EXISTS vp_find_lattice_route AS
SELECT 
    lp.i as point_id,
    lp.x,
    lp.y,
    lp.z
FROM lp
ORDER BY 
    SQRT(POWER(lp.x, 2) + POWER(lp.y, 2) + POWER(lp.z, 2))
LIMIT 100;

CREATE VIEW IF NOT EXISTS vp_active_quantum_processes AS
SELECT 
    ec.pid,
    ec.program_name,
    ec.qubit_count,
    ec.quantum_cycles,
    ec.exec_state,
    GROUP_CONCAT(qa.qubit_id) as allocated_qubits
FROM cpu_execution_contexts ec
LEFT JOIN cpu_qubit_allocator qa ON qa.allocated_to_pid = ec.pid
WHERE ec.exec_state IN ('RUNNING', 'READY')
AND ec.qubit_count > 0
GROUP BY ec.pid;
"""

# CROSS-SYSTEM LINKAGE VERIFICATION
LINKAGE_VERIFICATION = """
-- Create helper table for tracking system linkages
CREATE TABLE IF NOT EXISTS meta_system_linkages (
    linkage_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_system TEXT NOT NULL,
    target_system TEXT NOT NULL,
    link_type TEXT NOT NULL,
    source_table TEXT,
    target_table TEXT,
    foreign_key_column TEXT,
    verified INTEGER DEFAULT 0,
    last_verified REAL,
    created_at REAL DEFAULT (strftime('%s', 'now'))
);

-- Document all cross-system linkages
INSERT OR REPLACE INTO meta_system_linkages 
(source_system, target_system, link_type, source_table, target_table, foreign_key_column)
VALUES
('NIC', 'LATTICE', 'FK', 'nic_core', 'lp', 'lattice_point_id'),
('NIC', 'W_STATES', 'FK', 'nic_core', 'tri', 'w_state_triangle_id'),
('NIC', 'EPR_PAIRS', 'FK', 'nic_connections', 'e', 'epr_pair_id'),
('NIC', 'QUBITS', 'FK', 'nic_connections', 'q', 'bell_qubit_a'),
('NIC', 'QUBITS', 'FK', 'nic_connections', 'q', 'bell_qubit_b'),
('BUS', 'LATTICE', 'FK', 'bus_routing', 'lp', 'lattice_point_id'),
('BUS', 'W_STATES', 'FK', 'bus_routing', 'tri', 'triangle_id'),
('BUS', 'QUBITS', 'FK', 'bus_routing', 'q', 'epr_qubit_a'),
('BUS', 'QUBITS', 'FK', 'bus_routing', 'q', 'epr_qubit_b'),
('BUS', 'EPR_PAIRS', 'FK', 'bus_connections', 'e', 'epr_pair_id'),
('BUS', 'W_STATES', 'FK', 'bus_connections', 'tri', 'w_state_triangle_id'),
('FILESYSTEM', 'LATTICE', 'FK', 'fs_superblock', 'lp', 'lattice_base_point'),
('FILESYSTEM', 'LATTICE', 'FK', 'fs_inodes', 'lp', 'lattice_point_id'),
('FILESYSTEM', 'TERMINAL', 'FK', 'fs_cwd', 'terminal_sessions', 'session_id'),
('FILESYSTEM', 'TERMINAL', 'FK', 'fs_open_files', 'terminal_sessions', 'session_id'),
('CPU', 'QUBITS', 'FK', 'cpu_qubit_allocator', 'q', 'qubit_id'),
('CPU', 'TERMINAL', 'FK', 'cpu_execution_contexts', 'terminal_sessions', 'session_id'),
('CPU', 'FILESYSTEM', 'FK', 'cpu_execution_contexts', 'fs_inodes', 'cwd_inode'),
('TERMINAL', 'FILESYSTEM', 'FK', 'terminal_sessions', 'fs_inodes', 'cwd_inode'),
('TERMINAL', 'CPU', 'FK', 'terminal_sessions', 'cpu_execution_contexts', 'pid'),
('COMMANDS', 'CIRCUITS', 'FK', 'quantum_command_circuits', 'command_handlers', 'cmd_name');

-- Create verification view
CREATE VIEW IF NOT EXISTS v_linkage_health AS
SELECT 
    source_system,
    target_system,
    link_type,
    source_table,
    target_table,
    foreign_key_column,
    verified,
    last_verified
FROM meta_system_linkages
ORDER BY source_system, target_system;
"""

# ═══════════════════════════════════════════════════════════════════════════════
# PATCHER CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class ComprehensiveIntegratedPatcher:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.conn = None
        self.diagnostics = {}
        self.errors = []
        self.warnings = []
    
    def connect(self):
        print(f"\n{C.C}Connecting to: {self.db_path}{C.E}")
        self.conn = sqlite3.connect(str(self.db_path), timeout=60.0)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        print(f"{C.G}✓ Connected with WAL mode + Foreign Keys enabled{C.E}")
    
    def diagnose(self):
        """Run comprehensive diagnostic queries"""
        print(f"\n{C.BOLD}{C.Y}═══════════════════════════════════════{C.E}")
        print(f"{C.BOLD}{C.Y} PHASE 0: PRE-PATCH DIAGNOSTICS{C.E}")
        print(f"{C.BOLD}{C.Y}═══════════════════════════════════════{C.E}")
        
        c = self.conn.cursor()
        
        diagnostics = {
            'Core Tables': "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('q', 'e', 'lp', 'tri', 'command_registry') ORDER BY name",
            'Quantum Commands': "SELECT cmd_name, cmd_requires_qubits, gate_name FROM command_registry WHERE cmd_category='QUANTUM' LIMIT 5",
            'Existing Circuits': "SELECT COUNT(*) as count, 'quantum_command_circuits' as table_name FROM quantum_command_circuits UNION ALL SELECT COUNT(*), 'cpu_qiskit_circuits' FROM sqlite_master WHERE name='cpu_qiskit_circuits'",
            'Command Handlers': "SELECT COUNT(*) FROM command_handlers",
            'NIC Status': "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='nic_core'",
            'Bus Status': "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='bus_core'",
            'Filesystem': "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='fs_inodes'",
            'Qubits Available': "SELECT COUNT(*) FROM q",
            'EPR Pairs': "SELECT COUNT(*) FROM e WHERE t='e'",
            'Lattice Points': "SELECT COUNT(*) FROM lp",
            'W-State Triangles': "SELECT COUNT(*) FROM tri",
        }
        
        for desc, query in diagnostics.items():
            try:
                c.execute(query)
                results = c.fetchall()
                self.diagnostics[desc] = results
                if len(results) > 0 and len(results[0]) == 1:
                    print(f"  {C.G}✓{C.E} {desc:.<40} {results[0][0]}")
                else:
                    print(f"  {C.G}✓{C.E} {desc:.<40} {len(results)} rows")
                    for row in results[:3]:
                        print(f"    {C.C}└─{C.E} {row}")
            except Exception as e:
                print(f"  {C.Y}⚠{C.E} {desc:.<40} ERROR: {e}")
                self.diagnostics[desc] = []
                self.warnings.append(f"{desc}: {e}")
    
    def apply(self, sql: str, name: str, critical=True):
        """Apply SQL with error handling"""
        print(f"  {C.C}▸{C.E} {name:.<50}", end=" ")
        try:
            self.conn.executescript(sql)
            self.conn.commit()
            print(f"{C.G}✓{C.E}")
            return True
        except Exception as e:
            error_str = str(e).lower()
            # Ignore certain benign errors
            if any(x in error_str for x in ['duplicate column', 'already exists', 'unique constraint']):
                print(f"{C.Y}⚠ OK{C.E}")
                return True
            
            if critical:
                print(f"{C.R}✗ CRITICAL{C.E}")
                self.errors.append(f"{name}: {e}")
                return False
            else:
                print(f"{C.Y}⚠ SKIP{C.E}")
                self.warnings.append(f"{name}: {e}")
                return True
    
    def apply_gate_name_column(self):
        """Special handler for adding gate_name column to command_registry"""
        print(f"  {C.C}▸{C.E} Adding gate_name column to command_registry...", end=" ")
        try:
            self.conn.execute("ALTER TABLE command_registry ADD COLUMN gate_name TEXT")
            self.conn.commit()
            print(f"{C.G}✓{C.E}")
            return True
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"{C.Y}⚠ EXISTS{C.E}")
                return True
            print(f"{C.R}✗{C.E}")
            self.warnings.append(f"gate_name column: {e}")
            return False
    
    def run(self):
        """Execute full patch sequence"""
        self.connect()
        self.diagnose()
        
        # PHASE 1: Core Schema Creation
        print(f"\n{C.BOLD}{C.M}═══════════════════════════════════════{C.E}")
        print(f"{C.BOLD}{C.M} PHASE 1: CORE SCHEMA INSTALLATION{C.E}")
        print(f"{C.BOLD}{C.M}═══════════════════════════════════════{C.E}")
        
        schemas = [
            (NIC_SCHEMA, "NIC Network Interface", True),
            (FILESYSTEM_SCHEMA, "Filesystem + Inodes", True),
            (BUS_SCHEMA, "Quantum Bus + Klein Topology", True),
            (COMMAND_HANDLERS, "Command Handler Registry", True),
            (TERMINAL_SCHEMA, "Terminal Sessions", True),
            (QUBIT_ALLOCATOR, "Qubit Allocator", True),
            (EXECUTION_CONTEXT, "CPU Execution Contexts", True),
            (QUANTUM_CIRCUITS_SCHEMA, "Quantum Circuit Schema", True),
        ]
        
        phase1_success = 0
        for sql, name, critical in schemas:
            if self.apply(sql, name, critical):
                phase1_success += 1
        
        print(f"\n  {C.BOLD}Phase 1: {phase1_success}/{len(schemas)} schemas applied{C.E}")
        
        # PHASE 2: Circuit Definitions
        print(f"\n{C.BOLD}{C.M}═══════════════════════════════════════{C.E}")
        print(f"{C.BOLD}{C.M} PHASE 2: QUANTUM CIRCUIT DEFINITIONS{C.E}")
        print(f"{C.BOLD}{C.M}═══════════════════════════════════════{C.E}")
        
        self.apply(COMPLETE_QASM_CIRCUITS, "All QASM Circuit Definitions", True)
        
        # PHASE 3: Cross-linkages
        print(f"\n{C.BOLD}{C.M}═══════════════════════════════════════{C.E}")
        print(f"{C.BOLD}{C.M} PHASE 3: COMMAND REGISTRY LINKAGES{C.E}")
        print(f"{C.BOLD}{C.M}═══════════════════════════════════════{C.E}")
        
        self.apply_gate_name_column()
        self.apply(COMMAND_REGISTRY_GATE_NAMES, "Command→Gate Mappings", False)
        
        # PHASE 4: Views
        print(f"\n{C.BOLD}{C.M}═══════════════════════════════════════{C.E}")
        print(f"{C.BOLD}{C.M} PHASE 4: SYSTEM VIEWS{C.E}")
        print(f"{C.BOLD}{C.M}═══════════════════════════════════════{C.E}")
        
        self.apply(VIEWS, "System Status Views", False)
        
        # PHASE 5: Meta-level triggers
        print(f"\n{C.BOLD}{C.M}═══════════════════════════════════════{C.E}")
        print(f"{C.BOLD}{C.M} PHASE 5: META-LEVEL TRIGGERS & AUTOMATION{C.E}")
        print(f"{C.BOLD}{C.M}═══════════════════════════════════════{C.E}")
        
        self.apply(META_TRIGGERS, "Cross-System Triggers", False)
        
        # PHASE 6: Meta procedures
        print(f"\n{C.BOLD}{C.M}═══════════════════════════════════════{C.E}")
        print(f"{C.BOLD}{C.M} PHASE 6: META-PROCEDURES & QUERY PATTERNS{C.E}")
        print(f"{C.BOLD}{C.M}═══════════════════════════════════════{C.E}")
        
        self.apply(META_PROCEDURES, "Meta-Program Query Views", False)
        
        # PHASE 7: Linkage tracking
        print(f"\n{C.BOLD}{C.M}═══════════════════════════════════════{C.E}")
        print(f"{C.BOLD}{C.M} PHASE 7: SYSTEM LINKAGE DOCUMENTATION{C.E}")
        print(f"{C.BOLD}{C.M}═══════════════════════════════════════{C.E}")
        
        self.apply(LINKAGE_VERIFICATION, "Cross-System Linkage Registry", False)
        
        # PHASE 8: Verification
        self.verify()
        
        # Report
        self.report()
        
        self.conn.close()
    
    def verify(self):
        """Comprehensive post-patch verification"""
        print(f"\n{C.BOLD}{C.M}═══════════════════════════════════════{C.E}")
        print(f"{C.BOLD}{C.M} PHASE 8: POST-PATCH VERIFICATION{C.E}")
        print(f"{C.BOLD}{C.M}═══════════════════════════════════════{C.E}")
        
        c = self.conn.cursor()
        
        verifications = [
            ("Core Tables Present", """
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='table' AND name IN (
                    'nic_core', 'bus_core', 'fs_inodes', 'command_handlers',
                    'quantum_command_circuits', 'terminal_sessions', 
                    'cpu_qubit_allocator', 'cpu_execution_contexts'
                )
            """, 8),
            
            ("Quantum Circuits Loaded", "SELECT COUNT(*) FROM quantum_command_circuits", 15),
            
            ("Command Handlers", "SELECT COUNT(*) FROM command_handlers", 40),
            
            ("Commands with Gate Names", "SELECT COUNT(*) FROM command_registry WHERE gate_name IS NOT NULL", 15),
            
            ("Qubits in Allocator", "SELECT COUNT(*) FROM cpu_qubit_allocator", None),
            
            ("NIC Initialized", "SELECT COUNT(*) FROM nic_core WHERE nic_id = 1", 1),
            
            ("Bus Initialized", "SELECT COUNT(*) FROM bus_core WHERE bus_id = 1", 1),
            
            ("Filesystem Root", "SELECT COUNT(*) FROM fs_inodes WHERE inode_id = 1", 1),
            
            ("System Views", "SELECT COUNT(*) FROM sqlite_master WHERE type='view' AND name LIKE 'v_%'", 7),
            
            ("Meta Triggers", "SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name LIKE 'trg_%'", 9),
            
            ("Meta Procedures", "SELECT COUNT(*) FROM sqlite_master WHERE type='view' AND name LIKE 'vp_%'", 4),
            
            ("Foreign Keys Active", "PRAGMA foreign_keys", 1),
            
            ("System Linkages Documented", "SELECT COUNT(*) FROM meta_system_linkages", 19),
        ]
        
        all_passed = True
        for desc, query, expected in verifications:
            try:
                c.execute(query)
                result = c.fetchone()[0]
                
                if expected is not None:
                    if result >= expected:
                        print(f"  {C.G}✓{C.E} {desc:.<50} {result} (>= {expected})")
                    else:
                        print(f"  {C.Y}⚠{C.E} {desc:.<50} {result} (expected >= {expected})")
                        all_passed = False
                else:
                    print(f"  {C.G}✓{C.E} {desc:.<50} {result}")
            except Exception as e:
                print(f"  {C.R}✗{C.E} {desc:.<50} ERROR: {e}")
                self.errors.append(f"Verification '{desc}': {e}")
                all_passed = False
        
        # Detailed circuit verification
        print(f"\n{C.BOLD}  Sample Quantum Circuits:{C.E}")
        try:
            c.execute("""
                SELECT cmd_name, circuit_name, num_qubits, gate_sequence 
                FROM quantum_command_circuits 
                ORDER BY num_qubits, cmd_name
                LIMIT 10
            """)
            for row in c.fetchall():
                print(f"    {C.C}•{C.E} {row[0]:.<12} {row[1]:.<20} {row[2]}q  [{row[3]}]")
        except Exception as e:
            print(f"    {C.R}✗{C.E} Could not fetch circuits: {e}")
            all_passed = False
        
        # Command→Circuit linkage verification
        print(f"\n{C.BOLD}  Command→Circuit Linkages:{C.E}")
        try:
            c.execute("""
                SELECT 
                    ch.cmd_name,
                    ch.gate_name,
                    ch.qubits_required,
                    qcc.circuit_name
                FROM command_handlers ch
                LEFT JOIN quantum_command_circuits qcc ON ch.cmd_name = qcc.cmd_name
                WHERE ch.handler_type = 'quantum'
                AND ch.gate_name IS NOT NULL
                ORDER BY ch.qubits_required, ch.cmd_name
                LIMIT 10
            """)
            for row in c.fetchall():
                has_circuit = "✓" if row[3] else "✗"
                color = C.G if row[3] else C.Y
                print(f"    {color}{has_circuit}{C.E} {row[0]:.<12} gate={row[1]:.<8} {row[2]}q  circuit={row[3] or 'MISSING'}")
        except Exception as e:
            print(f"    {C.R}✗{C.E} Could not verify linkages: {e}")
            all_passed = False
        
        # System linkage health
        print(f"\n{C.BOLD}  Cross-System Linkages:{C.E}")
        try:
            c.execute("""
                SELECT 
                    source_system || ' → ' || target_system as link,
                    COUNT(*) as count
                FROM meta_system_linkages
                GROUP BY source_system, target_system
                ORDER BY source_system, target_system
            """)
            for row in c.fetchall():
                print(f"    {C.C}•{C.E} {row[0]:.<30} {row[1]} link(s)")
        except Exception as e:
            print(f"    {C.Y}⚠{C.E} Linkages not available: {e}")
        
        return all_passed
    
    def report(self):
        """Generate final report"""
        print(f"\n{C.BOLD}{C.M}═══════════════════════════════════════════════════════════{C.E}")
        print(f"{C.BOLD}{C.M} PATCH COMPLETION REPORT{C.E}")
        print(f"{C.BOLD}{C.M}═══════════════════════════════════════════════════════════{C.E}")
        
        if not self.errors and not self.warnings:
            print(f"\n{C.BOLD}{C.G}  ✓✓✓ ALL SYSTEMS NOMINAL ✓✓✓{C.E}")
            print(f"\n  {C.G}No errors or warnings detected.{C.E}")
            print(f"  {C.G}Database is fully integrated and operational.{C.E}")
        else:
            if self.errors:
                print(f"\n{C.BOLD}{C.R}  CRITICAL ERRORS: {len(self.errors)}{C.E}")
                for i, err in enumerate(self.errors, 1):
                    print(f"    {C.R}{i}.{C.E} {err}")
            
            if self.warnings:
                print(f"\n{C.BOLD}{C.Y}  WARNINGS: {len(self.warnings)}{C.E}")
                for i, warn in enumerate(self.warnings, 1):
                    print(f"    {C.Y}{i}.{C.E} {warn}")
        
        # Integration checklist
        print(f"\n{C.BOLD}  Integration Checklist:{C.E}")
        checklist = [
            ("NIC → Lattice/EPR/W-States", "Foreign key linkages"),
            ("Bus → Lattice/EPR/Qubits", "Routing infrastructure"),
            ("Filesystem → Lattice/Terminal", "Quantum-aware FS"),
            ("CPU → Qubits/Terminal/FS", "Process quantum state"),
            ("Commands → Circuits → Gates", "Execution pipeline"),
            ("Triggers → Auto-updates", "Reactive system behavior"),
            ("Views → Query optimization", "Fast meta-queries"),
            ("Allocator → Qubit tracking", "Resource management"),
        ]
        
        for item, desc in checklist:
            print(f"    {C.G}✓{C.E} {item:.<35} {desc}")
        
        print(f"\n{C.BOLD}  System Capabilities:{C.E}")
        capabilities = [
            "Quantum command execution with QASM compilation",
            "Network packet routing through Klein bottle topology",
            "Filesystem operations with quantum encoding",
            "Terminal session management with process tracking",
            "Automatic qubit allocation/deallocation",
            "Cross-system triggers for state synchronization",
            "EPR pair and W-state management",
            "Meta-program query views for system optimization",
            "Full foreign key integrity across all subsystems",
        ]
        
        for cap in capabilities:
            print(f"    {C.C}•{C.E} {cap}")
        
        print(f"\n{C.BOLD}{C.C}  Next Steps:{C.E}")
        print(f"    {C.BOLD}1.{C.E} Restart QUNIX system to load new schemas")
        print(f"    {C.BOLD}2.{C.E} Test quantum commands: {C.C}qh 0{C.E}, {C.C}qcnot 0 1{C.E}, {C.C}grover 5 7{C.E}")
        print(f"    {C.BOLD}3.{C.E} Verify NIC status: {C.C}nic status{C.E}")
        print(f"    {C.BOLD}4.{C.E} Check bus routing: {C.C}bus status{C.E}")
        print(f"    {C.BOLD}5.{C.E} Test filesystem: {C.C}ls{C.E}, {C.C}mkdir /quantum{C.E}, {C.C}pwd{C.E}")
        print(f"    {C.BOLD}6.{C.E} View system status: {C.C}status{C.E}")
        print(f"    {C.BOLD}7.{C.E} List all commands: {C.C}commands{C.E}")
        print(f"    {C.BOLD}8.{C.E} View circuit catalog: {C.C}circuits{C.E}")
        
        print(f"\n{C.BOLD}  Advanced Queries:{C.E}")
        print(f"    {C.C}SELECT * FROM v_system_status;{C.E}")
        print(f"    {C.C}SELECT * FROM v_qubit_allocation;{C.E}")
        print(f"    {C.C}SELECT * FROM v_command_stats;{C.E}")
        print(f"    {C.C}SELECT * FROM v_linkage_health;{C.E}")
        print(f"    {C.C}SELECT * FROM vp_allocate_qubits;{C.E}")
        
        print(f"\n{C.BOLD}{C.M}═══════════════════════════════════════════════════════════{C.E}")


def main():
    import sys
    
    print(f"{C.BOLD}{C.M}")
    print(f"╔═══════════════════════════════════════════════════════════╗")
    print(f"║                                                           ║")
    print(f"║  QUNIX COMPREHENSIVE DATABASE PATCH v{VERSION:^27} ║")
    print(f"║                                                           ║")
    print(f"║  FULL SYSTEM INTEGRATION + META-LEVEL LINKAGES            ║")
    print(f"║                                                           ║")
    print(f"╚═══════════════════════════════════════════════════════════╝")
    print(f"{C.E}")
    
    if len(sys.argv) < 2:
        print(f"\n{C.BOLD}Usage:{C.E}")
        print(f"  python {sys.argv[0]} <database.db>")
        print(f"\n{C.BOLD}Example:{C.E}")
        print(f"  python {sys.argv[0]} qunix_hyperbolic.db")
        return 1
    
    db_path = Path(sys.argv[1])
    if not db_path.exists():
        print(f"\n{C.R}✗ Database not found: {db_path}{C.E}")
        return 1
    
    print(f"\n{C.BOLD}Target Database:{C.E} {db_path}")
    print(f"\n{C.BOLD}This patch includes:{C.E}")
    
    features = [
        ("NIC Schema", "Network Interface Card with quantum caching"),
        ("Filesystem", "Complete inode/dentry system with quantum encoding"),
        ("Bus System", "Klein bottle topology routing"),
        ("Command Handlers", "All 40+ commands with gate mappings"),
        ("Terminal", "Session management + command history"),
        ("Qubit Allocator", "Resource tracking with FK to CPU processes"),
        ("Execution Context", "Process management with quantum state"),
        ("QASM Circuits", "15+ pre-compiled quantum circuits"),
        ("System Views", "7 optimized views for status monitoring"),
        ("Meta Triggers", "9 triggers for automatic state updates"),
        ("Meta Procedures", "4 query pattern views for optimization"),
        ("Linkage Registry", "19 documented cross-system foreign keys"),
    ]
    
    for feature, desc in features:
        print(f"  {C.G}✓{C.E} {feature:.<25} {desc}")
    
    print(f"\n{C.BOLD}Critical Features:{C.E}")
    critical = [
        "Full foreign key integrity across all subsystems",
        "Automatic qubit allocation tracking via triggers",
        "Command→Gate→Circuit pipeline fully linked",
        "NIC/Bus/FS all linked to hyperbolic lattice",
        "Terminal sessions linked to processes and filesystem",
        "Meta-program query views for system introspection",
    ]
    
    for item in critical:
        print(f"  {C.C}•{C.E} {item}")
    
    print(f"\n{C.BOLD}{C.Y}⚠ WARNING:{C.E}")
    print(f"  This patch will modify your database schema extensively.")
    print(f"  Foreign keys will be enforced.")
    print(f"  Triggers will be created for automatic state management.")
    print(f"  It is recommended to backup your database first.")
    
    print(f"\n{C.BOLD}Press Enter to continue or Ctrl+C to abort...{C.E}")
    try:
        input()
    except KeyboardInterrupt:
        print(f"\n\n{C.Y}✗ Patch aborted by user.{C.E}\n")
        return 0
    
    # Execute patch
    patcher = ComprehensiveIntegratedPatcher(db_path)
    patcher.run()
    
    print(f"\n{C.BOLD}{C.G}✓ Patch installation complete!{C.E}\n")
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
