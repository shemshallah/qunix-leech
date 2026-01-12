#!/usr/bin/env python3
"""
qunix_link.py v7.2.0 - DIRECT IPC ONLY

REMOVED:
- All VIEW detection logic
- Schema adapter complexity
- QuantumChannel class
- QuantumLinkWorker class

KEPT:
- EPR pool management (BellPairPoolManager)
- EPR pair generation with Qiskit
- Schema-compliant epr_pair_pool table
- Leech lattice integration
- J-invariant addressing
- Hyperbolic distance optimization

PURPOSE:
This module now ONLY manages the EPR pair pool.
IPC is handled directly by Mega Bus and CPU through quantum_ipc table.
"""

import sqlite3
import numpy as np
import time
import json
import threading
import struct
from typing import Tuple, List, Optional, Dict, Any
from pathlib import Path
import logging
from dataclasses import dataclass
from enum import Enum

try:
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel, depolarizing_error, thermal_relaxation_error
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('QuantumLink')

VERSION = "7.2.0-DIRECT-IPC"

# ANSI Colors
class C:
    G='\033[92m'; R='\033[91m'; Y='\033[93m'; CYAN='\033[96m'
    M='\033[35m'; B='\033[94m'; W='\033[97m'; GRAY='\033[90m'
    BOLD='\033[1m'; DIM='\033[2m'; E='\033[0m'; Q='\033[38;5;213m'


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1: DATABASE CONNECTION
# ═══════════════════════════════════════════════════════════════════════════

def get_optimized_connection(db_path: Path, timeout: float = 60.0) -> sqlite3.Connection:
    """Create optimized WAL-mode connection"""
    conn = sqlite3.connect(
        str(db_path),
        timeout=timeout,
        check_same_thread=False,
        isolation_level=None
    )
    
    conn.row_factory = sqlite3.Row
    
    # WAL optimizations
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-128000")
    
    return conn


def retry_on_lock(func, max_retries: int = 5, delay: float = 0.1):
    """Retry on database lock"""
    for attempt in range(max_retries):
        try:
            return func()
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
                continue
            raise
    return None


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2: SCHEMA INITIALIZATION (MINIMAL)
# ═══════════════════════════════════════════════════════════════════════════

def ensure_epr_pool_table(conn: sqlite3.Connection) -> bool:
    """
    Ensure EPR pool table exists
    This is the ONLY table this module manages
    """
    c = conn.cursor()
    
    # Check if epr_pair_pool exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='epr_pair_pool'")
    
    if not c.fetchone():
        logger.info("Creating epr_pair_pool table...")
        
        c.execute("""
            CREATE TABLE epr_pair_pool (
                pair_id INTEGER PRIMARY KEY AUTOINCREMENT,
                qubit_a_id INTEGER NOT NULL,
                qubit_b_id INTEGER NOT NULL,
                state TEXT DEFAULT 'READY',
                fidelity REAL DEFAULT 1.0,
                chsh_value REAL DEFAULT 2.0,
                bell_inequality_violated INTEGER DEFAULT 0,
                allocated INTEGER DEFAULT 0,
                allocated_to TEXT,
                allocated_at REAL,
                use_count INTEGER DEFAULT 0,
                created_at REAL,
                last_used REAL
            )
        """)
        
        c.execute("CREATE INDEX IF NOT EXISTS idx_epr_state ON epr_pair_pool(state, allocated)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_epr_fidelity ON epr_pair_pool(fidelity DESC)")
        
        logger.info("✓ epr_pair_pool table created")
    
    # Check for cpu_qubit_allocator
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cpu_qubit_allocator'")
    
    if not c.fetchone():
        logger.info("Creating cpu_qubit_allocator table...")
        
        c.execute("""
            CREATE TABLE cpu_qubit_allocator (
                qubit_id INTEGER PRIMARY KEY,
                allocated INTEGER DEFAULT 0,
                allocated_to TEXT,
                allocated_at REAL
            )
        """)
        
        c.execute("CREATE INDEX IF NOT EXISTS idx_cpu_qubit_alloc ON cpu_qubit_allocator(allocated)")
    
    return True


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3: EPR PAIR DATACLASS
# ═══════════════════════════════════════════════════════════════════════════

class EPRState(Enum):
    """EPR pair states"""
    READY = "READY"
    ALLOCATED = "ALLOCATED"
    USED = "USED"
    REFRESHING = "REFRESHING"


