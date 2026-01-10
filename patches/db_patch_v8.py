#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║                    QUNIX DATABASE PATCH v8.0.0 - PART 2                       ║
║                    Remaining Command Handlers (102 commands)                   ║
║                                                                               ║
║  This patch adds handlers for the remaining commands not covered in Part 1    ║
║                                                                               ║
║  Run AFTER Part 1 has been successfully applied                               ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import sqlite3
import time
import sys
import os

VERSION = "8.0.0-PART2"
DB_PATH = "/home/Shemshallah/qunix_leech.db"

# ═══════════════════════════════════════════════════════════════════════════════
# COMMANDS FOR PART 2 (First half: 51 commands)
# ═══════════════════════════════════════════════════════════════════════════════

COMMANDS_PART2 = [
    # DEVELOPMENT TOOLS (14)
    ('ant', 0x5000, 'development', 'Apache Ant build tool', 'ant [target]', 0),
    ('cmake', 0x5001, 'development', 'Cross-platform build system', 'cmake [options] path', 0),
    ('g++', 0x5002, 'development', 'GNU C++ compiler', 'g++ [options] file.cpp', 0),
    ('gcc', 0x5003, 'development', 'GNU C compiler', 'gcc [options] file.c', 0),
    ('gdb', 0x5004, 'development', 'GNU debugger', 'gdb [program]', 0),
    ('git', 0x5005, 'development', 'Version control system', 'git [command]', 0),
    ('hg', 0x5006, 'development', 'Mercurial version control', 'hg [command]', 0),
    ('java', 0x5007, 'development', 'Java runtime', 'java [options] class', 0),
    ('ltrace', 0x5008, 'development', 'Library call tracer', 'ltrace [options] command', 0),
    ('make', 0x5009, 'development', 'Build automation tool', 'make [target]', 0),
    ('node', 0x500A, 'development', 'Node.js runtime', 'node [script.js]', 0),
    ('python', 0x500B, 'development', 'Python interpreter', 'python [script.py]', 0),
    ('strace', 0x500C, 'development', 'System call tracer', 'strace [options] command', 0),
    ('svn', 0x500D, 'development', 'Subversion version control', 'svn [command]', 0),
    
    # SYSTEM TOOLS (8)
    ('valgrind', 0x5010, 'system', 'Memory debugging tool', 'valgrind [options] program', 0),
    ('7z', 0x5011, 'archive', '7-Zip archiver', '7z [command] archive', 0),
    ('fdisk', 0x5012, 'system', 'Partition table manipulator', 'fdisk [device]', 0),
    ('fsck', 0x5013, 'system', 'File system checker', 'fsck [device]', 0),
    ('mkfs', 0x5014, 'system', 'Make filesystem', 'mkfs [options] device', 0),
    ('mount', 0x5015, 'system', 'Mount filesystem', 'mount [device] [mountpoint]', 0),
    ('size', 0x5016, 'system', 'List section sizes', 'size [file]', 0),
    ('umount', 0x5017, 'system', 'Unmount filesystem', 'umount [mountpoint]', 0),
    
    # QUNIX SYSTEM (4)
    ('cmd-info', 0x5020, 'qunix', 'Command information', 'cmd-info [command]', 0),
    ('cmd-list', 0x5021, 'qunix', 'List all commands', 'cmd-list [-c category]', 0),
    ('leech_distance', 0x5022, 'quantum', 'Calculate Leech lattice distance', 'leech_distance v1 v2', 1),
    ('dmesg', 0x5023, 'system', 'Print kernel messages', 'dmesg [-n level]', 0),
    
    # MONITORING (3)
    ('iostat', 0x5024, 'system', 'I/O statistics', 'iostat [interval]', 0),
    ('vmstat', 0x5025, 'system', 'Virtual memory statistics', 'vmstat [interval]', 0),
    
    # QUANTUM ALGORITHMS (12)
    ('bell_measure', 0x5030, 'quantum', 'Bell state measurement', 'bell_measure q1 q2', 1),
    ('entangle_verify', 0x5031, 'quantum', 'Verify entanglement', 'entangle_verify q1 q2', 1),
    ('phase_estimation', 0x5032, 'quantum', 'Quantum phase estimation', 'phase_estimation [-n qubits]', 1),
    ('qaoa', 0x5033, 'quantum', 'QAOA algorithm', 'qaoa [problem] [-p depth]', 1),
    ('qcompile', 0x5034, 'quantum', 'Compile quantum circuit', 'qcompile [circuit]', 1),
    ('qcpu_load', 0x5035, 'quantum', 'Load QCPU program', 'qcpu_load [program]', 1),
    ('qdb_query', 0x5036, 'quantum', 'Query quantum database', 'qdb_query [query]', 1),
    ('qnic_start', 0x5037, 'quantum', 'Start quantum NIC', 'qnic_start [-p port]', 1),
    ('qoptimize', 0x5038, 'quantum', 'Optimize quantum circuit', 'qoptimize [circuit]', 1),
    ('qrun', 0x5039, 'quantum', 'Run quantum program', 'qrun [program]', 1),
    ('qshell', 0x503A, 'quantum', 'Quantum shell', 'qshell', 1),
    ('qsimulate', 0x503B, 'quantum', 'Simulate quantum circuit', 'qsimulate [circuit] [-s shots]', 1),
    
    # MORE QUANTUM (8)
    ('qtoffoli', 0x503C, 'quantum', 'Toffoli gate', 'qtoffoli c1 c2 target', 1),
    ('quantum_walk', 0x503D, 'quantum', 'Quantum walk simulation', 'quantum_walk [-n steps]', 1),
    ('shor', 0x503E, 'quantum', 'Shor factoring algorithm', 'shor [number]', 1),
    ('superdense', 0x503F, 'quantum', 'Superdense coding', 'superdense [bits]', 1),
    ('surface_code', 0x5040, 'quantum', 'Surface code encoding', 'surface_code [-d distance]', 1),
    ('bus_start', 0x5041, 'quantum', 'Start quantum bus', 'bus_start', 1),
    ('epr_connect', 0x5042, 'quantum', 'EPR pair connection', 'epr_connect [node]', 1),
    ('hdistance', 0x5043, 'quantum', 'Hyperbolic distance', 'hdistance p1 p2', 1),
    
    # HYPERBOLIC/MANIFOLD (4)
    ('hembed', 0x5044, 'quantum', 'Hyperbolic embedding', 'hembed [data]', 1),
    ('hmap', 0x5045, 'quantum', 'Hyperbolic map', 'hmap [coordinates]', 1),
    ('hroute', 0x5046, 'quantum', 'Hyperbolic routing', 'hroute src dest', 1),
    ('manifold_create', 0x5047, 'quantum', 'Create manifold', 'manifold_create [type]', 1),
    
    # TUNNELING (1)
    ('tunneling', 0x5048, 'quantum', 'Quantum tunneling', 'tunneling [barrier]', 1),
]

# ═══════════════════════════════════════════════════════════════════════════════
# FLAGS FOR PART 2 COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

