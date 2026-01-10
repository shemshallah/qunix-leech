#!/usr/bin/env python3
"""
QUNIX DATABASE PATCH v8.0.0 - PART 3
Final 51 Command Handlers

Run AFTER fix_all_tables.py, Part 1 and Part 2
"""

import sqlite3
import time
import sys
import os

VERSION = "8.0.0-PART3"
DB_PATH = "/data/data/com.termux/files/home/qunix_leech.db"

# 51 COMMANDS
COMMANDS = [
    # ARCHIVE (10)
    ('bunzip2', 0x6000, 'archive', 'Decompress bzip2', 'bunzip2 file.bz2', 0),
    ('bzip2', 0x6001, 'archive', 'Compress bzip2', 'bzip2 [-k] file', 0),
    ('gunzip', 0x6002, 'archive', 'Decompress gzip', 'gunzip file.gz', 0),
    ('gzip', 0x6003, 'archive', 'Compress gzip', 'gzip [-k] file', 0),
    ('tar', 0x6004, 'archive', 'Tape archive', 'tar [-xvf|-cvf] archive', 0),
    ('unxz', 0x6005, 'archive', 'Decompress xz', 'unxz file.xz', 0),
    ('unzip', 0x6006, 'archive', 'Extract ZIP', 'unzip archive.zip', 0),
    ('xz', 0x6007, 'archive', 'Compress xz', 'xz [-k] file', 0),
    ('zcat', 0x6008, 'archive', 'View compressed', 'zcat file.gz', 0),
    ('zip', 0x6009, 'archive', 'Create ZIP', 'zip archive.zip files', 0),
    # BUILTIN (11)
    ('alias', 0x6010, 'builtin', 'Create alias', 'alias name=cmd', 0),
    ('apropos', 0x6011, 'builtin', 'Search manpages', 'apropos keyword', 0),
    ('eval', 0x6012, 'builtin', 'Evaluate args', 'eval command', 0),
    ('exec', 0x6013, 'builtin', 'Execute command', 'exec command', 0),
    ('info', 0x6014, 'builtin', 'Info documents', 'info [topic]', 0),
    ('logout', 0x6015, 'builtin', 'Exit shell', 'logout', 0),
    ('printf', 0x6016, 'builtin', 'Format print', 'printf fmt [args]', 0),
    ('reset', 0x6017, 'builtin', 'Reset terminal', 'reset', 0),
    ('set', 0x6018, 'builtin', 'Shell options', 'set [options]', 0),
    ('source', 0x6019, 'builtin', 'Source file', 'source file', 0),
    ('unalias', 0x601A, 'builtin', 'Remove alias', 'unalias name', 0),
    # FILESYSTEM (8)
    ('chgrp', 0x6020, 'filesystem', 'Change group', 'chgrp group file', 0),
    ('chmod', 0x6021, 'filesystem', 'Change perms', 'chmod mode file', 0),
    ('chown', 0x6022, 'filesystem', 'Change owner', 'chown owner file', 0),
    ('cp', 0x6023, 'filesystem', 'Copy files', 'cp [-r] src dest', 0),
    ('du', 0x6024, 'filesystem', 'Disk usage', 'du [-h] [path]', 0),
    ('ln', 0x6025, 'filesystem', 'Create links', 'ln [-s] target link', 0),
    ('mv', 0x6026, 'filesystem', 'Move files', 'mv src dest', 0),
    ('umask', 0x6027, 'filesystem', 'File mask', 'umask [mode]', 0),
    # UTILITY (9)
    ('bc', 0x6030, 'utility', 'Calculator', 'bc [-l]', 0),
    ('cal', 0x6031, 'utility', 'Calendar', 'cal [month] [year]', 0),
    ('expr', 0x6032, 'utility', 'Evaluate expr', 'expr expression', 0),
    ('false', 0x6033, 'utility', 'Return false', 'false', 0),
    ('locate', 0x6034, 'utility', 'Find files', 'locate pattern', 0),
    ('sleep', 0x6035, 'utility', 'Delay', 'sleep seconds', 0),
    ('test', 0x6036, 'utility', 'Test expr', 'test expression', 0),
    ('true', 0x6037, 'utility', 'Return true', 'true', 0),
    ('yes', 0x6038, 'utility', 'Output string', 'yes [string]', 0),
    # NETWORK (10)
    ('curl', 0x6040, 'network', 'Transfer URL', 'curl [opts] URL', 0),
    ('dig', 0x6041, 'network', 'DNS lookup', 'dig [domain]', 0),
    ('ifconfig', 0x6042, 'network', 'Network config', 'ifconfig [iface]', 0),
    ('ip', 0x6043, 'network', 'IP config', 'ip [object] [cmd]', 0),
    ('netstat', 0x6044, 'network', 'Net stats', 'netstat [-an]', 0),
    ('ping', 0x6045, 'network', 'ICMP echo', 'ping host', 0),
    ('ss', 0x6046, 'network', 'Socket stats', 'ss [-tuln]', 0),
    ('ssh', 0x6047, 'network', 'Secure shell', 'ssh [user@]host', 0),
    ('traceroute', 0x6048, 'network', 'Trace route', 'traceroute host', 0),
    ('wget', 0x6049, 'network', 'Download', 'wget URL', 0),
    # PROCESS (8)
    ('bg', 0x6050, 'process', 'Background', 'bg [job]', 0),
    ('fg', 0x6051, 'process', 'Foreground', 'fg [job]', 0),
    ('jobs', 0x6052, 'process', 'List jobs', 'jobs [-l]', 0),
    ('kill', 0x6053, 'process', 'Send signal', 'kill [-sig] pid', 0),
    ('killall', 0x6054, 'process', 'Kill by name', 'killall name', 0),
    ('nice', 0x6055, 'process', 'Run priority', 'nice [-n] cmd', 0),
    ('renice', 0x6056, 'process', 'Alter priority', 'renice pri pid', 0),
    ('top', 0x6057, 'process', 'Process view', 'top', 0),
    # TEXT (8)
    ('awk', 0x6060, 'text', 'Pattern scan', 'awk pattern file', 0),
    ('cut', 0x6061, 'text', 'Cut sections', 'cut -d: -f1 file', 0),
    ('diff', 0x6062, 'text', 'Compare files', 'diff file1 file2', 0),
    ('paste', 0x6063, 'text', 'Merge lines', 'paste f1 f2', 0),
    ('sed', 0x6064, 'text', 'Stream edit', 'sed s/old/new/ file', 0),
    ('sort', 0x6065, 'text', 'Sort lines', 'sort [-r] file', 0),
    ('tr', 0x6066, 'text', 'Translate', 'tr set1 set2', 0),
    ('uniq', 0x6067, 'text', 'Unique lines', 'uniq [-c] file', 0),
    # QUANTUM GATES (9)
    ('qbarrier', 0x6070, 'quantum', 'Barrier', 'qbarrier [qubits]', 1),
    ('qccnot', 0x6071, 'quantum', 'CCX gate', 'qccnot c1 c2 t', 1),
    ('qcswap', 0x6072, 'quantum', 'CSWAP', 'qcswap c q1 q2', 1),
    ('qiswap', 0x6073, 'quantum', 'iSWAP', 'qiswap q1 q2', 1),
    ('qphase', 0x6074, 'quantum', 'Phase gate', 'qphase angle q', 1),
    ('qrx', 0x6075, 'quantum', 'RX gate', 'qrx angle q', 1),
    ('qry', 0x6076, 'quantum', 'RY gate', 'qry angle q', 1),
    ('qrz', 0x6077, 'quantum', 'RZ gate', 'qrz angle q', 1),
    ('grover', 0x6078, 'quantum', 'Grover search', 'grover [-n] target', 1),
    # QUANTUM OPS (9)
    ('entangle', 0x6080, 'quantum', 'Entangle', 'entangle q1 q2', 1),
    ('iqft', 0x6081, 'quantum', 'Inverse QFT', 'iqft [qubits]', 1),
    ('qft', 0x6082, 'quantum', 'QFT', 'qft [qubits]', 1),
    ('qinit', 0x6083, 'quantum', 'Init qubit', 'qinit q [state]', 1),
    ('qstate', 0x6084, 'quantum', 'Qubit state', 'qstate [q]', 1),
    ('teleport', 0x6085, 'quantum', 'Teleportation', 'teleport src dest', 1),
    ('vqe', 0x6086, 'quantum', 'VQE', 'vqe [hamiltonian]', 1),
    ('epr_pair', 0x6087, 'quantum', 'EPR pair', 'epr_pair q1 q2', 1),
    ('circuit_run', 0x6088, 'quantum', 'Run circuit', 'circuit_run [c]', 1),
    # LATTICE (8)
    ('golay_encode', 0x6090, 'quantum', 'Golay encode', 'golay_encode data', 1),
    ('golay_decode', 0x6091, 'quantum', 'Golay decode', 'golay_decode cw', 1),
    ('leech_encode', 0x6092, 'quantum', 'Leech encode', 'leech_encode vec', 1),
    ('leech_decode', 0x6093, 'quantum', 'Leech decode', 'leech_decode pt', 1),
    ('lattice_point', 0x6094, 'quantum', 'Nearest point', 'lattice_point v', 1),
    ('e8_split', 0x6095, 'quantum', 'E8 decomp', 'e8_split vector', 1),
    ('moonshine', 0x6096, 'quantum', 'Moonshine', 'moonshine [j]', 1),
    ('triangle', 0x6097, 'quantum', 'Triangle grp', 'triangle [p,q,r]', 1),
]

