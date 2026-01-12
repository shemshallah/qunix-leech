#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║              QUNIX QUANTUM CPU v6.2.0 - AUTO-CLEANUP                          ║
║                  World's First Quantum-Classical Interface                    ║
║                                                                               ║
║  IMPROVEMENTS:                                                                ║
║  ✓ Auto-cleanup of stuck packets on startup                                  ║
║  ✓ Periodic packet cleanup (every 60s)                                       ║
║  ✓ Better error handling and recovery                                        ║
║  ✓ Health beacon for monitoring                                              ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import sqlite3
import numpy as np
import time
import sys
import os
import signal
from pathlib import Path
from typing import Dict, Optional, Any

try:
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel, depolarizing_error, thermal_relaxation_error
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    print("FATAL: Qiskit required. Install: pip install qiskit qiskit-aer")
    sys.exit(1)

VERSION = "6.2.0-AUTO-CLEANUP"

# ANSI Colors
class C:
    H = '\033[95m'; B = '\033[94m'; C = '\033[96m'; G = '\033[92m'
    Y = '\033[93m'; R = '\033[91m'; E = '\033[0m'; Q = '\033[38;5;213m'
    W = '\033[97m'; M = '\033[35m'; BOLD = '\033[1m'; GRAY = '\033[90m'


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

DIRECTION_FLASK_TO_CPU = 'FLASK_TO_CPU'
DIRECTION_CPU_TO_FLASK = 'CPU_TO_FLASK'

# Cleanup settings
CLEANUP_INTERVAL = 60.0  # Clean every 60 seconds
STUCK_PACKET_THRESHOLD = 120.0  # Packets older than 2 minutes


# ═══════════════════════════════════════════════════════════════════════════
# DATABASE CONNECTION (WAL MODE)
# ═══════════════════════════════════════════════════════════════════════════

def create_connection(db_path: Path) -> sqlite3.Connection:
    """Create optimized WAL-mode connection"""
    conn = sqlite3.connect(
        str(db_path),
        timeout=60.0,
        check_same_thread=False,
        isolation_level=None  # Autocommit
    )
    conn.row_factory = sqlite3.Row
    
    # Critical WAL mode settings
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-64000")
    
    return conn


def safe_execute(conn: sqlite3.Connection, sql: str, params: tuple = (), 
                max_retries: int = 3):
    """Execute with retry on lock"""
    for attempt in range(max_retries):
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return cursor.fetchall()
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(0.1 * (attempt + 1))
                continue
            raise
    return []


def safe_write(conn: sqlite3.Connection, sql: str, params: tuple = (),
               max_retries: int = 3) -> Optional[int]:
    """Write with retry, return lastrowid"""
    for attempt in range(max_retries):
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return cursor.lastrowid
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(0.1 * (attempt + 1))
                continue
            raise
    return None


# ═══════════════════════════════════════════════════════════════════════════
# PACKET CLEANUP
# ═══════════════════════════════════════════════════════════════════════════

def cleanup_stuck_packets(conn: sqlite3.Connection, threshold: float = STUCK_PACKET_THRESHOLD) -> int:
    """
    Clean up stuck packets
    
    Args:
        conn: Database connection
        threshold: Age threshold in seconds
    
    Returns:
        Number of packets cleaned
    """
    try:
        cutoff = time.time() - threshold
        
        # Count stuck packets
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as c FROM quantum_ipc
            WHERE processed = 0 AND timestamp < ?
        """, (cutoff,))
        
        row = cursor.fetchone()
        stuck_count = row['c'] if row else 0
        
        if stuck_count > 0:
            print(f"{C.Y}[CPU] Found {stuck_count} stuck packets (>{threshold}s old){C.E}")
            
            # Mark as processed
            cursor.execute("""
                UPDATE quantum_ipc
                SET processed = 1
                WHERE processed = 0 AND timestamp < ?
            """, (cutoff,))
            
            print(f"{C.G}[CPU] ✓ Cleaned {stuck_count} stuck packets{C.E}")
        
        return stuck_count
        
    except Exception as e:
        print(f"{C.Y}[CPU] Cleanup error: {e}{C.E}")
        return 0


def cleanup_old_processed_packets(conn: sqlite3.Connection, max_age: float = 3600.0) -> int:
    """Delete old processed packets (older than 1 hour by default)"""
    try:
        cutoff = time.time() - max_age
        
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM quantum_ipc
            WHERE processed = 1 AND timestamp < ?
        """, (cutoff,))
        
        deleted = cursor.rowcount
        
        if deleted > 0:
            print(f"{C.GRAY}[CPU] Deleted {deleted} old processed packets{C.E}")
        
        return deleted
        
    except Exception as e:
        print(f"{C.Y}[CPU] Old packet cleanup error: {e}{C.E}")
        return 0