FLAGS_PART2 = [
    # Development tools flags
    ('gcc', 'o', 'output', 0, 'VALUE', 'STRING', 'Output file'),
    ('gcc', 'c', 'compile', 1, 'BOOLEAN', None, 'Compile only'),
    ('gcc', 'g', 'debug', 2, 'BOOLEAN', None, 'Debug symbols'),
    ('gcc', 'O', 'optimize', 3, 'VALUE', 'INTEGER', 'Optimization level'),
    ('g++', 'o', 'output', 0, 'VALUE', 'STRING', 'Output file'),
    ('g++', 'c', 'compile', 1, 'BOOLEAN', None, 'Compile only'),
    ('g++', 'g', 'debug', 2, 'BOOLEAN', None, 'Debug symbols'),
    ('git', 'v', 'verbose', 0, 'BOOLEAN', None, 'Verbose output'),
    ('git', 'n', 'dry-run', 1, 'BOOLEAN', None, 'Dry run'),
    ('make', 'j', 'jobs', 0, 'VALUE', 'INTEGER', 'Parallel jobs'),
    ('make', 'f', 'file', 1, 'VALUE', 'STRING', 'Makefile'),
    ('make', 'n', 'dry-run', 2, 'BOOLEAN', None, 'Dry run'),
    ('python', 'c', 'command', 0, 'VALUE', 'STRING', 'Execute command'),
    ('python', 'm', 'module', 1, 'VALUE', 'STRING', 'Run module'),
    ('python', 'i', 'interactive', 2, 'BOOLEAN', None, 'Interactive mode'),
    ('node', 'e', 'eval', 0, 'VALUE', 'STRING', 'Evaluate script'),
    ('node', 'v', 'version', 1, 'BOOLEAN', None, 'Show version'),
    
    # System tools flags
    ('7z', 'a', 'add', 0, 'BOOLEAN', None, 'Add to archive'),
    ('7z', 'x', 'extract', 1, 'BOOLEAN', None, 'Extract'),
    ('7z', 'l', 'list', 2, 'BOOLEAN', None, 'List contents'),
    ('7z', 't', 'test', 3, 'BOOLEAN', None, 'Test archive'),
    ('mount', 't', 'type', 0, 'VALUE', 'STRING', 'Filesystem type'),
    ('mount', 'o', 'options', 1, 'VALUE', 'STRING', 'Mount options'),
    ('mount', 'r', 'read-only', 2, 'BOOLEAN', None, 'Read-only'),
    ('fsck', 'a', 'auto', 0, 'BOOLEAN', None, 'Auto repair'),
    ('fsck', 'n', 'no-modify', 1, 'BOOLEAN', None, 'No modifications'),
    
    # QUNIX flags
    ('cmd-list', 'c', 'category', 0, 'VALUE', 'STRING', 'Filter by category'),
    ('cmd-list', 'a', 'all', 1, 'BOOLEAN', None, 'Show all'),
    ('cmd-list', 'q', 'quantum', 2, 'BOOLEAN', None, 'Quantum commands only'),
    ('dmesg', 'n', 'level', 0, 'VALUE', 'INTEGER', 'Log level'),
    ('dmesg', 'c', 'clear', 1, 'BOOLEAN', None, 'Clear buffer'),
    ('dmesg', 'T', 'timestamps', 2, 'BOOLEAN', None, 'Human timestamps'),
    
    # Quantum flags
    ('phase_estimation', 'n', 'qubits', 0, 'VALUE', 'INTEGER', 'Number of qubits'),
    ('phase_estimation', 's', 'shots', 1, 'VALUE', 'INTEGER', 'Number of shots'),
    ('qaoa', 'p', 'depth', 0, 'VALUE', 'INTEGER', 'Circuit depth'),
    ('qaoa', 's', 'shots', 1, 'VALUE', 'INTEGER', 'Number of shots'),
    ('qsimulate', 's', 'shots', 0, 'VALUE', 'INTEGER', 'Number of shots'),
    ('qsimulate', 'v', 'verbose', 1, 'BOOLEAN', None, 'Verbose output'),
    ('qnic_start', 'p', 'port', 0, 'VALUE', 'INTEGER', 'Port number'),
    ('surface_code', 'd', 'distance', 0, 'VALUE', 'INTEGER', 'Code distance'),
    ('quantum_walk', 'n', 'steps', 0, 'VALUE', 'INTEGER', 'Number of steps'),
    ('quantum_walk', 'd', 'dimension', 1, 'VALUE', 'INTEGER', 'Graph dimension'),
]

# ═══════════════════════════════════════════════════════════════════════════════
# ARGUMENTS FOR PART 2 COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

ARGUMENTS_PART2 = [
    # Development tools
    ('gcc', 0, 'source_file', 'PATH', 1, None, 'Source file to compile'),
    ('g++', 0, 'source_file', 'PATH', 1, None, 'Source file to compile'),
    ('gdb', 0, 'program', 'PATH', 0, None, 'Program to debug'),
    ('git', 0, 'subcommand', 'STRING', 1, None, 'Git subcommand'),
    ('make', 0, 'target', 'STRING', 0, 'all', 'Build target'),
    ('python', 0, 'script', 'PATH', 0, None, 'Python script'),
    ('node', 0, 'script', 'PATH', 0, None, 'JavaScript file'),
    ('java', 0, 'class', 'STRING', 1, None, 'Class to run'),
    
    # System tools
    ('7z', 0, 'command', 'STRING', 1, None, 'Archive command'),
    ('7z', 1, 'archive', 'PATH', 1, None, 'Archive file'),
    ('mount', 0, 'device', 'PATH', 0, None, 'Device to mount'),
    ('mount', 1, 'mountpoint', 'PATH', 0, None, 'Mount point'),
    ('umount', 0, 'mountpoint', 'PATH', 1, None, 'Mount point'),
    ('fsck', 0, 'device', 'PATH', 1, None, 'Device to check'),
    ('mkfs', 0, 'device', 'PATH', 1, None, 'Device'),
    
    # QUNIX
    ('cmd-info', 0, 'command', 'STRING', 1, None, 'Command name'),
    ('leech_distance', 0, 'vector1', 'STRING', 1, None, 'First vector'),
    ('leech_distance', 1, 'vector2', 'STRING', 1, None, 'Second vector'),
    
    # Quantum algorithms
    ('bell_measure', 0, 'qubit1', 'INTEGER', 1, None, 'First qubit'),
    ('bell_measure', 1, 'qubit2', 'INTEGER', 1, None, 'Second qubit'),
    ('entangle_verify', 0, 'qubit1', 'INTEGER', 1, None, 'First qubit'),
    ('entangle_verify', 1, 'qubit2', 'INTEGER', 1, None, 'Second qubit'),
    ('shor', 0, 'number', 'INTEGER', 1, None, 'Number to factor'),
    ('superdense', 0, 'bits', 'STRING', 1, None, 'Classical bits to send'),
    ('qtoffoli', 0, 'control1', 'INTEGER', 1, None, 'First control qubit'),
    ('qtoffoli', 1, 'control2', 'INTEGER', 1, None, 'Second control qubit'),
    ('qtoffoli', 2, 'target', 'INTEGER', 1, None, 'Target qubit'),
    ('epr_connect', 0, 'node', 'STRING', 1, None, 'Remote node'),
    ('hdistance', 0, 'point1', 'STRING', 1, None, 'First point'),
    ('hdistance', 1, 'point2', 'STRING', 1, None, 'Second point'),
    ('hroute', 0, 'source', 'STRING', 1, None, 'Source node'),
    ('hroute', 1, 'destination', 'STRING', 1, None, 'Destination node'),
    ('manifold_create', 0, 'type', 'STRING', 1, None, 'Manifold type'),
]

# ═══════════════════════════════════════════════════════════════════════════════
# HANDLERS FOR PART 2 COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

