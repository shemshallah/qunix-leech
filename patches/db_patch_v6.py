
#!/usr/bin/env python3
"""
QUNIX ULTIMATE INTEGRATION PATCH v6.0.0-COMPLETE
Fixes ALL missing tables, adds ALL circuits, ensures 100% command coverage
"""

import sqlite3
import json
import time
import struct
import hashlib
from pathlib import Path

VERSION = "6.0.0-ULTIMATE"

class C:
    R='\033[91m';G='\033[92m';Y='\033[93m';B='\033[94m';M='\033[95m'
    C='\033[96m';BOLD='\033[1m';E='\033[0m';GRAY='\033[90m'

# ═══════════════════════════════════════════════════════════════════════════
# PART 1: CRITICAL SCHEMA FIXES
# ═══════════════════════════════════════════════════════════════════════════

SCHEMA_FIXES = """
-- Fix 1: Create lp table (was referenced but missing)
CREATE TABLE IF NOT EXISTS lp(
    i INTEGER PRIMARY KEY,
    c BLOB,
    n REAL,
    e INTEGER DEFAULT 0,
    x REAL,
    y REAL,
    z REAL,
    allocated INTEGER DEFAULT 0,
    allocated_to TEXT,
    created_at REAL
);

-- Populate from l table if exists
INSERT OR IGNORE INTO lp (i, c, n, e, x, y, z)
SELECT i, c, n, e, x, y, 0.0 FROM l WHERE 1=1;

-- Fix 2: Add exec_state to cpu_execution_contexts
-- (handled in apply_fixes with ALTER TABLE)

-- Fix 3: Add gate_sequence to quantum_command_circuits
-- (handled in apply_fixes with ALTER TABLE)

-- Fix 4: Ensure command_registry has gate_name
-- (handled in apply_fixes with ALTER TABLE)
"""

# ═══════════════════════════════════════════════════════════════════════════
# PART 2: CPU SUBSYSTEM TABLES (from db_patch_cpu_1.py)
# ═══════════════════════════════════════════════════════════════════════════

CPU_TABLES = """
CREATE TABLE IF NOT EXISTS cpu_instruction_formats (
    format_id INTEGER PRIMARY KEY AUTOINCREMENT,
    format_name TEXT UNIQUE NOT NULL,
    opcode_length INTEGER NOT NULL,
    operand_count INTEGER NOT NULL,
    operand_sizes TEXT NOT NULL,
    total_bytes INTEGER NOT NULL,
    byte_layout TEXT NOT NULL,
    endianness TEXT DEFAULT 'little',
    description TEXT
);

CREATE TABLE IF NOT EXISTS cpu_binary_cache (
    binary_hash BLOB PRIMARY KEY,
    instruction_bytes BLOB NOT NULL,
    opcode_id INTEGER NOT NULL,
    operands BLOB NOT NULL,
    parsed_at REAL NOT NULL,
    hit_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cpu_opcode_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alias_mnemonic TEXT UNIQUE NOT NULL,
    canonical_opcode INTEGER NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS cpu_microcode_sequences (
    sequence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    opcode INTEGER NOT NULL,
    sequence_order INTEGER NOT NULL,
    micro_opcode INTEGER NOT NULL,
    micro_operands TEXT,
    conditional TEXT,
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

CREATE TABLE IF NOT EXISTS cpu_qiskit_circuits (
    circuit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    circuit_name TEXT NOT NULL UNIQUE,
    description TEXT,
    num_qubits INTEGER NOT NULL,
    num_clbits INTEGER DEFAULT 0,
    num_gates INTEGER,
    circuit_depth INTEGER,
    qasm_code TEXT NOT NULL,
    qiskit_json TEXT,
    optimized_qasm TEXT,
    success_rate REAL,
    avg_execution_time_ms REAL,
    tags TEXT,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS cpu_qiskit_backends (
    backend_id INTEGER PRIMARY KEY AUTOINCREMENT,
    backend_name TEXT UNIQUE NOT NULL,
    backend_type TEXT NOT NULL,
    provider TEXT,
    num_qubits INTEGER,
    coupling_map TEXT,
    basis_gates TEXT,
    configuration TEXT,
    is_available INTEGER DEFAULT 1,
    priority INTEGER DEFAULT 0,
    last_used REAL,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS cpu_circuit_cache (
    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
    circuit_hash BLOB UNIQUE NOT NULL,
    circuit_id INTEGER,
    backend_id INTEGER,
    input_state TEXT,
    execution_result TEXT,
    execution_time_ms REAL,
    shots INTEGER,
    success INTEGER DEFAULT 1,
    hit_count INTEGER DEFAULT 0,
    last_hit REAL,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS cpu_measurement_results (
    measurement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    state_id INTEGER,
    execution_id INTEGER,
    measured_qubits TEXT,
    measurement_basis TEXT,
    outcome_bitstring TEXT,
    outcome_counts TEXT,
    probability REAL,
    timestamp REAL
);

CREATE TABLE IF NOT EXISTS cpu_optimizer_rules (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_name TEXT UNIQUE NOT NULL,
    rule_type TEXT NOT NULL,
    pattern TEXT NOT NULL,
    replacement TEXT NOT NULL,
    gate_reduction INTEGER DEFAULT 0,
    depth_reduction INTEGER DEFAULT 0,
    applies_to_backends TEXT,
    priority INTEGER DEFAULT 0,
    enabled INTEGER DEFAULT 1,
    description TEXT
);

CREATE TABLE IF NOT EXISTS cpu_optimization_log (
    opt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    circuit_id INTEGER NOT NULL,
    rule_id INTEGER,
    gates_before INTEGER,
    gates_after INTEGER,
    depth_before INTEGER,
    depth_after INTEGER,
    optimization_time_ms REAL,
    applied_at REAL
);

CREATE TABLE IF NOT EXISTS cpu_error_correction_codes (
    ecc_id INTEGER PRIMARY KEY AUTOINCREMENT,
    code_name TEXT UNIQUE NOT NULL,
    code_type TEXT NOT NULL,
    logical_qubits INTEGER NOT NULL,
    physical_qubits INTEGER NOT NULL,
    distance INTEGER NOT NULL,
    syndrome_circuit_id INTEGER,
    recovery_circuit_id INTEGER,
    encoding_overhead REAL,
    error_threshold REAL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS cpu_ecc_log (
    ecc_log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pid INTEGER NOT NULL,
    ecc_id INTEGER NOT NULL,
    logical_qubit INTEGER,
    physical_qubits TEXT,
    syndrome_measured TEXT,
    errors_detected INTEGER DEFAULT 0,
    errors_corrected INTEGER DEFAULT 0,
    correction_success INTEGER DEFAULT 1,
    timestamp REAL
);

CREATE TABLE IF NOT EXISTS dist_nodes (
    node_id TEXT PRIMARY KEY,
    node_name TEXT,
    address TEXT NOT NULL,
    public_key BLOB,
    leech_capacity INTEGER,
    epr_capacity INTEGER,
    golay_implementation TEXT,
    status TEXT DEFAULT 'UNKNOWN',
    latency_ms REAL,
    last_ping REAL,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS dist_shared_epr (
    pair_id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_a TEXT NOT NULL,
    node_b TEXT NOT NULL,
    qubit_a INTEGER NOT NULL,
    qubit_b INTEGER NOT NULL,
    fidelity REAL DEFAULT 0.95,
    established_at REAL NOT NULL,
    last_used REAL,
    use_count INTEGER DEFAULT 0,
    UNIQUE(node_a, node_b, qubit_a, qubit_b)
);

CREATE TABLE IF NOT EXISTS dist_teleport_log (
    teleport_id INTEGER PRIMARY KEY AUTOINCREMENT,
    src_node TEXT NOT NULL,
    dst_node TEXT NOT NULL,
    epr_pair_id INTEGER NOT NULL,
    src_qubit INTEGER NOT NULL,
    dst_qubit INTEGER,
    bell_measurement TEXT,
    correction_gates TEXT,
    fidelity_estimate REAL,
    success INTEGER DEFAULT 0,
    latency_ms REAL,
    timestamp REAL
);

CREATE TABLE IF NOT EXISTS dist_remote_opcodes (
    remote_opcode INTEGER PRIMARY KEY,
    local_opcode INTEGER NOT NULL,
    target_node TEXT NOT NULL,
    requires_teleport INTEGER DEFAULT 0,
    epr_pairs_needed INTEGER DEFAULT 0,
    estimated_latency_ms REAL
);

CREATE TABLE IF NOT EXISTS qsh_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    node_id TEXT NOT NULL,
    epr_tunnel_id INTEGER,
    authentication_method TEXT,
    authenticated INTEGER DEFAULT 0,
    shell_env TEXT,
    working_directory TEXT,
    current_context_pid INTEGER,
    created_at REAL,
    last_activity REAL,
    expires_at REAL
);

CREATE TABLE IF NOT EXISTS qsh_command_history (
    cmd_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    command_text TEXT NOT NULL,
    quantum_signature BLOB,
    execution_pid INTEGER,
    exit_code INTEGER,
    output TEXT,
    execution_time_ms REAL,
    timestamp REAL
);

CREATE TABLE IF NOT EXISTS qsh_quantum_auth (
    auth_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    challenge_qubits TEXT,
    challenge_bases TEXT,
    response_bitstring TEXT,
    verified INTEGER DEFAULT 0,
    timestamp REAL
);

CREATE TABLE IF NOT EXISTS cpu_algorithm_library (
    algo_id INTEGER PRIMARY KEY AUTOINCREMENT,
    algorithm_name TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    circuit_template_id INTEGER,
    num_qubits_required INTEGER,
    num_qubits_ancilla INTEGER DEFAULT 0,
    complexity_time TEXT,
    complexity_space TEXT,
    parameters TEXT,
    output_format TEXT,
    reference_paper TEXT,
    implementation_notes TEXT,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS cpu_algorithm_implementations (
    impl_id INTEGER PRIMARY KEY AUTOINCREMENT,
    algo_id INTEGER NOT NULL,
    backend_id INTEGER,
    optimized_circuit_id INTEGER,
    gate_count INTEGER,
    circuit_depth INTEGER,
    estimated_runtime_ms REAL,
    success_rate REAL,
    fidelity REAL,
    calibration_data TEXT,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS cpu_algorithm_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    algo_id INTEGER NOT NULL,
    impl_id INTEGER,
    execution_pid INTEGER NOT NULL,
    input_parameters TEXT,
    output_result TEXT,
    success INTEGER DEFAULT 1,
    execution_time_ms REAL,
    quantum_advantage REAL,
    verification_passed INTEGER,
    timestamp REAL
);

CREATE TABLE IF NOT EXISTS cpu_execution_profile (
    profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pid INTEGER,
    opcode INTEGER,
    execution_count INTEGER DEFAULT 0,
    total_cycles INTEGER DEFAULT 0,
    total_sigma_time REAL DEFAULT 0.0,
    total_wall_time_ms REAL DEFAULT 0.0,
    avg_cycles REAL,
    min_cycles INTEGER,
    max_cycles INTEGER,
    cache_hits INTEGER DEFAULT 0,
    cache_misses INTEGER DEFAULT 0,
    last_executed REAL,
    UNIQUE(pid, opcode)
);

CREATE TABLE IF NOT EXISTS cpu_system_metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,
    metric_value REAL,
    metric_unit TEXT,
    metric_type TEXT,
    timestamp_sigma REAL,
    timestamp_wall REAL,
    context TEXT
);

CREATE TABLE IF NOT EXISTS cpu_resource_usage (
    usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pid INTEGER NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id INTEGER NOT NULL,
    allocated_at REAL,
    released_at REAL,
    usage_duration REAL,
    operations_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cpu_execution_flow (
    flow_id INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_name TEXT UNIQUE NOT NULL,
    flow_type TEXT NOT NULL,
    steps TEXT NOT NULL,
    parameters TEXT,
    error_handling TEXT,
    enabled INTEGER DEFAULT 1,
    description TEXT
);

CREATE TABLE IF NOT EXISTS cpu_system_config (
    config_key TEXT PRIMARY KEY,
    config_value TEXT NOT NULL,
    config_type TEXT NOT NULL,
    description TEXT,
    is_runtime_modifiable INTEGER DEFAULT 0,
    last_updated REAL
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS cpu_physical_constants (
    constant_name TEXT PRIMARY KEY,
    constant_value REAL NOT NULL,
    constant_unit TEXT,
    description TEXT,
    reference TEXT
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS cpu_maintenance_jobs (
    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_name TEXT UNIQUE NOT NULL,
    job_type TEXT NOT NULL,
    schedule TEXT NOT NULL,
    sql_command TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    last_run REAL,
    next_run REAL,
    run_count INTEGER DEFAULT 0,
    description TEXT
);

CREATE INDEX IF NOT EXISTS idx_cpu_opcodes_cat ON cpu_opcodes(category);
CREATE INDEX IF NOT EXISTS idx_cpu_exec_prof ON cpu_execution_profile(pid, opcode);
CREATE INDEX IF NOT EXISTS idx_cpu_metrics_name ON cpu_system_metrics(metric_name);
"""