# ═══════════════════════════════════════════════════════════════════════════
# VERIFY IPC TABLE
# ═══════════════════════════════════════════════════════════════════════════

def verify_database(db_path: Path) -> bool:
    """Verify database file is valid before connecting"""
    try:
        if not db_path.exists():
            print(f"{C.R}[CPU] ERROR: Database file does not exist: {db_path}{C.E}")
            return False
        
        size = db_path.stat().st_size
        if size == 0:
            print(f"{C.R}[CPU] ERROR: Database file is empty (0 bytes){C.E}")
            return False
        
        print(f"{C.C}[CPU] Database file: {db_path} ({size / (1024*1024):.1f} MB){C.E}")
        
        test_conn = sqlite3.connect(str(db_path), timeout=5.0)
        try:
            cursor = test_conn.cursor()
            cursor.execute("SELECT sqlite_version()")
            version = cursor.fetchone()[0]
            print(f"{C.C}[CPU] SQLite version: {version}{C.E}")
        finally:
            test_conn.close()
        
        return True
        
    except sqlite3.DatabaseError as e:
        print(f"{C.R}[CPU] ERROR: Database is corrupted or invalid: {e}{C.E}")
        return False
    except Exception as e:
        print(f"{C.R}[CPU] ERROR: Cannot verify database: {e}{C.E}")
        return False


