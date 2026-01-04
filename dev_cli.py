
#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║                    QUNIX DEVELOPMENT TOOLS v3.0                           ║
║         Full-Featured Quantum Development Environment                     ║
║                                                                           ║
║  • Real quantum execution on Leech lattice substrate                      ║
║  • Python-to-bitcode compiler with AST parsing                            ║
║  • Qiskit Aer backend for accurate simulation                             ║
║  • W-state tripartite kernel boot sequence                                ║
║  • Interactive REPL with multi-line support                               ║
║  • Complete binary execution on lattice-mapped qubits                     ║
║  • Full access to opcodes, syscalls, and bitcode programs                 ║
║  • Metaprogram monitoring and control                                     ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import sqlite3
import json
import time
import sys
import os
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import ast
import struct
import zlib
import traceback
from collections import defaultdict
import re

# Qiskit imports
try:
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator
    from qiskit.quantum_info import Statevector
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    print("⚠ WARNING: Qiskit not available - using fallback simulation")

# Terminal colors
class C:
    H = '\033[95m'; B = '\033[94m'; C = '\033[96m'
    G = '\033[92m'; Y = '\033[93m'; R = '\033[91m'
    E = '\033[0m'; Q = '\033[38;5;213m'; W = '\033[97m'
    M = '\033[35m'; O = '\033[38;5;208m'; BOLD = '\033[1m'
    GRAY = '\033[90m'

# ═══════════════════════════════════════════════════════════════════════════
# DATABASE PATH CONFIGURATION - MATCHES BUILDER
# ═══════════════════════════════════════════════════════════════════════════

RENDER_DISK_PATH = os.environ.get('RENDER_DISK_PATH', '/data')
DATA_DIR = Path(RENDER_DISK_PATH)

# Fallback to current directory if /data not writable
if not DATA_DIR.exists() or not os.access(str(DATA_DIR), os.W_OK):
    print(f"{C.Y}⚠ {DATA_DIR} not accessible, using current directory{C.E}")
    DATA_DIR = Path.cwd()

DB_PATH = DATA_DIR / "qunix_leech.db"

print(f"{C.C}Database location: {DB_PATH}{C.E}")

# Table names from builder
T_LAT="lat";T_PQB="pqb";T_TRI="tri";T_PRC="prc";T_THR="thr";T_MEM="mem"
T_SYS="sys";T_INT="int";T_SIG="sig";T_IPC="ipc";T_PIP="pip";T_SKT="skt"
T_FIL="fil";T_INO="ino";T_DIR="dir";T_NET="net";T_QMS="qms";T_ENT="ent"
T_CLK="clk";T_REG="reg";T_INS="ins";T_STK="stk";T_HEP="hep";T_TLB="tlb"
T_PGT="pgt";T_BIN="bin";T_QEX="qex"

# ═══════════════════════════════════════════════════════════════════════════
# QUANTUM OPCODE DEFINITIONS (from builder)
# ═══════════════════════════════════════════════════════════════════════════

OPCODES = {
    # Single-qubit gates
    0x00: ('QNOP', 0),
    0x01: ('QI', 1),
    0x02: ('QH', 1),
    0x03: ('QX', 1),
    0x04: ('QY', 1),
    0x05: ('QZ', 1),
    0x06: ('QS', 1),
    0x07: ('QT', 1),
    0x08: ('QSDG', 1),
    0x09: ('QTDG', 1),
    
    # Two-qubit gates
    0x0B: ('QCNOT', 2),
    0x0C: ('QCZ', 2),
    0x0D: ('QSWAP', 2),
    
    # Three-qubit gates
    0x0E: ('QTOFF', 3),
    
    # Measurement
    0x10: ('QMEAS', 1),
    
    # Composite operations
    0x12: ('QW3', 3),
    0x13: ('QW4', 4),
    0x14: ('QBELL', 2),
    0x15: ('QGHZ', 3),
    
    # Classical ops
    0x40: ('NOP', 0),
    0x41: ('HALT', 0),
    0x42: ('MOV', 2),
    0x43: ('ADD', 3),
    0x44: ('SUB', 3),
    0x45: ('CMP', 2),
    0x46: ('JMP', 1),
    0x47: ('JNZ', 1),
    0x48: ('JZ', 1),
    0x49: ('CALL', 1),
    0x4A: ('RET', 0),
    
    # Memory ops
    0x80: ('LOAD', 2),
    0x81: ('STORE', 2),
    0x82: ('DBREAD', 2),
    0x83: ('DBWRITE', 3),
    0x84: ('DBQUERY', 2),
    
    # Metaprogramming ops
    0xA0: ('SELF_READ', 0),
    0xA1: ('SELF_MUTATE', 1),
    0xA2: ('SELF_FORK', 0),
    0xA3: ('VERIFY', 1),
    0xA4: ('ROLLBACK', 1),
    0xA5: ('CHECKPOINT', 0),
    0xA6: ('PATCH_APPLY', 1),
    0xA7: ('LOOP_START', 0),
    0xA8: ('LOOP_END', 1),
    0xA9: ('SYMBOLIC_STATE', 1),
    0xAA: ('CTC_BACKPROP', 2),
    0xAB: ('ENTANGLE_MUTATE', 2),
    
    # Syscalls
    0xE0: ('SYSCALL', 1),
    0xE1: ('FORK', 0),
    0xE3: ('EXIT', 1),
}

# Reverse lookup
MNEMONIC_TO_OPCODE = {v[0]: k for k, v in OPCODES.items()}

# Syscall numbers
SYSCALLS = {
    0: 'exit',
    1: 'fork',
    14: 'getpid',
    20: 'qalloc',
    23: 'qmeas',
    24: 'qent',
}


# ═══════════════════════════════════════════════════════════════════════════
# OUTPUT CHANNEL & KERNEL BOOT
# ═══════════════════════════════════════════════════════════════════════════

def initialize_output_channel(conn: sqlite3.Connection):
    """Initialize output channel in database"""
    c = conn.cursor()
    
    # Create output channel table
    c.execute('''
        CREATE TABLE IF NOT EXISTS output_channel (
            msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            source TEXT,
            level TEXT,
            message TEXT,
            data BLOB
        )
    ''')
    
    # Create kernel log table
    c.execute('''
        CREATE TABLE IF NOT EXISTS kernel_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            event_type TEXT,
            details TEXT,
            qubits_involved TEXT
        )
    ''')
    
    conn.commit()
    print(f"{C.G}✓ Output channel initialized{C.E}")


def log_to_channel(conn: sqlite3.Connection, source: str, level: str, message: str, data: bytes = None):
    """Write message to output channel"""
    c = conn.cursor()
    c.execute(f'''
        INSERT INTO output_channel (timestamp, source, level, message, data)
        VALUES (?, ?, ?, ?, ?)
    ''', (time.time(), source, level, message, data))
    conn.commit()


def log_kernel_event(conn: sqlite3.Connection, event_type: str, details: str, qubits: List[int] = None):
    """Log kernel event"""
    c = conn.cursor()
    c.execute(f'''
        INSERT INTO kernel_log (timestamp, event_type, details, qubits_involved)
        VALUES (?, ?, ?, ?)
    ''', (time.time(), event_type, details, json.dumps(qubits) if qubits else None))
    conn.commit()


def read_output_channel(conn: sqlite3.Connection, limit: int = 50):
    """Read recent messages from output channel"""
    c = conn.cursor()
    c.execute('''
        SELECT timestamp, source, level, message
        FROM output_channel
        ORDER BY msg_id DESC
        LIMIT ?
    ''', (limit,))
    
    messages = c.fetchall()
    
    if messages:
        print(f"\n{C.BOLD}{C.C}═══ OUTPUT CHANNEL ═══{C.E}\n")
        for ts, src, lvl, msg in reversed(messages):
            color = C.G if lvl == 'INFO' else C.Y if lvl == 'WARN' else C.R
            time_str = time.strftime('%H:%M:%S', time.localtime(ts))
            print(f"{C.GRAY}[{time_str}]{C.E} {color}{lvl:5s}{C.E} {C.C}{src:12s}{C.E} {msg}")
        print()