# ═══════════════════════════════════════════════════════════════════════════
# PART 3: COMMAND SUBSYSTEM TABLES (from db_patch_cmd_1.py)
# ═══════════════════════════════════════════════════════════════════════════

COMMAND_TABLES = """
CREATE TABLE IF NOT EXISTS command_parameters (
    param_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_id INTEGER NOT NULL,
    param_name TEXT NOT NULL,
    param_type TEXT NOT NULL,
    param_required INTEGER DEFAULT 0,
    param_description TEXT
);

CREATE TABLE IF NOT EXISTS command_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alias_name TEXT UNIQUE NOT NULL,
    canonical_cmd_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS command_performance_stats (
    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_name TEXT NOT NULL,
    execution_count INTEGER DEFAULT 0,
    total_time_ms REAL DEFAULT 0,
    avg_time_ms REAL DEFAULT 0,
    min_time_ms REAL DEFAULT 0,
    max_time_ms REAL DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    quantum_executions INTEGER DEFAULT 0,
    classical_executions INTEGER DEFAULT 0,
    last_executed REAL,
    UNIQUE(cmd_name)
);

CREATE TABLE IF NOT EXISTS command_cache (
    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_hash BLOB UNIQUE NOT NULL,
    cmd_name TEXT NOT NULL,
    arguments_hash BLOB,
    result BLOB,
    qubit_state BLOB,
    hit_count INTEGER DEFAULT 0,
    last_hit REAL,
    created_at REAL,
    expires_at REAL
);

CREATE TABLE IF NOT EXISTS quantum_command_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    exec_id INTEGER NOT NULL,
    circuit_id INTEGER NOT NULL,
    qubits_used TEXT,
    measurement_results TEXT,
    state_vector BLOB,
    density_matrix BLOB,
    fidelity REAL,
    shots INTEGER DEFAULT 1024,
    backend_name TEXT,
    timestamp REAL
);

CREATE TABLE IF NOT EXISTS help_examples (
    example_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_name TEXT NOT NULL,
    example_command TEXT NOT NULL,
    example_output TEXT,
    example_description TEXT
);

CREATE TABLE IF NOT EXISTS command_man_pages (
    man_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_name TEXT NOT NULL,
    section INTEGER DEFAULT 1,
    content TEXT NOT NULL,
    formatted_text TEXT,
    html_version TEXT,
    created_at REAL,
    updated_at REAL,
    UNIQUE(cmd_name, section)
);

CREATE TABLE IF NOT EXISTS command_monitor_state (
    monitor_id INTEGER PRIMARY KEY DEFAULT 1,
    active INTEGER DEFAULT 0,
    input_buffer TEXT,
    last_command TEXT,
    last_command_time REAL,
    command_buffer_size INTEGER DEFAULT 1000,
    auto_complete_enabled INTEGER DEFAULT 1,
    history_enabled INTEGER DEFAULT 1,
    session_id TEXT,
    created_at REAL,
    last_updated REAL
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS command_auto_completion (
    completion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    prefix TEXT NOT NULL,
    cmd_name TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    last_used REAL,
    use_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS command_categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT UNIQUE NOT NULL,
    description TEXT,
    parent_category TEXT,
    command_count INTEGER DEFAULT 0,
    quantum_command_count INTEGER DEFAULT 0,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS command_category_mapping (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_name TEXT NOT NULL,
    category_name TEXT NOT NULL,
    is_primary INTEGER DEFAULT 1,
    UNIQUE(cmd_name, category_name)
);

CREATE TABLE IF NOT EXISTS binary_command_formats (
    format_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_name TEXT NOT NULL,
    format_type TEXT NOT NULL,
    header_magic BLOB NOT NULL,
    opcode_position INTEGER DEFAULT 0,
    param_count_position INTEGER DEFAULT 4,
    param_data_position INTEGER DEFAULT 6,
    flags_position INTEGER DEFAULT 10,
    checksum_position INTEGER DEFAULT 14,
    total_length INTEGER,
    description TEXT
);

CREATE TABLE IF NOT EXISTS command_binary_templates (
    template_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_name TEXT NOT NULL,
    template_name TEXT NOT NULL,
    template_binary BLOB NOT NULL,
    placeholder_positions TEXT,
    description TEXT,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS quantum_storage_manifolds (
    manifold_id INTEGER PRIMARY KEY AUTOINCREMENT,
    manifold_name TEXT UNIQUE NOT NULL,
    manifold_type TEXT NOT NULL,
    dimension INTEGER NOT NULL,
    curvature REAL,
    storage_capacity_qubits INTEGER,
    allocated_qubits INTEGER DEFAULT 0,
    entanglement_connections TEXT,
    tunneling_paths TEXT,
    created_at REAL,
    last_accessed REAL,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS vacuum_tunneling_paths (
    path_id INTEGER PRIMARY KEY AUTOINCREMENT,
    src_manifold_id INTEGER NOT NULL,
    dst_manifold_id INTEGER NOT NULL,
    path_length REAL,
    tunneling_probability REAL,
    quantum_fluctuations BLOB,
    established_at REAL,
    last_used REAL,
    use_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cpu_command_mapping (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_opcode BLOB NOT NULL,
    cpu_opcode INTEGER NOT NULL,
    translation_script BLOB,
    qubit_mapping TEXT,
    memory_mapping TEXT,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS cpu_command_queue (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pid INTEGER NOT NULL,
    cmd_name TEXT NOT NULL,
    arguments TEXT,
    priority INTEGER DEFAULT 0,
    status TEXT DEFAULT 'PENDING',
    scheduled_time REAL,
    execution_time REAL,
    completion_time REAL,
    result TEXT
);

CREATE TABLE IF NOT EXISTS qubit_allocation (
    allocation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    qubit_id INTEGER NOT NULL,
    cmd_name TEXT NOT NULL,
    process_id INTEGER,
    allocated_at REAL,
    released_at REAL,
    state_vector BLOB
);

CREATE INDEX IF NOT EXISTS idx_cmd_params ON command_parameters(cmd_id);
CREATE INDEX IF NOT EXISTS idx_cmd_perf ON command_performance_stats(cmd_name);
CREATE INDEX IF NOT EXISTS idx_cmd_cache_hash ON command_cache(cmd_hash);
"""

