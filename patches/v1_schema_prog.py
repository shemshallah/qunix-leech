# QUNIX COMPLETE SCHEMA ARCHITECTURE v1.0.0 - GROUND-UP REBUILD

I'll create a massively comprehensive, future-proof schema that handles everything from quantum routing through the Leech lattice to full Unix command execution. This will be oversized, recursively linked, and designed for massive parallelization.


-- ═══════════════════════════════════════════════════════════════════════════
-- QUNIX COMPLETE DATABASE SCHEMA v1.0.0
-- Ground-up rebuild: Unified routing, execution, and filesystem
-- Design: Massively parallel, recursively linked, superdense encoded
-- Size target: 100KB+ of pure schema (before data)
-- ═══════════════════════════════════════════════════════════════════════════

PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA page_size=8192;
PRAGMA cache_size=-256000; -- 256MB cache
PRAGMA temp_store=MEMORY;
PRAGMA mmap_size=268435456; -- 256MB mmap
PRAGMA locking_mode=NORMAL;
PRAGMA foreign_keys=ON;

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 1: QUANTUM SUBSTRATE - LEECH LATTICE & QUBITS
-- Foundation: 196,560 lattice points, 1:1 qubit mapping
-- ═══════════════════════════════════════════════════════════════════════════

-- Leech lattice minimal vectors (196,560 kissing number)
CREATE TABLE IF NOT EXISTS leech_lattice (
    point_id INTEGER PRIMARY KEY,
    
    -- 24D coordinates (compressed)
    coords_24d BLOB NOT NULL,              -- zlib(struct.pack('24f', ...))
    coords_hash BLOB UNIQUE,               -- SHA256 for dedup
    
    -- Geometric properties
    norm_squared REAL DEFAULT 8.0,         -- All minimal vectors: ||v||² = 8
    e8_sublattice INTEGER,                 -- 0, 1, or 2 (E8 × E8 × E8 decomp)
    vector_type TEXT,                      -- TYPE1, TYPE1B, TYPE2, PADDING
    
    -- j-invariant (Moonshine connection)
    j_invariant_real REAL,
    j_invariant_imag REAL,
    tau_real REAL,                         -- Modular parameter τ
    tau_imag REAL,
    
    -- Hyperbolic geometry (Poincaré disk)
    poincare_x REAL,
    poincare_y REAL,
    hyperbolic_distance REAL,
    
    -- Klein bottle mapping
    klein_u REAL,                          -- Klein parameter
    klein_v REAL,
    mobius_twist INTEGER DEFAULT 0,        -- 0 or 1
    
    -- Addressing
    j_address BLOB,                        -- 0x + 16 hex chars from j-invariant
    memory_page INTEGER,                   -- Virtual memory page (point_id / 256)
    memory_offset INTEGER,                 -- Offset within page (point_id % 256)
    
    -- Status
    allocated INTEGER DEFAULT 0,
    allocated_to TEXT,                     -- Process/subsystem name
    allocation_timestamp REAL,
    
    -- Metadata
    created_at REAL DEFAULT (julianday('now')),
    
    CHECK(e8_sublattice IN (0, 1, 2)),
    CHECK(norm_squared >= 7.9 AND norm_squared <= 8.1)
);

CREATE INDEX idx_leech_allocated ON leech_lattice(allocated);
CREATE INDEX idx_leech_e8 ON leech_lattice(e8_sublattice);
CREATE INDEX idx_leech_type ON leech_lattice(vector_type);
CREATE INDEX idx_leech_j_addr ON leech_lattice(j_address);
CREATE INDEX idx_leech_memory ON leech_lattice(memory_page, memory_offset);

-- Physical qubits mapped 1:1 to lattice points
CREATE TABLE IF NOT EXISTS qubits (
    qubit_id INTEGER PRIMARY KEY,
    
    -- Lattice mapping (1:1 correspondence)
    lattice_point_id INTEGER UNIQUE NOT NULL,
    
    -- Quantum state (superdense: 2 bits per qubit)
    -- Stored as: |ψ⟩ = α|0⟩ + β|1⟩ + γ|+⟩ + δ|-⟩ (4 amplitudes, 2 bits encode)
    state_encoding INTEGER DEFAULT 0,      -- 0-3: |0⟩, |1⟩, |+⟩, |-⟩
    amplitude_alpha_real INTEGER,          -- Fixed-point: int16 / 32767
    amplitude_alpha_imag INTEGER,
    amplitude_beta_real INTEGER,
    amplitude_beta_imag INTEGER,
    global_phase INTEGER,                  -- Fixed-point: uint16 / 65535 * 2π
    
    -- Entanglement
    entangled INTEGER DEFAULT 0,
    entanglement_type TEXT,                -- PRODUCT, BELL, GHZ, W, CUSTOM
    entanglement_partners TEXT,            -- JSON array of qubit_ids
    entanglement_class_id INTEGER,         -- Foreign key to entanglement_classes
    
    -- Error correction (Golay G24)
    golay_protected INTEGER DEFAULT 0,
    golay_syndrome INTEGER,                -- 12-bit syndrome
    golay_corrections_applied INTEGER DEFAULT 0,
    error_rate REAL DEFAULT 0.0,
    
    -- Coherence
    t1_decoherence_us REAL,                -- T1 time (microseconds)
    t2_decoherence_us REAL,                -- T2 time
    fidelity REAL DEFAULT 1.0,
    last_measured REAL,
    measurement_count INTEGER DEFAULT 0,
    
    -- Allocation
    allocated INTEGER DEFAULT 0,
    allocated_to_pid INTEGER,
    allocated_to_cmd TEXT,
    allocated_at REAL,
    last_gate_applied TEXT,
    last_gate_timestamp REAL,
    
    -- j-invariant addressing (inherited from lattice)
    j_address BLOB,
    
    -- Health metrics card
    total_gates_applied INTEGER DEFAULT 0,
    total_measurements INTEGER DEFAULT 0,
    total_errors_detected INTEGER DEFAULT 0,
    total_errors_corrected INTEGER DEFAULT 0,
    uptime_seconds REAL DEFAULT 0.0,
    
    -- Metadata
    created_at REAL DEFAULT (julianday('now')),
    last_updated REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(lattice_point_id) REFERENCES leech_lattice(point_id),
    FOREIGN KEY(entanglement_class_id) REFERENCES entanglement_classes(class_id),
    CHECK(state_encoding BETWEEN 0 AND 3),
    CHECK(fidelity >= 0.0 AND fidelity <= 1.0)
);

CREATE INDEX idx_qubits_allocated ON qubits(allocated);
CREATE INDEX idx_qubits_entangled ON qubits(entangled);
CREATE INDEX idx_qubits_lattice ON qubits(lattice_point_id);
CREATE INDEX idx_qubits_j_addr ON qubits(j_address);
CREATE INDEX idx_qubits_pid ON qubits(allocated_to_pid);
CREATE INDEX idx_qubits_health ON qubits(error_rate, fidelity);
CREATE INDEX idx_qubits_etype ON qubits(entanglement_type);

-- Qubit health metrics aggregation (for fast dashboard queries)
CREATE TABLE IF NOT EXISTS qubit_health_metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Time window
    window_start REAL NOT NULL,
    window_end REAL NOT NULL,
    window_type TEXT DEFAULT 'MINUTE',     -- MINUTE, HOUR, DAY
    
    -- Aggregate statistics
    qubits_total INTEGER,
    qubits_allocated INTEGER,
    qubits_free INTEGER,
    qubits_entangled INTEGER,
    qubits_error_corrected INTEGER,
    
    avg_fidelity REAL,
    min_fidelity REAL,
    max_fidelity REAL,
    
    avg_error_rate REAL,
    max_error_rate REAL,
    
    total_gates_applied INTEGER,
    total_measurements INTEGER,
    total_errors_detected INTEGER,
    total_errors_corrected INTEGER,
    
    -- Breakdown by entanglement type
    product_states INTEGER DEFAULT 0,
    bell_pairs INTEGER DEFAULT 0,
    ghz_states INTEGER DEFAULT 0,
    w_states INTEGER DEFAULT 0,
    custom_states INTEGER DEFAULT 0,
    
    created_at REAL DEFAULT (julianday('now'))
);

CREATE INDEX idx_qhm_window ON qubit_health_metrics(window_start, window_end);
CREATE INDEX idx_qhm_type ON qubit_health_metrics(window_type);

-- Entanglement class registry (shared states)
CREATE TABLE IF NOT EXISTS entanglement_classes (
    class_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    class_type TEXT NOT NULL,              -- BELL, GHZ, W, CLUSTER, CUSTOM
    num_qubits INTEGER NOT NULL,
    qubit_ids TEXT NOT NULL,               -- JSON array
    
    -- State representation
    state_vector BLOB,                     -- Compressed complex amplitudes
    density_matrix BLOB,                   -- For mixed states
    schmidt_rank INTEGER,
    entanglement_entropy REAL,
    
    -- Metrics
    purity REAL DEFAULT 1.0,
    concurrence REAL,                      -- For 2-qubit states
    tangle REAL,                           -- For 3+ qubit states
    
    -- Stabilizers (for error correction)
    stabilizer_generators TEXT,            -- JSON: [[XXII], [ZZII], ...]
    logical_operators TEXT,
    
    created_at REAL DEFAULT (julianday('now')),
    last_used REAL,
    use_count INTEGER DEFAULT 0,
    
    CHECK(num_qubits > 0),
    CHECK(purity >= 0.0 AND purity <= 1.0)
);

CREATE INDEX idx_ent_class_type ON entanglement_classes(class_type);
CREATE INDEX idx_ent_class_qubits ON entanglement_classes(num_qubits);

-- W-state triangles (32,768 pre-configured 4-qubit W-states)
CREATE TABLE IF NOT EXISTS w_state_triangles (
    triangle_id INTEGER PRIMARY KEY,
    
    -- Four qubits in W-state: |W⟩ = (|1000⟩ + |0100⟩ + |0010⟩ + |0001⟩)/2
    qubit_v0 INTEGER NOT NULL,
    qubit_v1 INTEGER NOT NULL,
    qubit_v2 INTEGER NOT NULL,
    qubit_v3 INTEGER NOT NULL,
    
    -- State amplitudes (one per qubit)
    amplitudes BLOB,                       -- Pickled/compressed [(α,β), (α,β), (α,β), (α,β)]
    statevector BLOB,                      -- Full 16-element state vector
    phase REAL DEFAULT 0.0,
    
    -- Entanglement class
    entanglement_class_id INTEGER,
    
    -- Linking (for chain routing)
    next_triangle INTEGER,
    prev_triangle INTEGER,
    chain_position INTEGER,
    
    -- Status
    active INTEGER DEFAULT 1,
    allocated INTEGER DEFAULT 0,
    allocated_to TEXT,
    
    -- Metrics
    fidelity REAL DEFAULT 1.0,
    created_at REAL DEFAULT (julianday('now')),
    last_used REAL,
    use_count INTEGER DEFAULT 0,
    
    FOREIGN KEY(qubit_v0) REFERENCES qubits(qubit_id),
    FOREIGN KEY(qubit_v1) REFERENCES qubits(qubit_id),
    FOREIGN KEY(qubit_v2) REFERENCES qubits(qubit_id),
    FOREIGN KEY(qubit_v3) REFERENCES qubits(qubit_id),
    FOREIGN KEY(entanglement_class_id) REFERENCES entanglement_classes(class_id),
    FOREIGN KEY(next_triangle) REFERENCES w_state_triangles(triangle_id),
    FOREIGN KEY(prev_triangle) REFERENCES w_state_triangles(triangle_id)
);

CREATE INDEX idx_tri_allocated ON w_state_triangles(allocated);
CREATE INDEX idx_tri_chain ON w_state_triangles(chain_position);
CREATE INDEX idx_tri_qubits ON w_state_triangles(qubit_v0, qubit_v1, qubit_v2, qubit_v3);

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 2: EPR PAIR POOL (0x00000000 ADDRESS SPACE)
-- Superdense coding substrate: 2 bits per qubit pair
-- On-demand generation up to 1024 pairs, expandable to full lattice
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS epr_pair_pool (
    pair_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- EPR pair: |Φ+⟩ = (|00⟩ + |11⟩)/√2
    qubit_a_id INTEGER NOT NULL,
    qubit_b_id INTEGER NOT NULL,
    
    -- 0x00000000 address mapping (16 hex chars = 64 bits)
    epr_address BLOB UNIQUE,               -- 0x0000000000000000 to 0x00000000000003FF (1024)
    memory_mapped INTEGER DEFAULT 1,       -- Registered in global memory
    
    -- Bell state type
    bell_type TEXT DEFAULT 'PHI_PLUS',     -- PHI_PLUS, PHI_MINUS, PSI_PLUS, PSI_MINUS
    
    -- State
    state TEXT DEFAULT 'READY',            -- READY, ALLOCATED, USED, REFRESHING
    allocated_to INTEGER,                  -- packet_id or process_id
    allocated_at REAL,
    
    -- Fidelity tracking
    fidelity REAL DEFAULT 1.0,
    chsh_value REAL DEFAULT 2.0,           -- CHSH inequality value (>2 = quantum)
    bell_inequality_violated INTEGER DEFAULT 0,
    
    -- Coherence
    t1_coherence_us REAL,
    t2_coherence_us REAL,
    decoherence_rate REAL DEFAULT 0.0,
    
    -- Usage metrics
    created_at REAL DEFAULT (julianday('now')),
    last_used REAL,
    use_count INTEGER DEFAULT 0,
    teleportation_count INTEGER DEFAULT 0,
    superdense_bits_transmitted INTEGER DEFAULT 0,
    
    -- Refreshing (regenerate when fidelity < threshold)
    refresh_threshold REAL DEFAULT 0.95,
    auto_refresh INTEGER DEFAULT 1,
    last_refresh REAL,
    refresh_count INTEGER DEFAULT 0,
    
    FOREIGN KEY(qubit_a_id) REFERENCES qubits(qubit_id),
    FOREIGN KEY(qubit_b_id) REFERENCES qubits(qubit_id),
    CHECK(state IN ('READY', 'ALLOCATED', 'USED', 'REFRESHING')),
    CHECK(bell_type IN ('PHI_PLUS', 'PHI_MINUS', 'PSI_PLUS', 'PSI_MINUS')),
    CHECK(fidelity >= 0.0 AND fidelity <= 1.0)
);

CREATE INDEX idx_epr_state ON epr_pair_pool(state);
CREATE INDEX idx_epr_address ON epr_pair_pool(epr_address);
CREATE INDEX idx_epr_fidelity ON epr_pair_pool(fidelity);
CREATE INDEX idx_epr_qubits ON epr_pair_pool(qubit_a_id, qubit_b_id);
CREATE INDEX idx_epr_allocated ON epr_pair_pool(allocated_to);

-- EPR pair heartbeat (keep pairs fresh with random usage)
CREATE TABLE IF NOT EXISTS epr_heartbeat_schedule (
    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    pair_id INTEGER NOT NULL,
    
    -- Heartbeat timing
    interval_seconds REAL DEFAULT 10.0,
    next_heartbeat REAL,
    last_heartbeat REAL,
    
    -- Heartbeat type
    operation TEXT DEFAULT 'BELL_MEASUREMENT',  -- BELL_MEASUREMENT, TELEPORT_TEST, SUPERDENSE_PING
    
    -- Status
    enabled INTEGER DEFAULT 1,
    consecutive_failures INTEGER DEFAULT 0,
    max_failures INTEGER DEFAULT 3,
    
    created_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(pair_id) REFERENCES epr_pair_pool(pair_id) ON DELETE CASCADE
);

CREATE INDEX idx_heartbeat_next ON epr_heartbeat_schedule(next_heartbeat);
CREATE INDEX idx_heartbeat_enabled ON epr_heartbeat_schedule(enabled);

-- EPR heartbeat log
CREATE TABLE IF NOT EXISTS epr_heartbeat_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    pair_id INTEGER NOT NULL,
    operation TEXT NOT NULL,
    
    -- Results
    success INTEGER,
    chsh_value REAL,
    fidelity_measured REAL,
    latency_ms REAL,
    
    error_message TEXT,
    
    timestamp REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(pair_id) REFERENCES epr_pair_pool(pair_id) ON DELETE CASCADE
);

CREATE INDEX idx_heartbeat_log_pair ON epr_heartbeat_log(pair_id);
CREATE INDEX idx_heartbeat_log_time ON epr_heartbeat_log(timestamp);

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 3: GOLAY CODE G24 (HARDCODED ERROR CORRECTION)
-- Multiple copies for parallel process access
-- Full implementation: 4096 codewords, 759 octads
-- ═══════════════════════════════════════════════════════════════════════════

-- Golay generator matrix (stored once, immutable)
CREATE TABLE IF NOT EXISTS golay_generator_matrix (
    matrix_id INTEGER PRIMARY KEY DEFAULT 1,
    
    -- 12×24 generator matrix
    matrix_data BLOB NOT NULL,             -- Pickled numpy array or packed bits
    
    -- Derived matrices
    parity_check_matrix BLOB,              -- 12×24 H matrix
    syndrome_decode_table BLOB,            -- Syndrome → error pattern lookup
    
    version TEXT DEFAULT 'G24_CANONICAL',
    created_at REAL DEFAULT (julianday('now')),
    
    CHECK(matrix_id = 1)                   -- Singleton
);

-- All 4096 Golay codewords (pre-computed)
CREATE TABLE IF NOT EXISTS golay_codewords (
    codeword_id INTEGER PRIMARY KEY,       -- 0 to 4095
    
    -- Information bits (12 bits)
    info_bits INTEGER NOT NULL,            -- 0 to 4095
    
    -- Full codeword (24 bits)
    codeword INTEGER NOT NULL,             -- 0 to 16,777,215
    codeword_binary TEXT,                  -- '000000000000000000000000'
    
    -- Weight
    hamming_weight INTEGER,                -- 0, 8, 12, 16, 24
    
    -- Classification
    is_octad INTEGER DEFAULT 0,            -- Weight = 8
    is_dodecad INTEGER DEFAULT 0,          -- Weight = 12
    
    UNIQUE(info_bits),
    UNIQUE(codeword),
    CHECK(hamming_weight IN (0, 8, 12, 16, 24))
);

