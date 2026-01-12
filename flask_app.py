#!/usr/bin/env python3
"""
flask_app.py v18.1.0 - CPU STARTUP FIXED + KEEP-ALIVE

Key fixes:
1. Better CPU process management with health checks
2. Keep-alive system to monitor CPU status
3. Auto-restart CPU if it crashes
4. Packet cleanup on startup
5. Better error handling and logging
"""

import os
import sys
import time
import threading
import secrets
import sqlite3
import functools
import traceback
import atexit
import subprocess
import signal
from pathlib import Path
from flask import Flask, jsonify, request, send_file, send_from_directory
from typing import Optional, Dict, Any

VERSION = "18.1.0-CPU-FIXED"

app = Flask(__name__, static_url_path='/static')
application = app

# ═══════════════════════════════════════════════════════════════════════════
# GLOBAL STATE
# ═══════════════════════════════════════════════════════════════════════════

_initialized = False
_init_attempted = False
_init_error = None
_init_lock = threading.RLock()
_db_path = None
_db_executor = None
_quantum_worker = None
_quantum_bus = None
_executor = None

# CPU Management
_cpu_process = None
_cpu_monitor_thread = None
_cpu_should_run = False
_cpu_health_thread = None
_cpu_start_attempts = 0
_cpu_last_seen = 0
_cpu_restart_cooldown = 5.0

_metrics = {
    'commands_sent': 0,
    'results_received': 0,
    'timeouts': 0,
    'quantum_ops': 0,
    'chsh_violations': 0,
    'avg_chsh': 0.0,
    'bus_status': 'unknown',
    'cpu_status': 'offline',
    'cpu_restarts': 0,
    'packets_cleaned': 0
}
_metrics_lock = threading.Lock()


def _log(msg):
    """Safe logging"""
    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        sys.stderr.write(f"[{timestamp}] [FLASK] {msg}\n")
        sys.stderr.flush()
    except:
        pass