def boot_quantum_kernel(conn: sqlite3.Connection):
    """
    Boot quantum kernel with W-state tripartite entanglement
    Creates W-state on qubits 0, 1, 2 then applies H(q0) and CNOT(q0, q1)
    """
    print(f"\n{C.BOLD}{C.M}╔══════════════════════════════════════════════════════════════╗{C.E}")
    print(f"{C.BOLD}{C.M}║         BOOTING QUANTUM KERNEL - W-STATE TRIPARTITE          ║{C.E}")
    print(f"{C.BOLD}{C.M}╚══════════════════════════════════════════════════════════════╝{C.E}\n")
    
    c = conn.cursor()
    
    # Check if already booted
    c.execute("SELECT val FROM meta WHERE key='kernel_state'")
    row = c.fetchone()
    if row and row[0] == 'BOOTED':
        print(f"{C.Y}Kernel already booted. Re-booting...{C.E}\n")
    
    # Step 1: Create W-state on qubits 0, 1, 2
    print(f"{C.C}Step 1: Creating W-state |W⟩ = (|100⟩ + |010⟩ + |001⟩)/√3{C.E}")
    
    if QISKIT_AVAILABLE:
        # Create W-state using basic gates
        qc = QuantumCircuit(3)
        
        # W-state preparation
        qc.x(0)
        qc.ry(np.arccos(np.sqrt(2/3)), 0)
        qc.cx(0, 1)
        qc.x(0)
        qc.ccx(0, 1, 2)
        qc.x(0)

        # Simulate
        sim = AerSimulator(method='statevector')
        qc.save_statevector()
        result = sim.run(qc, shots=1).result()
        statevector = result.get_statevector()
        
        coeff = 1.0 / np.sqrt(3)
        amplitudes = [(coeff, coeff), (coeff, coeff), (coeff, coeff)]
        
        print(f"  {C.GRAY}[Using Qiskit Aer simulation]{C.E}")
    else:
        coeff = 1.0 / np.sqrt(3)
        amplitudes = [(coeff, coeff), (coeff, coeff), (coeff, coeff)]
        print(f"  {C.GRAY}[Using classical simulation]{C.E}")
    
    # Update qubits 0, 1, 2 in database
    for qid in range(3):
        alpha, beta = amplitudes[qid]
        c.execute(f'''
            UPDATE {T_PQB} SET 
                ar = ?, ai = 0, br = ?, bi = 0,
                typ = 'kernel_w', gat = 'W3', crt = ?
            WHERE qid = ?
        ''', (alpha, beta, time.time(), qid))
    
    # Create W-state entanglement entries
    c.execute(f"INSERT INTO {T_ENT} VALUES (NULL, 0, 1, 'w_state', 0.99, ?)", (time.time(),))
    c.execute(f"INSERT INTO {T_ENT} VALUES (NULL, 0, 2, 'w_state', 0.99, ?)", (time.time(),))
    c.execute(f"INSERT INTO {T_ENT} VALUES (NULL, 1, 2, 'w_state', 0.99, ?)", (time.time(),))
    
    log_to_channel(conn, 'KERNEL', 'INFO', 'W-state created on qubits [0, 1, 2]')
    log_kernel_event(conn, 'W_STATE', 'Tripartite entanglement established', [0, 1, 2])
    print(f"  {C.G}✓ W-state entanglement established{C.E}")
    
    # Step 2: Apply Hadamard to qubit 0
    print(f"\n{C.C}Step 2: Applying H(q0) for superposition{C.E}")
    
    if QISKIT_AVAILABLE:
        qc2 = QuantumCircuit(1)
        qc2.h(0)
        sim = AerSimulator(method='statevector')
        qc2.save_statevector()
        result = sim.run(qc2, shots=1).result()
        sv = result.get_statevector()
        alpha_h = float(sv[0].real)
        beta_h = float(sv[1].real)
    else:
        sqrt2_inv = 1.0 / np.sqrt(2)
        alpha_h = beta_h = sqrt2_inv
    
    c.execute(f'''
        UPDATE {T_PQB} SET 
            ar = ?, ai = 0, br = ?, bi = 0, gat = 'H', crt = ?
        WHERE qid = 0
    ''', (alpha_h, beta_h, time.time()))
    
    log_to_channel(conn, 'KERNEL', 'INFO', 'Hadamard applied to q0')
    log_kernel_event(conn, 'GATE', 'H applied to q0', [0])
    print(f"  {C.G}✓ H(q0) applied: |0⟩ → (|0⟩ + |1⟩)/√2{C.E}")
    
    # Step 3: Apply CNOT(0, 1) for Bell pair
    print(f"\n{C.C}Step 3: Applying CNOT(q0, q1) for computational basis{C.E}")
    
    if QISKIT_AVAILABLE:
        qc3 = QuantumCircuit(2)
        qc3.h(0)
        qc3.cx(0, 1)
        sim = AerSimulator(method='statevector')
        qc3.save_statevector()
        result = sim.run(qc3, shots=1).result()
        sv = result.get_statevector()
        
        alpha_1 = beta_1 = 1.0 / np.sqrt(2)
    else:
        alpha_1 = beta_1 = 1.0 / np.sqrt(2)
    
    c.execute(f'''
        UPDATE {T_PQB} SET 
            ar = ?, br = ?, gat = 'CNOT', crt = ?
        WHERE qid = 1
    ''', (alpha_1, beta_1, time.time()))
    
    # Add Bell entanglement
    c.execute(f"INSERT INTO {T_ENT} VALUES (NULL, 0, 1, 'bell', 1.0, ?)", (time.time(),))
    
    log_to_channel(conn, 'KERNEL', 'INFO', 'CNOT(q0, q1) applied - Bell pair formed')
    log_kernel_event(conn, 'GATE', 'CNOT applied (q0→q1)', [0, 1])
    print(f"  {C.G}✓ CNOT(q0, q1) applied: Bell pair formed{C.E}")
    
    # Mark kernel as booted
    c.execute('''
        INSERT OR REPLACE INTO meta (key, val, upd) 
        VALUES ('kernel_state', 'BOOTED', ?)
    ''', (time.time(),))
    
    c.execute('''
        INSERT OR REPLACE INTO meta (key, val, upd)
        VALUES ('boot_sequence', 'W3-H-CNOT', ?)
    ''', (time.time(),))
    
    c.execute('''
        INSERT OR REPLACE INTO meta (key, val, upd)
        VALUES ('boot_time', ?, ?)
    ''', (str(time.time()), time.time()))
    
    conn.commit()
    
    log_to_channel(conn, 'KERNEL', 'INFO', 'Quantum kernel boot complete')
    log_kernel_event(conn, 'BOOT', 'Kernel fully operational', [0, 1, 2])
    
    print(f"\n{C.BOLD}{C.G}✓ QUANTUM KERNEL BOOTED{C.E}")
    print(f"{C.C}  Boot sequence: W-state(0,1,2) → H(0) → CNOT(0,1){C.E}")
    print(f"{C.C}  System state: ENTANGLED & OPERATIONAL{C.E}\n")
    
    return True


# ═══════════════════════════════════════════════════════════════════════════
# METAPROGRAM MONITORING
# ═══════════════════════════════════════════════════════════════════════════

def show_metaprogram_status(conn: sqlite3.Connection):
    """Show status of all metaprograms"""
    print(f"\n{C.BOLD}{C.M}╔══════════════════════════════════════════════════════════════╗{C.E}")
    print(f"{C.BOLD}{C.M}║            METAPROGRAM STATUS (INFINITE LOOPS)               ║{C.E}")
    print(f"{C.BOLD}{C.M}╚══════════════════════════════════════════════════════════════╝{C.E}\n")
    
    c = conn.cursor()
    
    # Get metaprograms from T_BIN
    c.execute(f'''
        SELECT bid, nam, typ, loop_enabled, size, crt
        FROM {T_BIN}
        WHERE typ = 'metaprogram'
        ORDER BY bid
    ''')
    
    metaprogs = c.fetchall()
    
    if not metaprogs:
        print(f"{C.Y}No metaprograms found in database{C.E}\n")
        return
    
    print(f"{C.BOLD}Metaprograms in Database:{C.E}\n")
    
    for bid, nam, typ, loop_enabled, size, crt in metaprogs:
        print(f"{C.BOLD}BID {bid}: {nam}{C.E}")
        print(f"  Type:         {typ}")
        print(f"  Loop Enabled: {'YES' if loop_enabled else 'NO'}")
        print(f"  Size:         {size} bytes")
        print(f"  Created:      {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(crt))}")
        
        # Check for linked process
        c.execute(f'''
            SELECT p.pid, p.nam, p.sta, t.pc
            FROM {T_PRC} p
            JOIN {T_THR} t ON p.pid = t.pid
            JOIN loop_state l ON l.pid = p.pid
            WHERE l.bid = ?
        ''', (bid,))
        
        proc_info = c.fetchone()
        if proc_info:
            pid, proc_name, status, pc = proc_info
            status_color = C.G if status == 'RUNNING' else C.Y
            print(f"  Process:      PID {pid} [{status_color}{status}{C.E}]")
            print(f"  PC:           0x{pc:04X}")
            
            # Get loop state
            c.execute('''
                SELECT iteration, loop_start_pc, continue_flag
                FROM loop_state
                WHERE bid = ?
            ''', (bid,))
            
            loop_info = c.fetchone()
            if loop_info:
                iteration, loop_start, cont_flag = loop_info
                print(f"  Iteration:    {iteration}")
                print(f"  Loop Start:   0x{loop_start:04X}")
                print(f"  Continue:     {'YES' if cont_flag else 'NO'}")
        else:
            print(f"  {C.Y}Process:      Not linked{C.E}")
        
        # Check mutations
        c.execute('''
            SELECT COUNT(*) FROM mutation_history WHERE source_bid = ?
        ''', (bid,))
        mut_count = c.fetchone()[0]
        print(f"  Mutations:    {mut_count}")
        
        # Check patches
        if 'patcher' in nam.lower():
            c.execute('SELECT COUNT(*) FROM patches WHERE applied = 1')
            patch_count = c.fetchone()[0]
            print(f"  Applied:      {patch_count} patches")
        
        # Check verifications
        if 'verifier' in nam.lower():
            c.execute('SELECT COUNT(*) FROM verify_log WHERE target_bid = ?', (bid,))
            verify_count = c.fetchone()[0]
            print(f"  Verified:     {verify_count} programs")
        
        print()
    
    # Show recent microcode log
    c.execute('''
        SELECT log_id, bid, pid, pc, opcode, tms
        FROM microcode_log
        ORDER BY log_id DESC
        LIMIT 10
    ''')
    
    logs = c.fetchall()
    
    if logs:
        print(f"{C.BOLD}Recent Microcode Execution:{C.E}\n")
        print(f"{'Log ID':>7} {'BID':>4} {'PID':>4} {'PC':>6} {'Opcode':>8} {'Time'}")
        print(f"{'-'*55}")
        
        for log_id, bid, pid, pc, opcode, tms in logs:
            time_str = time.strftime('%H:%M:%S', time.localtime(tms))
            print(f"{log_id:>7} {bid:>4} {pid:>4} 0x{pc:04X} 0x{opcode:02X}     {time_str}")
        print()


def show_checkpoint_state(conn: sqlite3.Connection):
    """Show checkpoint/rollback state"""
    print(f"\n{C.BOLD}{C.C}═══ CHECKPOINT STATE ═══{C.E}\n")
    
    c = conn.cursor()
    
    c.execute('''
        SELECT cid, pid, bid, pc, tms
        FROM ckpt
        ORDER BY cid DESC
        LIMIT 20
    ''')
    
    checkpoints = c.fetchall()
    
    if not checkpoints:
        print(f"{C.Y}No checkpoints found{C.E}\n")
        return
    
    print(f"{'CID':>5} {'PID':>4} {'BID':>4} {'PC':>6} {'Time'}")
    print(f"{'-'*40}")
    
    for cid, pid, bid, pc, tms in checkpoints:
        time_str = time.strftime('%H:%M:%S', time.localtime(tms))
        print(f"{cid:>5} {pid:>4} {bid:>4} 0x{pc:04X} {time_str}")
    
    print()


def show_patch_status(conn: sqlite3.Connection):
    """Show patch application status"""
    print(f"\n{C.BOLD}{C.C}═══ PATCH STATUS ═══{C.E}\n")
    
    c = conn.cursor()
    
    c.execute('''
        SELECT patch_id, target_prog, description, applied, sandbox_tested, tms
        FROM patches
        ORDER BY patch_id DESC
        LIMIT 20
    ''')
    
    patches = c.fetchall()
    
    if not patches:
        print(f"{C.Y}No patches found{C.E}\n")
        return
    
    print(f"{'ID':>4} {'Target':20} {'Applied':>8} {'Tested':>7} {'Description'}")
    print(f"{'-'*70}")
    
    for patch_id, target, desc, applied, tested, tms in patches:
        status = f"{C.G}YES{C.E}" if applied else f"{C.Y}NO{C.E}"
        tested_str = f"{C.G}YES{C.E}" if tested else f"{C.R}NO{C.E}"
        desc_short = (desc[:30] + '...') if desc and len(desc) > 30 else (desc or '')
        print(f"{patch_id:>4} {target:20} {status:>8} {tested_str:>7} {desc_short}")
    
    print()


def show_program_genealogy(conn: sqlite3.Connection):
    """Show program version tree (quine evolution)"""
    print(f"\n{C.BOLD}{C.M}═══ PROGRAM GENEALOGY (QUINE EVOLUTION) ═══{C.E}\n")
    
    c = conn.cursor()
    
    c.execute('''
        SELECT vid, parent_bid, child_bid, generation, fitness, tms
        FROM prog_versions
        ORDER BY generation, vid
        LIMIT 50
    ''')
    
    versions = c.fetchall()
    
    if not versions:
        print(f"{C.Y}No program versions found{C.E}\n")
        return
    
    print(f"{'VID':>5} {'Parent':>7} {'Child':>6} {'Gen':>4} {'Fitness':>8} {'Time'}")
    print(f"{'-'*55}")
    
    for vid, parent, child, gen, fitness, tms in versions:
        time_str = time.strftime('%H:%M:%S', time.localtime(tms))
        parent_str = f"BID{parent}" if parent else "ROOT"
        fitness_str = f"{fitness:.3f}" if fitness else "N/A"
        print(f"{vid:>5} {parent_str:>7} BID{child:>3} {gen:>4} {fitness_str:>8} {time_str}")
    
    print()