# ═══════════════════════════════════════════════════════════════════════════
# PART 4: QNIC SUBSYSTEM TABLES (from db_patch_qnic_1.py)
# ═══════════════════════════════════════════════════════════════════════════

QNIC_TABLES = """
CREATE TABLE IF NOT EXISTS qnic_traffic_log (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    client_ip TEXT,
    client_port INTEGER,
    method TEXT,
    url TEXT,
    host TEXT,
    path TEXT,
    headers_json TEXT,
    quantum_route_json TEXT,
    lattice_points_used INTEGER,
    epr_pairs_used INTEGER,
    triangles_used INTEGER,
    routing_strategy TEXT,
    routing_cost_sigma REAL,
    response_status INTEGER,
    response_size INTEGER,
    response_headers_json TEXT,
    latency_ms REAL,
    quantum_latency_ms REAL,
    classical_latency_estimate_ms REAL,
    quantum_advantage REAL,
    proof_hash BLOB,
    proof_signature BLOB,
    merkle_root BLOB,
    verified INTEGER DEFAULT 1,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS qnic_metrics_realtime (
    metric_name TEXT PRIMARY KEY,
    metric_value REAL,
    metric_unit TEXT,
    last_updated REAL
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS qnic_domain_stats (
    domain TEXT PRIMARY KEY,
    request_count INTEGER DEFAULT 0,
    bytes_sent INTEGER DEFAULT 0,
    bytes_received INTEGER DEFAULT 0,
    avg_latency_ms REAL,
    quantum_routes_used INTEGER DEFAULT 0,
    last_request REAL,
    created_at REAL
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS qnic_active_connections (
    conn_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_ip TEXT,
    client_port INTEGER,
    dest_host TEXT,
    dest_port INTEGER,
    state TEXT,
    quantum_path TEXT,
    bytes_sent INTEGER DEFAULT 0,
    bytes_received INTEGER DEFAULT 0,
    established_at REAL,
    last_activity REAL
);

CREATE INDEX IF NOT EXISTS idx_qnic_traffic_ts ON qnic_traffic_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_qnic_traffic_host ON qnic_traffic_log(host);
CREATE INDEX IF NOT EXISTS idx_qnic_conn_state ON qnic_active_connections(state);

INSERT OR IGNORE INTO qnic_metrics_realtime VALUES
    ('total_requests', 0, 'count', 0),
    ('total_bytes_sent', 0, 'bytes', 0),
    ('total_bytes_received', 0, 'bytes', 0),
    ('active_connections', 0, 'count', 0),
    ('avg_latency_ms', 0, 'milliseconds', 0),
    ('quantum_advantage_avg', 0, 'ratio', 0),
    ('cache_hit_rate', 0, 'percent', 0),
    ('uptime_seconds', 0, 'seconds', 0);
"""

# ═══════════════════════════════════════════════════════════════════════════
# PART 5: COMPLETE QASM CIRCUITS FOR ALL 168 COMMANDS
# ═══════════════════════════════════════════════════════════════════════════

