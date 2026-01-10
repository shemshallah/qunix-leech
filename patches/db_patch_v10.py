#!/usr/bin/env python3
"""
QUNIX MISSING COMMAND HANDLERS PATCH
Adds handlers for the remaining 30 commands
"""

import sqlite3
import time
import sys

VERSION = "MISSING_30_HANDLERS"
DB_PATH = "/home/Shemshallah/qunix_leech.db"

# All 30 missing handlers with implementations
MISSING_HANDLERS = [
    # BUILTIN (3)
    {
        'cmd_name': 'whatis',
        'handler_type': 'SQL_QUERY',
        'sql_query': 'SELECT cmd_name, cmd_description FROM command_registry WHERE cmd_name = ?',
        'python_code': '''
def handler(args, flags, context, conn):
    cmd = args.get('command', '')
    c = conn.cursor()
    c.execute("SELECT cmd_description FROM command_registry WHERE cmd_name = ?", (cmd,))
    row = c.fetchone()
    return row[0] if row else f"{cmd}: nothing appropriate"
''',
        'result_formatter': '{result}'
    },
    {
        'cmd_name': 'which',
        'handler_type': 'SQL_QUERY',
        'sql_query': 'SELECT cmd_name FROM command_registry WHERE cmd_name = ? AND cmd_enabled = 1',
        'python_code': '''
def handler(args, flags, context, conn):
    cmd = args.get('command', '')
    c = conn.cursor()
    c.execute("SELECT cmd_name FROM command_registry WHERE cmd_name = ? AND cmd_enabled = 1", (cmd,))
    return f"/bin/{cmd}" if c.fetchone() else ""
''',
        'result_formatter': '{result}'
    },
    {
        'cmd_name': 'whereis',
        'handler_type': 'SQL_QUERY',
        'sql_query': 'SELECT cmd_name FROM command_registry WHERE cmd_name = ?',
        'python_code': '''
def handler(args, flags, context, conn):
    cmd = args.get('command', '')
    c = conn.cursor()
    c.execute("SELECT cmd_name FROM command_registry WHERE cmd_name = ?", (cmd,))
    if c.fetchone():
        return f"{cmd}: /bin/{cmd} /usr/share/man/man1/{cmd}.1"
    return f"{cmd}:"
''',
        'result_formatter': '{result}'
    },
    
    # FILESYSTEM (4)
    {
        'cmd_name': 'dir',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    # dir is just ls with different default flags
    path = args.get('path', '.')
    c = conn.cursor()
    c.execute("SELECT name, type FROM quantum_fs WHERE parent_path = ?", (path,))
    entries = [f"{r[0]}{'/' if r[1] == 'dir' else ''}" for r in c.fetchall()]
    return '  '.join(entries)
''',
        'result_formatter': '{result}'
    },
    {
        'cmd_name': 'rmdir',
        'handler_type': 'FILESYSTEM',
        'python_code': '''
def handler(args, flags, context, conn):
    dirname = args.get('dir', '')
    c = conn.cursor()
    c.execute("SELECT type FROM quantum_fs WHERE path = ?", (dirname,))
    row = c.fetchone()
    if not row:
        return {"error": f"rmdir: {dirname}: No such directory"}
    if row[0] != 'dir':
        return {"error": f"rmdir: {dirname}: Not a directory"}
    c.execute("SELECT COUNT(*) FROM quantum_fs WHERE parent_path = ?", (dirname,))
    if c.fetchone()[0] > 0:
        return {"error": f"rmdir: {dirname}: Directory not empty"}
    c.execute("DELETE FROM quantum_fs WHERE path = ?", (dirname,))
    conn.commit()
    return {"removed": dirname}
''',
        'result_formatter': ''
    },
    {
        'cmd_name': 'stat',
        'handler_type': 'FILESYSTEM',
        'python_code': '''
def handler(args, flags, context, conn):
    filepath = args.get('file', '')
    c = conn.cursor()
    c.execute("SELECT * FROM quantum_fs WHERE path = ?", (filepath,))
    row = c.fetchone()
    if not row:
        return f"stat: cannot stat '{filepath}': No such file or directory"
    return f"  File: {filepath}\\n  Size: {row[2]}\\n  Type: {row[1]}"
''',
        'result_formatter': '{result}'
    },
    {
        'cmd_name': 'file',
        'handler_type': 'FILESYSTEM',
        'python_code': '''
def handler(args, flags, context, conn):
    filepath = args.get('file', '')
    c = conn.cursor()
    c.execute("SELECT type, content FROM quantum_fs WHERE path = ?", (filepath,))
    row = c.fetchone()
    if not row:
        return f"{filepath}: cannot open"
    ftype = row[0]
    if ftype == 'dir':
        return f"{filepath}: directory"
    content = row[1] or ""
    if content.startswith('#!/'):
        return f"{filepath}: script text executable"
    return f"{filepath}: ASCII text"
''',
        'result_formatter': '{result}'
    },
    
    # TEXT (3)
    {
        'cmd_name': 'more',
        'handler_type': 'TEXT_PROCESSOR',
        'python_code': '''
def handler(args, flags, context, conn):
    filepath = args.get('file', '')
    c = conn.cursor()
    c.execute("SELECT content FROM quantum_fs WHERE path = ?", (filepath,))
    row = c.fetchone()
    if not row:
        return f"more: {filepath}: No such file"
    lines = (row[0] or "").split('\\n')
    return '\\n'.join(lines[:24]) + '\\n--More--(50%)--'
''',
        'result_formatter': '{result}'
    },
    {
        'cmd_name': 'less',
        'handler_type': 'TEXT_PROCESSOR',
        'python_code': '''
def handler(args, flags, context, conn):
    filepath = args.get('file', '')
    c = conn.cursor()
    c.execute("SELECT content FROM quantum_fs WHERE path = ?", (filepath,))
    row = c.fetchone()
    if not row:
        return f"less: {filepath}: No such file"
    return row[0] or ""
''',
        'result_formatter': '{result}'
    },
    {
        'cmd_name': 'patch',
        'handler_type': 'TEXT_PROCESSOR',
        'python_code': '''
def handler(args, flags, context, conn):
    return {"status": "patch: Not implemented yet"}
''',
        'result_formatter': 'patch: Not implemented'
    },
    
    # NETWORK (5)
    {
        'cmd_name': 'route',
        'handler_type': 'NETWORK',
        'python_code': '''
def handler(args, flags, context, conn):
    c = conn.cursor()
    c.execute("SELECT * FROM rc LIMIT 10")
    routes = c.fetchall()
    return {"routes": len(routes), "table": "routing"}
''',
        'result_formatter': 'Kernel IP routing table'
    },
    {
        'cmd_name': 'scp',
        'handler_type': 'NETWORK',
        'python_code': '''
def handler(args, flags, context, conn):
    src = args.get('source', '')
    dest = args.get('dest', '')
    return {"copied": src, "to": dest, "protocol": "scp"}
''',
        'result_formatter': 'scp: {copied} -> {to}'
    },
    {
        'cmd_name': 'ftp',
        'handler_type': 'NETWORK',
        'python_code': '''
def handler(args, flags, context, conn):
    host = args.get('host', 'localhost')
    return {"host": host, "status": "Connected", "mode": "passive"}
''',
        'result_formatter': 'Connected to {host}'
    },
    {
        'cmd_name': 'telnet',
        'handler_type': 'NETWORK',
        'python_code': '''
def handler(args, flags, context, conn):
    host = args.get('host', 'localhost')
    port = args.get('port', 23)
    return {"host": host, "port": port, "status": "Connected"}
''',
        'result_formatter': 'Trying {host}:{port}...'
    },
    {
        'cmd_name': 'nslookup',
        'handler_type': 'NETWORK',
        'python_code': '''
def handler(args, flags, context, conn):
    name = args.get('name', 'localhost')
    return {"name": name, "address": "127.0.0.1", "server": "dns.qunix"}
''',
        'result_formatter': 'Server: {server}\\nAddress: {address}'
    },
    
    # SYSTEM (3)
    {
        'cmd_name': 'time',
        'handler_type': 'SYSTEM',
        'python_code': '''
def handler(args, flags, context, conn):
    import time
    cmd = args.get('command', '')
    start = time.time()
    # Simulate command execution
    elapsed = time.time() - start
    return {"real": elapsed, "user": elapsed * 0.8, "sys": elapsed * 0.2}
''',
        'result_formatter': 'real {real:.3f}s\\nuser {user:.3f}s\\nsys {sys:.3f}s'
    },
    {
        'cmd_name': 'w',
        'handler_type': 'SYSTEM',
        'python_code': '''
def handler(args, flags, context, conn):
    c = conn.cursor()
    c.execute("SELECT username, login_time FROM quantum_sessions WHERE active = 1")
    users = c.fetchall()
    return {"users": len(users), "uptime": "10 days"}
''',
        'result_formatter': 'USER     LOGIN@   IDLE   JCPU   PCPU  WHAT'
    },
    {
        'cmd_name': 'export',
        'handler_type': 'BUILTIN',
        'python_code': '''
def handler(args, flags, context, conn):
    assignment = args.get('assignment', '')
    if '=' in assignment:
        var, val = assignment.split('=', 1)
        context['env'] = context.get('env', {})
        context['env'][var] = val
        return {"exported": var, "value": val}
    return {"error": "export: invalid syntax"}
''',
        'result_formatter': ''
    },
    
    # QUNIX (10)
    {
        'cmd_name': 'bus_status',
        'handler_type': 'SQL_QUERY',
        'sql_query': 'SELECT * FROM bus_core WHERE bus_id = 1',
        'python_code': '''
def handler(args, flags, context, conn):
    c = conn.cursor()
    c.execute("SELECT active, mode, packets_processed FROM bus_core WHERE bus_id = 1")
    row = c.fetchone()
    if row:
        return {"active": bool(row[0]), "mode": row[1], "packets": row[2]}
    return {"active": False}
''',
        'result_formatter': 'Bus Status: {"active" if active else "inactive"} | Mode: {mode} | Packets: {packets}'
    },
    {
        'cmd_name': 'bus_send',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': 'h q[0]; cx q[0],q[1];',
        'python_code': '''
def handler(args, flags, context, conn):
    dest = args.get('dest', '')
    data = args.get('data', '')
    return {"sent": len(data), "to": dest, "protocol": "quantum_bus"}
''',
        'result_formatter': 'Sent {sent} bytes to {to}',
        'requires_qubits': 1,
        'qubit_count': 2
    },
    {
        'cmd_name': 'bus_recv',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': 'measure q[0] -> c[0];',
        'python_code': '''
def handler(args, flags, context, conn):
    return {"received": 0, "from": "quantum_bus"}
''',
        'result_formatter': 'Received {received} bytes',
        'requires_qubits': 1,
        'qubit_count': 1
    },
    {
        'cmd_name': 'qnic_status',
        'handler_type': 'SQL_QUERY',
        'sql_query': 'SELECT * FROM qnic_core WHERE qnic_id = 1',
        'python_code': '''
def handler(args, flags, context, conn):
    c = conn.cursor()
    c.execute("SELECT active, bind_address, bind_port FROM qnic_core WHERE qnic_id = 1")
    row = c.fetchone()
    if row:
        return {"active": bool(row[0]), "address": row[1], "port": row[2]}
    return {"active": False}
''',
        'result_formatter': 'QNIC: {"active" if active else "inactive"} | {address}:{port}'
    },
    {
        'cmd_name': 'qnic_connect',
        'handler_type': 'NETWORK',
        'python_code': '''
def handler(args, flags, context, conn):
    address = args.get('address', '')
    c = conn.cursor()
    c.execute("INSERT INTO qnic_connections (dest_ip, state, created_at) VALUES (?, 'ESTABLISHED', ?)", 
              (address, __import__('time').time()))
    conn.commit()
    return {"connected": address, "status": "ESTABLISHED"}
''',
        'result_formatter': 'Connected to {connected}',
        'requires_qubits': 1
    },
    {
        'cmd_name': 'qnic_listen',
        'handler_type': 'NETWORK',
        'python_code': '''
def handler(args, flags, context, conn):
    port = args.get('port', 8080)
    c = conn.cursor()
    c.execute("UPDATE qnic_core SET bind_port = ?, active = 1 WHERE qnic_id = 1", (port,))
    conn.commit()
    return {"listening": port}
''',
        'result_formatter': 'QNIC listening on port {listening}'
    },
    {
        'cmd_name': 'hyperbolic',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': 'ry(0.7854) q[0];',
        'python_code': '''
def handler(args, flags, context, conn):
    p1 = args.get('p1', '0,0')
    p2 = args.get('p2', '1,0')
    import math
    # Simplified hyperbolic distance
    x1, y1 = map(float, p1.split(','))
    x2, y2 = map(float, p2.split(','))
    dist = math.sqrt((x2-x1)**2 + (y2-y1)**2)
    return {"distance": dist, "metric": "hyperbolic"}
''',
        'result_formatter': 'Hyperbolic distance: {distance:.4f}',
        'requires_qubits': 1,
        'qubit_count': 1
    },
    {
        'cmd_name': 'circuit_save',
        'handler_type': 'SQL_QUERY',
        'sql_query': 'INSERT INTO quantum_command_circuits (cmd_name, circuit_name, num_qubits, qasm_code, created_at) VALUES (?, ?, ?, ?, ?)',
        'python_code': '''
def handler(args, flags, context, conn):
    name = args.get('name', '')
    qasm = args.get('qasm', '')
    c = conn.cursor()
    c.execute("INSERT INTO quantum_command_circuits (circuit_name, num_qubits, qasm_code, created_at) VALUES (?, 1, ?, ?)",
              (name, qasm, __import__('time').time()))
    conn.commit()
    return {"saved": name}
''',
        'result_formatter': 'Circuit saved: {saved}',
        'requires_qubits': 1
    },
    {
        'cmd_name': 'opcode',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    code = args.get('code', '')
    try:
        opcode = int(code, 16)
        c = conn.cursor()
        c.execute("SELECT mnemonic, description FROM cpu_opcodes WHERE opcode = ?", (opcode,))
        row = c.fetchone()
        if row:
            return {"opcode": hex(opcode), "mnemonic": row[0], "description": row[1]}
        return {"opcode": hex(opcode), "status": "unknown"}
    except:
        return {"error": "Invalid opcode"}
''',
        'result_formatter': 'Opcode {opcode}: {mnemonic} - {description}'
    },
    {
        'cmd_name': 'binary',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    hex_str = args.get('hex', '')
    try:
        binary = bytes.fromhex(hex_str)
        return {"binary": hex_str, "length": len(binary), "decoded": True}
    except:
        return {"error": "Invalid hex string"}
''',
        'result_formatter': 'Binary: {length} bytes'
    },
    
    # QUANTUM (1)
    {
        'cmd_name': 'qcy',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
cy q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];''',
        'context_map': '{"control": "args.control", "target": "args.target", "shots": "flags.s or 1024"}',
        'result_formatter': '{"type": "histogram", "title": "CY Gate", "qubits": ["{control}", "{target}"]}',
        'requires_qubits': 1,
        'qubit_count': 2,
        'priority': 100
    },
    
    # MISC (1)
    {
        'cmd_name': 'type',
        'handler_type': 'BUILTIN',
        'python_code': '''
def handler(args, flags, context, conn):
    cmd = args.get('command', '')
    c = conn.cursor()
    c.execute("SELECT cmd_category FROM command_registry WHERE cmd_name = ?", (cmd,))
    row = c.fetchone()
    if row:
        return f"{cmd} is a {row[0]} command"
    return f"{cmd}: not found"
''',
        'result_formatter': '{result}'
    },
]

