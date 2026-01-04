#!/usr/bin/env python3
"""
QUNIX HuggingFace Space - Web Terminal Interface with Auto-Bootstrap
Automatically builds database on first run, handles path detection
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import asyncio
import pty
import os
import select
import subprocess
import signal
from pathlib import Path
import uvicorn
import shutil
import sys
import sqlite3

app = FastAPI()

# ═══════════════════════════════════════════════════════════════════════════
# PATH RESOLUTION - FIND PERSISTENT STORAGE
# ═══════════════════════════════════════════════════════════════════════════

def find_persistent_storage():
    """
    Find the best persistent storage location
    Priority: /data > /datasets > ~/qunix_data > ./qunix_data
    """
    APP_DIR = Path(__file__).parent.absolute()
    
    candidates = [
        Path("/data"),
        Path("/datasets"),
        Path.home() / "qunix_data",
        APP_DIR / "qunix_data",
        APP_DIR  # Fallback to app directory
    ]
    
    for path in candidates:
        if path.exists() and os.access(str(path), os.W_OK):
            return path, APP_DIR
        elif not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
                if os.access(str(path), os.W_OK):
                    return path, APP_DIR
            except:
                continue
    
    # Absolute fallback
    return APP_DIR, APP_DIR

DATA_DIR, APP_DIR = find_persistent_storage()
DB_PATH = DATA_DIR / "qunix_leech.db"

print(f"[INIT] Application directory: {APP_DIR}")
print(f"[INIT] Data directory: {DATA_DIR}")
print(f"[INIT] Database path: {DB_PATH}")

# Track active sessions
active_sessions = {}

# ═══════════════════════════════════════════════════════════════════════════
# DATABASE AUTO-BUILDER
# ═══════════════════════════════════════════════════════════════════════════

def check_database_valid() -> bool:
    """Check if database exists and is valid"""
    if not DB_PATH.exists():
        return False
    
    size_mb = DB_PATH.stat().st_size / (1024 * 1024)
    if size_mb < 0.1:  # Too small
        return False
    
    # Try to open it
    try:
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        count = c.fetchone()[0]
        conn.close()
        return count > 10  # Should have many tables
    except:
        return False


def build_database_if_needed():
    """Build database if it doesn't exist"""
    if check_database_valid():
        print(f"[INIT] ✓ Database exists: {DB_PATH}")
        return True
    
    print(f"[INIT] ⚠ Database missing or invalid - building...")
    
    # Find builder script
    builder_candidates = [
        APP_DIR / "qunix-leech-builder.py",
        Path.cwd() / "qunix-leech-builder.py",
    ]
    
    builder_path = None
    for candidate in builder_candidates:
        if candidate.exists():
            builder_path = candidate
            break
    
    if not builder_path:
        print(f"[INIT] ✗ Builder script not found!")
        return False
    
    print(f"[INIT] Running builder: {builder_path}")
    
    # Set environment
    env = os.environ.copy()
    env['RENDER_DISK_PATH'] = str(DATA_DIR)
    env['PYTHONUNBUFFERED'] = '1'
    
    try:
        result = subprocess.run(
            [sys.executable, str(builder_path)],
            env=env,
            cwd=str(DATA_DIR),
            timeout=300,  # 5 min timeout
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and check_database_valid():
            print(f"[INIT] ✓ Database built successfully")
            return True
        else:
            print(f"[INIT] ✗ Builder failed:")
            print(result.stdout[-500:] if result.stdout else "")
            print(result.stderr[-500:] if result.stderr else "")
            return False
            
    except Exception as e:
        print(f"[INIT] ✗ Builder exception: {e}")
        return False


# Build on startup
DB_READY = build_database_if_needed()

# ═══════════════════════════════════════════════════════════════════════════
# HTML TEMPLATE (same as before)
# ═══════════════════════════════════════════════════════════════════════════

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>QUNIX Web Terminal</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css" />
    <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/xterm-addon-web-links@0.9.0/lib/xterm-addon-web-links.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0e27;
            font-family: 'Monaco', monospace;
            display: flex;
            flex-direction: column;
            height: 100vh;
            padding: 20px;
            gap: 15px;
        }
        #header {
            background: linear-gradient(135deg, #1a1f3a 0%, #2d1b4e 100%);
            padding: 20px;
            border-radius: 10px;
            border: 2px solid #00ff41;
            box-shadow: 0 0 20px rgba(0, 255, 65, 0.3);
        }
        h1 {
            color: #00ff41;
            text-align: center;
            margin: 0 0 15px 0;
            font-size: 24px;
            text-shadow: 0 0 10px rgba(0, 255, 65, 0.5);
        }
        #status {
            display: flex;
            justify-content: center;
            gap: 30px;
            color: #00d4ff;
            font-size: 14px;
        }
        .status-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #ff4444;
            box-shadow: 0 0 5px rgba(255, 68, 68, 0.5);
        }
        .status-dot.active {
            background: #00ff41;
            box-shadow: 0 0 10px rgba(0, 255, 65, 0.8);
        }
        #controls {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-top: 15px;
        }
        button {
            background: linear-gradient(135deg, #00ff41 0%, #00d4ff 100%);
            color: #000;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }
        button:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0, 255, 65, 0.4);
        }
        button:disabled {
            opacity: 0.3;
            cursor: not-allowed;
        }
        #terminal-container {
            flex: 1;
            background: #000;
            border: 2px solid #00ff41;
            border-radius: 10px;
            padding: 10px;
            overflow: hidden;
            box-shadow: 0 0 30px rgba(0, 255, 65, 0.2);
        }
        .xterm-viewport {
            overflow-y: scroll !important;
            scrollbar-width: thin;
            scrollbar-color: #00ff41 #1a1f3a;
        }
    </style>