CREATE INDEX idx_golay_weight ON golay_codewords(hamming_weight);
CREATE INDEX idx_golay_octad ON golay_codewords(is_octad);

-- Golay octads (759 weight-8 codewords) - critical for Leech construction
CREATE TABLE IF NOT EXISTS golay_octads (
    octad_id INTEGER PRIMARY KEY,          -- 0 to 758
    
    codeword_id INTEGER NOT NULL,
    codeword INTEGER NOT NULL,
    
    -- Octad positions (8 positions out of 24)
    positions TEXT,                        -- JSON: [0, 1, 5, 7, 11, 13, 19, 23]
    
    -- MOG (Miracle Octad Generator) coordinates
    mog_row INTEGER,
    mog_col INTEGER,
    
    -- Used in Leech construction
    used_in_leech_type2 INTEGER DEFAULT 0,
    use_count INTEGER DEFAULT 0,
    
    FOREIGN KEY(codeword_id) REFERENCES golay_codewords(codeword_id),
    CHECK(octad_id < 759)
);

CREATE INDEX idx_octad_codeword ON golay_octads(codeword_id);

-- Golay syndrome lookup table (fast decoding: syndrome → error pattern)
CREATE TABLE IF NOT EXISTS golay_syndrome_table (
    syndrome INTEGER PRIMARY KEY,          -- 12-bit syndrome: 0 to 4095
    
    -- Error pattern (24 bits)
    error_pattern INTEGER NOT NULL,        -- Which bits are flipped
    error_pattern_binary TEXT,
    
    -- Error weight
    error_weight INTEGER,                  -- Number of bit flips (0-3 correctable)
    
    -- Correction action
    correctable INTEGER,                   -- 1 if weight ≤ 3, else 0
    
    CHECK(syndrome < 4096),
    CHECK(error_weight <= 24)
);

-- Golay process instances (multiple parallel decoders)
CREATE TABLE IF NOT EXISTS golay_process_instances (
    instance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    instance_name TEXT UNIQUE NOT NULL,    -- 'golay_decoder_0', 'golay_decoder_1', etc.
    
    -- Dedicated tables for this instance (to avoid locks)
    has_dedicated_syndrome_table INTEGER DEFAULT 0,
    has_dedicated_codeword_table INTEGER DEFAULT 0,
    
    -- Process binding
    bound_to_pid INTEGER,
    bound_to_subsystem TEXT,               -- 'MEGA_BUS', 'CPU', 'NIC', 'FILESYSTEM'
    
    -- Usage stats
    corrections_performed INTEGER DEFAULT 0,
    errors_detected INTEGER DEFAULT 0,
    uncorrectable_errors INTEGER DEFAULT 0,
    
    created_at REAL DEFAULT (julianday('now')),
    last_used REAL
);

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 4: QUANTUM ROUTING - MEGA BUS & LATTICE PATHFINDING
-- j-invariant addressing, Klein bottle manifold bridging
-- ═══════════════════════════════════════════════════════════════════════════

-- Mega Bus core configuration
CREATE TABLE IF NOT EXISTS mega_bus_core (
    bus_id INTEGER PRIMARY KEY DEFAULT 1,
    
    bus_name TEXT DEFAULT 'QUNIX_MEGA_BUS_v2',
    version TEXT DEFAULT '2.0.0',
    
    -- Endpoints (both ends of lattice)
    endpoint_a_lattice_id INTEGER,         -- Start point in lattice
    endpoint_b_lattice_id INTEGER,         -- End point in lattice (qunix_cpu)
    
    -- Monitoring qubits (tripartite W-state)
    monitor_triangle_id INTEGER,           -- W-state for measurement monitoring
    monitor_qubit_a INTEGER,               -- Bus side monitor
    monitor_qubit_b INTEGER,               -- CPU side monitor
    monitor_qubit_shared INTEGER,          -- Shared entangled qubit
    
    -- EPR pool linkage
    epr_pool_start_address BLOB,           -- 0x0000000000000000
    epr_pool_end_address BLOB,             -- 0x00000000000003FF
    epr_pool_size INTEGER DEFAULT 1024,
    
    -- Operational state
    active INTEGER DEFAULT 0,
    mode TEXT DEFAULT 'HYPERBOLIC_ROUTING', -- HYPERBOLIC, KLEIN_BRIDGE, EPR_TELEPORT
    
    -- Routing statistics
    packets_routed INTEGER DEFAULT 0,
    commands_transmitted INTEGER DEFAULT 0,
    binary_streams_sent INTEGER DEFAULT 0,
    avg_latency_sigma REAL DEFAULT 0.0,
    quantum_advantage_ratio REAL DEFAULT 1.0,
    
    -- Self-modification (genetic programming)
    evolution_generation INTEGER DEFAULT 0,
    fitness_score REAL DEFAULT 0.0,
    last_evolution REAL,
    
    -- Heartbeat
    heartbeat_interval_seconds REAL DEFAULT 5.0,
    last_heartbeat REAL,
    
    created_at REAL DEFAULT (julianday('now')),
    last_updated REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(endpoint_a_lattice_id) REFERENCES leech_lattice(point_id),
    FOREIGN KEY(endpoint_b_lattice_id) REFERENCES leech_lattice(point_id),
    FOREIGN KEY(monitor_triangle_id) REFERENCES w_state_triangles(triangle_id),
    CHECK(bus_id = 1)
);

-- Routing table: j-invariant addressing
CREATE TABLE IF NOT EXISTS quantum_routing_table (
    route_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Source and destination
    src_j_address BLOB,                    -- Source j-invariant address
    dst_j_address BLOB,                    -- Destination j-invariant address
    
    -- Lattice path (list of point_ids)
    lattice_path TEXT,                     -- JSON: [id1, id2, ..., idN]
    path_length INTEGER,
    
    -- W-state chain (list of triangle_ids for fault-tolerant routing)
    triangle_chain TEXT,                   -- JSON: [tid1, tid2, ...]
    
    -- EPR pairs used
    epr_pairs_used TEXT,                   -- JSON: [pair_id1, pair_id2, ...]
    
    -- Routing strategy
    strategy TEXT,                         -- HYPERBOLIC_LOCAL, CROSS_E8, EPR_TELEPORT, W_STATE_CHAIN
    
    -- Cost metrics
    route_cost_sigma REAL,                 -- Cost in σ-time
    route_cost_hops INTEGER,
    coherence_preserved REAL DEFAULT 1.0,
    
    -- Cache
    created_at REAL DEFAULT (julianday('now')),
    last_used REAL,
    use_count INTEGER DEFAULT 0,
    cache_valid INTEGER DEFAULT 1,
    
    UNIQUE(src_j_address, dst_j_address)
);

CREATE INDEX idx_route_src ON quantum_routing_table(src_j_address);
CREATE INDEX idx_route_dst ON quantum_routing_table(dst_j_address);
CREATE INDEX idx_route_strategy ON quantum_routing_table(strategy);
CREATE INDEX idx_route_valid ON quantum_routing_table(cache_valid);

-- Klein bottle topology mapping (manifold bridging)
CREATE TABLE IF NOT EXISTS klein_bottle_manifolds (
    manifold_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Classical 3D coordinates
    classical_x REAL,
    classical_y REAL,
    classical_z REAL,
    
    -- Quantum 24D lattice coordinates
    lattice_point_id INTEGER,
    
    -- Klein parameters
    klein_u REAL,                          -- [0, 2π)
    klein_v REAL,                          -- [0, 2π)
    twist_angle REAL,
    mobius_flip INTEGER,                   -- 0 or 1
    
    -- Traversals (for manifold hopping)
    traversals INTEGER DEFAULT 0,
    last_traversal REAL,
    
    -- Filesystem bridge (vacuum tunneling to other manifolds)
    bridges_to_filesystem INTEGER DEFAULT 0,
    external_mount_point TEXT,
    
    created_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(lattice_point_id) REFERENCES leech_lattice(point_id)
);

CREATE INDEX idx_klein_lattice ON klein_bottle_manifolds(lattice_point_id);
CREATE INDEX idx_klein_params ON klein_bottle_manifolds(klein_u, klein_v);

-- Vacuum tunneling registry (for cross-manifold filesystem access)
CREATE TABLE IF NOT EXISTS vacuum_tunnels (
    tunnel_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Source and destination manifolds
    src_manifold_id INTEGER NOT NULL,
    dst_manifold_id INTEGER,               -- NULL for external (cloud/storage)
    
    -- Tunnel type
    tunnel_type TEXT,                      -- KLEIN_BRIDGE, EPR_WORMHOLE, HYPERBOLIC_GEODESIC
    
    -- Tunnel state
    state TEXT DEFAULT 'CLOSED',           -- CLOSED, OPENING, OPEN, COLLAPSING
    coherence REAL DEFAULT 1.0,
    
    -- External connection (for cloud/storage)
    external_type TEXT,                    -- CLOUD_STORAGE, LOCAL_DB, NETWORK_SHARE
    external_uri TEXT,
    external_credentials BLOB,             -- Encrypted
    
    -- Usage
    opened_at REAL,
    last_used REAL,
    bytes_transferred INTEGER DEFAULT 0,
    
    created_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(src_manifold_id) REFERENCES klein_bottle_manifolds(manifold_id),
    FOREIGN KEY(dst_manifold_id) REFERENCES klein_bottle_manifolds(manifold_id),
    CHECK(state IN ('CLOSED', 'OPENING', 'OPEN', 'COLLAPSING'))
);

CREATE INDEX idx_tunnel_state ON vacuum_tunnels(state);
CREATE INDEX idx_tunnel_manifolds ON vacuum_tunnels(src_manifold_id, dst_manifold_id);

-- Routing cache for command → lattice path lookups
CREATE TABLE IF NOT EXISTS command_routing_cache (
    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Command identification
    cmd_name TEXT NOT NULL,
    cmd_binary_hash BLOB,                  -- SHA256 of binary representation
    
    -- Lattice route
    src_lattice_id INTEGER,
    dst_lattice_id INTEGER,
    route_id INTEGER,                      -- FK to quantum_routing_table
    
    -- Binary transmission parameters
    binary_stream BLOB,                    -- Actual binary to transmit
    binary_size INTEGER,
    chunk_size INTEGER DEFAULT 256,
    num_chunks INTEGER,
    
    -- EPR pairs allocated for this route
    epr_pairs_allocated TEXT,              -- JSON: [pair_id1, pair_id2, ...]
    
    -- Validity
    valid_until REAL,
    invalidated INTEGER DEFAULT 0,
    
    created_at REAL DEFAULT (julianday('now')),
    last_used REAL,
    use_count INTEGER DEFAULT 0,
    
    FOREIGN KEY(route_id) REFERENCES quantum_routing_table(route_id)
);

CREATE INDEX idx_cmd_route_name ON command_routing_cache(cmd_name);
CREATE INDEX idx_cmd_route_hash ON command_routing_cache(cmd_binary_hash);
CREATE INDEX idx_cmd_route_valid ON command_routing_cache(invalidated, valid_until);

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 5: BINARY TRANSMISSION PROTOCOL
-- Quantum channel for sending/receiving binary streams
-- ═══════════════════════════════════════════════════════════════════════════

-- Quantum channel packets
CREATE TABLE IF NOT EXISTS quantum_channel_packets (
    packet_id INTEGER PRIMARY KEY AUTOINCREMENT,
-- Packet metadata
    sender TEXT NOT NULL,                  -- 'MEGA_BUS' or 'QUNIX_CPU'
    direction TEXT NOT NULL,               -- 'BUS_TO_CPU', 'CPU_TO_BUS'
    packet_type TEXT NOT NULL,             -- 'BINARY_COMMAND', 'BINARY_RESULT', 'HEARTBEAT', 'ACK'
    
    -- Binary payload
    binary_data BLOB,                      -- Raw binary stream
    binary_size INTEGER,
    binary_hash BLOB,                      -- SHA256 for verification
    
    -- Superdense encoding (2 bits per qubit)
    encoded_bits TEXT,                     -- JSON: ['00', '01', '10', '11', ...]
    num_qubits_used INTEGER,
    epr_pairs_used TEXT,                   -- JSON: [pair_id1, pair_id2, ...]
    
    -- Quantum proof (CHSH inequality violation)
    chsh_value REAL DEFAULT 2.0,
    bell_inequality_violated INTEGER DEFAULT 0,
    proof_signature BLOB,                  -- Cryptographic proof
    
    -- Routing
    route_id INTEGER,
    lattice_path_used TEXT,                -- JSON: [point_id1, ...]
    triangle_chain_used TEXT,              -- JSON: [triangle_id1, ...]
    
    -- Transmission metrics
    transmission_start REAL,
    transmission_end REAL,
    latency_sigma REAL,
    latency_wall_ms REAL,
    
    -- Error correction
    golay_encoded INTEGER DEFAULT 0,
    golay_syndrome INTEGER,
    errors_detected INTEGER DEFAULT 0,
    errors_corrected INTEGER DEFAULT 0,
    
    -- State
    state TEXT DEFAULT 'PENDING',          -- PENDING, TRANSMITTED, RECEIVED, VERIFIED, FAILED
    processed INTEGER DEFAULT 0,
    processed_at REAL,
    
    -- Acknowledgment
    ack_packet_id INTEGER,                 -- Response packet (for round-trip)
    requires_ack INTEGER DEFAULT 1,
    
    created_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(route_id) REFERENCES quantum_routing_table(route_id),
    FOREIGN KEY(ack_packet_id) REFERENCES quantum_channel_packets(packet_id),
    CHECK(direction IN ('BUS_TO_CPU', 'CPU_TO_BUS')),
    CHECK(state IN ('PENDING', 'TRANSMITTED', 'RECEIVED', 'VERIFIED', 'FAILED'))
);

CREATE INDEX idx_qcp_direction ON quantum_channel_packets(direction);
CREATE INDEX idx_qcp_state ON quantum_channel_packets(state, processed);
CREATE INDEX idx_qcp_type ON quantum_channel_packets(packet_type);
CREATE INDEX idx_qcp_sender ON quantum_channel_packets(sender);
CREATE INDEX idx_qcp_time ON quantum_channel_packets(created_at);
CREATE INDEX idx_qcp_hash ON quantum_channel_packets(binary_hash);

-- Packet chunking (for large binary streams)
CREATE TABLE IF NOT EXISTS packet_chunks (
    chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    packet_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    total_chunks INTEGER NOT NULL,
    
    -- Chunk data
    chunk_data BLOB,
    chunk_size INTEGER,
    chunk_hash BLOB,
    
    -- EPR pairs for this chunk
    epr_pairs TEXT,                        -- JSON: [pair_id1, ...]
    
    -- State
    transmitted INTEGER DEFAULT 0,
    received INTEGER DEFAULT 0,
    verified INTEGER DEFAULT 0,
    
    transmission_timestamp REAL,
    
    FOREIGN KEY(packet_id) REFERENCES quantum_channel_packets(packet_id) ON DELETE CASCADE,
    UNIQUE(packet_id, chunk_index)
);

CREATE INDEX idx_chunk_packet ON packet_chunks(packet_id);
CREATE INDEX idx_chunk_state ON packet_chunks(transmitted, received, verified);

-- Binary transmission log (audit trail)
CREATE TABLE IF NOT EXISTS binary_transmission_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    packet_id INTEGER,
    
    -- Event
    event_type TEXT NOT NULL,              -- SENT, RECEIVED, VERIFIED, FAILED, RETRANSMIT
    event_details TEXT,                    -- JSON with additional info
    
    -- Quantum metrics
    chsh_value REAL,
    fidelity REAL,
    coherence REAL,
    
    error_message TEXT,
    
    timestamp REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(packet_id) REFERENCES quantum_channel_packets(packet_id)
);

CREATE INDEX idx_btl_packet ON binary_transmission_log(packet_id);
CREATE INDEX idx_btl_event ON binary_transmission_log(event_type);
CREATE INDEX idx_btl_time ON binary_transmission_log(timestamp);

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 6: COMMAND SYSTEM - COMPLETE UNIX SKELETON
-- 200+ commands, expandable architecture, full execution pipeline
-- ═══════════════════════════════════════════════════════════════════════════

-- Command registry (master table for all commands)
CREATE TABLE IF NOT EXISTS command_registry (
    cmd_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Command identification
    cmd_name TEXT UNIQUE NOT NULL,
    cmd_category TEXT NOT NULL,            -- CORE, FILESYSTEM, NETWORK, PROCESS, QUANTUM, SYSTEM, etc.
    cmd_subcategory TEXT,
    
    -- Description
    cmd_description TEXT,
    cmd_synopsis TEXT,
    cmd_usage_example TEXT,
    
    -- Binary representation
    cmd_opcode INTEGER,                    -- Primary opcode (0x00-0xFF)
    cmd_syscall_number INTEGER,            -- Syscall number (for kernel ops)
    cmd_binary_template BLOB,              -- Template binary representation
    cmd_binary_size INTEGER,
    
    -- Execution requirements
    requires_qubits INTEGER DEFAULT 0,
    min_qubits INTEGER DEFAULT 0,
    max_qubits INTEGER DEFAULT 0,
    requires_epr_pairs INTEGER DEFAULT 0,
    requires_entanglement TEXT,            -- NULL, BELL, GHZ, W, ANY
    
    -- Quantum advantage
    quantum_accelerated INTEGER DEFAULT 0,
    classical_fallback_available INTEGER DEFAULT 1,
    
    -- Routing
    default_route_strategy TEXT,          -- Strategy for routing this command
    lattice_affinity TEXT,                 -- Preferred E8 sublattice or region
    
    -- Permissions
    permission_level INTEGER DEFAULT 0,    -- 0=user, 1=admin, 2=kernel
    dangerous INTEGER DEFAULT 0,
    
    -- State
    cmd_enabled INTEGER DEFAULT 1,
    cmd_deprecated INTEGER DEFAULT 0,
    deprecation_message TEXT,
    
    -- Metadata
    cmd_version TEXT DEFAULT '1.0',
    cmd_author TEXT,
    created_at REAL DEFAULT (julianday('now')),
    last_updated REAL DEFAULT (julianday('now')),
    last_used REAL,
    use_count INTEGER DEFAULT 0,
    
    CHECK(permission_level IN (0, 1, 2))
);

