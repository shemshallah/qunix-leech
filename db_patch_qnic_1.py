
#!/usr/bin/env python3
"""
QUNIX QNIC Tables Patch - Direct Database Creation
Run this BEFORE starting Flask to ensure QNIC tables exist
"""

import sqlite3
import sys
from pathlib import Path

QNIC_TABLES_PATCH = """
-- ═══════════════════════════════════════════════════════════════════════════
-- QNIC TABLES PATCH - Creates all QNIC tables
-- ═══════════════════════════════════════════════════════════════════════════

-- Traffic interception log
CREATE TABLE IF NOT EXISTS qnic_traffic_log (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    client_ip TEXT,
    client_port INTEGER,
    method TEXT,
    url TEXT,
    host TEXT,
    path TEXT,
    headers_json TEXT,
    
    -- Quantum routing
    quantum_route_json TEXT,
    lattice_points_used INTEGER,
    epr_pairs_used INTEGER,
    triangles_used INTEGER,
    routing_strategy TEXT,
    routing_cost_sigma REAL,
    
    -- Response
    response_status INTEGER,
    response_size INTEGER,
    response_headers_json TEXT,
    
    -- Performance
    latency_ms REAL,
    quantum_latency_ms REAL,
    classical_latency_estimate_ms REAL,
    quantum_advantage REAL,
    
    -- Proof
    proof_hash BLOB,
    proof_signature BLOB,
    merkle_root BLOB,
    verified INTEGER DEFAULT 1,
    
    created_at REAL
);

CREATE INDEX IF NOT EXISTS idx_traffic_timestamp ON qnic_traffic_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_traffic_host ON qnic_traffic_log(host);
CREATE INDEX IF NOT EXISTS idx_traffic_status ON qnic_traffic_log(response_status);

-- Real-time metrics (updated continuously)
CREATE TABLE IF NOT EXISTS qnic_metrics_realtime (
    metric_name TEXT PRIMARY KEY,
    metric_value REAL,
    metric_unit TEXT,
    last_updated REAL
) WITHOUT ROWID;

-- Domain statistics
CREATE TABLE IF NOT EXISTS qnic_domain_stats (
    domain TEXT PRIMARY KEY,
    request_count INTEGER DEFAULT 0,
    bytes_sent INTEGER DEFAULT 0,
    bytes_received INTEGER DEFAULT 0,
    avg_latency_ms REAL,
    quantum_routes_used INTEGER DEFAULT 0,
    last_request REAL,
    created_at REAL
) WITHOUT ROWID;

-- Active connections tracking
CREATE TABLE IF NOT EXISTS qnic_active_connections (
    conn_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_ip TEXT,
    client_port INTEGER,
    dest_host TEXT,
    dest_port INTEGER,
    state TEXT,
    quantum_path TEXT,
    bytes_sent INTEGER DEFAULT 0,
    bytes_received INTEGER DEFAULT 0,
    established_at REAL,
    last_activity REAL
);

-- Initialize metrics with default values
INSERT OR REPLACE INTO qnic_metrics_realtime VALUES
    ('total_requests', 0, 'count', 0);
INSERT OR REPLACE INTO qnic_metrics_realtime VALUES
    ('total_bytes_sent', 0, 'bytes', 0);
INSERT OR REPLACE INTO qnic_metrics_realtime VALUES
    ('total_bytes_received', 0, 'bytes', 0);
INSERT OR REPLACE INTO qnic_metrics_realtime VALUES
    ('active_connections', 0, 'count', 0);
INSERT OR REPLACE INTO qnic_metrics_realtime VALUES
    ('avg_latency_ms', 0, 'milliseconds', 0);
INSERT OR REPLACE INTO qnic_metrics_realtime VALUES
    ('quantum_advantage_avg', 0, 'ratio', 0);
INSERT OR REPLACE INTO qnic_metrics_realtime VALUES
    ('cache_hit_rate', 0, 'percent', 0);
INSERT OR REPLACE INTO qnic_metrics_realtime VALUES
    ('uptime_seconds', 0, 'seconds', 0);
INSERT OR REPLACE INTO qnic_metrics_realtime VALUES
    ('http_requests', 0, 'count', 0);
INSERT OR REPLACE INTO qnic_metrics_realtime VALUES
    ('https_tunnels', 0, 'count', 0);
INSERT OR REPLACE INTO qnic_metrics_realtime VALUES
    ('fallback_routes', 0, 'count', 0);
"""