def create_optimized_connection(db_path: Path, timeout: float = 30.0):
    """Create optimized connection"""
    conn = sqlite3.connect(str(db_path), timeout=timeout, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def retry_on_lock(max_retries: int = 5, initial_delay: float = 0.1):
    """Decorator for retry on lock"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import random
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "locked" in str(e).lower() or "busy" in str(e).lower():
                        last_exception = e
                        if attempt < max_retries - 1:
                            delay = initial_delay * (2 ** attempt)
                            jitter = random.uniform(0, delay * 0.1)
                            time.sleep(delay + jitter)
                            continue
                    raise
                except Exception:
                    raise
            raise last_exception or Exception("Retry limit exceeded")
        return wrapper
    return decorator


class SafeDatabaseExecutor:
    """Thread-safe database executor"""
    def __init__(self, db_path: Path, pool_size: int = 10):
        self.db_path = db_path
        self.connections = []
        self.available = []
        self.lock = threading.Lock()
        _log(f"Creating connection pool (size={pool_size})...")
        for i in range(pool_size):
            try:
                conn = create_optimized_connection(db_path)
                self.connections.append(conn)
                self.available.append(conn)
            except Exception as e:
                _log(f"Failed connection {i}: {e}")
        _log(f"✓ Pool ready ({len(self.available)} connections)")
    
    @retry_on_lock(max_retries=3)
    def execute(self, sql: str, params: tuple = (), timeout: float = 5.0):
        conn = self._acquire_connection(timeout)
        try:
            cursor = conn.execute(sql, params)
            return cursor.fetchall()
        finally:
            self._release_connection(conn)
    
    @retry_on_lock(max_retries=3)
    def execute_write(self, sql: str, params: tuple = (), timeout: float = 5.0) -> int:
        conn = self._acquire_connection(timeout)
        try:
            cursor = conn.execute(sql, params)
            return cursor.lastrowid
        finally:
            self._release_connection(conn)
    
    def executescript(self, script: str, timeout: float = 10.0):
        conn = self._acquire_connection(timeout)
        try:
            conn.executescript(script)
        finally:
            self._release_connection(conn)
    
    def _acquire_connection(self, timeout: float):
        start = time.time()
        while (time.time() - start) < timeout:
            with self.lock:
                if self.available:
                    return self.available.pop()
            time.sleep(0.01)
        raise TimeoutError("Connection pool exhausted")
    
    def _release_connection(self, conn):
        with self.lock:
            if conn not in self.available:
                self.available.append(conn)
    
    def close_all(self):
        with self.lock:
            for conn in self.connections:
                try:
                    conn.close()
                except:
                    pass
            self.connections.clear()
            self.available.clear()


def _find_database():
    """Find QUNIX database"""
    locations = [
        Path('/home/Shemshallah/qunix_leech.db'),
        Path('/home/Shemshallah/mysite/qunix_leech.db'),
        Path('/data/qunix_leech.db'),
        Path.home() / 'qunix_leech.db',
        Path.cwd() / 'qunix_leech.db',
    ]
    for loc in locations:
        try:
            if loc.exists():
                _log(f"Found database at: {loc}")
                return loc
        except Exception as e:
            _log(f"Error checking {loc}: {e}")
    _log("ERROR: No database found")
    return None


# ═══════════════════════════════════════════════════════════════════════════
# PACKET CLEANUP
# ═══════════════════════════════════════════════════════════════════════════

def _cleanup_stuck_packets():
    """Clean up stuck packets on startup"""
    global _db_executor
    if not _db_executor:
        return 0
    
    try:
        _log("Cleaning stuck packets...")
        
        # Get count before cleanup
        rows = _db_executor.execute("SELECT COUNT(*) as c FROM quantum_ipc WHERE processed = 0")
        stuck_count = rows[0]['c'] if rows else 0
        
        if stuck_count > 0:
            _log(f"Found {stuck_count} stuck packets")
            
            # Mark old unprocessed packets as processed (older than 60 seconds)
            cutoff = time.time() - 60.0
            _db_executor.execute_write(
                "UPDATE quantum_ipc SET processed = 1 WHERE processed = 0 AND timestamp < ?",
                (cutoff,)
            )
            
            with _metrics_lock:
                _metrics['packets_cleaned'] = stuck_count
            
            _log(f"✓ Cleaned {stuck_count} stuck packets")
        
        return stuck_count
        
    except Exception as e:
        _log(f"Packet cleanup error: {e}")
        return 0


# ═══════════════════════════════════════════════════════════════════════════
# CPU PROCESS MANAGEMENT - IMPROVED
# ═══════════════════════════════════════════════════════════════════════════

def _find_cpu_script():
    """Find qunix_cpu.py"""
    locations = [
        Path(__file__).parent / 'qunix_cpu.py',
        Path('/home/Shemshallah/mysite/qunix_cpu.py'),
        Path('/home/Shemshallah/qunix_cpu.py'),
        Path.cwd() / 'qunix_cpu.py',
    ]
    for loc in locations:
        if loc.exists():
            _log(f"Found CPU script: {loc}")
            return loc
    return None


def _check_cpu_health() -> bool:
    """Check if CPU is responding"""
    global _db_executor, _cpu_last_seen, _cpu_in_process_running
    
    if not _db_executor:
        return False
    
    # If running in-process, check the flag
    if _cpu_in_process_running:
        return True
    
    try:
        # Check if CPU has processed anything recently (last 30 seconds)
        cutoff = time.time() - 30.0
        rows = _db_executor.execute("""
            SELECT COUNT(*) as c FROM quantum_ipc 
            WHERE sender = 'QUNIX_CPU' 
            AND timestamp > ?
        """, (cutoff,))
        
        recent_activity = rows[0]['c'] if rows else 0
        
        if recent_activity > 0:
            _cpu_last_seen = time.time()
            return True
        
        # Check if CPU process is still running
        if _cpu_process and _cpu_process.poll() is None:
            # Process running but no activity - might be stuck
            if (time.time() - _cpu_last_seen) > 60.0:
                _log("⚠ CPU process alive but no activity for 60s")
                return False
            return True
        
        return False
        
    except Exception as e:
        _log(f"CPU health check error: {e}")
        return False


def _find_python_executable():
    """Find actual Python executable (not uwsgi)"""
    # Try various Python executables
    candidates = [
        'python3',
        'python',
        '/usr/bin/python3',
        '/usr/bin/python',
        '/usr/local/bin/python3',
        '/usr/local/bin/python',
    ]
    
    import shutil
    for candidate in candidates:
        python_path = shutil.which(candidate)
        if python_path:
            _log(f"Found Python: {python_path}")
            return python_path
    
    # Last resort - try sys.executable if it's actually python
    if 'python' in sys.executable.lower():
        return sys.executable
    
    _log("ERROR: No Python executable found")
    return None


def _start_cpu_process() -> bool:
    """Start CPU process with better error handling"""
    global _cpu_process, _cpu_should_run, _cpu_start_attempts, _cpu_last_seen
    
    try:
        # Find CPU script
        cpu_script = _find_cpu_script()
        if not cpu_script:
            _log("⚠ qunix_cpu.py not found")
            with _metrics_lock:
                _metrics['cpu_status'] = 'not_found'
            return False
        
        # Find Python executable
        python_exe = _find_python_executable()
        if not python_exe:
            _log("⚠ Python executable not found")
            with _metrics_lock:
                _metrics['cpu_status'] = 'no_python'
            return False
        
        # Clean up any stuck packets first
        _cleanup_stuck_packets()
        
        # Check if already running
        if _cpu_process and _cpu_process.poll() is None:
            _log("CPU already running")
            return True
        
        _cpu_start_attempts += 1
        _log(f"Starting CPU (attempt {_cpu_start_attempts})")
        _log(f"  Python: {python_exe}")
        _log(f"  Script: {cpu_script}")
        _log(f"  DB: {_db_path}")
        
        # Start CPU process
        _cpu_process = subprocess.Popen(
            [python_exe, str(cpu_script), '--db', str(_db_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            start_new_session=True  # Create new process group
        )
        
        _log(f"✓ CPU started (PID: {_cpu_process.pid})")
        _cpu_last_seen = time.time()
        
        # Wait for CPU to initialize
        time.sleep(3.0)
        
        # Check if it's still running
        if _cpu_process.poll() is None:
            _log("✓ CPU confirmed running")
            with _metrics_lock:
                _metrics['cpu_status'] = 'online'
            return True
        else:
            exit_code = _cpu_process.returncode
            _log(f"⚠ CPU exited immediately (code: {exit_code})")
            
            # Try to read stderr
            try:
                stderr = _cpu_process.stderr.read()
                if stderr:
                    _log(f"CPU stderr: {stderr[:500]}")
            except:
                pass
            
            with _metrics_lock:
                _metrics['cpu_status'] = 'crashed'
            
            # Try in-process fallback
            _log("⚠ Attempting in-process CPU fallback...")
            return _start_cpu_in_process()
            
    except Exception as e:
        _log(f"ERROR: CPU start failed: {e}")
        _log(traceback.format_exc())
        with _metrics_lock:
            _metrics['cpu_status'] = 'error'
        
        # Try in-process fallback
        _log("⚠ Attempting in-process CPU fallback...")
        return _start_cpu_in_process()


_cpu_thread = None
_cpu_in_process_running = False

def _start_cpu_in_process() -> bool:
    """
    Fallback: Run CPU in a thread instead of subprocess
    This works when subprocess fails (uwsgi environment)
    """
    global _cpu_thread, _cpu_in_process_running, _cpu_should_run
    
    try:
        if _cpu_in_process_running:
            _log("CPU already running in-process")
            return True
        
        _log("Starting CPU in-process (thread mode)...")
        
        # Import CPU components
        cpu_script = _find_cpu_script()
        if not cpu_script:
            _log("ERROR: CPU script not found for in-process mode")
            return False
        
        # Add CPU directory to path
        cpu_dir = cpu_script.parent
        if str(cpu_dir) not in sys.path:
            sys.path.insert(0, str(cpu_dir))
        
        # Import and run CPU in thread
        def _run_cpu_thread():
            global _cpu_in_process_running
            try:
                _log("CPU thread starting...")
                _cpu_in_process_running = True
                
                # Import CPU module
                import qunix_cpu
                
                # Create CPU instance
                cpu = qunix_cpu.QuantumCPUCore(_db_path)
                
                # Run CPU loop
                cpu.run()
                
            except Exception as e:
                _log(f"CPU thread error: {e}")
                _log(traceback.format_exc())
            finally:
                _cpu_in_process_running = False
                _log("CPU thread stopped")
        
        _cpu_thread = threading.Thread(target=_run_cpu_thread, daemon=True)
        _cpu_thread.start()
        _cpu_should_run = True
        
        # Wait a bit for startup
        time.sleep(2.0)
        
        if _cpu_in_process_running:
            _log("✓ CPU running in-process mode")
            with _metrics_lock:
                _metrics['cpu_status'] = 'online_inprocess'
            return True
        else:
            _log("✗ CPU in-process mode failed to start")
            return False
        
    except Exception as e:
        _log(f"ERROR: In-process CPU failed: {e}")
        _log(traceback.format_exc())
        return False


def _stop_cpu_process():
    """Stop CPU process"""
    global _cpu_process, _cpu_should_run
    
    if not _cpu_process:
        return
    
    _log("Stopping CPU...")
    _cpu_should_run = False
    
    try:
        # Try graceful shutdown first
        _cpu_process.terminate()
        
        try:
            _cpu_process.wait(timeout=5.0)
            _log("✓ CPU stopped gracefully")
        except subprocess.TimeoutExpired:
            _log("CPU didn't stop, killing...")
            _cpu_process.kill()
            _cpu_process.wait(timeout=2.0)
            _log("✓ CPU killed")
            
    except Exception as e:
        _log(f"Error stopping CPU: {e}")
    finally:
        _cpu_process = None
        with _metrics_lock:
            _metrics['cpu_status'] = 'offline'


def _monitor_cpu_process():
    """Monitor CPU process and output"""
    global _cpu_process, _cpu_should_run
    
    _log("CPU monitor started")
    
    try:
        while _cpu_should_run and _cpu_process:
            # Check if process exited
            if _cpu_process.poll() is not None:
                exit_code = _cpu_process.returncode
                _log(f"⚠ CPU exited (code: {exit_code})")
                
                # Read any remaining output
                try:
                    stdout = _cpu_process.stdout.read()
                    stderr = _cpu_process.stderr.read()
                    if stdout:
                        _log(f"CPU stdout: {stdout[:200]}")
                    if stderr:
                        _log(f"CPU stderr: {stderr[:200]}")
                except:
                    pass
                
                with _metrics_lock:
                    _metrics['cpu_status'] = 'crashed'
                
                break
            
            # Read output without blocking
            try:
                import select
                if hasattr(select, 'select'):
                    # Unix-like systems
                    readable, _, _ = select.select([_cpu_process.stdout], [], [], 0.1)
                    if readable:
                        line = _cpu_process.stdout.readline()
                        if line:
                            _log(f"CPU: {line.rstrip()}")
            except:
                pass
            
            time.sleep(0.5)
            
    except Exception as e:
        _log(f"CPU monitor error: {e}")
    finally:
        _log("CPU monitor stopped")


def _cpu_health_monitor():
    """Health monitor with auto-restart"""
    global _cpu_should_run, _cpu_process, _cpu_restart_cooldown
    
    _log("CPU health monitor started")
    last_restart = 0
    
    try:
        while _cpu_should_run:
            time.sleep(10.0)  # Check every 10 seconds
            
            if not _cpu_should_run:
                break
            
            # Check CPU health
            is_healthy = _check_cpu_health()
            
            if not is_healthy:
                _log("⚠ CPU unhealthy or crashed")
                
                # Check cooldown
                if (time.time() - last_restart) < _cpu_restart_cooldown:
                    _log(f"Waiting for cooldown ({_cpu_restart_cooldown}s)")
                    continue
                
                # Stop old process if exists
                if _cpu_process:
                    _log("Stopping crashed CPU...")
                    try:
                        _cpu_process.kill()
                        _cpu_process.wait(timeout=2.0)
                    except:
                        pass
                    _cpu_process = None
                
                # Attempt restart
                _log("Attempting CPU restart...")
                with _metrics_lock:
                    _metrics['cpu_restarts'] += 1
                
                if _start_cpu_process():
                    _log("✓ CPU restarted successfully")
                    last_restart = time.time()
                    
                    # Start new monitor thread
                    monitor = threading.Thread(target=_monitor_cpu_process, daemon=True)
                    monitor.start()
                else:
                    _log("✗ CPU restart failed")
                    # Increase cooldown on failure
                    _cpu_restart_cooldown = min(_cpu_restart_cooldown * 1.5, 60.0)
            else:
                # Reset cooldown on success
                _cpu_restart_cooldown = 5.0
                
    except Exception as e:
        _log(f"Health monitor error: {e}")
    finally:
        _log("CPU health monitor stopped")


# ═══════════════════════════════════════════════════════════════════════════
# INITIALIZATION - SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

TERMINAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS terminal_sessions (
    session_id TEXT PRIMARY KEY,
    status TEXT,
    created REAL,
    last_activity REAL
);

CREATE TABLE IF NOT EXISTS terminal_output (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    data TEXT,
    ts REAL
);

CREATE INDEX IF NOT EXISTS idx_terminal_output_session ON terminal_output(session_id, id);
"""

QUANTUM_CHANNEL_SCHEMA = """
-- Quantum IPC table for CPU communication
CREATE TABLE IF NOT EXISTS quantum_ipc (
    packet_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT NOT NULL,
    direction TEXT NOT NULL,
    data BLOB,
    data_size INTEGER DEFAULT 0,
    chsh_value REAL DEFAULT 2.0,
    timestamp REAL,
    processed INTEGER DEFAULT 0
);

-- CPU qubit allocator (required by CPU)
CREATE TABLE IF NOT EXISTS cpu_qubit_allocator (
    qubit_id INTEGER PRIMARY KEY,
    allocated INTEGER DEFAULT 0,
    allocated_to TEXT,
    allocated_at REAL
);

-- Initialize some qubits if empty
INSERT OR IGNORE INTO cpu_qubit_allocator (qubit_id, allocated)
SELECT seq, 0 FROM 
    (WITH RECURSIVE cnt(x) AS (
        SELECT 0 UNION ALL SELECT x+1 FROM cnt LIMIT 1000
    ) SELECT x as seq FROM cnt);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_quantum_ipc_direction ON quantum_ipc(direction, processed);
CREATE INDEX IF NOT EXISTS idx_quantum_ipc_processed ON quantum_ipc(processed);
CREATE INDEX IF NOT EXISTS idx_quantum_ipc_timestamp ON quantum_ipc(timestamp);
CREATE INDEX IF NOT EXISTS idx_cpu_qubit_alloc ON cpu_qubit_allocator(allocated);
"""


def _initialize_terminal_tables():
    global _db_executor
    try:
        _db_executor.executescript(TERMINAL_SCHEMA)
        _log("✓ Terminal tables initialized")
        return True
    except Exception as e:
        _log(f"ERROR: Terminal tables init failed: {e}")
        return False


def _initialize_quantum_channel():
    """Initialize quantum channel schema required by CPU"""
    global _db_executor
    try:
        _log("Initializing quantum channel schema...")
        _db_executor.executescript(QUANTUM_CHANNEL_SCHEMA)
        
        # Verify tables exist
        rows = _db_executor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('quantum_ipc', 'cpu_qubit_allocator')"
        )
        tables = [r['name'] for r in rows]
        
        if 'quantum_ipc' not in tables:
            _log("ERROR: quantum_ipc table not created")
            return False
        
        if 'cpu_qubit_allocator' not in tables:
            _log("ERROR: cpu_qubit_allocator table not created")
            return False
        
        # Check qubit count
        rows = _db_executor.execute("SELECT COUNT(*) as c FROM cpu_qubit_allocator")
        qubit_count = rows[0]['c'] if rows else 0
        
        _log(f"✓ Quantum channel schema ready ({qubit_count} qubits allocated)")
        return True
        
    except Exception as e:
        _log(f"ERROR: Quantum channel init failed: {e}")
        _log(traceback.format_exc())
        return False