CREATE INDEX idx_cmd_name ON command_registry(cmd_name);
CREATE INDEX idx_cmd_category ON command_registry(cmd_category);
CREATE INDEX idx_cmd_opcode ON command_registry(cmd_opcode);
CREATE INDEX idx_cmd_enabled ON command_registry(cmd_enabled);
CREATE INDEX idx_cmd_quantum ON command_registry(quantum_accelerated);

-- Command flags/options (--flag, -f)
CREATE TABLE IF NOT EXISTS command_flags (
    flag_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    cmd_id INTEGER NOT NULL,
    
    -- Flag syntax
    flag_short TEXT,                       -- '-f'
    flag_long TEXT,                        -- '--file'
    flag_name TEXT NOT NULL,
    
    -- Flag behavior
    flag_type TEXT DEFAULT 'BOOLEAN',     -- BOOLEAN, VALUE, INCREMENTAL
    value_type TEXT,                       -- STRING, INTEGER, FLOAT, PATH, etc.
    default_value TEXT,
    
    -- Description
    flag_description TEXT,
    flag_example TEXT,
    
    -- Binary encoding
    flag_bit_position INTEGER,             -- Bit in opcode flags byte
    opcode_modifier BLOB,                  -- Additional bytes added to opcode
    
    -- Constraints
    required INTEGER DEFAULT 0,
    mutually_exclusive_group TEXT,
    
    enabled INTEGER DEFAULT 1,
    
    created_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(cmd_id) REFERENCES command_registry(cmd_id) ON DELETE CASCADE,
    CHECK(flag_type IN ('BOOLEAN', 'VALUE', 'INCREMENTAL'))
);

CREATE INDEX idx_flag_cmd ON command_flags(cmd_id);
CREATE INDEX idx_flag_short ON command_flags(flag_short);
CREATE INDEX idx_flag_long ON command_flags(flag_long);

-- Command arguments (positional args)
CREATE TABLE IF NOT EXISTS command_arguments (
    arg_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    cmd_id INTEGER NOT NULL,
    
    -- Argument specification
    arg_position INTEGER NOT NULL,         -- 0-based position
    arg_name TEXT NOT NULL,
    arg_type TEXT NOT NULL,                -- FILE, DIRECTORY, STRING, INTEGER, PATH, PATTERN, etc.
    
    -- Constraints
    required INTEGER DEFAULT 0,
    variadic INTEGER DEFAULT 0,            -- Can accept multiple values
    min_count INTEGER DEFAULT 0,
    max_count INTEGER,
    
    -- Validation
    validation_regex TEXT,
    validation_function TEXT,              -- Name of validation function
    allowed_values TEXT,                   -- JSON array for enumerated types
    
    -- Description
    arg_description TEXT,
    arg_example TEXT,
    
    -- Binary encoding
    encoding_method TEXT,                  -- LENGTH_PREFIXED, NULL_TERMINATED, FIXED_SIZE
    max_encoded_size INTEGER,
    
    created_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(cmd_id) REFERENCES command_registry(cmd_id) ON DELETE CASCADE,
    UNIQUE(cmd_id, arg_position)
);

CREATE INDEX idx_arg_cmd ON command_arguments(cmd_id);
CREATE INDEX idx_arg_position ON command_arguments(cmd_id, arg_position);

-- Command handlers (execution logic chains)
CREATE TABLE IF NOT EXISTS command_handlers (
    handler_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    cmd_id INTEGER NOT NULL,
    
    -- Handler type
    handler_type TEXT NOT NULL,            -- QUANTUM_CIRCUIT, SYSCALL, BUILTIN, SQL, PYTHON, COMPOSITE, EXTERNAL
    
    -- Execution method
    execution_method TEXT,                 -- Method/function name
    execution_code TEXT,                   -- SQL query, Python code, or circuit definition
    
    -- Quantum circuit (if handler_type = QUANTUM_CIRCUIT)
    qasm_code TEXT,                        -- OpenQASM 2.0/3.0
    circuit_id INTEGER,                    -- FK to quantum_circuits
    
    -- Binary implementation
    binary_implementation BLOB,            -- Compiled binary code
    microcode_sequence TEXT,               -- JSON: [opcode1, opcode2, ...]
    
    -- Syscall (if handler_type = SYSCALL)
    syscall_number INTEGER,
    syscall_params TEXT,                   -- JSON: parameter mapping
    
    -- Execution requirements
    requires_qubits INTEGER DEFAULT 0,
    qubit_count INTEGER,
    requires_lattice_routing INTEGER DEFAULT 0,
    
    -- Priority (multiple handlers per command)
    priority INTEGER DEFAULT 0,
    
    -- Timeouts and retries
    timeout_seconds REAL DEFAULT 30.0,
    retry_count INTEGER DEFAULT 0,
    
    -- State
    enabled INTEGER DEFAULT 1,
    
    -- Metadata
    created_at REAL DEFAULT (julianday('now')),
    last_executed REAL,
    execution_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    avg_execution_ms REAL DEFAULT 0.0,
    
    FOREIGN KEY(cmd_id) REFERENCES command_registry(cmd_id) ON DELETE CASCADE,
    FOREIGN KEY(circuit_id) REFERENCES quantum_circuits(circuit_id),
    CHECK(handler_type IN ('QUANTUM_CIRCUIT', 'SYSCALL', 'BUILTIN', 'SQL', 'PYTHON', 'COMPOSITE', 'EXTERNAL'))
);

CREATE INDEX idx_handler_cmd ON command_handlers(cmd_id);
CREATE INDEX idx_handler_type ON command_handlers(handler_type);
CREATE INDEX idx_handler_priority ON command_handlers(cmd_id, priority DESC);
CREATE INDEX idx_handler_enabled ON command_handlers(enabled);

-- Command execution pipeline (multi-stage execution)
CREATE TABLE IF NOT EXISTS command_execution_pipeline (
    pipeline_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    cmd_id INTEGER NOT NULL,
    
    -- Pipeline stages
    stage_number INTEGER NOT NULL,
    stage_name TEXT NOT NULL,
    stage_handler_id INTEGER,
    
    -- Dependencies
    depends_on_stage INTEGER,              -- Previous stage that must complete
    
    -- Data flow
    input_from_stage INTEGER,              -- Which stage provides input
    output_to_stage INTEGER,               -- Which stage receives output
    
    -- Execution
    parallel_execution INTEGER DEFAULT 0,   -- Can execute in parallel with other stages
    optional INTEGER DEFAULT 0,             -- Stage can be skipped
    
    created_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(cmd_id) REFERENCES command_registry(cmd_id) ON DELETE CASCADE,
    FOREIGN KEY(stage_handler_id) REFERENCES command_handlers(handler_id),
    UNIQUE(cmd_id, stage_number)
);

CREATE INDEX idx_pipeline_cmd ON command_execution_pipeline(cmd_id);
CREATE INDEX idx_pipeline_stage ON command_execution_pipeline(cmd_id, stage_number);

-- Command aliases
CREATE TABLE IF NOT EXISTS command_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    alias_name TEXT UNIQUE NOT NULL,
    target_cmd_id INTEGER NOT NULL,
    
    -- Alias behavior
    prepend_args TEXT,                     -- JSON: args to prepend
    append_args TEXT,                      -- JSON: args to append
    flag_substitutions TEXT,               -- JSON: {alias_flag: real_flag}
    
    enabled INTEGER DEFAULT 1,
    
    created_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(target_cmd_id) REFERENCES command_registry(cmd_id) ON DELETE CASCADE
);

CREATE INDEX idx_alias_name ON command_aliases(alias_name);
CREATE INDEX idx_alias_target ON command_aliases(target_cmd_id);

-- Command groups (for command completion and discovery)
CREATE TABLE IF NOT EXISTS command_groups (
    group_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    group_name TEXT UNIQUE NOT NULL,
    group_description TEXT,
    parent_group_id INTEGER,
    
    FOREIGN KEY(parent_group_id) REFERENCES command_groups(group_id)
);

CREATE TABLE IF NOT EXISTS command_group_membership (
    cmd_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,
    
    PRIMARY KEY(cmd_id, group_id),
    FOREIGN KEY(cmd_id) REFERENCES command_registry(cmd_id) ON DELETE CASCADE,
    FOREIGN KEY(group_id) REFERENCES command_groups(group_id) ON DELETE CASCADE
);

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 7: OPCODE SYSTEM (BINARY INSTRUCTION SET)
-- Complete opcode architecture with microcode translation
-- ═══════════════════════════════════════════════════════════════════════════

-- CPU opcodes (master instruction set)
CREATE TABLE IF NOT EXISTS cpu_opcodes (
    opcode INTEGER PRIMARY KEY,            -- 0x00 to 0xFF (256 opcodes)
    
    -- Opcode identification
    mnemonic TEXT UNIQUE NOT NULL,
    opcode_name TEXT,
    
    -- Classification
    category TEXT NOT NULL,                -- QUANTUM, ARITHMETIC, LOGIC, MEMORY, CONTROL, IO, SYSTEM
    subcategory TEXT,
    
    -- Description
    description TEXT,
    
    -- Operands
    operand_count INTEGER DEFAULT 0,
    operand_types TEXT,                    -- JSON: ['REGISTER', 'IMMEDIATE', 'ADDRESS']
    operand_sizes TEXT,                    -- JSON: [1, 2, 4] (bytes)
    
    -- Encoding
    instruction_length INTEGER,            -- Total bytes (opcode + operands)
    byte_layout TEXT,                      -- JSON: {opcode: 0, operand1: 1, operand2: 2}
    
    -- Execution
    execution_cycles_min INTEGER DEFAULT 1,
    execution_cycles_max INTEGER,
    
    -- Quantum properties
    is_quantum INTEGER DEFAULT 0,
    quantum_gate_type TEXT,                -- H, X, Y, Z, CNOT, TOFFOLI, etc.
    requires_qubits INTEGER DEFAULT 0,
    modifies_quantum_state INTEGER DEFAULT 0,
    
    -- Microcode
    has_microcode INTEGER DEFAULT 0,
    microcode_entry_point INTEGER,
    
    -- Flags affected
    flags_affected TEXT,                   -- JSON: ['ZERO', 'CARRY', 'OVERFLOW', 'QUANTUM']
    
    -- Privileges
    privileged INTEGER DEFAULT 0,
    kernel_only INTEGER DEFAULT 0,
    
    -- State
    implemented INTEGER DEFAULT 1,
    deprecated INTEGER DEFAULT 0,
    
    created_at REAL DEFAULT (julianday('now')),
    
    CHECK(category IN ('QUANTUM', 'ARITHMETIC', 'LOGIC', 'MEMORY', 'CONTROL', 'IO', 'SYSTEM'))
);

CREATE INDEX idx_opcode_mnemonic ON cpu_opcodes(mnemonic);
CREATE INDEX idx_opcode_category ON cpu_opcodes(category);
CREATE INDEX idx_opcode_quantum ON cpu_opcodes(is_quantum);

-- Microcode sequences (opcode → microcode translation)
CREATE TABLE IF NOT EXISTS microcode_sequences (
    sequence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    opcode INTEGER NOT NULL,
    sequence_order INTEGER NOT NULL,       -- Execution order within opcode
    
    -- Microcode instruction
    micro_opcode TEXT NOT NULL,            -- FETCH, DECODE, EXECUTE, WRITEBACK, etc.
    micro_operands TEXT,                   -- JSON: operand specifications
    
    -- Control
    conditional TEXT,                      -- Condition for execution
    branch_target INTEGER,                 -- For conditional micro-ops
    
    -- Quantum operations
    quantum_operation TEXT,                -- Gate to apply, measurement, etc.
    qubit_allocation TEXT,                 -- Which qubits to use
    
    -- Description
    description TEXT,
    
    FOREIGN KEY(opcode) REFERENCES cpu_opcodes(opcode) ON DELETE CASCADE,
    UNIQUE(opcode, sequence_order)
);

CREATE INDEX idx_micro_opcode ON microcode_sequences(opcode);
CREATE INDEX idx_micro_order ON microcode_sequences(opcode, sequence_order);

-- Microcode primitives (atomic quantum operations)
CREATE TABLE IF NOT EXISTS microcode_primitives (
    primitive_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    primitive_name TEXT UNIQUE NOT NULL,
    
    -- Operation type
    operation_type TEXT NOT NULL,          -- GATE, MEASUREMENT, ALLOCATION, TRANSPORT
    
    -- Quantum implementation
    qasm_code TEXT,                        -- QASM for this primitive
    qiskit_method TEXT,                    -- Qiskit method name
    gate_matrix BLOB,                      -- Unitary matrix (for gates)
    
    -- Parameters
    parameter_count INTEGER DEFAULT 0,
    parameters TEXT,                       -- JSON: parameter specifications
    
    -- Execution
    execution_cycles INTEGER DEFAULT 1,
    
    -- Description
    description TEXT,
    
    created_at REAL DEFAULT (julianday('now')),
    
    CHECK(operation_type IN ('GATE', 'MEASUREMENT', 'ALLOCATION', 'TRANSPORT', 'RESET'))
);

CREATE INDEX idx_primitive_name ON microcode_primitives(primitive_name);
CREATE INDEX idx_primitive_type ON microcode_primitives(operation_type);

-- Syscall table (kernel interface)
CREATE TABLE IF NOT EXISTS syscall_table (
    syscall_number INTEGER PRIMARY KEY,
    
    syscall_name TEXT UNIQUE NOT NULL,
    syscall_category TEXT NOT NULL,       -- PROCESS, FILE, NETWORK, IPC, QUANTUM, SYSTEM
    
    -- Parameters
    param_count INTEGER DEFAULT 0,
    param_types TEXT,                      -- JSON: ['int', 'char*', 'size_t']
    param_names TEXT,                      -- JSON: ['fd', 'buf', 'count']
    
    -- Return value
    return_type TEXT DEFAULT 'int',
    
    -- Implementation
    handler_function TEXT,                 -- C function name or SQL query
    
    -- Quantum requirements
    requires_quantum_context INTEGER DEFAULT 0,
    allocates_qubits INTEGER DEFAULT 0,
    
    -- Permissions
    requires_capability TEXT,              -- JSON: required capabilities
    
    -- Description
    description TEXT,
    man_page_section INTEGER DEFAULT 2,
    
    enabled INTEGER DEFAULT 1,
    
    created_at REAL DEFAULT (julianday('now'))
);

CREATE INDEX idx_syscall_name ON syscall_table(syscall_name);
CREATE INDEX idx_syscall_category ON syscall_table(syscall_category);

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 8: QUANTUM CIRCUITS (QASM GATE PLACEHOLDERS)
-- Pre-defined quantum circuits for command execution
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS quantum_circuits (
    circuit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    circuit_name TEXT UNIQUE NOT NULL,
    circuit_description TEXT,
    
    -- Circuit specification
    num_qubits INTEGER NOT NULL,
    num_clbits INTEGER DEFAULT 0,
    circuit_depth INTEGER,
    gate_count INTEGER,
    
    -- QASM representation
    qasm_code TEXT NOT NULL,               -- OpenQASM 2.0 or 3.0
    qasm_version TEXT DEFAULT '2.0',
    
    -- Binary encoding
    binary_representation BLOB,            -- Compiled circuit binary
    binary_size INTEGER,
    
    -- Gate sequence
    gate_sequence TEXT,                    -- JSON: [{gate: 'H', qubits: [0]}, ...]
    
    -- Optimization
    optimization_level INTEGER DEFAULT 0,  -- 0-3
    optimized_qasm TEXT,
    optimized_depth INTEGER,
    optimized_gate_count INTEGER,
    
    -- Parameters (for parametrized circuits)
    has_parameters INTEGER DEFAULT 0,
    parameter_names TEXT,                  -- JSON: ['theta', 'phi']
    parameter_defaults TEXT,               -- JSON: [0.0, 1.57]
    
    -- Execution metrics
    avg_fidelity REAL DEFAULT 1.0,
    avg_execution_time_ms REAL,
    shots_default INTEGER DEFAULT 1024,
    
    -- Classification
    circuit_category TEXT,                 -- BASIC_GATE, ALGORITHM, SUBROUTINE, ERROR_CORRECTION
    tags TEXT,                             -- JSON: ['grover', 'search']
    
    -- State
    tested INTEGER DEFAULT 0,
    approved INTEGER DEFAULT 0,
    
    created_at REAL DEFAULT (julianday('now')),
    last_used REAL,
    use_count INTEGER DEFAULT 0,
    
    CHECK(num_qubits > 0),
    CHECK(optimization_level BETWEEN 0 AND 3)
);

CREATE INDEX idx_circuit_name ON quantum_circuits(circuit_name);
CREATE INDEX idx_circuit_category ON quantum_circuits(circuit_category);
CREATE INDEX idx_circuit_qubits ON quantum_circuits(num_qubits);

-- Quantum gate library (individual gates)
CREATE TABLE IF NOT EXISTS quantum_gate_library (
    gate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    gate_name TEXT UNIQUE NOT NULL,        -- H, X, Y, Z, RX, RY, RZ, CNOT, TOFFOLI, etc.
    gate_symbol TEXT,                      -- Symbol for display
    
    -- Gate properties
    num_qubits INTEGER NOT NULL,
    num_parameters INTEGER DEFAULT 0,
    parameter_names TEXT,                  -- JSON: ['theta'] for RX(theta)
    
    -- Unitary matrix
    matrix_real BLOB,                      -- Real part of 2^n × 2^n matrix
    matrix_imag BLOB,                      -- Imaginary part
    
    -- QASM representation
    qasm_definition TEXT,
    
    -- Gate type
    gate_type TEXT,                        -- PAULI, CLIFFORD, T, ROTATION, CONTROLLED, SWAP
    
    -- Properties
    is_hermitian INTEGER DEFAULT 0,
    is_unitary INTEGER DEFAULT 1,
    is_clifford INTEGER DEFAULT 0,
    
    -- Binary opcode
    opcode INTEGER,                        -- Associated CPU opcode
    
    -- Description
    description TEXT,
    
    created_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(opcode) REFERENCES cpu_opcodes(opcode),
    CHECK(num_qubits > 0)
);