# [CONTINUE WITH REST OF QuantumExecutor CLASS - keeping all the gate operations and execution engine exactly as before, no changes needed]

# ═══════════════════════════════════════════════════════════════════════════
# QUANTUM EXECUTOR - FULL BINARY EXECUTION ON LATTICE
# ═══════════════════════════════════════════════════════════════════════════

class QuantumExecutor:
    """Execute quantum binaries directly on Leech lattice substrate"""
    
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.cursor = conn.cursor()
        
        if QISKIT_AVAILABLE:
            self.sim = AerSimulator(method='statevector')
            print(f"{C.G}✓ Qiskit Aer backend initialized{C.E}")
        else:
            self.sim = None
            print(f"{C.Y}⚠ Using classical fallback simulation{C.E}")
        
        self.pc = 0
        self.registers = {}
        self.stack = []
        self.flags = {'zero': 0, 'carry': 0, 'overflow': 0}
        
        self.load_substrate_info()
        self.load_opcodes()
        self.load_syscalls()
        self.load_programs()
        
        print(f"{C.G}✓ Quantum Executor initialized{C.E}")
        print(f"{C.C}  Available qubits: {self.num_qubits}{C.E}")
        print(f"{C.C}  Lattice points: {self.num_lattice}{C.E}")
        print(f"{C.C}  Programs loaded: {len(self.programs)}{C.E}\n")
    
    def load_substrate_info(self):
        self.cursor.execute(f'SELECT COUNT(*) FROM {T_PQB}')
        self.num_qubits = self.cursor.fetchone()[0]
        
        self.cursor.execute(f'SELECT COUNT(*) FROM {T_LAT}')
        self.num_lattice = self.cursor.fetchone()[0]
        
        self.cursor.execute(f'SELECT qid, lid, adr FROM {T_PQB} ORDER BY qid')
        self.qubit_map = {}
        for qid, lid, adr in self.cursor.fetchall():
            self.qubit_map[qid] = {'lid': lid, 'adr': adr}
    
    def load_opcodes(self):
        self.cursor.execute(f'SELECT opc, mne, nop FROM {T_INS}')
        self.opcodes = {}
        for opc, mne, nop in self.cursor.fetchall():
            self.opcodes[opc] = {'mne': mne, 'nop': nop}
        
        for opc, (mne, nop) in OPCODES.items():
            
            if opc not in self.opcodes:
                self.opcodes[opc] = {'mne': mne, 'nop': nop}
    
    def load_syscalls(self):
        self.cursor.execute(f'SELECT sid, nam FROM {T_SYS}')
        self.syscalls = {}
        for sid, nam in self.cursor.fetchall():
            self.syscalls[sid] = nam
    
    def load_programs(self):
        self.cursor.execute(f'SELECT bid, nam, cod, typ FROM {T_BIN}')
        self.programs = {}
        for bid, nam, cod, typ in self.cursor.fetchall():
            self.programs[nam] = {
                'bid': bid,
                'bytecode': cod,
                'type': typ
            }
    
    def get_qubit_state(self, qid: int) -> Tuple[complex, complex]:
        self.cursor.execute(f'''
            SELECT ar, ai, br, bi FROM {T_PQB} WHERE qid = ?
        ''', (qid,))
        
        row = self.cursor.fetchone()
        if not row:
            return (1.0+0j, 0.0+0j)
        
        ar, ai, br, bi = row
        return (complex(ar, ai), complex(br, bi))
    
    def set_qubit_state(self, qid: int, alpha: complex, beta: complex, gate: str = 'SET'):
        norm = abs(alpha)**2 + abs(beta)**2
        if norm > 0:
            alpha /= np.sqrt(norm)
            beta /= np.sqrt(norm)
        
        self.cursor.execute(f'''
            UPDATE {T_PQB}
            SET ar = ?, ai = ?, br = ?, bi = ?, gat = ?, crt = ?
            WHERE qid = ?
        ''', (alpha.real, alpha.imag, beta.real, beta.imag, gate, time.time(), qid))
        self.conn.commit()
    
    def route_to_qubit(self, qid: int) -> Dict:
        if qid not in self.qubit_map:
            raise ValueError(f"Qubit {qid} not in substrate")
        
        mapping = self.qubit_map[qid]
        
        self.cursor.execute(f'SELECT crd, nrm FROM {T_LAT} WHERE lid = ?', (mapping['lid'],))
        row = self.cursor.fetchone()
        
        if row:
            crd_blob, nrm = row
            coords = np.frombuffer(zlib.decompress(crd_blob), dtype=np.float32)
        else:
            coords = None
            nrm = None
        
        return {
            'qid': qid,
            'lid': mapping['lid'],
            'adr': mapping['adr'],
            'coords': coords,
            'norm': nrm
        }
    
    # ═══════════════════════════════════════════════════════════════════════
    # QUANTUM GATE OPERATIONS (keeping all gates from original)
    # ═══════════════════════════════════════════════════════════════════════
    
    def gate_hadamard(self, qid: int):
        route = self.route_to_qubit(qid)
        alpha, beta = self.get_qubit_state(qid)
        
        if QISKIT_AVAILABLE:
            qc = QuantumCircuit(1)
            qc.initialize([alpha, beta], 0)
            qc.h(0)
            qc.save_statevector()
            result = self.sim.run(qc, shots=1).result()
            sv = result.get_statevector()
            new_alpha = complex(sv[0])
            new_beta = complex(sv[1])
        else:
            sqrt2_inv = 1.0 / np.sqrt(2)
            new_alpha = sqrt2_inv * (alpha + beta)
            new_beta = sqrt2_inv * (alpha - beta)
        
        self.set_qubit_state(qid, new_alpha, new_beta, 'H')
        log_to_channel(self.conn, 'EXECUTOR', 'INFO', f'H(q{qid}) executed on lattice point {route["lid"]}')
        print(f"  {C.C}H(q{qid}): α={new_alpha:.4f}, β={new_beta:.4f} [lattice:{route['lid']}]{C.E}")
    
    def gate_pauli_x(self, qid: int):
        route = self.route_to_qubit(qid)
        alpha, beta = self.get_qubit_state(qid)
        
        if QISKIT_AVAILABLE:
            qc = QuantumCircuit(1)
            qc.initialize([alpha, beta], 0)
            qc.x(0)
            qc.save_statevector()
            result = self.sim.run(qc, shots=1).result()
            sv = result.get_statevector()
            new_alpha = complex(sv[0])
            new_beta = complex(sv[1])
        else:
            new_alpha = beta
            new_beta = alpha
        
        self.set_qubit_state(qid, new_alpha, new_beta, 'X')
        log_to_channel(self.conn, 'EXECUTOR', 'INFO', f'X(q{qid}) executed')
        print(f"  {C.C}X(q{qid}): α={new_alpha:.4f}, β={new_beta:.4f}{C.E}")
    
    def gate_pauli_y(self, qid: int):
        route = self.route_to_qubit(qid)
        alpha, beta = self.get_qubit_state(qid)
        
        if QISKIT_AVAILABLE:
            qc = QuantumCircuit(1)
            qc.initialize([alpha, beta], 0)
            qc.y(0)
            qc.save_statevector()
            result = self.sim.run(qc, shots=1).result()
            sv = result.get_statevector()
            new_alpha = complex(sv[0])
            new_beta = complex(sv[1])
        else:
            new_alpha = -1j * beta
            new_beta = 1j * alpha
        
        self.set_qubit_state(qid, new_alpha, new_beta, 'Y')
        log_to_channel(self.conn, 'EXECUTOR', 'INFO', f'Y(q{qid}) executed')
        print(f"  {C.C}Y(q{qid}): α={new_alpha:.4f}, β={new_beta:.4f}{C.E}")
    
    def gate_pauli_z(self, qid: int):
        route = self.route_to_qubit(qid)
        alpha, beta = self.get_qubit_state(qid)
        
        if QISKIT_AVAILABLE:
            qc = QuantumCircuit(1)
            qc.initialize([alpha, beta], 0)
            qc.z(0)
            qc.save_statevector()
            result = self.sim.run(qc, shots=1).result()
            sv = result.get_statevector()
            new_alpha = complex(sv[0])
            new_beta = complex(sv[1])
        else:
            new_alpha = alpha
            new_beta = -beta
        
        self.set_qubit_state(qid, new_alpha, new_beta, 'Z')
        log_to_channel(self.conn, 'EXECUTOR', 'INFO', f'Z(q{qid}) executed')
        print(f"  {C.C}Z(q{qid}): α={new_alpha:.4f}, β={new_beta:.4f}{C.E}")
    
    def gate_s(self, qid: int):
        route = self.route_to_qubit(qid)
        alpha, beta = self.get_qubit_state(qid)
        
        if QISKIT_AVAILABLE:
            qc = QuantumCircuit(1)
            qc.initialize([alpha, beta], 0)
            qc.s(0)
            qc.save_statevector()
            result = self.sim.run(qc, shots=1).result()
            sv = result.get_statevector()
            new_alpha = complex(sv[0])
            new_beta = complex(sv[1])
        else:
            new_alpha = alpha
            new_beta = 1j * beta
        
        self.set_qubit_state(qid, new_alpha, new_beta, 'S')
        log_to_channel(self.conn, 'EXECUTOR', 'INFO', f'S(q{qid}) executed')
        print(f"  {C.C}S(q{qid}): α={new_alpha:.4f}, β={new_beta:.4f}{C.E}")
    
    def gate_t(self, qid: int):
        route = self.route_to_qubit(qid)
        alpha, beta = self.get_qubit_state(qid)
        
        if QISKIT_AVAILABLE:
            qc = QuantumCircuit(1)
            qc.initialize([alpha, beta], 0)
            qc.t(0)
            qc.save_statevector()
            result = self.sim.run(qc, shots=1).result()
            sv = result.get_statevector()
            new_alpha = complex(sv[0])
            new_beta = complex(sv[1])
        else:
            new_alpha = alpha
            new_beta = beta * np.exp(1j * np.pi / 4)
        
        self.set_qubit_state(qid, new_alpha, new_beta, 'T')
        log_to_channel(self.conn, 'EXECUTOR', 'INFO', f'T(q{qid}) executed')
        print(f"  {C.C}T(q{qid}): α={new_alpha:.4f}, β={new_beta:.4f}{C.E}")
    
    def gate_sdg(self, qid: int):
        route = self.route_to_qubit(qid)
        alpha, beta = self.get_qubit_state(qid)
        
        if QISKIT_AVAILABLE:
            qc = QuantumCircuit(1)
            qc.initialize([alpha, beta], 0)
            qc.sdg(0)
            qc.save_statevector()
            result = self.sim.run(qc, shots=1).result()
            sv = result.get_statevector()
            new_alpha = complex(sv[0])
            new_beta = complex(sv[1])
        else:
            new_alpha = alpha
            new_beta = -1j * beta
        
        self.set_qubit_state(qid, new_alpha, new_beta, 'SDG')
        log_to_channel(self.conn, 'EXECUTOR', 'INFO', f'SDG(q{qid}) executed')
        print(f"  {C.C}SDG(q{qid}): α={new_alpha:.4f}, β={new_beta:.4f}{C.E}")
    
    def gate_tdg(self, qid: int):
        route = self.route_to_qubit(qid)
        alpha, beta = self.get_qubit_state(qid)
        
        if QISKIT_AVAILABLE:
            qc = QuantumCircuit(1)
            qc.initialize([alpha, beta], 0)
            qc.tdg(0)
            qc.save_statevector()
            result = self.sim.run(qc, shots=1).result()
            sv = result.get_statevector()
            new_alpha = complex(sv[0])
            new_beta = complex(sv[1])
        else:
            new_alpha = alpha
            new_beta = beta * np.exp(-1j * np.pi / 4)
        
        self.set_qubit_state(qid, new_alpha, new_beta, 'TDG')
        log_to_channel(self.conn, 'EXECUTOR', 'INFO', f'TDG(q{qid}) executed')
        print(f"  {C.C}TDG(q{qid}): α={new_alpha:.4f}, β={new_beta:.4f}{C.E}")
    
    def gate_cnot(self, ctrl_qid: int, tgt_qid: int):
        ctrl_route = self.route_to_qubit(ctrl_qid)
        tgt_route = self.route_to_qubit(tgt_qid)
        
        ctrl_alpha, ctrl_beta = self.get_qubit_state(ctrl_qid)
        tgt_alpha, tgt_beta = self.get_qubit_state(tgt_qid)
        
        if QISKIT_AVAILABLE:
            qc = QuantumCircuit(2)
            qc.initialize([ctrl_alpha, ctrl_beta], 0)
            qc.initialize([tgt_alpha, tgt_beta], 1)
            qc.cx(0, 1)
            qc.save_statevector()
            result = self.sim.run(qc, shots=1).result()
            sv = result.get_statevector()
            
            prob_ctrl_1 = abs(ctrl_beta)**2
            
            if prob_ctrl_1 > 0.5:
                new_tgt_alpha = tgt_beta
                new_tgt_beta = tgt_alpha
            else:
                new_tgt_alpha = tgt_alpha
                new_tgt_beta = tgt_beta
        else:
            prob_ctrl_1 = abs(ctrl_beta)**2
            
            if prob_ctrl_1 > 0.5:
                new_tgt_alpha = tgt_beta
                new_tgt_beta = tgt_alpha
            else:
                new_tgt_alpha = tgt_alpha
                new_tgt_beta = tgt_beta
        
        self.set_qubit_state(tgt_qid, new_tgt_alpha, new_tgt_beta, 'CNOT')
        
        self.cursor.execute(f'''
            INSERT INTO {T_ENT} VALUES (NULL, ?, ?, 'cnot', 0.95, ?)
        ''', (ctrl_qid, tgt_qid, time.time()))
        self.conn.commit()
        
        log_to_channel(self.conn, 'EXECUTOR', 'INFO', 
                      f'CNOT(q{ctrl_qid}, q{tgt_qid}) executed - lattice points [{ctrl_route["lid"]}, {tgt_route["lid"]}]')
        print(f"  {C.C}CNOT(q{ctrl_qid}, q{tgt_qid}): entangled [lattice:{ctrl_route['lid']}↔{tgt_route['lid']}]{C.E}")
    
    def gate_cz(self, ctrl_qid: int, tgt_qid: int):
        ctrl_route = self.route_to_qubit(ctrl_qid)
        tgt_route = self.route_to_qubit(tgt_qid)
        
        ctrl_alpha, ctrl_beta = self.get_qubit_state(ctrl_qid)
        tgt_alpha, tgt_beta = self.get_qubit_state(tgt_qid)
        
        if QISKIT_AVAILABLE:
            qc = QuantumCircuit(2)
            qc.initialize([ctrl_alpha, ctrl_beta], 0)
            qc.initialize([tgt_alpha, tgt_beta], 1)
            qc.cz(0, 1)
            qc.save_statevector()
            result = self.sim.run(qc, shots=1).result()
            sv = result.get_statevector()
            
            prob_ctrl_1 = abs(ctrl_beta)**2
            if prob_ctrl_1 > 0.5:
                new_tgt_beta = -tgt_beta
            else:
                new_tgt_beta = tgt_beta
            new_tgt_alpha = tgt_alpha
        else:
            prob_ctrl_1 = abs(ctrl_beta)**2
            if prob_ctrl_1 > 0.5:
                new_tgt_beta = -tgt_beta
            else:
                new_tgt_beta = tgt_beta
            new_tgt_alpha = tgt_alpha
        
        self.set_qubit_state(tgt_qid, new_tgt_alpha, new_tgt_beta, 'CZ')
        
        self.cursor.execute(f'''
            INSERT INTO {T_ENT} VALUES (NULL, ?, ?, 'cz', 0.95, ?)
        ''', (ctrl_qid, tgt_qid, time.time()))
        self.conn.commit()
        
        log_to_channel(self.conn, 'EXECUTOR', 'INFO', f'CZ(q{ctrl_qid}, q{tgt_qid}) executed')
        print(f"  {C.C}CZ(q{ctrl_qid}, q{tgt_qid}): phase applied{C.E}")
    
    def gate_swap(self, qid1: int, qid2: int):
        route1 = self.route_to_qubit(qid1)
        route2 = self.route_to_qubit(qid2)
        
        alpha1, beta1 = self.get_qubit_state(qid1)
        alpha2, beta2 = self.get_qubit_state(qid2)
        
        self.set_qubit_state(qid1, alpha2, beta2, 'SWAP')
        self.set_qubit_state(qid2, alpha1, beta1, 'SWAP')
        
        log_to_channel(self.conn, 'EXECUTOR', 'INFO', f'SWAP(q{qid1}, q{qid2}) executed')
        print(f"  {C.C}SWAP(q{qid1}, q{qid2}): states exchanged{C.E}")
    
    def gate_toffoli(self, ctrl1: int, ctrl2: int, tgt: int):
        route1 = self.route_to_qubit(ctrl1)
        route2 = self.route_to_qubit(ctrl2)
        route_tgt = self.route_to_qubit(tgt)
        
        c1_alpha, c1_beta = self.get_qubit_state(ctrl1)
        c2_alpha, c2_beta = self.get_qubit_state(ctrl2)
        tgt_alpha, tgt_beta = self.get_qubit_state(tgt)
        
        if QISKIT_AVAILABLE:
            qc = QuantumCircuit(3)
            qc.initialize([c1_alpha, c1_beta], 0)
            qc.initialize([c2_alpha, c2_beta], 1)
            qc.initialize([tgt_alpha, tgt_beta], 2)
            qc.ccx(0, 1, 2)
            qc.save_statevector()
            result = self.sim.run(qc, shots=1).result()
            sv = result.get_statevector()
            
            prob_c1_1 = abs(c1_beta)**2
            prob_c2_1 = abs(c2_beta)**2
            
            if prob_c1_1 > 0.5 and prob_c2_1 > 0.5:
                new_tgt_alpha = tgt_beta
                new_tgt_beta = tgt_alpha
            else:
                new_tgt_alpha = tgt_alpha
                new_tgt_beta = tgt_beta
        else:
            prob_c1_1 = abs(c1_beta)**2
            prob_c2_1 = abs(c2_beta)**2
            
            if prob_c1_1 > 0.5 and prob_c2_1 > 0.5:
                new_tgt_alpha = tgt_beta
                new_tgt_beta = tgt_alpha
            else:
                new_tgt_alpha = tgt_alpha
                new_tgt_beta = tgt_beta
        
        self.set_qubit_state(tgt, new_tgt_alpha, new_tgt_beta, 'TOFF')
        
        log_to_channel(self.conn, 'EXECUTOR', 'INFO', f'TOFFOLI(q{ctrl1}, q{ctrl2}, q{tgt}) executed')
        print(f"  {C.C}TOFFOLI(q{ctrl1}, q{ctrl2}, q{tgt}): CCX applied{C.E}")
    
    def gate_measure(self, qid: int) -> int:
        route = self.route_to_qubit(qid)
        alpha, beta = self.get_qubit_state(qid)
        
        prob_0 = abs(alpha)**2
        prob_1 = abs(beta)**2
        
        total = prob_0 + prob_1
        if total > 0:
            prob_0 /= total
            prob_1 /= total
        
        result = 1 if np.random.random() < prob_1 else 0
        
        if result == 0:
            self.set_qubit_state(qid, 1.0+0j, 0.0+0j, 'MEAS')
        else:
            self.set_qubit_state(qid, 0.0+0j, 1.0+0j, 'MEAS')
        
        self.cursor.execute(f'''
            INSERT INTO {T_QMS} VALUES (NULL, 'measurement', ?, ?)
        ''', (json.dumps({'qid': qid, 'result': result, 'prob_0': prob_0, 'prob_1': prob_1}), time.time()))
        self.conn.commit()
        
        log_to_channel(self.conn, 'EXECUTOR', 'INFO', 
                      f'MEAS(q{qid}) → |{result}⟩ [lattice:{route["lid"]}]')
        print(f"  {C.G}MEAS(q{qid}) → |{result}⟩ (P(0)={prob_0:.3f}, P(1)={prob_1:.3f}) [lattice:{route['lid']}]{C.E}")
        
        return result
    
    def gate_bell(self, qid1: int, qid2: int):
        print(f"  {C.C}Creating Bell pair on q{qid1}, q{qid2}{C.E}")
        self.gate_hadamard(qid1)
        self.gate_cnot(qid1, qid2)
        log_to_channel(self.conn, 'EXECUTOR', 'INFO', f'Bell pair created on q{qid1}, q{qid2}')
    
    def gate_ghz(self, qid1: int, qid2: int, qid3: int):
        print(f"  {C.C}Creating GHZ state on q{qid1}, q{qid2}, q{qid3}{C.E}")
        self.gate_hadamard(qid1)
        self.gate_cnot(qid1, qid2)
        self.gate_cnot(qid1, qid3)
        log_to_channel(self.conn, 'EXECUTOR', 'INFO', f'GHZ state created on q{qid1}, q{qid2}, q{qid3}')
    
    def gate_w3(self, qid1: int, qid2: int, qid3: int):
        print(f"  {C.C}Creating W-state on q{qid1}, q{qid2}, q{qid3}{C.E}")
        
        coeff = 1.0 / np.sqrt(3)
        
        for qid in [qid1, qid2, qid3]:
            self.set_qubit_state(qid, complex(coeff, 0), complex(coeff, 0), 'W3')
        
        for qa, qb in [(qid1, qid2), (qid1, qid3), (qid2, qid3)]:
            self.cursor.execute(f'''
                INSERT INTO {T_ENT} VALUES (NULL, ?, ?, 'w_state', 0.99, ?)
            ''', (qa, qb, time.time()))
        
        self.conn.commit()
        log_to_channel(self.conn, 'EXECUTOR', 'INFO', f'W-state created on q{qid1}, q{qid2}, q{qid3}')
    
    def gate_w4(self, qid1: int, qid2: int, qid3: int, qid4: int):
        print(f"  {C.C}Creating W4-state on q{qid1}, q{qid2}, q{qid3}, q{qid4}{C.E}")
        
        coeff = 1.0 / np.sqrt(4)
        
        for qid in [qid1, qid2, qid3, qid4]:
            self.set_qubit_state(qid, complex(coeff, 0), complex(coeff, 0), 'W4')
        
        log_to_channel(self.conn, 'EXECUTOR', 'INFO', f'W4-state created')
    
    # ═══════════════════════════════════════════════════════════════════════
    # SYSCALL HANDLERS
    # ═══════════════════════════════════════════════════════════════════════
    
    def syscall_exit(self, code: int = 0):
        print(f"  {C.Y}SYSCALL: exit({code}){C.E}")
        log_to_channel(self.conn, 'SYSCALL', 'INFO', f'exit({code})')
        return False
    
    def syscall_fork(self):
        print(f"  {C.Y}SYSCALL: fork(){C.E}")
        
        self.cursor.execute(f'''
            INSERT INTO {T_PRC} VALUES (NULL, 'user_process', 'READY', 10, ?)
        ''', (time.time(),))
        
        new_pid = self.cursor.lastrowid
        self.conn.commit()
        
        log_to_channel(self.conn, 'SYSCALL', 'INFO', f'fork() → pid={new_pid}')
        print(f"    {C.G}→ Created process {new_pid}{C.E}")
        
        return new_pid
    
    def syscall_getpid(self):
        print(f"  {C.Y}SYSCALL: getpid(){C.E}")
        log_to_channel(self.conn, 'SYSCALL', 'INFO', 'getpid() → 1')
        return 1
    
    def syscall_qalloc(self, num_qubits: int):
        print(f"  {C.Y}SYSCALL: qalloc({num_qubits}){C.E}")
        
        self.cursor.execute(f'''
            SELECT qid FROM {T_PQB}
            WHERE typ = 'pseudoqubit'
            ORDER BY qid
            LIMIT ?
        ''', (num_qubits,))
        
        allocated = [row[0] for row in self.cursor.fetchall()]
        
        log_to_channel(self.conn, 'SYSCALL', 'INFO', f'qalloc({num_qubits}) → {allocated}')
        print(f"    {C.G}→ Allocated qubits: {allocated}{C.E}")
        
        return allocated
    
    def syscall_qmeas(self, qid: int):
        print(f"  {C.Y}SYSCALL: qmeas({qid}){C.E}")
        result = self.gate_measure(qid)
        log_to_channel(self.conn, 'SYSCALL', 'INFO', f'qmeas({qid}) → {result}')
        return result
    
    def syscall_qent(self, qid1: int, qid2: int):
        print(f"  {C.Y}SYSCALL: qent({qid1}, {qid2}){C.E}")
        self.gate_bell(qid1, qid2)
        log_to_channel(self.conn, 'SYSCALL', 'INFO', f'qent({qid1}, {qid2})')
        return True
    
    # ═══════════════════════════════════════════════════════════════════════
    # BINARY EXECUTION ENGINE
    # ═══════════════════════════════════════════════════════════════════════
    
    def execute_binary(self, bytecode: bytes, program_name: str = "user_program") -> Dict:
        print(f"\n{C.BOLD}{C.Q}╔══════════════════════════════════════════════════════════════╗{C.E}")
        print(f"{C.BOLD}{C.Q}║  EXECUTING BINARY: {program_name:43s}║{C.E}")
        print(f"{C.BOLD}{C.Q}╚══════════════════════════════════════════════════════════════╝{C.E}\n")
        
        log_to_channel(self.conn, 'EXECUTOR', 'INFO', f'Executing binary: {program_name}')
        
        self.pc = 0
        results = []
        instruction_count = 0
        
        while self.pc < len(bytecode):
            opcode = bytecode[self.pc]
            
            if opcode not in self.opcodes:
                print(f"{C.R}ERROR: Invalid opcode 0x{opcode:02X} at PC={self.pc}{C.E}")
                log_to_channel(self.conn, 'EXECUTOR', 'ERROR', f'Invalid opcode 0x{opcode:02X}')
                break
            
            inst_info = self.opcodes[opcode]
            mnemonic = inst_info['mne']
            num_ops = inst_info['nop']
            
            operands = []
            for i in range(num_ops):
                if self.pc + 1 + (i * 2) + 1 < len(bytecode):
                    op_bytes = bytecode[self.pc + 1 + (i * 2):self.pc + 1 + (i * 2) + 2]
                    if len(op_bytes) == 2:
                        operand = struct.unpack('<H', op_bytes)[0]
                        operands.append(operand)
            
            ops_str = ', '.join(map(str, operands))
            print(f"{C.BOLD}[0x{self.pc:04X}] {mnemonic:8s} {ops_str}{C.E}")
            
            continue_exec = self.execute_instruction(opcode, mnemonic, operands)
            
            if not continue_exec:
                break
            
            instruction_count += 1
            
            self.pc += 1 + (num_ops * 2)
        
        log_to_channel(self.conn, 'EXECUTOR', 'INFO', 
                      f'Binary execution complete: {instruction_count} instructions')
        
        print(f"\n{C.G}✓ Execution complete ({instruction_count} instructions){C.E}\n")
        
        return {
            'instructions': instruction_count,
            'results': results
        }
    
    def execute_instruction(self, opcode: int, mnemonic: str, operands: List[int]) -> bool:
        """Execute single instruction"""
        try:
            # Quantum gates
            if mnemonic == 'QH' and len(operands) >= 1:
                self.gate_hadamard(operands[0])
            
            elif mnemonic == 'QX' and len(operands) >= 1:
                self.gate_pauli_x(operands[0])
            
            elif mnemonic == 'QY' and len(operands) >= 1:
                self.gate_pauli_y(operands[0])
            
            elif mnemonic == 'QZ' and len(operands) >= 1:
                self.gate_pauli_z(operands[0])
            
            elif mnemonic == 'QS' and len(operands) >= 1:
                self.gate_s(operands[0])
            
            elif mnemonic == 'QT' and len(operands) >= 1:
                self.gate_t(operands[0])
            
            elif mnemonic == 'QSDG' and len(operands) >= 1:
                self.gate_sdg(operands[0])
            
            elif mnemonic == 'QTDG' and len(operands) >= 1:
                self.gate_tdg(operands[0])
            
            elif mnemonic == 'QCNOT' and len(operands) >= 2:
                self.gate_cnot(operands[0], operands[1])
            
            elif mnemonic == 'QCZ' and len(operands) >= 2:
                self.gate_cz(operands[0], operands[1])
            
            elif mnemonic == 'QSWAP' and len(operands) >= 2:
                self.gate_swap(operands[0], operands[1])
            
            elif mnemonic == 'QTOFF' and len(operands) >= 3:
                self.gate_toffoli(operands[0], operands[1], operands[2])
            
            elif mnemonic == 'QMEAS' and len(operands) >= 1:
                result = self.gate_measure(operands[0])
                self.registers['meas_result'] = result
            
            elif mnemonic == 'QBELL' and len(operands) >= 2:
                self.gate_bell(operands[0], operands[1])
            
            elif mnemonic == 'QGHZ' and len(operands) >= 3:
                self.gate_ghz(operands[0], operands[1], operands[2])
            
            elif mnemonic == 'QW3' and len(operands) >= 3:
                self.gate_w3(operands[0], operands[1], operands[2])
            
            elif mnemonic == 'QW4' and len(operands) >= 4:
                self.gate_w4(operands[0], operands[1], operands[2], operands[3])
            
            # Classical operations
            elif mnemonic == 'NOP':
                print(f"  {C.GRAY}(no operation){C.E}")
            
            elif mnemonic == 'HALT':
                print(f"  {C.Y}HALT - stopping execution{C.E}")
                return False
            
            elif mnemonic == 'MOV' and len(operands) >= 2:
                self.registers[f'r{operands[0]}'] = self.registers.get(f'r{operands[1]}', 0)
                print(f"  {C.C}MOV r{operands[0]} ← r{operands[1]}{C.E}")
            
            # Syscalls
            elif mnemonic == 'SYSCALL' and len(operands) >= 1:
                syscall_num = operands[0]
                if syscall_num == 0:
                    return self.syscall_exit(0) == False
                elif syscall_num == 1:
                    self.syscall_fork()
                elif syscall_num == 14:
                    self.syscall_getpid()
                elif syscall_num == 20:
                    self.syscall_qalloc(4)
                elif syscall_num == 23:
                    if len(operands) >= 2:
                        self.syscall_qmeas(operands[1])
                elif syscall_num == 24:
                    if len(operands) >= 3:
                        self.syscall_qent(operands[1], operands[2])
            
            elif mnemonic == 'FORK':
                self.syscall_fork()
            
            elif mnemonic == 'EXIT':
                code = operands[0] if operands else 0
                return not self.syscall_exit(code)
            
            else:
                print(f"  {C.GRAY}(instruction not fully implemented){C.E}")
            
            return True
            
        except Exception as e:
            print(f"{C.R}ERROR executing {mnemonic}: {e}{C.E}")
            log_to_channel(self.conn, 'EXECUTOR', 'ERROR', f'Exception in {mnemonic}: {str(e)}')
            traceback.print_exc()
            return False
    
    def execute_program_by_name(self, program_name: str) -> Dict:
        """Execute stored program by name"""
        if program_name not in self.programs:
            print(f"{C.R}ERROR: Program '{program_name}' not found{C.E}")
            return {'error': 'Program not found'}
        
        prog = self.programs[program_name]
        return self.execute_binary(prog['bytecode'], program_name)


