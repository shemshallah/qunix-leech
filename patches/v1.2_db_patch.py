
#!/usr/bin/env python3
"""
qunix_followup_patch.py - FIXES ALL REMAINING ISSUES

Fixes:
1. Missing requires_qubits column in command_registry
2. Missing leech_lattice table
3. Any other schema mismatches
"""

import sqlite3
import json
import time
import struct
import zlib
import numpy as np
from pathlib import Path
import sys

VERSION = "1.0.0-FOLLOWUP"

# ANSI Colors
class C:
    G='\033[92m'; R='\033[91m'; Y='\033[93m'; C='\033[96m'
    M='\033[35m'; B='\033[94m'; BOLD='\033[1m'; E='\033[0m'

print(f"\n{C.BOLD}{C.M}{'='*70}{C.E}")
print(f"{C.BOLD}{C.M}QUNIX FOLLOW-UP PATCH v{VERSION}{C.E}")
print(f"{C.BOLD}{C.M}Fixes Missing Columns and Tables{C.E}")
print(f"{C.BOLD}{C.M}{'='*70}{C.E}\n")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1: SCHEMA FIXES
# ═══════════════════════════════════════════════════════════════════════════

def find_database():
    """Find QUNIX database"""
    locations = [
        Path('/home/Shemshallah/qunix_leech.db'),
        Path('/home/Shemshallah/mysite/qunix_leech.db'),
        Path('/data/qunix_leech.db'),
        Path.home() / 'qunix_leech.db',
        Path.cwd() / 'qunix_leech.db',
    ]
    
    for loc in locations:
        if loc.exists():
            return loc
    return None