CREATE INDEX idx_gate_name ON quantum_gate_library(gate_name);
CREATE INDEX idx_gate_type ON quantum_gate_library(gate_type);
CREATE INDEX idx_gate_qubits ON quantum_gate_library(num_qubits);

-- Circuit compilation cache
CREATE TABLE IF NOT EXISTS circuit_compilation_cache (
    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    circuit_id INTEGER NOT NULL,
    
    -- Compilation parameters
    optimization_level INTEGER,
    target_backend TEXT,
    coupling_map TEXT,                     -- JSON: topology constraints
    
    -- Compiled circuit
    compiled_qasm TEXT,
    compiled_binary BLOB,
    
    -- Metrics
    original_depth INTEGER,
    compiled_depth INTEGER,
    original_gates INTEGER,
    compiled_gates INTEGER,
    compilation_time_ms REAL,
    
    -- Validity
    valid_until REAL,
    
    created_at REAL DEFAULT (julianday('now')),
    last_used REAL,
    use_count INTEGER DEFAULT 0,
    
    FOREIGN KEY(circuit_id) REFERENCES quantum_circuits(circuit_id) ON DELETE CASCADE
);

CREATE INDEX idx_comp_circuit ON circuit_compilation_cache(circuit_id);
CREATE INDEX idx_comp_params ON circuit_compilation_cache(circuit_id, optimization_level);

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 9: COMMAND EXECUTION LOG & RESULT RETRIEVAL
-- Complete audit trail with quantum metrics
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS command_execution_log (
    exec_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Session context
    session_id TEXT NOT NULL,
    pid INTEGER,
    
    -- Command
    cmd_id INTEGER,
    cmd_name TEXT NOT NULL,
    cmd_line TEXT,                         -- Full command line as entered
    
    -- Parsing
    parsed_args TEXT,                      -- JSON: parsed arguments
    parsed_flags TEXT,                     -- JSON: parsed flags
    
    -- Execution
    handler_id INTEGER,
    execution_method TEXT,
    
    -- Binary transmission
    binary_sent BLOB,                      -- Binary sent to CPU
    binary_hash BLOB,
    packet_id INTEGER,                     -- Quantum packet used
    
    -- Quantum metrics
    qubits_allocated TEXT,                 -- JSON: [qubit_id1, ...]
    epr_pairs_used TEXT,                   -- JSON: [pair_id1, ...]
    triangles_used TEXT,                   -- JSON: [triangle_id1, ...]
    route_id INTEGER,
    
    chsh_value REAL,
    bell_inequality_violated INTEGER,
    quantum_advantage REAL DEFAULT 1.0,
    
    -- Timing
    start_time REAL,
    end_time REAL,
    execution_time_ms REAL,
    quantum_time_ms REAL,                  -- Time spent in quantum operations
    classical_time_ms REAL,                -- Time spent in classical processing
    latency_sigma REAL,                    -- σ-time metric
    
    -- Result
    success INTEGER,
    exit_code INTEGER DEFAULT 0,
    return_value TEXT,                     -- JSON: structured return value
    output_text TEXT,                      -- Text output for terminal
    output_binary BLOB,                    -- Binary output
    
    error_occurred INTEGER DEFAULT 0,
    error_message TEXT,
    error_code TEXT,
    
    -- Resource usage
    memory_used_bytes INTEGER,
    qubits_measured INTEGER DEFAULT 0,
    gates_applied INTEGER DEFAULT 0,
    
    timestamp REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(cmd_id) REFERENCES command_registry(cmd_id),
    FOREIGN KEY(handler_id) REFERENCES command_handlers(handler_id),
    FOREIGN KEY(packet_id) REFERENCES quantum_channel_packets(packet_id),
    FOREIGN KEY(route_id) REFERENCES quantum_routing_table(route_id)
);

CREATE INDEX idx_exec_cmd ON command_execution_log(cmd_name);
CREATE INDEX idx_exec_session ON command_execution_log(session_id);
CREATE INDEX idx_exec_time ON command_execution_log(timestamp);
CREATE INDEX idx_exec_success ON command_execution_log(success);
CREATE INDEX idx_exec_packet ON command_execution_log(packet_id);

-- Quantum measurement results (for qmeasure and similar commands)
CREATE TABLE IF NOT EXISTS quantum_measurement_results (
    measurement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    exec_id INTEGER NOT NULL,
    
    -- Measurement specification
    qubit_ids TEXT NOT NULL,               -- JSON: qubits measured
    measurement_basis TEXT DEFAULT 'Z',    -- Z, X, Y, BELL, GHZ
    
    -- Results
    outcome_bitstring TEXT,                -- '01101010...'
    outcome_counts TEXT,                   -- JSON: {'0': 512, '1': 512}
    probability_distribution TEXT,         -- JSON: {'0': 0.5, '1': 0.5}
    
    -- Statistics
    shots INTEGER DEFAULT 1024,
    most_probable_outcome TEXT,
    shannon_entropy REAL,
    
    -- Quantum state before measurement
    pre_measurement_state BLOB,
    
    -- Classical shadow (for state tomography)
    classical_shadow BLOB,
    
    timestamp REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(exec_id) REFERENCES command_execution_log(exec_id) ON DELETE CASCADE
);

CREATE INDEX idx_meas_exec ON quantum_measurement_results(exec_id);
CREATE INDEX idx_meas_qubits ON quantum_measurement_results(qubit_ids);

-- Output-only command results (e.g., ls, cat, echo)
CREATE TABLE IF NOT EXISTS command_output_results (
    output_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    exec_id INTEGER NOT NULL,
    
    -- Output type
    output_type TEXT NOT NULL,             -- TEXT, BINARY, JSON, TABLE
    
    -- Output data
    output_text TEXT,
    output_binary BLOB,
    output_json TEXT,
    
    -- Formatting
    format_applied TEXT,                   -- ANSI colors, table formatting, etc.
    mime_type TEXT,
    
    -- Paging
    is_paged INTEGER DEFAULT 0,
    page_size INTEGER,
    total_pages INTEGER,
    
    timestamp REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(exec_id) REFERENCES command_execution_log(exec_id) ON DELETE CASCADE,
    CHECK(output_type IN ('TEXT', 'BINARY', 'JSON', 'TABLE', 'XML', 'HTML'))
);

CREATE INDEX idx_output_exec ON command_output_results(exec_id);
CREATE INDEX idx_output_type ON command_output_results(output_type);

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 10: FILESYSTEM SUBSYSTEM
-- Complete virtual filesystem with external mounting via vacuum tunnels
-- ═══════════════════════════════════════════════════════════════════════════

-- Filesystem superblock (global filesystem state)
CREATE TABLE IF NOT EXISTS filesystem_superblock (
    fs_id INTEGER PRIMARY KEY DEFAULT 1,
    
    fs_name TEXT DEFAULT 'QUNIX_VFS',
    fs_version TEXT DEFAULT '1.0.0',
    
    -- Block configuration
    block_size INTEGER DEFAULT 4096,
    total_blocks INTEGER,
    free_blocks INTEGER,
    
    -- Inode configuration
    total_inodes INTEGER DEFAULT 1000000,
    free_inodes INTEGER,
    next_inode INTEGER DEFAULT 2,          -- Root is always 1
    
    -- Mount state
    mounted INTEGER DEFAULT 0,
    mount_point TEXT DEFAULT '/',
    mount_time REAL,
    mount_flags TEXT,                      -- JSON: mount options
    
    -- Quantum features
    quantum_encoding_enabled INTEGER DEFAULT 1,
    lattice_base_point INTEGER,            -- Starting lattice point for FS
    ecc_enabled INTEGER DEFAULT 1,         -- Golay error correction
    
    -- External mounts
    external_mounts_enabled INTEGER DEFAULT 1,
    vacuum_tunneling_enabled INTEGER DEFAULT 1,
    
    -- Statistics
    files_total INTEGER DEFAULT 0,
    directories_total INTEGER DEFAULT 1,   -- Root
    symlinks_total INTEGER DEFAULT 0,
    bytes_used INTEGER DEFAULT 0,
    
    -- Metadata
    created_at REAL DEFAULT (julianday('now')),
    last_fsck REAL,
    last_defrag REAL,
    
    CHECK(fs_id = 1)
);

-- Inodes (universal file/directory representation)
CREATE TABLE IF NOT EXISTS filesystem_inodes (
    inode_id INTEGER PRIMARY KEY,
    
    -- Type
    inode_type TEXT NOT NULL,              -- f=file, d=directory, l=symlink, p=pipe, s=socket
    
    -- Permissions (Unix-style)
    mode INTEGER DEFAULT 0644,             -- rwxrwxrwx bits
    uid INTEGER DEFAULT 0,
    gid INTEGER DEFAULT 0,
    
    -- Size and blocks
    size INTEGER DEFAULT 0,                -- File size in bytes
    blocks_allocated INTEGER DEFAULT 0,
    
    -- Link count
    nlink INTEGER DEFAULT 1,               -- Hard link count
    
    -- Timestamps (Unix epoch)
    atime REAL,                            -- Last access
    mtime REAL,                            -- Last modification
    ctime REAL,                            -- Last status change
    crtime REAL,                           -- Creation time
    
    -- Quantum encoding
    quantum_encoded INTEGER DEFAULT 0,
    lattice_point_id INTEGER,              -- If quantum-encoded
    amplitude_encoding BLOB,               -- Quantum state amplitudes
    
    -- Error correction
    golay_protected INTEGER DEFAULT 0,
    golay_parity BLOB,
    
    -- Extended attributes
    xattrs TEXT,                           -- JSON: extended attributes
    
    -- Flags
    flags INTEGER DEFAULT 0,               -- Immutable, append-only, etc.
    
    -- Generation (for NFS)
    generation INTEGER DEFAULT 0,
    
    created_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(lattice_point_id) REFERENCES leech_lattice(point_id),
    CHECK(inode_type IN ('f', 'd', 'l', 'p', 's', 'b', 'c'))
);

CREATE INDEX idx_inode_type ON filesystem_inodes(inode_type);
CREATE INDEX idx_inode_lattice ON filesystem_inodes(lattice_point_id);

-- Directory entries (name → inode mapping)
CREATE TABLE IF NOT EXISTS filesystem_dentries (
    dentry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    parent_inode INTEGER NOT NULL,         -- Parent directory inode
    child_inode INTEGER NOT NULL,          -- Child inode
    
    -- Name
    name TEXT NOT NULL,                    -- Filename (no path)
    name_hash BLOB,                        -- SHA256 for fast lookup
    
    -- Type hint (for performance)
    file_type TEXT,                        -- Same as inode_type
    
    created_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(parent_inode) REFERENCES filesystem_inodes(inode_id) ON DELETE CASCADE,
    FOREIGN KEY(child_inode) REFERENCES filesystem_inodes(inode_id) ON DELETE CASCADE,
    UNIQUE(parent_inode, name)
);

CREATE INDEX idx_dentry_parent ON filesystem_dentries(parent_inode);
CREATE INDEX idx_dentry_name ON filesystem_dentries(name);
CREATE INDEX idx_dentry_hash ON filesystem_dentries(name_hash);
CREATE INDEX idx_dentry_child ON filesystem_dentries(child_inode);

-- File data blocks
CREATE TABLE IF NOT EXISTS filesystem_blocks (
    block_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    inode_id INTEGER NOT NULL,
    block_index INTEGER NOT NULL,         -- Sequential block number within file
    
    -- Data
    data BLOB,                             -- Actual file data (up to block_size)
    data_size INTEGER,                     -- Actual bytes in this block
    
    -- Compression
    compressed INTEGER DEFAULT 0,
    compression_algo TEXT,                 -- ZLIB, GZIP, LZ4, ZSTD
    original_size INTEGER,
    
    -- Quantum encoding
    quantum_encoded INTEGER DEFAULT 0,
    qubit_ids TEXT,                        -- JSON: qubits used for this block
    amplitude_data BLOB,                   -- Quantum amplitude encoding
    
    -- Integrity
    checksum BLOB,                         -- SHA256 of uncompressed data
    golay_parity BLOB,                     -- Golay ECC parity bits
    
    -- Metadata
    created_at REAL DEFAULT (julianday('now')),
    modified_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(inode_id) REFERENCES filesystem_inodes(inode_id) ON DELETE CASCADE,
    UNIQUE(inode_id, block_index)
);

CREATE INDEX idx_block_inode ON filesystem_blocks(inode_id);
CREATE INDEX idx_block_quantum ON filesystem_blocks(quantum_encoded);

-- Symlinks (target path storage)
CREATE TABLE IF NOT EXISTS filesystem_symlinks (
    link_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    inode_id INTEGER UNIQUE NOT NULL,
    target_path TEXT NOT NULL,             -- Symlink target
    
    created_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(inode_id) REFERENCES filesystem_inodes(inode_id) ON DELETE CASCADE
);

CREATE INDEX idx_symlink_inode ON filesystem_symlinks(inode_id);

-- Current working directory per session
CREATE TABLE IF NOT EXISTS filesystem_cwd (
    session_id TEXT PRIMARY KEY,
    
    cwd_inode INTEGER NOT NULL,
    cwd_path TEXT NOT NULL,               -- Cached full path
    
    updated_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(cwd_inode) REFERENCES filesystem_inodes(inode_id)
);

-- External filesystem mounts (via vacuum tunnels)
CREATE TABLE IF NOT EXISTS filesystem_external_mounts (
    mount_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- External source
    external_type TEXT NOT NULL,           -- SQLITE_DB, POSTGRES, MYSQL, S3, LOCAL_DIR
    external_uri TEXT NOT NULL,            -- Connection string or path
    external_credentials BLOB,             -- Encrypted credentials
    
    -- Mount point
    mount_inode INTEGER UNIQUE NOT NULL,   -- Directory where mounted
    mount_path TEXT NOT NULL,              -- Full path (cached)
    
    -- Tunnel
    vacuum_tunnel_id INTEGER,
    manifold_id INTEGER,
    
    -- Options
    readonly INTEGER DEFAULT 0,
    automount INTEGER DEFAULT 0,
    mount_on_access INTEGER DEFAULT 1,
    
    -- State
    currently_mounted INTEGER DEFAULT 0,
    mount_time REAL,
    last_access REAL,
    access_count INTEGER DEFAULT 0,
    
    -- Errors
    mount_errors INTEGER DEFAULT 0,
    last_error TEXT,
    last_error_time REAL,
    
    -- Metadata
    created_at REAL DEFAULT (julianday('now')),
    enabled INTEGER DEFAULT 1,
    
    FOREIGN KEY(mount_inode) REFERENCES filesystem_inodes(inode_id),
    FOREIGN KEY(vacuum_tunnel_id) REFERENCES vacuum_tunnels(tunnel_id),
    FOREIGN KEY(manifold_id) REFERENCES klein_bottle_manifolds(manifold_id),
    CHECK(external_type IN ('SQLITE_DB', 'POSTGRES', 'MYSQL', 'S3', 'GCS', 'AZURE', 'LOCAL_DIR', 'NFS', 'CIFS'))
);

CREATE INDEX idx_ext_mount_inode ON filesystem_external_mounts(mount_inode);
CREATE INDEX idx_ext_mount_path ON filesystem_external_mounts(mount_path);
CREATE INDEX idx_ext_mount_state ON filesystem_external_mounts(currently_mounted);

-- File descriptor table (open files)
CREATE TABLE IF NOT EXISTS filesystem_open_files (
    fd INTEGER PRIMARY KEY AUTOINCREMENT,
    
    session_id TEXT NOT NULL,
    inode_id INTEGER NOT NULL,
    
    -- Open mode
    mode TEXT NOT NULL,                    -- r, w, a, r+, w+, a+
    flags INTEGER,                         -- O_RDONLY, O_WRONLY, O_RDWR, etc.
    
    -- Position
    offset INTEGER DEFAULT 0,              -- Current read/write position
    
    -- Locking
    locked INTEGER DEFAULT 0,
    lock_type TEXT,                        -- SHARED, EXCLUSIVE
    lock_owner TEXT,
    
    -- Statistics
    bytes_read INTEGER DEFAULT 0,
    bytes_written INTEGER DEFAULT 0,
    
    opened_at REAL DEFAULT (julianday('now')),
    last_access REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(inode_id) REFERENCES filesystem_inodes(inode_id)
);

CREATE INDEX idx_fd_session ON filesystem_open_files(session_id);
CREATE INDEX idx_fd_inode ON filesystem_open_files(inode_id);

-- Filesystem cache (inode cache)
CREATE TABLE IF NOT EXISTS filesystem_inode_cache (
    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    inode_id INTEGER UNIQUE NOT NULL,
    
    -- Cached data
    cached_metadata TEXT,                  -- JSON: full inode metadata
    cached_dentries TEXT,                  -- JSON: for directories
    
    -- Cache state
    dirty INTEGER DEFAULT 0,
    locked INTEGER DEFAULT 0,
    pinned INTEGER DEFAULT 0,              -- Keep in cache
    
    -- Timing
    cached_at REAL DEFAULT (julianday('now')),
    last_access REAL DEFAULT (julianday('now')),
    access_count INTEGER DEFAULT 0,
    
    FOREIGN KEY(inode_id) REFERENCES filesystem_inodes(inode_id)
);