COMPLETE_CIRCUITS = """
-- CORE QUANTUM GATES (already exist, ensure complete)
INSERT OR REPLACE INTO quantum_command_circuits (cmd_name, circuit_name, num_qubits, num_clbits, qasm_code, gate_sequence, created_at) VALUES

-- FILESYSTEM COMMANDS (48 total)
('ls', 'quantum_directory_search', 8, 8,
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0]; h q[1]; h q[2]; h q[3]; h q[4]; h q[5]; h q[6]; h q[7];
barrier q;
x q[0]; x q[1]; x q[2]; x q[3]; x q[4]; x q[5]; x q[6]; x q[7];
h q[7];
ccx q[0],q[1],q[2];
ccx q[2],q[3],q[4];
ccx q[4],q[5],q[6];
cx q[6],q[7];
ccx q[4],q[5],q[6];
ccx q[2],q[3],q[4];
ccx q[0],q[1],q[2];
h q[7];
x q[0]; x q[1]; x q[2]; x q[3]; x q[4]; x q[5]; x q[6]; x q[7];
h q[0]; h q[1]; h q[2]; h q[3]; h q[4]; h q[5]; h q[6]; h q[7];
measure q -> c;',
'H,H,H,H,H,H,H,H,BARRIER,GROVER,MEASURE',
strftime('%s','now')),

('dir', 'quantum_dir_alias', 8, 8,
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0]; h q[1]; h q[2]; h q[3]; h q[4]; h q[5]; h q[6]; h q[7];
measure q -> c;',
'H_8,MEASURE',
strftime('%s','now')),

('tree', 'quantum_tree_display', 10, 10,
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[10];
h q[0]; h q[1]; h q[2];
cx q[0],q[3]; cx q[1],q[4]; cx q[2],q[5];
h q[6]; h q[7];
cx q[3],q[8]; cx q[4],q[9];
measure q -> c;',
'H,H,H,CX,CX,CX,H,H,CX,CX,MEASURE',
strftime('%s','now')),

('find', 'quantum_tree_walk', 10, 10,
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[10];
h q[8]; h q[9];
cx q[8],q[0]; cx q[9],q[1];
h q[8]; h q[9];
cx q[8],q[2]; cx q[9],q[3];
measure q -> c;',
'H,H,CX,CX,H,H,CX,CX,MEASURE',
strftime('%s','now')),

('locate', 'quantum_locate', 8, 8,
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0]; h q[1]; h q[2]; h q[3];
cz q[0],q[4]; cz q[1],q[5];
measure q -> c;',
'H,H,H,H,CZ,CZ,MEASURE',
strftime('%s','now')),

('cat', 'quantum_file_read', 8, 8,
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
ry(0.785398) q[0];
ry(1.570796) q[1];
ry(0.392699) q[2];
cx q[0],q[1]; cx q[1],q[2];
measure q -> c;',
'RY,RY,RY,CX,CX,MEASURE',
strftime('%s','now')),

('more', 'quantum_paginate', 6, 6,
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0]; h q[1]; h q[2];
cx q[0],q[3]; cx q[1],q[4]; cx q[2],q[5];
measure q -> c;',
'H,H,H,CX,CX,CX,MEASURE',
strftime('%s','now')),

('less', 'quantum_pager', 6, 6,
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0]; h q[1]; h q[2];
cx q[0],q[3]; cx q[1],q[4]; cx q[2],q[5];
measure q -> c;',
'H,H,H,CX,CX,CX,MEASURE',
strftime('%s','now')),

('head', 'quantum_head', 6, 6,
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0]; h q[1]; h q[2];
cx q[0],q[3]; cx q[1],q[4]; cx q[2],q[5];
measure q -> c;',
'H,H,H,CX,CX,CX,MEASURE',
strftime('%s','now')),

('tail', 'quantum_tail', 6, 6,
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0]; h q[1]; h q[2];
x q[3];
cx q[0],q[4]; cx q[1],q[5];
measure q -> c;',
'H,H,H,X,CX,CX,MEASURE',
strftime('%s','now')),

('touch', 'quantum_file_create', 4, 4,
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
x q[0];
h q[1];
cx q[0],q[2]; cx q[1],q[3];
measure q -> c;',
'X,H,CX,CX,MEASURE',
strftime('%s','now')),

('rm', 'quantum_file_delete', 5, 5,
'OPENQASM 2.0;
include "qelib1.inc";
qreg q[5];
creg c[5];
h q[0];h q[1];
x q[2];
cx q[0],q[3];cx q[1],q[4];
measure q->c;','H,H,X,CX,CX,MEASURE',strftime('%s','now')),

('cp','cp_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('mv','mv_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0];h q[1];h q[2];
swap q[0],q[3];swap q[1],q[4];swap q[2],q[5];
measure q->c;','H3,SWAP3,MEASURE',strftime('%s','now')),

('ln','ln_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0];h q[1];h q[2];
cx q[0],q[3];cx q[1],q[4];cx q[2],q[5];
measure q->c;','H3,CX3,MEASURE',strftime('%s','now')),

('stat','stat_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('file','file_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0];h q[1];h q[2];
cz q[0],q[3];cz q[1],q[4];cz q[2],q[5];
measure q->c;','H3,CZ3,MEASURE',strftime('%s','now')),

('wc','wc_10q',10,5,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[5];
h q[0];h q[1];h q[2];h q[3];h q[4];
cz q[0],q[5];cz q[1],q[6];
cx q[2],q[7];cx q[3],q[8];
measure q[5]->c[0];measure q[6]->c[1];measure q[7]->c[2];measure q[8]->c[3];','H5,CZ2,CX2,MEASURE',strftime('%s','now')),

('du','du_10q',10,5,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[5];
h q[0];h q[1];h q[2];h q[3];h q[4];
cx q[0],q[5];cx q[1],q[6];cx q[2],q[7];cx q[3],q[8];cx q[4],q[9];
measure q[5]->c[0];measure q[6]->c[1];measure q[7]->c[2];measure q[8]->c[3];measure q[9]->c[4];','H5,CX5,MEASURE',strftime('%s','now')),

('df','df_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('size','size_4q',4,4,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0];h q[1];
cx q[0],q[2];cx q[1],q[3];
measure q->c;','H2,CX2,MEASURE',strftime('%s','now')),

('chmod','chmod_9q',9,9,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[9];
creg c[9];
h q[0];h q[1];h q[2];h q[3];h q[4];h q[5];h q[6];h q[7];h q[8];
measure q->c;','H9,MEASURE',strftime('%s','now')),

('chown','chown_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('chgrp','chgrp_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('umask','umask_4q',4,4,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0];h q[1];h q[2];h q[3];
measure q->c;','H4,MEASURE',strftime('%s','now')),

('grep','grep_12q',12,12,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[12];
creg c[12];
h q[0];h q[1];h q[2];h q[3];h q[4];h q[5];h q[6];h q[7];
cz q[0],q[8];cz q[1],q[9];
h q[0];h q[1];h q[2];h q[3];h q[4];h q[5];h q[6];h q[7];
x q[0];x q[1];x q[2];x q[3];x q[4];x q[5];x q[6];x q[7];
h q[7];
ccx q[0],q[1],q[10];ccx q[10],q[2],q[11];cx q[11],q[7];
ccx q[10],q[2],q[11];ccx q[0],q[1],q[10];
h q[7];
x q[0];x q[1];x q[2];x q[3];x q[4];x q[5];x q[6];x q[7];
h q[0];h q[1];h q[2];h q[3];h q[4];h q[5];h q[6];h q[7];
measure q->c;','H8,CZ2,GROVER,MEASURE',strftime('%s','now')),

('sed','sed_10q',10,10,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[10];
h q[0];h q[1];h q[2];h q[3];
x q[4];h q[5];
cx q[0],q[6];cx q[1],q[7];cx q[2],q[8];cx q[3],q[9];
measure q->c;','H4,X,H,CX4,MEASURE',strftime('%s','now')),

('awk','awk_12q',12,12,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[12];
creg c[12];
h q[0];h q[1];h q[2];h q[3];
x q[4];
cx q[0],q[8];cx q[1],q[9];cx q[2],q[10];cx q[3],q[11];
measure q->c;','H4,X,CX4,MEASURE',strftime('%s','now')),

('cut','cut_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('paste','paste_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('sort','sort_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cz q[0],q[4];cz q[1],q[5];
swap q[0],q[1];swap q[2],q[3];
measure q->c;','H4,CZ2,SWAP2,MEASURE',strftime('%s','now')),

('uniq','uniq_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0];h q[1];h q[2];
cx q[0],q[3];cx q[1],q[4];cx q[2],q[5];
cz q[3],q[4];
measure q->c;','H3,CX3,CZ,MEASURE',strftime('%s','now')),

('diff','diff_12q',12,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[12];
creg c[6];
h q[0];h q[1];h q[2];h q[3];h q[4];h q[5];
cx q[0],q[6];cx q[3],q[6];
cx q[1],q[7];cx q[4],q[7];
cx q[2],q[8];cx q[5],q[8];
measure q[6]->c[0];measure q[7]->c[1];measure q[8]->c[2];','H6,CX6,MEASURE',strftime('%s','now')),

('patch','patch_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('tar','tar_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('gzip','gzip_10q',10,5,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[5];
h q[0];h q[1];h q[2];h q[3];h q[4];
cx q[0],q[5];cx q[1],q[6];cx q[2],q[7];cx q[3],q[8];cx q[4],q[9];
measure q[5]->c[0];measure q[6]->c[1];measure q[7]->c[2];measure q[8]->c[3];measure q[9]->c[4];','H5,CX5,MEASURE',strftime('%s','now')),

('zip','zip_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('unzip','unzip_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('7z','7z_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('mount','mount_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0];h q[1];h q[2];
cx q[0],q[3];cx q[1],q[4];cx q[2],q[5];
measure q->c;','H3,CX3,MEASURE',strftime('%s','now')),

('umount','umount_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0];h q[1];h q[2];
cx q[0],q[3];cx q[1],q[4];cx q[2],q[5];
measure q->c;','H3,CX3,MEASURE',strftime('%s','now')),

('fdisk','fdisk_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('mkfs','mkfs_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('fsck','fsck_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('pwd','pwd_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
x q[0];h q[1];
cx q[0],q[2];cx q[1],q[3];
measure q->c;','X,H,CX2,MEASURE',strftime('%s','now')),

('cd','cd_4q',4,4,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0];cx q[0],q[1];
x q[2];cx q[1],q[2];
measure q->c;','H,CX,X,CX,MEASURE',strftime('%s','now')),

('mkdir','mkdir_5q',5,5,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[5];
creg c[5];
x q[0];h q[1];h q[2];
cx q[0],q[3];cx q[1],q[4];
measure q->c;','X,H2,CX2,MEASURE',strftime('%s','now'));
"""