def create_connection(db_path: Path):
    """Create optimized connection"""
    conn = sqlite3.connect(str(db_path), timeout=60, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=60000")
    return conn


def check_column_exists(cursor, table: str, column: str):
    """Check if column exists in table"""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def check_table_exists(cursor, table: str):
    """Check if table exists"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2: FIX COMMAND_REGISTRY TABLE
# ═══════════════════════════════════════════════════════════════════════════

def fix_command_registry(conn):
    """Fix command_registry table - add missing columns"""
    print(f"{C.C}Fixing command_registry table...{C.E}")
    
    cursor = conn.cursor()
    
    # Check what columns exist
    cursor.execute("PRAGMA table_info(command_registry)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    
    print(f"  Existing columns: {existing_cols}")
    
    # Columns we need
    required_cols = {
        'requires_qubits': 'INTEGER DEFAULT 0',
        'min_qubits': 'INTEGER DEFAULT 0',
        'max_qubits': 'INTEGER DEFAULT 10',
        'cmd_enabled': 'INTEGER DEFAULT 1',
    }
    
    # Add missing columns
    for col, col_type in required_cols.items():
        if col not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE command_registry ADD COLUMN {col} {col_type}")
                print(f"  {C.G}✓{C.E} Added column: {col}")
            except sqlite3.OperationalError as e:
                print(f"  {C.Y}!{C.E} Column {col}: {e}")
    
    print(f"{C.G}✓ command_registry fixed{C.E}\n")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3: CREATE LEECH_LATTICE TABLE
# ═══════════════════════════════════════════════════════════════════════════

def create_leech_lattice_table(conn):
    """Create leech_lattice table with sample data"""
    print(f"{C.C}Creating leech_lattice table...{C.E}")
    
    cursor = conn.cursor()
    
    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leech_lattice (
            point_id INTEGER PRIMARY KEY,
            coords BLOB,
            norm_sq INTEGER,
            e8_sublattice INTEGER,
            j_address BLOB,
            poincare_x REAL,
            poincare_y REAL,
            sigma_phase REAL,
            allocated INTEGER DEFAULT 0
        )
    """)
    
    # Check if empty
    cursor.execute("SELECT COUNT(*) FROM leech_lattice")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print(f"  Populating with sample lattice points...")
        
        # Generate sample lattice points
        for i in range(1000):
            # Generate 24D coordinates (simple version)
            coords = np.zeros(24, dtype=np.float32)
            
            # Simple lattice point generation
            # Real Leech lattice has specific construction rules
            for j in range(24):
                coords[j] = np.random.choice([-2, -1, 0, 1, 2])
            
            # Compress coordinates
            coords_bytes = coords.tobytes()
            coords_compressed = zlib.compress(coords_bytes)
            
            # Compute norm squared
            norm_sq = int(np.sum(coords**2))
            
            # E8 sublattice (0, 1, or 2)
            e8_sub = i % 3
            
            # J-invariant address (placeholder)
            j_address = struct.pack('>QQ', i, i*2)
            
            # Poincaré disk coordinates
            angle = (i / 1000.0) * 2 * np.pi
            radius = 0.5 + (i % 100) / 200.0
            poincare_x = radius * np.cos(angle)
            poincare_y = radius * np.sin(angle)
            
            # Sigma phase
            sigma_phase = (i % 360) * np.pi / 180.0
            
            cursor.execute("""
                INSERT INTO leech_lattice 
                (point_id, coords, norm_sq, e8_sublattice, j_address, 
                 poincare_x, poincare_y, sigma_phase, allocated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (i, coords_compressed, norm_sq, e8_sub, j_address,
                  poincare_x, poincare_y, sigma_phase))
            
            if (i + 1) % 100 == 0:
                print(f"    Generated {i+1}/1000 points...")
        
        print(f"  {C.G}✓{C.E} Generated 1000 sample lattice points")
    else:
        print(f"  {C.G}✓{C.E} Table already has {count} points")
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leech_allocated ON leech_lattice(allocated)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leech_e8 ON leech_lattice(e8_sublattice)")
    
    print(f"{C.G}✓ leech_lattice created{C.E}\n")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4: CREATE MISSING ALIAS TABLE (l → leech_lattice)
# ═══════════════════════════════════════════════════════════════════════════

def create_view_aliases(conn):
    """Create view aliases for compatibility"""
    print(f"{C.C}Creating view aliases...{C.E}")
    
    cursor = conn.cursor()
    
    # Create 'l' view as alias for leech_lattice
    cursor.execute("DROP VIEW IF EXISTS l")
    cursor.execute("""
        CREATE VIEW l AS
        SELECT 
            point_id AS i,
            coords AS c,
            norm_sq AS n,
            e8_sublattice AS e,
            CAST(point_id AS REAL) AS j,
            CAST(point_id * 2 AS REAL) AS ji,
            poincare_x AS x,
            poincare_y AS y,
            sigma_phase AS s
        FROM leech_lattice
    """)
    
    print(f"  {C.G}✓{C.E} Created view 'l' → leech_lattice")
    
    # Create 'q' view as alias for qubits (if qubits table exists)
    if check_table_exists(cursor, 'qubits'):
        cursor.execute("DROP VIEW IF EXISTS q")
        cursor.execute("""
            CREATE VIEW q AS
            SELECT * FROM qubits
        """)
        print(f"  {C.G}✓{C.E} Created view 'q' → qubits")
    
    print(f"{C.G}✓ View aliases created{C.E}\n")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5: ADD MISSING TABLES REFERENCED BY SCRIPTS
# ═══════════════════════════════════════════════════════════════════════════

def create_missing_tables(conn):
    """Create any other missing tables"""
    print(f"{C.C}Creating missing tables...{C.E}")
    
    cursor = conn.cursor()
    
    tables_sql = {
        'ipc_pipe_messages': """
            CREATE TABLE IF NOT EXISTS ipc_pipe_messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pipe_name TEXT,
                direction TEXT,
                data BLOB,
                priority INTEGER DEFAULT 0,
                timestamp REAL,
                read_flag INTEGER DEFAULT 0
            )
        """,
        
        'circuit_gates': """
            CREATE TABLE IF NOT EXISTS circuit_gates (
                gate_id INTEGER PRIMARY KEY AUTOINCREMENT,
                circuit_id INTEGER,
                gate_order INTEGER,
                gate_type TEXT,
                target_qubits TEXT,
                control_qubits TEXT,
                parameters TEXT,
                FOREIGN KEY(circuit_id) REFERENCES quantum_circuits(circuit_id)
            )
        """,
        
        'circuit_executions': """
            CREATE TABLE IF NOT EXISTS circuit_executions (
                execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                circuit_id INTEGER,
                session_id TEXT,
                executed_at REAL,
                shots INTEGER DEFAULT 1024,
                results_json TEXT,
                fidelity REAL,
                chsh_value REAL,
                execution_time_ms REAL,
                FOREIGN KEY(circuit_id) REFERENCES quantum_circuits(circuit_id)
            )
        """,
        
        'hyperbolic_routes': """
            CREATE TABLE IF NOT EXISTS hyperbolic_routes (
                hyp_route_id INTEGER PRIMARY KEY AUTOINCREMENT,
                src_poincare_x REAL,
                src_poincare_y REAL,
                dst_poincare_x REAL,
                dst_poincare_y REAL,
                hyperbolic_distance REAL,
                geodesic_path TEXT,
                num_hops INTEGER,
                created_at REAL
            )
        """,
        
        'quantum_gate_log': """
            CREATE TABLE IF NOT EXISTS quantum_gate_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                reg_id INTEGER,
                gate_name TEXT,
                qubit_ids TEXT,
                timestamp REAL,
                fidelity REAL
            )
        """,
    }
    
    for table_name, sql in tables_sql.items():
        if not check_table_exists(cursor, table_name):
            cursor.execute(sql)
            print(f"  {C.G}✓{C.E} Created table: {table_name}")
        else:
            print(f"  {C.Y}·{C.E} Table exists: {table_name}")
    
    print(f"{C.G}✓ Missing tables created{C.E}\n")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6: FIX QUANTUM_CHANNEL_PACKETS TABLE
# ═══════════════════════════════════════════════════════════════════════════

def fix_quantum_channel_packets(conn):
    """Fix quantum_channel_packets table"""
    print(f"{C.C}Fixing quantum_channel_packets table...{C.E}")
    
    cursor = conn.cursor()
    
    # Add missing columns
    missing_columns = {
        'encoded_bits': 'TEXT',
        'num_qubits_used': 'INTEGER DEFAULT 0',
        'epr_pairs_used': 'TEXT',
        'route_id': 'INTEGER',
        'lattice_path_used': 'TEXT',
        'transmission_start': 'REAL',
        'transmission_end': 'REAL',
        'processed_at': 'REAL',
        'binary_hash': 'BLOB',
    }
    
    for col, col_type in missing_columns.items():
        if not check_column_exists(cursor, 'quantum_channel_packets', col):
            try:
                cursor.execute(f"ALTER TABLE quantum_channel_packets ADD COLUMN {col} {col_type}")
                print(f"  {C.G}✓{C.E} Added column: {col}")
            except Exception as e:
                print(f"  {C.Y}!{C.E} {col}: {e}")
    
    print(f"{C.G}✓ quantum_channel_packets fixed{C.E}\n")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7: VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════

def verify_all(conn):
    """Verify all fixes"""
    print(f"{C.C}Running verification...{C.E}\n")
    
    cursor = conn.cursor()
    
    # Check command_registry has requires_qubits
    print(f"  Checking command_registry...")
    if check_column_exists(cursor, 'command_registry', 'requires_qubits'):
        print(f"    {C.G}✓{C.E} requires_qubits column exists")
    else:
        print(f"    {C.R}✗{C.E} requires_qubits column missing")
        return False
    
    # Check leech_lattice exists
    print(f"  Checking leech_lattice...")
    if check_table_exists(cursor, 'leech_lattice'):
        cursor.execute("SELECT COUNT(*) FROM leech_lattice")
        count = cursor.fetchone()[0]
        print(f"    {C.G}✓{C.E} leech_lattice exists ({count} points)")
    else:
        print(f"    {C.R}✗{C.E} leech_lattice missing")
        return False
    
    # Check view 'l' exists
    print(f"  Checking view 'l'...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='l'")
    if cursor.fetchone():
        print(f"    {C.G}✓{C.E} View 'l' exists")
    else:
        print(f"    {C.Y}!{C.E} View 'l' not found (non-critical)")
    
    # Check all required tables
    print(f"  Checking required tables...")
    required = [
        'mega_bus_core',
        'command_registry',
        'quantum_circuits',
        'quantum_channel_packets',
        'epr_pair_pool',
        'quantum_result_queue',
        'leech_lattice',
        'system_metrics',
        'cpu_core_state',
    ]
    
    all_good = True
    for table in required:
        if check_table_exists(cursor, table):
            print(f"    {C.G}✓{C.E} {table}")
        else:
            print(f"    {C.R}✗{C.E} {table}")
            all_good = False
    
    if all_good:
        print(f"\n{C.G}✓ All verifications passed{C.E}\n")
        return True
    else:
        print(f"\n{C.R}✗ Some verifications failed{C.E}\n")
        return False


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 8: STATISTICS
# ═══════════════════════════════════════════════════════════════════════════

def show_statistics(conn):
    """Show final statistics"""
    print(f"{C.BOLD}{C.M}DATABASE STATISTICS{C.E}")
    print(f"{C.M}{'='*70}{C.E}\n")
    
    cursor = conn.cursor()
    
    stats = [
        ("Commands", "SELECT COUNT(*) FROM command_registry"),
        ("Quantum Circuits", "SELECT COUNT(*) FROM quantum_circuits"),
        ("Binary Commands", "SELECT COUNT(*) FROM binary_commands"),
        ("Leech Lattice Points", "SELECT COUNT(*) FROM leech_lattice"),
        ("EPR Pairs", "SELECT COUNT(*) FROM epr_pair_pool"),
        ("System Metrics", "SELECT COUNT(*) FROM system_metrics"),
    ]
    
    for name, query in stats:
        try:
            cursor.execute(query)
            count = cursor.fetchone()[0]
            print(f"  {name:.<35} {count:>10,}")
        except Exception as e:
            print(f"  {name:.<35} {C.Y}Error{C.E}")
    
    # Table count
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
    table_count = cursor.fetchone()[0]
    print(f"  {'Total Tables':.<35} {table_count:>10,}")
    
    # View count
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='view'")
    view_count = cursor.fetchone()[0]
    print(f"  {'Total Views':.<35} {view_count:>10,}")
    
    print(f"\n{C.M}{'='*70}{C.E}\n")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 9: MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='QUNIX Follow-up Patch')
    parser.add_argument('--db', type=str, help='Database path')
    parser.add_argument('--verify-only', action='store_true', help='Only verify, no fixes')
    args = parser.parse_args()
    
    # Find database
    if args.db:
        db_path = Path(args.db)
    else:
        db_path = find_database()
    
    if not db_path or not db_path.exists():
        print(f"{C.R}✗ Database not found{C.E}")
        return 1
    
    print(f"{C.G}✓ Found: {db_path}{C.E}")
    print(f"  Size: {db_path.stat().st_size / (1024*1024):.2f} MB\n")
    
    # Connect
    conn = create_connection(db_path)
    
    if args.verify_only:
        # Verification only
        if verify_all(conn):
            print(f"{C.G}✓ Database is ready{C.E}\n")
            conn.close()
            return 0
        else:
            print(f"{C.R}✗ Database needs fixes{C.E}\n")
            conn.close()
            return 1
    
    # Apply fixes
    print(f"{C.BOLD}Applying fixes...{C.E}\n")
    
    try:
        # Fix 1: command_registry columns
        fix_command_registry(conn)
        
        # Fix 2: Create leech_lattice
        create_leech_lattice_table(conn)
        
        # Fix 3: Create view aliases
        create_view_aliases(conn)
        
        # Fix 4: Create missing tables
        create_missing_tables(conn)
        
        # Fix 5: Fix quantum_channel_packets
        fix_quantum_channel_packets(conn)
        
        # Verify
        if not verify_all(conn):
            print(f"{C.R}✗ Verification failed{C.E}")
            conn.close()
            return 1
        
        # Show statistics
        show_statistics(conn)
        
        conn.close()
        
        print(f"{C.BOLD}{C.G}{'='*70}{C.E}")
        print(f"{C.BOLD}{C.G}✓ ALL FIXES APPLIED SUCCESSFULLY{C.E}")
        print(f"{C.BOLD}{C.G}{'='*70}{C.E}\n")
        
        return 0
    
    except Exception as e:
        print(f"\n{C.R}✗ Error: {e}{C.E}\n")
        import traceback
        traceback.print_exc()
        conn.close()
        return 1


if __name__ == '__main__':
    sys.exit(main())