CREATE INDEX idx_icache_inode ON filesystem_inode_cache(inode_id);
CREATE INDEX idx_icache_dirty ON filesystem_inode_cache(dirty);

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 11: PROCESS MANAGEMENT
-- Unix process model with quantum resource tracking
-- ═══════════════════════════════════════════════════════════════════════════

-- Process table
CREATE TABLE IF NOT EXISTS processes (
    pid INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Process identification
    process_name TEXT NOT NULL,
    program_path TEXT,                     -- Path to executable
    
    -- Parent/child relationships
    ppid INTEGER,                          -- Parent PID
    pgid INTEGER,                          -- Process group ID
    sid INTEGER,                           -- Session ID
    
    -- User/group
    uid INTEGER DEFAULT 0,
    gid INTEGER DEFAULT 0,
    euid INTEGER,                          -- Effective UID
    egid INTEGER,                          -- Effective GID
    
    -- State
    state TEXT DEFAULT 'RUNNING',          -- RUNNING, SLEEPING, STOPPED, ZOMBIE, DEAD
    exit_code INTEGER,
    
    -- Execution context
    program_counter INTEGER DEFAULT 0,     -- PC register
    stack_pointer INTEGER DEFAULT 0,       -- SP register
    base_pointer INTEGER DEFAULT 0,        -- BP register
    
    -- Registers (JSON)
    registers TEXT,                        -- JSON: general-purpose registers
    flags TEXT,                            -- JSON: CPU flags
    
    -- Memory
    memory_base INTEGER,
    memory_size INTEGER,
    stack_size INTEGER DEFAULT 65536,
    heap_size INTEGER DEFAULT 0,
    
    -- Quantum resources
    quantum_context_id INTEGER,
    qubit_base INTEGER,                    -- First allocated qubit
    num_qubits_allocated INTEGER DEFAULT 0,
    lattice_region_start INTEGER,
    lattice_region_end INTEGER,
    
    -- File descriptors
    stdin_fd INTEGER,
    stdout_fd INTEGER,
    stderr_fd INTEGER,
    
    -- Working directory
    cwd_inode INTEGER,
    
    -- Priority
    nice INTEGER DEFAULT 0,
    priority INTEGER DEFAULT 0,
    
    -- Resource usage
    cpu_time_us INTEGER DEFAULT 0,
    quantum_time_sigma REAL DEFAULT 0.0,
    memory_usage_bytes INTEGER DEFAULT 0,
    
    -- Timing
    start_time REAL,
    end_time REAL,
    last_scheduled REAL,
    
    -- Flags
    is_kernel_process INTEGER DEFAULT 0,
    is_daemon INTEGER DEFAULT 0,
    
    created_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(ppid) REFERENCES processes(pid),
    FOREIGN KEY(cwd_inode) REFERENCES filesystem_inodes(inode_id),
    CHECK(state IN ('RUNNING', 'SLEEPING', 'STOPPED', 'ZOMBIE', 'DEAD'))
);

CREATE INDEX idx_proc_state ON processes(state);
CREATE INDEX idx_proc_ppid ON processes(ppid);
CREATE INDEX idx_proc_uid ON processes(uid);
CREATE INDEX idx_proc_qubits ON processes(qubit_base);

-- Process quantum context (detailed quantum state)
CREATE TABLE IF NOT EXISTS process_quantum_contexts (
    context_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    pid INTEGER UNIQUE NOT NULL,
    
    -- Qubit allocation
    allocated_qubits TEXT,                 -- JSON: [qubit_id1, ...]
    qubit_allocation_map TEXT,             -- JSON: {logical: physical}
    
    -- Entanglement resources
    epr_pairs_allocated TEXT,              -- JSON: [pair_id1, ...]
    triangles_allocated TEXT,              -- JSON: [triangle_id1, ...]
    entanglement_classes TEXT,             -- JSON: [class_id1, ...]
    
    -- Quantum state
    quantum_state_vector BLOB,             -- Full state vector (if small)
    density_matrix BLOB,                   -- Density matrix (if mixed)
    
    -- Error correction
    golay_instances TEXT,                  -- JSON: decoder instance IDs
    error_correction_enabled INTEGER DEFAULT 1,
    
    -- Measurements
    measurement_history TEXT,              -- JSON: recent measurements
    measurement_count INTEGER DEFAULT 0,
    
    -- Coherence
    coherence_time_remaining_us REAL,
    
    created_at REAL DEFAULT (julianday('now')),
    last_updated REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(pid) REFERENCES processes(pid) ON DELETE CASCADE
);

CREATE INDEX idx_qctx_pid ON process_quantum_contexts(pid);

-- Process scheduling queue
CREATE TABLE IF NOT EXISTS process_scheduler_queue (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    pid INTEGER NOT NULL,
    
    -- Scheduling
    queue_type TEXT DEFAULT 'READY',       -- READY, WAITING, BLOCKED
    priority INTEGER DEFAULT 0,
    time_slice_remaining_us INTEGER,
    
    -- Waiting conditions
    waiting_for TEXT,                      -- QUBIT, EPR, IO, CHILD, SIGNAL
    wait_start_time REAL,
    timeout REAL,
    
    enqueued_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(pid) REFERENCES processes(pid) ON DELETE CASCADE,
    CHECK(queue_type IN ('READY', 'WAITING', 'BLOCKED'))
);

CREATE INDEX idx_sched_queue ON process_scheduler_queue(queue_type, priority DESC);
CREATE INDEX idx_sched_pid ON process_scheduler_queue(pid);

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 12: TERMINAL I/O SUBSYSTEM
-- Complete terminal emulation with session management
-- ═══════════════════════════════════════════════════════════════════════════

-- Terminal sessions
CREATE TABLE IF NOT EXISTS terminal_sessions (
    session_id TEXT PRIMARY KEY,
    
    -- Session type
    session_type TEXT DEFAULT 'XTERM',     -- XTERM, PTY, SSH, TELNET
    
    -- User
    uid INTEGER,
    username TEXT,
    
    -- Terminal settings
    term_type TEXT DEFAULT 'xterm-256color',
    rows INTEGER DEFAULT 24,
    cols INTEGER DEFAULT 80,
    
    -- Shell
    shell_pid INTEGER,                     -- PID of shell process
    shell_path TEXT DEFAULT '/bin/qsh',
    
    -- Current directory
    cwd_inode INTEGER,
    cwd_path TEXT,
    
    -- Environment
    environment TEXT,                      -- JSON: environment variables
    
    -- State
    status TEXT DEFAULT 'ACTIVE',          -- ACTIVE, SUSPENDED, CLOSED
    
    -- Command history
    history_size INTEGER DEFAULT 1000,
    history_index INTEGER DEFAULT 0,
    
    -- Statistics
    commands_executed INTEGER DEFAULT 0,
    bytes_input INTEGER DEFAULT 0,
    bytes_output INTEGER DEFAULT 0,
    
    -- Timing
    created_at REAL DEFAULT (julianday('now')),
    last_activity REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(shell_pid) REFERENCES processes(pid),
    FOREIGN KEY(cwd_inode) REFERENCES filesystem_inodes(inode_id),
    CHECK(status IN ('ACTIVE', 'SUSPENDED', 'CLOSED'))
);

CREATE INDEX idx_term_status ON terminal_sessions(status);
CREATE INDEX idx_term_user ON terminal_sessions(uid);

-- Terminal input buffer
CREATE TABLE IF NOT EXISTS terminal_input (
    input_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    session_id TEXT NOT NULL,
    
    -- Input data
    data TEXT NOT NULL,                    -- Raw input
    data_type TEXT DEFAULT 'TEXT',         -- TEXT, CONTROL, BINARY
    
    -- Processing
    processed INTEGER DEFAULT 0,
    processed_at REAL,
    
    -- Echo
    echoed INTEGER DEFAULT 0,
    
    timestamp REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(session_id) REFERENCES terminal_sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX idx_term_input_session ON terminal_input(session_id);
CREATE INDEX idx_term_input_processed ON terminal_input(processed);

-- Terminal output buffer
CREATE TABLE IF NOT EXISTS terminal_output (
    output_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    session_id TEXT NOT NULL,
    
    -- Output data
    data TEXT NOT NULL,                    -- Raw output (with ANSI codes)
    data_size INTEGER,
    
    -- Type
    output_type TEXT DEFAULT 'STDOUT',     -- STDOUT, STDERR, SYSTEM
    
    -- Formatting
    ansi_formatted INTEGER DEFAULT 1,
    color_depth INTEGER DEFAULT 256,
    
    -- Paging
    page_number INTEGER,
    
    timestamp REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(session_id) REFERENCES terminal_sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX idx_term_output_session ON terminal_output(session_id);
CREATE INDEX idx_term_output_time ON terminal_output(timestamp);

-- Terminal command history
CREATE TABLE IF NOT EXISTS terminal_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    session_id TEXT NOT NULL,
    
    -- Command
    command TEXT NOT NULL,
    command_number INTEGER,                -- Sequential number in session
    
    -- Context
    cwd TEXT,
    
    -- Execution
    exec_id INTEGER,                       -- FK to command_execution_log
    exit_code INTEGER,
    
    -- Timestamp
    executed_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(session_id) REFERENCES terminal_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY(exec_id) REFERENCES command_execution_log(exec_id)
);

CREATE INDEX idx_hist_session ON terminal_history(session_id);
CREATE INDEX idx_hist_time ON terminal_history(executed_at);

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 13: NETWORK SUBSYSTEM
-- Quantum NIC integration with classical networking
-- ═══════════════════════════════════════════════════════════════════════════

-- Network interfaces
CREATE TABLE IF NOT EXISTS network_interfaces (
    interface_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Interface identification
    interface_name TEXT UNIQUE NOT NULL,   -- eth0, qnic0, lo, etc.
    interface_type TEXT NOT NULL,          -- QUANTUM_NIC, ETHERNET, LOOPBACK
    
    -- MAC address (for classical)
    mac_address BLOB,
    
    -- Quantum addressing (for QNIC)
    lattice_point_id INTEGER,
    j_address BLOB,
    epr_pool_base_address BLOB,
    
    -- IP configuration
    ip_address TEXT,                       -- IPv4 or IPv6
    netmask TEXT,
    gateway TEXT,
    
    -- State
    state TEXT DEFAULT 'DOWN',             -- UP, DOWN, TESTING
    mtu INTEGER DEFAULT 1500,
    
    -- Statistics
    packets_sent INTEGER DEFAULT 0,
    packets_received INTEGER DEFAULT 0,
    bytes_sent INTEGER DEFAULT 0,
    bytes_received INTEGER DEFAULT 0,
    errors_send INTEGER DEFAULT 0,
    errors_receive INTEGER DEFAULT 0,
    
    -- Quantum metrics (for QNIC)
    quantum_packets_sent INTEGER DEFAULT 0,
    quantum_packets_received INTEGER DEFAULT 0,
    avg_chsh_value REAL,
    
    created_at REAL DEFAULT (julianday('now')),
    last_up_time REAL,
    
    FOREIGN KEY(lattice_point_id) REFERENCES leech_lattice(point_id),
    CHECK(interface_type IN ('QUANTUM_NIC', 'ETHERNET', 'LOOPBACK', 'TUNNEL')),
    CHECK(state IN ('UP', 'DOWN', 'TESTING'))
);

CREATE INDEX idx_iface_type ON network_interfaces(interface_type);
CREATE INDEX idx_iface_state ON network_interfaces(state);

-- Network connections (sockets)
CREATE TABLE IF NOT EXISTS network_connections (
    connection_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Connection identification
    protocol TEXT NOT NULL,                -- TCP, UDP, QUANTUM
    
    -- Local endpoint
    local_interface_id INTEGER,
    local_address TEXT,
    local_port INTEGER,
    
    -- Remote endpoint
    remote_address TEXT,
    remote_port INTEGER,
    
    -- Quantum routing (for QUANTUM protocol)
    quantum_route_id INTEGER,
    epr_pairs_allocated TEXT,              -- JSON: pair IDs
    
    -- State
    state TEXT DEFAULT 'CLOSED',           -- LISTEN, SYN_SENT, ESTABLISHED, CLOSE_WAIT, CLOSED
    
    -- Process binding
    pid INTEGER,                           -- Owning process
    
    -- Statistics
    packets_sent INTEGER DEFAULT 0,
    packets_received INTEGER DEFAULT 0,
    bytes_sent INTEGER DEFAULT 0,
    bytes_received INTEGER DEFAULT 0,
    retransmits INTEGER DEFAULT 0,
    
    -- Timing
    established_at REAL,
    last_activity REAL,
    timeout REAL,
    
    created_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(local_interface_id) REFERENCES network_interfaces(interface_id),
    FOREIGN KEY(quantum_route_id) REFERENCES quantum_routing_table(route_id),
    FOREIGN KEY(pid) REFERENCES processes(pid),
    CHECK(protocol IN ('TCP', 'UDP', 'ICMP', 'QUANTUM', 'RAW')),
    CHECK(state IN ('CLOSED', 'LISTEN', 'SYN_SENT', 'SYN_RECEIVED', 'ESTABLISHED', 
                    'FIN_WAIT_1', 'FIN_WAIT_2', 'CLOSE_WAIT', 'CLOSING', 'LAST_ACK', 'TIME_WAIT'))
);

CREATE INDEX idx_conn_state ON network_connections(state);
CREATE INDEX idx_conn_protocol ON network_connections(protocol);
CREATE INDEX idx_conn_pid ON network_connections(pid);

-- Routing table (classical + quantum)
CREATE TABLE IF NOT EXISTS network_routing_table (
    route_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Destination
    destination_network TEXT,              -- CIDR notation or j-address
    destination_type TEXT,                 -- CLASSICAL, QUANTUM, HYBRID
    
    -- Gateway
    gateway_address TEXT,
    gateway_interface_id INTEGER,
    
    -- Quantum path (for QUANTUM routes)
    quantum_route_id INTEGER,
    
    -- Metrics
    metric INTEGER DEFAULT 1,
    hops INTEGER,
    latency_ms REAL,
    
    -- Flags
    is_default_route INTEGER DEFAULT 0,
    is_static INTEGER DEFAULT 0,
    
    -- State
    enabled INTEGER DEFAULT 1,
    
    created_at REAL DEFAULT (julianday('now')),
    last_used REAL,
    use_count INTEGER DEFAULT 0,
    
    FOREIGN KEY(gateway_interface_id) REFERENCES network_interfaces(interface_id),
    FOREIGN KEY(quantum_route_id) REFERENCES quantum_routing_table(route_id),
    CHECK(destination_type IN ('CLASSICAL', 'QUANTUM', 'HYBRID'))
);

CREATE INDEX idx_net_route_dest ON network_routing_table(destination_network);
CREATE INDEX idx_net_route_default ON network_routing_table(is_default_route);

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 14: SYSTEM MONITORING & HEALTH
-- Comprehensive metrics and diagnostics
-- ═══════════════════════════════════════════════════════════════════════════

-- System metrics (real-time)
CREATE TABLE IF NOT EXISTS system_metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    metric_name TEXT NOT NULL,
    metric_category TEXT,                  -- CPU, MEMORY, QUANTUM, NETWORK, FILESYSTEM
    
    -- Value
    metric_value REAL NOT NULL,
    metric_unit TEXT,                      -- percent, bytes, qubits, ms, etc.
    
    -- Context
    component TEXT,                        -- Which component this metric is for
    
    -- Timing
    timestamp REAL DEFAULT (julianday('now')),
    window_start REAL,
    window_end REAL
);

CREATE INDEX idx_metric_name ON system_metrics(metric_name);
CREATE INDEX idx_metric_category ON system_metrics(metric_category);
CREATE INDEX idx_metric_time ON system_metrics(timestamp);

-- System health checks
CREATE TABLE IF NOT EXISTS system_health_checks (
    check_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    check_name TEXT NOT NULL,
    check_category TEXT,                   -- QUANTUM, DATABASE, FILESYSTEM, NETWORK
    
    -- Status
    status TEXT,                           -- PASS, WARN, FAIL, UNKNOWN
    status_message TEXT,
    
    -- Measurements
    measured_value REAL,
    threshold_warn REAL,
    threshold_fail REAL,
    
    -- Timing
    check_duration_ms REAL,
    timestamp REAL DEFAULT (julianday('now')),
    
    CHECK(status IN ('PASS', 'WARN', 'FAIL', 'UNKNOWN'))
);

CREATE INDEX idx_health_status ON system_health_checks(status);
CREATE INDEX idx_health_time ON system_health_checks(timestamp);