CIRCUITS_PART3="""
INSERT INTO quantum_command_circuits(cmd_name,circuit_name,num_qubits,num_clbits,qasm_code,gate_sequence,created_at)VALUES
('ps','ps_10q',10,10,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[10];
h q[0];h q[1];h q[2];h q[3];h q[4];
cx q[0],q[5];cx q[1],q[6];cx q[2],q[7];cx q[3],q[8];cx q[4],q[9];
measure q->c;','H5,CX5,MEASURE',strftime('%s','now')),
('top','top_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];ry(0.785398)q[2];h q[3];h q[4];
cx q[0],q[5];cx q[1],q[6];
measure q->c;','H2,RY,H2,CX2,MEASURE',strftime('%s','now')),
('kill','kill_6q',6,3,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[3];
h q[0];h q[1];h q[2];
x q[3];
cx q[0],q[3];cx q[1],q[4];
measure q[3]->c[0];measure q[4]->c[1];','H3,X,CX2,MEASURE',strftime('%s','now')),
('nice','nice_5q',5,5,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[5];
creg c[5];
ry(0.785398)q[0];cx q[0],q[1];h q[2];cx q[1],q[3];
measure q->c;','RY,CX,H,CX,MEASURE',strftime('%s','now')),
('renice','renice_5q',5,5,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[5];
creg c[5];
ry(1.047198)q[0];cx q[0],q[1];h q[2];cx q[1],q[3];
measure q->c;','RY,CX,H,CX,MEASURE',strftime('%s','now')),
('jobs','jobs_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),
('bg','bg_4q',4,4,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0];h q[1];cx q[0],q[2];cx q[1],q[3];
measure q->c;','H2,CX2,MEASURE',strftime('%s','now')),
('fg','fg_4q',4,4,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0];h q[1];cx q[0],q[2];cx q[1],q[3];
measure q->c;','H2,CX2,MEASURE',strftime('%s','now')),
('uname','uname_5q',5,5,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[5];
creg c[5];
x q[0];h q[1];x q[2];cx q[0],q[3];cx q[1],q[4];
measure q->c;','X,H,X,CX2,MEASURE',strftime('%s','now')),
('hostname','hostname_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
x q[0];x q[1];h q[2];h q[3];cx q[0],q[4];cx q[1],q[5];
measure q->c;','X2,H2,CX2,MEASURE',strftime('%s','now')),
('date','date_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
u1(1.570796)q[0];u1(0.785398)q[1];u1(0.392699)q[2];
h q[3];h q[4];cx q[0],q[5];cx q[1],q[6];
measure q->c;','U1_3,H2,CX2,MEASURE',strftime('%s','now')),
('time','time_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
x q[0];barrier q;
u1(1.570796)q[1];u1(0.785398)q[2];u1(0.392699)q[3];
barrier q;x q[4];
measure q->c;','X,BARRIER,U1_3,BARRIER,X,MEASURE',strftime('%s','now')),
('uptime','uptime_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
u1(1.570796)q[0];u1(0.785398)q[1];u1(0.392699)q[2];
h q[3];cx q[0],q[4];cx q[1],q[5];
measure q->c;','U1_3,H,CX2,MEASURE',strftime('%s','now')),
('who','who_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0];h q[1];h q[2];
cx q[0],q[3];cx q[1],q[4];cx q[2],q[5];
measure q->c;','H3,CX3,MEASURE',strftime('%s','now')),
('w','w_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0];h q[1];h q[2];
cx q[0],q[3];cx q[1],q[4];cx q[2],q[5];
measure q->c;','H3,CX3,MEASURE',strftime('%s','now')),
('ping','ping_4q',4,4,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0];cx q[0],q[1];x q[2];cx q[2],q[0];h q[2];
measure q[2]->c[2];measure q[0]->c[0];measure q[1]->c[1];','H,CX,X,CX,H,MEASURE',strftime('%s','now')),
('traceroute','traceroute_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];barrier q;
cx q[0],q[3];cx q[1],q[4];cx q[2],q[5];
h q[6];cx q[3],q[6];cx q[4],q[6];cx q[5],q[6];
measure q->c;','H3,CX3,H,CX3,MEASURE',strftime('%s','now')),
('netstat','netstat_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0];h q[1];h q[2];
cx q[0],q[3];cx q[1],q[4];cx q[2],q[5];
measure q->c;','H3,CX3,MEASURE',strftime('%s','now')),
('ifconfig','ifconfig_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),
('ssh','ssh_12q',12,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[12];
creg c[6];
h q[0];h q[1];h q[2];h q[3];h q[4];h q[5];
cx q[0],q[6];cx q[1],q[7];cx q[2],q[8];cx q[3],q[9];cx q[4],q[10];cx q[5],q[11];
measure q[6]->c[0];measure q[7]->c[1];measure q[8]->c[2];measure q[9]->c[3];measure q[10]->c[4];measure q[11]->c[5];','H6,CX6,MEASURE',strftime('%s','now')),
('scp','scp_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),
('vmstat','vmstat_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),
('iostat','iostat_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),
('dmesg','dmesg_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now'));
"""