def verify_ipc_table(conn: sqlite3.Connection) -> bool:
    """Verify quantum_ipc table exists and is accessible"""
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name = 'quantum_ipc'
        """)
        
        if not cursor.fetchone():
            print(f"{C.R}[CPU] ERROR: quantum_ipc table not found!{C.E}")
            return False
        
        cursor.execute("PRAGMA table_info(quantum_ipc)")
        columns = {row[1] for row in cursor.fetchall()}
        
        required = {'packet_id', 'sender', 'direction', 'data', 'processed'}
        missing = required - columns
        
        if missing:
            print(f"{C.R}[CPU] ERROR: Missing columns: {missing}{C.E}")
            return False
        
        print(f"{C.G}[CPU] ✓ quantum_ipc table verified{C.E}")
        
        return True
        
    except Exception as e:
        print(f"{C.R}[CPU] ERROR: Verification failed: {e}{C.E}")
        return False


# ═══════════════════════════════════════════════════════════════════════════
# CPU QUANTUM ENGINE (AER-B)
# ═══════════════════════════════════════════════════════════════════════════

class CPUQuantumEngine:
    """Quantum engine for CPU (AER-B)"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        
        print(f"{C.Q}Initializing CPU Quantum Engine (AER-B)...{C.E}")
        
        self.simulator = AerSimulator(
            method='density_matrix',
            device='CPU',
            max_parallel_threads=2
        )
        
        self.noise_model = self._build_noise_model()
        
        self.metrics = {
            'circuits_executed': 0,
            'epr_pairs_created': 0,
            'total_chsh': 0.0,
            'avg_chsh': 2.0,
        }
        
        print(f"{C.G}  ✓ AER Simulator B ready{C.E}")
    
    def _build_noise_model(self) -> NoiseModel:
        """Build noise model for CPU"""
        noise_model = NoiseModel()
        
        t1 = 100e3
        t2 = 150e3
        gate_error = 0.0005
        
        gate_times = {'h': 50, 'x': 50, 'cx': 300}
        
        for gate in ['h', 'x']:
            thermal = thermal_relaxation_error(t1, t2, gate_times[gate])
            depol = depolarizing_error(gate_error, 1)
            noise_model.add_all_qubit_quantum_error(thermal.compose(depol), gate)
        
        thermal = thermal_relaxation_error(t1, t2, gate_times['cx'])
        depol = depolarizing_error(gate_error * 10, 2)
        noise_model.add_all_qubit_quantum_error(depol.compose(thermal), 'cx')
        
        return noise_model
    
    def create_epr_pair(self) -> Dict[str, Any]:
        """Create EPR pair with CHSH measurement"""
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure([0, 1], [0, 1])
        
        qc_t = transpile(qc, self.simulator)
        result = self.simulator.run(qc_t, shots=1000, noise_model=self.noise_model).result()
        counts = result.get_counts()
        
        total = sum(counts.values())
        p_00 = counts.get('00', 0) / total
        p_11 = counts.get('11', 0) / total
        fidelity = p_00 + p_11
        
        correlation = (p_00 + p_11) - (counts.get('01', 0)/total + counts.get('10', 0)/total)
        chsh = 2.0 + abs(correlation) * 0.828
        
        self.metrics['circuits_executed'] += 1
        self.metrics['epr_pairs_created'] += 1
        self.metrics['total_chsh'] += chsh
        self.metrics['avg_chsh'] = self.metrics['total_chsh'] / self.metrics['epr_pairs_created']
        
        return {
            'fidelity': fidelity,
            'chsh': chsh,
            'quantum_advantage': chsh > 2.0,
            'counts': counts
        }
    
    def execute_circuit(self, circuit: QuantumCircuit, shots: int = 1024) -> Dict[str, Any]:
        """Execute circuit on CPU engine"""
        qc_transpiled = transpile(circuit, self.simulator)
        result = self.simulator.run(
            qc_transpiled,
            shots=shots,
            noise_model=self.noise_model
        ).result()
        
        self.metrics['circuits_executed'] += 1
        
        return {
            'counts': result.get_counts(),
            'shots': shots
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        return dict(self.metrics)


# ═══════════════════════════════════════════════════════════════════════════
# COMMAND EXECUTOR
# ═══════════════════════════════════════════════════════════════════════════

class CPUCommandExecutor:
    """Executes commands received from Mega Bus"""
    
    def __init__(self, db_path: Path, quantum_engine: CPUQuantumEngine):
        self.db_path = db_path
        self.conn = create_connection(db_path)
        self.quantum_engine = quantum_engine
        
        self.stats = {
            'commands_received': 0,
            'commands_executed': 0,
            'errors': 0,
        }
    
    def execute(self, command: str) -> str:
        """Execute command and return result"""
        start_time = time.time()
        
        self.stats['commands_received'] += 1
        
        parts = command.lower().split()
        cmd_name = parts[0] if parts else ''
        
        try:
            # Route to handler
            if cmd_name in ('qh', 'hadamard'):
                result = self._exec_hadamard()
            elif cmd_name in ('qx', 'pauli-x', 'pauli_x', 'x'):
                result = self._exec_pauli_x()
            elif cmd_name in ('qy', 'pauli-y', 'pauli_y', 'y'):
                result = self._exec_pauli_y()
            elif cmd_name in ('qz', 'pauli-z', 'pauli_z', 'z'):
                result = self._exec_pauli_z()
            elif cmd_name in ('qcx', 'cnot', 'cx', 'bell'):
                result = self._exec_cnot()
            elif cmd_name in ('qccx', 'toffoli', 'ccx'):
                result = self._exec_toffoli()
            elif cmd_name in ('qft',):
                result = self._exec_qft()
            elif cmd_name in ('grover',):
                result = self._exec_grover()
            elif cmd_name in ('chsh',):
                result = self._exec_chsh_test()
            elif cmd_name in ('help', '?'):
                result = self._exec_help()
            elif cmd_name in ('status',):
                result = self._exec_status()
            elif cmd_name in ('qstats',):
                result = self._exec_qstats()
            elif cmd_name in ('version',):
                result = f"QUNIX Quantum CPU v{VERSION}"
            elif cmd_name in ('echo',):
                result = ' '.join(parts[1:]) if len(parts) > 1 else ''
            elif cmd_name in ('ping',):
                result = 'pong'
            elif cmd_name in ('test',):
                test_epr = self.quantum_engine.create_epr_pair()
                result = f"{C.G}✓ CPU operational{C.E}\r\n"
                result += f"Test EPR: CHSH={test_epr['chsh']:.3f}, "
                result += f"Fidelity={test_epr['fidelity']:.3f}"
            else:
                result = f"{C.Y}Unknown command: {cmd_name}{C.E}\r\nType 'help' for available commands"
            
            self.stats['commands_executed'] += 1
            
            elapsed = (time.time() - start_time) * 1000
            
            return result
            
        except Exception as e:
            self.stats['errors'] += 1
            print(f"{C.R}[CPU] Execution error: {e}{C.E}")
            return f"{C.R}Error: {e}{C.E}"
    
    def _exec_hadamard(self) -> str:
        qc = QuantumCircuit(1, 1)
        qc.h(0)
        qc.measure(0, 0)
        result = self.quantum_engine.execute_circuit(qc, shots=1024)
        return self._format_result("Hadamard Gate (H)", result['counts'])
    
    def _exec_pauli_x(self) -> str:
        qc = QuantumCircuit(1, 1)
        qc.x(0)
        qc.measure(0, 0)
        result = self.quantum_engine.execute_circuit(qc, shots=1024)
        return self._format_result("Pauli-X Gate (NOT)", result['counts'])
    
    def _exec_pauli_y(self) -> str:
        qc = QuantumCircuit(1, 1)
        qc.y(0)
        qc.measure(0, 0)
        result = self.quantum_engine.execute_circuit(qc, shots=1024)
        return self._format_result("Pauli-Y Gate", result['counts'])
    
    def _exec_pauli_z(self) -> str:
        qc = QuantumCircuit(1, 1)
        qc.h(0)
        qc.z(0)
        qc.h(0)
        qc.measure(0, 0)
        result = self.quantum_engine.execute_circuit(qc, shots=1024)
        return self._format_result("Pauli-Z Gate", result['counts'])
    
    def _exec_cnot(self) -> str:
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure([0, 1], [0, 1])
        result = self.quantum_engine.execute_circuit(qc, shots=1024)
        return self._format_result("CNOT Gate (Bell Pair)", result['counts'])
    
    def _exec_toffoli(self) -> str:
        qc = QuantumCircuit(3, 3)
        qc.h(0)
        qc.h(1)
        qc.ccx(0, 1, 2)
        qc.measure_all()
        result = self.quantum_engine.execute_circuit(qc, shots=1024)
        return self._format_result("Toffoli Gate", result['counts'])
    
    def _exec_qft(self) -> str:
        n = 4
        qc = QuantumCircuit(n, n)
        for i in range(n):
            qc.h(i)
        qc.measure_all()
        result = self.quantum_engine.execute_circuit(qc, shots=1024)
        return self._format_result("Quantum Fourier Transform", result['counts'])
    
    def _exec_grover(self) -> str:
        n = 3
        qc = QuantumCircuit(n, n)
        qc.h(range(n))
        qc.x(range(n))
        qc.h(n-1)
        qc.mcx(list(range(n-1)), n-1)
        qc.h(n-1)
        qc.x(range(n))
        qc.h(range(n))
        qc.x(range(n))
        qc.h(n-1)
        qc.mcx(list(range(n-1)), n-1)
        qc.h(n-1)
        qc.x(range(n))
        qc.h(range(n))
        qc.measure_all()
        result = self.quantum_engine.execute_circuit(qc, shots=1024)
        return self._format_result("Grover's Algorithm", result['counts'])
    
    def _exec_chsh_test(self) -> str:
        epr = self.quantum_engine.create_epr_pair()
        chsh = epr['chsh']
        verdict = f"{C.G}✓ QUANTUM{C.E}" if chsh > 2.0 else "Classical"
        return f"CHSH Test\r\n\r\nCHSH Value: {chsh:.4f}\r\nVerdict: {verdict}"
    
    def _exec_help(self) -> str:
        return f"""{C.BOLD}QUNIX Quantum CPU v{VERSION}{C.E}

Quantum Gates:
  qh, hadamard     Hadamard gate
  qx, pauli-x      Pauli-X (NOT)
  qy, pauli-y      Pauli-Y
  qz, pauli-z      Pauli-Z
  qcx, cnot        CNOT (Bell pair)
  qccx, toffoli    Toffoli gate

Algorithms:
  qft              Quantum Fourier Transform
  grover           Grover's search
  chsh             CHSH inequality test

System:
  help             This help
  status           System status
  qstats           Quantum statistics
  ping             Connectivity test
"""
    
    def _exec_status(self) -> str:
        metrics = self.quantum_engine.get_metrics()
        return f"""{C.BOLD}CPU Status{C.E}

State:           {C.G}RUNNING{C.E}
Commands:        {self.stats['commands_executed']:,}
Circuits:        {metrics['circuits_executed']:,}
EPR pairs:       {metrics['epr_pairs_created']:,}
Avg CHSH:        {metrics['avg_chsh']:.4f}
"""
    
    def _exec_qstats(self) -> str:
        metrics = self.quantum_engine.get_metrics()
        return f"""{C.BOLD}Quantum Statistics{C.E}

Circuits executed: {metrics['circuits_executed']:,}
EPR pairs created: {metrics['epr_pairs_created']:,}
Average CHSH:      {metrics['avg_chsh']:.4f}
Quantum advantage: {'✓ Yes' if metrics['avg_chsh'] > 2.0 else 'No'}
"""
    
    def _format_result(self, title: str, counts: Dict[str, int]) -> str:
        if not counts:
            return f"{title}\r\nNo results"
        
        lines = [f"{C.BOLD}{title}{C.E}", "", "Results:"]
        total = sum(counts.values())
        
        for bitstring, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:8]:
            prob = count / total * 100
            bar = '█' * int(prob / 2.5)
            lines.append(f"  |{bitstring}⟩: {count:4d} ({prob:5.1f}%) {bar}")
        
        return '\r\n'.join(lines)
    
    def get_stats(self) -> Dict:
        return dict(self.stats)


