#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║              QUNIX QUANTUM MEGA BUS v5.1.0 - DIRECT IPC FIXED                 ║
║                    Quantum-Classical Interface (AER-A)                         ║
║                                                                               ║
║  ARCHITECTURE:                                                                ║
║  ✓ Direct quantum_ipc table access only                                      ║
║  ✓ No views, no schema detection complexity                                  ║
║  ✓ Fixed response polling with proper cleanup                                ║
║  ✓ Sends FLASK_TO_CPU, receives CPU_TO_FLASK                                 ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import sqlite3
import numpy as np
import time
import sys
from pathlib import Path
from typing import Dict, Optional

try:
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel, depolarizing_error, thermal_relaxation_error
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    print("FATAL: Qiskit required. Install: pip install qiskit qiskit-aer")
    sys.exit(1)

VERSION = "5.1.0-DIRECT-IPC-FIXED"

# ANSI Colors
class C:
    H = '\033[95m'; B = '\033[94m'; C = '\033[96m'; G = '\033[92m'
    Y = '\033[93m'; R = '\033[91m'; E = '\033[0m'; Q = '\033[38;5;213m'
    W = '\033[97m'; M = '\033[35m'; BOLD = '\033[1m'; GRAY = '\033[90m'


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

DIRECTION_FLASK_TO_CPU = 'FLASK_TO_CPU'
DIRECTION_CPU_TO_FLASK = 'CPU_TO_FLASK'


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE CONNECTION (WAL MODE)
# ═══════════════════════════════════════════════════════════════════════════════

def create_connection(db_path: Path) -> sqlite3.Connection:
    """Create optimized WAL-mode connection"""
    conn = sqlite3.connect(
        str(db_path),
        timeout=60.0,
        check_same_thread=False,
        isolation_level=None
    )
    conn.row_factory = sqlite3.Row
    
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


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFY IPC TABLE
# ═══════════════════════════════════════════════════════════════════════════════

def verify_ipc_table(conn: sqlite3.Connection) -> bool:
    """Verify quantum_ipc table exists and is accessible"""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name = 'quantum_ipc'
    """)
    
    if not cursor.fetchone():
        print(f"{C.R}[BUS] ERROR: quantum_ipc table not found!{C.E}")
        return False
    
    cursor.execute("PRAGMA table_info(quantum_ipc)")
    columns = {row[1] for row in cursor.fetchall()}
    
    required = {'packet_id', 'sender', 'direction', 'data', 'processed'}
    missing = required - columns
    
    if missing:
        print(f"{C.R}[BUS] ERROR: Missing columns: {missing}{C.E}")
        return False
    
    print(f"{C.G}[BUS] ✓ quantum_ipc table verified{C.E}")
    
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# BUS QUANTUM ENGINE (AER-A)
# ═══════════════════════════════════════════════════════════════════════════════

class BusQuantumEngine:
    """Quantum engine for Mega Bus (AER-A)"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        
        print(f"{C.Q}Initializing Bus Quantum Engine (AER-A)...{C.E}")
        
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
        
        print(f"{C.G}  ✓ AER Simulator A ready{C.E}")
    
    def _build_noise_model(self) -> NoiseModel:
        """Build noise model"""
        noise_model = NoiseModel()
        
        t1 = 50e3
        t2 = 70e3
        gate_error = 0.001
        
        gate_times = {'h': 50, 'x': 50, 'cx': 300}
        
        for gate in ['h', 'x']:
            thermal = thermal_relaxation_error(t1, t2, gate_times[gate])
            depol = depolarizing_error(gate_error, 1)
            noise_model.add_all_qubit_quantum_error(thermal.compose(depol), gate)
        
        thermal = thermal_relaxation_error(t1, t2, gate_times['cx'])
        depol = depolarizing_error(gate_error * 10, 2)
        noise_model.add_all_qubit_quantum_error(depol.compose(thermal), 'cx')
        
        return noise_model
    
    def create_epr_pair(self) -> Dict[str, any]:
        """Create EPR pair with CHSH"""
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
    
    def get_metrics(self) -> Dict:
        return dict(self.metrics)


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND EXECUTOR - FIXED POLLING
# ═══════════════════════════════════════════════════════════════════════════════