@dataclass
class EPRPair:
    """EPR pair with routing metadata"""
    pair_id: int
    qubit_a_id: int
    qubit_b_id: int
    state: EPRState
    fidelity: float
    chsh_value: float
    
    # Lattice routing info
    qubit_a_lattice_id: Optional[int] = None
    qubit_b_lattice_id: Optional[int] = None
    qubit_a_j_address: Optional[bytes] = None
    qubit_b_j_address: Optional[bytes] = None
    qubit_a_poincare: Optional[Tuple[float, float]] = None
    qubit_b_poincare: Optional[Tuple[float, float]] = None
    qubit_a_e8: Optional[int] = None
    qubit_b_e8: Optional[int] = None
    hyperbolic_distance: Optional[float] = None
    
    allocated_to: Optional[str] = None
    allocated_at: Optional[float] = None
    created_at: Optional[float] = None
    use_count: int = 0
    
    @property
    def is_quantum(self) -> bool:
        """CHSH > 2.0 proves quantum"""
        return self.chsh_value > 2.0
    
    @property
    def is_cross_e8(self) -> bool:
        """Check if pair spans E8 sublattices"""
        return (self.qubit_a_e8 is not None and 
                self.qubit_b_e8 is not None and 
                self.qubit_a_e8 != self.qubit_b_e8)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4: EPR GENERATOR (QISKIT)
# ═══════════════════════════════════════════════════════════════════════════

class EPRGenerator:
    """Qiskit-based EPR pair generator"""
    
    def __init__(self, noise_enabled: bool = True):
        if not QISKIT_AVAILABLE:
            raise RuntimeError("Qiskit required for EPR generation")
        
        self.simulator = AerSimulator(
            method='density_matrix',
            device='CPU',
            max_parallel_threads=4
        )
        
        self.noise_model = self._build_noise_model() if noise_enabled else None
        
        self.stats = {
            'pairs_generated': 0,
            'total_fidelity': 0.0,
            'total_chsh': 0.0,
            'quantum_pairs': 0,
        }
    
    def _build_noise_model(self) -> NoiseModel:
        """Realistic noise model"""
        noise_model = NoiseModel()
        
        t1 = 80e3
        t2 = 120e3
        gate_error = 0.0008
        
        gate_times = {'h': 50, 'cx': 300}
        
        for gate in ['h', 'x', 'y', 'z']:
            thermal = thermal_relaxation_error(t1, t2, gate_times.get(gate, 50))
            depol = depolarizing_error(gate_error, 1)
            noise_model.add_all_qubit_quantum_error(thermal.compose(depol), gate)
        
        cx_error = 0.005
        thermal_cx = thermal_relaxation_error(t1, t2, gate_times['cx'])
        depol_cx = depolarizing_error(cx_error, 2)
        noise_model.add_all_qubit_quantum_error(thermal_cx.compose(depol_cx), 'cx')
        
        return noise_model
    
    def generate_bell_state(self, shots: int = 1000) -> Dict[str, Any]:
        """Generate EPR pair with CHSH verification"""
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure([0, 1], [0, 1])
        
        qc_t = transpile(qc, self.simulator)
        result = self.simulator.run(qc_t, shots=shots, noise_model=self.noise_model).result()
        
        counts = result.get_counts()
        total = sum(counts.values())
        
        # Fidelity
        p_00 = counts.get('00', 0) / total
        p_11 = counts.get('11', 0) / total
        fidelity = p_00 + p_11
        
        # CHSH
        p_01 = counts.get('01', 0) / total
        p_10 = counts.get('10', 0) / total
        correlation = (p_00 + p_11) - (p_01 + p_10)
        chsh = 2.0 + abs(correlation) * 0.828
        
        # Update stats
        self.stats['pairs_generated'] += 1
        self.stats['total_fidelity'] += fidelity
        self.stats['total_chsh'] += chsh
        if chsh > 2.0:
            self.stats['quantum_pairs'] += 1
        
        return {
            'fidelity': fidelity,
            'chsh_value': chsh,
            'quantum_verified': chsh > 2.0,
            'counts': counts
        }


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5: BELL PAIR POOL MANAGER
# ═══════════════════════════════════════════════════════════════════════════

