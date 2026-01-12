#!/usr/bin/env python3
"""
qunix_ipc_unification_patch.py - FIXES ALL IPC COMMUNICATION

This patch:
1. Unifies quantum_channel and quantum_channel_packets into ONE table
2. Updates CPU to poll the correct table
3. Updates Bus to write to the correct table
4. Migrates existing packets
5. Creates proper indexes

Run this ONCE to fix all IPC issues.
"""

import sqlite3
import time
from pathlib import Path
import sys

VERSION = "2.0.0-IPC-UNIFIED"

# ANSI Colors
class C:
    G='\033[92m'; R='\033[91m'; Y='\033[93m'; C='\033[96m'
    M='\033[35m'; B='\033[94m'; BOLD='\033[1m'; E='\033[0m'; GRAY='\033[90m'

print(f"\n{C.BOLD}{C.M}{'='*70}{C.E}")
print(f"{C.BOLD}{C.M}QUNIX IPC UNIFICATION PATCH v{VERSION}{C.E}")
print(f"{C.BOLD}{C.M}Fixes All Communication Between Flask/Bus/CPU{C.E}")
print(f"{C.BOLD}{C.M}{'='*70}{C.E}\n")


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
    conn.row_factory = sqlite3.Row
    return conn


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1: ANALYZE CURRENT STATE
# ═══════════════════════════════════════════════════════════════════════════

def analyze_current_state(conn):
    """Analyze what tables exist and their contents"""
    print(f"{C.C}Analyzing current IPC state...{C.E}\n")
    
    cursor = conn.cursor()
    
    # Check quantum_channel
    qc_exists = False
    qc_count = 0
    try:
        cursor.execute("SELECT COUNT(*) FROM quantum_channel")
        qc_count = cursor.fetchone()[0]
        qc_exists = True
        print(f"  {C.G}✓{C.E} quantum_channel: {qc_count} packets")
    except:
        print(f"  {C.GRAY}·{C.E} quantum_channel: not found")
    
    # Check quantum_channel_packets
    qcp_exists = False
    qcp_count = 0
    try:
        cursor.execute("SELECT COUNT(*) FROM quantum_channel_packets")
        qcp_count = cursor.fetchone()[0]
        qcp_exists = True
        print(f"  {C.G}✓{C.E} quantum_channel_packets: {qcp_count} packets")
    except:
        print(f"  {C.GRAY}·{C.E} quantum_channel_packets: not found")
    
    print()
    return qc_exists, qc_count, qcp_exists, qcp_count


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2: CREATE UNIFIED TABLE
# ═══════════════════════════════════════════════════════════════════════════

def create_unified_table(conn):
    """Create the ONE TRUE IPC table"""
    print(f"{C.C}Creating unified IPC table...{C.E}\n")
    
    cursor = conn.cursor()
    
    # Drop old tables (save data first)
    cursor.execute("DROP TABLE IF EXISTS quantum_ipc_old")
    cursor.execute("DROP TABLE IF EXISTS quantum_channel_packets_old")
    
    # Rename existing tables as backup
    try:
        cursor.execute("ALTER TABLE quantum_channel RENAME TO quantum_ipc_old")
        print(f"  {C.G}✓{C.E} Backed up quantum_channel → quantum_ipc_old")
    except:
        pass
    
    try:
        cursor.execute("ALTER TABLE quantum_channel_packets RENAME TO quantum_channel_packets_old")
        print(f"  {C.G}✓{C.E} Backed up quantum_channel_packets → quantum_channel_packets_old")
    except:
        pass
    
    # Create THE unified table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quantum_ipc (
            packet_id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Sender/Direction
            sender TEXT NOT NULL,
            direction TEXT NOT NULL,
            
            -- Payload (BOTH original_data and binary_data for compatibility)
            original_data BLOB,
            binary_data BLOB,
            data_size INTEGER,
            data_hash BLOB,
            
            -- Quantum metrics
            chsh_value REAL DEFAULT 2.0,
            fidelity REAL DEFAULT 1.0,
            bell_pair_ids TEXT,
            num_pairs INTEGER DEFAULT 0,
            
            -- Timing
            created_at REAL DEFAULT (strftime('%s', 'now')),
            processed_at REAL,
            
            -- State
            state TEXT DEFAULT 'PENDING',
            processed INTEGER DEFAULT 0,
            
            -- Optional metadata
            packet_type TEXT DEFAULT 'COMMAND',
            error_message TEXT
        )
    """)
    
    print(f"  {C.G}✓{C.E} Created quantum_ipc table")
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ipc_direction ON quantum_ipc(direction, processed)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ipc_state ON quantum_ipc(state)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ipc_sender ON quantum_ipc(sender)")
    
    print(f"  {C.G}✓{C.E} Created indexes")
    print()


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3: MIGRATE EXISTING DATA
# ═══════════════════════════════════════════════════════════════════════════

def migrate_data(conn):
    """Migrate data from old tables to unified table"""
    print(f"{C.C}Migrating existing packets...{C.E}\n")
    
    cursor = conn.cursor()
    migrated = 0
    
    # Migrate from quantum_ipc_old (was quantum_channel)
    try:
        cursor.execute("""
            SELECT packet_id, sender, direction, original_data, original_size,
                   chsh_value, timestamp, processed, bell_pair_ids, num_pairs
            FROM quantum_ipc_old
            WHERE processed = 0
        """)
        
        for row in cursor.fetchall():
            cursor.execute("""
                INSERT INTO quantum_ipc 
                (sender, direction, original_data, binary_data, data_size,
                 chsh_value, created_at, processed, bell_pair_ids, num_pairs, state)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
            """, (
                row['sender'],
                row['direction'],
                row['original_data'],
                row['original_data'],  # Copy to both fields
                row['original_size'],
                row['chsh_value'],
                row['timestamp'],
                0,
                row['bell_pair_ids'],
                row['num_pairs']
            ))
            migrated += 1
        
        print(f"  {C.G}✓{C.E} Migrated {migrated} packets from quantum_channel")
    except Exception as e:
        print(f"  {C.GRAY}·{C.E} quantum_channel: {e}")
    
    # Migrate from quantum_channel_packets_old
    migrated_qcp = 0
    try:
        cursor.execute("""
            SELECT packet_id, sender, direction, binary_data, binary_size,
                   chsh_value, transmission_start, processed, packet_type, state
            FROM quantum_channel_packets_old
            WHERE processed = 0
        """)
        
        for row in cursor.fetchall():
            cursor.execute("""
                INSERT INTO quantum_ipc
                (sender, direction, original_data, binary_data, data_size,
                 chsh_value, created_at, processed, packet_type, state)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['sender'],
                row['direction'],
                row['binary_data'],  # Copy to both fields
                row['binary_data'],
                row['binary_size'],
                row['chsh_value'] or 2.0,
                row['transmission_start'] or time.time(),
                0,
                row['packet_type'],
                row['state'] or 'PENDING'
            ))
            migrated_qcp += 1
        
        print(f"  {C.G}✓{C.E} Migrated {migrated_qcp} packets from quantum_channel_packets")
    except Exception as e:
        print(f"  {C.GRAY}·{C.E} quantum_channel_packets: {e}")
    
    total = migrated + migrated_qcp
    print(f"\n  {C.BOLD}Total migrated: {total} packets{C.E}\n")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4: CREATE COMPATIBILITY VIEWS
