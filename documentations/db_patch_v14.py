#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║        QUNIX AUTO-FIX APPLIER - VERIFIED FOR ALL 196,560 QUBITS          ║
║        Applies the auto-generated fix with verification                   ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import sqlite3
import sys
from pathlib import Path
import time

class C:
    G='\033[92m';R='\033[91m';Y='\033[93m';C='\033[96m';M='\033[95m'
    BOLD='\033[1m';E='\033[0m';GRAY='\033[90m';Q='\033[38;5;213m'

def apply_fix(db_path: Path):
    """Apply the auto-generated fix with full verification"""
    
    print(f"\n{C.BOLD}{C.M}╔══════════════════════════════════════════════════════════════╗{C.E}")
    print(f"{C.BOLD}{C.M}║         APPLYING AUTO-FIX FOR ALL 196,560 QUBITS             ║{C.E}")
    print(f"{C.BOLD}{C.M}╚══════════════════════════════════════════════════════════════╝{C.E}\n")
    
    # Backup first
    import shutil
    backup_path = db_path.with_suffix('.db.pre-autofix')
    print(f"{C.C}Creating backup...{C.E}")
    shutil.copy2(db_path, backup_path)
    print(f"{C.G}✓{C.E} Backup: {backup_path}\n")
    
    conn = sqlite3.connect(str(db_path), timeout=60.0)
    c = conn.cursor()
    
    try:
        # ══════════════════════════════════════════════════════════════
        # STEP 1: Fix NULL etypes
        # ══════════════════════════════════════════════════════════════
        print(f"{C.BOLD}[STEP 1] Fixing NULL etypes{C.E}")
        
        # Check current state
        c.execute("SELECT COUNT(*) FROM q WHERE etype IS NULL OR etype = ''")
        null_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM q")
        total_count = c.fetchone()[0]
        
        print(f"  Total qubits in q: {total_count:,}")
        print(f"  NULL/empty etypes: {null_count:,}")
        
        if null_count > 0:
            print(f"\n  {C.C}Executing: UPDATE q SET etype = 'PRODUCT' WHERE etype IS NULL OR etype = '';{C.E}")
            c.execute("UPDATE q SET etype = 'PRODUCT' WHERE etype IS NULL OR etype = ''")
            print(f"  {C.G}✓{C.E} Updated {c.rowcount:,} qubits")
        else:
            print(f"  {C.G}✓{C.E} All qubits already have etype set")
        
        # Verify
        c.execute("SELECT etype, COUNT(*) FROM q GROUP BY etype")
        print(f"\n  etype distribution:")
        for row in c.fetchall():
            etype = row[0] or 'NULL'
            cnt = row[1]
            print(f"    {etype:20s} {cnt:>10,}")
        
        conn.commit()
        
        # ══════════════════════════════════════════════════════════════
        # STEP 2: Clear allocator
        # ══════════════════════════════════════════════════════════════
        print(f"\n{C.BOLD}[STEP 2] Clearing allocator{C.E}")
        
        c.execute("SELECT COUNT(*) FROM cpu_qubit_allocator")
        old_count = c.fetchone()[0]
        print(f"  Current allocator entries: {old_count:,}")
        
        print(f"\n  {C.C}Executing: DELETE FROM cpu_qubit_allocator;{C.E}")
        c.execute("DELETE FROM cpu_qubit_allocator")
        print(f"  {C.G}✓{C.E} Deleted {c.rowcount:,} entries")
        
        conn.commit()
        
        # ══════════════════════════════════════════════════════════════
        # STEP 3: Populate allocator from q
        # ══════════════════════════════════════════════════════════════
        print(f"\n{C.BOLD}[STEP 3] Populating allocator from q table{C.E}")
        
        # Check q table structure
        c.execute("PRAGMA table_info(q)")
        columns = [row[1] for row in c.fetchall()]
        print(f"  q table columns: {', '.join(columns)}")
        
        if 'i' not in columns:
            print(f"  {C.R}✗ Column 'i' not found in q table!{C.E}")
            return False
        
        # Get qubit ID range
        c.execute("SELECT MIN(i), MAX(i), COUNT(*) FROM q")
        min_id, max_id, count = c.fetchone()
        print(f"  Qubit ID range: {min_id} - {max_id}")
        print(f"  Total qubits:   {count:,}")
        
        # Verify expected count
        if count != 196560:
            print(f"  {C.Y}⚠ Warning: Expected 196,560 qubits, found {count:,}{C.E}")
        
        # Execute the population query
        print(f"\n  {C.C}Executing: INSERT INTO cpu_qubit_allocator (qubit_id, allocated, allocated_to_pid){C.E}")
        print(f"  {C.C}           SELECT i, 0, NULL FROM q;{C.E}")
        
        start_time = time.time()
        c.execute("""
            INSERT INTO cpu_qubit_allocator (qubit_id, allocated, allocated_to_pid)
            SELECT i, 0, NULL FROM q
        """)
        elapsed = time.time() - start_time
        
        print(f"  {C.G}✓{C.E} Inserted {c.rowcount:,} entries in {elapsed:.2f}s")
        
        conn.commit()
        
        # ══════════════════════════════════════════════════════════════
        # VERIFICATION
        # ══════════════════════════════════════════════════════════════
        print(f"\n{C.BOLD}[VERIFICATION] Checking results{C.E}")
        
        # Check 1: Total count
        print(f"\n  {C.C}Check 1: Total count{C.E}")
        c.execute("SELECT COUNT(*) FROM cpu_qubit_allocator")
        alloc_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM q")
        q_count = c.fetchone()[0]
        
        print(f"    q table:       {q_count:>10,}")
        print(f"    Allocator:     {alloc_count:>10,}")
        print(f"    Expected:      {196560:>10,}")
        
        if alloc_count == q_count == 196560:
            print(f"    {C.G}✓ Perfect! All 196,560 qubits accounted for{C.E}")
        elif alloc_count == q_count:
            print(f"    {C.G}✓ Counts match ({alloc_count:,}){C.E}")
        else:
            print(f"    {C.R}✗ Count mismatch!{C.E}")
            return False
        
        # Check 2: ID matching
        print(f"\n  {C.C}Check 2: ID matching{C.E}")
        c.execute("""
            SELECT COUNT(*) FROM q 
            WHERE i NOT IN (SELECT qubit_id FROM cpu_qubit_allocator)
        """)
        missing = c.fetchone()[0]
        
        c.execute("""
            SELECT COUNT(*) FROM cpu_qubit_allocator 
            WHERE qubit_id NOT IN (SELECT i FROM q)
        """)
        orphaned = c.fetchone()[0]
        
        print(f"    Qubits missing from allocator:     {missing:>10,}")
        print(f"    Allocator entries with invalid ID: {orphaned:>10,}")
        
        if missing == 0 and orphaned == 0:
            print(f"    {C.G}✓ All IDs match perfectly{C.E}")
        else:
            print(f"    {C.R}✗ ID mismatch found!{C.E}")
            return False
        
        # Check 3: Allocation status
        print(f"\n  {C.C}Check 3: Allocation status{C.E}")
        c.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN allocated = 0 THEN 1 ELSE 0 END) as free,
                SUM(CASE WHEN allocated = 1 THEN 1 ELSE 0 END) as allocated
            FROM cpu_qubit_allocator
        """)
        
        stats = c.fetchone()
        print(f"    Total:     {stats[0]:>10,}")
        print(f"    Free:      {stats[1]:>10,}")
        print(f"    Allocated: {stats[2]:>10,}")
        
        if stats[1] == stats[0]:
            print(f"    {C.G}✓ All qubits are FREE and ready{C.E}")
        else:
            print(f"    {C.Y}⚠ Some qubits already allocated{C.E}")
        
        # Check 4: PRODUCT qubits
        print(f"\n  {C.C}Check 4: PRODUCT qubits available{C.E}")
        c.execute("""
            SELECT COUNT(*) FROM q WHERE etype = 'PRODUCT'
        """)
        product_count = c.fetchone()[0]
        print(f"    PRODUCT qubits in q: {product_count:,}")
        
        c.execute("""
            SELECT COUNT(*) 
            FROM q 
            JOIN cpu_qubit_allocator ON q.i = cpu_qubit_allocator.qubit_id
            WHERE q.etype = 'PRODUCT' AND cpu_qubit_allocator.allocated = 0
        """)
        free_product = c.fetchone()[0]
        print(f"    Free PRODUCT qubits: {free_product:,}")
        
        if free_product > 0:
            print(f"    {C.G}✓ PRODUCT qubits ready for allocation{C.E}")
        else:
            print(f"    {C.R}✗ No free PRODUCT qubits!{C.E}")
            return False
        
        # Check 5: Sample allocation test
        print(f"\n  {C.C}Check 5: Allocation query test{C.E}")
        c.execute("""
            SELECT i FROM q 
            WHERE etype = 'PRODUCT' 
            LIMIT 10
        """)
        available = [row[0] for row in c.fetchall()]
        
        c.execute("SELECT qubit_id FROM cpu_qubit_allocator WHERE allocated = 1")
        allocated_set = set(row[0] for row in c.fetchall())
        
        free_qubits = [qid for qid in available if qid not in allocated_set]
        
        print(f"    Query returned: {len(available)} qubits")
        print(f"    After filtering: {len(free_qubits)} FREE")
        
        if len(free_qubits) > 0:
            print(f"    Sample IDs: {free_qubits[:5]}")
            print(f"    {C.G}✓ qalloc query will work!{C.E}")
        else:
            print(f"    {C.R}✗ No free qubits after filtering{C.E}")
            return False
        
        # Final summary
        print(f"\n{C.BOLD}{C.G}╔══════════════════════════════════════════════════════════════╗{C.E}")
        print(f"{C.BOLD}{C.G}║                 ✓ ALL CHECKS PASSED                          ║{C.E}")
        print(f"{C.BOLD}{C.G}║          {alloc_count:,} QUBITS READY FOR ALLOCATION          ║{C.E}")
        print(f"{C.BOLD}{C.G}╚══════════════════════════════════════════════════════════════╝{C.E}\n")
        
        return True
        
    except Exception as e:
        print(f"\n{C.R}✗ Error: {e}{C.E}\n")
        import traceback
        traceback.print_exc()
        print(f"\n{C.Y}Restore from: {backup_path}{C.E}\n")
        return False
    
    finally:
        conn.close()

def main():
    if len(sys.argv) < 2:
        print(f"\n{C.R}Usage: python db_apply_fix.py <database.db>{C.E}\n")
        return 1
    
    db_path = Path(sys.argv[1])
    if not db_path.exists():
        print(f"\n{C.R}Database not found: {db_path}{C.E}\n")
        return 1
    
    print(f"{C.C}Database: {db_path}{C.E}")
    
    if apply_fix(db_path):
        print(f"{C.C}Ready to test!{C.E}")
        print(f"\n  {C.BOLD}python qunix_cpu.py{C.E}")
        print(f"  {C.Q}qunix>{C.E} status")
        print(f"  {C.Q}qunix>{C.E} qalloc 5")
        print(f"  {C.Q}qunix>{C.E} qh 0")
        print()
        return 0
    else:
        print(f"{C.R}Fix failed - see errors above{C.E}\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())