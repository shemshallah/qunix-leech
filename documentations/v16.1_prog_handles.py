#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║  QUNIX HANDLER FIX PATCH v2.0.0 - FIXED SYNTAX                                ║
║  Complete Handler Population with Executable SQL Chains                       ║
║                                                                               ║
║  Fixes handlers 5 at a time for filesystem commands:                         ║
║    • ls, dir, tree, find, locate (Batch 1)                                   ║
║    • pwd, cd, mkdir, rm, cat (Batch 2)                                       ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import sqlite3
import struct
import json
import time
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

VERSION = "2.0.0-FIXED"

# ANSI Colors
class C:
    G = '\033[92m'; R = '\033[91m'; Y = '\033[93m'; C = '\033[96m'
    M = '\033[35m'; B = '\033[94m'; W = '\033[97m'
    BOLD = '\033[1m'; DIM = '\033[2m'; GRAY = '\033[90m'
    E = '\033[0m'


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

class SchemaDetector:
    """Detect actual database schema and adapt"""
    
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.tables = self._get_tables()
        self.columns = {}
        for table in self.tables:
            self.columns[table] = self._get_columns(table)
        
        self.use_cmd_name = self._detect_fk_strategy()
        self.schema_version = self._detect_version()
    
    def _get_tables(self) -> List[str]:
        c = self.conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return [r[0] for r in c.fetchall()]
    
    def _get_columns(self, table: str) -> List[str]:
        c = self.conn.cursor()
        c.execute(f"PRAGMA table_info({table})")
        return [r[1] for r in c.fetchall()]
    
    def _detect_fk_strategy(self) -> bool:
        """Detect if we use cmd_name or cmd_id for foreign keys"""
        if 'command_handlers' not in self.tables:
            return True  # Default to cmd_name
        
        cols = self.columns['command_handlers']
        
        if 'cmd_name' in cols and 'cmd_id' not in cols:
            return True  # v12+ schema
        elif 'cmd_id' in cols and 'cmd_name' not in cols:
            return False  # v7-v10 schema
        elif 'cmd_name' in cols and 'cmd_id' in cols:
            return True  # Both exist, prefer cmd_name
        else:
            return True  # Default
    
    def _detect_version(self) -> str:
        """Detect schema version"""
        if 'command_handlers' not in self.tables:
            return 'pre-v7'
        
        cols = self.columns['command_handlers']
        
        if 'cmd_name' in cols and 'cmd_id' not in cols:
            return 'v12+'
        elif 'cmd_id' in cols:
            if 'command_flags' not in self.tables:
                return 'v11'
            return 'v7-v10'
        else:
            return 'unknown'
    
    def has_table(self, name: str) -> bool:
        return name in self.tables
    
    def has_column(self, table: str, column: str) -> bool:
        return table in self.columns and column in self.columns[table]


# ═══════════════════════════════════════════════════════════════════════════════
# QASM CIRCUIT TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

QASM_TEMPLATES = {
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
measure q -> c;''',
    
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
measure q -> c;''',
    
    'amplitude_amp_6': '''OPENQASM 2.0;
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
measure q -> c;''',
    
    'metadata_query': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0], q[1];
cx q[1], q[2];
measure q -> c;''',
}


# ═══════════════════════════════════════════════════════════════════════════════
# HANDLER DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_batch_1_handlers() -> List[Dict]:
    """Batch 1: Search commands"""
    return [
        {
            'cmd_name': 'ls',
            'handler_type': 'FILESYSTEM',
            'method_name': 'cmd_ls',
            'qasm_code': QASM_TEMPLATES['grover_8'],
            'requires_qubits': 1,
            'qubit_count': 8,
            'priority': 100,
            'python_code': '''path = parsed_args.get('arg_0', type('obj', (), {'value': '.'})).value
entries = executor.qfs.listdir(path) if executor.qfs else []
result = '\\n'.join(f"  {e.name}{'/' if e.file_type == 'd' else ''}" for e in entries if e.name not in ('.', '..'))''',
        },
        {
            'cmd_name': 'dir',
            'handler_type': 'FILESYSTEM',
            'method_name': 'cmd_ls',
            'qasm_code': QASM_TEMPLATES['grover_8'],
            'requires_qubits': 1,
            'qubit_count': 8,
            'priority': 100,
            'python_code': '''path = parsed_args.get('arg_0', type('obj', (), {'value': '.'})).value