def _ensure_static_directory():
    """Ensure static directory exists with xterm files"""
    static_dir = Path(__file__).parent / 'static'
    static_dir.mkdir(exist_ok=True)
    (static_dir / 'css').mkdir(exist_ok=True)
    (static_dir / 'js').mkdir(exist_ok=True)
    
    # Create xterm.css (abbreviated for space)
    css_file = static_dir / 'css' / 'xterm.css'
    if not css_file.exists():
        css_file.write_text(""".terminal { font-family: 'Courier New', courier, monospace; font-size: 14px; position: relative; }""")
    
    # Create minimal xterm.js (from previous working version)
    js_file = static_dir / 'js' / 'xterm.js'
    if not js_file.exists():
        # Use the working implementation from the provided code
        js_file.write_text("""(function() { window.Terminal = class Terminal { constructor(options) { this.options = options || {}; this.element = null; this._onDataHandlers = []; } open(parent) { this.element = document.createElement('div'); this.element.className = 'terminal'; this.element.style.height = '100%'; parent.appendChild(this.element); } write(text) { if (this.element) this.element.innerHTML += text.replace(/\\r\\n/g, '<br>'); } onData(handler) { this._onDataHandlers.push(handler); } focus() {} }; })();""")
    
    _log(f"✓ Static files ensured")
    return static_dir