-- Error log (system-wide)
CREATE TABLE IF NOT EXISTS system_error_log (
    error_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Error classification
    error_level TEXT NOT NULL,             -- DEBUG, INFO, WARNING, ERROR, CRITICAL
    error_category TEXT,                   -- QUANTUM, FILESYSTEM, NETWORK, PROCESS, etc.
    error_code TEXT,
    
    -- Error details
    error_message TEXT NOT NULL,
    error_context TEXT,                    -- JSON: additional context
    stack_trace TEXT,
    
    -- Source
    component TEXT,                        -- Which component raised the error
    pid INTEGER,
    session_id TEXT,
    
    -- Resolution
    resolved INTEGER DEFAULT 0,
    resolution_notes TEXT,
    resolved_at REAL,
    
    timestamp REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(pid) REFERENCES processes(pid),
    CHECK(error_level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'))
);

CREATE INDEX idx_error_level ON system_error_log(error_level);
CREATE INDEX idx_error_category ON system_error_log(error_category);
CREATE INDEX idx_error_time ON system_error_log(timestamp);
CREATE INDEX idx_error_resolved ON system_error_log(resolved);

-- Performance profiling
CREATE TABLE IF NOT EXISTS performance_profiles (
    profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Profile identification
    profile_name TEXT NOT NULL,
    profile_type TEXT,                     -- COMMAND, CIRCUIT, ROUTE, SYSCALL
    
    -- Measurements
    sample_count INTEGER DEFAULT 0,
    
    total_time_ms REAL DEFAULT 0.0,
    min_time_ms REAL,
    max_time_ms REAL,
    avg_time_ms REAL,
    stddev_time_ms REAL,
    
    -- Quantum-specific
    quantum_operations INTEGER DEFAULT 0,
    avg_qubits_used REAL,
    avg_gates_applied REAL,
    avg_fidelity REAL,
    
    -- Resource usage
    avg_memory_bytes INTEGER,
    peak_memory_bytes INTEGER,
    
    created_at REAL DEFAULT (julianday('now')),
    last_updated REAL DEFAULT (julianday('now'))
);

CREATE INDEX idx_prof_name ON performance_profiles(profile_name);
CREATE INDEX idx_prof_type ON performance_profiles(profile_type);

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 15: HELP SYSTEM & DOCUMENTATION
-- Man pages, examples, and interactive help
-- ═══════════════════════════════════════════════════════════════════════════

-- Man pages
CREATE TABLE IF NOT EXISTS man_pages (
    page_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Identification
    cmd_name TEXT NOT NULL,
    section INTEGER DEFAULT 1,             -- 1=commands, 2=syscalls, 3=library, etc.
    
    -- Content
    name_line TEXT,                        -- Short description
    synopsis TEXT,                         -- Usage syntax
    description TEXT,                      -- Detailed description
    options TEXT,                          -- Flag/option descriptions
    examples TEXT,                         -- Usage examples
    see_also TEXT,                         -- Related commands
    notes TEXT,                            -- Additional notes
    bugs TEXT,                             -- Known issues
    author TEXT,
    
    -- Quantum-specific
    quantum_requirements TEXT,             -- Qubit/EPR requirements
    quantum_algorithms TEXT,               -- Algorithms used
    
    -- Versioning
    version TEXT DEFAULT '1.0',
    
    created_at REAL DEFAULT (julianday('now')),
    last_updated REAL DEFAULT (julianday('now')),
    
    UNIQUE(cmd_name, section)
);

CREATE INDEX idx_man_cmd ON man_pages(cmd_name);
CREATE INDEX idx_man_section ON man_pages(section);

-- Command examples
CREATE TABLE IF NOT EXISTS command_examples (
    example_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    cmd_name TEXT NOT NULL,
    
    -- Example
    example_command TEXT NOT NULL,
    example_description TEXT,
    example_output TEXT,                   -- Expected output
    
    -- Context
    requires_setup TEXT,                   -- Prerequisites
    difficulty_level TEXT,                 -- BEGINNER, INTERMEDIATE, ADVANCED
    
    -- Tags
    tags TEXT,                             -- JSON: searchable tags
    
    -- Validation
    validated INTEGER DEFAULT 0,
    validation_date REAL,
    
    created_at REAL DEFAULT (julianday('now'))
);

CREATE INDEX idx_example_cmd ON command_examples(cmd_name);
CREATE INDEX idx_example_difficulty ON command_examples(difficulty_level);

-- Interactive tutorials
CREATE TABLE IF NOT EXISTS tutorials (
    tutorial_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    tutorial_name TEXT UNIQUE NOT NULL,
    tutorial_category TEXT,                -- BASICS, QUANTUM, FILESYSTEM, NETWORKING
    
    -- Content
    title TEXT NOT NULL,
    description TEXT,
    difficulty TEXT DEFAULT 'BEGINNER',
    estimated_time_minutes INTEGER,
    
    -- Steps
    steps TEXT NOT NULL,                   -- JSON: [{step: 1, instruction: '...', command: '...', validation: '...'}]
    
    -- Prerequisites
    required_knowledge TEXT,               -- JSON: list of concepts
    required_commands TEXT,                -- JSON: list of commands
    
    -- Progress tracking
    completion_count INTEGER DEFAULT 0,
    
    created_at REAL DEFAULT (julianday('now')),
    last_updated REAL DEFAULT (julianday('now'))
);

CREATE INDEX idx_tutorial_category ON tutorials(tutorial_category);
CREATE INDEX idx_tutorial_difficulty ON tutorials(difficulty);

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 16: CONFIGURATION & SYSTEM STATE
-- System-wide configuration and persistent state
-- ═══════════════════════════════════════════════════════════════════════════

-- System configuration
CREATE TABLE IF NOT EXISTS system_config (
    config_key TEXT PRIMARY KEY,
    
    config_value TEXT NOT NULL,
    config_type TEXT DEFAULT 'STRING',     -- STRING, INTEGER, FLOAT, BOOLEAN, JSON
    
    -- Metadata
    description TEXT,
    category TEXT,                         -- QUANTUM, FILESYSTEM, NETWORK, TERMINAL, etc.
    
    -- Constraints
    allowed_values TEXT,                   -- JSON: enumerated values
    min_value REAL,
    max_value REAL,
    
    -- Permissions
    requires_admin INTEGER DEFAULT 0,
    immutable INTEGER DEFAULT 0,
    
    -- Defaults
    default_value TEXT,
    
    updated_at REAL DEFAULT (julianday('now')),
    updated_by TEXT
);

CREATE INDEX idx_config_category ON system_config(category);

-- System state (runtime)
CREATE TABLE IF NOT EXISTS system_state (
    state_key TEXT PRIMARY KEY,
    
    state_value TEXT,
    state_type TEXT DEFAULT 'STRING',
    
    -- Persistence
    persistent INTEGER DEFAULT 0,          -- Survives restart
    
    updated_at REAL DEFAULT (julianday('now'))
);

-- Boot sequence log
CREATE TABLE IF NOT EXISTS boot_log (
    boot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Boot event
    event_type TEXT NOT NULL,              -- START, INIT_LATTICE, INIT_EPR, MOUNT_FS, START_BUS, etc.
    event_status TEXT,                     -- PENDING, SUCCESS, FAILED
    event_message TEXT,
    
    -- Timing
    event_start REAL,
    event_end REAL,
    event_duration_ms REAL,
    
    boot_session_id TEXT,
    
    timestamp REAL DEFAULT (julianday('now'))
);

CREATE INDEX idx_boot_session ON boot_log(boot_session_id);
CREATE INDEX idx_boot_event ON boot_log(event_type);

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 17: INTER-PROCESS COMMUNICATION
-- Pipes, message queues, shared memory
-- ═══════════════════════════════════════════════════════════════════════════

-- Pipes (for IPC)
CREATE TABLE IF NOT EXISTS ipc_pipes (
    pipe_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Pipe type
    pipe_type TEXT DEFAULT 'ANONYMOUS',    -- ANONYMOUS, NAMED
    pipe_name TEXT,                        -- For named pipes
    
    -- Endpoints
    reader_pid INTEGER,
    writer_pid INTEGER,
    
    -- Buffering
    buffer_size INTEGER DEFAULT 65536,
    current_buffer_usage INTEGER DEFAULT 0,
    
    -- State
    state TEXT DEFAULT 'OPEN',             -- OPEN, CLOSED
    
    -- Statistics
    bytes_written INTEGER DEFAULT 0,
    bytes_read INTEGER DEFAULT 0,
    
    created_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(reader_pid) REFERENCES processes(pid),
    FOREIGN KEY(writer_pid) REFERENCES processes(pid),
    CHECK(pipe_type IN ('ANONYMOUS', 'NAMED'))
);

CREATE INDEX idx_pipe_reader ON ipc_pipes(reader_pid);
CREATE INDEX idx_pipe_writer ON ipc_pipes(writer_pid);

-- Message queues
CREATE TABLE IF NOT EXISTS ipc_message_queues (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    queue_name TEXT UNIQUE,
    
    -- Owner
    owner_pid INTEGER,
    
    -- Configuration
    max_messages INTEGER DEFAULT 100,
    max_message_size INTEGER DEFAULT 8192,
    
    -- State
    current_message_count INTEGER DEFAULT 0,
    
    created_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(owner_pid) REFERENCES processes(pid)
);

-- Message queue contents
CREATE TABLE IF NOT EXISTS ipc_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    queue_id INTEGER NOT NULL,
    
    -- Message
    message_type INTEGER DEFAULT 0,
    message_data BLOB NOT NULL,
    message_size INTEGER,
    
    -- Priority
    priority INTEGER DEFAULT 0,
    
    -- Sender
    sender_pid INTEGER,
    
    -- Timing
    enqueued_at REAL DEFAULT (julianday('now')),
    expires_at REAL,
    
    FOREIGN KEY(queue_id) REFERENCES ipc_message_queues(queue_id) ON DELETE CASCADE,
    FOREIGN KEY(sender_pid) REFERENCES processes(pid)
);

CREATE INDEX idx_msg_queue ON ipc_messages(queue_id, priority DESC);

-- Shared memory segments
CREATE TABLE IF NOT EXISTS ipc_shared_memory (
    segment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    segment_name TEXT UNIQUE,
    
    -- Size
    segment_size INTEGER NOT NULL,
    
    -- Owner
    owner_pid INTEGER,
    
    -- Permissions
    permissions INTEGER DEFAULT 0666,
    
    -- Data (stored in DB for persistence)
    segment_data BLOB,
    
    -- Access control
    attached_pids TEXT,                    -- JSON: list of attached PIDs
    
    -- State
    marked_for_deletion INTEGER DEFAULT 0,
    
    created_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(owner_pid) REFERENCES processes(pid)
);

-- Semaphores
CREATE TABLE IF NOT EXISTS ipc_semaphores (
    semaphore_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    semaphore_name TEXT UNIQUE,
    
    -- Value
    current_value INTEGER DEFAULT 0,
    max_value INTEGER,
    
    -- Owner
    owner_pid INTEGER,
    
    -- Waiting queue
    waiting_pids TEXT,                     -- JSON: PIDs waiting on this semaphore
    
    created_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(owner_pid) REFERENCES processes(pid)
);

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 18: SECURITY & AUTHENTICATION
-- User management, permissions, quantum authentication
-- ═══════════════════════════════════════════════════════════════════════════

-- Users
CREATE TABLE IF NOT EXISTS users (
    uid INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- User identification
    username TEXT UNIQUE NOT NULL,
    full_name TEXT,
    
    -- Authentication
    password_hash BLOB,                    -- SHA256 + salt
    password_salt BLOB,
    
    -- Quantum authentication
    quantum_auth_enabled INTEGER DEFAULT 0,
    quantum_public_key BLOB,               -- Quantum key distribution
    entangled_qubits TEXT,                 -- JSON: qubit IDs for QKD
    
    -- Groups
    primary_gid INTEGER,
    supplementary_gids TEXT,               -- JSON: additional group IDs
    
    -- Home directory
    home_directory_inode INTEGER,
    
    -- Shell
    default_shell TEXT DEFAULT '/bin/qsh',
    
    -- Limits
    max_processes INTEGER DEFAULT 100,
    max_open_files INTEGER DEFAULT 1024,
    max_qubits_allocated INTEGER DEFAULT 1000,
    
    -- State
    account_enabled INTEGER DEFAULT 1,
    account_locked INTEGER DEFAULT 0,
    
    -- Audit
    last_login REAL,
    login_count INTEGER DEFAULT 0,
    failed_login_attempts INTEGER DEFAULT 0,
    
    created_at REAL DEFAULT (julianday('now')),
    
    FOREIGN KEY(home_directory_inode) REFERENCES filesystem_inodes(inode_id)
);

CREATE INDEX idx_user_username ON users(username);
CREATE INDEX idx_user_enabled ON users(account_enabled);

-- Groups
CREATE TABLE IF NOT EXISTS groups (
    gid INTEGER PRIMARY KEY AUTOINCREMENT,
    
    group_name TEXT UNIQUE NOT NULL,
    
    -- Members
    member_uids TEXT,                      -- JSON: list of user IDs
    
    -- Quantum resources
    quantum_resource_quota INTEGER,        -- Max qubits for group
    
    created_at REAL DEFAULT (julianday('now'))
);

-- Capabilities (fine-grained permissions)
CREATE TABLE IF NOT EXISTS capabilities (
    capability_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    capability_name TEXT UNIQUE NOT NULL,  -- CAP_QUANTUM_ADMIN, CAP_NET_ADMIN, etc.
    capability_description TEXT,
    
    -- Assignment
    granted_to_uids TEXT,                  -- JSON: user IDs
    granted_to_gids TEXT                   -- JSON: group IDs
);

-- Authentication sessions
CREATE TABLE IF NOT EXISTS auth_sessions (
    session_id TEXT PRIMARY KEY,
    
    uid INTEGER NOT NULL,
    
    -- Session type
    session_type TEXT,                     -- LOGIN, SSH, QUANTUM
    
    -- Quantum authentication (if used)
    quantum_challenge BLOB,
    quantum_response BLOB,
    qkd_key BLOB,
    bell_state_verified INTEGER DEFAULT 0,
    
    -- Timing
    created_at REAL DEFAULT (julianday('now')),
    expires_at REAL,
    last_activity REAL,
    
    -- State
    active INTEGER DEFAULT 1,
    
    FOREIGN KEY(uid) REFERENCES users(uid)
);

CREATE INDEX idx_auth_uid ON auth_sessions(uid);
CREATE INDEX idx_auth_active ON auth_sessions(active);

-- Audit log (security events)
CREATE TABLE IF NOT EXISTS security_audit_log (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Event
    event_type TEXT NOT NULL,              -- LOGIN, LOGOUT, AUTH_FAIL, PERMISSION_DENIED, etc.
    event_status TEXT,                     -- SUCCESS, FAILURE
    event_description TEXT,
    
    -- User context
    uid INTEGER,
    username TEXT,
    session_id TEXT,
    
    -- Resource
    resource_type TEXT,                    -- FILE, QUBIT, NETWORK, PROCESS
    resource_id TEXT,
    
    -- Source
    source_ip TEXT,
    source_interface TEXT,
    
    -- Severity
    severity TEXT DEFAULT 'INFO',          -- DEBUG, INFO, WARNING, CRITICAL
    
    timestamp REAL DEFAULT (julianday('now')),
    
    CHECK(severity IN ('DEBUG', 'INFO', 'WARNING', 'CRITICAL'))
);

CREATE INDEX idx_audit_event ON security_audit_log(event_type);
CREATE INDEX idx_audit_uid ON security_audit_log(uid);
CREATE INDEX idx_audit_time ON security_audit_log(timestamp);
CREATE INDEX idx_audit_severity ON security_audit_log(severity);

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 19: COMMAND PLACEHOLDERS
-- Comprehensive Unix command skeleton (200+ commands)
-- ═══════════════════════════════════════════════════════════════════════════

-- CORE COMMANDS
INSERT OR IGNORE INTO command_registry (cmd_name, cmd_category, cmd_description, cmd_opcode) VALUES
('help', 'CORE', 'Display help information', 0x01),
('man', 'CORE', 'Display manual pages', 0x02),
('info', 'CORE', 'Read info documents', 0x03),
('apropos', 'CORE', 'Search man page descriptions', 0x04),
('whatis', 'CORE', 'Display one-line command descriptions', 0x05);

-- FILESYSTEM COMMANDS
INSERT OR IGNORE INTO command_registry (cmd_name, cmd_category, cmd_description, cmd_opcode) VALUES
('ls', 'FILESYSTEM', 'List directory contents', 0x10),
('cd', 'FILESYSTEM', 'Change directory', 0x11),
('pwd', 'FILESYSTEM', 'Print working directory', 0x12),
('mkdir', 'FILESYSTEM', 'Make directories', 0x13),
('rmdir', 'FILESYSTEM', 'Remove empty directories', 0x14),
('rm', 'FILESYSTEM', 'Remove files or directories', 0x15),
('cp', 'FILESYSTEM', 'Copy files and directories', 0x16),
('mv', 'FILESYSTEM', 'Move or rename files', 0x17),
('touch', 'FILESYSTEM', 'Change file timestamps or create files', 0x18),
('cat', 'FILESYSTEM', 'Concatenate and display files', 0x19),
('more', 'FILESYSTEM', 'Page through file content', 0x1A),
('less', 'FILESYSTEM', 'Page through file content (enhanced)', 0x1B),
('head', 'FILESYSTEM', 'Output first part of files', 0x1C),
('tail', 'FILESYSTEM', 'Output last part of files', 0x1D),
('find', 'FILESYSTEM', 'Search for files', 0x1E),
('locate', 'FILESYSTEM', 'Find files by name', 0x1F),
('which', 'FILESYSTEM', 'Show full path of commands', 0x20),
('whereis', 'FILESYSTEM', 'Locate binary, source, and manual', 0x21),
('file', 'FILESYSTEM', 'Determine file type', 0x22),
('stat', 'FILESYSTEM', 'Display file status', 0x23),
('df', 'FILESYSTEM', 'Report filesystem disk space usage', 0x24),
('du', 'FILESYSTEM', 'Estimate file space usage', 0x25),
('mount', 'FILESYSTEM', 'Mount a filesystem', 0x26),
('umount', 'FILESYSTEM', 'Unmount a filesystem', 0x27),
('ln', 'FILESYSTEM', 'Create links between files', 0x28),
('readlink', 'FILESYSTEM', 'Display symbolic link target', 0x29),
('chmod', 'FILESYSTEM', 'Change file mode bits', 0x2A),
('chown', 'FILESYSTEM', 'Change file owner and group', 0x2B),
('chgrp', 'FILESYSTEM', 'Change group ownership', 0x2C);

-- TEXT PROCESSING
INSERT OR IGNORE INTO command_registry (cmd_name, cmd_category, cmd_description, cmd_opcode) VALUES
('grep', 'TEXT', 'Search text using patterns', 0x30),
('egrep', 'TEXT', 'Extended grep', 0x31),
('fgrep', 'TEXT', 'Fixed-string grep', 0x32),
('sed', 'TEXT', 'Stream editor', 0x33),
('awk', 'TEXT', 'Pattern scanning and processing', 0x34),
('cut', 'TEXT', 'Remove sections from lines', 0x35),
('paste', 'TEXT', 'Merge lines of files', 0x36),
('sort', 'TEXT', 'Sort lines of text', 0x37),
('uniq', 'TEXT', 'Report or omit repeated lines', 0x38),
('wc', 'TEXT', 'Word, line, character count', 0x39),
('tr', 'TEXT', 'Translate or delete characters', 0x3A),
('diff', 'TEXT', 'Compare files line by line', 0x3B),
('patch', 'TEXT', 'Apply diff file to original', 0x3C),
('comm', 'TEXT', 'Compare sorted files', 0x3D),
('join', 'TEXT', 'Join lines on common field', 0x3E),
('split', 'TEXT', 'Split file into pieces', 0x3F);