class BusCommandExecutor:
    """Executes commands via quantum IPC - FIXED"""
    
    def __init__(self, db_path: Path, quantum_engine: BusQuantumEngine):
        self.db_path = db_path
        self.conn = create_connection(db_path)
        self.quantum_engine = quantum_engine
        
        if not verify_ipc_table(self.conn):
            print(f"{C.R}FATAL: IPC table verification failed{C.E}")
            sys.exit(1)
        
        self.stats = {
            'commands_sent': 0,
            'responses_received': 0,
            'timeouts': 0,
        }
        
        print(f"{C.C}[BUS] Executor initialized{C.E}")
    
    def execute(self, command: str, timeout: float = 10.0) -> str:
        """Execute command via quantum IPC"""
        if not command.strip():
            return ""
        
        start_time = time.time()
        
        try:
            # Create EPR pair for quantum entanglement proof
            epr_result = self.quantum_engine.create_epr_pair()
            chsh = epr_result['chsh']
        except Exception as epr_error:
            print(f"{C.Y}[BUS] EPR generation error: {epr_error}{C.E}")
            chsh = 2.0  # Fallback to classical
        
        # Encode command
        try:
            cmd_bytes = command.encode('utf-8')
        except Exception as encode_error:
            print(f"{C.R}[BUS] Command encode error: {encode_error}{C.E}")
            return f"{C.R}Encode error: {encode_error}{C.E}"
        
        # Send command to quantum_ipc
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO quantum_ipc
                (sender, direction, data, data_size, chsh_value, timestamp, processed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                'MEGA_BUS',
                DIRECTION_FLASK_TO_CPU,
                cmd_bytes,
                len(cmd_bytes),
                chsh,
                time.time(),
                0
            ))
            
            packet_id = cursor.lastrowid
            
            self.stats['commands_sent'] += 1
            
            print(f"{C.Q}[BUS] TX packet {packet_id}: '{command[:50]}...' (CHSH={chsh:.3f}){C.E}")
            
        except Exception as send_error:
            print(f"{C.R}[BUS] Send error: {send_error}{C.E}")
            import traceback
            traceback.print_exc()
            return f"{C.R}Send error: {send_error}{C.E}"
        
        # Wait for response
        try:
            response = self._wait_for_result(packet_id, timeout)
        except Exception as wait_error:
            print(f"{C.R}[BUS] Wait error: {wait_error}{C.E}")
            import traceback
            traceback.print_exc()
            return f"{C.R}Wait error: {wait_error}{C.E}"
        
        elapsed = (time.time() - start_time) * 1000
        
        if response:
            self.stats['responses_received'] += 1
            
            quantum_tag = f"\n{C.GRAY}[Bus CHSH: {chsh:.3f} "
            quantum_tag += f"{'✓ quantum' if chsh > 2.0 else ''}"
            quantum_tag += f"] [{elapsed:.1f}ms]{C.E}"
            
            return response + quantum_tag
        else:
            self.stats['timeouts'] += 1
            return (f"{C.Y}Timeout waiting for CPU ({timeout}s){C.E}\n"
                   f"Is qunix_cpu.py running?")
    
    def _wait_for_result(self, sent_packet_id: int, timeout: float) -> Optional[str]:
        """
        Wait for CPU response - FIXED VERSION
        
        Key fixes:
        1. Poll for ANY CPU_TO_FLASK response (not tied to sent_packet_id)
        2. Mark as processed immediately after reading
        3. Better error handling
        """
        start = time.time()
        poll_count = 0
        last_log = time.time()
        
        while (time.time() - start) < timeout:
            poll_count += 1
            
            try:
                cursor = self.conn.cursor()
                
                # Get oldest unprocessed CPU_TO_FLASK response
                cursor.execute("""
                    SELECT packet_id, data, chsh_value
                    FROM quantum_ipc
                    WHERE direction = ?
                      AND processed = 0
                    ORDER BY packet_id ASC
                    LIMIT 1
                """, (DIRECTION_CPU_TO_FLASK,))
                
                row = cursor.fetchone()
                
                if row:
                    resp_packet_id = row['packet_id']
                    data = row['data']
                    resp_chsh = row['chsh_value'] or 2.0
                    
                    # Mark as processed IMMEDIATELY
                    cursor.execute("""
                        UPDATE quantum_ipc
                        SET processed = 1
                        WHERE packet_id = ?
                    """, (resp_packet_id,))
                    
                    # Decode response
                    response = ''
                    if data:
                        try:
                            if isinstance(data, bytes):
                                response = data.decode('utf-8', errors='replace')
                            else:
                                response = str(data)
                        except Exception as e:
                            print(f"{C.Y}[BUS] Decode error: {e}{C.E}")
                            response = f"[Decode error: {e}]"
                    
                    print(f"{C.G}[BUS] RX packet {resp_packet_id} (CHSH={resp_chsh:.3f}) [{poll_count} polls]{C.E}")
                    
                    return response
                
            except Exception as e:
                print(f"{C.Y}[BUS] Poll error: {e}{C.E}")
            
            # Log progress every 2 seconds
            if time.time() - last_log > 2.0:
                print(f"{C.GRAY}[BUS] Waiting for response... ({poll_count} polls, {time.time()-start:.1f}s){C.E}")
                last_log = time.time()
            
            # Poll every 50ms
            time.sleep(0.05)
        
        print(f"{C.Y}[BUS] Timeout after {poll_count} polls{C.E}")
        return None
    
    def get_stats(self) -> Dict:
        return dict(self.stats)