# ═══════════════════════════════════════════════════════════════════════════
# COMPONENT INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════

def _init_quantum_link() -> bool:
    global _quantum_worker
    try:
        from qunix_link import BellPairPoolManager
        _quantum_worker = BellPairPoolManager(_db_path)
        _log("✓ BellPairPoolManager created")
        return True
    except ImportError as e:
        _log(f"⚠ qunix_link not available: {e}")
        _quantum_worker = None
        return True
    except Exception as e:
        _log(f"ERROR: Quantum link init failed: {e}")
        return False


def _init_quantum_bus() -> bool:
    global _quantum_bus
    try:
        from quantum_mega_bus import QuantumMegaBus
        _quantum_bus = QuantumMegaBus(_db_path)
        _quantum_bus.start()
        _log("✓ QuantumMegaBus initialized")
        with _metrics_lock:
            _metrics['bus_status'] = 'online'
        return True
    except ImportError as e:
        _log(f"⚠ quantum_mega_bus not available: {e}")
        _quantum_bus = None
        return True
    except Exception as e:
        _log(f"ERROR: Quantum Bus init failed: {e}")
        return False


def _init_executor() -> bool:
    global _executor
    if _quantum_bus:
        _executor = _quantum_bus
        _log("✓ Using QuantumMegaBus as executor")
        return True
    
    _log("ERROR: No executor available")
    return False