def insert_handlers(conn):
    """Insert all 30 missing handlers"""
    c = conn.cursor()
    now = time.time()
    inserted = 0
    
    for h in MISSING_HANDLERS:
        # Get cmd_id
        c.execute("SELECT cmd_id FROM command_registry WHERE cmd_name = ?", (h['cmd_name'],))
        row = c.fetchone()
        if not row:
            print(f"  Warning: Command '{h['cmd_name']}' not found in registry")
            continue
        
        cmd_id = row[0]
        
        try:
            c.execute("""
                INSERT OR REPLACE INTO command_handlers 
                (cmd_id, handler_type, qasm_code, sql_query, python_code, 
                 context_map, result_formatter, requires_qubits, qubit_count, 
                 priority, created_at, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                cmd_id,
                h['handler_type'],
                h.get('qasm_code'),
                h.get('sql_query'),
                h.get('python_code'),
                h.get('context_map', '{}'),
                h.get('result_formatter', '{result}'),
                h.get('requires_qubits', 0),
                h.get('qubit_count', 0),
                h.get('priority', 100),
                now
            ))
            inserted += 1
            print(f"  ✓ {h['cmd_name']}")
        except Exception as e:
            print(f"  ✗ {h['cmd_name']}: {e}")
    
    conn.commit()
    return inserted

def apply_patch(db_path=None):
    if db_path is None:
        db_path = DB_PATH
    
    print(f"\n╔══════════════════════════════════════════════════════════╗")
    print(f"║  QUNIX MISSING 30 HANDLERS PATCH                         ║")
    print(f"╚══════════════════════════════════════════════════════════╝\n")
    print(f"Target: {db_path}\n")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        print("Inserting 30 missing handlers...")
        inserted = insert_handlers(conn)
        
        # Verify
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM command_registry WHERE cmd_enabled = 1")
        total_cmds = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM command_handlers WHERE enabled = 1")
        total_handlers = c.fetchone()[0]
        
        c.execute("""
            SELECT COUNT(*) FROM command_registry 
            WHERE cmd_enabled = 1 
            AND cmd_id NOT IN (SELECT DISTINCT cmd_id FROM command_handlers WHERE enabled = 1)
        """)
        still_missing = c.fetchone()[0]
        
        print(f"\n╔══════════════════════════════════════════════════════════╗")
        print(f"║  COMPLETE: {total_cmds} commands, {total_handlers} handlers, {still_missing} missing           ║")
        print(f"╚══════════════════════════════════════════════════════════╝\n")
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    sys.exit(0 if apply_patch(db) else 1)