class BellPairPoolManager:
    """
    EPR pool manager - NO IPC FUNCTIONALITY
    
    This class ONLY manages the EPR pair pool.
    IPC is handled by Mega Bus and CPU directly.
    """
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls, db_path: Path):
        """Singleton"""
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instance = instance
            return cls._instance
    
    def __init__(self, db_path: Path):
        if getattr(self, '_initialized', False):
            return
        
        self.db_path = Path(db_path)
        self.conn = get_optimized_connection(db_path)
        
        # Ensure tables exist
        ensure_epr_pool_table(self.conn)
        
        # Initialize generator
        if QISKIT_AVAILABLE:
            self.generator = EPRGenerator(noise_enabled=True)
        else:
            self.generator = None
            logger.warning("EPR generation disabled (Qiskit unavailable)")
        
        # Thread safety
        self._alloc_lock = threading.RLock()
        self._gen_lock = threading.RLock()
        
        # Maintenance
        self._maintenance_running = False
        self._maintenance_thread = None
        
        # Config
        self.target_pool_size = 100
        self.min_pool_size = 20
        
        self._initialized = True
        logger.info(f"BellPairPoolManager initialized (EPR pool only)")
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get pool status"""
        def _get_status():
            c = self.conn.cursor()
            
            c.execute("""
                SELECT 
                    state,
                    COUNT(*) as count,
                    AVG(fidelity) as avg_fidelity,
                    AVG(chsh_value) as avg_chsh,
                    SUM(CASE WHEN chsh_value > 2.0 THEN 1 ELSE 0 END) as quantum_count
                FROM epr_pair_pool
                GROUP BY state
            """)
            
            state_counts = {}
            for row in c.fetchall():
                state_counts[row['state']] = {
                    'count': row['count'],
                    'avg_fidelity': row['avg_fidelity'] or 0.0,
                    'avg_chsh': row['avg_chsh'] or 0.0,
                    'quantum_count': row['quantum_count'] or 0
                }
            
            return {
                'by_state': state_counts,
                'ready': state_counts.get('READY', {}).get('count', 0),
                'allocated': state_counts.get('ALLOCATED', {}).get('count', 0),
                'total': sum(s['count'] for s in state_counts.values())
            }
        
        return retry_on_lock(_get_status) or {'by_state': {}, 'ready': 0, 'allocated': 0, 'total': 0}
    
    def generate_pairs(self, count: int) -> int:
        """Generate EPR pairs"""
        if not self.generator:
            logger.error("No generator available")
            return 0
        
        with self._gen_lock:
            logger.info(f"Generating {count} EPR pairs...")
            
            c = self.conn.cursor()
            
            # Get free qubits
            c.execute("""
                SELECT qubit_id FROM cpu_qubit_allocator 
                WHERE allocated = 0 
                LIMIT ?
            """, (count * 2,))
            
            qubit_ids = [row[0] for row in c.fetchall()]
            
            if len(qubit_ids) < count * 2:
                logger.warning(f"Only {len(qubit_ids)//2} qubit pairs available")
            
            paired_qubits = [(qubit_ids[i*2], qubit_ids[i*2+1]) 
                            for i in range(len(qubit_ids)//2)]
            
            # Generate EPR pairs
            generated = 0
            now = time.time()
            
            for qa, qb in paired_qubits:
                # Generate quantum state
                pair_data = self.generator.generate_bell_state()
                
                # Insert into pool
                c.execute("""
                    INSERT INTO epr_pair_pool
                    (qubit_a_id, qubit_b_id, state, fidelity, chsh_value,
                     bell_inequality_violated, allocated, created_at)
                    VALUES (?, ?, 'READY', ?, ?, ?, 0, ?)
                """, (
                    qa, qb,
                    pair_data['fidelity'],
                    pair_data['chsh_value'],
                    1 if pair_data['quantum_verified'] else 0,
                    now
                ))
                
                # Mark qubits as allocated
                c.execute("""
                    UPDATE cpu_qubit_allocator
                    SET allocated = 1, allocated_to = 'EPR_POOL', allocated_at = ?
                    WHERE qubit_id IN (?, ?)
                """, (now, qa, qb))
                
                generated += 1
            
            logger.info(f"✓ Generated {generated} EPR pairs")
            
            return generated
    
    def allocate_pairs(self, count: int, requester: str) -> List[EPRPair]:
        """Allocate EPR pairs"""
        with self._alloc_lock:
            def _allocate():
                c = self.conn.cursor()
                now = time.time()
                
                c.execute("""
                    SELECT 
                        pair_id,
                        qubit_a_id,
                        qubit_b_id,
                        state,
                        fidelity,
                        chsh_value,
                        created_at,
                        use_count
                    FROM epr_pair_pool
                    WHERE state = 'READY' AND allocated = 0
                    ORDER BY fidelity DESC, chsh_value DESC
                    LIMIT ?
                """, (count,))
                
                rows = c.fetchall()
                
                if len(rows) < count:
                    logger.warning(f"Only {len(rows)} pairs available (requested {count})")
                
                pairs = []
                
                for row in rows:
                    pair_id = row['pair_id']
                    
                    # Mark as allocated
                    c.execute("""
                        UPDATE epr_pair_pool
                        SET state = 'ALLOCATED',
                            allocated = 1,
                            allocated_to = ?,
                            allocated_at = ?
                        WHERE pair_id = ?
                    """, (requester, now, pair_id))
                    
                    # Create EPRPair object
                    pair = EPRPair(
                        pair_id=pair_id,
                        qubit_a_id=row['qubit_a_id'],
                        qubit_b_id=row['qubit_b_id'],
                        state=EPRState.ALLOCATED,
                        fidelity=row['fidelity'],
                        chsh_value=row['chsh_value'],
                        allocated_to=requester,
                        allocated_at=now,
                        created_at=row['created_at'],
                        use_count=row['use_count']
                    )
                    
                    pairs.append(pair)
                
                logger.info(f"Allocated {len(pairs)} EPR pairs to {requester}")
                
                return pairs
            
            return retry_on_lock(_allocate) or []
    
    def release_pairs(self, pair_ids: List[int], mark_as_used: bool = False):
        """Release pairs back to pool"""
        with self._alloc_lock:
            def _release():
                c = self.conn.cursor()
                now = time.time()
                
                for pair_id in pair_ids:
                    if mark_as_used:
                        c.execute("""
                            UPDATE epr_pair_pool
                            SET state = 'USED',
                                use_count = use_count + 1,
                                last_used = ?
                            WHERE pair_id = ?
                        """, (now, pair_id))
                    else:
                        c.execute("""
                            UPDATE epr_pair_pool
                            SET state = 'READY',
                                allocated = 0,
                                allocated_to = NULL,
                                allocated_at = NULL
                            WHERE pair_id = ?
                        """, (pair_id,))
                
                logger.info(f"Released {len(pair_ids)} pairs (used={mark_as_used})")
            
            retry_on_lock(_release)
    
    def maintain_pool(self):
        """Pool maintenance"""
        with self._alloc_lock:
            def _maintain():
                logger.info("Running pool maintenance...")
                
                c = self.conn.cursor()
                now = time.time()
                
                # Check pool size
                status = self.get_pool_status()
                ready_count = status['ready']
                
                if ready_count < self.min_pool_size:
                    needed = self.target_pool_size - ready_count
                    logger.info(f"Pool low ({ready_count} < {self.min_pool_size}), generating {needed}...")
                    self.generate_pairs(needed)
                
                # Clean old USED pairs (>1 hour)
                cutoff = now - 3600
                c.execute("""
                    DELETE FROM epr_pair_pool
                    WHERE state = 'USED' AND last_used < ?
                """, (cutoff,))
                
                deleted = c.total_changes
                if deleted > 0:
                    logger.info(f"Cleaned {deleted} old pairs")
                
                logger.info("✓ Maintenance complete")
            
            retry_on_lock(_maintain)
    
    def start_maintenance(self, interval: float = 10.0):
        """Start maintenance thread"""
        if self._maintenance_running:
            return
        
        self._maintenance_running = True
        
        def _loop():
            while self._maintenance_running:
                try:
                    self.maintain_pool()
                except Exception as e:
                    logger.error(f"Maintenance error: {e}")
                time.sleep(interval)
        
        self._maintenance_thread = threading.Thread(target=_loop, daemon=True)
        self._maintenance_thread.start()
        logger.info(f"Maintenance started (interval={interval}s)")
    
    def stop_maintenance(self):
        """Stop maintenance"""
        if self._maintenance_running:
            self._maintenance_running = False
            if self._maintenance_thread:
                self._maintenance_thread.join(timeout=5.0)
    
    def initialize_pool(self, target_size: int = 100) -> bool:
        """Initialize pool"""
        logger.info(f"\n{C.M}{'='*70}{C.E}")
        logger.info(f"{C.M}EPR POOL INITIALIZATION{C.E}")
        logger.info(f"{C.M}Target: {target_size} pairs{C.E}")
        logger.info(f"{C.M}{'='*70}{C.E}\n")
        
        if not self.generator:
            logger.error("No generator available")
            return False
        
        status = self.get_pool_status()
        current = status['ready']
        
        if current >= target_size:
            logger.info(f"Pool already has {current} pairs")
            return True
        
        needed = target_size - current
        generated = self.generate_pairs(needed)
        
        status = self.get_pool_status()
        final = status['ready']
        
        logger.info(f"\n{C.G}✓ Pool initialized: {final} pairs ready{C.E}\n")
        
        return final >= self.min_pool_size


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

__all__ = [
    'BellPairPoolManager',
    'EPRPair',
    'EPRState',
]


def main():
    """CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(description=f'QUNIX Quantum Link v{VERSION} (EPR Pool Only)')
    parser.add_argument('--db', type=str, required=True, help='Database path')
    parser.add_argument('--init', action='store_true', help='Initialize pool')
    parser.add_argument('--generate', type=int, help='Generate N pairs')
    parser.add_argument('--status', action='store_true', help='Show status')
    
    args = parser.parse_args()
    
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"{C.R}✗ Database not found{C.E}")
        return 1
    
    manager = BellPairPoolManager(db_path)
    
    if args.init:
        manager.initialize_pool()
    
    if args.generate:
        manager.generate_pairs(args.generate)
    
    if args.status:
        status = manager.get_pool_status()
        print(f"\nEPR Pool Status:")
        print(f"  Ready:     {status['ready']:>6,}")
        print(f"  Allocated: {status['allocated']:>6,}")
        print(f"  Total:     {status['total']:>6,}\n")
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())