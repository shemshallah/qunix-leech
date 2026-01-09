
#!/usr/bin/env python3
"""
flask_app.py v9.5.1 - COMPLETE WITH TERMINAL + QNIC + FIX
All functionality included: Terminal, QNIC, Static files, Full UI
FIXED: QunixCommandProcessor initialization
"""

import os
import sys
import time
import threading
import secrets
import json
import sqlite3
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory, Response, send_file
from queue import Queue, Empty
from collections import defaultdict

VERSION = "9.5.1-COMPLETE-FIXED"

app = Flask(__name__, static_url_path='/static')
application = app

# ═══════════════════════════════════════════════════════════════════════════
# GLOBAL STATE
# ═══════════════════════════════════════════════════════════════════════════

_initialized = False
_init_attempted = False
_init_error = None
_init_lock = threading.RLock()
_engine = None
_processor = None
_conn = None
_qnic_interceptor = None
_qnic_running = False
_qnic_ready = threading.Event()
_qnic_error = None
_metrics_queue = Queue(maxsize=1000)
_db_path = None

def _log(msg):
    """Safe logging"""
    try:
        sys.stderr.write(f"[FLASK v{VERSION}] {msg}\n")
        sys.stderr.flush()
    except:
        pass

def _find_database():
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
            _log(f"Found database at: {loc}")
            return loc
    return None

def _ensure_static_directory():
    """Ensure static directory exists with xterm files"""
    static_dir = Path(__file__).parent / 'static'
    static_dir.mkdir(exist_ok=True)
    (static_dir / 'css').mkdir(exist_ok=True)
    (static_dir / 'js').mkdir(exist_ok=True)
    
    # Create minimal xterm.css
    css_file = static_dir / 'css' / 'xterm.css'
    if not css_file.exists():
        css_file.write_text("""
.terminal { font-family: courier-new, courier, monospace; font-size: 14px; }
.xterm-viewport { overflow-y: auto; }
""")
    
    # Create minimal xterm.js
    js_file = static_dir / 'js' / 'xterm.js'
    if not js_file.exists():
        js_file.write_text("""
window.Terminal = class Terminal {
    constructor(o) { this.options = o; }
    loadAddon(a) {}
    open(el) { this.element = el; }
    write(t) { if(this.element) this.element.innerHTML += t.replace(/\\r\\n/g,'<br>'); }
    onData(cb) { this.dataCallback = cb; }
    focus() {}
    clear() { if(this.element) this.element.innerHTML = ''; }
};
""")
    
    # Create fit addon
    fit_file = static_dir / 'js' / 'xterm-addon-fit.js'
    if not fit_file.exists():
        fit_file.write_text("""
window.FitAddon = { FitAddon: class { constructor(){} activate(){} fit(){} } };
""")
    
    return static_dir

