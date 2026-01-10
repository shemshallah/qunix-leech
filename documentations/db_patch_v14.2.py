#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║        QUNIX QUBIT DISTRIBUTION CHECKER                                   ║
║        Where are all the qubits? Should be ~194k free!                    ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import sqlite3
import sys
from pathlib import Path

class C:
    G='\033[92m';R='\033[91m';Y='\033[93m';C='\033[96m';M='\033[95m'
    BOLD='\033[1m';E='\033[0m';GRAY='\033[90m';Q='\033[38;5;213m'

def check_distribution(db_path: Path):
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    
    print(f"\n{C.BOLD}{C.M}╔══════════════════════════════════════════════════════════════╗{C.E}")
    print(f"{C.BOLD}{C.M}║         QUBIT DISTRIBUTION ANALYSIS                          ║{C.E}")
    print(f"{C.BOLD}{C.M}╚══════════════════════════════════════════════════════════════╝{C.E}\n")
    
    # Total qubits in q table
    c.execute("SELECT COUNT(*) FROM q")
    total_q = c.fetchone()[0]
    print(f"{C.C}Total qubits in q table:{C.E} {total_q:,}")
    print(f"{C.C}Expected:{C.E} 196,560 (Leech lattice kissing number)")
    print(f"{C.Y}Missing:{C.E} {196560 - total_q:,}\n")
    
    # Breakdown by etype
    print(f"{C.BOLD}ETYPE DISTRIBUTION:{C.E}\n")
    c.execute("SELECT etype, COUNT(*) as cnt FROM q GROUP BY etype ORDER BY cnt DESC")
    
    for row in c.fetchall():
        etype = row[0] or 'NULL'
        cnt = row[1]
        pct = (cnt / total_q * 100) if total_q > 0 else 0
        bar = '█' * int(pct / 2)
        print(f"  {etype:20s} {cnt:>10,} ({pct:5.1f}%) {bar}")
    
    # Allocator status
    print(f"\n{C.BOLD}ALLOCATOR STATUS:{C.E}\n")
    c.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN allocated = 0 THEN 1 ELSE 0 END) as free,
            SUM(CASE WHEN allocated = 1 THEN 1 ELSE 0 END) as allocated
        FROM cpu_qubit_allocator
    """)
    stats = c.fetchone()
    
    print(f"  Total entries:  {stats[0]:>10,}")
    print(f"  FREE:           {stats[1]:>10,} {C.G}← Should be ~194k!{C.E}")
    print(f"  ALLOCATED:      {stats[2]:>10,}")
    
    # Check which etypes are FREE
    print(f"\n{C.BOLD}FREE QUBITS BY ETYPE:{C.E}\n")
    c.execute("""
        SELECT q.etype, COUNT(*) as cnt
        FROM q
        JOIN cpu_qubit_allocator a ON q.i = a.qubit_id
        WHERE a.allocated = 0
        GROUP BY q.etype
        ORDER BY cnt DESC
    """)
    
    total_free_by_type = 0
    for row in c.fetchall():
        etype = row[0] or 'NULL'
        cnt = row[1]
        total_free_by_type += cnt
        print(f"  {etype:20s} {cnt:>10,} free")
    
    print(f"\n  {C.BOLD}Total FREE:{C.E} {total_free_by_type:,}")
    
    # Check which etypes are ALLOCATED
    print(f"\n{C.BOLD}ALLOCATED QUBITS BY ETYPE:{C.E}\n")
    c.execute("""
        SELECT q.etype, COUNT(*) as cnt
        FROM q
        JOIN cpu_qubit_allocator a ON q.i = a.qubit_id
        WHERE a.allocated = 1
        GROUP BY q.etype
        ORDER BY cnt DESC
    """)
    
    for row in c.fetchall():
        etype = row[0] or 'NULL'
        cnt = row[1]
        print(f"  {etype:20s} {cnt:>10,} allocated")
    
    # Check for qubits NOT in allocator
    print(f"\n{C.BOLD}QUBITS NOT IN ALLOCATOR:{C.E}\n")
    c.execute("""
        SELECT COUNT(*) FROM q
        WHERE i NOT IN (SELECT qubit_id FROM cpu_qubit_allocator)
    """)
    not_in_alloc = c.fetchone()[0]
    
    if not_in_alloc > 0:
        print(f"  {C.R}Found {not_in_alloc:,} qubits in q but NOT in allocator!{C.E}")
        
        c.execute("""
            SELECT etype, COUNT(*) as cnt
            FROM q
            WHERE i NOT IN (SELECT qubit_id FROM cpu_qubit_allocator)
            GROUP BY etype
            ORDER BY cnt DESC
        """)
        
        print(f"\n  Breakdown:")
        for row in c.fetchall():
            etype = row[0] or 'NULL'
            cnt = row[1]
            print(f"    {etype:20s} {cnt:>10,}")
        
        print(f"\n  {C.Y}These qubits need to be added to the allocator!{C.E}")
    else:
        print(f"  {C.G}✓ All qubits are in the allocator{C.E}")
    
    # Summary
    print(f"\n{C.BOLD}SUMMARY:{C.E}\n")
    
    if total_free_by_type < 190000:
        print(f"  {C.R}✗ Only {total_free_by_type:,} free qubits (expected ~194k){C.E}")
        print(f"\n  {C.Y}POSSIBLE ISSUES:{C.E}")
        
        if not_in_alloc > 0:
            print(f"    1. {not_in_alloc:,} qubits missing from allocator")
            print(f"       Fix: Run populate script again")
        
        if stats[2] > 1000:
            print(f"    2. {stats[2]:,} qubits marked as ALLOCATED")
            print(f"       Fix: Reset with UPDATE cpu_qubit_allocator SET allocated = 0")
        
        if total_q < 196560:
            print(f"    3. Database only has {total_q:,} qubits (missing {196560 - total_q:,})")
            print(f"       Fix: Regenerate full database with all 196,560 qubits")
    else:
        print(f"  {C.G}✓ {total_free_by_type:,} free qubits available!{C.E}")
    
    print()
    conn.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"\n{C.R}Usage: python check_qubit_distribution.py <database.db>{C.E}\n")
        sys.exit(1)
    
    db_path = Path(sys.argv[1])
    if not db_path.exists():
        print(f"\n{C.R}Database not found: {db_path}{C.E}\n")
        sys.exit(1)
    
    check_distribution(db_path)