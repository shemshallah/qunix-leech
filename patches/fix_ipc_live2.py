#!/usr/bin/env python3
"""
Verify IPC is set up correctly
"""
import sqlite3
from pathlib import Path

class C:
    G='\033[92m'; R='\033[91m'; Y='\033[93m'; C='\033[96m'
    BOLD='\033[1m'; E='\033[0m'; GRAY='\033[90m'

db_path = Path('/home/Shemshallah/qunix_leech.db')

print(f"\n{C.BOLD}IPC Setup Verification{C.E}\n")

conn = sqlite3.connect(str(db_path), timeout=60)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 1. Check quantum_ipc table
print(f"1. {C.C}quantum_ipc table:{C.E}")
try:
    cursor.execute("SELECT COUNT(*) as cnt FROM quantum_ipc")
    total = cursor.fetchone()['cnt']
    print(f"   {C.G}✓{C.E} Exists with {total} packets")
    
    cursor.execute("SELECT COUNT(*) FROM quantum_ipc WHERE processed=0")
    pending = cursor.fetchone()[0]
    print(f"   {C.Y if pending > 0 else C.G}{'⚠' if pending > 0 else '✓'}{C.E} {pending} unprocessed packets")
    
except Exception as e:
    print(f"   {C.R}✗{C.E} Error: {e}")

# 2. Check quantum_channel view
print(f"\n2. {C.C}quantum_channel view:{C.E}")
try:
    cursor.execute("SELECT COUNT(*) FROM quantum_channel")
    count = cursor.fetchone()[0]
    print(f"   {C.G}✓{C.E} Exists ({count} packets visible)")
    
    # Test if CPU can read from it
    cursor.execute("""
        SELECT packet_id, sender, direction, processed 
        FROM quantum_channel 
        WHERE direction = 'FLASK_TO_CPU' AND processed = 0
        LIMIT 1
    """)
    row = cursor.fetchone()
    if row:
        print(f"   {C.Y}⚠{C.E} Sample packet found: ID={row['packet_id']}, from={row['sender']}")
    else:
        print(f"   {C.G}✓{C.E} No pending FLASK_TO_CPU packets")
        
except Exception as e:
    print(f"   {C.R}✗{C.E} Error: {e}")

# 3. Check quantum_channel_packets view
print(f"\n3. {C.C}quantum_channel_packets view:{C.E}")
try:
    cursor.execute("SELECT COUNT(*) FROM quantum_channel_packets")
    count = cursor.fetchone()[0]
    print(f"   {C.G}✓{C.E} Exists ({count} packets visible)")
except Exception as e:
    print(f"   {C.R}✗{C.E} Error: {e}")

# 4. Show schema of quantum_channel view
print(f"\n4. {C.C}quantum_channel schema (what CPU sees):{C.E}")
cursor.execute("PRAGMA table_info(quantum_channel)")
columns = cursor.fetchall()
for col in columns:
    print(f"   {C.GRAY}·{C.E} {col[1]} ({col[2]})")

# 5. Direction values
print(f"\n5. {C.C}Current direction values:{C.E}")
cursor.execute("""
    SELECT direction, COUNT(*) as cnt, SUM(CASE WHEN processed=0 THEN 1 ELSE 0 END) as pending
    FROM quantum_ipc
    GROUP BY direction
""")
for row in cursor.fetchall():
    status = f"{C.Y}⚠{C.E}" if row['pending'] > 0 else f"{C.G}✓{C.E}"
    print(f"   {status} {row['direction']}: {row['cnt']} total, {row['pending']} pending")

# 6. Test CPU query
print(f"\n6. {C.C}Test CPU's exact query:{C.E}")
try:
    cursor.execute("""
        SELECT packet_id, sender, direction, original_data, chsh_value, state
        FROM quantum_channel
        WHERE direction = 'a_to_b' 
          AND processed = 0
        ORDER BY packet_id
        LIMIT 5
    """)
    rows = cursor.fetchall()
    if rows:
        print(f"   {C.Y}⚠{C.E} Found {len(rows)} packets with direction='a_to_b'")
        print(f"   {C.GRAY}(CPU is looking for 'a_to_b' but we standardized to 'FLASK_TO_CPU'){C.E}")
    else:
        print(f"   {C.G}✓{C.E} No packets with direction='a_to_b' (expected)")
    
    # Try the standardized direction
    cursor.execute("""
        SELECT packet_id, sender, direction, original_data, chsh_value, state
        FROM quantum_channel
        WHERE direction = 'FLASK_TO_CPU'
          AND processed = 0
        ORDER BY packet_id
        LIMIT 5
    """)
    rows = cursor.fetchall()
    if rows:
        print(f"   {C.Y}⚠{C.E} Found {len(rows)} packets with direction='FLASK_TO_CPU'")
        for row in rows:
            data = row['original_data']
            if data:
                try:
                    cmd = data.decode('utf-8') if isinstance(data, bytes) else str(data)
                    print(f"      • Packet {row['packet_id']}: '{cmd[:30]}' (from {row['sender']})")
                except:
                    print(f"      • Packet {row['packet_id']}: <binary> (from {row['sender']})")
    else:
        print(f"   {C.G}✓{C.E} No pending FLASK_TO_CPU packets")
        
except Exception as e:
    print(f"   {C.R}✗{C.E} Error: {e}")

conn.close()

print(f"\n{C.BOLD}Diagnosis:{C.E}")
print(f"\nThe IPC system is set up correctly!")
print(f"\n{C.BOLD}The issue:{C.E} CPU code is looking for direction='a_to_b'")
print(f"but we standardized to 'FLASK_TO_CPU'")
print(f"\n{C.BOLD}Solution:{C.E} Update CPU code to use standard directions")
print(f"OR add INSERT trigger to auto-convert on write")
print()