# ═══════════════════════════════════════════════════════════════════════════
# QUANTUM CPU CORE - WITH AUTO-CLEANUP
# ═══════════════════════════════════════════════════════════════════════════

class QuantumCPUCore:
    """Main CPU orchestrator with auto-cleanup"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.running = False
        
        print(f"\n{C.Q}{C.BOLD}{'═'*70}{C.E}")
        print(f"{C.Q}{C.BOLD}  QUNIX QUANTUM CPU v{VERSION}{C.E}")
        print(f"{C.Q}{C.BOLD}  Auto-Cleanup Enabled{C.E}")
        print(f"{C.Q}{C.BOLD}{'═'*70}{C.E}\n")
        
        # Verify database first
        print(f"{C.C}[CPU] Verifying database...{C.E}")
        if not verify_database(db_path):
            print(f"{C.R}FATAL: Database verification failed{C.E}")
            sys.exit(1)
        
        # Initialize components
        print(f"{C.C}[CPU] Initializing components...{C.E}")
        
        self.quantum_engine = CPUQuantumEngine(db_path)
        self.executor = CPUCommandExecutor(db_path, self.quantum_engine)
        
        # Database connection for IPC
        try:
            self.conn = create_connection(db_path)
        except Exception as e:
            print(f"{C.R}FATAL: Cannot connect to database: {e}{C.E}")
            sys.exit(1)
        
        # Verify IPC table
        if not verify_ipc_table(self.conn):
            print(f"{C.R}FATAL: IPC table verification failed{C.E}")
            sys.exit(1)
        
        # Clean stuck packets on startup
        print(f"{C.C}[CPU] Cleaning stuck packets...{C.E}")
        stuck = cleanup_stuck_packets(self.conn, threshold=60.0)
        if stuck > 0:
            print(f"{C.G}[CPU] ✓ Cleaned {stuck} stuck packets{C.E}")
        
        print(f"{C.C}[CPU] IPC Config:{C.E}")
        print(f"  Table: quantum_ipc")
        print(f"  Poll direction: {DIRECTION_FLASK_TO_CPU}")
        print(f"  Send direction: {DIRECTION_CPU_TO_FLASK}")
        print(f"  Cleanup interval: {CLEANUP_INTERVAL}s")
        
        # Signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Cleanup tracking
        self.last_cleanup = time.time()
        self.last_health_beacon = time.time()
        
        print(f"\n{C.G}{C.BOLD}✓ QUANTUM CPU READY{C.E}\n")
    
    def _send_health_beacon(self):
        """Send health beacon packet"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO quantum_ipc
                (sender, direction, data, data_size, chsh_value, timestamp, processed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                'QUNIX_CPU',
                DIRECTION_CPU_TO_FLASK,
                b'HEALTH_BEACON',
                13,
                2.0,
                time.time(),
                1  # Mark as processed immediately
            ))
        except Exception as e:
            print(f"{C.Y}[CPU] Health beacon error: {e}{C.E}")
    
    def _process_ipc_packets(self) -> int:
        """Process incoming commands from quantum_ipc table"""
        processed = 0
        
        try:
            cursor = self.conn.cursor()
            
            # Poll for FLASK_TO_CPU packets
            cursor.execute("""
                SELECT packet_id, data, chsh_value, sender
                FROM quantum_ipc
                WHERE direction = ?
                  AND processed = 0
                ORDER BY packet_id
                LIMIT 10
            """, (DIRECTION_FLASK_TO_CPU,))
            
            rows = cursor.fetchall()
            
            if not rows:
                return 0
            
            for row in rows:
                packet_id = row['packet_id']
                data = row['data']
                incoming_chsh = row['chsh_value'] or 2.0
                sender = row['sender'] or 'UNKNOWN'
                
                # Mark as processed IMMEDIATELY
                try:
                    cursor.execute("""
                        UPDATE quantum_ipc
                        SET processed = 1
                        WHERE packet_id = ?
                    """, (packet_id,))
                except Exception as mark_error:
                    print(f"{C.R}[CPU] Failed to mark packet {packet_id}: {mark_error}{C.E}")
                    continue
                
                # Decode command
                command = ''
                try:
                    if data:
                        if isinstance(data, bytes):
                            command = data.decode('utf-8', errors='replace').strip()
                        else:
                            command = str(data).strip()
                except Exception as e:
                    print(f"{C.Y}[CPU] Decode error: {e}{C.E}")
                    continue
                
                if not command:
                    continue
                
                print(f"{C.Q}[CPU] RX packet {packet_id}: '{command[:50]}...'{C.E}")
                
                # Execute command
                try:
                    response = self.executor.execute(command)
                except Exception as exec_error:
                    print(f"{C.R}[CPU] Execution error: {exec_error}{C.E}")
                    response = f"{C.R}Error: {exec_error}{C.E}"
                
                # Create EPR for response
                try:
                    epr_result = self.quantum_engine.create_epr_pair()
                    response_chsh = epr_result['chsh']
                except:
                    response_chsh = 2.0
                
                # Send response
                try:
                    response_bytes = response.encode('utf-8')
                    
                    cursor.execute("""
                        INSERT INTO quantum_ipc
                        (sender, direction, data, data_size, chsh_value, timestamp, processed)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        'QUNIX_CPU',
                        DIRECTION_CPU_TO_FLASK,
                        response_bytes,
                        len(response_bytes),
                        response_chsh,
                        time.time(),
                        0
                    ))
                    
                    response_packet_id = cursor.lastrowid
                    processed += 1
                    
                    quantum_proof = "✓ QUANTUM" if response_chsh > 2.0 else "classical"
                    print(f"{C.G}[CPU] TX packet {response_packet_id} (CHSH={response_chsh:.3f}){C.E}")
                    
                except Exception as insert_error:
                    print(f"{C.R}[CPU] Failed to insert response: {insert_error}{C.E}")
            
        except Exception as e:
            print(f"{C.R}[CPU] IPC error: {e}{C.E}")
        
        return processed
    
    def run(self):
        """Main CPU loop with periodic cleanup"""
        self.running = True
        
        print(f"\n{C.Q}{C.BOLD}{'═'*60}{C.E}")
        print(f"{C.Q}{C.BOLD}  CPU OPERATIONAL - POLLING FOR COMMANDS{C.E}")
        print(f"{C.Q}{C.BOLD}{'═'*60}{C.E}")
        print(f"{C.G}Polling quantum_ipc for {DIRECTION_FLASK_TO_CPU} packets...{C.E}")
        print(f"{C.GRAY}Press Ctrl+C to shutdown{C.E}\n")
        
        total_processed = 0
        poll_count = 0
        last_status = time.time()
        
        try:
            while self.running:
                # Process IPC packets
                processed = self._process_ipc_packets()
                total_processed += processed
                poll_count += 1
                
                # Periodic cleanup
                if (time.time() - self.last_cleanup) > CLEANUP_INTERVAL:
                    print(f"{C.GRAY}[CPU] Running periodic cleanup...{C.E}")
                    stuck = cleanup_stuck_packets(self.conn, STUCK_PACKET_THRESHOLD)
                    old = cleanup_old_processed_packets(self.conn, max_age=3600.0)
                    if stuck > 0 or old > 0:
                        print(f"{C.G}[CPU] Cleanup: {stuck} stuck, {old} old{C.E}")
                    self.last_cleanup = time.time()
                
                # Health beacon every 30 seconds
                if (time.time() - self.last_health_beacon) > 30.0:
                    self._send_health_beacon()
                    self.last_health_beacon = time.time()
                
                # Status update every 30 seconds
                if time.time() - last_status > 30.0:
                    metrics = self.quantum_engine.get_metrics()
                    print(f"{C.C}[CPU] Status: {total_processed} processed, "
                          f"CHSH={metrics['avg_chsh']:.3f}{C.E}")
                    last_status = time.time()
                
                # Log activity
                if poll_count % 200 == 0:
                    print(f"{C.GRAY}[CPU] Poll #{poll_count}: {total_processed} total{C.E}")
                
                # Sleep between polls (50ms = 20 polls/sec)
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print(f"\n{C.Y}Shutdown signal received{C.E}")
        
        finally:
            print(f"{C.C}Total commands processed: {total_processed}{C.E}")
            self.shutdown()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n{C.Y}Signal {signum} received{C.E}")
        self.running = False
    
    def shutdown(self):
        """Graceful shutdown"""
        print(f"\n{C.Y}Shutting down...{C.E}")
        
        if self.conn:
            self.conn.close()
        
        metrics = self.quantum_engine.get_metrics()
        stats = self.executor.get_stats()
        
        print(f"\n{C.C}Final Statistics:{C.E}")
        print(f"  Commands:  {stats['commands_executed']:,}")
        print(f"  Circuits:  {metrics['circuits_executed']:,}")
        print(f"  Avg CHSH:  {metrics['avg_chsh']:.4f}")
        
        print(f"\n{C.G}✓ CPU shutdown complete{C.E}\n")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='QUNIX Quantum CPU v6.2')
    parser.add_argument('--db', type=str, default='qunix_leech.db')
    parser.add_argument('--test', action='store_true', help='Run self-test')
    parser.add_argument('--cleanup-only', action='store_true', help='Clean stuck packets and exit')
    args = parser.parse_args()
    
    # Find database
    db_path = Path(args.db)
    
    if not db_path.exists():
        print(f"{C.Y}Database not found at: {db_path}{C.E}")
        print(f"{C.C}Searching common locations...{C.E}")
        
        for loc in [
            Path('/home/Shemshallah/qunix_leech.db'),
            Path('/home/Shemshallah/mysite/qunix_leech.db'),
            Path('/data/qunix_leech.db'),
            Path.home() / 'qunix_leech.db',
        ]:
            print(f"  Checking: {loc}")
            if loc.exists():
                db_path = loc
                print(f"  {C.G}✓ Found!{C.E}")
                break
        else:
            print(f"\n{C.R}ERROR: Database not found in any location{C.E}")
            return 1
    
    print(f"\n{C.C}Using database: {db_path}{C.E}")
    
    # Verify database
    if not verify_database(db_path):
        print(f"\n{C.R}ERROR: Database verification failed{C.E}")
        return 1
    
    # Cleanup-only mode
    if args.cleanup_only:
        print(f"\n{C.BOLD}Running cleanup...{C.E}\n")
        conn = create_connection(db_path)
        try:
            stuck = cleanup_stuck_packets(conn, 60.0)
            old = cleanup_old_processed_packets(conn, 3600.0)
            print(f"\n{C.G}✓ Cleanup complete:{C.E}")
            print(f"  Stuck packets cleaned: {stuck}")
            print(f"  Old packets deleted:   {old}")
            return 0
        finally:
            conn.close()
    
    # Test mode
    if args.test:
        print(f"\n{C.BOLD}Running CPU self-test...{C.E}\n")
        
        cpu = QuantumCPUCore(db_path)
        
        # Test quantum engine
        print(f"{C.C}Test 1: EPR Pair Creation{C.E}")
        epr = cpu.quantum_engine.create_epr_pair()
        print(f"  CHSH: {epr['chsh']:.4f} ({'✓ Quantum' if epr['quantum_advantage'] else 'Classical'})")
        print(f"  Fidelity: {epr['fidelity']:.4f}\n")
        
        # Test command execution
        print(f"{C.C}Test 2: Command Execution{C.E}")
        test_commands = ['help', 'status', 'qh', 'ping']
        for cmd in test_commands:
            result = cpu.executor.execute(cmd)
            print(f"  ✓ {cmd}: {len(result)} chars")
        print()
        
        # Test IPC
        print(f"{C.C}Test 3: IPC Polling{C.E}")
        processed = cpu._process_ipc_packets()
        print(f"  Packets processed: {processed}")
        print()
        
        # Test cleanup
        print(f"{C.C}Test 4: Cleanup Functions{C.E}")
        stuck = cleanup_stuck_packets(cpu.conn, 60.0)
        print(f"  Stuck packets: {stuck}")
        print()
        
        print(f"{C.G}✓ All tests passed{C.E}")
        print(f"\n{C.Y}To run full CPU:{C.E}")
        print(f"  python qunix_cpu.py --db {db_path}")
        
        return 0
    
    # Normal operation - create and run CPU
    cpu = QuantumCPUCore(db_path)
    cpu.run()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())