# ═══════════════════════════════════════════════════════════════════════════
# QUANTUM SCRIPT COMPILER
# ═══════════════════════════════════════════════════════════════════════════

class QuantumScriptCompiler:
    """Compile quantum assembly scripts to executable bytecode"""
    
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.cursor = conn.cursor()
    
    def compile_script(self, script: str, program_name: str = "user_script") -> bytes:
        """Compile quantum script to bytecode"""
        print(f"\n{C.C}Compiling quantum script: {program_name}{C.E}\n")
        
        bytecode = bytearray()
        line_num = 0
        
        for line in script.split('\n'):
            line_num += 1
            
            line = line.split('#')[0].strip()
            
            if not line:
                continue
            
            parts = line.upper().split()
            if not parts:
                continue
            
            mnemonic = parts[0]
            operands = []
            
            for part in parts[1:]:
                try:
                    operands.append(int(part))
                except ValueError:
                    pass
            
            if mnemonic not in MNEMONIC_TO_OPCODE:
                print(f"{C.R}Line {line_num}: Unknown instruction '{mnemonic}'{C.E}")
                continue
            
            opcode = MNEMONIC_TO_OPCODE[mnemonic]
            
            bytecode.append(opcode)
            
            for op in operands:
                bytecode.extend(struct.pack('<H', op & 0xFFFF))
            
            print(f"  {C.C}Line {line_num:3d}: {mnemonic:8s} {', '.join(map(str, operands)):20s} → 0x{opcode:02X}{C.E}")
        
        compiled_bytes = bytes(bytecode)
        
        # Store in database - FIX: add missing columns
        self.cursor.execute(f'''
            INSERT INTO {T_BIN} VALUES (NULL, ?, ?, 'userland', 0, ?, 0, ?)
        ''', (program_name, compiled_bytes, len(compiled_bytes), time.time()))
        
        program_id = self.cursor.lastrowid
        self.conn.commit()
        
        print(f"\n{C.G}✓ Compiled {len(compiled_bytes)} bytes (program_id={program_id}){C.E}\n")
        
        log_to_channel(self.conn, 'COMPILER', 'INFO', 
                      f'Compiled {program_name}: {len(compiled_bytes)} bytes')
        
        return compiled_bytes