# FLAGS
FLAGS = [
    ('gzip','k','keep',0,'BOOLEAN',None,'Keep original'),
    ('gzip','d','decompress',1,'BOOLEAN',None,'Decompress'),
    ('bzip2','k','keep',0,'BOOLEAN',None,'Keep original'),
    ('xz','k','keep',0,'BOOLEAN',None,'Keep original'),
    ('tar','x','extract',0,'BOOLEAN',None,'Extract'),
    ('tar','c','create',1,'BOOLEAN',None,'Create'),
    ('tar','v','verbose',2,'BOOLEAN',None,'Verbose'),
    ('tar','f','file',3,'VALUE','STRING','Archive'),
    ('tar','z','gzip',4,'BOOLEAN',None,'Gzip'),
    ('zip','r','recursive',0,'BOOLEAN',None,'Recursive'),
    ('unzip','l','list',0,'BOOLEAN',None,'List'),
    ('cp','r','recursive',0,'BOOLEAN',None,'Recursive'),
    ('cp','v','verbose',1,'BOOLEAN',None,'Verbose'),
    ('mv','v','verbose',0,'BOOLEAN',None,'Verbose'),
    ('ln','s','symbolic',0,'BOOLEAN',None,'Symbolic'),
    ('chmod','R','recursive',0,'BOOLEAN',None,'Recursive'),
    ('chown','R','recursive',0,'BOOLEAN',None,'Recursive'),
    ('du','h','human',0,'BOOLEAN',None,'Human'),
    ('du','s','summarize',1,'BOOLEAN',None,'Summarize'),
    ('bc','l','mathlib',0,'BOOLEAN',None,'Math lib'),
    ('sort','r','reverse',0,'BOOLEAN',None,'Reverse'),
    ('sort','n','numeric',1,'BOOLEAN',None,'Numeric'),
    ('uniq','c','count',0,'BOOLEAN',None,'Count'),
    ('curl','o','output',0,'VALUE','STRING','Output'),
    ('curl','X','request',1,'VALUE','STRING','Method'),
    ('wget','O','output',0,'VALUE','STRING','Output'),
    ('wget','q','quiet',1,'BOOLEAN',None,'Quiet'),
    ('ping','c','count',0,'VALUE','INTEGER','Count'),
    ('netstat','a','all',0,'BOOLEAN',None,'All'),
    ('netstat','n','numeric',1,'BOOLEAN',None,'Numeric'),
    ('ss','t','tcp',0,'BOOLEAN',None,'TCP'),
    ('ss','u','udp',1,'BOOLEAN',None,'UDP'),
    ('ss','l','listening',2,'BOOLEAN',None,'Listening'),
    ('jobs','l','long',0,'BOOLEAN',None,'Long'),
    ('kill','s','signal',0,'VALUE','STRING','Signal'),
    ('nice','n','adjustment',0,'VALUE','INTEGER','Priority'),
    ('cut','d','delimiter',0,'VALUE','STRING','Delimiter'),
    ('cut','f','fields',1,'VALUE','STRING','Fields'),
    ('awk','F','separator',0,'VALUE','STRING','Separator'),
    ('sed','i','in-place',0,'BOOLEAN',None,'In-place'),
    ('diff','u','unified',0,'BOOLEAN',None,'Unified'),
    ('tr','d','delete',0,'BOOLEAN',None,'Delete'),
    ('grover','n','qubits',0,'VALUE','INTEGER','Qubits'),
    ('grover','i','iterations',1,'VALUE','INTEGER','Iterations'),
    ('qft','n','qubits',0,'VALUE','INTEGER','Qubits'),
    ('iqft','n','qubits',0,'VALUE','INTEGER','Qubits'),
    ('vqe','d','depth',0,'VALUE','INTEGER','Depth'),
    ('qrx','a','angle',0,'VALUE','FLOAT','Angle'),
    ('qry','a','angle',0,'VALUE','FLOAT','Angle'),
    ('qrz','a','angle',0,'VALUE','FLOAT','Angle'),
    ('qphase','a','angle',0,'VALUE','FLOAT','Angle'),
]

