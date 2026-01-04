#!/usr/bin/env python3
"""
QUNIX HuggingFace Space - Web Terminal Interface
Runs dev_cli.py in a PTY with WebSocket connection
FIXED: Uses /data directory exclusively
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

app = FastAPI()

None_PATH = DATA_DIR / "qunix_leech.db"

print(f"[INIT] Application directory: {APP_DIR}")
print(f"[INIT] Data directory: {DATA_DIR}")
print(f"[INIT] Data directory exists: {DATA_DIR.exists()}")
print(f"[INIT] Data directory writable: {os.access(str(DATA_DIR), os.W_OK)}")
print(f"[INIT] Database path: {DB_PATH}")

# Track active sessions
active_sessions = {}

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
            position: relative;
        }
        .xterm-selection {
            background-color: rgba(0, 255, 65, 0.3) !important;
        }
        .xterm-viewport {
            overflow-y: scroll !important;
            scrollbar-width: thin;
            scrollbar-color: #00ff41 #1a1f3a;
        }
        .xterm-viewport::-webkit-scrollbar {
            width: 10px;
        }
        .xterm-viewport::-webkit-scrollbar-track {
            background: #1a1f3a;
        }
        .xterm-viewport::-webkit-scrollbar-thumb {
            background: #00ff41;
            border-radius: 5px;
        }
        .xterm-viewport::-webkit-scrollbar-thumb:hover {
            background: #00d4ff;
        }
        #loading {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(10, 14, 39, 0.98);
            padding: 50px;
            border: 3px solid #00ff41;
            border-radius: 15px;
            text-align: center;
            display: none;
            z-index: 1000;
            box-shadow: 0 0 60px rgba(0, 255, 65, 0.6);
        }
        #loading.active { display: block; }
        .spinner {
            border: 5px solid rgba(0, 255, 65, 0.1);
            border-top: 5px solid #00ff41;
            border-radius: 50%;
            width: 70px;
            height: 70px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        #loading h2 { color: #00ff41; margin: 0 0 10px 0; font-size: 20px; }
        #loading p { color: #00d4ff; margin: 5px 0; font-size: 14px; }
        .progress-bar {
            width: 300px;
            height: 20px;
            background: rgba(0, 255, 65, 0.1);
            border: 1px solid #00ff41;
            border-radius: 10px;
            margin: 20px auto 10px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00ff41 0%, #00d4ff 100%);
            width: 0%;
            transition: width 0.5s;
        }
        #copy-notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0, 255, 65, 0.95);
            color: #000;
            padding: 15px 25px;
            border-radius: 8px;
            font-weight: bold;
            display: none;
            z-index: 2000;
            box-shadow: 0 0 20px rgba(0, 255, 65, 0.6);
            animation: slideIn 0.3s ease-out;
        }
        #copy-notification.show {
            display: block;
        }
        @keyframes slideIn {
            from { transform: translateX(400px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        .help-text {
            text-align: center;
            color: #00d4ff;
            font-size: 12px;
            margin-top: 10px;
        }
        .help-text kbd {
            background: rgba(0, 255, 65, 0.2);
            padding: 2px 6px;
            border-radius: 3px;
            border: 1px solid #00ff41;
            font-family: monospace;
        }
        .info-banner {
            background: rgba(0, 212, 255, 0.1);
            border: 1px solid #00d4ff;
            border-radius: 8px;
            padding: 10px;
            margin-top: 10px;
            text-align: center;
            color: #00d4ff;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div id="header">
        <h1>🔮 QUNIX QUANTUM OPERATING SYSTEM - BITCODE EDITION</h1>
        <div id="status">
            <div class="status-item">
                <div class="status-dot" id="db-status"></div>
                <span>Database: <span id="db-text">Checking...</span></span>
            </div>
            <div class="status-item">
                <div class="status-dot" id="ws-status"></div>
                <span>Terminal: <span id="ws-text">Disconnected</span></span>
            </div>
        </div>
        <div class="info-banner">
            📦 All programs stored as executable bitcode in /data/qunix_leech.db
        </div>
    </div>
    
    <div id="controls">
        <button id="btn-build" onclick="buildDatabase()">🔧 Build Database (First Time Only)</button>
        <button id="btn-connect" onclick="connectTerminal()" disabled>▶️ Connect Terminal</button>
        <button id="btn-disconnect" onclick="disconnectTerminal()" disabled>⏹️ Disconnect</button>
    </div>
    
    <div class="help-text">
        💡 Tip: Select text to copy • <kbd>Ctrl+C</kbd> to copy • <kbd>Ctrl+V</kbd> to paste • Scroll with mouse wheel
    </div>
    
    <div id="terminal-container"></div>
    
    <div id="copy-notification">✓ Copied to clipboard!</div>
    
    <div id="loading">
        <div class="spinner"></div>
        <h2 id="loading-title">Building QUNIX Database...</h2>
        <p id="loading-text">Generating Leech lattice (~196K points)</p>
        <div class="progress-bar">
            <div class="progress-fill" id="progress"></div>
        </div>
        <p id="loading-time">Estimated time: 30-90 seconds</p>
    </div>

    <script>
        let term, socket, fitAddon, webLinksAddon;

        function showCopyNotification() {
            const notification = document.getElementById('copy-notification');
            notification.classList.add('show');
            setTimeout(() => notification.classList.remove('show'), 2000);
        }

        async function init() {
            term = new Terminal({
                cursorBlink: true,
                fontSize: 14,
                fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
                theme: {
                    background: '#000000',
                    foreground: '#00ff41',
                    cursor: '#00ff41',
                    selection: 'rgba(0, 255, 65, 0.3)',
                    selectionBackground: 'rgba(0, 255, 65, 0.3)'
                },
                rows: 30,
                cols: 100,
                scrollback: 10000,
                allowTransparency: false,
                convertEol: true
            });
            
            fitAddon = new FitAddon.FitAddon();
            term.loadAddon(fitAddon);
            
            webLinksAddon = new WebLinksAddon.WebLinksAddon();
            term.loadAddon(webLinksAddon);
            
            term.open(document.getElementById('terminal-container'));
            fitAddon.fit();
            
            term.attachCustomKeyEventHandler((event) => {
                if (event.ctrlKey && event.key === 'c' && term.hasSelection()) {
                    const selection = term.getSelection();
                    if (selection) {
                        navigator.clipboard.writeText(selection).then(() => {
                            showCopyNotification();
                        });
                        return false;
                    }
                }
                
                if (event.ctrlKey && event.key === 'v') {
                    event.preventDefault();
                    navigator.clipboard.readText().then(text => {
                        if (socket && socket.readyState === WebSocket.OPEN) {
                            socket.send(text);
                        }
                    });
                    return false;
                }
                
                return true;
            });
            
            document.getElementById('terminal-container').addEventListener('contextmenu', (e) => {
                const selection = term.getSelection();
                if (selection) {
                    e.preventDefault();
                    navigator.clipboard.writeText(selection).then(() => {
                        showCopyNotification();
                    });
                }
            });
            
            term.writeln('\\x1b[1;32m╔═══════════════════════════════════════════════════════════════╗\\x1b[0m');
            term.writeln('\\x1b[1;32m║     QUNIX QUANTUM OS - BITCODE EDITION - Web Terminal        ║\\x1b[0m');
            term.writeln('\\x1b[1;32m╚═══════════════════════════════════════════════════════════════╝\\x1b[0m');
            term.writeln('');
            term.writeln('\\x1b[35m🔮 BITCODE QUANTUM OPERATING SYSTEM\\x1b[0m');
            term.writeln('\\x1b[36mAll programs stored as executable bytecode in database\\x1b[0m');
            term.writeln('\\x1b[36mMetaprograms run in infinite loops from DB\\x1b[0m');
            term.writeln('');
            term.writeln('\\x1b[33mFirst time? Follow these steps:\\x1b[0m');
            term.writeln('  1. Click "Build Database" (30-90 seconds, creates /data/qunix_leech.db)');
            term.writeln('  2. Click "Connect Terminal" to launch dev_cli.py');
            term.writeln('  3. Use the interactive 40+ option menu');
            term.writeln('');
            term.writeln('\\x1b[36m💡 Text Selection Enabled:\\x1b[0m');
            term.writeln('   • Click and drag to select text');
            term.writeln('   • Ctrl+C or right-click to copy');
            term.writeln('   • Ctrl+V to paste');
            term.writeln('');
            
            await updateStatus();
            
            window.addEventListener('resize', () => {
                fitAddon.fit();
            });
        }

        async function updateStatus() {
            try {
                const res = await fetch('/api/status');
                const status = await res.json();
                
                const dbDot = document.getElementById('db-status');
                const dbText = document.getElementById('db-text');
                const btnConnect = document.getElementById('btn-connect');
                
                term.writeln('\\x1b[36m[STATUS] Checking database at ' + status.db_path + '\\x1b[0m');
                
                if (status.database_exists) {
                    dbDot.classList.add('active');
                    const sizeMB = (status.database_size / 1024 / 1024).toFixed(1);
                    dbText.textContent = `Ready (${sizeMB} MB)`;
                    btnConnect.disabled = false;
                    term.writeln('\\x1b[32m[STATUS] Database found at /data/qunix_leech.db (' + sizeMB + ' MB)\\x1b[0m');
                    term.writeln('\\x1b[32m[STATUS] Ready to connect!\\x1b[0m');
                } else {
                    dbDot.classList.remove('active');
                    dbText.textContent = 'Not Built';
                    term.writeln('\\x1b[33m[STATUS] Database not found - click "Build Database"\\x1b[0m');
                    term.writeln('\\x1b[33m[STATUS] Will create at: /data/qunix_leech.db\\x1b[0m');
                }
            } catch (e) {
                console.error('Status check failed:', e);
                term.writeln('\\x1b[31m[ERROR] Status check failed: ' + e.message + '\\x1b[0m');
            }
        }

        async function buildDatabase() {
            const loading = document.getElementById('loading');
            const btn = document.getElementById('btn-build');
            const progress = document.getElementById('progress');
            
            btn.disabled = true;
            loading.classList.add('active');
            
            term.clear();
            term.writeln('\\x1b[35m╔══════════════════════════════════════════════════════════════╗\\x1b[0m');
            term.writeln('\\x1b[35m║         BUILDING QUNIX BITCODE DATABASE                      ║\\x1b[0m');
            term.writeln('\\x1b[35m╚══════════════════════════════════════════════════════════════╝\\x1b[0m');
            term.writeln('');
            term.writeln('\\x1b[33m[BUILD] Starting database build in /data directory...\\x1b[0m');
            term.writeln('\\x1b[33m[BUILD] This will take 30-90 seconds. Please wait...\\x1b[0m');
            term.writeln('');
            
            let prog = 0;
            const progressInterval = setInterval(() => {
                prog += Math.random() * 5;
                if (prog > 95) prog = 95;
                progress.style.width = prog + '%';
            }, 1000);
            
            try {
                const res = await fetch('/api/build', { 
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const result = await res.json();
                
                clearInterval(progressInterval);
                progress.style.width = '100%';
                
                if (result.success) {
                    term.writeln('\\x1b[32m╔══════════════════════════════════════════════════════════════╗\\x1b[0m');
                    term.writeln('\\x1b[32m║                  BUILD SUCCESSFUL                            ║\\x1b[0m');
                    term.writeln('\\x1b[32m╚══════════════════════════════════════════════════════════════╝\\x1b[0m');
                    term.writeln('');
                    term.writeln('\\x1b[36m[SUCCESS] Database: /data/qunix_leech.db\\x1b[0m');
                    term.writeln('\\x1b[36m[SUCCESS] Size: ' + (result.database_size / 1024 / 1024).toFixed(1) + ' MB\\x1b[0m');
                    term.writeln('\\x1b[36m[SUCCESS] Lattice points: ~196,560\\x1b[0m');
                    term.writeln('\\x1b[36m[SUCCESS] Qubits: ~196,562\\x1b[0m');
                    term.writeln('\\x1b[36m[SUCCESS] Bitcode programs: 9 (6 standard + 3 metaprograms)\\x1b[0m');
                    term.writeln('');
                    term.writeln('\\x1b[35m[INFO] Metaprograms installed:\\x1b[0m');
                    term.writeln('\\x1b[35m  • quine_evolver (infinite loop, PID 10)\\x1b[0m');
                    term.writeln('\\x1b[35m  • live_patcher (infinite loop, PID 11)\\x1b[0m');
                    term.writeln('\\x1b[35m  • symbolic_verifier (infinite loop, PID 12)\\x1b[0m');
                    term.writeln('');
                    term.writeln('\\x1b[32m✓ Ready! Click "Connect Terminal" to start.\\x1b[0m');
                    await updateStatus();
                } else {
                    term.writeln('\\x1b[31m[ERROR] Build failed:\\x1b[0m');
                    term.writeln('\\x1b[31m' + (result.error || 'Unknown error') + '\\x1b[0m');
                    if (result.output) {
                        term.writeln('');
                        term.writeln('\\x1b[33m[OUTPUT]\\x1b[0m');
                        result.output.split('\\n').slice(-20).forEach(line => {
                            term.writeln('\\x1b[90m' + line + '\\x1b[0m');
                        });
                    }
                }
            } catch (e) {
                clearInterval(progressInterval);
                term.writeln('\\x1b[31m[ERROR] ' + e.message + '\\x1b[0m');
            } finally {
                loading.classList.remove('active');
                btn.disabled = false;
                progress.style.width = '0%';
            }
        }

        function connectTerminal() {
            const wsDot = document.getElementById('ws-status');
            const wsText = document.getElementById('ws-text');
            const btnConnect = document.getElementById('btn-connect');
            const btnDisconnect = document.getElementById('btn-disconnect');
            
            term.clear();
            term.writeln('\\x1b[36m[SYSTEM] Connecting to QUNIX terminal...\\x1b[0m');
            term.writeln('\\x1b[36m[SYSTEM] Database: /data/qunix_leech.db\\x1b[0m');
            term.writeln('');
            
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            socket = new WebSocket(`${protocol}//${window.location.host}/ws/terminal`);
            
            socket.onopen = () => {
                term.writeln('\\x1b[32m[CONNECTED] Terminal session active\\x1b[0m');
                term.writeln('\\x1b[32m[CONNECTED] Executing bitcode from database\\x1b[0m');
                term.writeln('');
                wsDot.classList.add('active');
                wsText.textContent = 'Connected';
                btnConnect.disabled = true;
                btnDisconnect.disabled = false;
            };
            
            socket.onmessage = (e) => term.write(e.data);
            
            socket.onclose = () => {
                term.writeln('');
                term.writeln('\\x1b[33m[DISCONNECTED] Terminal session ended\\x1b[0m');
                wsDot.classList.remove('active');
                wsText.textContent = 'Disconnected';
                btnConnect.disabled = false;
                btnDisconnect.disabled = true;
            };
            
            socket.onerror = (e) => {
                term.writeln('\\x1b[31m[ERROR] WebSocket error\\x1b[0m');
                console.error('WebSocket error:', e);
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

        init();
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
    import sqlite3
    
    db_exists = DB_PATH.exists()
    db_size = DB_PATH.stat().st_size if db_exists else 0
    
    # Check kernel status
    kernel_booted = False
    bitcode_count = 0
    if db_exists:
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("SELECT val FROM meta WHERE key='kernel_state'")
            row = c.fetchone()
            kernel_booted = row and row[0] == 'BOOTED'
            
            c.execute("SELECT COUNT(*) FROM bin")
            bitcode_count = c.fetchone()[0]
            
            conn.close()
        except:
            pass
    
    return {
        "database_exists": db_exists,
        "database_size": db_size,
        "kernel_booted": kernel_booted,
        "bitcode_programs": bitcode_count,
        "data_dir": str(DATA_DIR),
        "app_dir": str(APP_DIR),
        "db_path": str(DB_PATH)
    }

@app.post("/api/build")
async def build_database():
    """Build the QUNIX database (one-time)"""
    try:
        # Remove old database if exists
        if DB_PATH.exists():
            print(f"[BUILD] Removing old database: {DB_PATH}")
            DB_PATH.unlink()
        
        # Path to builder script
        builder_script = APP_DIR / "qunix-leech-builder.py"
        
        if not builder_script.exists():
            return {
                "success": False,
                "error": f"Builder script not found at {builder_script}",
                "traceback": f"Checked path: {builder_script}\nApp dir: {APP_DIR}"
            }
        
        print(f"[BUILD] Running builder: {builder_script}")
        print(f"[BUILD] Database will be created at: {DB_PATH}")
        print(f"[BUILD] Working directory: {DATA_DIR}")
        
        # Set environment to force /data usage
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        
        # Run builder - it will create DB in /data
        result = subprocess.run(
            [sys.executable, str(builder_script)],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            env=env
        )
        
        print(f"[BUILD] Return code: {result.returncode}")
        print(f"[BUILD] Stdout length: {len(result.stdout)}")
        
        if result.stderr:
            print(f"[BUILD] Stderr length: {len(result.stderr)}")
            # Print last 500 chars of stderr
            print(f"[BUILD] Stderr (last 500):\n{result.stderr[-500:]}")
        
        # Check if DB was created in /data
        db_exists = DB_PATH.exists()
        
        if db_exists:
            print(f"[BUILD] ✓ Database created at {DB_PATH}")
            print(f"[BUILD] ✓ Size: {DB_PATH.stat().st_size / 1024 / 1024:.1f} MB")
        else:
            print(f"[BUILD] ✗ Database NOT found at {DB_PATH}")
            # Check if it was created elsewhere
            alt_paths = [
                APP_DIR / "qunix_leech.db",
                Path.cwd() / "qunix_leech.db",
            ]
            for alt_path in alt_paths:
                if alt_path.exists():
                    print(f"[BUILD] ! Found database at {alt_path}, moving to {DB_PATH}")
                    shutil.move(str(alt_path), str(DB_PATH))
                    db_exists = True
                    break
        
        return {
            "success": result.returncode == 0 and db_exists,
            "database_exists": db_exists,
            "database_size": DB_PATH.stat().st_size if db_exists else 0,
            "error": result.stderr[-1000:] if result.returncode != 0 else None,
            "output": result.stdout[-2000:] if result.stdout else None,
            "traceback": result.stderr[-2000:] if result.returncode != 0 else None,
            "db_path": str(DB_PATH)
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Build timeout (>5 min)",
            "traceback": "Process exceeded 5 minute timeout limit"
        }
    except Exception as e:
        import traceback as tb
        return {
            "success": False,
            "error": str(e),
            "traceback": tb.format_exc()
        }

@app.websocket("/ws/terminal")
async def terminal_websocket(websocket: WebSocket):
    """WebSocket for terminal I/O"""
    await websocket.accept()
    
    # Check if database exists
    if not DB_PATH.exists():
        await websocket.send_text(f"\x1b[31mERROR: Database not found at {DB_PATH}\x1b[0m\r\n")
        await websocket.send_text(f"\x1b[33mPlease build the database first using the 'Build Database' button\x1b[0m\r\n")
        await websocket.close()
        return
    
    # Path to dev_cli script
    dev_cli_script = APP_DIR / "dev_cli.py"