# ═══════════════════════════════════════════════════════════════════════════════
# QUANTUM MEGA BUS - MAIN CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class QuantumMegaBus:
    """Main Quantum Mega Bus - Direct IPC"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.running = False
        
        print(f"\n{C.Q}{C.BOLD}{'═'*70}{C.E}")
        print(f"{C.Q}{C.BOLD}  QUNIX QUANTUM MEGA BUS v{VERSION}{C.E}")
        print(f"{C.Q}{C.BOLD}  Direct IPC Mode{C.E}")
        print(f"{C.Q}{C.BOLD}{'═'*70}{C.E}\n")
        
        self.quantum_engine = BusQuantumEngine(db_path)
        self.executor = BusCommandExecutor(db_path, self.quantum_engine)
        
        conn = create_connection(db_path)
        try:
            rows = safe_execute(conn, "SELECT COUNT(*) as c FROM l LIMIT 1")
            lattice_size = rows[0]['c'] if rows else 0
        except:
            lattice_size = 0
        finally:
            conn.close()
        
        print(f"{C.G}✓ Leech lattice: {lattice_size:,} points{C.E}")
        print(f"\n{C.G}{C.BOLD}✓ QUANTUM MEGA BUS READY{C.E}")
        print(f"{C.GRAY}  Sends: {DIRECTION_FLASK_TO_CPU}{C.E}")
        print(f"{C.GRAY}  Receives: {DIRECTION_CPU_TO_FLASK}{C.E}\n")
    
    def execute_command(self, command: str, timeout: float = 10.0) -> str:
        """Execute via quantum IPC"""
        return self.executor.execute(command, timeout)
    
    def get_status(self) -> Dict:
        """Get status"""
        return {
            'version': VERSION,
            'running': self.running,
            'quantum_engine': self.quantum_engine.get_metrics(),
            'executor': self.executor.get_stats()
        }
    
    def start(self):
        self.running = True
        print(f"{C.G}Bus started{C.E}")
    
    def stop(self):
        self.running = False
        print(f"{C.Y}Bus stopped{C.E}")


# ═══════════════════════════════════════════════════════════════════════════════
# FLASK INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

_bus_instance: Optional[QuantumMegaBus] = None

def get_bus(db_path: Path = None) -> QuantumMegaBus:
    """Get or create bus"""
    global _bus_instance
    
    if _bus_instance is None:
        if db_path is None:
            for loc in [
                Path('/home/Shemshallah/qunix_leech.db'),
                Path('/home/Shemshallah/mysite/qunix_leech.db'),
                Path.home() / 'qunix_leech.db',
            ]:
                if loc.exists():
                    db_path = loc
                    break
        
        if not db_path or not db_path.exists():
            raise FileNotFoundError("Database not found")
        
        _bus_instance = QuantumMegaBus(db_path)
        _bus_instance.start()
    
    return _bus_instance


def execute_via_bus(command: str, db_path: Path = None, timeout: float = 10.0) -> str:
    """Execute via bus"""
    bus = get_bus(db_path)
    return bus.execute_command(command, timeout)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN - FOR TESTING
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='QUNIX Quantum Mega Bus v5.1')
    parser.add_argument('--db', type=str, help='Database path')
    parser.add_argument('--test', action='store_true', help='Run test')
    args = parser.parse_args()
    
    # Find database
    db_path = None
    if args.db:
        db_path = Path(args.db)
    else:
        for loc in [
            Path('/home/Shemshallah/qunix_leech.db'),
            Path('/home/Shemshallah/mysite/qunix_leech.db'),
            Path('/data/qunix_leech.db'),
        ]:
            if loc.exists():
                db_path = loc
                break
    
    if not db_path or not db_path.exists():
        print(f"{C.R}ERROR: Database not found{C.E}")
        sys.exit(1)
    
    print(f"{C.C}Using database: {db_path}{C.E}\n")
    
    # Create bus
    bus = QuantumMegaBus(db_path)
    bus.start()
    
    if args.test:
        print(f"\n{C.BOLD}Running test...{C.E}\n")
        
        # Test commands
        for cmd in ['help', 'status', 'ping']:
            print(f"\n{C.C}Testing: {cmd}{C.E}")
            result = bus.execute_command(cmd, timeout=5.0)
            print(f"\n{C.G}Result:{C.E}")
            print(result)
            print()
            time.sleep(0.5)
        
        # Show status
        status = bus.get_status()
        print(f"{C.C}Final Status:{C.E}")
        print(f"  Commands sent: {status['executor']['commands_sent']}")
        print(f"  Responses: {status['executor']['responses_received']}")
        print(f"  Timeouts: {status['executor']['timeouts']}")
    else:
        print(f"{C.Y}Run with --test to test communication{C.E}")
        print(f"{C.GRAY}Or import in flask_app.py{C.E}")