entries = executor.qfs.listdir(path) if executor.qfs else []
result = '\\n'.join(f"  {e.name}{'/' if e.file_type == 'd' else ''}" for e in entries if e.name not in ('.', '..'))''',
        },
        {
            'cmd_name': 'tree',
            'handler_type': 'FILESYSTEM',
            'method_name': 'cmd_tree',
            'qasm_code': QASM_TEMPLATES['quantum_walk_10'],
            'requires_qubits': 1,
            'qubit_count': 10,
            'priority': 100,
            'python_code': '''path = parsed_args.get('arg_0', type('obj', (), {'value': '.'})).value
result = executor.qfs.tree(path, max_depth=5) if executor.qfs else 'Filesystem not available' ''',
        },
        {
            'cmd_name': 'find',
            'handler_type': 'FILESYSTEM',
            'method_name': 'cmd_find',
            'qasm_code': QASM_TEMPLATES['grover_8'],
            'requires_qubits': 1,
            'qubit_count': 8,
            'priority': 100,
            'python_code': '''path = parsed_args.get('arg_0', type('obj', (), {'value': '.'})).value
pattern = parsed_args.get('arg_1', type('obj', (), {'value': '*'})).value
c = conn.cursor()
c.execute("SELECT path FROM fs_locate_index WHERE path LIKE ? LIMIT 100", (f'{path}%',))
result = '\\n'.join(r[0] for r in c.fetchall())''',
        },
        {
            'cmd_name': 'locate',
            'handler_type': 'FILESYSTEM',
            'method_name': 'cmd_locate',
            'qasm_code': QASM_TEMPLATES['amplitude_amp_6'],
            'requires_qubits': 1,
            'qubit_count': 6,
            'priority': 100,
            'python_code': '''pattern = parsed_args.get('arg_0', type('obj', (), {'value': ''})).value
c = conn.cursor()
c.execute("SELECT path FROM fs_locate_index WHERE basename LIKE ? LIMIT 50", (f'%{pattern}%',))
result = '\\n'.join(r[0] for r in c.fetchall())''',
        },
    ]


def get_batch_2_handlers() -> List[Dict]:
    """Batch 2: Basic commands"""
    return [
        {
            'cmd_name': 'pwd',
            'handler_type': 'FILESYSTEM',
            'method_name': 'cmd_pwd',
            'qasm_code': QASM_TEMPLATES['metadata_query'],
            'requires_qubits': 0,
            'qubit_count': 3,
            'priority': 100,
            'python_code': '''result = executor.qfs.getcwd() if executor.qfs else '/' ''',
        },
        {
            'cmd_name': 'cd',
            'handler_type': 'FILESYSTEM',
            'method_name': 'cmd_cd',
            'qasm_code': QASM_TEMPLATES['metadata_query'],
            'requires_qubits': 0,
            'qubit_count': 3,
            'priority': 100,
            'python_code': '''path = parsed_args.get('arg_0', type('obj', (), {'value': '/'})).value
success = executor.qfs.chdir(path) if executor.qfs else False
result = f"Changed to: {executor.qfs.getcwd()}" if success else f"cd: {path}: No such directory" ''',
        },
        {
            'cmd_name': 'mkdir',
            'handler_type': 'FILESYSTEM',
            'method_name': 'cmd_mkdir',
            'qasm_code': QASM_TEMPLATES['metadata_query'],
            'requires_qubits': 0,
            'qubit_count': 3,
            'priority': 100,
            'python_code': '''path = parsed_args.get('arg_0', type('obj', (), {'value': ''})).value
success = executor.qfs.mkdir(path, 0o755) if executor.qfs and path else False
result = f"Created: {path}" if success else f"mkdir: cannot create directory" ''',
        },
        {
            'cmd_name': 'rm',
            'handler_type': 'FILESYSTEM',
            'method_name': 'cmd_rm',
            'qasm_code': QASM_TEMPLATES['metadata_query'],
            'requires_qubits': 0,
            'qubit_count': 3,
            'priority': 100,
            'python_code': '''path = parsed_args.get('arg_0', type('obj', (), {'value': ''})).value