def _init_cpu_with_monitoring() -> bool:
    """Initialize CPU with monitoring threads"""
    global _cpu_should_run, _cpu_monitor_thread, _cpu_health_thread
    
    _cpu_should_run = True
    
    # Start CPU process
    if not _start_cpu_process():
        _log("⚠ CPU failed to start")
        return False
    
    # Start monitor thread for output
    _cpu_monitor_thread = threading.Thread(target=_monitor_cpu_process, daemon=True)
    _cpu_monitor_thread.start()
    
    # Start health monitor thread
    _cpu_health_thread = threading.Thread(target=_cpu_health_monitor, daemon=True)
    _cpu_health_thread.start()
    
    _log("✓ CPU monitoring started")
    return True


# ═══════════════════════════════════════════════════════════════════════════
# MAIN INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════

def _init_system():
    global _initialized, _init_attempted, _init_error, _db_path, _db_executor
    
    if _initialized:
        return True
    
    with _init_lock:
        if _initialized:
            return True
        
        if _init_attempted:
            return _init_error is None
        
        _init_attempted = True
        
        # Skip if reloader parent
        werkzeug_main = os.environ.get('WERKZEUG_RUN_MAIN')
        if werkzeug_main is not None and werkzeug_main != 'true':
            _log("Skipping init (reloader parent)")
            _init_attempted = False
            return True
        
        _log("=" * 70)
        _log(f"FLASK INIT v{VERSION}")
        _log("=" * 70)
        
        try:
            _log("[1/9] Finding database...")
            _db_path = _find_database()
            if not _db_path:
                _init_error = "Database not found"
                return False
            
            _db_executor = SafeDatabaseExecutor(_db_path, pool_size=10)
            
            _log("[2/9] Static files...")
            _ensure_static_directory()
            
            _log("[3/9] Terminal tables...")
            if not _initialize_terminal_tables():
                _init_error = "Terminal tables failed"
                return False
            
            _log("[4/9] Quantum channel schema...")
            if not _initialize_quantum_channel():
                _init_error = "Quantum channel schema failed"
                return False
            
            _log("[5/9] Cleaning stuck packets...")
            _cleanup_stuck_packets()
            
            _log("[6/9] Quantum Link...")
            _init_quantum_link()
            
            _log("[7/9] Quantum Bus...")
            if not _init_quantum_bus():
                _init_error = "Quantum Bus failed"
                return False
            
            _log("[8/9] Executor...")
            if not _init_executor():
                _init_error = "Executor failed"
                return False
            
            _log("[9/9] CPU Process + Monitoring...")
            _init_cpu_with_monitoring()  # Don't fail if CPU doesn't start
            
            _initialized = True
            _init_error = None
            _log("✓ SYSTEM READY")
            return True
            
        except Exception as e:
            _init_error = str(e)
            _log(f"FATAL: {e}")
            _log(traceback.format_exc())
            return False