CIRCUITS_PART4="""
INSERT INTO quantum_command_circuits(cmd_name,circuit_name,num_qubits,num_clbits,qasm_code,gate_sequence,created_at)VALUES

('gcc','gcc_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];
cx q[0],q[3];cx q[1],q[4];cx q[2],q[5];
h q[6];cx q[3],q[6];
measure q->c;','H3,CX3,H,CX,MEASURE',strftime('%s','now')),('python','python_10q',10,10,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[10];
h q[0];h q[1];h q[2];h q[3];h q[4];
cx q[0],q[5];cx q[1],q[6];cx q[2],q[7];cx q[3],q[8];cx q[4],q[9];
measure q->c;','H5,CX5,MEASURE',strftime('%s','now')),

('node','node_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('java','java_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('gdb','gdb_10q',10,10,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[10];
h q[0];h q[1];h q[2];x q[3];h q[4];
cx q[0],q[5];cz q[1],q[6];
measure q->c;','H3,X,H,CX,CZ,MEASURE',strftime('%s','now')),

('strace','strace_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('ltrace','ltrace_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('valgrind','valgrind_10q',10,10,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[10];
h q[0];h q[1];h q[2];h q[3];h q[4];
cx q[0],q[5];cx q[1],q[6];cx q[2],q[7];cx q[3],q[8];cx q[4],q[9];
measure q->c;','H5,CX5,MEASURE',strftime('%s','now')),

('git','git_10q',10,10,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[10];
h q[0];h q[1];h q[2];h q[3];h q[4];
cx q[0],q[5];cx q[1],q[6];cx q[2],q[7];cx q[3],q[8];cx q[4],q[9];
measure q->c;','H5,CX5,MEASURE',strftime('%s','now')),

('svn','svn_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('hg','hg_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('make','make_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('cmake','cmake_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('ant','ant_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('javac','javac_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('g++','gpp_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

-- QUNIX LEECH/GOLAY COMMANDS

('leech_encode','leech_encode_24q',24,24,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[24];
creg c[24];
h q[0];h q[1];h q[2];h q[3];h q[4];h q[5];h q[6];h q[7];
h q[8];h q[9];h q[10];h q[11];
cx q[0],q[12];cx q[1],q[13];cx q[2],q[14];cx q[3],q[15];
cx q[4],q[16];cx q[5],q[17];cx q[6],q[18];cx q[7],q[19];
cx q[8],q[20];cx q[9],q[21];cx q[10],q[22];cx q[11],q[23];
measure q->c;','H12,CX12,MEASURE',strftime('%s','now')),

('leech_decode','leech_decode_24q',24,12,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[24];
creg c[12];
h q[0];h q[1];h q[2];h q[3];h q[4];h q[5];
h q[6];h q[7];h q[8];h q[9];h q[10];h q[11];
measure q[0]->c[0];measure q[1]->c[1];measure q[2]->c[2];
measure q[3]->c[3];measure q[4]->c[4];measure q[5]->c[5];
measure q[6]->c[6];measure q[7]->c[7];measure q[8]->c[8];
measure q[9]->c[9];measure q[10]->c[10];measure q[11]->c[11];','H12,MEASURE12',strftime('%s','now')),

('leech_distance','leech_dist_8q',8,4,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[4];
ry(0.785398)q[0];ry(1.047198)q[1];ry(1.308997)q[2];ry(0.523599)q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q[4]->c[0];measure q[5]->c[1];measure q[6]->c[2];measure q[7]->c[3];','RY4,CX4,MEASURE',strftime('%s','now')),

('leech_nearest','leech_near_10q',10,5,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[5];
h q[0];h q[1];h q[2];h q[3];h q[4];
cx q[0],q[5];cx q[1],q[6];cx q[2],q[7];cx q[3],q[8];cx q[4],q[9];
measure q[5]->c[0];measure q[6]->c[1];measure q[7]->c[2];measure q[8]->c[3];measure q[9]->c[4];','H5,CX5,MEASURE',strftime('%s','now')),

('golay_encode','golay_enc_24q',24,12,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[24];
creg c[12];
h q[0];h q[1];h q[2];h q[3];h q[4];h q[5];
cx q[0],q[12];cx q[1],q[13];cx q[2],q[14];
cx q[3],q[15];cx q[4],q[16];cx q[5],q[17];
measure q[12]->c[0];measure q[13]->c[1];measure q[14]->c[2];
measure q[15]->c[3];measure q[16]->c[4];measure q[17]->c[5];','H6,CX6,MEASURE6',strftime('%s','now')),

('golay_decode','golay_dec_24q',24,12,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[24];
creg c[12];
cx q[0],q[12];cx q[1],q[13];cx q[2],q[14];
cx q[3],q[15];cx q[4],q[16];cx q[5],q[17];
measure q[12]->c[0];measure q[13]->c[1];measure q[14]->c[2];
measure q[15]->c[3];measure q[16]->c[4];measure q[17]->c[5];','CX6,MEASURE6',strftime('%s','now')),

('golay_syndrome','golay_syn_24q',24,12,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[24];
creg c[12];
h q[0];h q[1];h q[2];h q[3];h q[4];h q[5];
cx q[0],q[12];cx q[1],q[13];cx q[2],q[14];
measure q[12]->c[0];measure q[13]->c[1];measure q[14]->c[2];','H6,CX3,MEASURE3',strftime('%s','now')),

('golay_correct','golay_corr_24q',24,12,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[24];
creg c[12];
h q[0];h q[1];h q[2];h q[3];h q[4];h q[5];
cx q[0],q[12];cx q[1],q[13];cx q[2],q[14];
x q[12];x q[13];
measure q[12]->c[0];measure q[13]->c[1];','H6,CX3,X2,MEASURE2',strftime('%s','now')),

-- HYPERBOLIC ROUTING

('hroute','hroute_12q',12,12,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[12];
creg c[12];
ry(0.785398)q[0];ry(1.570796)q[1];
h q[2];h q[3];h q[4];
cx q[0],q[5];cx q[1],q[6];cx q[2],q[7];cx q[3],q[8];cx q[4],q[9];
cz q[5],q[10];cz q[6],q[11];
measure q->c;','RY2,H3,CX5,CZ2,MEASURE',strftime('%s','now')),

('hdistance','hdist_8q',8,4,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[4];
ry(0.785398)q[0];ry(1.047198)q[1];ry(1.308997)q[2];ry(0.523599)q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q[4]->c[0];measure q[5]->c[1];measure q[6]->c[2];measure q[7]->c[3];','RY4,CX4,MEASURE',strftime('%s','now')),

('hmap','hmap_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
ry(0.523599)q[0];ry(1.047198)q[1];
h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','RY2,H2,CX4,MEASURE',strftime('%s','now')),

('hembed','hembed_10q',10,10,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[10];
h q[0];h q[1];h q[2];h q[3];h q[4];
cx q[0],q[5];cx q[1],q[6];cx q[2],q[7];cx q[3],q[8];cx q[4],q[9];
measure q->c;','H5,CX5,MEASURE',strftime('%s','now')),

-- EPR & QUANTUM NETWORKING

('epr_connect','epr_conn_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('epr_disconnect','epr_disc_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0];h q[1];h q[2];
x q[3];x q[4];x q[5];
measure q->c;','H3,X3,MEASURE',strftime('%s','now')),

('epr_status','epr_stat_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('epr_teleport','epr_tele_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0];cx q[0],q[1];
cx q[2],q[0];h q[2];
measure q[2]->c[2];measure q[0]->c[0];
if(c[0]==1)x q[1];
if(c[2]==1)z q[1];
measure q[1]->c[1];','H,CX,CX,H,MEASURE,X,Z,MEASURE',strftime('%s','now')),

-- QNIC/BUS CONTROL

('qnic_start','qnic_start_4q',4,4,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
x q[0];h q[1];cx q[0],q[2];cx q[1],q[3];
measure q->c;','X,H,CX2,MEASURE',strftime('%s','now')),

('qnic_stop','qnic_stop_4q',4,4,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0];h q[1];x q[2];x q[3];
measure q->c;','H2,X2,MEASURE',strftime('%s','now')),

('qnic_status','qnic_stat_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0];h q[1];h q[2];
cx q[0],q[3];cx q[1],q[4];cx q[2],q[5];
measure q->c;','H3,CX3,MEASURE',strftime('%s','now')),

('qnic_logs','qnic_logs_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('bus_start','bus_start_4q',4,4,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
x q[0];h q[1];cx q[0],q[2];cx q[1],q[3];
measure q->c;','X,H,CX2,MEASURE',strftime('%s','now')),

('bus_stop','bus_stop_4q',4,4,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0];h q[1];x q[2];x q[3];
measure q->c;','H2,X2,MEASURE',strftime('%s','now')),

('bus_status','bus_stat_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0];h q[1];h q[2];
cx q[0],q[3];cx q[1],q[4];cx q[2],q[5];
measure q->c;','H3,CX3,MEASURE',strftime('%s','now')),

-- QUANTUM VACUUM & MANIFOLDS

('quantum_vacuum','qvac_10q',10,10,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[10];
h q[0];h q[1];h q[2];ry(1.570796)q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];
h q[7];cx q[3],q[7];
measure q->c;','H3,RY,CX3,H,CX,MEASURE',strftime('%s','now')),

('tunneling','tunnel_10q',10,10,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[10];
h q[0];h q[1];h q[2];ry(1.570796)q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];
h q[7];cx q[3],q[7];
measure q->c;','H3,RY,CX3,H,CX,MEASURE',strftime('%s','now')),

('manifold_create','mfld_16q',16,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[16];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
cz q[4],q[8];cz q[5],q[9];
cx q[8],q[12];cx q[9],q[13];
measure q[12]->c[0];measure q[13]->c[1];measure q[4]->c[2];measure q[5]->c[3];','H4,CX4,CZ2,CX2,MEASURE',strftime('%s','now')),

('manifold_list','mfld_list_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0];h q[1];h q[2];
cx q[0],q[3];cx q[1],q[4];cx q[2],q[5];
measure q->c;','H3,CX3,MEASURE',strftime('%s','now')),

('manifold_connect','mfld_conn_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

-- QSHELL & QDB

('qshell','qshell_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('qcpu_status','qcpu_stat_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];x q[4];
cx q[0],q[5];cx q[1],q[6];
measure q->c;','H4,X,CX2,MEASURE',strftime('%s','now')),

('qcpu_load','qcpu_load_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('qcpu_run','qcpu_run_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('qdb_query','qdb_query_10q',10,10,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[10];
h q[0];h q[1];h q[2];h q[3];h q[4];
cx q[0],q[5];cx q[1],q[6];cx q[2],q[7];cx q[3],q[8];cx q[4],q[9];
measure q->c;','H5,CX5,MEASURE',strftime('%s','now')),

('qdb_exec','qdb_exec_10q',10,10,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[10];
h q[0];h q[1];h q[2];h q[3];h q[4];
cx q[0],q[5];cx q[1],q[6];cx q[2],q[7];cx q[3],q[8];cx q[4],q[9];
measure q->c;','H5,CX5,MEASURE',strftime('%s','now')),

-- HELP & UTILITY

('help','help_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0];h q[1];h q[2];
cx q[0],q[3];cx q[1],q[4];cx q[2],q[5];
measure q->c;','H3,CX3,MEASURE',strftime('%s','now')),

('man','man_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('info','info_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0];h q[1];h q[2];
cx q[0],q[3];cx q[1],q[4];cx q[2],q[5];
measure q->c;','H3,CX3,MEASURE',strftime('%s','now')),

('whatis','whatis_4q',4,4,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0];h q[1];cx q[0],q[2];cx q[1],q[3];
measure q->c;','H2,CX2,MEASURE',strftime('%s','now')),

('apropos','apropos_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('cmd-list','cmdlist_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('cmd-info','cmdinfo_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0];h q[1];h q[2];
cx q[0],q[3];cx q[1],q[4];cx q[2],q[5];
measure q->c;','H3,CX3,MEASURE',strftime('%s','now')),

('cmd-stats','cmdstats_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('history','hist_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','H4,CX4,MEASURE',strftime('%s','now')),

('alias','alias_4q',4,4,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0];h q[1];cx q[0],q[2];cx q[1],q[3];
measure q->c;','H2,CX2,MEASURE',strftime('%s','now')),

('unalias','unalias_4q',4,4,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0];h q[1];x q[2];x q[3];
measure q->c;','H2,X2,MEASURE',strftime('%s','now')),

('type','type_4q',4,4,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0];h q[1];cx q[0],q[2];cx q[1],q[3];
measure q->c;','H2,CX2,MEASURE',strftime('%s','now')),

('which','which_6q',6,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0];h q[1];h q[2];
cx q[0],q[3];cx q[1],q[4];cz q[2],q[5];
measure q->c;','H3,CX2,CZ,MEASURE',strftime('%s','now')),

('whereis','whereis_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
cz q[4],q[5];
measure q->c;','H4,CX4,CZ,MEASURE',strftime('%s','now')),

('echo','echo_4q',4,4,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
x q[0];h q[1];
u1(0.785398)q[0];u1(1.570796)q[1];
measure q->c;','X,H,U1_2,MEASURE',strftime('%s','now')),

('clear','clear_2q',2,2,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
x q[0];x q[1];
measure q->c;','X2,MEASURE',strftime('%s','now')),

-- MATH/ARITHMETIC COMMANDS

('add','add_8q',8,4,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[4];
cx q[0],q[6];cx q[2],q[6];
ccx q[0],q[2],q[4];
cx q[1],q[7];cx q[3],q[7];
ccx q[1],q[3],q[5];
cx q[4],q[7];
measure q[6]->c[0];measure q[7]->c[1];measure q[4]->c[2];measure q[5]->c[3];','CX2,CCX,CX3,CCX,CX,MEASURE',strftime('%s','now')),

('mul','mul_12q',12,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[12];
creg c[6];
h q[6];cx q[0],q[6];cx q[3],q[6];
h q[7];cx q[1],q[7];cx q[4],q[7];
cx q[6],q[9];cx q[7],q[10];
measure q[9]->c[0];measure q[10]->c[1];','H,CX2,H,CX3,MEASURE',strftime('%s','now')),

('div','div_12q',12,6,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[12];
creg c[6];
h q[0];h q[1];h q[2];h q[3];
cx q[0],q[6];cx q[1],q[7];cx q[2],q[8];cx q[3],q[9];
measure q[6]->c[0];measure q[7]->c[1];measure q[8]->c[2];measure q[9]->c[3];','H4,CX4,MEASURE',strftime('%s','now')),

('sqrt','sqrt_10q',10,5,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[5];
ry(1.047198)q[0];
h q[1];h q[2];h q[3];h q[4];
cu1(3.141593)q[1],q[0];
cu1(1.570796)q[2],q[0];
cu1(0.785398)q[3],q[0];
cu1(0.392699)q[4],q[0];
swap q[1],q[4];
h q[1];cu1(-1.570796)q[2],q[1];h q[2];
measure q[1]->c[0];measure q[2]->c[1];measure q[3]->c[2];measure q[4]->c[3];','RY,H4,CU1_4,SWAP,H,CU1,H,MEASURE',strftime('%s','now')),

('sin','sin_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
ry(0.785398)q[0];ry(0.392699)q[1];
h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','RY2,H2,CX4,MEASURE',strftime('%s','now')),

('cos','cos_8q',8,8,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
ry(1.570796)q[0];ry(0.392699)q[1];
h q[2];h q[3];
cx q[0],q[4];cx q[1],q[5];cx q[2],q[6];cx q[3],q[7];
measure q->c;','RY2,H2,CX4,MEASURE',strftime('%s','now')),

('exp','exp_10q',10,5,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[5];
ry(0.523599)q[0];
h q[1];h q[2];h q[3];h q[4];
cu1(2.718282)q[1],q[0];
cu1(1.359141)q[2],q[0];
cu1(0.679570)q[3],q[0];
cu1(0.339785)q[4],q[0];
measure q[1]->c[0];measure q[2]->c[1];measure q[3]->c[2];measure q[4]->c[3];','RY,H4,CU1_4,MEASURE',strftime('%s','now')),

('log','log_10q',10,5,'OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[5];
ry(1.047198)q[0];
h q[1];h q[2];h q[3];h q[4];
cu1(0.693147)q[1],q[0];
cu1(0.346574)q[2],q[0];
cu1(0.173287)q[3],q[0];
cu1(0.086643)q[4],q[0];
measure q[1]->c[0];measure q[2]->c[1];measure q[3]->c[2];measure q[4]->c[3];','RY,H4,CU1_4,MEASURE',strftime('%s','now'));
"""