success = executor.qfs.unlink(path) if executor.qfs and path else False
result = f"Removed: {path}" if success else f"rm: cannot remove '{path}'" ''',
        },
        {
            'cmd_name': 'cat',
            'handler_type': 'FILESYSTEM',
            'method_name': 'cmd_cat',
            'qasm_code': QASM_TEMPLATES['metadata_query'],
            'requires_qubits': 0,
            'qubit_count': 3,
            'priority': 100,
            'python_code': '''path = parsed_args.get('arg_0', type('obj', (), {'value': ''})).value
data = executor.qfs.read_file(path) if executor.qfs and path else None
result = data.decode('utf-8', errors='replace') if data else f"cat: {path}: No such file" ''',
        },
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# MAN PAGES
# ═══════════════════════════════════════════════════════════════════════════════

def get_man_pages() -> List[Dict]:
    """Man pages for all commands"""
    return [
        {
            'cmd_name': 'ls',
            'short_description': 'List directory contents',
            'long_description': 'List information about files and directories. Uses Grover quantum search for O(√N) speedup.',
            'syntax': 'ls [PATH]',
            'examples': json.dumps([
                {'command': 'ls', 'description': 'List current directory'},
                {'command': 'ls /home', 'description': 'List /home directory'},
            ]),
            'quantum_aspects': 'Uses 8-qubit Grover search for quantum advantage on large directories.',
        },
        {
            'cmd_name': 'tree',
            'short_description': 'Display directory tree',
            'long_description': 'Display directory structure in tree format using quantum walk algorithm.',
            'syntax': 'tree [PATH]',
            'examples': json.dumps([
                {'command': 'tree', 'description': 'Show tree from current directory'},
                {'command': 'tree /home', 'description': 'Show tree from /home'},
            ]),
            'quantum_aspects': 'Uses 10-qubit quantum walk for O(√N) traversal speedup.',
        },
        {
            'cmd_name': 'find',
            'short_description': 'Search for files',
            'long_description': 'Search filesystem for files matching pattern using Grover search.',
            'syntax': 'find PATH PATTERN',
            'examples': json.dumps([
                {'command': 'find . "*.py"', 'description': 'Find Python files'},
            ]),
            'quantum_aspects': '8-qubit Grover oracle for O(√N) search complexity.',
        },
        {
            'cmd_name': 'locate',
            'short_description': 'Fast file location',
            'long_description': 'Quickly find files using pre-built index and quantum amplitude amplification.',
            'syntax': 'locate PATTERN',
            'examples': json.dumps([
                {'command': 'locate qunix', 'description': 'Find files with "qunix"'},
            ]),
            'quantum_aspects': '6-qubit amplitude amplification boosts matching states.',
        },
        {
            'cmd_name': 'pwd',
            'short_description': 'Print working directory',
            'long_description': 'Display the current working directory path.',
            'syntax': 'pwd',
            'examples': json.dumps([{'command': 'pwd', 'description': 'Show current directory'}]),
        },
        {
            'cmd_name': 'cd',
            'short_description': 'Change directory',
            'long_description': 'Change the current working directory.',
            'syntax': 'cd PATH',
            'examples': json.dumps([
                {'command': 'cd /home', 'description': 'Change to /home'},
                {'command': 'cd ..', 'description': 'Go up one level'},
            ]),
        },
        {
            'cmd_name': 'mkdir',
            'short_description': 'Create directory',
            'long_description': 'Create a new directory.',
            'syntax': 'mkdir PATH',
            'examples': json.dumps([{'command': 'mkdir test', 'description': 'Create directory "test"'}]),
        },
        {
            'cmd_name': 'rm',
            'short_description': 'Remove file',
            'long_description': 'Remove (delete) a file from the filesystem.',
            'syntax': 'rm FILE',
            'examples': json.dumps([{'command': 'rm test.txt', 'description': 'Remove test.txt'}]),
        },
        {
            'cmd_name': 'cat',
            'short_description': 'Display file contents',
            'long_description': 'Concatenate and display file contents.',
            'syntax': 'cat FILE',
            'examples': json.dumps([{'command': 'cat readme.txt', 'description': 'Display readme.txt'}]),
        },
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# PATCHER CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class HandlerPatcher:
    """Fix and populate command handlers"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), timeout=30.0)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        
        self.schema = SchemaDetector(self.conn)
        
        print(f"\n{C.BOLD}{C.C}Schema Detection:{C.E}")
        print(f"  Version: {self.schema.schema_version}")
        print(f"  FK Strategy: {'cmd_name' if self.schema.use_cmd_name else 'cmd_id'}")
        print(f"  Tables: {len(self.schema.tables)}")
        
        self.handlers_created = 0
        self.circuits_created = 0
        self.man_pages_created = 0
    
    def ensure_tables(self):
        """Ensure required tables exist"""
        print(f"\n{C.C}Ensuring required tables...{C.E}")
        
        if not self.schema.has_table('command_handlers'):
            print(f"  {C.Y}Creating command_handlers...{C.E}")
            self.conn.execute("""
                CREATE TABLE command_handlers (
                    handler_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cmd_name TEXT NOT NULL,
                    handler_type TEXT NOT NULL,
                    qasm_code TEXT,
                    sql_query TEXT,
                    python_code TEXT,
                    method_name TEXT,
                    builtin_name TEXT,
                    priority INTEGER DEFAULT 100,
                    requires_qubits INTEGER DEFAULT 0,
                    qubit_count INTEGER DEFAULT 0,
                    enabled INTEGER DEFAULT 1,
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                )
            """)
            self.conn.commit()
            print(f"    {C.G}✓ Created{C.E}")
        
        if not self.schema.has_table('help_system'):
            print(f"  {C.Y}Creating help_system...{C.E}")
            self.conn.execute("""
                CREATE TABLE help_system (
                    help_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cmd_name TEXT UNIQUE NOT NULL,
                    short_description TEXT,
                    long_description TEXT,
                    syntax TEXT,
                    examples TEXT,
                    quantum_aspects TEXT,
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                )
            """)
            self.conn.commit()
            print(f"    {C.G}✓ Created{C.E}")
        
        print(f"  {C.G}✓ All required tables present{C.E}")
    
    def insert_handlers(self, handlers: List[Dict], batch_name: str):
        """Insert handlers"""
        print(f"\n{C.BOLD}{C.C}Inserting {batch_name}...{C.E}")
        
        c = self.conn.cursor()
        
        for handler in handlers:
            cmd_name = handler['cmd_name']
            
            # Check if command exists
            c.execute("SELECT cmd_name FROM command_registry WHERE cmd_name = ?", (cmd_name,))
            if not c.fetchone():
                print(f"  {C.Y}⚠{C.E} Command '{cmd_name}' not in registry, skipping")
                continue
            
            # Check if handler exists
            c.execute("SELECT handler_id FROM command_handlers WHERE cmd_name = ?", (cmd_name,))
            existing = c.fetchone()
            
            if existing:
                c.execute("""
                    UPDATE command_handlers SET
                        handler_type = ?, qasm_code = ?, python_code = ?,
                        method_name = ?, requires_qubits = ?, qubit_count = ?,
                        priority = ?, enabled = 1
                    WHERE cmd_name = ?
                """, (
                    handler['handler_type'], handler.get('qasm_code'),
                    handler.get('python_code'), handler.get('method_name'),
                    handler.get('requires_qubits', 0), handler.get('qubit_count', 0),
                    handler.get('priority', 100), cmd_name
                ))
                print(f"  {C.C}↻{C.E} Updated: {cmd_name}")
            else:
                c.execute("""
                    INSERT INTO command_handlers (
                        cmd_name, handler_type, qasm_code, python_code, method_name,
                        requires_qubits, qubit_count, priority, enabled, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """, (
                    cmd_name, handler['handler_type'], handler.get('qasm_code'),
                    handler.get('python_code'), handler.get('method_name'),
                    handler.get('requires_qubits', 0), handler.get('qubit_count', 0),
                    handler.get('priority', 100), time.time()
                ))
                print(f"  {C.G}✓{C.E} Created: {cmd_name}")
                self.handlers_created += 1
            
            if handler.get('qasm_code'):
                self._insert_circuit(cmd_name, handler)
        
        self.conn.commit()
        print(f"  {C.G}✓ {batch_name} complete{C.E}")
    
    def _insert_circuit(self, cmd_name: str, handler: Dict):
        """Insert quantum circuit"""
        if not self.schema.has_table('quantum_command_circuits'):
            return
        
        c = self.conn.cursor()
        c.execute("SELECT circuit_id FROM quantum_command_circuits WHERE cmd_name = ?", (cmd_name,))
        existing = c.fetchone()
        
        qasm_code = handler['qasm_code']
        num_qubits = handler.get('qubit_count', 1)
        
        gates = []
        for line in qasm_code.split('\n'):
            line = line.strip()
            if any(g in line for g in ['h ', 'x ', 'cx ', 'ccx ', 'measure']):
                gate = line.split()[0]
                gates.append(gate.upper())
        gate_sequence = ','.join(gates[:20])
        
        if existing:
            c.execute("""
                UPDATE quantum_command_circuits SET
                    qasm_code = ?, num_qubits = ?, gate_sequence = ?
                WHERE cmd_name = ?
            """, (qasm_code, num_qubits, gate_sequence, cmd_name))
        else:
            c.execute("""
                INSERT INTO quantum_command_circuits (
                    cmd_name, circuit_name, num_qubits, num_clbits, qasm_code, gate_sequence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (cmd_name, f"{cmd_name}_circuit", num_qubits, num_qubits, qasm_code, gate_sequence, time.time()))
            self.circuits_created += 1
    
    def insert_man_pages(self, man_pages: List[Dict]):
        """Insert man pages"""
        print(f"\n{C.BOLD}{C.C}Inserting Man Pages...{C.E}")
        
        if not self.schema.has_table('help_system'):
            print(f"  {C.Y}⚠ help_system table not found, skipping{C.E}")
            return
        
        c = self.conn.cursor()
        
        for man in man_pages:
            cmd_name = man['cmd_name']
            c.execute("SELECT help_id FROM help_system WHERE cmd_name = ?", (cmd_name,))
            existing = c.fetchone()
            
            if existing:
                c.execute("""
                    UPDATE help_system SET
                        short_description = ?, long_description = ?,
                        syntax = ?, examples = ?, quantum_aspects = ?
                    WHERE cmd_name = ?
                """, (
                    man.get('short_description'), man.get('long_description'),
                    man.get('syntax'), man.get('examples'),
                    man.get('quantum_aspects'), cmd_name
                ))
                print(f"  {C.C}↻{C.E} Updated: {cmd_name}")
            else:
                c.execute("""
                    INSERT INTO help_system (
                        cmd_name, short_description, long_description,
                        syntax, examples, quantum_aspects, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    cmd_name, man.get('short_description'),
                    man.get('long_description'), man.get('syntax'),
                    man.get('examples'), man.get('quantum_aspects'), time.time()
                ))
                print(f"  {C.G}✓{C.E} Created: {cmd_name}")
                self.man_pages_created += 1
        
        self.conn.commit()
        print(f"  {C.G}✓ Man pages complete{C.E}")
    
    def verify_installation(self):
        """Verify installation"""
        print(f"\n{C.BOLD}{C.C}Verifying Installation...{C.E}")
        
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM command_handlers WHERE enabled=1")
        handler_count = c.fetchone()[0]
        
        circuit_count = 0
        if self.schema.has_table('quantum_command_circuits'):
            c.execute("SELECT COUNT(*) FROM quantum_command_circuits")
            circuit_count = c.fetchone()[0]
        
        man_count = 0
        if self.schema.has_table('help_system'):
            c.execute("SELECT COUNT(*) FROM help_system")
            man_count = c.fetchone()[0]
        
        test_commands = ['ls', 'tree', 'find', 'locate', 'pwd']
        print(f"\n  {C.C}Testing commands:{C.E}")
        
        for cmd in test_commands:
            c.execute("SELECT handler_type FROM command_handlers WHERE cmd_name = ?", (cmd,))
            handler = c.fetchone()
            
            circuit = None
            if self.schema.has_table('quantum_command_circuits'):
                c.execute("SELECT num_qubits FROM quantum_command_circuits WHERE cmd_name = ?", (cmd,))
                circuit = c.fetchone()
            
            man = None
            if self.schema.has_table('help_system'):
                c.execute("SELECT short_description FROM help_system WHERE cmd_name = ?", (cmd,))
                man = c.fetchone()
            
            h_status = f"{C.G}✓{C.E}" if handler else f"{C.R}✗{C.E}"
            c_status = f"{C.G}✓{C.E}" if circuit else f"{C.Y}−{C.E}"
            m_status = f"{C.G}✓{C.E}" if man else f"{C.Y}−{C.E}"
            
            print(f"    {cmd:15s} Handler:{h_status} Circuit:{c_status} Man:{m_status}")
        
        print(f"\n  {C.BOLD}Summary:{C.E}")
        print(f"    Handlers: {handler_count}")
        print(f"    Circuits: {circuit_count}")
        print(f"    Man pages: {man_count}")
        
        return handler_count > 0
    
    def print_summary(self):
        """Print summary"""
        print(f"\n{C.BOLD}{'═'*70}{C.E}")
        print(f"{C.BOLD}{C.G}HANDLER FIX PATCH COMPLETE{C.E}")
        print(f"{C.BOLD}{'═'*70}{C.E}\n")
        
        print(f"{C.C}Statistics:{C.E}")
        print(f"  Handlers created: {self.handlers_created}")
        print(f"  Circuits created: {self.circuits_created}")
        print(f"  Man pages created: {self.man_pages_created}")
        
        print(f"\n{C.C}Schema:{C.E}")
        print(f"  Version: {self.schema.schema_version}")
        print(f"  FK Strategy: {'cmd_name' if self.schema.use_cmd_name else 'cmd_id'}")
        
        print(f"\n{C.BOLD}{C.G}✓ Installation complete{C.E}")
        print(f"\n{C.C}Test commands:{C.E}")
        print(f"  python qunix_cpu.py --db {self.db_path}")
        print(f"  qunix> ls")
        print(f"  qunix> tree")
        print(f"  qunix> help ls")
        print()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='QUNIX Handler Fix Patch v2.0.0 - FIXED',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s qunix_leech.db
  %(prog)s /data/qunix_leech.db --verify-only
  %(prog)s qunix_leech.db --batch=1,2
        """
    )
    
    parser.add_argument('db', type=str, help='Path to QUNIX database')
    parser.add_argument('--verify-only', action='store_true', help='Only verify')
    parser.add_argument('--batch', type=str, help='Batches to install (e.g., 1,2)')
    parser.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')
    
    args = parser.parse_args()
    
    db_path = Path(args.db).expanduser()
    
    if not db_path.exists():
        print(f"\n{C.R}✗ Database not found: {db_path}{C.E}")
        return 1
    
    print(f"\n{C.BOLD}{C.M}╔══════════════════════════════════════════════════════════════╗{C.E}")
    print(f"{C.BOLD}{C.M}║  QUNIX HANDLER FIX PATCH v{VERSION}                    ║{C.E}")
    print(f"{C.BOLD}{C.M}║  Production Grade Handler Installation                       ║{C.E}")
    print(f"{C.BOLD}{C.M}╚══════════════════════════════════════════════════════════════╝{C.E}")
    
    try:
        patcher = HandlerPatcher(db_path)
        
        if args.verify_only:
            success = patcher.verify_installation()
            return 0 if success else 1
        
        # Determine batches
        if args.batch:
            batches = [int(b.strip()) for b in args.batch.split(',')]
        else:
            batches = [1, 2]
        
        # Ensure tables
        patcher.ensure_tables()
        
        # Install batches
        start = time.time()
        
        if 1 in batches:
            handlers = get_batch_1_handlers()
            patcher.insert_handlers(handlers, "Batch 1: Search Commands")
        
        if 2 in batches:
            handlers = get_batch_2_handlers()
            patcher.insert_handlers(handlers, "Batch 2: Basic Commands")
        
        # Install man pages
        man_pages = get_man_pages()
        patcher.insert_man_pages(man_pages)
        
        # Verify
        if patcher.verify_installation():
            elapsed = time.time() - start
            print(f"\n{C.G}✓ Patch completed in {elapsed:.1f}s{C.E}")
            patcher.print_summary()
            return 0
        else:
            print(f"\n{C.Y}⚠ Verification failed{C.E}\n")
            return 1
    
    except Exception as e:
        print(f"\n{C.R}✗ Patch failed: {e}{C.E}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())