# ARGUMENTS
ARGUMENTS = [
    ('gzip',0,'file','PATH',1,None,'File'),
    ('gunzip',0,'file','PATH',1,None,'File'),
    ('bzip2',0,'file','PATH',1,None,'File'),
    ('bunzip2',0,'file','PATH',1,None,'File'),
    ('xz',0,'file','PATH',1,None,'File'),
    ('unxz',0,'file','PATH',1,None,'File'),
    ('tar',0,'archive','PATH',1,None,'Archive'),
    ('zip',0,'archive','PATH',1,None,'Archive'),
    ('zip',1,'files','PATH',1,None,'Files'),
    ('unzip',0,'archive','PATH',1,None,'Archive'),
    ('zcat',0,'file','PATH',1,None,'File'),
    ('alias',0,'definition','STRING',0,None,'Definition'),
    ('apropos',0,'keyword','STRING',1,None,'Keyword'),
    ('eval',0,'command','STRING',1,None,'Command'),
    ('exec',0,'command','STRING',1,None,'Command'),
    ('info',0,'topic','STRING',0,None,'Topic'),
    ('printf',0,'format','STRING',1,None,'Format'),
    ('source',0,'file','PATH',1,None,'File'),
    ('unalias',0,'name','STRING',1,None,'Name'),
    ('chmod',0,'mode','STRING',1,None,'Mode'),
    ('chmod',1,'file','PATH',1,None,'File'),
    ('chown',0,'owner','STRING',1,None,'Owner'),
    ('chown',1,'file','PATH',1,None,'File'),
    ('chgrp',0,'group','STRING',1,None,'Group'),
    ('chgrp',1,'file','PATH',1,None,'File'),
    ('cp',0,'source','PATH',1,None,'Source'),
    ('cp',1,'dest','PATH',1,None,'Dest'),
    ('mv',0,'source','PATH',1,None,'Source'),
    ('mv',1,'dest','PATH',1,None,'Dest'),
    ('ln',0,'target','PATH',1,None,'Target'),
    ('ln',1,'link','PATH',1,None,'Link'),
    ('du',0,'path','PATH',0,'.','Path'),
    ('umask',0,'mode','STRING',0,None,'Mode'),
    ('expr',0,'expression','STRING',1,None,'Expr'),
    ('sleep',0,'seconds','FLOAT',1,None,'Seconds'),
    ('test',0,'expression','STRING',1,None,'Expr'),
    ('yes',0,'string','STRING',0,'y','String'),
    ('locate',0,'pattern','STRING',1,None,'Pattern'),
    ('cal',0,'month','INTEGER',0,None,'Month'),
    ('cal',1,'year','INTEGER',0,None,'Year'),
    ('curl',0,'url','STRING',1,None,'URL'),
    ('wget',0,'url','STRING',1,None,'URL'),
    ('ping',0,'host','STRING',1,None,'Host'),
    ('dig',0,'domain','STRING',1,None,'Domain'),
    ('ssh',0,'destination','STRING',1,None,'Dest'),
    ('traceroute',0,'host','STRING',1,None,'Host'),
    ('ifconfig',0,'interface','STRING',0,None,'Interface'),
    ('ip',0,'object','STRING',0,None,'Object'),
    ('bg',0,'job','INTEGER',0,None,'Job'),
    ('fg',0,'job','INTEGER',0,None,'Job'),
    ('kill',0,'pid','INTEGER',1,None,'PID'),
    ('killall',0,'name','STRING',1,None,'Name'),
    ('nice',0,'command','STRING',1,None,'Command'),
    ('renice',0,'priority','INTEGER',1,None,'Priority'),
    ('renice',1,'pid','INTEGER',1,None,'PID'),
    ('awk',0,'pattern','STRING',1,None,'Pattern'),
    ('awk',1,'file','PATH',0,None,'File'),
    ('sed',0,'script','STRING',1,None,'Script'),
    ('sed',1,'file','PATH',0,None,'File'),
    ('cut',0,'file','PATH',0,None,'File'),
    ('sort',0,'file','PATH',0,None,'File'),
    ('uniq',0,'file','PATH',0,None,'File'),
    ('diff',0,'file1','PATH',1,None,'File1'),
    ('diff',1,'file2','PATH',1,None,'File2'),
    ('paste',0,'file1','PATH',1,None,'File1'),
    ('paste',1,'file2','PATH',1,None,'File2'),
    ('tr',0,'set1','STRING',1,None,'Set1'),
    ('tr',1,'set2','STRING',0,None,'Set2'),
    ('qrx',0,'angle','FLOAT',1,None,'Angle'),
    ('qrx',1,'qubit','INTEGER',1,None,'Qubit'),
    ('qry',0,'angle','FLOAT',1,None,'Angle'),
    ('qry',1,'qubit','INTEGER',1,None,'Qubit'),
    ('qrz',0,'angle','FLOAT',1,None,'Angle'),
    ('qrz',1,'qubit','INTEGER',1,None,'Qubit'),
    ('qphase',0,'angle','FLOAT',1,None,'Angle'),
    ('qphase',1,'qubit','INTEGER',1,None,'Qubit'),
    ('qccnot',0,'control1','INTEGER',1,None,'Control1'),
    ('qccnot',1,'control2','INTEGER',1,None,'Control2'),
    ('qccnot',2,'target','INTEGER',1,None,'Target'),
    ('qcswap',0,'control','INTEGER',1,None,'Control'),
    ('qcswap',1,'qubit1','INTEGER',1,None,'Qubit1'),
    ('qcswap',2,'qubit2','INTEGER',1,None,'Qubit2'),
    ('qiswap',0,'qubit1','INTEGER',1,None,'Qubit1'),
    ('qiswap',1,'qubit2','INTEGER',1,None,'Qubit2'),
    ('entangle',0,'qubit1','INTEGER',1,None,'Qubit1'),
    ('entangle',1,'qubit2','INTEGER',1,None,'Qubit2'),
    ('teleport',0,'source','INTEGER',1,None,'Source'),
    ('teleport',1,'dest','INTEGER',1,None,'Dest'),
    ('grover',0,'target','STRING',1,None,'Target'),
    ('qinit',0,'qubit','INTEGER',1,None,'Qubit'),
    ('qinit',1,'state','STRING',0,'0','State'),
    ('qstate',0,'qubit','INTEGER',0,None,'Qubit'),
    ('epr_pair',0,'qubit1','INTEGER',1,None,'Qubit1'),
    ('epr_pair',1,'qubit2','INTEGER',1,None,'Qubit2'),
    ('circuit_run',0,'circuit','STRING',1,None,'Circuit'),
    ('golay_encode',0,'data','STRING',1,None,'Data'),
    ('golay_decode',0,'codeword','STRING',1,None,'Codeword'),
    ('leech_encode',0,'vector','STRING',1,None,'Vector'),
    ('leech_decode',0,'point','STRING',1,None,'Point'),
    ('lattice_point',0,'vector','STRING',1,None,'Vector'),
    ('e8_split',0,'vector','STRING',1,None,'Vector'),
    ('moonshine',0,'j_invariant','STRING',0,None,'J-inv'),
    ('triangle',0,'signature','STRING',1,None,'Signature'),
]