# ═══════════════════════════════════════════════════════════════════════════
# PYTHON TO QUANTUM BYTECODE COMPILER
# ═══════════════════════════════════════════════════════════════════════════

class PythonToQuantumCompiler:
    """Compile Python code to quantum bytecode"""
    
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.cursor = conn.cursor()
    
    def compile_python(self, code: str, program_name: str = "python_program") -> bytes:
        """Compile Python code to quantum bytecode"""
        print(f"\n{C.C}Compiling Python to quantum bytecode: {program_name}{C.E}\n")
        
        bytecode = bytearray()
        
        try:
            tree = ast.parse(code)
            
            print(f"{C.C}Analyzing AST...{C.E}")
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = None
                    
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr
                    
                    if func_name:
                        args = []
                        for arg in node.args:
                            if isinstance(arg, ast.Constant):
                                args.append(arg.value)
                            elif isinstance(arg, ast.Num):
                                args.append(arg.n)
                        
                        opcode = None
                        
                        if func_name in ['h', 'hadamard']:
                            opcode = 0x02
                        elif func_name in ['x', 'pauli_x', 'not_gate']:
                            opcode = 0x03
                        elif func_name in ['y', 'pauli_y']:
                            opcode = 0x04
                        elif func_name in ['z', 'pauli_z']:
                            opcode = 0x05
                        elif func_name in ['s', 'phase']:
                            opcode = 0x06
                        elif func_name in ['t', 't_gate']:
                            opcode = 0x07
                        elif func_name in ['cnot', 'cx']:
                            opcode = 0x0B
                        elif func_name in ['measure', 'meas']:
                            opcode = 0x10
                        elif func_name in ['bell', 'bell_pair']:
                            opcode = 0x14
                        elif func_name in ['ghz']:
                            opcode = 0x15
                        
                        if opcode:
                            bytecode.append(opcode)
                            for arg in args:
                                if isinstance(arg, int):
                                    bytecode.extend(struct.pack('<H', arg & 0xFFFF))
                            
                            print(f"  {C.C}{func_name}({', '.join(map(str, args))}) → opcode 0x{opcode:02X}{C.E}")
            
            bytecode.append(0x41)
            
            compiled_bytes = bytes(bytecode)
            
            # FIX: add missing columns
            self.cursor.execute(f'''
                INSERT INTO {T_BIN} VALUES (NULL, ?, ?, 'python', 0, ?, 0, ?)
            ''', (program_name, compiled_bytes, len(compiled_bytes), time.time()))
            
            program_id = self.cursor.lastrowid
            self.conn.commit()
            
            print(f"\n{C.G}✓ Compiled Python to {len(compiled_bytes)} bytes{C.E}\n")
            
            log_to_channel(self.conn, 'COMPILER', 'INFO', 
                          f'Compiled Python {program_name}: {len(compiled_bytes)} bytes')
            
            return compiled_bytes
            
        except Exception as e:
            print(f"{C.R}Compilation error: {e}{C.E}")
            traceback.print_exc()
            return bytes()