def _init_system():
    """Initialize QUNIX system"""
    global _initialized, _init_attempted, _init_error
    global _engine, _processor, _conn, _qnic_interceptor, _qnic_running
    global _qnic_ready, _qnic_error, _db_path
    
    if _initialized:
        return True
    
    with _init_lock:
        if _initialized:
            return True
        
        if _init_attempted:
            return _init_error is None
        
        _init_attempted = True
        
        werkzeug_main = os.environ.get('WERKZEUG_RUN_MAIN')
        is_reloader_parent = (werkzeug_main is not None and werkzeug_main != 'true')
        
        if is_reloader_parent:
            _init_attempted = False
            return True
        
        _log("=" * 70)
        _log(f"QUNIX INITIALIZATION v{VERSION}")
        _log("=" * 70)
        
        try:
            # Find database
            _db_path = _find_database()
            if not _db_path:
                _init_error = "Database not found"
                _log(f"ERROR: {_init_error}")
                return False
            
            _log(f"Database: {_db_path}")
            
            # Connect to database
            _log("Connecting to database...")
            _conn = sqlite3.connect(
                str(_db_path),
                check_same_thread=False,
                isolation_level=None,
                timeout=30.0
            )
            _conn.execute("PRAGMA journal_mode=WAL")
            _conn.execute("PRAGMA synchronous=NORMAL")
            _log("✓ Database connected")
            
            # Import CPU modules
            try:
                from qunix_cpu import QunixExecutionEngine
                _log("✓ CPU modules imported")
            except ImportError as e:
                _init_error = f"CPU modules not found: {e}"
                _log(f"ERROR: {_init_error}")
                return False
            
            # Initialize CPU
            _log("Initializing CPU...")
            _engine = QunixExecutionEngine(_conn)
            _processor = _engine.command_processor  # FIX: Get processor from engine!
            _log("✓ CPU initialized")
            
            # Initialize QNIC (optional)
            _log("Attempting QNIC initialization...")
            try:
                # Try direct import first
                try:
                    import quantum_nic_v6_hijack as qnic_module
                    _log("✓ QNIC imported directly")
                except ImportError:
                    # Try file-based import
                    import importlib.util
                    
                    qnic_paths = [
                        Path(__file__).parent / "quantum_nic_v6_hijack.py",
                        Path("/home/Shemshallah/mysite/quantum_nic_v6_hijack.py"),
                        Path.cwd() / "quantum_nic_v6_hijack.py",
                    ]
                    
                    qnic_module = None
                    for qnic_path in qnic_paths:
                        _log(f"  Checking: {qnic_path}")
                        if qnic_path.exists():
                            _log(f"  Found QNIC at: {qnic_path}")
                            spec = importlib.util.spec_from_file_location("qnic", str(qnic_path))
                            if spec and spec.loader:
                                qnic_module = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(qnic_module)
                                _log("✓ QNIC loaded from file")
                                break
                    
                    if not qnic_module:
                        raise ImportError("quantum_nic_v6_hijack.py not found in any location")
                
                # Check aiosqlite
                if not qnic_module.AIOSQLITE_AVAILABLE:
                    _qnic_error = "aiosqlite not installed"
                    _log(f"⚠ QNIC disabled: {_qnic_error}")
                    _qnic_ready.set()
                else:
                    # Initialize QNIC tables
                    _log("Creating QNIC tables...")
                    if not qnic_module.init_qnic_tables_sync(str(_db_path)):
                        _qnic_error = "Table creation failed"
                        _log(f"✗ {_qnic_error}")
                        _qnic_ready.set()
                    else:
                        _log("✓ QNIC tables created")
                        
                        # Create interceptor
                        _qnic_interceptor = qnic_module.QuantumTrafficInterceptor(
                            str(_db_path),
                            _metrics_queue,
                            bind_addr='0.0.0.0',
                            bind_port=8080
                        )
                        
                        # Start QNIC thread
                        def run_qnic():
                            try:
                                import asyncio
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                
                                async def start_with_signal():
                                    global _qnic_running
                                    try:
                                        _qnic_interceptor.server = await asyncio.start_server(
                                            _qnic_interceptor.handle_client,
                                            _qnic_interceptor.bind_addr,
                                            _qnic_interceptor.bind_port
                                        )
                                        
                                        _qnic_running = True
                                        _qnic_ready.set()
                                        _log("✓ QNIC server started")
                                        
                                        _qnic_interceptor.running = True
                                        async with _qnic_interceptor.server:
                                            await _qnic_interceptor.server.serve_forever()
                                    
                                    except Exception as e:
                                        global _qnic_error
                                        _qnic_error = str(e)
                                        _qnic_ready.set()
                                        _log(f"✗ QNIC error: {e}")
                                
                                loop.run_until_complete(start_with_signal())
                            
                            except Exception as e:
                                _log(f"QNIC thread fatal: {e}")
                                global _qnic_error
                                _qnic_error = str(e)
                                _qnic_ready.set()
                        
                        qnic_thread = threading.Thread(target=run_qnic, daemon=True)
                        qnic_thread.start()
                        
                        # Wait for startup
                        _log("Waiting for QNIC...")
                        if _qnic_ready.wait(timeout=5.0):
                            if _qnic_running:
                                _log("✓ QNIC ready on :8080")
                                # Register Flask routes
                                qnic_module.create_flask_routes(app, _conn, str(_db_path), _qnic_interceptor, _metrics_queue)
                                _log("✓ QNIC routes registered")
                            else:
                                _log(f"⚠ QNIC failed: {_qnic_error}")
                        else:
                            _qnic_error = "Startup timeout"
                            _log(f"⚠ QNIC timeout")
            
            except Exception as e:
                _qnic_error = str(e)
                _log(f"⚠ QNIC disabled: {e}")
                _qnic_ready.set()
            
            # Mark initialized
            _initialized = True
            _init_error = None
            
            _log("=" * 70)
            _log("✓ SYSTEM READY")
            _log(f"  CPU: Active")
            _log(f"  QNIC: {'Active' if _qnic_running else f'Disabled ({_qnic_error})'}")
            _log("=" * 70)
            
            return True
        
        except Exception as e:
            _init_error = str(e)
            _log(f"FATAL: {e}")
            import traceback
            _log(traceback.format_exc())
            return False