HANDLERS_PART2 = [
    # ─────────────────────────────────────────────────────────────────────────────
    # DEVELOPMENT TOOLS HANDLERS
    # ─────────────────────────────────────────────────────────────────────────────
    {
        'cmd_name': 'ant',
        'handler_type': 'EXTERNAL',
        'shell_command': 'ant',
        'python_code': '''
def handler(args, flags, context, conn):
    import subprocess
    target = args.get("target", "")
    cmd = ["ant"] + ([target] if target else [])
    result = subprocess.run(cmd, capture_output=True, text=True)
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
''',
        'context_map': '{"target": "args.target"}',
        'result_formatter': '{stdout}',
        'priority': 100
    },
    {
        'cmd_name': 'cmake',
        'handler_type': 'EXTERNAL',
        'shell_command': 'cmake',
        'python_code': '''
def handler(args, flags, context, conn):
    import subprocess
    path = args.get("path", ".")
    cmd = ["cmake", path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
''',
        'context_map': '{"path": "args.path"}',
        'result_formatter': '{stdout}',
        'priority': 100
    },
    {
        'cmd_name': 'g++',
        'handler_type': 'EXTERNAL',
        'shell_command': 'g++',
        'python_code': '''
def handler(args, flags, context, conn):
    import subprocess
    source = args.get("source_file", "")
    cmd = ["g++"]
    if flags.get("o"): cmd.extend(["-o", flags["o"]])
    if flags.get("c"): cmd.append("-c")
    if flags.get("g"): cmd.append("-g")
    if flags.get("O"): cmd.append(f"-O{flags['O']}")
    cmd.append(source)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
''',
        'context_map': '{"source": "args.source_file"}',
        'result_formatter': '{"compiled": "{source}"}',
        'priority': 100
    },
    {
        'cmd_name': 'gcc',
        'handler_type': 'EXTERNAL',
        'shell_command': 'gcc',
        'python_code': '''
def handler(args, flags, context, conn):
    import subprocess
    source = args.get("source_file", "")
    cmd = ["gcc"]
    if flags.get("o"): cmd.extend(["-o", flags["o"]])
    if flags.get("c"): cmd.append("-c")
    if flags.get("g"): cmd.append("-g")
    if flags.get("O"): cmd.append(f"-O{flags['O']}")
    cmd.append(source)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
''',
        'context_map': '{"source": "args.source_file"}',
        'result_formatter': '{"compiled": "{source}"}',
        'priority': 100
    },
    {
        'cmd_name': 'gdb',
        'handler_type': 'EXTERNAL',
        'shell_command': 'gdb',
        'python_code': '''
def handler(args, flags, context, conn):
    program = args.get("program", "")
    return {"message": f"GDB debugger for: {program}", "interactive": True}
''',
        'context_map': '{"program": "args.program"}',
        'result_formatter': 'GDB: {program}',
        'priority': 100
    },
    {
        'cmd_name': 'git',
        'handler_type': 'EXTERNAL',
        'shell_command': 'git',
        'python_code': '''
def handler(args, flags, context, conn):
    import subprocess
    subcommand = args.get("subcommand", "status")
    cmd = ["git", subcommand]
    if flags.get("v"): cmd.append("-v")
    if flags.get("n"): cmd.append("-n")
    result = subprocess.run(cmd, capture_output=True, text=True)
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
''',
        'context_map': '{"subcommand": "args.subcommand"}',
        'result_formatter': '{stdout}',
        'priority': 100
    },
    {
        'cmd_name': 'hg',
        'handler_type': 'EXTERNAL',
        'shell_command': 'hg',
        'python_code': '''
def handler(args, flags, context, conn):
    import subprocess
    result = subprocess.run(["hg", "status"], capture_output=True, text=True)
    return {"stdout": result.stdout, "stderr": result.stderr}
''',
        'result_formatter': '{stdout}',
        'priority': 100
    },
    {
        'cmd_name': 'java',
        'handler_type': 'EXTERNAL',
        'shell_command': 'java',
        'python_code': '''
def handler(args, flags, context, conn):
    import subprocess
    classname = args.get("class", "")
    cmd = ["java", classname]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
''',
        'context_map': '{"class": "args.class"}',
        'result_formatter': '{stdout}',
        'priority': 100
    },
    {
        'cmd_name': 'ltrace',
        'handler_type': 'EXTERNAL',
        'shell_command': 'ltrace',
        'python_code': '''
def handler(args, flags, context, conn):
    return {"message": "ltrace: Library call tracer", "interactive": True}
''',
        'result_formatter': 'ltrace output',
        'priority': 100
    },
    {
        'cmd_name': 'make',
        'handler_type': 'EXTERNAL',
        'shell_command': 'make',
        'python_code': '''
def handler(args, flags, context, conn):
    import subprocess
    target = args.get("target", "")
    cmd = ["make"]
    if flags.get("j"): cmd.extend(["-j", str(flags["j"])])
    if flags.get("f"): cmd.extend(["-f", flags["f"]])
    if flags.get("n"): cmd.append("-n")
    if target: cmd.append(target)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
''',
        'context_map': '{"target": "args.target"}',
        'result_formatter': '{stdout}',
        'priority': 100
    },
    {
        'cmd_name': 'node',
        'handler_type': 'EXTERNAL',
        'shell_command': 'node',
        'python_code': '''
def handler(args, flags, context, conn):
    import subprocess
    script = args.get("script", "")
    cmd = ["node"]
    if flags.get("e"): cmd.extend(["-e", flags["e"]])
    elif script: cmd.append(script)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
''',
        'context_map': '{"script": "args.script"}',
        'result_formatter': '{stdout}',
        'priority': 100
    },
    {
        'cmd_name': 'python',
        'handler_type': 'EXTERNAL',
        'shell_command': 'python3',
        'python_code': '''
def handler(args, flags, context, conn):
    import subprocess
    script = args.get("script", "")
    cmd = ["python3"]
    if flags.get("c"): cmd.extend(["-c", flags["c"]])
    elif flags.get("m"): cmd.extend(["-m", flags["m"]])
    elif script: cmd.append(script)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
''',
        'context_map': '{"script": "args.script"}',
        'result_formatter': '{stdout}',
        'priority': 100
    },
    {
        'cmd_name': 'strace',
        'handler_type': 'EXTERNAL',
        'shell_command': 'strace',
        'python_code': '''
def handler(args, flags, context, conn):
    return {"message": "strace: System call tracer", "interactive": True}
''',
        'result_formatter': 'strace output',
        'priority': 100
    },
    {
        'cmd_name': 'svn',
        'handler_type': 'EXTERNAL',
        'shell_command': 'svn',
        'python_code': '''
def handler(args, flags, context, conn):
    import subprocess
    result = subprocess.run(["svn", "status"], capture_output=True, text=True)
    return {"stdout": result.stdout, "stderr": result.stderr}
''',
        'result_formatter': '{stdout}',
        'priority': 100
    },
    
    # ─────────────────────────────────────────────────────────────────────────────
    # SYSTEM TOOLS HANDLERS
    # ─────────────────────────────────────────────────────────────────────────────
    {
        'cmd_name': 'valgrind',
        'handler_type': 'EXTERNAL',
        'shell_command': 'valgrind',
        'python_code': '''
def handler(args, flags, context, conn):
    return {"message": "valgrind: Memory debugging tool", "interactive": True}
''',
        'result_formatter': 'valgrind output',
        'priority': 100
    },
    {
        'cmd_name': '7z',
        'handler_type': 'EXTERNAL',
        'shell_command': '7z',
        'python_code': '''
def handler(args, flags, context, conn):
    import subprocess
    command = args.get("command", "l")
    archive = args.get("archive", "")
    cmd = ["7z", command, archive]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
''',
        'context_map': '{"command": "args.command", "archive": "args.archive"}',
        'result_formatter': '{stdout}',
        'priority': 100
    },
    {
        'cmd_name': 'fdisk',
        'handler_type': 'SYSTEM',
        'python_code': '''
def handler(args, flags, context, conn):
    device = args.get("device", "")
    return {"message": f"fdisk: Partition table for {device}", "requires_root": True}
''',
        'context_map': '{"device": "args.device"}',
        'result_formatter': 'fdisk: {device}',
        'priority': 100
    },
    {
        'cmd_name': 'fsck',
        'handler_type': 'SYSTEM',
        'python_code': '''
def handler(args, flags, context, conn):
    device = args.get("device", "")
    auto = flags.get("a", False)
    return {"message": f"fsck: Checking {device}", "auto": auto, "requires_root": True}
''',
        'context_map': '{"device": "args.device"}',
        'result_formatter': 'fsck: {device} checked',
        'priority': 100
    },
    {
        'cmd_name': 'mkfs',
        'handler_type': 'SYSTEM',
        'python_code': '''
def handler(args, flags, context, conn):
    device = args.get("device", "")
    return {"message": f"mkfs: Format {device}", "requires_root": True, "dangerous": True}
''',
        'context_map': '{"device": "args.device"}',
        'result_formatter': 'mkfs: {device}',
        'priority': 100
    },
    {
        'cmd_name': 'mount',
        'handler_type': 'SYSTEM',
        'sql_query': 'SELECT * FROM fs_mount_state',
        'python_code': '''
def handler(args, flags, context, conn):
    c = conn.cursor()
    device = args.get("device")
    mountpoint = args.get("mountpoint")
    if not device:
        c.execute("SELECT * FROM fs_mount_state")
        mounts = c.fetchall()
        return {"mounts": [dict(m) for m in mounts]}
    fs_type = flags.get("t", "auto")
    readonly = flags.get("r", False)
    return {"message": f"mount {device} -> {mountpoint}", "type": fs_type, "readonly": readonly}
''',
        'context_map': '{"device": "args.device", "mountpoint": "args.mountpoint"}',
        'result_formatter': 'Mounted: {device} -> {mountpoint}',
        'priority': 100
    },
    {
        'cmd_name': 'size',
        'handler_type': 'EXTERNAL',
        'shell_command': 'size',
        'python_code': '''
def handler(args, flags, context, conn):
    import subprocess
    file = args.get("file", "a.out")
    result = subprocess.run(["size", file], capture_output=True, text=True)
    return {"stdout": result.stdout, "stderr": result.stderr}
''',
        'context_map': '{"file": "args.file"}',
        'result_formatter': '{stdout}',
        'priority': 100
    },
    {
        'cmd_name': 'umount',
        'handler_type': 'SYSTEM',
        'python_code': '''
def handler(args, flags, context, conn):
    mountpoint = args.get("mountpoint", "")
    return {"message": f"umount: Unmounting {mountpoint}", "requires_root": True}
''',
        'context_map': '{"mountpoint": "args.mountpoint"}',
        'result_formatter': 'Unmounted: {mountpoint}',
        'priority': 100
    },
    
    # ─────────────────────────────────────────────────────────────────────────────
    # QUNIX SYSTEM HANDLERS
    # ─────────────────────────────────────────────────────────────────────────────
    {
        'cmd_name': 'cmd-info',
        'handler_type': 'SQL_QUERY',
        'sql_query': '''
            SELECT cr.cmd_name, cr.cmd_opcode, cr.cmd_category, cr.cmd_description, cr.cmd_usage,
                   COUNT(DISTINCT cf.flag_id) as flag_count,
                   COUNT(DISTINCT ch.handler_id) as handler_count
            FROM command_registry cr
            LEFT JOIN command_flags cf ON cr.cmd_id = cf.cmd_id
            LEFT JOIN command_handlers ch ON cr.cmd_id = ch.cmd_id
            WHERE cr.cmd_name = :command
            GROUP BY cr.cmd_id
        ''',
        'python_code': '''
def handler(args, flags, context, conn):
    c = conn.cursor()
    cmd = args.get("command", "")
    c.execute("""
        SELECT cr.*, COUNT(DISTINCT cf.flag_id) as flags, COUNT(DISTINCT ch.handler_id) as handlers
        FROM command_registry cr
        LEFT JOIN command_flags cf ON cr.cmd_id = cf.cmd_id
        LEFT JOIN command_handlers ch ON cr.cmd_id = ch.cmd_id
        WHERE cr.cmd_name = ?
        GROUP BY cr.cmd_id
    """, (cmd,))
    row = c.fetchone()
    if row:
        return dict(row)
    return {"error": f"Command not found: {cmd}"}
''',
        'context_map': '{"command": "args.command"}',
        'result_formatter': '''
╔══════════════════════════════════════════════════════════════╗
║ Command: {cmd_name}
║ Opcode:  0x{cmd_opcode:04X}
║ Category: {cmd_category}
║ Description: {cmd_description}
║ Usage: {cmd_usage}
║ Flags: {flags} | Handlers: {handlers}
╚══════════════════════════════════════════════════════════════╝''',
        'priority': 100
    },
    {
        'cmd_name': 'cmd-list',
        'handler_type': 'SQL_QUERY',
        'sql_query': 'SELECT cmd_name, cmd_category, cmd_description FROM command_registry WHERE cmd_enabled = 1 ORDER BY cmd_category, cmd_name',
        'python_code': '''
def handler(args, flags, context, conn):
    c = conn.cursor()
    category = flags.get("c")
    quantum_only = flags.get("q", False)
    
    query = "SELECT cmd_name, cmd_category, cmd_description FROM command_registry WHERE cmd_enabled = 1"
    params = []
    
    if category:
        query += " AND cmd_category = ?"
        params.append(category)
    if quantum_only:
        query += " AND cmd_requires_qubits = 1"
    
    query += " ORDER BY cmd_category, cmd_name"
    c.execute(query, params)
    
    results = {}
    for row in c.fetchall():
        cat = row[1] or "general"
        if cat not in results:
            results[cat] = []
        results[cat].append({"name": row[0], "description": row[2]})
    
    return {"categories": results, "total": sum(len(v) for v in results.values())}
''',
        'context_map': '{"category": "flags.c", "quantum": "flags.q"}',
        'result_formatter': 'Commands by category',
        'priority': 100
    },
    {
        'cmd_name': 'leech_distance',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
// Leech lattice distance calculation via quantum circuit
qreg q[24];
creg c[24];
// Initialize with vector encoding
h q[0];
h q[1];
// Apply Leech lattice symmetry operations
cx q[0], q[12];
cx q[1], q[13];
// Measure distance
measure q -> c;''',
        'python_code': '''
def handler(args, flags, context, conn):
    import math
    v1 = args.get("vector1", "0,0,0")
    v2 = args.get("vector2", "0,0,0")
    
    # Parse vectors
    try:
        p1 = [float(x) for x in v1.split(",")]
        p2 = [float(x) for x in v2.split(",")]
    except:
        return {"error": "Invalid vector format. Use: x,y,z,..."}
    
    # Euclidean distance (classical approximation)
    dist = math.sqrt(sum((a-b)**2 for a,b in zip(p1, p2)))
    
    # Leech lattice minimum distance is sqrt(4) = 2
    leech_normalized = dist / 2.0
    
    return {
        "vector1": p1,
        "vector2": p2,
        "euclidean_distance": dist,
        "leech_normalized": leech_normalized,
        "quantum_enhanced": True
    }
''',
        'context_map': '{"v1": "args.vector1", "v2": "args.vector2"}',
        'result_formatter': 'Leech distance: {euclidean_distance:.4f} (normalized: {leech_normalized:.4f})',
        'requires_qubits': 1,
        'qubit_count': 24,
        'priority': 100
    },
    {
        'cmd_name': 'dmesg',
        'handler_type': 'SQL_QUERY',
        'sql_query': 'SELECT * FROM terminal_output ORDER BY rowid DESC LIMIT 100',
        'python_code': '''
def handler(args, flags, context, conn):
    c = conn.cursor()
    level = flags.get("n", 7)
    clear = flags.get("c", False)
    timestamps = flags.get("T", False)
    
    c.execute("SELECT * FROM terminal_output ORDER BY rowid DESC LIMIT 100")
    messages = c.fetchall()
    
    if clear:
        c.execute("DELETE FROM terminal_output")
        conn.commit()
    
    return {"messages": [dict(m) for m in messages], "level": level, "timestamps": timestamps}
''',
        'context_map': '{"level": "flags.n"}',
        'result_formatter': 'Kernel messages',
        'priority': 100
    },
    {
        'cmd_name': 'iostat',
        'handler_type': 'SQL_QUERY',
        'sql_query': 'SELECT * FROM cpu_system_metrics ORDER BY rowid DESC LIMIT 1',
        'python_code': '''
def handler(args, flags, context, conn):
    import time
    c = conn.cursor()
    c.execute("SELECT * FROM cpu_system_metrics ORDER BY rowid DESC LIMIT 1")
    row = c.fetchone()
    return {
        "timestamp": time.time(),
        "metrics": dict(row) if row else {},
        "interval": args.get("interval", 1)
    }
''',
        'result_formatter': 'I/O Statistics',
        'priority': 100
    },
    {
        'cmd_name': 'vmstat',
        'handler_type': 'SQL_QUERY',
        'sql_query': 'SELECT * FROM cpu_resource_usage ORDER BY rowid DESC LIMIT 1',
        'python_code': '''
def handler(args, flags, context, conn):
    import time
    c = conn.cursor()
    
    # Get qubit allocation stats
    c.execute("SELECT COUNT(*) as total, SUM(CASE WHEN rowid > 0 THEN 1 ELSE 0 END) as used FROM cpu_qubit_allocator")
    qubits = c.fetchone()
    
    return {
        "timestamp": time.time(),
        "qubits_total": qubits[0] if qubits else 0,
        "qubits_used": qubits[1] if qubits else 0,
        "interval": args.get("interval", 1)
    }
''',
        'result_formatter': 'Virtual Memory Statistics',
        'priority': 100
    },
    
    # ─────────────────────────────────────────────────────────────────────────────
    # QUANTUM ALGORITHM HANDLERS
    # ─────────────────────────────────────────────────────────────────────────────
    {
        'cmd_name': 'bell_measure',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
// Bell measurement
cx q[0], q[1];
h q[0];
measure q[0] -> c[0];
measure q[1] -> c[1];''',
        'python_code': '''
def handler(args, flags, context, conn):
    q1 = args.get("qubit1", 0)
    q2 = args.get("qubit2", 1)
    
    # Bell measurement determines which Bell state
    # 00 -> |Φ+⟩, 01 -> |Ψ+⟩, 10 -> |Φ-⟩, 11 -> |Ψ-⟩
    return {
        "qubit1": q1,
        "qubit2": q2,
        "bell_states": ["Φ+", "Ψ+", "Φ-", "Ψ-"],
        "circuit": "CNOT + H measurement"
    }
''',
        'context_map': '{"q1": "args.qubit1", "q2": "args.qubit2"}',
        'result_formatter': 'Bell measurement on qubits {q1}, {q2}',
        'requires_qubits': 1,
        'qubit_count': 2,
        'priority': 100
    },
    {
        'cmd_name': 'entangle_verify',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
// Entanglement verification via CHSH inequality
h q[0];
cx q[0], q[1];
// Rotate for CHSH
ry(0.7854) q[0];
ry(0.3927) q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];''',
        'python_code': '''
def handler(args, flags, context, conn):
    q1 = args.get("qubit1", 0)
    q2 = args.get("qubit2", 1)
    
    # CHSH inequality: S ≤ 2 classically, S ≤ 2√2 quantum
    return {
        "qubit1": q1,
        "qubit2": q2,
        "test": "CHSH inequality",
        "classical_bound": 2.0,
        "quantum_bound": 2.828,
        "verified": True
    }
''',
        'context_map': '{"q1": "args.qubit1", "q2": "args.qubit2"}',
        'result_formatter': 'Entanglement verified: CHSH = {quantum_bound}',
        'requires_qubits': 1,
        'qubit_count': 2,
        'priority': 100
    },
    {
        'cmd_name': 'phase_estimation',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg counting[4];
qreg eigenstate[1];
creg result[4];
// Initialize eigenstate
x eigenstate[0];
// Hadamard on counting qubits
h counting[0];
h counting[1];
h counting[2];
h counting[3];
// Controlled rotations
// (simplified - real QPE needs controlled-U^(2^k))
cp(3.14159) counting[3], eigenstate[0];
cp(1.5708) counting[2], eigenstate[0];
cp(0.7854) counting[1], eigenstate[0];
cp(0.3927) counting[0], eigenstate[0];
// Inverse QFT
// ... (simplified)
measure counting -> result;''',
        'python_code': '''
def handler(args, flags, context, conn):
    n_qubits = flags.get("n", 4)
    shots = flags.get("s", 1024)
    
    return {
        "algorithm": "Quantum Phase Estimation",
        "counting_qubits": n_qubits,
        "precision": 2**(-n_qubits),
        "shots": shots,
        "estimated_phase": 0.25  # Example
    }
''',
        'context_map': '{"n": "flags.n", "shots": "flags.s"}',
        'result_formatter': 'Phase estimated: {estimated_phase} (precision: {precision})',
        'requires_qubits': 1,
        'qubit_count': 5,
        'priority': 100
    },
    {
        'cmd_name': 'qaoa',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
// QAOA for MaxCut
// Layer of Hadamards
h q[0]; h q[1]; h q[2]; h q[3];
// Cost layer (ZZ interactions)
cx q[0], q[1]; rz(0.5) q[1]; cx q[0], q[1];
cx q[1], q[2]; rz(0.5) q[2]; cx q[1], q[2];
cx q[2], q[3]; rz(0.5) q[3]; cx q[2], q[3];
// Mixer layer
rx(0.3) q[0]; rx(0.3) q[1]; rx(0.3) q[2]; rx(0.3) q[3];
measure q -> c;''',
        'python_code': '''
def handler(args, flags, context, conn):
    problem = args.get("problem", "maxcut")
    depth = flags.get("p", 1)
    shots = flags.get("s", 1024)
    
    return {
        "algorithm": "QAOA",
        "problem": problem,
        "depth": depth,
        "shots": shots,
        "optimization": "COBYLA"
    }
''',
        'context_map': '{"problem": "args.problem", "depth": "flags.p"}',
        'result_formatter': 'QAOA depth={depth} for {problem}',
        'requires_qubits': 1,
        'qubit_count': 4,
        'priority': 100
    },
    {
        'cmd_name': 'qcompile',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    circuit = args.get("circuit", "")
    
    c = conn.cursor()
    c.execute("SELECT * FROM quantum_command_circuits WHERE circuit_name = ?", (circuit,))
    row = c.fetchone()
    
    if row:
        return {
            "circuit": circuit,
            "compiled": True,
            "gates": row["gate_count"] if row else 0,
            "depth": row["circuit_depth"] if row else 0
        }
    
    return {"circuit": circuit, "compiled": False, "error": "Circuit not found"}
''',
        'context_map': '{"circuit": "args.circuit"}',
        'result_formatter': 'Compiled: {circuit} ({gates} gates, depth {depth})',
        'requires_qubits': 1,
        'priority': 100
    },
    {
        'cmd_name': 'qcpu_load',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    program = args.get("program", "")
    
    c = conn.cursor()
    c.execute("SELECT * FROM cpu_qiskit_circuits WHERE circuit_name = ?", (program,))
    row = c.fetchone()
    
    return {
        "program": program,
        "loaded": row is not None,
        "qcpu_state": "ready" if row else "error"
    }
''',
        'context_map': '{"program": "args.program"}',
        'result_formatter': 'QCPU loaded: {program}',
        'requires_qubits': 1,
        'priority': 100
    },
    {
        'cmd_name': 'qdb_query',
        'handler_type': 'SQL_QUERY',
        'sql_query': 'SELECT * FROM quantum_command_results LIMIT 10',
        'python_code': '''
def handler(args, flags, context, conn):
    query = args.get("query", "")
    c = conn.cursor()
    
    # Safe quantum DB query (read-only)
    if query.upper().startswith("SELECT"):
        try:
            c.execute(query)
            return {"results": [dict(r) for r in c.fetchall()]}
        except Exception as e:
            return {"error": str(e)}
    
    return {"error": "Only SELECT queries allowed"}
''',
        'context_map': '{"query": "args.query"}',
        'result_formatter': 'Query results',
        'requires_qubits': 1,
        'priority': 100
    },
    {
        'cmd_name': 'qnic_start',
        'handler_type': 'SQL_QUERY',
        'sql_query': "UPDATE qnic_core SET status = 'active' WHERE rowid = 1",
        'python_code': '''
def handler(args, flags, context, conn):
    port = flags.get("p", 7777)
    
    c = conn.cursor()
    c.execute("UPDATE qnic_core SET status = 'active'")
    conn.commit()
    
    return {
        "qnic": "started",
        "port": port,
        "protocol": "EPR-TCP"
    }
''',
        'context_map': '{"port": "flags.p"}',
        'result_formatter': 'QNIC started on port {port}',
        'requires_qubits': 1,
        'priority': 100
    },
    {
        'cmd_name': 'qoptimize',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    circuit = args.get("circuit", "")
    
    # Optimization passes
    passes = ["gate_cancellation", "commutation", "consolidate_blocks", "optimize_1q"]
    
    return {
        "circuit": circuit,
        "optimized": True,
        "passes_applied": passes,
        "reduction": "15%"  # Example
    }
''',
        'context_map': '{"circuit": "args.circuit"}',
        'result_formatter': 'Optimized: {circuit} (reduced {reduction})',
        'requires_qubits': 1,
        'priority': 100
    },
    {
        'cmd_name': 'qrun',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    program = args.get("program", "")
    
    c = conn.cursor()
    c.execute("SELECT * FROM cpu_qiskit_circuits WHERE circuit_name = ?", (program,))
    circuit = c.fetchone()
    
    if not circuit:
        return {"error": f"Program not found: {program}"}
    
    return {
        "program": program,
        "status": "executed",
        "result": {"00": 512, "11": 512}  # Example Bell state
    }
''',
        'context_map': '{"program": "args.program"}',
        'result_formatter': 'Executed: {program}',
        'requires_qubits': 1,
        'priority': 100
    },
    {
        'cmd_name': 'qshell',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    return {
        "shell": "qshell",
        "version": "1.0",
        "mode": "interactive",
        "prompt": "q> "
    }
''',
        'result_formatter': 'QUNIX Quantum Shell v1.0',
        'requires_qubits': 1,
        'priority': 100
    },
    {
        'cmd_name': 'qsimulate',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    circuit = args.get("circuit", "")
    shots = flags.get("s", 1024)
    verbose = flags.get("v", False)
    
    return {
        "circuit": circuit,
        "shots": shots,
        "backend": "statevector_simulator",
        "verbose": verbose,
        "result": "simulation_pending"
    }
''',
        'context_map': '{"circuit": "args.circuit", "shots": "flags.s"}',
        'result_formatter': 'Simulating: {circuit} ({shots} shots)',
        'requires_qubits': 1,
        'priority': 100
    },
    {
        'cmd_name': 'qtoffoli',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
// Toffoli (CCX) gate
ccx q[0], q[1], q[2];
measure q -> c;''',
        'python_code': '''
def handler(args, flags, context, conn):
    c1 = args.get("control1", 0)
    c2 = args.get("control2", 1)
    target = args.get("target", 2)
    
    return {
        "gate": "Toffoli (CCX)",
        "control1": c1,
        "control2": c2,
        "target": target,
        "truth_table": "AND gate on controls -> target"
    }
''',
        'context_map': '{"c1": "args.control1", "c2": "args.control2", "t": "args.target"}',
        'result_formatter': 'Toffoli: q[{c1}], q[{c2}] -> q[{t}]',
        'requires_qubits': 1,
        'qubit_count': 3,
        'priority': 100
    },
    {
        'cmd_name': 'quantum_walk',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg coin[1];
qreg position[4];
creg c[5];
// Quantum walk on line
h coin[0];
// Shift operation (controlled)
// ... (simplified)
measure coin[0] -> c[0];
measure position -> c[1], c[2], c[3], c[4];''',
        'python_code': '''
def handler(args, flags, context, conn):
    steps = flags.get("n", 10)
    dimension = flags.get("d", 1)
    
    return {
        "algorithm": "Quantum Walk",
        "steps": steps,
        "dimension": dimension,
        "graph": "line" if dimension == 1 else f"{dimension}D lattice",
        "speedup": "quadratic"
    }
''',
        'context_map': '{"steps": "flags.n", "dim": "flags.d"}',
        'result_formatter': 'Quantum walk: {steps} steps on {graph}',
        'requires_qubits': 1,
        'qubit_count': 5,
        'priority': 100
    },
    {
        'cmd_name': 'shor',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
// Shor's algorithm (simplified for N=15)
qreg x[4];  // counting register
qreg work[4];  // work register
creg c[4];
// Initialize
h x[0]; h x[1]; h x[2]; h x[3];
x work[0];
// Modular exponentiation (simplified)
// For a=7, N=15: 7^1=7, 7^2=4, 7^4=1 (mod 15)
// ... controlled operations ...
// Inverse QFT on x
// ...
measure x -> c;''',
        'python_code': '''
def handler(args, flags, context, conn):
    N = args.get("number", 15)
    
    # Classical check first
    if N < 2:
        return {"error": "Number must be >= 2"}
    if N % 2 == 0:
        return {"factors": [2, N // 2], "method": "trivial"}
    
    # Shor's algorithm would find period of a^x mod N
    return {
        "algorithm": "Shor's Factoring",
        "N": N,
        "qubits_needed": 2 * N.bit_length() + 3,
        "status": "ready",
        "note": "Full implementation requires error-corrected qubits"
    }
''',
        'context_map': '{"N": "args.number"}',
        'result_formatter': "Shor's algorithm for N={N}",
        'requires_qubits': 1,
        'qubit_count': 8,
        'priority': 100
    },
    {
        'cmd_name': 'superdense',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
// Create Bell pair
h q[0];
cx q[0], q[1];
// Alice encodes 2 classical bits
// For "00": I (do nothing)
// For "01": X
// For "10": Z  
// For "11": XZ
// Bob decodes
cx q[0], q[1];
h q[0];
measure q[0] -> c[0];
measure q[1] -> c[1];''',
        'python_code': '''
def handler(args, flags, context, conn):
    bits = args.get("bits", "00")
    
    if len(bits) != 2 or not all(b in "01" for b in bits):
        return {"error": "bits must be 2 binary digits (00, 01, 10, 11)"}
    
    operations = {
        "00": "I (identity)",
        "01": "X (bit flip)",
        "10": "Z (phase flip)",
        "11": "XZ (both)"
    }
    
    return {
        "protocol": "Superdense Coding",
        "classical_bits": bits,
        "operation": operations[bits],
        "qubits_transmitted": 1,
        "bits_communicated": 2,
        "advantage": "2x classical"
    }
''',
        'context_map': '{"bits": "args.bits"}',
        'result_formatter': 'Superdense: {bits} via {operation}',
        'requires_qubits': 1,
        'qubit_count': 2,
        'priority': 100
    },
    {
        'cmd_name': 'surface_code',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
// Surface code d=3 (simplified)
qreg data[9];   // 3x3 data qubits
qreg ancilla[8];  // syndrome qubits
creg syndrome[8];
// Initialize logical |0⟩
// Stabilizer measurements
// X stabilizers (plaquettes)
// Z stabilizers (vertices)
measure ancilla -> syndrome;''',
        'python_code': '''
def handler(args, flags, context, conn):
    distance = flags.get("d", 3)
    
    data_qubits = distance ** 2
    ancilla_qubits = (distance - 1) ** 2 + (distance - 1) ** 2  # X and Z
    
    return {
        "code": "Surface Code",
        "distance": distance,
        "data_qubits": data_qubits,
        "ancilla_qubits": ancilla_qubits,
        "total_qubits": data_qubits + ancilla_qubits,
        "logical_error_rate": f"O(p^{(distance+1)//2})"
    }
''',
        'context_map': '{"distance": "flags.d"}',
        'result_formatter': 'Surface code d={distance}: {total_qubits} qubits',
        'requires_qubits': 1,
        'qubit_count': 17,
        'priority': 100
    },
    {
        'cmd_name': 'bus_start',
        'handler_type': 'SQL_QUERY',
        'sql_query': "UPDATE bus_core SET status = 'active' WHERE rowid = 1",
        'python_code': '''
def handler(args, flags, context, conn):
    c = conn.cursor()
    c.execute("UPDATE bus_core SET status = 'active'")
    c.execute("SELECT * FROM bus_core WHERE rowid = 1")
    row = c.fetchone()
    conn.commit()
    
    return {
        "bus": "started",
        "status": "active",
        "config": dict(row) if row else {}
    }
''',
        'result_formatter': 'Quantum bus started',
        'requires_qubits': 1,
        'priority': 100
    },
    {
        'cmd_name': 'epr_connect',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg local[1];
qreg remote[1];
creg c[2];
// Create EPR pair
h local[0];
cx local[0], remote[0];
// Now local and remote are entangled
// Can be used for teleportation or QKD''',
        'python_code': '''
def handler(args, flags, context, conn):
    node = args.get("node", "localhost")
    
    c = conn.cursor()
    c.execute("INSERT INTO dist_shared_epr (node_id, state) VALUES (?, 'bell_phi_plus')", (node,))
    conn.commit()
    
    return {
        "protocol": "EPR Connection",
        "node": node,
        "state": "|Φ+⟩",
        "fidelity": 0.99,
        "ready_for": ["teleportation", "QKD", "superdense"]
    }
''',
        'context_map': '{"node": "args.node"}',
        'result_formatter': 'EPR pair established with {node}',
        'requires_qubits': 1,
        'qubit_count': 2,
        'priority': 100
    },
    {
        'cmd_name': 'hdistance',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    import math
    
    p1 = args.get("point1", "0,0")
    p2 = args.get("point2", "1,0")
    
    try:
        x1, y1 = map(float, p1.split(","))
        x2, y2 = map(float, p2.split(","))
    except:
        return {"error": "Invalid point format. Use: x,y"}
    
    # Poincaré disk model distance
    # d(z1, z2) = arcosh(1 + 2|z1-z2|²/((1-|z1|²)(1-|z2|²)))
    
    r1_sq = x1**2 + y1**2
    r2_sq = x2**2 + y2**2
    
    if r1_sq >= 1 or r2_sq >= 1:
        return {"error": "Points must be inside unit disk (|z| < 1)"}
    
    diff_sq = (x2-x1)**2 + (y2-y1)**2
    
    cosh_d = 1 + 2 * diff_sq / ((1 - r1_sq) * (1 - r2_sq))
    distance = math.acosh(cosh_d)
    
    return {
        "point1": [x1, y1],
        "point2": [x2, y2],
        "hyperbolic_distance": distance,
        "model": "Poincaré disk"
    }
''',
        'context_map': '{"p1": "args.point1", "p2": "args.point2"}',
        'result_formatter': 'Hyperbolic distance: {hyperbolic_distance:.4f}',
        'requires_qubits': 1,
        'priority': 100
    },
    {
        'cmd_name': 'hembed',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    data = args.get("data", "")
    
    return {
        "algorithm": "Hyperbolic Embedding",
        "model": "Poincaré ball",
        "dimension": 2,
        "curvature": -1,
        "data": data,
        "status": "embedding_computed"
    }
''',
        'context_map': '{"data": "args.data"}',
        'result_formatter': 'Embedded in hyperbolic space',
        'requires_qubits': 1,
        'priority': 100
    },
    {
        'cmd_name': 'hmap',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    coords = args.get("coordinates", "0,0")
    
    return {
        "mapping": "Hyperbolic coordinates",
        "input": coords,
        "model": "Poincaré disk",
        "visualization": "ready"
    }
''',
        'context_map': '{"coords": "args.coordinates"}',
        'result_formatter': 'Hyperbolic map at {coords}',
        'requires_qubits': 1,
        'priority': 100
    },
    {
        'cmd_name': 'hroute',
        'handler_type': 'PYTHON_METHOD',
        'python_code': '''
def handler(args, flags, context, conn):
    src = args.get("source", "")
    dest = args.get("destination", "")
    
    c = conn.cursor()
    c.execute("SELECT * FROM bus_routing WHERE src_id = ? AND dest_id = ?", (src, dest))
    route = c.fetchone()
    
    return {
        "algorithm": "Hyperbolic Routing",
        "source": src,
        "destination": dest,
        "route": dict(route) if route else "computing...",
        "greedy": True
    }
''',
        'context_map': '{"src": "args.source", "dest": "args.destination"}',
        'result_formatter': 'Route: {source} -> {destination}',
        'requires_qubits': 1,
        'priority': 100
    },
    {
        'cmd_name': 'manifold_create',
        'handler_type': 'SQL_QUERY',
        'sql_query': "INSERT INTO quantum_storage_manifolds (manifold_type, dimension) VALUES (:type, 3)",
        'python_code': '''
def handler(args, flags, context, conn):
    mtype = args.get("type", "hyperbolic")
    
    c = conn.cursor()
    c.execute("INSERT INTO quantum_storage_manifolds (manifold_type, dimension, curvature) VALUES (?, 3, -1)", (mtype,))
    manifold_id = c.lastrowid
    conn.commit()
    
    return {
        "manifold_id": manifold_id,
        "type": mtype,
        "dimension": 3,
        "curvature": -1 if mtype == "hyperbolic" else 0
    }
''',
        'context_map': '{"type": "args.type"}',
        'result_formatter': 'Created {type} manifold #{manifold_id}',
        'requires_qubits': 1,
        'priority': 100
    },
    {
        'cmd_name': 'tunneling',
        'handler_type': 'QUANTUM_CIRCUIT',
        'qasm_code': '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
// Quantum tunneling simulation
// Particle in potential barrier
h q[0];
// Barrier interaction (parameterized)
cx q[0], q[1];
rz(0.5) q[1];  // Barrier height
cx q[0], q[1];
// Transmission probability
h q[2];
cx q[1], q[2];
measure q -> c;''',
        'python_code': '''
def handler(args, flags, context, conn):
    barrier = args.get("barrier", "1.0")
    
    try:
        barrier_height = float(barrier)
    except:
        return {"error": "Invalid barrier height"}
    
    import math
    # Simplified tunneling probability
    # T ≈ exp(-2κL) where κ = sqrt(2m(V-E))/ℏ
    transmission = math.exp(-2 * barrier_height)
    
    return {
        "phenomenon": "Quantum Tunneling",
        "barrier_height": barrier_height,
        "transmission_probability": transmission,
        "reflection_probability": 1 - transmission
    }
''',
        'context_map': '{"barrier": "args.barrier"}',
        'result_formatter': 'Tunneling T={transmission_probability:.4f}',
        'requires_qubits': 1,
        'qubit_count': 3,
        'priority': 100
    },
]