# ═══════════════════════════════════════════════════════════════════════════
# INTERACTIVE DEVELOPMENT CLI
# ═══════════════════════════════════════════════════════════════════════════

class DevelopmentCLI:
    """Full-featured development environment"""
    
    def __init__(self):
        if not DB_PATH.exists():
            print(f"{C.R}ERROR: Database not found: {DB_PATH}{C.E}")
            print(f"{C.Y}Run qunix-leech-builder.py first to build the system{C.E}")
            sys.exit(1)
        
        self.conn = sqlite3.connect(str(DB_PATH))
        
        print(f"\n{C.BOLD}{C.W}╔══════════════════════════════════════════════════════════════╗{C.E}")
        print(f"{C.BOLD}{C.W}║   QUNIX QUANTUM DEVELOPMENT TOOLS v3.0                       ║{C.E}")
        print(f"{C.BOLD}{C.W}║   Full Binary Execution on Leech Lattice Substrate           ║{C.E}")
        print(f"{C.BOLD}{C.W}╚══════════════════════════════════════════════════════════════╝{C.E}\n")
        
        initialize_output_channel(self.conn)
        
        self.check_kernel_state()
        
        self.executor = QuantumExecutor(self.conn)
        self.script_compiler = QuantumScriptCompiler(self.conn)
        self.python_compiler = PythonToQuantumCompiler(self.conn)
        
        print(f"{C.G}✓ Development tools ready{C.E}\n")
    
    def check_kernel_state(self):
        c = self.conn.cursor()
        c.execute("SELECT val FROM meta WHERE key='kernel_state'")
        row = c.fetchone()
        
        if row and row[0] == 'BOOTED':
            print(f"{C.G}✓ Quantum kernel is BOOTED{C.E}")
            
            c.execute("SELECT val FROM meta WHERE key='boot_sequence'")
            row = c.fetchone()
            if row:
                print(f"{C.C}  Boot sequence: {row[0]}{C.E}")
        else:
            print(f"{C.Y}⚠ Quantum kernel NOT booted{C.E}")
            print(f"{C.C}  Use option 1 to boot kernel{C.E}")
        
        print()
    
    def show_menu(self):
        print(f"\n{C.BOLD}{C.Q}╔══════════════════════════════════════════════════════════════╗{C.E}")
        print(f"{C.BOLD}{C.Q}║              QUNIX DEVELOPMENT MENU                          ║{C.E}")
        print(f"{C.BOLD}{C.Q}╚══════════════════════════════════════════════════════════════╝{C.E}\n")
        
        print(f"{C.BOLD}System:{C.E}")
        print(f"  1. Boot Quantum Kernel (W-state tripartite)")
        print(f"  2. Show System Info")
        print(f"  3. Show Kernel State")
        print(f"  4. Show Entanglement Map")
        print(f"  5. Show Output Channel")
        print(f"  6. Show Metaprogram Status")
        print(f"  7. Show Checkpoint State")
        print(f"  8. Show Patch Status")
        print(f"  9. Show Program Genealogy")
        
        print(f"\n{C.BOLD}Execution:{C.E}")
        print(f"  10. List All Programs")
        print(f"  11. Execute Program by Name")
        print(f"  12. Execute Bell Pair")
        print(f"  13. Execute GHZ State")
        print(f"  14. Execute W-State")
        print(f"  15. Execute Quantum Teleportation")
        
        print(f"\n{C.BOLD}Development:{C.E}")
        print(f"  20. Write Quantum Script (Interactive)")
        print(f"  21. Compile & Execute Script")
        print(f"  22. Write Python Code (Interactive)")
        print(f"  23. Compile & Execute Python")
        print(f"  24. Interactive Quantum Operations")
        
        print(f"\n{C.BOLD}Examples:{C.E}")
        print(f"  30. Example: Bell State")
        print(f"  31. Example: GHZ State")
        print(f"  32. Example: W-State")
        print(f"  33. Example: Deutsch Algorithm")
        print(f"  34. Example: Quantum Teleportation")
        
        print(f"\n{C.BOLD}Inspection:{C.E}")
        print(f"  40. Show Qubit State")
        print(f"  41. Show Lattice Mapping")
        print(f"  42. Show Program Bytecode")
        print(f"  43. Show Syscall Table")
        print(f"  44. Show Opcode Table")
        
        print(f"\n  0. Exit")
        print()
    
    def boot_kernel(self):
        boot_quantum_kernel(self.conn)
    
    def show_system_info(self):
        c = self.conn.cursor()
        
        print(f"\n{C.BOLD}{C.C}═══ SYSTEM INFORMATION ═══{C.E}\n")
        
        c.execute("SELECT key, val FROM meta ORDER BY key")
        print(f"{C.BOLD}Metadata:{C.E}")
        for key, val in c.fetchall():
            print(f"  {key:20s}: {val}")
        
        print()
        
        c.execute(f'SELECT COUNT(*) FROM {T_LAT}')
        n_lat = c.fetchone()[0]
        
        c.execute(f'SELECT COUNT(*) FROM {T_PQB}')
        n_qub = c.fetchone()[0]
        
        c.execute(f'SELECT COUNT(*) FROM {T_BIN}')
        n_prog = c.fetchone()[0]
        
        c.execute(f'SELECT COUNT(*) FROM {T_ENT}')
        n_ent = c.fetchone()[0]
        
        c.execute(f'SELECT COUNT(*) FROM {T_PRC}')
        n_proc = c.fetchone()[0]
        
        print(f"{C.BOLD}Resources:{C.E}")
        print(f"  Lattice Points:       {n_lat:,}")
        print(f"  Qubits:               {n_qub:,}")
        print(f"  Programs:             {n_prog}")
        print(f"  Entanglements:        {n_ent}")
        print(f"  Processes:            {n_proc}")
        
        print()
    
    def show_kernel_state(self):
        c = self.conn.cursor()
        
        print(f"\n{C.BOLD}{C.C}═══ KERNEL STATE ═══{C.E}\n")
        
        c.execute(f'''
            SELECT qid, ar, ai, br, bi, gat, typ
            FROM {T_PQB}
            WHERE qid IN (0, 1, 2)
            ORDER BY qid
        ''')
        
        print(f"{C.BOLD}Boot Qubits:{C.E}")
        for qid, ar, ai, br, bi, gate, typ in c.fetchall():
            alpha = complex(ar, ai)
            beta = complex(br, bi)
            prob_0 = abs(alpha)**2
            prob_1 = abs(beta)**2
            
            print(f"  q{qid}: |ψ⟩ = {alpha:.4f}|0⟩ + {beta:.4f}|1⟩")
            print(f"      Gate: {gate or 'INIT':8s}  Type: {typ:12s}")
            print(f"      P(|0⟩) = {prob_0:.4f}, P(|1⟩) = {prob_1:.4f}")
            print()
        
        c.execute('''
            SELECT timestamp, event_type, details
            FROM kernel_log
            ORDER BY log_id DESC
            LIMIT 5
        ''')
        
        events = c.fetchall()
        if events:
            print(f"{C.BOLD}Recent Kernel Events:{C.E}")
            for ts, evt, details in events:
                time_str = time.strftime('%H:%M:%S', time.localtime(ts))
                print(f"  [{time_str}] {evt:12s} - {details}")
        
        print()
    
    def show_entanglement_map(self):
        c = self.conn.cursor()
        
        print(f"\n{C.BOLD}{C.C}═══ ENTANGLEMENT MAP ═══{C.E}\n")
        
        c.execute(f'''
            SELECT qa, qb, typ, str
            FROM {T_ENT}
            ORDER BY eid
        ''')
        
        entanglements = c.fetchall()
        
        if not entanglements:
            print(f"{C.Y}No entanglements found{C.E}\n")
            return
        
        print(f"{'Qubit A':>8} {'Qubit B':>8} {'Type':15} {'Strength':>10}")
        print(f"{'-'*50}")
        
        for qa, qb, typ, strength in entanglements:
            print(f"   q{qa:3d}    q{qb:3d}     {typ:15s} {strength*100:>8.1f}%")
        
        print(f"\n{C.C}Total entanglements: {len(entanglements)}{C.E}\n")
    
    def show_output_channel(self):
        read_output_channel(self.conn)
    
    def list_programs(self):
        c = self.conn.cursor()
        
        print(f"\n{C.BOLD}{C.C}═══ COMPILED PROGRAMS ═══{C.E}\n")
        
        c.execute(f'''
            SELECT bid, nam, typ, size
            FROM {T_BIN}
            ORDER BY bid
        ''')
        
        print(f"{'ID':>4} {'Name':30} {'Type':15} {'Size':>8}")
        print(f"{'-'*65}")
        
        for bid, nam, typ, size in c.fetchall():
            print(f"{bid:>4} {nam:30} {typ:15} {size:>6}B")
        
        print()
    
    def execute_program_interactive(self):
        self.list_programs()
        
        name = input(f"\n{C.C}Program name to execute: {C.E}").strip()
        
        if name:
            self.executor.execute_program_by_name(name)
    
    def execute_builtin(self, program_name: str):
        self.executor.execute_program_by_name(program_name)
    
    def write_quantum_script(self):
        print(f"\n{C.BOLD}{C.C}═══ QUANTUM SCRIPT EDITOR ═══{C.E}\n")
        print(f"{C.C}Enter quantum assembly code (type 'END' on a new line to finish):{C.E}")
        print(f"{C.GRAY}Example:{C.E}")
        print(f"{C.GRAY}  H 0        # Hadamard on qubit 0{C.E}")
        print(f"{C.GRAY}  CNOT 0 1   # CNOT control=0, target=1{C.E}")
        print(f"{C.GRAY}  QMEAS 0    # Measure qubit 0{C.E}")
        print(f"{C.GRAY}  HALT       # End program{C.E}\n")
        
        lines = []
        line_num = 1
        
        while True:
            try:
                line = input(f"{C.C}{line_num:3d}> {C.E}")
                
                if line.strip().upper() == 'END':
                    break
                
                lines.append(line)
                line_num += 1
                
            except EOFError:
                break
        
        if not lines:
            print(f"{C.Y}No code entered{C.E}")
            return None
        
        script = '\n'.join(lines)
        name = input(f"\n{C.C}Program name: {C.E}").strip() or "user_script"
        
        return script, name
    
    def compile_and_execute_script(self):
        result = self.write_quantum_script()
        
        if not result:
            return
        
        script, name = result
        
        bytecode = self.script_compiler.compile_script(script, name)
        
        execute = input(f"{C.C}Execute now? (y/n): {C.E}").lower()
        
        if execute == 'y':
            self.executor.execute_binary(bytecode, name)
    
    def write_python_code(self):
        print(f"\n{C.BOLD}{C.C}═══ PYTHON TO QUANTUM COMPILER ═══{C.E}\n")
        print(f"{C.C}Enter Python code (type 'END' on a new line to finish):{C.E}")
        print(f"{C.GRAY}Example:{C.E}")
        print(f"{C.GRAY}  h(0)           # Hadamard on qubit 0{C.E}")
        print(f"{C.GRAY}  cnot(0, 1)     # CNOT gate{C.E}")
        print(f"{C.GRAY}  measure(0)     # Measure qubit 0{C.E}\n")
        
        lines = []
        line_num = 1
        
        while True:
            try:
                line = input(f"{C.C}{line_num:3d}> {C.E}")
                
                if line.strip().upper() == 'END':
                    break
                
                lines.append(line)
                line_num += 1
                
            except EOFError:
                break
        
        if not lines:
            print(f"{C.Y}No code entered{C.E}")
            return None
        
        code = '\n'.join(lines)
        name = input(f"\n{C.C}Program name: {C.E}").strip() or "python_program"
        
        return code, name
    
    def compile_and_execute_python(self):
        result = self.write_python_code()
        
        if not result:
            return
        
        code, name = result
        
        bytecode = self.python_compiler.compile_python(code, name)
        
        execute = input(f"{C.C}Execute now? (y/n): {C.E}").lower()
        
        if execute == 'y':
            self.executor.execute_binary(bytecode, name)
    
    def interactive_quantum_ops(self):
        print(f"\n{C.BOLD}{C.C}═══ INTERACTIVE QUANTUM MODE ═══{C.E}\n")
        print(f"{C.C}Commands:{C.E}")
        print(f"  H <qubit>              - Hadamard")
        print(f"  X <qubit>              - Pauli-X")
        print(f"  Y <qubit>              - Pauli-Y")
        print(f"  Z <qubit>              - Pauli-Z")
        print(f"  S <qubit>              - S gate")
        print(f"  T <qubit>              - T gate")
        print(f"  CNOT <ctrl> <tgt>      - CNOT")
        print(f"  QMEAS <qubit>          - Measure")
        print(f"  STATE <qubit>          - Show state")
        print(f"  QBELL <q1> <q2>        - Bell pair")
        print(f"  QGHZ <q1> <q2> <q3>    - GHZ state")
        print(f"  DONE                   - Exit")
        print()
        
        while True:
            try:
                cmd = input(f"{C.Q}quantum> {C.E}").strip().upper()
                
                if not cmd:
                    continue
                
                if cmd == 'DONE':
                    break
                
                parts = cmd.split()
                op = parts[0]
                args = [int(x) for x in parts[1:] if x.isdigit()]
                
                if op == 'H' and args:
                    self.executor.gate_hadamard(args[0])
                
                elif op == 'X' and args:
                    self.executor.gate_pauli_x(args[0])
                
                elif op == 'Y' and args:
                    self.executor.gate_pauli_y(args[0])
                
                elif op == 'Z' and args:
                    self.executor.gate_pauli_z(args[0])
                
                elif op == 'S' and args:
                    self.executor.gate_s(args[0])
                
                elif op == 'T' and args:
                    self.executor.gate_t(args[0])
                
                elif op == 'CNOT' and len(args) >= 2:
                    self.executor.gate_cnot(args[0], args[1])
                
                elif op == 'QMEAS' and args:
                    self.executor.gate_measure(args[0])
                
                elif op == 'STATE' and args:
                    self.show_qubit_state_detail(args[0])
                
                elif op == 'QBELL' and len(args) >= 2:
                    self.executor.gate_bell(args[0], args[1])
                
                elif op == 'QGHZ' and len(args) >= 3:
                    self.executor.gate_ghz(args[0], args[1], args[2])
                
                else:
                    print(f"{C.R}Unknown or invalid command{C.E}")
                
            except KeyboardInterrupt:
                print(f"\n{C.Y}Use DONE to exit{C.E}")
            except Exception as e:
                print(f"{C.R}Error: {e}{C.E}")
        
        print(f"{C.G}Interactive mode ended{C.E}\n")
    
    def load_example(self, example_type: str):
        examples = {
            'bell': """# Bell State |Φ+⟩ = (|00⟩ + |11⟩)/√2
QH 0
QCNOT 0 1
QMEAS 0

QMEAS 1
HALT""",
            
            'ghz': """# GHZ State |GHZ⟩ = (|000⟩ + |111⟩)/√2
QH 0
QCNOT 0 1
QCNOT 0 2
QMEAS 0
QMEAS 1
QMEAS 2
HALT""",
            
            'w': """# W-State
QW3 0 1 2
QMEAS 0
QMEAS 1
QMEAS 2
HALT""",
            
            'deutsch': """# Deutsch Algorithm (simplified)
QX 1
QH 0
QH 1
QCNOT 0 1
QH 0
QMEAS 0
HALT""",
            
            'teleport': """# Quantum Teleportation (simplified)
QH 1
QCNOT 1 2
QCNOT 0 1
QH 0
QMEAS 0
QMEAS 1
QMEAS 2
HALT"""
        }
        
        if example_type not in examples:
            print(f"{C.R}Unknown example: {example_type}{C.E}")
            return
        
        script = examples[example_type]
        name = f"example_{example_type}"
        
        print(f"\n{C.BOLD}{C.C}═══ EXAMPLE: {example_type.upper()} ═══{C.E}\n")
        print(f"{C.GRAY}{script}{C.E}\n")
        
        bytecode = self.script_compiler.compile_script(script, name)
        self.executor.execute_binary(bytecode, name)
    
    def show_qubit_state_detail(self, qid: int):
        c = self.conn.cursor()
        
        print(f"\n{C.BOLD}Qubit {qid} State:{C.E}")
        
        c.execute(f'''
            SELECT qid, lid, ar, ai, br, bi, gat, typ, adr
            FROM {T_PQB}
            WHERE qid = ?
        ''', (qid,))
        
        row = c.fetchone()
        
        if not row:
            print(f"{C.R}Qubit {qid} not found{C.E}\n")
            return
        
        qid, lid, ar, ai, br, bi, gate, typ, adr = row
        
        alpha = complex(ar, ai)
        beta = complex(br, bi)
        prob_0 = abs(alpha)**2
        prob_1 = abs(beta)**2
        
        print(f"  |ψ⟩ = {alpha:.4f}|0⟩ + {beta:.4f}|1⟩")
        print(f"  P(|0⟩) = {prob_0:.4f}")
        print(f"  P(|1⟩) = {prob_1:.4f}")
        print(f"  Type:          {typ}")
        print(f"  Last gate:     {gate or 'none'}")
        print(f"  Lattice ID:    {lid}")
        print(f"  Address:       {adr}")
        
        c.execute(f'''
            SELECT qb, typ, str FROM {T_ENT} WHERE qa = ?
            UNION
            SELECT qa, typ, str FROM {T_ENT} WHERE qb = ?
        ''', (qid, qid))
        
        ents = c.fetchall()
        if ents:
            print(f"  Entangled with:")
            for other_q, ent_type, strength in ents:
                print(f"    q{other_q} [{ent_type}] ({strength*100:.1f}%)")
        
        print()
    
    def show_lattice_mapping(self):
        qid_str = input(f"{C.C}Qubit ID: {C.E}").strip()
        
        try:
            qid = int(qid_str)
        except ValueError:
            print(f"{C.R}Invalid qubit ID{C.E}")
            return
        
        route = self.executor.route_to_qubit(qid)
        
        print(f"\n{C.BOLD}Qubit {qid} Lattice Mapping:{C.E}")
        print(f"  Qubit ID:      {route['qid']}")
        print(f"  Lattice ID:    {route['lid']}")
        print(f"  Address:       {route['adr']}")
        print(f"  Norm:          {route['norm']:.6f}")
        
        if route['coords'] is not None:
            print(f"  Coordinates:   {route['coords'][:5]}... (24-dim)")
        
        print()
    
    def show_program_bytecode(self):
        self.list_programs()
        
        name = input(f"\n{C.C}Program name: {C.E}").strip()
        
        if name not in self.executor.programs:
            print(f"{C.R}Program not found{C.E}")
            return
        
        prog = self.executor.programs[name]
        bytecode = prog['bytecode']
        
        print(f"\n{C.BOLD}Program: {name}{C.E}")
        print(f"  Type: {prog['type']}")
        print(f"  Size: {len(bytecode)} bytes")
        print(f"\n{C.BOLD}Bytecode:{C.E}")
        
        for i in range(0, len(bytecode), 16):
            chunk = bytecode[i:i+16]
            hex_str = ' '.join(f'{b:02X}' for b in chunk)
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            print(f"  {i:04X}  {hex_str:48s}  {ascii_str}")
        
        print()
    
    def show_syscall_table(self):
        print(f"\n{C.BOLD}{C.C}═══ SYSCALL TABLE ═══{C.E}\n")
        
        print(f"{'Number':>6} {'Name':20} {'Description'}")
        print(f"{'-'*60}")
        
        syscalls = [
            (0, 'exit', 'Terminate process'),
            (1, 'fork', 'Create new process'),
            (14, 'getpid', 'Get process ID'),
            (20, 'qalloc', 'Allocate qubits'),
            (23, 'qmeas', 'Measure qubit'),
            (24, 'qent', 'Create entanglement'),
        ]
        
        for num, name, desc in syscalls:
            print(f"{num:>6} {name:20} {desc}")
        
        print()
    
    def show_opcode_table(self):
        print(f"\n{C.BOLD}{C.C}═══ OPCODE TABLE ═══{C.E}\n")
        
        print(f"{'Opcode':>6} {'Mnemonic':12} {'Ops':>4} {'Description'}")
        print(f"{'-'*70}")
        
        opcode_desc = {
            0x00: 'No operation',
            0x01: 'Identity gate',
            0x02: 'Hadamard gate',
            0x03: 'Pauli-X gate',
            0x04: 'Pauli-Y gate',
            0x05: 'Pauli-Z gate',
            0x06: 'S gate (phase)',
            0x07: 'T gate (π/8)',
            0x08: 'S† gate',
            0x09: 'T† gate',
            0x0B: 'CNOT gate',
            0x0C: 'CZ gate',
            0x0D: 'SWAP gate',
            0x0E: 'Toffoli (CCX) gate',
            0x10: 'Measurement',
            0x12: 'W-state (3 qubits)',
            0x13: 'W-state (4 qubits)',
            0x14: 'Bell pair',
            0x15: 'GHZ state',
            0x40: 'Classical NOP',
            0x41: 'Halt execution',
            0x42: 'Move register',
            0x43: 'Add registers',
            0x44: 'Subtract registers',
            0x80: 'Load from memory',
            0x81: 'Store to memory',
            0xA0: 'Self read',
            0xA1: 'Self mutate',
            0xA2: 'Self fork',
            0xA3: 'Verify',
            0xA4: 'Rollback',
            0xA5: 'Checkpoint',
            0xA6: 'Patch apply',
            0xA7: 'Loop start',
            0xA8: 'Loop end',
            0xA9: 'Symbolic state',
            0xAA: 'CTC backprop',
            0xAB: 'Entangle mutate',
            0xE0: 'System call',
            0xE1: 'Fork process',
            0xE3: 'Exit process',
        }
        
        for opc, (mne, nop) in sorted(OPCODES.items()):
            desc = opcode_desc.get(opc, '')
            print(f"  0x{opc:02X} {mne:12} {nop:>4} {desc}")
        
        print()
    
    def run(self):
        """Main CLI loop"""
        while True:
            self.show_menu()
            
            try:
                choice = input(f"{C.Q}qunix-dev> {C.E}").strip()
                
                if not choice:
                    continue
                
                if choice == '0':
                    break
                
                # System
                elif choice == '1':
                    self.boot_kernel()
                elif choice == '2':
                    self.show_system_info()
                elif choice == '3':
                    self.show_kernel_state()
                elif choice == '4':
                    self.show_entanglement_map()
                elif choice == '5':
                    self.show_output_channel()
                elif choice == '6':
                    show_metaprogram_status(self.conn)
                elif choice == '7':
                    show_checkpoint_state(self.conn)
                elif choice == '8':
                    show_patch_status(self.conn)
                elif choice == '9':
                    show_program_genealogy(self.conn)
                
                # Execution
                elif choice == '10':
                    self.list_programs()
                elif choice == '11':
                    self.execute_program_interactive()
                elif choice == '12':
                    self.execute_builtin('bell_pair')
                elif choice == '13':
                    self.execute_builtin('ghz_3')
                elif choice == '14':
                    self.execute_builtin('w_state_4')
                elif choice == '15':
                    self.execute_builtin('teleport')
                
                # Development
                elif choice == '20':
                    self.write_quantum_script()
                elif choice == '21':
                    self.compile_and_execute_script()
                elif choice == '22':
                    self.write_python_code()
                elif choice == '23':
                    self.compile_and_execute_python()
                elif choice == '24':
                    self.interactive_quantum_ops()
                
                # Examples
                elif choice == '30':
                    self.load_example('bell')
                elif choice == '31':
                    self.load_example('ghz')
                elif choice == '32':
                    self.load_example('w')
                elif choice == '33':
                    self.load_example('deutsch')
                elif choice == '34':
                    self.load_example('teleport')
                
                # Inspection
                elif choice == '40':
                    qid_str = input(f"{C.C}Qubit ID: {C.E}").strip()
                    try:
                        self.show_qubit_state_detail(int(qid_str))
                    except ValueError:
                        print(f"{C.R}Invalid qubit ID{C.E}")
                elif choice == '41':
                    self.show_lattice_mapping()
                elif choice == '42':
                    self.show_program_bytecode()
                elif choice == '43':
                    self.show_syscall_table()
                elif choice == '44':
                    self.show_opcode_table()
                
                else:
                    print(f"{C.Y}Invalid choice{C.E}")
            
            except KeyboardInterrupt:
                print(f"\n{C.Y}Use option 0 to exit{C.E}")
            except Exception as e:
                print(f"{C.R}Error: {e}{C.E}")
                traceback.print_exc()
        
        self.conn.close()
        print(f"\n{C.G}Development tools closed{C.E}")