# ═══════════════════════════════════════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════════════════════════════════════

@app.before_request
def ensure_initialized():
    """Ensure initialization"""
    werkzeug_main = os.environ.get('WERKZEUG_RUN_MAIN')
    if werkzeug_main and werkzeug_main != 'true':
        return None
    
    if not _initialized and not _init_attempted:
        if not _init_system():
            return jsonify({'error': _init_error}), 503

# ═══════════════════════════════════════════════════════════════════════════
# STATIC FILES
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    static_dirs = [
        Path(__file__).parent / 'static',
        Path('/home/Shemshallah/mysite/static'),
        Path.cwd() / 'static',
    ]
    
    for static_dir in static_dirs:
        if static_dir.exists():
            file_path = static_dir / filename
            if file_path.exists():
                return send_file(str(file_path))
    
    return "Not found", 404

# ═══════════════════════════════════════════════════════════════════════════
# TERMINAL API - COMPLETE
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/terminal/start', methods=['POST'])
def api_terminal_start():
    """Start terminal session"""
    if not _conn or not _processor:
        return jsonify({'success': False, 'error': 'System not ready'}), 503
    
    try:
        session_id = secrets.token_hex(16)
        now = time.time()
        
        c = _conn.cursor()
        c.execute('''
            INSERT INTO terminal_sessions (session_id, status, created, last_activity) 
            VALUES (?, ?, ?, ?)
        ''', (session_id, 'active', now, now))
        
        welcome = (
            f"\033[38;5;201m╔═══════════════════════════════════════════════════════╗\033[0m\r\n"
            f"\033[1m\033[38;5;213m        QUNIX v{VERSION}                 \033[0m\r\n"
            f"\033[38;5;201m╚═══════════════════════════════════════════════════════╝\033[0m\r\n\r\n"
            f"Type 'help' for commands\r\n\r\n\033[38;5;213mqunix>\033[0m "
        )
        
        c.execute('INSERT INTO terminal_output (session_id, data, ts) VALUES (?, ?, ?)',
                 (session_id, welcome, now))
        _conn.commit()
        
        return jsonify({'success': True, 'session_id': session_id})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/terminal/input', methods=['POST'])
def api_terminal_input():
    """Process terminal input"""
    if not _processor:
        return jsonify({'success': False}), 503
    
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        input_data = data.get('data', '').rstrip('\r\n').strip()
        
        if not input_data:
            output = "\r\n\033[38;5;213mqunix>\033[0m "
        else:
            result = _processor.execute(input_data)
            output = f"\r\n{result}\r\n\033[38;5;213mqunix>\033[0m " if result else "\r\n\033[38;5;213mqunix>\033[0m "
        
        c = _conn.cursor()
        c.execute('INSERT INTO terminal_output (session_id, data, ts) VALUES (?, ?, ?)',
                 (session_id, output, time.time()))
        c.execute('UPDATE terminal_sessions SET last_activity = ? WHERE session_id = ?',
                 (time.time(), session_id))
        _conn.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/terminal/output/<session_id>')
def api_terminal_output(session_id):
    """Get terminal output"""
    try:
        last_id = request.args.get('last_id', 0, type=int)
        
        c = _conn.cursor()
        c.execute('SELECT id, data FROM terminal_output WHERE session_id = ? AND id > ? ORDER BY id LIMIT 50',
                 (session_id, last_id))
        
        return jsonify({'data': [{'id': r[0], 'text': r[1]} for r in c.fetchall()]})
    
    except:
        return jsonify({'data': []})

# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM API
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/health')
def health():
    """Health check"""
    qnic_status = 'initializing'
    if _qnic_ready.is_set():
        qnic_status = 'active' if _qnic_running else 'disabled'
    
    return jsonify({
        'status': 'healthy' if _initialized else 'initializing',
        'version': VERSION,
        'xenolith': _engine is not None,
        'qnic': _qnic_running,
        'qnic_status': qnic_status,
        'qnic_error': _qnic_error,
        'timestamp': time.time()
    })