def find_database():
    """Find QUNIX database"""
    locations = [
        Path('/data/qunix_leech.db'),
        Path('/home/Shemshallah/qunix_leech.db'),
        Path('/home/Shemshallah/mysite/qunix_leech.db'),
        Path.home() / 'qunix_leech.db',
        Path.cwd() / 'qunix_leech.db',
    ]
    
    for loc in locations:
        if loc.exists():
            return loc
    return None

def apply_qnic_patch(db_path: Path):
    """Apply QNIC tables patch"""
    print(f"\n╔══════════════════════════════════════════════════════════════╗")
    print(f"║         QUNIX QNIC TABLES PATCH v1.0                         ║")
    print(f"╚══════════════════════════════════════════════════════════════╝\n")
    
    print(f"Database: {db_path}")
    
    # Connect
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    
    print(f"\nApplying QNIC tables patch...")
    
    try:
        # Apply patch
        conn.executescript(QNIC_TABLES_PATCH)
        conn.commit()
        
        # Verify tables exist
        c = conn.cursor()
        
        print(f"\n✓ Verifying tables:")
        
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='qnic_traffic_log'")
        if c.fetchone():
            c.execute("SELECT COUNT(*) FROM qnic_traffic_log")
            count = c.fetchone()[0]
            print(f"  ✓ qnic_traffic_log ({count} rows)")
        else:
            print(f"  ✗ qnic_traffic_log MISSING")
            return False
        
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='qnic_metrics_realtime'")
        if c.fetchone():
            c.execute("SELECT COUNT(*) FROM qnic_metrics_realtime")
            count = c.fetchone()[0]
            print(f"  ✓ qnic_metrics_realtime ({count} metrics)")
        else:
            print(f"  ✗ qnic_metrics_realtime MISSING")
            return False
        
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='qnic_domain_stats'")
        if c.fetchone():
            print(f"  ✓ qnic_domain_stats")
        else:
            print(f"  ✗ qnic_domain_stats MISSING")
            return False
        
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='qnic_active_connections'")
        if c.fetchone():
            print(f"  ✓ qnic_active_connections")
        else:
            print(f"  ✗ qnic_active_connections MISSING")
            return False
        
        # Verify metrics initialized
        print(f"\n✓ Verifying metrics initialization:")
        c.execute("SELECT metric_name, metric_value FROM qnic_metrics_realtime ORDER BY metric_name")
        for row in c.fetchall():
            print(f"  • {row[0]}: {row[1]}")
        
        conn.close()
        
        print(f"\n╔══════════════════════════════════════════════════════════════╗")
        print(f"║  ✓ QNIC TABLES PATCH APPLIED SUCCESSFULLY                    ║")
        print(f"╚══════════════════════════════════════════════════════════════╝\n")
        print(f"You can now start Flask: python flask_app.py\n")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Patch failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])
    else:
        db_path = find_database()
        if not db_path:
            print("\n✗ Database not found!")
            print("\nUsage: python patch_qnic_tables.py [database_path]")
            print("\nOr place qunix_leech.db in one of these locations:")
            print("  /data/qunix_leech.db")
            print("  /home/Shemshallah/qunix_leech.db")
            print("  /home/Shemshallah/mysite/qunix_leech.db")
            print("  ~/qunix_leech.db")
            print("  ./qunix_leech.db\n")
            return 1
    
    if not db_path.exists():
        print(f"\n✗ Database not found: {db_path}\n")
        return 1
    
    success = apply_qnic_patch(db_path)
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