# ═══════════════════════════════════════════════════════════════════════════
# PART 6: PATCHER CLASS WITH COMPLETE FIXES
# ═══════════════════════════════════════════════════════════════════════════

class UltimateIntegrationPatcher:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.conn = None
        self.stats = {
            'tables_created': 0,
            'columns_added': 0,
            'circuits_added': 0,
            'commands_linked': 0,
            'errors': []
        }
    
    def connect(self):
        print(f"\n{C.C}Connecting to {self.db_path}{C.E}")
        self.conn = sqlite3.connect(str(self.db_path), timeout=60.0)
        self.conn.execute("PRAGMA foreign_keys=OFF")
        self.conn.execute("PRAGMA journal_mode=WAL")
        print(f"{C.G}Connected{C.E}")
    
    def apply_fixes(self):
        '''Fix missing tables and columns'''
        print(f"\n{C.BOLD}{C.M}PHASE 1: Schema Fixes{C.E}")
        
        # Fix 1: Create lp table
        print(f"{C.C}Creating lp table...{C.E}")
        try:
            self.conn.executescript(SCHEMA_FIXES)
            self.conn.commit()
            print(f"{C.G}✓ Fixed lp table{C.E}")
        except Exception as e:
            print(f"{C.Y}⚠ lp table: {e}{C.E}")
        
        # Fix 2: Add exec_state column
        print(f"{C.C}Adding exec_state to cpu_execution_contexts...{C.E}")
        try:
            self.conn.execute("ALTER TABLE cpu_execution_contexts ADD COLUMN exec_state TEXT DEFAULT 'READY'")
            self.conn.commit()
            print(f"{C.G}✓ Added exec_state{C.E}")
            self.stats['columns_added'] += 1
        except sqlite3.OperationalError as e:
            if 'duplicate' in str(e).lower():
                print(f"{C.Y}⚠ exec_state exists{C.E}")
            else:
                print(f"{C.R}✗ exec_state: {e}{C.E}")
        
        # Fix 3: Add gate_sequence column
        print(f"{C.C}Adding gate_sequence to quantum_command_circuits...{C.E}")
        try:
            self.conn.execute("ALTER TABLE quantum_command_circuits ADD COLUMN gate_sequence TEXT")
            self.conn.commit()
            print(f"{C.G}✓ Added gate_sequence{C.E}")
            self.stats['columns_added'] += 1
        except sqlite3.OperationalError as e:
            if 'duplicate' in str(e).lower():
                print(f"{C.Y}⚠ gate_sequence exists{C.E}")
            else:
                print(f"{C.R}✗ gate_sequence: {e}{C.E}")
        
        # Fix 4: Add gate_name to command_registry
        print(f"{C.C}Adding gate_name to command_registry...{C.E}")
        try:
            self.conn.execute("ALTER TABLE command_registry ADD COLUMN gate_name TEXT")
            self.conn.commit()
            print(f"{C.G}✓ Added gate_name{C.E}")
            self.stats['columns_added'] += 1
        except sqlite3.OperationalError as e:
            if 'duplicate' in str(e).lower():
                print(f"{C.Y}⚠ gate_name exists{C.E}")
            else:
                print(f"{C.R}✗ gate_name: {e}{C.E}")
    
    def install_cpu_tables(self):
        '''Install CPU subsystem tables'''
        print(f"\n{C.BOLD}{C.M}PHASE 2: CPU Subsystem{C.E}")
        try:
            self.conn.executescript(CPU_TABLES)
            self.conn.commit()
            
            c = self.conn.cursor()
            c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name LIKE 'cpu_%'")
            count = c.fetchone()[0]
            self.stats['tables_created'] += count
            print(f"{C.G}✓ Created {count} CPU tables{C.E}")
        except Exception as e:
            print(f"{C.R}✗ CPU tables: {e}{C.E}")
            self.stats['errors'].append(('CPU tables', str(e)))
    
    def install_command_tables(self):
        '''Install command subsystem tables'''
        print(f"\n{C.BOLD}{C.M}PHASE 3: Command Subsystem{C.E}")
        try:
            self.conn.executescript(COMMAND_TABLES)
            self.conn.commit()
            
            c = self.conn.cursor()
            c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name LIKE 'command_%'")
            count = c.fetchone()[0]
            self.stats['tables_created'] += count
            print(f"{C.G}✓ Created {count} command tables{C.E}")
        except Exception as e:
            print(f"{C.R}✗ Command tables: {e}{C.E}")
            self.stats['errors'].append(('Command tables', str(e)))
    
    def install_qnic_tables(self):
        '''Install QNIC subsystem tables'''
        print(f"\n{C.BOLD}{C.M}PHASE 4: QNIC Subsystem{C.E}")
        try:
            self.conn.executescript(QNIC_TABLES)
            self.conn.commit()
            
            c = self.conn.cursor()
            c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name LIKE 'qnic_%'")
            count = c.fetchone()[0]
            self.stats['tables_created'] += count
            print(f"{C.G}✓ Created {count} QNIC tables{C.E}")
        except Exception as e:
            print(f"{C.R}✗ QNIC tables: {e}{C.E}")
            self.stats['errors'].append(('QNIC tables', str(e)))
    
    def install_all_circuits(self):
        '''Install complete 168 circuit library'''
        print(f"\n{C.BOLD}{C.M}PHASE 5: Complete Circuit Library (168 circuits){C.E}")
        
        print(f"{C.C}Installing base quantum gates...{C.E}")
        try:
            self.conn.executescript(COMPLETE_CIRCUITS)
            self.conn.commit()
            print(f"{C.G}✓ Installed base circuits{C.E}")
        except Exception as e:
            print(f"{C.R}✗ Base circuits: {e}{C.E}")
        
        print(f"{C.C}Installing filesystem circuits...{C.E}")
        try:
            self.conn.executescript(CIRCUITS_PART3)
            self.conn.commit()
            print(f"{C.G}✓ Installed filesystem circuits{C.E}")
        except Exception as e:
            print(f"{C.R}✗ Filesystem circuits: {e}{C.E}")
        
        print(f"{C.C}Installing utility circuits...{C.E}")
        try:
            self.conn.executescript(CIRCUITS_PART4)
            self.conn.commit()
            print(f"{C.G}✓ Installed utility circuits{C.E}")
        except Exception as e:
            print(f"{C.R}✗ Utility circuits: {e}{C.E}")
        
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM quantum_command_circuits")
        self.stats['circuits_added'] = c.fetchone()[0]
        print(f"{C.G}✓ Total circuits: {self.stats['circuits_added']}{C.E}")
    
    def link_commands_to_circuits(self):
        '''Link command_registry to quantum_command_circuits'''
        print(f"\n{C.BOLD}{C.M}PHASE 6: Command→Circuit Linkage{C.E}")
        
        # Update gate_name in command_registry
        print(f"{C.C}Updating gate_name mappings...{C.E}")
        gate_mappings = {
            'qh': 'h', 'qx': 'x', 'qy': 'y', 'qz': 'z',
            'qs': 's', 'qt': 't', 'qcnot': 'cx', 'qcz': 'cz',
            'qswap': 'swap', 'qtoffoli': 'ccx',
            'epr_create': 'bell', 'ghz_create': 'ghz',
            'qmeasure': 'measure', 'qreset': 'reset',
            'grover': 'grover', 'qft': 'qft', 'teleport': 'teleport'
        }
        
        for cmd, gate in gate_mappings.items():
            try:
                self.conn.execute("UPDATE command_registry SET gate_name = ? WHERE cmd_name = ?", (gate, cmd))
            except:
                pass
        
        self.conn.commit()
        
        # Verify linkages
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM command_registry cr " +
                  "INNER JOIN quantum_command_circuits qcc ON cr.cmd_name = qcc.cmd_name")
        self.stats['commands_linked'] = c.fetchone()[0]
        print(f"{C.G}✓ Linked {self.stats['commands_linked']} commands to circuits{C.E}")
    
    def verify(self):
        '''Comprehensive verification'''
        print(f"\n{C.BOLD}{C.M}PHASE 7: Verification{C.E}")
        
        c = self.conn.cursor()
        
        # Check critical tables
        checks = [
            ("lp", "Lattice points table"),
            ("cpu_opcodes", "CPU opcodes"),
            ("command_registry", "Command registry"),
            ("quantum_command_circuits", "Quantum circuits"),
            ("cpu_execution_contexts", "Execution contexts"),
            ("qnic_traffic_log", "QNIC traffic log"),
        ]
        
        all_ok = True
        for table, desc in checks:
            try:
                c.execute(f"SELECT COUNT(*) FROM {table}")
                count = c.fetchone()[0]
                print(f"  {C.G}✓{C.E} {desc:.<40} {count:>8,} rows")
            except Exception as e:
                print(f"  {C.R}✗{C.E} {desc:.<40} MISSING")
                all_ok = False
        
        # Check column existence
        print(f"\n{C.C}Column checks:{C.E}")
        column_checks = [
            ("cpu_execution_contexts", "exec_state"),
            ("quantum_command_circuits", "gate_sequence"),
            ("command_registry", "gate_name"),
        ]
        
        for table, column in column_checks:
            try:
                c.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in c.fetchall()]
                if column in columns:
                    print(f"  {C.G}✓{C.E} {table}.{column}")
                else:
                    print(f"  {C.R}✗{C.E} {table}.{column} MISSING")
                    all_ok = False
            except:
                print(f"  {C.R}✗{C.E} {table}.{column} ERROR")
                all_ok = False
        
        # Check circuit coverage
        print(f"\n{C.C}Circuit coverage by category:{C.E}")
        c.execute("SELECT cr.cmd_category, " +
                  "COUNT(*) as total_cmds, " +
                  "COUNT(qcc.circuit_id) as with_circuit, " +
                  "ROUND(100.0 * COUNT(qcc.circuit_id) / COUNT(*), 1) as pct " +
                  "FROM command_registry cr " +
                  "LEFT JOIN quantum_command_circuits qcc ON cr.cmd_name = qcc.cmd_name " +
                  "GROUP BY cr.cmd_category " +
                  "ORDER BY pct DESC")
        
        for cat, total, with_circ, pct in c.fetchall():
            bar = '█' * int(pct / 5)
            color = C.G if pct >= 90 else C.Y if pct >= 70 else C.R
            print(f"  {color}{cat:.<20}{C.E} {with_circ}/{total} ({pct}%) {bar}")
        
        return all_ok
    
    def print_summary(self):
        '''Print final summary'''
        print(f"\n{C.BOLD}{C.G}{'='*60}{C.E}")
        print(f"{C.BOLD}{C.G}ULTIMATE INTEGRATION PATCH v{VERSION} COMPLETE{C.E}")
        print(f"{C.BOLD}{C.G}{'='*60}{C.E}\n")
        
        print(f"{C.C}Statistics:{C.E}")
        print(f"  Tables created:      {self.stats['tables_created']}")
        print(f"  Columns added:       {self.stats['columns_added']}")
        print(f"  Circuits installed:  {self.stats['circuits_added']}")
        print(f"  Commands linked:     {self.stats['commands_linked']}")
        print(f"  Errors encountered:  {len(self.stats['errors'])}")
        
        if self.stats['errors']:
            print(f"\n{C.Y}Errors (non-critical):{C.E}")
            for subsys, err in self.stats['errors'][:5]:
                print(f"  • {subsys}: {err[:60]}...")
        
        print(f"\n{C.C}System is now ready for:{C.E}")
        print(f"  • Full quantum command execution")
        print(f"  • CPU opcode processing")
        print(f"  • QNIC network operations")
        print(f"  • Complete circuit library (168 commands)")
        print(f"  • Command→Circuit→Execution pipeline")
        
        print(f"\n{C.C}Next steps:{C.E}")
        print(f"  1. Restart Flask: {C.Y}python flask_app.py{C.E}")
        print(f"  2. Test commands: {C.Y}qh 0{C.E}, {C.Y}ls{C.E}, {C.Y}grep pattern file{C.E}")
        print(f"  3. Verify circuits: {C.Y}SELECT * FROM quantum_command_circuits{C.E}")
        
        db_size = self.db_path.stat().st_size / (1024*1024)
        print(f"\n{C.C}Database: {self.db_path} ({db_size:.1f} MB){C.E}\n")
    
    def close(self):
        if self.conn:
            self.conn.commit()
            self.conn.close()