@app.route('/api/metrics')
def api_metrics():
    """System metrics"""
    if not _engine or not _conn:
        return jsonify({'error': 'Not ready'}), 503
    
    try:
        c = _conn.cursor()
        c.execute("SELECT COUNT(*) FROM q")
        qubits = c.fetchone()[0]
        
        return jsonify({
            'version': VERSION,
            'timestamp': time.time(),
            'cpu': {
                'cycles': _engine.cycle_count,
                'instructions': _engine.instruction_count
            },
            'quantum': {'qubits': qubits},
            'qnic': _qnic_running
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ═══════════════════════════════════════════════════════════════════════════
# MAIN UI - COMPLETE WITH TERMINAL
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """Main terminal interface"""
    return '''<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QUNIX MOONSHINE Terminal</title>
<link rel="stylesheet" href="/static/css/xterm.css"/>
<script src="/static/js/xterm.js"></script>
<script src="/static/js/xterm-addon-fit.js"></script>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#000; font-family:monospace; overflow:hidden; color:#fff; }
#header { background:linear-gradient(90deg,#1a0033,#4d0080); border-bottom:2px solid #cc00ff; padding:12px 20px; display:flex; justify-content:space-between; align-items:center; }
#logo { font-weight:bold; font-size:18px; color:#ff66ff; }
#status { color:#aaaaff; font-size:11px; }
#terminal-container { height:calc(100vh - 100px); padding:10px; background:#000; }
#footer { background:#0a0014; border-top:1px solid #660099; padding:10px 20px; font-size:10px; color:#aaaaff; }
</style>
</head><body>
<div id="header">
  <div id="logo">⚛ QUNIX MOONSHINE</div>
  <div id="status">Status: <span id="status-text">Connecting...</span></div>
</div>
<div id="terminal-container"></div>
<div id="footer">
  <strong>APIs:</strong> 
  <a href="/health" target="_blank" style="color:#ff66ff;margin:0 8px;">/health</a>
  <a href="/api/qnic/status" target="_blank" style="color:#ff66ff;margin:0 8px;">/api/qnic/status</a>
  <a href="/api/qnic/metrics" target="_blank" style="color:#ff66ff;margin:0 8px;">/api/qnic/metrics</a>
  <span style="margin-left:20px;">QNIC Proxy: localhost:8080</span>
</div>
<script>
const term = new Terminal({ 
  cursorBlink:true, 
  fontFamily:'"Courier New",monospace', 
  fontSize:13, 
  theme:{ background:'#000000', foreground:'#00ff00', cursor:'#ff00ff' }
});
const fitAddon = new FitAddon.FitAddon();
term.loadAddon(fitAddon);
term.open(document.getElementById('terminal-container'));
fitAddon.fit();
window.addEventListener('resize', () => fitAddon.fit());

let sessionId = null;
let lastOutputId = 0;
let inputBuffer = '';
let ready = false;
let isProcessing = false;
let pollTimer = null; // FIX: Track the timer

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
    document.getElementById('status-text').textContent = 'Online';
    document.getElementById('status-text').style.color = '#0f0';
    
    // FIX: Clear any existing timer before starting new one
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
    
    // FIX: Start single polling loop
    pollTimer = setInterval(poll, 200);
    
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
        
        // FIX: Only set ready once
        if (!ready && item.text.includes('qunix>')) {
          ready = true;
          setTimeout(() => term.focus(), 100);
        }
      });
    }
  } catch (e) {
    // Silent failure for network issues
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

// FIX: Cleanup on page unload
window.addEventListener('beforeunload', () => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
});

// FIX: Start only once
startSession();
term.focus();
</script>
</body></html>'''


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 70)
    print("  QUNIX v9.5.1 - COMPLETE SYSTEM (FIXED)")
    print("  Terminal + CPU + QNIC Integration")
    print("=" * 70)
    print()
    print("Dashboard: http://localhost:5000")
    print("QNIC Proxy: localhost:8080 (if enabled)")
    print()
    
    # Ensure static directory
    _ensure_static_directory()
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True, use_reloader=True)