# HANDLERS - compact format
HANDLERS = [
    # Archive
    ('gzip','EXTERNAL','gzip','import subprocess\ndef handler(a,f,c,conn): return {"r":subprocess.run(["gzip"]+(["-k"] if f.get("k") else [])+[a.get("file","")],capture_output=True,text=True).returncode}'),
    ('gunzip','EXTERNAL','gunzip','import subprocess\ndef handler(a,f,c,conn): return {"r":subprocess.run(["gunzip",a.get("file","")],capture_output=True,text=True).returncode}'),
    ('bzip2','EXTERNAL','bzip2','import subprocess\ndef handler(a,f,c,conn): return {"r":subprocess.run(["bzip2"]+(["-k"] if f.get("k") else [])+[a.get("file","")],capture_output=True,text=True).returncode}'),
    ('bunzip2','EXTERNAL','bunzip2','import subprocess\ndef handler(a,f,c,conn): return {"r":subprocess.run(["bunzip2",a.get("file","")],capture_output=True,text=True).returncode}'),
    ('xz','EXTERNAL','xz','import subprocess\ndef handler(a,f,c,conn): return {"r":subprocess.run(["xz"]+(["-k"] if f.get("k") else [])+[a.get("file","")],capture_output=True,text=True).returncode}'),
    ('unxz','EXTERNAL','unxz','import subprocess\ndef handler(a,f,c,conn): return {"r":subprocess.run(["unxz",a.get("file","")],capture_output=True,text=True).returncode}'),
    ('tar','EXTERNAL','tar','import subprocess\ndef handler(a,f,c,conn): opts="".join([k for k in "xcvz" if f.get(k)])+"f"; return {"r":subprocess.run(["tar","-"+opts,a.get("archive","")],capture_output=True,text=True).returncode}'),
    ('zip','EXTERNAL','zip','import subprocess\ndef handler(a,f,c,conn): return {"r":subprocess.run(["zip"]+(["-r"] if f.get("r") else [])+[a.get("archive",""),a.get("files","")],capture_output=True,text=True).returncode}'),
    ('unzip','EXTERNAL','unzip','import subprocess\ndef handler(a,f,c,conn): return {"r":subprocess.run(["unzip"]+(["-l"] if f.get("l") else [])+[a.get("archive","")],capture_output=True,text=True).returncode}'),
    ('zcat','EXTERNAL','zcat','import subprocess\ndef handler(a,f,c,conn): r=subprocess.run(["zcat",a.get("file","")],capture_output=True,text=True); return {"out":r.stdout}'),
    # Builtins
    ('alias','SQL_QUERY',None,'def handler(a,f,c,conn): cur=conn.cursor(); cur.execute("SELECT alias_name,target_cmd_id FROM command_aliases WHERE enabled=1"); return {"aliases":[{"n":r[0],"t":r[1]} for r in cur.fetchall()]}'),
    ('apropos','SQL_QUERY',None,'def handler(a,f,c,conn): cur=conn.cursor(); cur.execute("SELECT cmd_name,cmd_description FROM command_registry WHERE cmd_description LIKE ?",(f"%{a.get(\'keyword\',\'\')}%",)); return {"m":[{"c":r[0],"d":r[1]} for r in cur.fetchall()]}'),
    ('eval','BUILTIN',None,'def handler(a,f,c,conn): return {"eval":a.get("command","")}'),
    ('exec','BUILTIN',None,'def handler(a,f,c,conn): return {"exec":a.get("command","")}'),
    ('info','BUILTIN',None,'def handler(a,f,c,conn): return {"info":a.get("topic","dir")}'),
    ('logout','BUILTIN',None,'def handler(a,f,c,conn): return {"logout":True}'),
    ('printf','BUILTIN',None,'def handler(a,f,c,conn): return {"out":a.get("format","")}'),
    ('reset','BUILTIN',None,'def handler(a,f,c,conn): return {"reset":True}'),
    ('set','BUILTIN',None,'def handler(a,f,c,conn): return {"set":True}'),
    ('source','BUILTIN',None,'def handler(a,f,c,conn): return {"source":a.get("file","")}'),
    ('unalias','SQL_QUERY',None,'def handler(a,f,c,conn): cur=conn.cursor(); cur.execute("DELETE FROM command_aliases WHERE alias_name=?",(a.get("name",""),)); conn.commit(); return {"removed":a.get("name","")}'),
    # Filesystem
    ('chmod','FILESYSTEM',None,'def handler(a,f,c,conn): return {"file":a.get("file",""),"mode":a.get("mode","")}'),
    ('chown','FILESYSTEM',None,'def handler(a,f,c,conn): return {"file":a.get("file",""),"owner":a.get("owner","")}'),
    ('chgrp','FILESYSTEM',None,'def handler(a,f,c,conn): return {"file":a.get("file",""),"group":a.get("group","")}'),
    ('cp','FILESYSTEM',None,'def handler(a,f,c,conn): return {"src":a.get("source",""),"dst":a.get("dest","")}'),
    ('mv','FILESYSTEM',None,'def handler(a,f,c,conn): return {"src":a.get("source",""),"dst":a.get("dest","")}'),
    ('ln','FILESYSTEM',None,'def handler(a,f,c,conn): return {"link":a.get("link",""),"target":a.get("target",""),"sym":f.get("s",False)}'),
    ('du','FILESYSTEM',None,'def handler(a,f,c,conn): return {"path":a.get("path","."),"size":"4.0K"}'),
    ('umask','BUILTIN',None,'def handler(a,f,c,conn): return {"umask":a.get("mode","0022")}'),
    # Utilities
    ('bc','PYTHON_METHOD',None,'def handler(a,f,c,conn): return {"calc":"bc","interactive":True}'),
    ('cal','PYTHON_METHOD',None,'import calendar,datetime\ndef handler(a,f,c,conn): m,y=a.get("month"),a.get("year"); now=datetime.datetime.now(); return {"cal":calendar.month(int(y) if y else now.year,int(m) if m else now.month)}'),
    ('expr','PYTHON_METHOD',None,'def handler(a,f,c,conn):\n e=a.get("expression","")\n try: return {"r":eval(e) if all(x in "0123456789+-*/%() " for x in e) else "err"}\n except: return {"r":"err"}'),
    ('false','BUILTIN',None,'def handler(a,f,c,conn): return {"rc":1}'),
    ('true','BUILTIN',None,'def handler(a,f,c,conn): return {"rc":0}'),
    ('test','BUILTIN',None,'def handler(a,f,c,conn): return {"r":True}'),
    ('sleep','PYTHON_METHOD',None,'import time\ndef handler(a,f,c,conn): time.sleep(min(float(a.get("seconds",1)),10)); return {"slept":True}'),
    ('yes','PYTHON_METHOD',None,'def handler(a,f,c,conn): return {"out":"\\n".join([a.get("string","y")]*10)}'),
    ('locate','SQL_QUERY',None,'def handler(a,f,c,conn): cur=conn.cursor(); cur.execute("SELECT path FROM fs_inodes WHERE path LIKE ?",(f"%{a.get(\'pattern\',\'\')}%",)); return {"m":[r[0] for r in cur.fetchall()]}'),
    # Network
    ('curl','NETWORK',None,'def handler(a,f,c,conn): return {"url":a.get("url",""),"status":"simulated"}'),
    ('wget','NETWORK',None,'def handler(a,f,c,conn): return {"url":a.get("url",""),"status":"simulated"}'),
    ('ping','NETWORK',None,'def handler(a,f,c,conn): return {"host":a.get("host",""),"ms":10}'),
    ('dig','NETWORK',None,'def handler(a,f,c,conn): return {"domain":a.get("domain",""),"answer":"127.0.0.1"}'),
    ('ifconfig','NETWORK',None,'def handler(a,f,c,conn): return {"iface":a.get("interface","qnic0"),"inet":"192.168.1.100"}'),
    ('ip','NETWORK',None,'def handler(a,f,c,conn): return {"obj":a.get("object","addr")}'),
    ('netstat','SQL_QUERY',None,'def handler(a,f,c,conn): cur=conn.cursor(); cur.execute("SELECT * FROM qnic_active_connections"); return {"conns":cur.fetchall()}'),
    ('ss','SQL_QUERY',None,'def handler(a,f,c,conn): cur=conn.cursor(); cur.execute("SELECT * FROM qnic_active_connections"); return {"socks":cur.fetchall()}'),
    ('ssh','NETWORK',None,'def handler(a,f,c,conn): return {"dest":a.get("destination","")}'),
    ('traceroute','NETWORK',None,'def handler(a,f,c,conn): return {"host":a.get("host",""),"hops":2}'),
    # Process
    ('bg','BUILTIN',None,'def handler(a,f,c,conn): return {"job":a.get("job",1),"bg":True}'),
    ('fg','BUILTIN',None,'def handler(a,f,c,conn): return {"job":a.get("job",1),"fg":True}'),
    ('jobs','BUILTIN',None,'def handler(a,f,c,conn): return {"jobs":[]}'),
    ('kill','SYSTEM',None,'def handler(a,f,c,conn): return {"pid":a.get("pid",0),"sig":f.get("s","TERM")}'),
    ('killall','SYSTEM',None,'def handler(a,f,c,conn): return {"name":a.get("name",""),"killed":0}'),
    ('nice','SYSTEM',None,'def handler(a,f,c,conn): return {"cmd":a.get("command",""),"n":f.get("n",10)}'),
    ('renice','SYSTEM',None,'def handler(a,f,c,conn): return {"pid":a.get("pid",0),"pri":a.get("priority",0)}'),
    ('top','SQL_QUERY',None,'def handler(a,f,c,conn): cur=conn.cursor(); cur.execute("SELECT COUNT(*) FROM cpu_qubit_allocator"); return {"qubits":cur.fetchone()[0]}'),
    # Text
    ('awk','TEXT_PROCESSOR',None,'def handler(a,f,c,conn): return {"pat":a.get("pattern",""),"file":a.get("file","")}'),
    ('sed','TEXT_PROCESSOR',None,'def handler(a,f,c,conn): return {"script":a.get("script",""),"file":a.get("file","")}'),
    ('cut','TEXT_PROCESSOR',None,'def handler(a,f,c,conn): return {"file":a.get("file",""),"d":f.get("d","\\t")}'),
    ('sort','TEXT_PROCESSOR',None,'def handler(a,f,c,conn): return {"file":a.get("file",""),"r":f.get("r",False)}'),
    ('uniq','TEXT_PROCESSOR',None,'def handler(a,f,c,conn): return {"file":a.get("file",""),"c":f.get("c",False)}'),
    ('diff','TEXT_PROCESSOR',None,'def handler(a,f,c,conn): return {"f1":a.get("file1",""),"f2":a.get("file2","")}'),
    ('paste','TEXT_PROCESSOR',None,'def handler(a,f,c,conn): return {"f1":a.get("file1",""),"f2":a.get("file2","")}'),
    ('tr','TEXT_PROCESSOR',None,'def handler(a,f,c,conn): return {"s1":a.get("set1",""),"s2":a.get("set2","")}'),
    # Quantum gates
    ('qbarrier','QUANTUM_CIRCUIT','h q;','def handler(a,f,c,conn): return {"gate":"barrier"}'),
    ('qccnot','QUANTUM_CIRCUIT','ccx q[0],q[1],q[2];','def handler(a,f,c,conn): return {"gate":"CCX","c1":a.get("control1",0),"c2":a.get("control2",1),"t":a.get("target",2)}'),
    ('qcswap','QUANTUM_CIRCUIT','cswap q[0],q[1],q[2];','def handler(a,f,c,conn): return {"gate":"CSWAP"}'),
    ('qiswap','QUANTUM_CIRCUIT','iswap q[0],q[1];','def handler(a,f,c,conn): return {"gate":"iSWAP","q1":a.get("qubit1",0),"q2":a.get("qubit2",1)}'),
    ('qphase','QUANTUM_CIRCUIT','p(0.785) q[0];','def handler(a,f,c,conn): return {"gate":"Phase","angle":a.get("angle",0.785)}'),
    ('qrx','QUANTUM_CIRCUIT','rx(1.5708) q[0];','def handler(a,f,c,conn): return {"gate":"RX","angle":a.get("angle",1.5708)}'),
    ('qry','QUANTUM_CIRCUIT','ry(1.5708) q[0];','def handler(a,f,c,conn): return {"gate":"RY","angle":a.get("angle",1.5708)}'),
    ('qrz','QUANTUM_CIRCUIT','rz(1.5708) q[0];','def handler(a,f,c,conn): return {"gate":"RZ","angle":a.get("angle",1.5708)}'),
    ('grover','QUANTUM_CIRCUIT','h q; grover;','import math\ndef handler(a,f,c,conn): n=f.get("n",4); return {"alg":"Grover","target":a.get("target",""),"iters":int(math.pi/4*math.sqrt(2**n))}'),
    # Quantum ops
    ('entangle','QUANTUM_CIRCUIT','h q[0]; cx q[0],q[1];','def handler(a,f,c,conn): return {"q1":a.get("qubit1",0),"q2":a.get("qubit2",1),"state":"|Φ+⟩"}'),
    ('qft','QUANTUM_CIRCUIT','qft q;','def handler(a,f,c,conn): return {"op":"QFT","n":f.get("n",4)}'),
    ('iqft','QUANTUM_CIRCUIT','iqft q;','def handler(a,f,c,conn): return {"op":"IQFT","n":f.get("n",4)}'),
    ('qinit','QUANTUM_CIRCUIT','reset q[0];','def handler(a,f,c,conn): return {"q":a.get("qubit",0),"state":a.get("state","0")}'),
    ('qstate','SQL_QUERY',None,'def handler(a,f,c,conn): cur=conn.cursor(); q=a.get("qubit"); cur.execute("SELECT COUNT(*) FROM cpu_qubit_allocator"); return {"total":cur.fetchone()[0]}'),
    ('teleport','QUANTUM_CIRCUIT','h q[1]; cx q[1],q[2]; cx q[0],q[1]; h q[0];','def handler(a,f,c,conn): return {"src":a.get("source",0),"dst":a.get("dest",2)}'),
    ('vqe','QUANTUM_CIRCUIT','ry(0.5) q; cx q[0],q[1];','def handler(a,f,c,conn): return {"alg":"VQE","H":a.get("hamiltonian","H2")}'),
    ('epr_pair','QUANTUM_CIRCUIT','h q[0]; cx q[0],q[1];','def handler(a,f,c,conn): return {"q1":a.get("qubit1",0),"q2":a.get("qubit2",1),"state":"|Φ+⟩"}'),
    ('circuit_run','PYTHON_METHOD',None,'def handler(a,f,c,conn): cur=conn.cursor(); cur.execute("SELECT * FROM quantum_command_circuits WHERE circuit_name=?",(a.get("circuit",""),)); r=cur.fetchone(); return {"run":True} if r else {"err":"not found"}'),
    # Lattice
    ('golay_encode','QUANTUM_CIRCUIT','golay_enc;','def handler(a,f,c,conn): return {"code":"Golay[24,12,8]","data":a.get("data","")}'),
    ('golay_decode','PYTHON_METHOD',None,'def handler(a,f,c,conn): return {"code":"Golay[24,12,8]","cw":a.get("codeword","")}'),
    ('leech_encode','QUANTUM_CIRCUIT','leech_enc;','def handler(a,f,c,conn): return {"lattice":"Leech","vec":a.get("vector","")}'),
    ('leech_decode','PYTHON_METHOD',None,'def handler(a,f,c,conn): return {"lattice":"Leech","pt":a.get("point","")}'),
    ('lattice_point','PYTHON_METHOD',None,'import math\ndef handler(a,f,c,conn):\n try:\n  v=[float(x) for x in a.get("vector","0,0,0").split(",")]\n  n=[round(x) for x in v]\n  d=math.sqrt(sum((x-y)**2 for x,y in zip(v,n)))\n  return {"near":n,"dist":d}\n except: return {"err":"bad vec"}'),
    ('e8_split','QUANTUM_CIRCUIT','e8_split;','def handler(a,f,c,conn): return {"lattice":"E8","vec":a.get("vector",""),"roots":240}'),
    ('moonshine','PYTHON_METHOD',None,'def handler(a,f,c,conn): return {"theory":"Monstrous Moonshine","j":a.get("j_invariant","")}'),
    ('triangle','PYTHON_METHOD',None,'def handler(a,f,c,conn):\n try:\n  p,q,r=map(int,a.get("signature","2,3,7").split(","))\n  s=1/p+1/q+1/r\n  g="hyperbolic" if s<1 else "Euclidean" if s==1 else "spherical"\n  return {"grp":f"Δ({p},{q},{r})","geo":g}\n except: return {"err":"bad sig"}'),
]