# ═══════════════════════════════════════════════════════════════════════════
# FLASK ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@app.before_request
def ensure_initialized():
    werkzeug_main = os.environ.get('WERKZEUG_RUN_MAIN')
    if werkzeug_main and werkzeug_main != 'true':
        return None
    if not _initialized and not _init_attempted:
        if not _init_system():
            return jsonify({'error': _init_error or 'Init failed'}), 503


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    static_dir = Path(__file__).parent / 'static'
    if static_dir.exists():
        file_path = static_dir / filename
        if file_path.exists():
            return send_file(str(file_path))
    return "Not found", 404


@app.route('/api/terminal/start', methods=['POST'])
def api_terminal_start():
    if not _db_executor:
        return jsonify({'success': False, 'error': 'Not ready'}), 503
    try:
        session_id = secrets.token_hex(16)
        now = time.time()
        _db_executor.execute_write(
            'INSERT INTO terminal_sessions (session_id, status, created, last_activity) VALUES (?, ?, ?, ?)',
            (session_id, 'active', now, now)
        )
        
        cpu_status = _metrics['cpu_status']
        cpu_indicator = "🟢" if cpu_status == 'online' else "🔴"
        
        welcome = (
            "\033[38;5;201m" + "="*70 + "\033[0m\r\n"
            "\033[1m\033[38;5;213m     QUNIX QUANTUM OPERATING SYSTEM\033[0m\r\n"
            f"     v{VERSION}\r\n"
            "\033[38;5;201m" + "="*70 + "\033[0m\r\n"
            f"  Session: {session_id[:8]}...\r\n"
            f"  CPU: {cpu_indicator} {cpu_status}\r\n"
            "  Type '\033[38;5;87mhelp\033[0m' for commands\r\n"
            "\r\n\033[38;5;213mqunix>\033[0m "
        )
        _db_executor.execute_write(
            'INSERT INTO terminal_output (session_id, data, ts) VALUES (?, ?, ?)',
            (session_id, welcome, now)
        )
        return jsonify({'success': True, 'session_id': session_id})
    except Exception as e:
        _log(f"Terminal start error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/terminal/input', methods=['POST'])
def api_terminal_input():
    if not _executor or not _db_executor:
        return jsonify({'success': False, 'error': 'Not ready'}), 503
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        input_data = data.get('data', '').rstrip('\r\n').strip()
        
        _log(f"Input: [{input_data}]")
        
        if not input_data:
            output = "\r\n\033[38;5;213mqunix>\033[0m "
        else:
            try:
                result = _executor.execute_command(input_data, timeout=10.0)
                with _metrics_lock:
                    _metrics['commands_sent'] += 1
                    if result:
                        _metrics['results_received'] += 1
                    else:
                        _metrics['timeouts'] += 1
                
                if result:
                    output = f"\r\n{result}\r\n\033[38;5;213mqunix>\033[0m "
                else:
                    output = "\r\n\033[91mTimeout - CPU not responding\033[0m\r\n\033[38;5;213mqunix>\033[0m "
            except Exception as e:
                _log(f"Executor error: {e}")
                output = f"\r\n\033[91mError: {e}\033[0m\r\n\033[38;5;213mqunix>\033[0m "
        
        _db_executor.execute_write(
            'INSERT INTO terminal_output (session_id, data, ts) VALUES (?, ?, ?)',
            (session_id, output, time.time())
        )
        _db_executor.execute_write(
            'UPDATE terminal_sessions SET last_activity = ? WHERE session_id = ?',
            (time.time(), session_id)
        )
        return jsonify({'success': True})
    except Exception as e:
        _log(f"Terminal input error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/terminal/output/<session_id>')
def api_terminal_output(session_id):
    if not _db_executor:
        return jsonify({'data': []})
    try:
        last_id = request.args.get('last_id', 0, type=int)
        rows = _db_executor.execute(
            'SELECT id, data FROM terminal_output WHERE session_id = ? AND id > ? ORDER BY id LIMIT 50',
            (session_id, last_id)
        )
        return jsonify({'data': [{'id': r['id'], 'text': r['data']} for r in rows]})
    except Exception as e:
        _log(f"Output error: {e}")
        return jsonify({'data': []})


@app.route('/api/cpu/restart', methods=['POST'])
def api_cpu_restart():
    """Manual CPU restart endpoint"""
    if not _initialized:
        return jsonify({'success': False, 'error': 'Not initialized'}), 503
    
    try:
        _log("Manual CPU restart requested")
        
        # Stop existing CPU
        _stop_cpu_process()
        time.sleep(1.0)
        
        # Clean packets
        cleaned = _cleanup_stuck_packets()
        
        # Restart
        if _start_cpu_process():
            return jsonify({
                'success': True,
                'message': 'CPU restarted',
                'packets_cleaned': cleaned
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to restart CPU'
            }), 500
            
    except Exception as e:
        _log(f"CPU restart error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/health')
def health():
    with _metrics_lock:
        metrics_copy = _metrics.copy()
    
    # Check CPU health
    cpu_healthy = _check_cpu_health()
    if cpu_healthy and metrics_copy['cpu_status'] != 'online':
        with _metrics_lock:
            _metrics['cpu_status'] = 'online'
        metrics_copy['cpu_status'] = 'online'
    
    return jsonify({
        'status': 'healthy' if _initialized else 'initializing',
        'version': VERSION,
        'database': {
            'connected': _db_executor is not None,
            'path': str(_db_path) if _db_path else None
        },
        'cpu': {
            'status': metrics_copy['cpu_status'],
            'pid': _cpu_process.pid if _cpu_process else None,
            'running': _cpu_process.poll() is None if _cpu_process else False,
            'restarts': metrics_copy['cpu_restarts'],
            'start_attempts': _cpu_start_attempts
        },
        'metrics': metrics_copy,
        'timestamp': time.time()
    })


@app.route('/')
def index():
    """Main terminal UI"""
    return '''<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QUNIX Terminal</title>
<link rel="stylesheet" href="/static/css/xterm.css"/>
<script src="/static/js/xterm.js"></script>
<script src="/static/js/xterm-addon-fit.js"></script>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#000; font-family:monospace; overflow:hidden; color:#fff; height:100vh; display:flex; flex-direction:column; }
#header { background:linear-gradient(90deg,#1a0033,#4d0080); border-bottom:2px solid #cc00ff; padding:12px 20px; display:flex; justify-content:space-between; align-items:center; }
#logo { font-weight:bold; font-size:18px; color:#ff66ff; }
#status { color:#aaaaff; font-size:11px; display:flex; gap:15px; }
.status-item { display:flex; align-items:center; gap:5px; }
.status-dot { width:8px; height:8px; border-radius:50%; }
.status-online { background:#0f0; }
.status-offline { background:#f00; }
.status-unknown { background:#888; }
#terminal-container { flex:1; padding:10px; background:#000; }
#footer { background:#0a0014; border-top:1px solid #660099; padding:10px 20px; font-size:10px; color:#aaaaff; display:flex; justify-content:space-between; }
#footer a { color:#ff66ff; text-decoration:none; margin:0 8px; }
#footer a:hover { text-decoration:underline; }
</style>
</head><body>
<div id="header">
  <div id="logo">⚛ QUNIX v''' + VERSION + '''</div>
  <div id="status">
    <div class="status-item">
      <span class="status-dot status-unknown" id="bus-dot"></span>
      <span id="bus-status">Bus: ...</span>
    </div>
    <div class="status-item">
      <span class="status-dot status-unknown" id="cpu-dot"></span>
      <span id="cpu-status">CPU: ...</span>
    </div>
  </div>
</div>
<div id="terminal-container"></div>
<div id="footer">
  <div>
    <strong>APIs:</strong> 
    <a href="/health" target="_blank">/health</a>
    <a href="#" onclick="restartCPU(); return false;">/api/cpu/restart</a>
  </div>
  <div>Quantum Computing Interface | Auto-restart enabled</div>
</div>
<script>
const term = new Terminal({ 
  cursorBlink:true, 
  fontFamily:'"Courier New",monospace', 
  fontSize:13, 
  theme:{ background:'#000000', foreground:'#00ff00', cursor:'#ff00ff' }
});

term.open(document.getElementById('terminal-container'));

let sessionId = null;
let lastOutputId = 0;
let inputBuffer = '';
let ready = false;
let isProcessing = false;
let pollTimer = null;
let healthTimer = null;

async function startSession() {
  try {
    const r = await fetch('/api/terminal/start', { 
      method:'POST', 
      headers:{'Content-Type':'application/json'}, 
      body:'{}' 
    });
    const data = await r.json();
    
    if (!data.success) { 
      term.write('\\r\\n\\x1b[91mFailed to start\\x1b[0m\\r\\n'); 
      return; 
    }
    
    sessionId = data.session_id;
    
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(poll, 200);
    
    if (healthTimer) clearInterval(healthTimer);
    healthTimer = setInterval(updateHealth, 5000);
    updateHealth();
    
  } catch (e) { 
    term.write('\\r\\n\\x1b[91mError: ' + e.message + '\\x1b[0m\\r\\n'); 
  }
}

async function poll() {
  if (!sessionId) return;
  
  try {
    const r = await fetch(`/api/terminal/output/${sessionId}?last_id=${lastOutputId}`);
    const data = await r.json();
    
    if (data.data && data.data.length > 0) {
      data.data.forEach(item => {
        term.write(item.text);
        if (item.id > lastOutputId) lastOutputId = item.id;
        
        if (!ready && item.text.includes('qunix>')) {
          ready = true;
          setTimeout(() => term.focus(), 100);
        }
      });
    }
  } catch (e) {
    // Silent
  }
}

async function updateHealth() {
  try {
    const r = await fetch('/health');
    const data = await r.json();
    
    // Update bus status
    const busStatus = data.metrics?.bus_status || 'unknown';
    const busDot = document.getElementById('bus-dot');
    document.getElementById('bus-status').textContent = 'Bus: ' + busStatus;
    busDot.className = 'status-dot status-' + (busStatus === 'online' ? 'online' : 'offline');
    
    // Update CPU status
    const cpuStatus = data.cpu?.status || 'unknown';
    const cpuDot = document.getElementById('cpu-dot');
    document.getElementById('cpu-status').textContent = 'CPU: ' + cpuStatus;
    cpuDot.className = 'status-dot status-' + (cpuStatus === 'online' ? 'online' : 'offline');
    
  } catch (e) {
    // Silent
  }
}

async function sendInput(data) {
  if (!sessionId || !ready || isProcessing) return;
  
  isProcessing = true;
  
  try {
    await fetch('/api/terminal/input', { 
      method:'POST', 
      headers:{'Content-Type':'application/json'}, 
      body:JSON.stringify({session_id:sessionId, data:data}) 
    });
  } catch (e) { 
    term.write('\\r\\n\\x1b[91mError\\x1b[0m\\r\\n'); 
  } finally {
    isProcessing = false;
  }
}

async function restartCPU() {
  if (!confirm('Restart CPU process?')) return;
  
  term.write('\\r\\n\\x1b[93mRestarting CPU...\\x1b[0m\\r\\n');
  
  try {
    const r = await fetch('/api/cpu/restart', { method: 'POST' });
    const data = await r.json();
    
    if (data.success) {
      term.write('\\x1b[92m✓ CPU restarted\\x1b[0m\\r\\n');
      if (data.packets_cleaned > 0) {
        term.write(`  Cleaned ${data.packets_cleaned} stuck packets\\r\\n`);
      }
    } else {
      term.write('\\x1b[91m✗ Restart failed: ' + data.error + '\\x1b[0m\\r\\n');
    }
  } catch (e) {
    term.write('\\x1b[91m✗ Error: ' + e.message + '\\x1b[0m\\r\\n');
  }
  
  setTimeout(updateHealth, 1000);
}

term.onData(async (data) => {
  if (!sessionId || !ready || isProcessing) return;
  
  const code = data.charCodeAt(0);
  
  if (data === '\\r' || data === '\\n') {
    const cmd = inputBuffer.trim();
    term.write('\\r\\n');
    inputBuffer = '';
    await sendInput(cmd);
  } else if (data === '\\x7F' || data === '\\b') {
    if (inputBuffer.length > 0) { 
      inputBuffer = inputBuffer.slice(0, -1); 
      term.write('\\b \\b'); 
    }
  } else if (code === 3) {
    term.write('^C\\r\\n');
    inputBuffer = '';
    await sendInput('');
  } else if (code >= 32 && code < 127) {
    inputBuffer += data;
    term.write(data);
  }
});

window.addEventListener('beforeunload', () => {
  if (pollTimer) clearInterval(pollTimer);
  if (healthTimer) clearInterval(healthTimer);
});

startSession();
term.focus();
</script>
</body></html>'''


def shutdown_handler():
    """Clean shutdown"""
    global _quantum_worker, _quantum_bus, _db_executor, _cpu_should_run, _cpu_in_process_running
    
    _log("Shutting down...")
    
    # Stop CPU (both modes)
    _cpu_should_run = False
    _cpu_in_process_running = False
    _stop_cpu_process()
    
    # Stop quantum components
    if _quantum_worker:
        try:
            if hasattr(_quantum_worker, 'stop_maintenance'):
                _quantum_worker.stop_maintenance()
        except:
            pass
    
    if _quantum_bus:
        try:
            _quantum_bus.stop()
        except:
            pass
    
    # Close database
    if _db_executor:
        try:
            _db_executor.close_all()
        except:
            pass
    
    _log("✓ Shutdown complete")


atexit.register(shutdown_handler)


if __name__ == '__main__':
    print("=" * 70)
    print(f"  QUNIX v{VERSION}")
    print("  Terminal + Quantum Infrastructure + CPU Auto-Restart")
    print("=" * 70)
    print()
    print("Dashboard: http://localhost:5000")
    print("Health:    http://localhost:5000/health")
    print()
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True, use_reloader=True)