-- PROCESS MANAGEMENT
INSERT OR IGNORE INTO command_registry (cmd_name, cmd_category, cmd_description, cmd_opcode) VALUES
('ps', 'PROCESS', 'Report process status', 0x40),
('top', 'PROCESS', 'Display dynamic process view', 0x41),
('htop', 'PROCESS', 'Interactive process viewer', 0x42),
('kill', 'PROCESS', 'Send signal to process', 0x43),
('killall', 'PROCESS', 'Kill processes by name', 0x44),
('pkill', 'PROCESS', 'Signal processes by pattern', 0x45),
('pgrep', 'PROCESS', 'Find processes by pattern', 0x46),
('nice', 'PROCESS', 'Run with modified priority', 0x47),
('renice', 'PROCESS', 'Alter priority of running process', 0x48),
('jobs', 'PROCESS', 'List active jobs', 0x49),
('fg', 'PROCESS', 'Bring job to foreground', 0x4A),
('bg', 'PROCESS', 'Resume job in background', 0x4B),
('nohup', 'PROCESS', 'Run immune to hangups', 0x4C),
('screen', 'PROCESS', 'Terminal multiplexer', 0x4D),
('tmux', 'PROCESS', 'Terminal multiplexer (modern)', 0x4E);

-- NETWORKING
INSERT OR IGNORE INTO command_registry (cmd_name, cmd_category, cmd_description, cmd_opcode) VALUES
('ping', 'NETWORK', 'Send ICMP ECHO_REQUEST', 0x50),
('traceroute', 'NETWORK', 'Trace packet route', 0x51),
('netstat', 'NETWORK', 'Network statistics', 0x52),
('ss', 'NETWORK', 'Socket statistics', 0x53),
('ifconfig', 'NETWORK', 'Configure network interface', 0x54),
('ip', 'NETWORK', 'Network configuration tool', 0x55),
('route', 'NETWORK', 'Show/manipulate routing table', 0x56),
('arp', 'NETWORK', 'Manipulate ARP cache', 0x57),
('hostname', 'NETWORK', 'Show or set system hostname', 0x58),
('curl', 'NETWORK', 'Transfer data from URLs', 0x59),
('wget', 'NETWORK', 'Network downloader', 0x5A),
('nc', 'NETWORK', 'Netcat - networking utility', 0x5B),
('telnet', 'NETWORK', 'User interface to TELNET', 0x5C),
('ssh', 'NETWORK', 'Secure shell client', 0x5D),
('scp', 'NETWORK', 'Secure copy', 0x5E),
('rsync', 'NETWORK', 'Remote file sync', 0x5F);

-- SYSTEM INFORMATION
INSERT OR IGNORE INTO command_registry (cmd_name, cmd_category, cmd_description, cmd_opcode) VALUES
('uname', 'SYSTEM', 'Print system information', 0x60),
('uptime', 'SYSTEM', 'Show system uptime', 0x61),
('date', 'SYSTEM', 'Print or set system date/time', 0x62),
('cal', 'SYSTEM', 'Display calendar', 0x63),
('whoami', 'SYSTEM', 'Print effective user ID', 0x64),
('who', 'SYSTEM', 'Show who is logged on', 0x65),
('w', 'SYSTEM', 'Show who and what they are doing', 0x66),
('last', 'SYSTEM', 'Show last logins', 0x67),
('history', 'SYSTEM', 'Command history', 0x68),
('env', 'SYSTEM', 'Print environment variables', 0x69),
('export', 'SYSTEM', 'Set environment variable', 0x6A),
('alias', 'SYSTEM', 'Create command alias', 0x6B),
('unalias', 'SYSTEM', 'Remove alias', 0x6C);

-- ARCHIVE & COMPRESSION
INSERT OR IGNORE INTO command_registry (cmd_name, cmd_category, cmd_description, cmd_opcode) VALUES
('tar', 'ARCHIVE', 'Tape archiver', 0x70),
('gzip', 'ARCHIVE', 'Compress files', 0x71),
('gunzip', 'ARCHIVE', 'Decompress gzip files', 0x72),
('bzip2', 'ARCHIVE', 'Block-sorting compressor', 0x73),
('bunzip2', 'ARCHIVE', 'Decompress bzip2 files', 0x74),
('xz', 'ARCHIVE', 'XZ compression', 0x75),
('unxz', 'ARCHIVE', 'Decompress xz files', 0x76),
('zip', 'ARCHIVE', 'Package and compress files', 0x77),
('unzip', 'ARCHIVE', 'Extract compressed files', 0x78),
('compress', 'ARCHIVE', 'Compress files (legacy)', 0x79),
('uncompress', 'ARCHIVE', 'Decompress files (legacy)', 0x7A);

-- QUANTUM OPERATIONS
INSERT OR IGNORE INTO command_registry (cmd_name, cmd_category, cmd_description, cmd_opcode, requires_qubits) VALUES
('qh', 'QUANTUM', 'Apply Hadamard gate', 0x80, 1),
('qx', 'QUANTUM', 'Apply Pauli-X gate', 0x81, 1),
('qy', 'QUANTUM', 'Apply Pauli-Y gate', 0x82, 1),
('qz', 'QUANTUM', 'Apply Pauli-Z gate', 0x83, 1),
('qcnot', 'QUANTUM', 'Apply CNOT gate', 0x84, 1),
('qtoffoli', 'QUANTUM', 'Apply Toffoli gate', 0x85, 1),
('qswap', 'QUANTUM', 'Apply SWAP gate', 0x86, 1),
('qmeasure', 'QUANTUM', 'Measure qubit(s)', 0x87, 1),
('qreset', 'QUANTUM', 'Reset qubit to |0⟩', 0x88, 1),
('qentangle', 'QUANTUM', 'Create entanglement', 0x89, 1),
('qteleport', 'QUANTUM', 'Quantum teleportation', 0x8A, 1),
('qft', 'QUANTUM', 'Quantum Fourier Transform', 0x8B, 1),
('grover', 'QUANTUM', 'Grover search algorithm', 0x8C, 1),
('shor', 'QUANTUM', 'Shor factoring algorithm', 0x8D, 1),
('vqe', 'QUANTUM', 'Variational Quantum Eigensolver', 0x8E, 1),
('qaoa', 'QUANTUM', 'Quantum Approx Optimization', 0x8F, 1);

-- QUANTUM SYSTEM MANAGEMENT
INSERT OR IGNORE INTO command_registry (cmd_name, cmd_category, cmd_description, cmd_opcode) VALUES
('qalloc', 'QUANTUM_SYSTEM', 'Allocate qubits', 0x90),
('qfree', 'QUANTUM_SYSTEM', 'Free allocated qubits', 0x91),
('qstat', 'QUANTUM_SYSTEM', 'Qubit allocation status', 0x92),
('qpool', 'QUANTUM_SYSTEM', 'EPR pair pool status', 0x93),
('qroute', 'QUANTUM_SYSTEM', 'Show quantum routing table', 0x94),
('qlattice', 'QUANTUM_SYSTEM', 'Lattice point information', 0x95),
('qchannel', 'QUANTUM_SYSTEM', 'Quantum channel statistics', 0x96),
('qproof', 'QUANTUM_SYSTEM', 'Verify quantum proof', 0x97),
('qcircuit', 'QUANTUM_SYSTEM', 'Display quantum circuit', 0x98),
('qoptimize', 'QUANTUM_SYSTEM', 'Optimize quantum circuit', 0x99);

-- USER MANAGEMENT
INSERT OR IGNORE INTO command_registry (cmd_name, cmd_category, cmd_description, cmd_opcode) VALUES
('useradd', 'USER', 'Create new user', 0xA0),
('userdel', 'USER', 'Delete user', 0xA1),
('usermod', 'USER', 'Modify user account', 0xA2),
('passwd', 'USER', 'Change user password', 0xA3),
('groupadd', 'USER', 'Create new group', 0xA4),
('groupdel', 'USER', 'Delete group', 0xA5),
('groupmod', 'USER', 'Modify group', 0xA6),
('groups', 'USER', 'Print group memberships', 0xA7),
('id', 'USER', 'Print user identity', 0xA8),
('su', 'USER', 'Substitute user identity', 0xA9),
('sudo', 'USER', 'Execute as superuser', 0xAA);

-- SHELL BUILTINS
INSERT OR IGNORE INTO command_registry (cmd_name, cmd_category, cmd_description, cmd_opcode) VALUES
('echo', 'BUILTIN', 'Display text', 0xB0),
('printf', 'BUILTIN', 'Format and print data', 0xB1),
('test', 'BUILTIN', 'Evaluate conditional expression', 0xB2),
('true', 'BUILTIN', 'Return success', 0xB3),
('false', 'BUILTIN', 'Return failure', 0xB4),
('exit', 'BUILTIN', 'Exit shell', 0xB5),
('logout', 'BUILTIN', 'Logout from shell', 0xB6),
('source', 'BUILTIN', 'Execute commands from file', 0xB7),
('eval', 'BUILTIN', 'Evaluate expression', 0xB8),
('exec', 'BUILTIN', 'Replace shell with command', 0xB9),
('set', 'BUILTIN', 'Set shell options', 0xBA),
('unset', 'BUILTIN', 'Unset variables', 0xBB),
('read', 'BUILTIN', 'Read from input', 0xBC),
('shift', 'BUILTIN', 'Shift positional parameters', 0xBD);

-- MISCELLANEOUS
INSERT OR IGNORE INTO command_registry (cmd_name, cmd_category, cmd_description, cmd_opcode) VALUES
('clear', 'MISC', 'Clear terminal screen', 0xC0),
('reset', 'MISC', 'Reset terminal', 0xC1),
('tput', 'MISC', 'Terminal control', 0xC2),
('stty', 'MISC', 'Set terminal options', 0xC3),
('tty', 'MISC', 'Print terminal name', 0xC4),
('sleep', 'MISC', 'Delay for specified time', 0xC5),
('watch', 'MISC', 'Execute program periodically', 0xC6),
('time', 'MISC', 'Time command execution', 0xC7),
('timeout', 'MISC', 'Run with time limit', 0xC8),
('yes', 'MISC', 'Output string repeatedly', 0xC9),
('seq', 'MISC', 'Print numeric sequences', 0xCA),
('bc', 'MISC', 'Arbitrary precision calculator', 0xCB),
('expr', 'MISC', 'Evaluate expressions', 0xCD),
('factor', 'MISC', 'Factor integers', 0xCE),
('units', 'MISC', 'Unit conversion', 0xCF);

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 20: VIEWS AND TRIGGERS
-- Convenience views and automated maintenance
-- ═══════════════════════════════════════════════════════════════════════════

-- View: Complete system status
CREATE VIEW IF NOT EXISTS v_system_status AS
SELECT 
    (SELECT COUNT(*) FROM qubits WHERE allocated = 0) as free_qubits,
    (SELECT COUNT(*) FROM qubits WHERE allocated = 1) as allocated_qubits,
    (SELECT COUNT(*) FROM epr_pair_pool WHERE state = 'READY') as ready_epr_pairs,
    (SELECT COUNT(*) FROM processes WHERE state = 'RUNNING') as running_processes,
    (SELECT COUNT(*) FROM filesystem_inodes WHERE inode_type = 'f') as total_files,
    (SELECT COUNT(*) FROM network_connections WHERE state = 'ESTABLISHED') as active_connections,
    (SELECT active FROM mega_bus_core WHERE bus_id = 1) as bus_active,
    (SELECT COUNT(*) FROM terminal_sessions WHERE status = 'ACTIVE') as active_sessions;

-- View: Command execution summary
CREATE VIEW IF NOT EXISTS v_command_stats AS
SELECT 
    cmd_name,
    COUNT(*) as execution_count,
    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as error_count,
    AVG(execution_time_ms) as avg_execution_time_ms
,
    AVG(quantum_advantage) as avg_quantum_advantage,
    MAX(execution_time_ms) as max_execution_time_ms,
    MIN(execution_time_ms) as min_execution_time_ms
FROM command_execution_log
GROUP BY cmd_name;

-- View: Qubit health summary
CREATE VIEW IF NOT EXISTS v_qubit_health AS
SELECT 
    entanglement_type,
    COUNT(*) as count,
    AVG(fidelity) as avg_fidelity,
    AVG(error_rate) as avg_error_rate,
    SUM(total_gates_applied) as total_gates,
    SUM(total_measurements) as total_measurements,
    SUM(total_errors_corrected) as total_corrections
FROM qubits
GROUP BY entanglement_type;

-- View: EPR pool status
CREATE VIEW IF NOT EXISTS v_epr_pool_status AS
SELECT 
    state,
    COUNT(*) as pair_count,
    AVG(fidelity) as avg_fidelity,
    AVG(chsh_value) as avg_chsh,
    SUM(CASE WHEN bell_inequality_violated = 1 THEN 1 ELSE 0 END) as quantum_pairs
FROM epr_pair_pool
GROUP BY state;

-- View: Network interface summary
CREATE VIEW IF NOT EXISTS v_network_summary AS
SELECT 
    interface_name,
    interface_type,
    state,
    packets_sent,
    packets_received,
    bytes_sent,
    bytes_received,
    CASE 
        WHEN packets_sent > 0 THEN CAST(errors_send AS REAL) / packets_sent * 100 
        ELSE 0 
    END as send_error_rate
FROM network_interfaces;

-- View: Filesystem usage
CREATE VIEW IF NOT EXISTS v_filesystem_usage AS
SELECT 
    (SELECT total_blocks FROM filesystem_superblock WHERE fs_id = 1) as total_blocks,
    (SELECT free_blocks FROM filesystem_superblock WHERE fs_id = 1) as free_blocks,
    (SELECT total_inodes FROM filesystem_superblock WHERE fs_id = 1) as total_inodes,
    (SELECT free_inodes FROM filesystem_superblock WHERE fs_id = 1) as free_inodes,
    (SELECT COUNT(*) FROM filesystem_inodes WHERE inode_type = 'f') as file_count,
    (SELECT COUNT(*) FROM filesystem_inodes WHERE inode_type = 'd') as directory_count,
    (SELECT COUNT(*) FROM filesystem_inodes WHERE inode_type = 'l') as symlink_count;

-- View: Active quantum routes
CREATE VIEW IF NOT EXISTS v_active_routes AS
SELECT 
    r.route_id,
    r.src_j_address,
    r.dst_j_address,
    r.strategy,
    r.path_length,
    r.route_cost_sigma,
    r.use_count,
    r.last_used
FROM quantum_routing_table r
WHERE r.cache_valid = 1
ORDER BY r.use_count DESC;

-- View: Recent errors
CREATE VIEW IF NOT EXISTS v_recent_errors AS
SELECT 
    error_level,
    error_category,
    error_message,
    component,
    timestamp,
    resolved
FROM system_error_log
WHERE timestamp > julianday('now') - 1  -- Last 24 hours
ORDER BY timestamp DESC
LIMIT 100;

-- View: Process tree
CREATE VIEW IF NOT EXISTS v_process_tree AS
SELECT 
    p.pid,
    p.process_name,
    p.ppid,
    p.state,
    p.num_qubits_allocated,
    p.cpu_time_us,
    p.memory_usage_bytes,
    pp.process_name as parent_name
FROM processes p
LEFT JOIN processes pp ON p.ppid = pp.pid;

-- Trigger: Update last_updated on qubit state change
CREATE TRIGGER IF NOT EXISTS tr_qubit_state_update
AFTER UPDATE ON qubits
FOR EACH ROW
BEGIN
    UPDATE qubits SET last_updated = julianday('now') WHERE qubit_id = NEW.qubit_id;
END;

-- Trigger: Increment command use count
CREATE TRIGGER IF NOT EXISTS tr_command_use_increment
AFTER INSERT ON command_execution_log
FOR EACH ROW
BEGIN
    UPDATE command_registry 
    SET use_count = use_count + 1, last_used = julianday('now')
    WHERE cmd_name = NEW.cmd_name;
END;

-- Trigger: Update EPR pair last_used
CREATE TRIGGER IF NOT EXISTS tr_epr_usage_update
AFTER UPDATE OF state ON epr_pair_pool
FOR EACH ROW
WHEN NEW.state = 'ALLOCATED'
BEGIN
    UPDATE epr_pair_pool 
    SET last_used = julianday('now'), use_count = use_count + 1
    WHERE pair_id = NEW.pair_id;
END;

-- Trigger: Auto-refresh low-fidelity EPR pairs
CREATE TRIGGER IF NOT EXISTS tr_epr_auto_refresh
AFTER UPDATE OF fidelity ON epr_pair_pool
FOR EACH ROW
WHEN NEW.fidelity < NEW.refresh_threshold AND NEW.auto_refresh = 1
BEGIN
    UPDATE epr_pair_pool 
    SET state = 'REFRESHING'
    WHERE pair_id = NEW.pair_id;
END;

-- Trigger: Update filesystem superblock on inode changes
CREATE TRIGGER IF NOT EXISTS tr_fs_superblock_file_count
AFTER INSERT ON filesystem_inodes
FOR EACH ROW
BEGIN
    UPDATE filesystem_superblock
    SET files_total = files_total + CASE WHEN NEW.inode_type = 'f' THEN 1 ELSE 0 END,
        directories_total = directories_total + CASE WHEN NEW.inode_type = 'd' THEN 1 ELSE 0 END,
        symlinks_total = symlinks_total + CASE WHEN NEW.inode_type = 'l' THEN 1 ELSE 0 END,
        free_inodes = free_inodes - 1
    WHERE fs_id = 1;
END;

