#!/usr/bin/env python3
"""
QUNIX FILESYSTEM INTERFACE v1.0.0
External Filesystem Integration for QUNIX Database
"""

import sqlite3
import os
import stat
import time
import hashlib
import json
import zlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass

VERSION = "1.0.0-QUNIX-FS"

class C:
    G = '\033[92m'; R = '\033[91m'; Y = '\033[93m'; C = '\033[96m'
    M = '\033[35m'; BOLD = '\033[1m'; E = '\033[0m'

@dataclass
class Inode:
    inode_id: int
    inode_type: str
    mode: int
    uid: int
    gid: int
    size: int
    nlink: int
    atime: float
    mtime: float
    ctime: float
    crtime: float
    quantum_encoded: bool = False
    lattice_point_id: Optional[int] = None

@dataclass
class DirEntry:
    name: str
    inode_id: int
    file_type: str

@dataclass
class FileHandle:
    fd: int
    inode_id: int
    mode: str
    offset: int
    session_id: str

class QunixFilesystem:
    TYPE_FILE = 'f'
    TYPE_DIR = 'd'
    TYPE_LINK = 'l'
    
    def __init__(self, conn: sqlite3.Connection, session_id: str = 'default'):
        self.conn = conn
        self.session_id = session_id
        self.block_size = 4096
        self._path_cache = {}
        self._fd_counter = 3
        self._open_files: Dict[int, FileHandle] = {}
        self._ensure_cwd()
    
    def _ensure_cwd(self):
        c = self.conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO fs_cwd (session_id, cwd_inode, cwd_path, updated_at)
            VALUES (?, 1, '/', ?)
        """, (self.session_id, time.time()))
        self.conn.commit()
    
    def _resolve_path(self, path: str) -> Optional[int]:
        if not path.startswith('/'):
            cwd = self.getcwd()
            path = os.path.normpath(os.path.join(cwd, path))
        else:
            path = os.path.normpath(path)
        
        if path in self._path_cache:
            return self._path_cache[path]
        
        if path == '/':
            return 1
        
        parts = [p for p in path.split('/') if p]
        current_inode = 1
        c = self.conn.cursor()
        
        for part in parts:
            c.execute("""
                SELECT child_inode FROM fs_dentries 
                WHERE parent_inode = ? AND name = ?
            """, (current_inode, part))
            row = c.fetchone()
            if not row:
                return None
            current_inode = row[0]
        
        self._path_cache[path] = current_inode
        return current_inode
    
    def _get_path(self, inode_id: int) -> str:
        if inode_id == 1:
            return '/'
        
        c = self.conn.cursor()
        parts = []
        current = inode_id
        
        while current != 1:
            c.execute("""
                SELECT parent_inode, name FROM fs_dentries 
                WHERE child_inode = ? AND name != '.' AND name != '..'
            """, (current,))
            row = c.fetchone()
            if not row:
                break
            parts.append(row[1])
            current = row[0]
        
        parts.reverse()
        return '/' + '/'.join(parts)
    
    def _get_inode(self, inode_id: int) -> Optional[Inode]:
        c = self.conn.cursor()
        c.execute("""
            SELECT inode_id, inode_type, mode, uid, gid, size, nlink,
                   atime, mtime, ctime, crtime, quantum_encoded, lattice_point_id
            FROM fs_inodes WHERE inode_id = ?
        """, (inode_id,))
        row = c.fetchone()
        if row:
            return Inode(*row)
        return None
    
    def getcwd(self) -> str:
        c = self.conn.cursor()
        c.execute("SELECT cwd_path FROM fs_cwd WHERE session_id = ?", (self.session_id,))
        row = c.fetchone()
        return row[0] if row else '/'
    
    def chdir(self, path: str) -> bool:
        inode_id = self._resolve_path(path)
        if inode_id is None:
            return False
        
        inode = self._get_inode(inode_id)
        if not inode or inode.inode_type != self.TYPE_DIR:
            return False
        
        full_path = self._get_path(inode_id)
        
        c = self.conn.cursor()
        c.execute("""
            UPDATE fs_cwd SET cwd_inode = ?, cwd_path = ?, updated_at = ?
            WHERE session_id = ?
        """, (inode_id, full_path, time.time(), self.session_id))
        self.conn.commit()
        return True
    
    def listdir(self, path: str = '.') -> List[DirEntry]:
        inode_id = self._resolve_path(path)
        if inode_id is None:
            return []
        
        c = self.conn.cursor()
        c.execute("""
            SELECT d.name, d.child_inode, i.inode_type
            FROM fs_dentries d
            JOIN fs_inodes i ON d.child_inode = i.inode_id
            WHERE d.parent_inode = ?
            ORDER BY d.name
        """, (inode_id,))
        
        return [DirEntry(name=row[0], inode_id=row[1], file_type=row[2]) 
                for row in c.fetchall()]
    
    def mkdir(self, path: str, mode: int = 0o755) -> bool:
        parent_path = os.path.dirname(path.rstrip('/'))
        name = os.path.basename(path.rstrip('/'))
        
        if not parent_path:
            parent_path = self.getcwd()
        
        parent_inode = self._resolve_path(parent_path)
        if parent_inode is None:
            return False
        
        if self._resolve_path(path) is not None:
            return False
        
        now = time.time()
        c = self.conn.cursor()
        
        c.execute("""
            INSERT INTO fs_inodes (inode_type, mode, uid, gid, nlink, size,
                                   atime, mtime, ctime, crtime)
            VALUES ('d', ?, 0, 0, 2, 0, ?, ?, ?, ?)
        """, (mode, now, now, now, now))
        new_inode = c.lastrowid
        
        c.execute("""
            INSERT INTO fs_dentries (parent_inode, child_inode, name, file_type, created_at)
            VALUES (?, ?, ?, 'd', ?)
        """, (parent_inode, new_inode, name, now))
        
        c.execute("""
            INSERT INTO fs_dentries (parent_inode, child_inode, name, file_type, created_at)
            VALUES (?, ?, '.', 'd', ?), (?, ?, '..', 'd', ?)
        """, (new_inode, new_inode, now, new_inode, parent_inode, now))
        
        c.execute("UPDATE fs_inodes SET nlink = nlink + 1 WHERE inode_id = ?", (parent_inode,))
        self.conn.commit()
        self._path_cache.pop(path, None)
        return True
    
    def create(self, path: str, mode: int = 0o644) -> Optional[int]:
        parent_path = os.path.dirname(path)
        name = os.path.basename(path)
        
        if not parent_path:
            parent_path = self.getcwd()
        
        parent_inode = self._resolve_path(parent_path)
        if parent_inode is None:
            return None
        
        existing = self._resolve_path(path)
        if existing is not None:
            return existing
        
        now = time.time()
        c = self.conn.cursor()
        
        c.execute("""
            INSERT INTO fs_inodes (inode_type, mode, uid, gid, nlink, size,
                                   atime, mtime, ctime, crtime)
            VALUES ('f', ?, 0, 0, 1, 0, ?, ?, ?, ?)
        """, (mode, now, now, now, now))
        new_inode = c.lastrowid
        
        c.execute("""
            INSERT INTO fs_dentries (parent_inode, child_inode, name, file_type, created_at)
            VALUES (?, ?, ?, 'f', ?)
        """, (parent_inode, new_inode, name, now))
        
        self.conn.commit()
        return new_inode
    
    def read_file(self, path: str) -> Optional[bytes]:
        inode_id = self._resolve_path(path)
        if inode_id is None:
            return None
        
        c = self.conn.cursor()
        c.execute("""
            SELECT data, compressed FROM fs_blocks
            WHERE inode_id = ? ORDER BY block_index
        """, (inode_id,))
        
        data = b''
        for block_data, compressed in c.fetchall():
            if block_data:
                if compressed:
                    block_data = zlib.decompress(block_data)
                data += block_data
        return data
    
    def write_file(self, path: str, data: bytes) -> bool:
        inode_id = self._resolve_path(path)
        if inode_id is None:
            inode_id = self.create(path)
        if inode_id is None:
            return False
        
        c = self.conn.cursor()
        c.execute("DELETE FROM fs_blocks WHERE inode_id = ?", (inode_id,))
        
        block_idx = 0
        offset = 0
        while offset < len(data):
            block_data = data[offset:offset + self.block_size]
            c.execute("""
                INSERT INTO fs_blocks (inode_id, block_index, data, data_size, created_at, modified_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (inode_id, block_idx, block_data, len(block_data), time.time(), time.time()))
            block_idx += 1
            offset += self.block_size
        
        c.execute("UPDATE fs_inodes SET size = ?, mtime = ? WHERE inode_id = ?",
                 (len(data), time.time(), inode_id))
        self.conn.commit()
        return True
    
    def unlink(self, path: str) -> bool:
        inode_id = self._resolve_path(path)
        if inode_id is None:
            return False
        
        inode = self._get_inode(inode_id)
        if not inode or inode.inode_type == self.TYPE_DIR:
            return False
        
        c = self.conn.cursor()
        c.execute("DELETE FROM fs_blocks WHERE inode_id = ?", (inode_id,))
        c.execute("DELETE FROM fs_inodes WHERE inode_id = ?", (inode_id,))
        
        name = os.path.basename(path)
        parent_path = os.path.dirname(path) or '/'
        parent_inode = self._resolve_path(parent_path)
        
        c.execute("DELETE FROM fs_dentries WHERE parent_inode = ? AND name = ?", 
                 (parent_inode, name))
        self.conn.commit()
        self._path_cache.pop(path, None)
        return True
    
    def stat(self, path: str) -> Optional[Dict]:
        inode_id = self._resolve_path(path)
        if inode_id is None:
            return None
        
        inode = self._get_inode(inode_id)
        if not inode:
            return None
        
        type_modes = {'f': stat.S_IFREG, 'd': stat.S_IFDIR, 'l': stat.S_IFLNK}
        
        return {
            'st_mode': type_modes.get(inode.inode_type, 0) | inode.mode,
            'st_ino': inode.inode_id,
            'st_nlink': inode.nlink,
            'st_uid': inode.uid,
            'st_gid': inode.gid,
            'st_size': inode.size,
            'st_atime': inode.atime,
            'st_mtime': inode.mtime,
            'st_ctime': inode.ctime,
        }
    
    def exists(self, path: str) -> bool:
        return self._resolve_path(path) is not None
    
    def isfile(self, path: str) -> bool:
        inode_id = self._resolve_path(path)
        if inode_id is None:
            return False
        inode = self._get_inode(inode_id)
        return inode is not None and inode.inode_type == self.TYPE_FILE
    
    def isdir(self, path: str) -> bool:
        inode_id = self._resolve_path(path)
        if inode_id is None:
            return False
        inode = self._get_inode(inode_id)
        return inode is not None and inode.inode_type == self.TYPE_DIR
    
    def tree(self, path: str = '/', prefix: str = '', max_depth: int = 5) -> str:
        if max_depth <= 0:
            return prefix + '...'
        
        result = []
        entries = self.listdir(path)
        
        for i, entry in enumerate(entries):
            if entry.name in ('.', '..'):
                continue
            
            is_last = (i == len(entries) - 1)
            connector = '└── ' if is_last else '├── '
            type_char = '/' if entry.file_type == 'd' else ''
            result.append(prefix + connector + entry.name + type_char)
            
            if entry.file_type == 'd':
                new_prefix = prefix + ('    ' if is_last else '│   ')
                sub_path = os.path.join(path, entry.name)
                result.append(self.tree(sub_path, new_prefix, max_depth - 1))
        
        return '\n'.join(result)
    
    def df(self) -> Dict:
        c = self.conn.cursor()
        c.execute("SELECT COALESCE(SUM(size), 0) FROM fs_inodes")
        used = c.fetchone()[0]
        total = 1000000 * 4096
        return {'total': total, 'used': used, 'free': total - used, 
                'percent_used': (used / total * 100) if total > 0 else 0}