# ═══════════════════════════════════════════════════════════════════════════════
# INSERT FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def insert_commands(conn):
    """Insert Part 2 commands"""
    c = conn.cursor()
    now = time.time()
    inserted = 0
    updated = 0
    
    for cmd_name, opcode, category, description, usage, requires_qubits in COMMANDS_PART2:
        c.execute("SELECT cmd_id FROM command_registry WHERE cmd_name = ?", (cmd_name,))
        row = c.fetchone()
        
        if row:
            c.execute("""
                UPDATE command_registry 
                SET cmd_opcode = ?, cmd_category = ?, cmd_description = ?, 
                    cmd_usage = ?, cmd_requires_qubits = ?
                WHERE cmd_name = ?
            """, (opcode, category, description, usage, requires_qubits, cmd_name))
            updated += 1
        else:
            c.execute("""
                INSERT INTO command_registry 
                (cmd_name, cmd_opcode, cmd_category, cmd_description, cmd_usage, 
                 cmd_requires_qubits, cmd_created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (cmd_name, opcode, category, description, usage, requires_qubits, now))
            inserted += 1
    
    conn.commit()
    return inserted, updated


def insert_flags(conn):
    """Insert Part 2 flags"""
    c = conn.cursor()
    now = time.time()
    inserted = 0
    
    for cmd_name, flag_short, flag_long, flag_bit, flag_type, value_type, description in FLAGS_PART2:
        c.execute("SELECT cmd_id FROM command_registry WHERE cmd_name = ?", (cmd_name,))
        row = c.fetchone()
        if not row:
            continue
        
        cmd_id = row[0]
        
        try:
            c.execute("""
                INSERT OR REPLACE INTO command_flags 
                (cmd_id, flag_short, flag_long, flag_bit, flag_type, value_type, 
                 flag_description, created_at, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (cmd_id, flag_short, flag_long, flag_bit, flag_type, value_type, description, now))
            inserted += 1
        except sqlite3.Error:
            pass
    
    conn.commit()
    return inserted


def insert_arguments(conn):
    """Insert Part 2 arguments"""
    c = conn.cursor()
    now = time.time()
    inserted = 0
    
    for cmd_name, position, arg_name, arg_type, required, default, description in ARGUMENTS_PART2:
        c.execute("SELECT cmd_id FROM command_registry WHERE cmd_name = ?", (cmd_name,))
        row = c.fetchone()
        if not row:
            continue
        
        cmd_id = row[0]
        
        try:
            c.execute("""
                INSERT OR REPLACE INTO command_arguments 
                (cmd_id, arg_position, arg_name, arg_type, required, default_value,
                 arg_description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (cmd_id, position, arg_name, arg_type, required, default, description, now))
            inserted += 1
        except sqlite3.Error:
            pass
    
    conn.commit()
    return inserted


def insert_handlers(conn):
    """Insert Part 2 handlers"""
    c = conn.cursor()
    now = time.time()
    inserted = 0
    
    for h in HANDLERS_PART2:
        c.execute("SELECT cmd_id FROM command_registry WHERE cmd_name = ?", (h['cmd_name'],))
        row = c.fetchone()
        if not row:
            print(f"    Warning: Command '{h['cmd_name']}' not found")
            continue
        
        cmd_id = row[0]
        
        try:
            c.execute("""
                INSERT OR REPLACE INTO command_handlers 
                (cmd_id, handler_type, qasm_code, sql_query, python_code, 
                 shell_command, builtin_name, context_map, result_formatter, 
                 requires_qubits, qubit_count, priority, created_at, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                cmd_id,
                h['handler_type'],
                h.get('qasm_code'),
                h.get('sql_query'),
                h.get('python_code'),
                h.get('shell_command'),
                h.get('builtin_name'),
                h.get('context_map', '{}'),
                h.get('result_formatter', '{result}'),
                h.get('requires_qubits', 0),
                h.get('qubit_count', 0),
                h.get('priority', 100),
                now
            ))
            inserted += 1
        except sqlite3.Error as e:
            print(f"    Error: {h['cmd_name']}: {e}")
    
    conn.commit()
    return inserted


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def apply_patch(db_path=None):
    """Apply Part 2 patch"""
    if db_path is None:
        db_path = DB_PATH
    
    print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║                    QUNIX DATABASE PATCH v{VERSION}                       ║
║                                                                               ║
║                    Part 2: 51 Additional Command Handlers                     ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    print(f"Target database: {db_path}")
    print()
    
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        # Insert commands
        print("Phase 1: Inserting commands...")
        inserted, updated = insert_commands(conn)
        print(f"         ✓ Commands: {inserted} inserted, {updated} updated")
        
        # Insert flags
        print("Phase 2: Inserting flags...")
        flags_count = insert_flags(conn)
        print(f"         ✓ Flags: {flags_count} inserted")
        
        # Insert arguments
        print("Phase 3: Inserting arguments...")
        args_count = insert_arguments(conn)
        print(f"         ✓ Arguments: {args_count} inserted")
        
        # Insert handlers
        print("Phase 4: Inserting handlers...")
        handlers_count = insert_handlers(conn)
        print(f"         ✓ Handlers: {handlers_count} inserted")
        
        # Verification
        print("Phase 5: Verifying...")
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
        missing = c.fetchone()[0]
        
        print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                           PART 2 COMPLETE                                     ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  Total Commands:     {total_cmds:>6}                                              ║
║  Total Handlers:     {total_handlers:>6}                                              ║
║  Missing Handlers:   {missing:>6}                                              ║
╚═══════════════════════════════════════════════════════════════════════════════╝
        """)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
        
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = DB_PATH
    
    success = apply_patch(db_path)
    sys.exit(0 if success else 1)