-- Trigger: Update filesystem superblock on inode deletion
CREATE TRIGGER IF NOT EXISTS tr_fs_superblock_file_delete
AFTER DELETE ON filesystem_inodes
FOR EACH ROW
BEGIN
    UPDATE filesystem_superblock
    SET files_total = files_total - CASE WHEN OLD.inode_type = 'f' THEN 1 ELSE 0 END,
        directories_total = directories_total - CASE WHEN OLD.inode_type = 'd' THEN 1 ELSE 0 END,
        symlinks_total = symlinks_total - CASE WHEN OLD.inode_type = 'l' THEN 1 ELSE 0 END,
        free_inodes = free_inodes + 1
    WHERE fs_id = 1;
END;

-- Trigger: Update process last_scheduled
CREATE TRIGGER IF NOT EXISTS tr_process_schedule_update
AFTER UPDATE OF state ON processes
FOR EACH ROW
WHEN NEW.state = 'RUNNING'
BEGIN
    UPDATE processes 
    SET last_scheduled = julianday('now')
    WHERE pid = NEW.pid;
END;

-- Trigger: Log security events on authentication
CREATE TRIGGER IF NOT EXISTS tr_auth_security_log
AFTER INSERT ON auth_sessions
FOR EACH ROW
BEGIN
    INSERT INTO security_audit_log (event_type, event_status, uid, session_id, severity)
    VALUES ('LOGIN', 'SUCCESS', NEW.uid, NEW.session_id, 'INFO');
END;

-- Trigger: Update terminal session activity
CREATE TRIGGER IF NOT EXISTS tr_terminal_activity_update
AFTER INSERT ON terminal_input
FOR EACH ROW
BEGIN
    UPDATE terminal_sessions 
    SET last_activity = julianday('now'),
        commands_executed = commands_executed + 1
    WHERE session_id = NEW.session_id;
END;

-- Trigger: Increment network interface stats
CREATE TRIGGER IF NOT EXISTS tr_network_stats_update
AFTER INSERT ON quantum_channel_packets
FOR EACH ROW
BEGIN
    UPDATE network_interfaces
    SET packets_sent = packets_sent + CASE WHEN NEW.direction = 'BUS_TO_CPU' THEN 1 ELSE 0 END,
        packets_received = packets_received + CASE WHEN NEW.direction = 'CPU_TO_BUS' THEN 1 ELSE 0 END,
        quantum_packets_sent = quantum_packets_sent + CASE WHEN NEW.direction = 'BUS_TO_CPU' THEN 1 ELSE 0 END,
        quantum_packets_received = quantum_packets_received + CASE WHEN NEW.direction = 'CPU_TO_BUS' THEN 1 ELSE 0 END
    WHERE interface_type = 'QUANTUM_NIC';
END;

-- Trigger: Update command handler statistics
CREATE TRIGGER IF NOT EXISTS tr_handler_stats_update
AFTER INSERT ON command_execution_log
FOR EACH ROW
BEGIN
    UPDATE command_handlers
    SET execution_count = execution_count + 1,
        success_count = success_count + CASE WHEN NEW.success = 1 THEN 1 ELSE 0 END,
        error_count = error_count + CASE WHEN NEW.success = 0 THEN 1 ELSE 0 END,
        avg_execution_ms = (avg_execution_ms * execution_count + COALESCE(NEW.execution_time_ms, 0)) / (execution_count + 1),
        last_executed = julianday('now')
    WHERE handler_id = NEW.handler_id;
END;

-- Trigger: Update routing table cache validity
CREATE TRIGGER IF NOT EXISTS tr_route_cache_invalidate
AFTER UPDATE OF lattice_path_used ON quantum_channel_packets
FOR EACH ROW
WHEN NEW.state = 'FAILED'
BEGIN
    UPDATE quantum_routing_table
    SET cache_valid = 0
    WHERE route_id = NEW.route_id;
END;

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 21: INITIALIZATION DATA
-- Bootstrap data for immediate system operability
-- ═══════════════════════════════════════════════════════════════════════════

-- Initialize filesystem superblock
INSERT OR IGNORE INTO filesystem_superblock (fs_id, total_blocks, free_blocks, total_inodes, free_inodes)
VALUES (1, 1000000, 999999, 1000000, 999999);

-- Create root inode
INSERT OR IGNORE INTO filesystem_inodes (inode_id, inode_type, mode, uid, gid, nlink, atime, mtime, ctime, crtime)
VALUES (1, 'd', 0755, 0, 0, 2, julianday('now'), julianday('now'), julianday('now'), julianday('now'));

-- Create root directory entries (. and ..)
INSERT OR IGNORE INTO filesystem_dentries (parent_inode, child_inode, name, file_type)
VALUES 
(1, 1, '.', 'd'),
(1, 1, '..', 'd');

-- Initialize mega bus
INSERT OR IGNORE INTO mega_bus_core (bus_id, epr_pool_start_address, epr_pool_end_address, epr_pool_size)
VALUES (1, X'0000000000000000', X'00000000000003FF', 1024);

-- Create default user (root)
INSERT OR IGNORE INTO users (uid, username, full_name, primary_gid, home_directory_inode)
VALUES (0, 'root', 'System Administrator', 0, 1);

-- Create default groups
INSERT OR IGNORE INTO groups (gid, group_name)
VALUES 
(0, 'root'),
(1, 'wheel'),
(2, 'users'),
(3, 'quantum');

-- Initialize loopback network interface
INSERT OR IGNORE INTO network_interfaces (interface_name, interface_type, state, ip_address, netmask)
VALUES ('lo', 'LOOPBACK', 'UP', '127.0.0.1', '255.0.0.0');

-- System configuration defaults
INSERT OR IGNORE INTO system_config (config_key, config_value, config_type, category, description) VALUES
('system.hostname', 'qunix-system', 'STRING', 'SYSTEM', 'System hostname'),
('system.timezone', 'UTC', 'STRING', 'SYSTEM', 'System timezone'),
('quantum.max_qubits_per_process', '1000', 'INTEGER', 'QUANTUM', 'Maximum qubits per process'),
('quantum.epr_pool_target_size', '1024', 'INTEGER', 'QUANTUM', 'Target EPR pool size'),
('quantum.auto_refresh_threshold', '0.95', 'FLOAT', 'QUANTUM', 'Auto-refresh fidelity threshold'),
('filesystem.max_open_files', '65536', 'INTEGER', 'FILESYSTEM', 'Maximum open file descriptors'),
('network.tcp_timeout', '30', 'INTEGER', 'NETWORK', 'TCP connection timeout (seconds)'),
('terminal.history_size', '1000', 'INTEGER', 'TERMINAL', 'Command history size'),
('terminal.default_shell', '/bin/qsh', 'STRING', 'TERMINAL', 'Default shell'),
('security.password_min_length', '8', 'INTEGER', 'SECURITY', 'Minimum password length'),
('security.max_login_attempts', '3', 'INTEGER', 'SECURITY', 'Max failed login attempts'),
('bus.heartbeat_interval', '5.0', 'FLOAT', 'QUANTUM', 'Bus heartbeat interval (seconds)'),
('bus.default_routing_strategy', 'HYPERBOLIC_LOCAL', 'STRING', 'QUANTUM', 'Default routing strategy'),
('golay.error_correction_enabled', '1', 'BOOLEAN', 'QUANTUM', 'Enable Golay error correction');

-- Create standard command groups
INSERT OR IGNORE INTO command_groups (group_name, group_description) VALUES
('file_operations', 'File and directory operations'),
('text_processing', 'Text manipulation and processing'),
('process_management', 'Process control and monitoring'),
('network_utilities', 'Network tools and diagnostics'),
('quantum_gates', 'Quantum gate operations'),
('quantum_algorithms', 'Quantum algorithms'),
('system_administration', 'System administration tools'),
('user_management', 'User and group management'),
('shell_builtins', 'Shell built-in commands'),
('archive_tools', 'Archive and compression utilities');

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 22: COMPATIBILITY VIEWS (for legacy table names)
-- Maintains backward compatibility with existing scripts
-- ═══════════════════════════════════════════════════════════════════════════

-- Legacy lattice view
CREATE VIEW IF NOT EXISTS l AS
SELECT 
    point_id as i,
    coords_24d as c,
    norm_squared as n,
    e8_sublattice as e,
    j_invariant_real as j,
    j_invariant_imag as ji,
    poincare_x as x,
    poincare_y as y,
    allocated
FROM leech_lattice;

-- Legacy qubit view
CREATE VIEW IF NOT EXISTS q AS
SELECT 
    qubit_id as i,
    lattice_point_id as l,
    'p' as t,
    amplitude_alpha_real as a,
    amplitude_beta_real as b,
    global_phase as p,
    entangled as e,
    j_invariant_real as j,
    j_invariant_imag as ji,
    poincare_x as x,
    poincare_y as y,
    measurement_count as m,
    entanglement_type as g,
    fidelity as s,
    entanglement_partners as entw,
    entanglement_type as etype
FROM qubits;

-- Legacy triangle view
CREATE VIEW IF NOT EXISTS tri AS
SELECT 
    triangle_id as tid,
    triangle_id as i,
    qubit_v0 as v0,
    qubit_v1 as v1,
    qubit_v2 as v2,
    qubit_v3 as v3,
    amplitudes as w,
    statevector as sv,
    next_triangle as n,
    prev_triangle as p
FROM w_state_triangles;

-- Legacy EPR view
CREATE VIEW IF NOT EXISTS e AS
SELECT 
    qubit_a_id as a,
    qubit_b_id as b,
    'e' as t,
    fidelity as s
FROM epr_pair_pool
WHERE state = 'READY';

-- Legacy process view
CREATE VIEW IF NOT EXISTS pqb AS
SELECT * FROM qubits WHERE qubit_id < 16777216;

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 23: PERFORMANCE INDICES
-- Additional indices for optimal query performance
-- ═══════════════════════════════════════════════════════════════════════════

-- Command system indices
CREATE INDEX IF NOT EXISTS idx_cmd_exec_session_time ON command_execution_log(session_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_cmd_exec_success_time ON command_execution_log(success, timestamp);
CREATE INDEX IF NOT EXISTS idx_cmd_handler_cmd_priority ON command_handlers(cmd_id, priority DESC, enabled);

-- Quantum channel indices
CREATE INDEX IF NOT EXISTS idx_qcp_pending ON quantum_channel_packets(state, direction) WHERE state = 'PENDING';
CREATE INDEX IF NOT EXISTS idx_qcp_chsh ON quantum_channel_packets(chsh_value) WHERE bell_inequality_violated = 1;

-- Filesystem indices
CREATE INDEX IF NOT EXISTS idx_fs_inode_parent ON filesystem_dentries(parent_inode, name);
CREATE INDEX IF NOT EXISTS idx_fs_block_inode_index ON filesystem_blocks(inode_id, block_index);
CREATE INDEX IF NOT EXISTS idx_fs_quantum_encoded ON filesystem_inodes(quantum_encoded) WHERE quantum_encoded = 1;

-- Process indices
CREATE INDEX IF NOT EXISTS idx_process_running ON processes(state, priority DESC) WHERE state = 'RUNNING';
CREATE INDEX IF NOT EXISTS idx_process_quantum_ctx ON process_quantum_contexts(pid);

-- Network indices
CREATE INDEX IF NOT EXISTS idx_net_conn_active ON network_connections(state, protocol) WHERE state = 'ESTABLISHED';
CREATE INDEX IF NOT EXISTS idx_net_iface_active ON network_interfaces(state) WHERE state = 'UP';

-- Routing indices
CREATE INDEX IF NOT EXISTS idx_route_j_src_dst ON quantum_routing_table(src_j_address, dst_j_address, cache_valid);
CREATE INDEX IF NOT EXISTS idx_route_strategy_cost ON quantum_routing_table(strategy, route_cost_sigma);

-- Security indices
CREATE INDEX IF NOT EXISTS idx_auth_session_active ON auth_sessions(uid, active) WHERE active = 1;
CREATE INDEX IF NOT EXISTS idx_security_audit_critical ON security_audit_log(severity, timestamp) WHERE severity = 'CRITICAL';

-- EPR pool indices
CREATE INDEX IF NOT EXISTS idx_epr_ready_fidelity ON epr_pair_pool(state, fidelity DESC) WHERE state = 'READY';
CREATE INDEX IF NOT EXISTS idx_epr_heartbeat_due ON epr_heartbeat_schedule(enabled, next_heartbeat) WHERE enabled = 1;

-- Golay indices
CREATE INDEX IF NOT EXISTS idx_golay_octad_positions ON golay_octads(octad_id, used_in_leech_type2);
CREATE INDEX IF NOT EXISTS idx_golay_syndrome_weight ON golay_syndrome_table(error_weight, correctable);

-- Metrics indices
CREATE INDEX IF NOT EXISTS idx_metric_cat_time ON system_metrics(metric_category, timestamp);
CREATE INDEX IF NOT EXISTS idx_health_fail ON system_health_checks(status, timestamp) WHERE status IN ('FAIL', 'WARN');

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 24: MAINTENANCE PROCEDURES (stored as system config)
-- ═══════════════════════════════════════════════════════════════════════════

-- Vacuum tunnel maintenance schedule
CREATE TABLE IF NOT EXISTS maintenance_schedule (
    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    task_name TEXT UNIQUE NOT NULL,
    task_type TEXT NOT NULL,               -- VACUUM, ANALYZE, CLEANUP, OPTIMIZE, HEARTBEAT
    
    -- Frequency
    interval_seconds REAL NOT NULL,
    next_run REAL,
    last_run REAL,
    
    -- Target
    target_table TEXT,                     -- Which table/component
    target_component TEXT,
    
    -- Parameters
    task_parameters TEXT,                  -- JSON: task-specific params
    
    -- Status
    enabled INTEGER DEFAULT 1,
    running INTEGER DEFAULT 0,
    
    -- Statistics
    run_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    avg_duration_ms REAL,
    last_error TEXT,
    
    created_at REAL DEFAULT (julianday('now'))
);

-- Insert default maintenance tasks
INSERT OR IGNORE INTO maintenance_schedule (task_name, task_type, interval_seconds, next_run, target_component) VALUES
('epr_heartbeat', 'HEARTBEAT', 10.0, julianday('now'), 'epr_pair_pool'),
('quantum_channel_cleanup', 'CLEANUP', 300.0, julianday('now'), 'quantum_channel_packets'),
('routing_cache_refresh', 'OPTIMIZE', 600.0, julianday('now'), 'quantum_routing_table'),
('filesystem_defrag', 'OPTIMIZE', 3600.0, julianday('now'), 'filesystem_blocks'),
('metrics_aggregation', 'CLEANUP', 60.0, julianday('now'), 'system_metrics'),
('health_check_all', 'VACUUM', 30.0, julianday('now'), 'system'),
('qubit_coherence_check', 'VACUUM', 120.0, julianday('now'), 'qubits'),
('process_zombie_cleanup', 'CLEANUP', 60.0, julianday('now'), 'processes'),
('terminal_session_timeout', 'CLEANUP', 300.0, julianday('now'), 'terminal_sessions'),
('auth_session_expiry', 'CLEANUP', 600.0, julianday('now'), 'auth_sessions');

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 25: FINAL SCHEMA METADATA
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS schema_metadata (
    metadata_key TEXT PRIMARY KEY,
    metadata_value TEXT,
    updated_at REAL DEFAULT (julianday('now'))
);

INSERT OR REPLACE INTO schema_metadata (metadata_key, metadata_value) VALUES
('schema_version', '1.0.0'),
('schema_name', 'QUNIX_COMPLETE_v1'),
('schema_size_kb', '120'),
('total_tables', '120'),
('total_views', '12'),
('total_triggers', '15'),
('total_indices', '150'),
('database_type', 'UNIFIED_QUANTUM_UNIX'),
('lattice_points', '196560'),
('max_qubits', '196560'),
('epr_pool_size', '1024'),
('golay_codewords', '4096'),
('golay_octads', '759'),
('command_count', '200'),
('build_date', datetime('now')),
('architecture', 'MEGA_BUS_CPU_UNIFIED'),
('quantum_enabled', '1'),
('filesystem_enabled', '1'),
('networking_enabled', '1'),
('security_enabled', '1'),
('superdense_encoding', '1'),
('error_correction', 'GOLAY_G24'),
('routing_strategies', 'HYPERBOLIC,KLEIN_BRIDGE,EPR_TELEPORT,W_STATE_CHAIN'),
('manifold_bridging', 'KLEIN_BOTTLE'),
('vacuum_tunneling', 'ENABLED');

-- ═══════════════════════════════════════════════════════════════════════════
-- END OF SCHEMA v1.0.0
-- Total Size: ~135 KB of pure SQL schema
-- Tables: 120+
-- Views: 12
-- Triggers: 15+
-- Indices: 150+
-- Commands: 200+
-- 
-- This schema provides:
-- ✓ Complete Unix command skeleton (200+ commands)
-- ✓ Quantum substrate (Leech lattice, qubits, entanglement)
-- ✓ EPR pair pool (0x00000000 address space, 1024 pairs)
-- ✓ Mega Bus unified routing engine
-- ✓ Binary transmission protocol (superdense coding)
-- ✓ Complete filesystem (VFS with external mounting)
-- ✓ Process management (Unix-style)
-- ✓ Terminal I/O subsystem
-- ✓ Network stack (classical + quantum NIC)
-- ✓ Security & authentication
-- ✓ Golay G24 error correction (hardcoded)
-- ✓ Klein bottle manifold bridging
-- ✓ Vacuum tunneling for cross-manifold access
-- ✓ Help system & documentation
-- ✓ System monitoring & health checks
-- ✓ IPC mechanisms (pipes, message queues, shared memory)
-- ✓ Comprehensive audit trail
-- ✓ Self-maintenance automation
-- ✓ Backward compatibility views
-- ═══════════════════════════════════════════════════════════════════════════

-- Verify schema integrity
PRAGMA foreign_key_check;
PRAGMA integrity_check;

-- Optimize database
ANALYZE;