class ExternalFSBridge:
    def __init__(self, qfs: QunixFilesystem, external_root: str = None):
        self.qfs = qfs
        self.external_root = Path(external_root) if external_root else Path.home()
    
    def import_file(self, external_path: str, virtual_path: str) -> bool:
        ext_path = Path(external_path)
        if not ext_path.exists():
            return False
        try:
            data = ext_path.read_bytes()
            return self.qfs.write_file(virtual_path, data)
        except Exception:
            return False
    
    def export_file(self, virtual_path: str, external_path: str) -> bool:
        data = self.qfs.read_file(virtual_path)
        if data is None:
            return False
        try:
            ext_path = Path(external_path)
            ext_path.parent.mkdir(parents=True, exist_ok=True)
            ext_path.write_bytes(data)
            return True
        except Exception:
            return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description='QUNIX Filesystem')
    parser.add_argument('db', help='Database path')
    parser.add_argument('--session', default='cli', help='Session ID')
    args = parser.parse_args()
    
    conn = sqlite3.connect(args.db)
    qfs = QunixFilesystem(conn, args.session)
    
    print(f"QUNIX Filesystem Shell v{VERSION}")
    print("Type 'help' for commands")
    
    while True:
        try:
            cwd = qfs.getcwd()
            cmd = input(f"qunix:{cwd}$ ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        
        if not cmd:
            continue
        
        parts = cmd.split()
        cmd_name = parts[0]
        cmd_args = parts[1:]
        
        if cmd_name == 'exit':
            break
        elif cmd_name == 'help':
            print("Commands: ls, cd, pwd, cat, mkdir, rm, touch, stat, tree, df")
        elif cmd_name == 'ls':
            for entry in qfs.listdir(cmd_args[0] if cmd_args else '.'):
                if entry.name not in ('.', '..'):
                    print(f"  {entry.name}{'/' if entry.file_type == 'd' else ''}")
        elif cmd_name == 'cd':
            if not qfs.chdir(cmd_args[0] if cmd_args else '/'):
                print("No such directory")
        elif cmd_name == 'pwd':
            print(qfs.getcwd())
        elif cmd_name == 'cat' and cmd_args:
            data = qfs.read_file(cmd_args[0])
            if data:
                print(data.decode('utf-8', errors='replace'))
        elif cmd_name == 'mkdir' and cmd_args:
            qfs.mkdir(cmd_args[0])
        elif cmd_name == 'touch' and cmd_args:
            qfs.create(cmd_args[0])
        elif cmd_name == 'rm' and cmd_args:
            qfs.unlink(cmd_args[0])
        elif cmd_name == 'stat' and cmd_args:
            s = qfs.stat(cmd_args[0])
            if s:
                print(f"  Size: {s['st_size']}, Mode: {oct(s['st_mode'])}")
        elif cmd_name == 'tree':
            print(qfs.tree(cmd_args[0] if cmd_args else '/'))
        elif cmd_name == 'df':
            u = qfs.df()
            print(f"Used: {u['used']:,} / {u['total']:,} ({u['percent_used']:.1f}%)")
    
    conn.close()

if __name__ == '__main__':
    main()