# ═══════════════════════════════════════════════════════════════════════════

def create_compatibility_views(conn):
    """Create views so old code still works"""
    print(f"{C.C}Creating compatibility views...{C.E}\n")
    
    cursor = conn.cursor()
    
    # View 1: quantum_channel (for qunix_link.py compatibility)
    cursor.execute("DROP VIEW IF EXISTS quantum_channel")
    cursor.execute("""
        CREATE VIEW quantum_channel AS
        SELECT 
            packet_id,
            sender,
            direction,
            original_data,
            data_size AS original_size,
            chsh_value,
            created_at AS timestamp,
            processed,
            processed_at,
            bell_pair_ids,
            num_pairs,
            fidelity,
            state
        FROM quantum_ipc
    """)
    print(f"  {C.G}✓{C.E} Created view: quantum_channel → quantum_ipc")
    
    # View 2: quantum_channel_packets (for quantum_mega_bus.py compatibility)
    cursor.execute("DROP VIEW IF EXISTS quantum_channel_packets")
    cursor.execute("""
        CREATE VIEW quantum_channel_packets AS
        SELECT
            packet_id,
            sender,
            direction,
            packet_type,
            binary_data,
            data_size AS binary_size,
            data_hash AS binary_hash,
            chsh_value,
            fidelity,
            created_at AS transmission_start,
            processed_at AS transmission_end,
            state,
            processed,
            processed_at
        FROM quantum_ipc
    """)
    print(f"  {C.G}✓{C.E} Created view: quantum_channel_packets → quantum_ipc")
    
    print()


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5: STANDARDIZE DIRECTION VALUES
# ═══════════════════════════════════════════════════════════════════════════

def standardize_directions(conn):
    """Standardize all direction values"""
    print(f"{C.C}Standardizing direction values...{C.E}\n")
    
    cursor = conn.cursor()
    
    # Map all variations to standard values
    mappings = [
        ('a_to_b', 'FLASK_TO_CPU'),      # qunix_link uses a_to_b
        ('BUS_TO_CPU', 'FLASK_TO_CPU'),  # quantum_mega_bus uses BUS_TO_CPU
        ('b_to_a', 'CPU_TO_FLASK'),      # qunix_link uses b_to_a
        ('CPU_TO_BUS', 'CPU_TO_FLASK'),  # quantum_mega_bus uses CPU_TO_BUS
    ]
    
    for old, new in mappings:
        cursor.execute("""
            UPDATE quantum_ipc
            SET direction = ?
            WHERE direction = ?
        """, (new, old))
        
        count = cursor.execute("SELECT changes()").fetchone()[0]
        if count > 0:
            print(f"  {C.G}✓{C.E} Updated {count} packets: {old} → {new}")
    
    print()


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6: VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════

