#!/usr/bin/env python3
"""
QUNIX Command Handler Diagnostic Mapper
Outputs to /home/Shemshallah/qunix_cmd_diagnostic.txt
"""

import sqlite3
from pathlib import Path

DB_PATH = "/home/Shemshallah/qunix_leech.db"
OUTPUT = "/home/Shemshallah/qunix_cmd_diagnostic.txt"

def analyze_commands():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get all commands
    c.execute("SELECT cmd_id, cmd_name FROM command_registry ORDER BY cmd_name")
    all_cmds = {row[1]: row[0] for row in c.fetchall()}
    
    # Get commands WITH handlers
    c.execute("""
        SELECT DISTINCT cr.cmd_name 
        FROM command_registry cr
        JOIN command_handlers ch ON cr.cmd_id = ch.cmd_id
        WHERE ch.enabled = 1
        ORDER BY cr.cmd_name
    """)
    with_handlers = set(row[0] for row in c.fetchall())
    
    # Get commands WITHOUT handlers
    missing = set(all_cmds.keys()) - with_handlers
    
    # Get duplicate definitions (same name, different patches)
    c.execute("""
        SELECT cmd_name, COUNT(*) as cnt
        FROM command_registry
        GROUP BY cmd_name
        HAVING cnt > 1
    """)
    duplicates = {row[0]: row[1] for row in c.fetchall()}
    
    with open(OUTPUT, 'w') as f:
        f.write("╔═══════════════════════════════════════════════════════════════╗\n")
        f.write("║        QUNIX COMMAND HANDLER DIAGNOSTIC REPORT                ║\n")
        f.write("╚═══════════════════════════════════════════════════════════════╝\n\n")
        
        f.write(f"Total Commands in Registry: {len(all_cmds)}\n")
        f.write(f"Commands WITH Handlers:     {len(with_handlers)}\n")
        f.write(f"Commands WITHOUT Handlers:  {len(missing)}\n\n")
        
        f.write("=" * 60 + "\n")
        f.write("MISSING HANDLERS (30 commands):\n")
        f.write("=" * 60 + "\n")
        for i, cmd in enumerate(sorted(missing), 1):
            cmd_id = all_cmds[cmd]
            f.write(f"{i:3}. {cmd:20} (cmd_id={cmd_id})\n")
        
        f.write("\n" + "=" * 60 + "\n")
        f.write("DUPLICATE DEFINITIONS:\n")
        f.write("=" * 60 + "\n")
        if duplicates:
            for cmd, count in sorted(duplicates.items()):
                f.write(f"  {cmd}: {count} definitions\n")
        else:
            f.write("  None found\n")
        
        f.write("\n" + "=" * 60 + "\n")
        f.write("COMMANDS BY CATEGORY:\n")
        f.write("=" * 60 + "\n")
        c.execute("""
            SELECT cmd_category, COUNT(*) as total,
                   SUM(CASE WHEN cmd_id IN (SELECT cmd_id FROM command_handlers WHERE enabled=1) THEN 1 ELSE 0 END) as with_handler
            FROM command_registry
            GROUP BY cmd_category
            ORDER BY cmd_category
        """)
        for cat, total, with_h in c.fetchall():
            missing_cat = total - with_h
            f.write(f"  {cat:15} {total:3} total | {with_h:3} handlers | {missing_cat:3} missing\n")
    
    conn.close()
    print(f"✓ Diagnostic written to: {OUTPUT}")
    return sorted(missing)

if __name__ == '__main__':
    missing_list = analyze_commands()
    print("\nMissing handlers:")
    for cmd in missing_list:
        print(f"  - {cmd}")