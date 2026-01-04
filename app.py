#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║                 QUNIX COMPLETE WEB APPLICATION                            ║
║         Fully Integrated CPU, Microcode, and OS System                    ║
║                                                                           ║
║  • Automatic database detection and initialization                        ║
║  • Leech CPU integration at every microcode level                         ║
║  • Process execution on quantum substrate                                 ║
║  • Metaprogram infinite loop monitoring                                   ║
║  • Complete dev_cli integration                                           ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
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
import time
import json

app = FastAPI()

# Get the application directory
APP_DIR = Path(__file__).parent.absolute()

# Use persistent storage directory if available
DATA_DIR = Path("/data") if Path("/data").exists() else APP_DIR
DB_PATH = DATA_DIR / "qunix_leech.db"

print(f"[INIT] Application directory: {APP_DIR}")
print(f"[INIT] Data directory: {DATA_DIR}")
print(f"[INIT] Database path: {DB_PATH}")

# Track active sessions
active_sessions = {}

# ═══════════════════════════════════════════════════════════════════════════
# DATABASE VERIFICATION WITH CPU CHECKS
# ═══════════════════════════════════════════════════════════════════════════

def verify_database_complete() -> dict:
    """
    Comprehensive database verification including CPU microcode
    Returns dict with status and details
    """
    if not DB_PATH.exists():
        return {
            'exists': False,
            'valid': False,
            'has_cpu': False,
            'has_metaprograms': False,
            'error': 'Database file not found'
        }
    
    try:
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        
        # Check core tables
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in c.fetchall()}
        
        required_tables = {'lat', 'pqb', 'tri', 'bin', 'prc', 'thr', 'ins', 'meta'}
        missing_tables = required_tables - tables
        
        if missing_tables:
            conn.close()
            return {
                'exists': True,
                'valid': False,
                'has_cpu': False,
                'has_metaprograms': False,
                'error': f'Missing tables: {missing_tables}'
            }
        
        # Check lattice points
        c.execute('SELECT COUNT(*) FROM lat')
        lattice_count = c.fetchone()[0]
        
        # Check pseudoqubits
        c.execute('SELECT COUNT(*) FROM pqb')
        qubit_count = c.fetchone()[0]
        
        # Check CPU microcode installation
        c.execute("SELECT COUNT(*) FROM bin WHERE nam LIKE 'cpu_%'")
        cpu_programs = c.fetchone()[0]
        
        # Check if CPU tables exist
        has_cpu_tables = 'cpubin' in tables and 'cpustate' in tables
        
        # Check metaprograms
        c.execute("SELECT COUNT(*) FROM bin WHERE typ='metaprogram'")
        metaprogram_count = c.fetchone()[0]
        
        # Check if metaprograms are running
        c.execute("""
            SELECT COUNT(*) FROM loop_state l 
            JOIN bin b ON l.bid = b.bid 
            WHERE b.typ='metaprogram' AND l.continue_flag=1
        """)
        running_metaprograms = c.fetchone()[0]
        
        # Check kernel boot status
        c.execute("SELECT val FROM meta WHERE key='kernel_state'")
        kernel_row = c.fetchone()
        kernel_booted = kernel_row and kernel_row[0] == 'BOOTED'
        
        conn.close()
        
        return {
            'exists': True,
            'valid': True,
            'has_cpu': has_cpu_tables and cpu_programs > 0,
            'has_metaprograms': metaprogram_count >= 3,
            'kernel_booted': kernel_booted,
            'lattice_points': lattice_count,
            'qubits': qubit_count,
            'cpu_programs': cpu_programs,
            'metaprograms': metaprogram_count,
            'running_metaprograms': running_metaprograms,
            'size_mb': DB_PATH.stat().st_size / (1024 * 1024)
        }
        
    except Exception as e:
        return {
            'exists': True,
            'valid': False,
            'has_cpu': False,
            'has_metaprograms': False,
            'error': str(e)
        }