def insert_commands(conn):
    c = conn.cursor()
    now = time.time()
    ins = upd = 0
    for name, opcode, cat, desc, usage, qreq in COMMANDS:
        c.execute("SELECT cmd_id FROM command_registry WHERE cmd_name=?", (name,))
        if c.fetchone():
            c.execute("UPDATE command_registry SET cmd_opcode=?,cmd_category=?,cmd_description=?,cmd_usage=?,cmd_requires_qubits=? WHERE cmd_name=?",
                (opcode,cat,desc,usage,qreq,name))
            upd += 1
        else:
            c.execute("INSERT INTO command_registry(cmd_name,cmd_opcode,cmd_category,cmd_description,cmd_usage,cmd_requires_qubits,cmd_created_at) VALUES(?,?,?,?,?,?,?)",
                (name,opcode,cat,desc,usage,qreq,now))
            ins += 1
    conn.commit()
    return ins, upd

def insert_flags(conn):
    c = conn.cursor()
    now = time.time()
    n = 0
    for name, short, long_, bit, ftype, vtype, desc in FLAGS:
        c.execute("SELECT cmd_id FROM command_registry WHERE cmd_name=?", (name,))
        row = c.fetchone()
        if not row: continue
        try:
            c.execute("INSERT OR REPLACE INTO command_flags(cmd_id,flag_short,flag_long,flag_bit,flag_type,value_type,flag_description,created_at,enabled) VALUES(?,?,?,?,?,?,?,?,1)",
                (row[0],short,long_,bit,ftype,vtype,desc,now))
            n += 1
        except: pass
    conn.commit()
    return n