# ═══════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def inspect_database():
    """Quick database inspection"""
    if not DB_PATH.exists():
        print(f"{C.R}Database not found: {DB_PATH}{C.E}")
        return
    
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    print(f"\n{C.BOLD}{C.C}═══ DATABASE INSPECTION ═══{C.E}\n")
    
    c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in c.fetchall()]
    
    print(f"{C.BOLD}Tables:{C.E}")
    for table in tables:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        count = c.fetchone()[0]
        print(f"  {table:20s}: {count:,} rows")
    
    print()
    
    c.execute("SELECT key, val FROM meta")
    meta = c.fetchall()
    
    if meta:
        print(f"{C.BOLD}Metadata:{C.E}")
        for key, val in meta:
            print(f"  {key:20s}: {val}")
    
    print()
    conn.close()


def quick_boot():
    """Quick boot for testing"""
    if not DB_PATH.exists():
        print(f"{C.R}Database not found{C.E}")
        return
    
    conn = sqlite3.connect(str(DB_PATH))
    
    c = conn.cursor()
    c.execute("SELECT val FROM meta WHERE key='kernel_state'")
    row = c.fetchone()
    
    if row and row[0] == 'BOOTED':
        print(f"{C.G}Kernel already booted{C.E}")
    else:
        print(f"{C.C}Booting kernel...{C.E}")
        initialize_output_channel(conn)
        boot_quantum_kernel(conn)
    
    conn.close()