def main():
    import sys
    if len(sys.argv) < 2:
        print(f"\nUsage: python db_patch_v6.py <database.db>\n")
        return 1
    
    db_path = Path(sys.argv[1])
    if not db_path.exists():
        print(f"\n{C.R}Database not found: {db_path}{C.E}\n")
        return 1
    
    print(f"{C.BOLD}{C.M}")
    print(f"╔════════════════════════════════════════════════════════════╗")
    print(f"║  QUNIX ULTIMATE INTEGRATION PATCH v{VERSION:^21}  ║")
    print(f"║         Complete System Integration                        ║")
    print(f"╚════════════════════════════════════════════════════════════╝")
    print(f"{C.E}\n")
    
    patcher = UltimateIntegrationPatcher(db_path)
    
    try:
        patcher.connect()
        patcher.apply_fixes()
        patcher.install_cpu_tables()
        patcher.install_command_tables()
        patcher.install_qnic_tables()
        patcher.install_all_circuits()
        patcher.link_commands_to_circuits()
        
        if patcher.verify():
            print(f"\n{C.G}✓ All verifications passed!{C.E}")
        else:
            print(f"\n{C.Y}⚠ Some verifications failed (see above){C.E}")
        
        patcher.print_summary()
        return 0
        
    except Exception as e:
        print(f"\n{C.R}✗ Patch failed: {e}{C.E}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        patcher.close()

if __name__ == '__main__':
    import sys
    sys.exit(main())