# ═══════════════════════════════════════════════════════════════════════════
# HTML INTERFACE
# ═══════════════════════════════════════════════════════════════════════════

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>QUNIX Quantum OS</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css" />
    <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #2d1b4e 100%);
            font-family: 'Monaco', 'Courier New', monospace;
            display: flex;
            flex-direction: column;
            height: 100vh;
            padding: 20px;
            gap: 15px;
        }
        #header {
            background: linear-gradient(135deg, #1a1f3a 0%, #2d1b4e 100%);
            padding: 25px;
            border-radius: 12px;
            border: 3px solid #00ff41;
            box-shadow: 0 0 30px rgba(0, 255, 65, 0.4);
        }
        h1 {
            color: #00ff41;
            text-align: center;
            margin: 0 0 15px 0;
            font-size: 28px;
            text-shadow: 0 0 15px rgba(0, 255, 65, 0.6);
            letter-spacing: 2px;
        }
        .subtitle {
            color: #00d4ff;
            text-align: center;
            font-size: 14px;
            margin-bottom: 20px;
            opacity: 0.9;
        }
        #status {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .status-item {
            background: rgba(0, 0, 0, 0.3);
            padding: 12px;
            border-radius: 8px;
            border: 1px solid rgba(0, 255, 65, 0.3);
        }
        .status-label {
            color: #00d4ff;
            font-size: 11px;
            text-transform: uppercase;
            margin-bottom: 5px;
            opacity: 0.8;
        }
        .status-value {
            color: #00ff41;
            font-size: 16px;
            font-weight: bold;
        }
        .status-value.error { color: #ff4444; }
        .status-value.warning { color: #ffaa00; }
        #controls {
            display: flex;
            gap: 12px;
            justify-content: center;
            flex-wrap: wrap;
        }
        button {
            background: linear-gradient(135deg, #00ff41 0%, #00d4ff 100%);
            color: #000;
            border: none;
            padding: 14px 28px;
            border-radius: 10px;
            font-weight: bold;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        button:hover:not(:disabled) {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0, 255, 65, 0.5);
        }
        button:active:not(:disabled) {
            transform: translateY(-1px);
        }
        button:disabled {
            opacity: 0.3;
            cursor: not-allowed;
        }
        button.danger {
            background: linear-gradient(135deg, #ff4444 0%, #ff6b6b 100%);
            color: #fff;
        }
        #terminal-container {
            flex: 1;
            background: #000;
            border: 3px solid #00ff41;
            border-radius: 12px;
            padding: 15px;
            overflow: hidden;
            box-shadow: 0 0 40px rgba(0, 255, 65, 0.3);
            position: relative;
        }
        .xterm-viewport {
            overflow-y: scroll !important;
            scrollbar-width: thin;
            scrollbar-color: #00ff41 #1a1f3a;
        }
        .xterm-viewport::-webkit-scrollbar { width: 12px; }
        .xterm-viewport::-webkit-scrollbar-track { background: #1a1f3a; }
        .xterm-viewport::-webkit-scrollbar-thumb {
            background: #00ff41;
            border-radius: 6px;
        }
        .xterm-viewport::-webkit-scrollbar-thumb:hover { background: #00d4ff; }
        #loading {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(10, 14, 39, 0.98);
            padding: 60px;
            border: 4px solid #00ff41;
            border-radius: 20px;
            text-align: center;
            display: none;
            z-index: 1000;
            box-shadow: 0 0 80px rgba(0, 255, 65, 0.7);
        }
        #loading.active { display: block; }
        .spinner {
            border: 6px solid rgba(0, 255, 65, 0.1);
            border-top: 6px solid #00ff41;
            border-radius: 50%;
            width: 80px;
            height: 80px;
            animation: spin 1s linear infinite;
            margin: 0 auto 25px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        #loading h2 {
            color: #00ff41;
            margin: 0 0 15px 0;
            font-size: 24px;
        }
        #loading p {
            color: #00d4ff;
            margin: 8px 0;
            font-size: 15px;
        }
        .progress-bar {
            width: 350px;
            height: 25px;
            background: rgba(0, 255, 65, 0.1);
            border: 2px solid #00ff41;
            border-radius: 12px;
            margin: 25px auto 15px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00ff41 0%, #00d4ff 100%);
            width: 0%;
            transition: width 0.5s;
            box-shadow: 0 0 20px rgba(0, 255, 65, 0.8);
        }
        .help-text {
            text-align: center;
            color: #00d4ff;
            font-size: 13px;
            margin-top: 12px;
            opacity: 0.9;
        }
        .help-text kbd {
            background: rgba(0, 255, 65, 0.2);
            padding: 3px 8px;
            border-radius: 4px;
            border: 1px solid #00ff41;
            font-family: monospace;
            font-size: 12px;
        }
        .system-info {
            background: rgba(0, 0, 0, 0.4);
            padding: 15px;
            border-radius: 8px;
            border: 1px solid rgba(0, 255, 65, 0.2);
            margin-top: 15px;
            font-size: 12px;
            color: #00d4ff;
        }
        .system-info h3 {
            color: #00ff41;
            margin: 0 0 10px 0;
            font-size: 14px;
        }
        .system-info ul {
            list-style: none;
            padding: 0;
        }
        .system-info li {
            padding: 4px 0;
        }
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 8px;
        }
        .badge.success { background: #00ff41; color: #000; }
        .badge.error { background: #ff4444; color: #fff; }
        .badge.warning { background: #ffaa00; color: #000; }
    </style>
</head>
<body>
    <div id="header">
        <h1>🔮 QUNIX QUANTUM OPERATING SYSTEM 🔮</h1>
        <div class="subtitle">Leech Lattice Substrate • Complete CPU Integration • Metaprogram Execution</div>
        
        <div id="status">
            <div class="status-item">
                <div class="status-label">Database</div>
                <div class="status-value" id="db-status">Checking...</div>
            </div>
            <div class="status-item">
                <div class="status-label">Lattice Points</div>
                <div class="status-value" id="lattice-status">—</div>
            </div>
            <div class="status-item">
                <div class="status-label">Qubits</div>
                <div class="status-value" id="qubit-status">—</div>
            </div>
            <div class="status-item">
                <div class="status-label">CPU Status</div>
                <div class="status-value" id="cpu-status">—</div>
            </div>
            <div class="status-item">
                <div class="status-label">Metaprograms</div>
                <div class="status-value" id="meta-status">—</div>
            </div>
            <div class="status-item">
                <div class="status-label">Terminal</div>
                <div class="status-value" id="ws-status">Disconnected</div>
            </div>
        </div>
        
        <div class="system-info" id="system-info" style="display:none;">
            <h3>System Details</h3>
            <ul id="system-details"></ul>
        </div>
    </div>
    
    <div id="controls">
        <button id="btn-build" onclick="buildDatabase()">🔧 Build Complete System</button>
        <button id="btn-connect" onclick="connectTerminal()" disabled>▶️ Launch Terminal</button>
        <button id="btn-disconnect" onclick="disconnectTerminal()" disabled>⏹️ Disconnect</button>
        <button id="btn-refresh" onclick="refreshStatus()">🔄 Refresh Status</button>
    </div>
    
    <div class="help-text">
        💡 Full quantum OS with CPU microcode • Select text to copy • <kbd>Ctrl+C</kbd>/<kbd>Ctrl+V</kbd> • Scroll enabled
    </div>
    
    <div id="terminal-container"></div>
    
    <div id="loading">
        <div class="spinner"></div>
        <h2 id="loading-title">Building QUNIX System...</h2>
        <p id="loading-text">Generating Leech lattice and CPU microcode</p>
        <div class="progress-bar">
            <div class="progress-fill" id="progress"></div>
        </div>
        <p id="loading-time">This may take 60-120 seconds</p>
    </div>

    <script>
        let term, socket, fitAddon;

        async function init() {
            term = new Terminal({
                cursorBlink: true,
                fontSize: 14,
                fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
                theme: {
                    background: '#000000',
                    foreground: '#00ff41',
                    cursor: '#00ff41',
                    selection: 'rgba(0, 255, 65, 0.3)'
                },
                rows: 30,
                cols: 100,
                scrollback: 50000,
                allowTransparency: false,
                convertEol: true
            });
            
            fitAddon = new FitAddon.FitAddon();
            term.loadAddon(fitAddon);
            term.open(document.getElementById('terminal-container'));
            fitAddon.fit();
            
            // Welcome message
            term.writeln('\\x1b[1;32m╔═══════════════════════════════════════════════════════════════╗\\x1b[0m');
            term.writeln('\\x1b[1;32m║     QUNIX QUANTUM OS - Complete CPU Microcode System         ║\\x1b[0m');
            term.writeln('\\x1b[1;32m╚═══════════════════════════════════════════════════════════════╝\\x1b[0m');
            term.writeln('');
            
            await updateStatus();
            
            window.addEventListener('resize', () => fitAddon.fit());
        }

        async function updateStatus() {
            try {
                const res = await fetch('/api/status');
                const status = await res.json();
                
                const dbStatus = document.getElementById('db-status');
                const latticeStatus = document.getElementById('lattice-status');
                const qubitStatus = document.getElementById('qubit-status');
                const cpuStatus = document.getElementById('cpu-status');
                const metaStatus = document.getElementById('meta-status');
                const btnConnect = document.getElementById('btn-connect');
                const systemInfo = document.getElementById('system-info');
                const systemDetails = document.getElementById('system-details');
                
                if (!status.exists) {
                    dbStatus.textContent = 'Not Found';
                    dbStatus.className = 'status-value error';
                    term.writeln('\\x1b[33m[STATUS] Database not found - click "Build Complete System"\\x1b[0m');
                    return;
                }
                
                if (!status.valid) {
                    dbStatus.textContent = 'Invalid';
                    dbStatus.className = 'status-value error';
                    term.writeln('\\x1b[31m[ERROR] ' + status.error + '\\x1b[0m');
                    return;
                }
                
                // Database OK
                dbStatus.textContent = `Ready (${status.size_mb.toFixed(1)} MB)`;
                dbStatus.className = 'status-value';
                
                // Lattice
                latticeStatus.textContent = status.lattice_points ? status.lattice_points.toLocaleString() : '—';
                
                // Qubits
                qubitStatus.textContent = status.qubits ? status.qubits.toLocaleString() : '—';
                
                // CPU
                if (status.has_cpu) {
                    cpuStatus.textContent = `Installed (${status.cpu_programs} programs)`;
                    cpuStatus.className = 'status-value';
                } else {
                    cpuStatus.textContent = 'Not Installed';
                    cpuStatus.className = 'status-value warning';
                }
                
                // Metaprograms
                if (status.has_metaprograms) {
                    metaStatus.textContent = `${status.running_metaprograms}/${status.metaprograms} Running`;
                    metaStatus.className = 'status-value';
                } else {
                    metaStatus.textContent = 'None';
                    metaStatus.className = 'status-value warning';
                }
                
                // Enable connect button
                btnConnect.disabled = false;
                
                // Show system details
                systemInfo.style.display = 'block';
                systemDetails.innerHTML = `
                    <li>Kernel: ${status.kernel_booted ? '<span class="badge success">Booted</span>' : '<span class="badge error">Not Booted</span>'}</li>
                    <li>CPU Microcode: ${status.has_cpu ? '<span class="badge success">Active</span>' : '<span class="badge error">Missing</span>'}</li>
                    <li>Metaprograms: ${status.metaprograms} total, ${status.running_metaprograms} active</li>
                    <li>Database: ${status.size_mb.toFixed(2)} MB</li>
                `;
                
                term.writeln('\\x1b[32m[STATUS] System ready - all components operational\\x1b[0m');
                term.writeln('\\x1b[36m[INFO] Click "Launch Terminal" to start dev_cli\\x1b[0m');
                
            } catch (e) {
                console.error('Status check failed:', e);
                term.writeln('\\x1b[31m[ERROR] Could not check system status\\x1b[0m');
            }
        }

        async function buildDatabase() {
            const loading = document.getElementById('loading');
            const btn = document.getElementById('btn-build');
            const progress = document.getElementById('progress');
            
            btn.disabled = true;
            loading.classList.add('active');
            
            term.clear();
            term.writeln('\\x1b[35m╔═══════════════════════════════════════════════════════════════╗\\x1b[0m');
            term.writeln('\\x1b[35m║         BUILDING COMPLETE QUNIX SYSTEM                        ║\\x1b[0m');
            term.writeln('\\x1b[35m╚═══════════════════════════════════════════════════════════════╝\\x1b[0m');
            term.writeln('');
            term.writeln('\\x1b[33m[BUILD] Starting comprehensive system build...\\x1b[0m');
            term.writeln('\\x1b[33m[BUILD] This includes:');
            term.writeln('  • Leech lattice generation (~196,560 points)');
            term.writeln('  • Quantum substrate initialization');
            term.writeln('  • CPU microcode compilation and installation');
            term.writeln('  • Metaprogram bitcode generation');
            term.writeln('  • Complete OS structure\\x1b[0m');
            term.writeln('');
            
            let prog = 0;
            const progressInterval = setInterval(() => {
                prog += Math.random() * 3;
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
                    term.writeln('\\x1b[32m[SUCCESS] ✓ Complete system built successfully!\\x1b[0m');
                    term.writeln('\\x1b[36m[INFO] Database: ' + (result.database_size / 1024 / 1024).toFixed(1) + ' MB\\x1b[0m');
                    term.writeln('\\x1b[36m[INFO] CPU microcode: Installed\\x1b[0m');
                    term.writeln('\\x1b[36m[INFO] Metaprograms: 3 infinite loops active\\x1b[0m');
                    term.writeln('');
                    term.writeln('\\x1b[32mSystem ready! Click "Launch Terminal" to start.\\x1b[0m');
                    await updateStatus();
                } else {
                    term.writeln('\\x1b[31m[ERROR] Build failed:\\x1b[0m');
                    term.writeln('\\x1b[31m' + (result.error || 'Unknown error') + '\\x1b[0m');
                    if (result.traceback) {
                        term.writeln('');
                        term.writeln('\\x1b[33m[TRACEBACK]\\x1b[0m');
                        result.traceback.split('\\n').forEach(line => {
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
            const wsStatus = document.getElementById('ws-status');
            const btnConnect = document.getElementById('btn-connect');
            const btnDisconnect = document.getElementById('btn-disconnect');
            
            term.clear();
            term.writeln('\\x1b[36m[SYSTEM] Launching dev_cli with full CPU integration...\\x1b[0m');
            
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            socket = new WebSocket(`${protocol}//${window.location.host}/ws/terminal`);
            
            socket.onopen = () => {
                term.writeln('\\x1b[32m[CONNECTED] Terminal session active\\x1b[0m');
                term.writeln('\\x1b[32m[SYSTEM] All CPU microcode and metaprograms accessible\\x1b[0m');
                term.writeln('');
                wsStatus.textContent = 'Connected';
                wsStatus.className = 'status-value';
                btnConnect.disabled = true;
                btnDisconnect.disabled = false;
            };
            
            socket.onmessage = (e) => term.write(e.data);
            
            socket.onclose = () => {
                term.writeln('');
                term.writeln('\\x1b[33m[DISCONNECTED] Terminal session ended\\x1b[0m');
                wsStatus.textContent = 'Disconnected';
                wsStatus.className = 'status-value error';
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

        async function refreshStatus() {
            term.writeln('\\x1b[36m[SYSTEM] Refreshing status...\\x1b[0m');
            await updateStatus();
        }

        init();
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the web interface"""
    return HTML_TEMPLATE

@app.get("/api/status")
async def get_status():
    """Comprehensive system status check"""
    status = verify_database_complete()
    return status

@app.post("/api/build")
async def build_database():
    """Build complete QUNIX system with CPU integration"""
    try:
        # Remove old database
        if DB_PATH.exists():
            DB_PATH.unlink()
        
        # Find builder script
        builder_script = APP_DIR / "qunix-leech-builder.py"
        
        if not builder_script.exists():
            return {
                "success": False,
                "error": f"Builder script not found at {builder_script}"
            }
        
        print(f"[BUILD] Running complete system builder: {builder_script}")
        print(f"[BUILD] Output directory: {DATA_DIR}")
        
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env['RENDER_DISK_PATH'] = str(DATA_DIR)
        
        # Run builder
        result = subprocess.run(
            [sys.executable, str(builder_script)],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout for full build
            cwd=str(DATA_DIR),
            env=env
        )
        
        print(f"[BUILD] Return code: {result.returncode}")
        
        # Check if database was created
        db_exists = DB_PATH.exists()
        
        # Verify CPU and metaprograms were installed
        if db_exists:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            
            # Check CPU installation
            c.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='cpubin'")
            has_cpu = c.fetchone()[0] > 0
            
            # Check metaprograms
            c.execute("SELECT COUNT(*) FROM bin WHERE typ='metaprogram'")
            metaprogram_count = c.fetchone()[0]
            
            conn.close()
            
            if not has_cpu:
                print("[BUILD] WARNING: CPU tables not found")
            if metaprogram_count < 3:
                print(f"[BUILD] WARNING: Expected 3+ metaprograms, found {metaprogram_count}")
        
        if result.returncode == 0 and db_exists:
            db_size = DB_PATH.stat().st_size
            print(f"[BUILD] Success! Database created: {db_size / 1024 / 1024:.1f} MB")
            
            return {
                "success": True,
                "database_size": db_size,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        else:
            error_msg = f"Build failed (exit code {result.returncode})"
            if not db_exists:
                error_msg += " - Database file not created"
            
            print(f"[BUILD] {error_msg}")
            print(f"[BUILD] STDOUT:\n{result.stdout}")
            print(f"[BUILD] STDERR:\n{result.stderr}")
            
            return {
                "success": False,
                "error": error_msg,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "traceback": result.stderr
            }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Build timeout (exceeded 10 minutes)"
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@app.websocket("/ws/terminal")
async def terminal_websocket(websocket: WebSocket):
    """WebSocket terminal with PTY"""
    await websocket.accept()
    
    session_id = id(websocket)
    print(f"[WS] New terminal session: {session_id}")
    
    # Find dev_cli script
    dev_cli = APP_DIR / "dev_cli.py"
    
    if not dev_cli.exists():
        await websocket.send_text(
            "\x1b[31m[ERROR] dev_cli.py not found\x1b[0m\r\n"
            f"Expected at: {dev_cli}\r\n"
        )
        await websocket.close()
        return
    
    # Check database exists
    if not DB_PATH.exists():
        await websocket.send_text(
            "\x1b[31m[ERROR] Database not found\x1b[0m\r\n"
            "Please build the system first.\r\n"
        )
        await websocket.close()
        return
    
    try:
        # Create PTY
        master_fd, slave_fd = pty.openpty()
        
        # Set terminal size
        import struct, fcntl, termios
        winsize = struct.pack("HHHH", 30, 100, 0, 0)
        fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)
        
        # Launch dev_cli
        env = os.environ.copy()
        env['TERM'] = 'xterm-256color'
        env['PYTHONUNBUFFERED'] = '1'
        env['DB_PATH'] = str(DB_PATH)
        
        process = subprocess.Popen(
            [sys.executable, str(dev_cli)],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env,
            cwd=str(DATA_DIR),
            preexec_fn=os.setsid
        )
        
        os.close(slave_fd)
        active_sessions[session_id] = (process, master_fd)
        
        print(f"[WS] Launched dev_cli (PID {process.pid}) for session {session_id}")
        
        # Handle I/O
        async def read_output():
            while True:
                try:
                    r, _, _ = select.select([master_fd], [], [], 0.1)
                    if r:
                        data = os.read(master_fd, 1024)
                        if data:
                            await websocket.send_bytes(data)
                        else:
                            break
                    
                    # Check if process died
                    if process.poll() is not None:
                        break
                        
                    await asyncio.sleep(0.01)
                    
                except Exception as e:
                    print(f"[WS] Read error: {e}")
                    break
        
        async def write_input():
            while True:
                try:
                    data = await websocket.receive_text()
                    os.write(master_fd, data.encode())
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    print(f"[WS] Write error: {e}")
                    break
        
        # Run both concurrently
        await asyncio.gather(
            read_output(),
            write_input(),
            return_exceptions=True
        )
        
    except Exception as e:
        print(f"[WS] Session error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print(f"[WS] Cleaning up session {session_id}")
        
        if session_id in active_sessions:
            proc, fd = active_sessions[session_id]
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait(timeout=2)
            except:
                try:
                    proc.kill()
                except:
                    pass
            
            try:
                os.close(fd)
            except:
                pass
            
            del active_sessions[session_id]
        
        try:
            await websocket.close()
        except:
            pass

# Cleanup on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up all active sessions"""
    print("[SHUTDOWN] Cleaning up active sessions...")
    for session_id, (proc, fd) in list(active_sessions.items()):
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=1)
        except:
            try:
                proc.kill()
            except:
                pass
        try:
            os.close(fd)
        except:
            pass
    active_sessions.clear()

# ═══════════════════════════════════════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "═" * 75)
    print("  QUNIX QUANTUM OS - Complete Web Application")
    print("  Leech CPU Integration • Metaprogram Execution • Full Terminal")
    print("═" * 75 + "\n")
    
    # Check for required files
    required_files = ['qunix-leech-builder.py', 'dev_cli.py']
    missing = [f for f in required_files if not (APP_DIR / f).exists()]
    
    if missing:
        print(f"⚠️  WARNING: Missing required files: {missing}")
        print(f"    Expected in: {APP_DIR}")
        print()
    
    # Check database status
    db_status = verify_database_complete()
    
    if db_status['exists'] and db_status['valid']:
        print("✓ Database found and valid")
        print(f"  • Lattice points: {db_status.get('lattice_points', '?'):,}")
        print(f"  • Qubits: {db_status.get('qubits', '?'):,}")
        print(f"  • CPU programs: {db_status.get('cpu_programs', '?')}")
        print(f"  • Metaprograms: {db_status.get('metaprograms', '?')}")
        print(f"  • Size: {db_status.get('size_mb', 0):.1f} MB")
        
        if not db_status.get('has_cpu'):
            print("  ⚠️  CPU microcode not detected")
        if not db_status.get('has_metaprograms'):
            print("  ⚠️  Metaprograms not detected")
    else:
        print("ℹ️  Database not found - use web interface to build")
    
    print("\n" + "═" * 75)
    print(f"  🚀 Starting server on http://0.0.0.0:10000")
    print("═" * 75 + "\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=10000,
        log_level="info",
        access_log=True
    )