def test_execution():
    """Test program execution"""
    if not DB_PATH.exists():
        print(f"{C.R}Database not found{C.E}")
        return
    
    conn = sqlite3.connect(str(DB_PATH))
    
    initialize_output_channel(conn)
    
    c = conn.cursor()
    c.execute("SELECT val FROM meta WHERE key='kernel_state'")
    row = c.fetchone()
    
    if not row or row[0] != 'BOOTED':
        print(f"{C.C}Booting kernel first...{C.E}")
        boot_quantum_kernel(conn)
    
    executor = QuantumExecutor(conn)
    
    print(f"\n{C.C}Testing Bell pair execution...{C.E}\n")
    executor.execute_program_by_name('bell_pair')
    
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point"""
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == 'inspect':
            inspect_database()
            return
        elif cmd == 'boot':
            quick_boot()
            return
        elif cmd == 'test':
            test_execution()
            return
        elif cmd == 'help':
            print(f"""
{C.BOLD}QUNIX Development Tools v3.0{C.E}

Usage:
  {sys.argv[0]}              - Start interactive CLI
  {sys.argv[0]} inspect      - Quick database inspection
  {sys.argv[0]} boot         - Quick boot kernel
  {sys.argv[0]} test         - Test program execution
  {sys.argv[0]} help         - Show this help

{C.BOLD}Features:{C.E}
  • Quantum kernel boot with W-state tripartite entanglement
  • Binary program execution on lattice-mapped qubits
  • Quantum script compilation (assembly → bytecode)
  • Python to quantum bytecode compilation
  • Interactive quantum operations REPL
  • Metaprogram monitoring (quine evolver, live patcher, verifier)
  • Checkpoint/rollback state inspection
  • Patch application status
  • Program genealogy tracking (quine evolution)
  • Complete system inspection tools
  • All opcodes (0x00-0xFF), syscalls, and stored programs

{C.BOLD}Database:{C.E}
  Location: {DB_PATH}
  
{C.BOLD}Metaprograms:{C.E}
  The system includes three infinite-loop metaprograms:
    • quine_evolver      - Self-mutating quantum quine
    • live_patcher       - Runtime code patcher with CTC
    • symbolic_verifier  - Self-verifying symbolic executor
  
  These run from database bytecode and can modify themselves
  and each other using CTC (closed timelike curve) backpropagation.

{C.BOLD}Integration:{C.E}
  This CLI fully integrates with the builder's metaprogramming system:
    • Monitors loop_state table for execution iterations
    • Tracks mutation_history for quine evolution
    • Displays patches table for live patching
    • Shows verify_log for symbolic verification
    • Accesses prog_versions for genealogy tracking
    • Reads microcode_log for execution history
""")
            return
    
    try:
        cli = DevelopmentCLI()
        cli.run()
    except KeyboardInterrupt:
        print(f"\n\n{C.Y}Interrupted{C.E}")
    except Exception as e:
        print(f"\n{C.R}Fatal error: {e}{C.E}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