</head>
<body>
    <div id="header">
        <h1>⚛️ QUNIX Quantum Operating System ⚛️</h1>
        <div id="status">
            <div class="status-item">
                <div class="status-dot" id="db-dot"></div>
                <span id="db-status">Checking database...</span>
            </div>
            <div class="status-item">
                <div class="status-dot" id="ws-dot"></div>
                <span id="ws-status">Disconnected</span>
            </div>
        </div>
        <div id="controls">
            <button id="btn-connect" onclick="connectTerminal()">Connect Terminal</button>
            <button id="btn-disconnect" onclick="disconnectTerminal()" disabled>Disconnect</button>
            <button id="btn-rebuild" onclick="rebuildDatabase()">Rebuild Database</button>
        </div>
    </div>
    <div id="terminal-container"></div>

    <script>
        const term = new Terminal({
            cursorBlink: true,
            fontSize: 14,
            fontFamily: 'Monaco, monospace',
            theme: {
                background: '#000000',
                foreground: '#00ff41',
                cursor: '#00ff41',
                selection: 'rgba(0, 255, 65, 0.3)'
            },
            cols: 120,
            rows: 30
        });
        
        const fitAddon = new FitAddon.FitAddon();
        const webLinksAddon = new WebLinksAddon.WebLinksAddon();
        
        term.loadAddon(fitAddon);
        term.loadAddon(webLinksAddon);
        term.open(document.getElementById('terminal-container'));
        fitAddon.fit();
        
        let socket = null;
        const dbDot = document.getElementById('db-dot');
        const dbStatus = document.getElementById('db-status');
        const wsDot = document.getElementById('ws-dot');
        const wsStatus = document.getElementById('ws-status');
        const btnConnect = document.getElementById('btn-connect');
        const btnDisconnect = document.getElementById('btn-disconnect');
        const btnRebuild = document.getElementById('btn-rebuild');
        
        async function checkStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                
                if (data.database_exists) {
                    dbDot.classList.add('active');
                    dbStatus.textContent = 'Database Ready';
                } else {
                    dbDot.classList.remove('active');
                    dbStatus.textContent = 'Database Missing';
                }
            } catch (e) {
                dbStatus.textContent = 'Status Error';
            }
        }
        
        async function rebuildDatabase() {
            if (!confirm('This will rebuild the database. Continue?')) return;
            
            btnRebuild.disabled = true;
            dbStatus.textContent = 'Building...';
            
            try {
                const res = await fetch('/api/build', { method: 'POST' });
                const data = await res.json();
                
                if (data.success) {
                    alert('Database built successfully!');
                    checkStatus();
                } else {
                    alert('Build failed: ' + data.error);
                }
            } catch (e) {
                alert('Build error: ' + e);
            } finally {
                btnRebuild.disabled = false;
            }
        }
        
        function connectTerminal() {
            const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
            socket = new WebSocket(`${proto}//${location.host}/ws/terminal`);
            
            btnConnect.disabled = true;
            wsDot.classList.add('active');
            wsStatus.textContent = 'Connected';
            
            socket.onopen = () => {
                btnDisconnect.disabled = false;
            };
            
            socket.onmessage = (e) => term.write(e.data);
            
            socket.onclose = () => {
                term.writeln('');
                term.writeln('\\x1b[33m[DISCONNECTED]\\x1b[0m');
                wsDot.classList.remove('active');
                wsStatus.textContent = 'Disconnected';
                btnConnect.disabled = false;
                btnDisconnect.disabled = true;
            };
            
            term.onData((data) => {
                if (socket && socket.readyState === WebSocket.OPEN) {
                    socket.send(data);
                }
            });
        }

        function disconnectTerminal() {
            if (socket) socket.close();
        }

        // Auto-check status on load
        checkStatus();
        
        window.addEventListener('resize', () => fitAddon.fit());
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the web terminal interface"""
    return HTML_TEMPLATE

@app.get("/api/status")
async def get_status():
    """Check system status"""
    db_exists = check_database_valid()
    db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    
    # Check kernel status
    kernel_booted = False
    if db_exists:
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("SELECT val FROM meta WHERE key='kernel_state'")
            row = c.fetchone()
            kernel_booted = row and row[0] == 'BOOTED'
            conn.close()
        except:
            pass
    
    return {
        "database_exists": db_exists,
        "database_size": db_size,
        "kernel_booted": kernel_booted,
        "data_dir": str(DATA_DIR),
        "app_dir": str(APP_DIR)
    }

@app.post("/api/build")
async def build_database():
    """Build/rebuild the QUNIX database"""
    try:
        # Remove old database
        if DB_PATH.exists():
            DB_PATH.unlink()
        
        # Build new one
        success = build_database_if_needed()
        
        return {
            "success": success,
            "database_path": str(DB_PATH)
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@app.websocket("/ws/terminal")
async def websocket_terminal(websocket: WebSocket):
    """WebSocket terminal connection"""
    await websocket.accept()
    
    # Check if database exists
    if not check_database_valid():
        await websocket.send_text("\x1b[31m╔══════════════════════════════════════════════════════════════╗\x1b[0m\r\n")
        await websocket.send_text("\x1b[31m║  ERROR: QUNIX database not found or invalid                  ║\x1b[0m\r\n")
        await websocket.send_text("\x1b[31m╚══════════════════════════════════════════════════════════════╝\x1b[0m\r\n")
        await websocket.send_text("\r\n")
        await websocket.send_text("\x1b[33mClick 'Rebuild Database' button above to build the system.\x1b[0m\r\n")
        await websocket.send_text("\x1b[33mThis will take 30-60 seconds.\x1b[0m\r\n")
        await websocket.close()
        return
    
    # Find dev_cli script
    dev_cli_script = APP_DIR / "dev_cli.py"
    
    if not dev_cli_script.exists():
        await websocket.send_text(f"\x1b[31mERROR: dev_cli.py not found at {dev_cli_script}\x1b[0m\r\n")
        await websocket.close()
        return
    
    # Create PTY
    master_fd, slave_fd = pty.openpty()
    
    # Set environment
    env = os.environ.copy()
    env['TERM'] = 'xterm-256color'
    env['PYTHONUNBUFFERED'] = '1'
    env['RENDER_DISK_PATH'] = str(DATA_DIR)
    
    print(f"[TERMINAL] Starting: {dev_cli_script}")
    print(f"[TERMINAL] Data dir: {DATA_DIR}")
    
    # Start dev_cli.py in PTY
    process = subprocess.Popen(
        [sys.executable, str(dev_cli_script)],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        preexec_fn=os.setsid,
        env=env,
        cwd=str(DATA_DIR)
    )
    
    os.close(slave_fd)
    
    session_id = id(websocket)
    active_sessions[session_id] = {'master_fd': master_fd, 'process': process}
    
    async def read_output():
        """Read from PTY, send to WebSocket"""
        try:
            while True:
                r, _, _ = select.select([master_fd], [], [], 0.1)
                if r:
                    try:
                        data = os.read(master_fd, 4096)
                        if data:
                            await websocket.send_text(data.decode('utf-8', errors='replace'))
                    except OSError:
                        break
                
                if process.poll() is not None:
                    break
                
                await asyncio.sleep(0.01)
        except:
            pass
    
    async def write_input():
        """Receive from WebSocket, write to PTY"""
        try:
            while True:
                data = await websocket.receive_text()
                os.write(master_fd, data.encode())
        except WebSocketDisconnect:
            pass
        except:
            pass
    
    try:
        await asyncio.gather(read_output(), write_input())
    finally:
        try:
            process.terminate()
            process.wait(timeout=2)
        except:
            try:
                process.kill()
            except:
                pass
        
        try:
            os.close(master_fd)
        except:
            pass
        
        if session_id in active_sessions:
            del active_sessions[session_id]

if __name__ == "__main__":
    print("🔮 QUNIX Web Terminal Server")
    print(f"📁 App: {APP_DIR}")
    print(f"📁 Data: {DATA_DIR}")
    print(f"💾 Database: {DB_PATH}")
    print(f"✓ Database ready: {DB_READY}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=7860,
        log_level="info"
    )