def insert_arguments(conn):
    c = conn.cursor()
    now = time.time()
    n = 0
    for name, pos, aname, atype, req, default, desc in ARGUMENTS:
        c.execute("SELECT cmd_id FROM command_registry WHERE cmd_name=?", (name,))
        row = c.fetchone()
        if not row: continue
        try:
            c.execute("INSERT OR REPLACE INTO command_arguments(cmd_id,arg_position,arg_name,arg_type,required,default_value,arg_description,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (row[0],pos,aname,atype,req,default,desc,now))
            n += 1
        except: pass
    conn.commit()
    return n

def insert_handlers(conn):
    c = conn.cursor()
    now = time.time()
    n = 0
    for name, htype, qasm, pycode in HANDLERS:
        c.execute("SELECT cmd_id FROM command_registry WHERE cmd_name=?", (name,))
        row = c.fetchone()
        if not row:
            print(f"  Warn: {name} not found")
            continue
        qreq = 1 if htype == 'QUANTUM_CIRCUIT' else 0
        try:
            c.execute("INSERT OR REPLACE INTO command_handlers(cmd_id,handler_type,qasm_code,python_code,result_formatter,requires_qubits,priority,created_at,enabled) VALUES(?,?,?,?,?,?,?,?,1)",
                (row[0],htype,qasm,pycode,'{result}',qreq,100,now))
            n += 1
        except sqlite3.Error as e:
            print(f"  Err {name}: {e}")
    conn.commit()
    return n

def apply_patch(db_path=None):
    if db_path is None:
        db_path = DB_PATH
    
    print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    QUNIX DATABASE PATCH v{VERSION}                       ║
║                    Part 3: Final 51 Command Handlers                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
Target: {db_path}
""")
    
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        print("Phase 1: Commands...")
        ins, upd = insert_commands(conn)
        print(f"  ✓ {ins} inserted, {upd} updated")
        
        print("Phase 2: Flags...")
        print(f"  ✓ {insert_flags(conn)} flags")
        
        print("Phase 3: Arguments...")
        print(f"  ✓ {insert_arguments(conn)} arguments")
        
        print("Phase 4: Handlers...")
        print(f"  ✓ {insert_handlers(conn)} handlers")
        
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM command_registry WHERE cmd_enabled=1")
        cmds = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM command_handlers WHERE enabled=1")
        hdlrs = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM command_registry WHERE cmd_enabled=1 AND cmd_id NOT IN (SELECT DISTINCT cmd_id FROM command_handlers WHERE enabled=1)")
        miss = c.fetchone()[0]
        
        print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║  COMPLETE: {cmds} commands, {hdlrs} handlers, {miss} missing                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
""")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    sys.exit(0 if apply_patch(db) else 1)