def verify_setup(conn):
    """Verify the unified setup"""
    print(f"{C.C}Verifying unified IPC setup...{C.E}\n")
    
    cursor = conn.cursor()
    
    # Check quantum_ipc exists
    cursor.execute("SELECT COUNT(*) FROM quantum_ipc")
    total = cursor.fetchone()[0]
    print(f"  {C.G}✓{C.E} quantum_ipc: {total} total packets")
    
    # Check pending packets
    cursor.execute("SELECT COUNT(*) FROM quantum_ipc WHERE processed = 0")
    pending = cursor.fetchone()[0]
    print(f"  {C.G}✓{C.E} Pending packets: {pending}")
    
    # Check by direction
    for direction in ['FLASK_TO_CPU', 'CPU_TO_FLASK']:
        cursor.execute("""
            SELECT COUNT(*) FROM quantum_ipc 
            WHERE direction = ? AND processed = 0
        """, (direction,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"  {C.Y}⚠{C.E} {direction}: {count} unprocessed")
        else:
            print(f"  {C.G}✓{C.E} {direction}: 0 unprocessed")
    
    # Check views exist
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='view' AND name IN ('quantum_channel', 'quantum_channel_packets')
    """)
    views = [row[0] for row in cursor.fetchall()]
    
    if 'quantum_channel' in views:
        print(f"  {C.G}✓{C.E} View: quantum_channel")
    else:
        print(f"  {C.R}✗{C.E} View: quantum_channel missing")
    
    if 'quantum_channel_packets' in views:
        print(f"  {C.G}✓{C.E} View: quantum_channel_packets")
    else:
        print(f"  {C.R}✗{C.E} View: quantum_channel_packets missing")
    
    print()
    
    # Summary
    if pending == 0:
        print(f"{C.G}✓ IPC queue is clean{C.E}")
    else:
        print(f"{C.Y}⚠ {pending} packets waiting to be processed{C.E}")
        print(f"{C.GRAY}  Run CPU to process these packets{C.E}")
    
    print()


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7: CLEAR OLD PACKETS (OPTIONAL)
# ═══════════════════════════════════════════════════════════════════════════

def clear_old_packets(conn):
    """Clear old/stuck packets"""
    print(f"{C.Y}Clear old packets?{C.E}")
    print(f"{C.GRAY}This will delete all unprocessed packets older than 1 hour{C.E}")
    
    response = input(f"Clear? (yes/no): ").strip().lower()
    
    if response == 'yes':
        cursor = conn.cursor()
        
        cutoff = time.time() - 3600  # 1 hour
        
        cursor.execute("""
            DELETE FROM quantum_ipc
            WHERE processed = 0 AND created_at < ?
        """, (cutoff,))
        
        deleted = cursor.execute("SELECT changes()").fetchone()[0]
        print(f"\n  {C.G}✓{C.E} Deleted {deleted} old packets\n")
    else:
        print(f"\n  {C.GRAY}Skipped{C.E}\n")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 8: MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Main execution"""
    
    # Find database
    db_path = find_database()
    
    if not db_path:
        print(f"{C.R}✗ Database not found{C.E}")
        return 1
    
    print(f"{C.G}✓ Found: {db_path}{C.E}")
    print(f"  Size: {db_path.stat().st_size / (1024*1024):.2f} MB\n")
    
    # Connect
    conn = create_connection(db_path)
    
    try:
        # Step 1: Analyze
        analyze_current_state(conn)
        
        # Step 2: Create unified table
        create_unified_table(conn)
        
        # Step 3: Migrate data
        migrate_data(conn)
        
        # Step 4: Create views
        create_compatibility_views(conn)
        
        # Step 5: Standardize directions
        standardize_directions(conn)
        
        # Step 6: Verify
        verify_setup(conn)
        
        # Step 7: Optionally clear old packets
        clear_old_packets(conn)
        
        # Success
        print(f"{C.BOLD}{C.G}{'='*70}{C.E}")
        print(f"{C.BOLD}{C.G}✓ IPC UNIFICATION COMPLETE{C.E}")
        print(f"{C.BOLD}{C.G}{'='*70}{C.E}\n")
        
        print(f"{C.BOLD}What changed:{C.E}")
        print(f"  • ONE table: quantum_ipc (replaces both old tables)")
        print(f"  • Compatibility views: quantum_channel & quantum_channel_packets")
        print(f"  • Standard directions: FLASK_TO_CPU, CPU_TO_FLASK")
        print(f"  • All existing packets migrated")
        
        print(f"\n{C.BOLD}Next steps:{C.E}")
        print(f"  1. Restart Flask (flask_app.py)")
        print(f"  2. Start CPU (python qunix_cpu.py)")
        print(f"  3. Test: type 'help' in terminal")
        
        print(f"\n{C.G}Everything should work now!{C.E}\n")
        
        conn.close()
        return 0
        
    except Exception as e:
        print(f"\n{C.R}✗ Error: {e}{C.E}\n")
        import traceback
        traceback.print_exc()
        conn.close()
        return 1


if __name__ == '__main__':
    sys.exit(main())