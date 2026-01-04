
#!/usr/bin/env python3
"""
QUNIX Web Interface
Flask app for visualizing and interacting with the quantum OS
"""

import os
import sqlite3
import json
import time
from pathlib import Path
from flask import Flask, render_template, jsonify, request
import numpy as np

# ═══════════════════════════════════════════════════════════════════════════
# DATABASE PATH CONFIGURATION - MATCHES BUILDER AND DEV_CLI
# ═══════════════════════════════════════════════════════════════════════════

RENDER_DISK_PATH = os.environ.get('RENDER_DISK_PATH', '/data')
DATA_DIR = Path(RENDER_DISK_PATH)

# Fallback to current directory if /data not writable
if not DATA_DIR.exists() or not os.access(str(DATA_DIR), os.W_OK):
    print(f"⚠ {DATA_DIR} not accessible, using current directory")
    DATA_DIR = Path.cwd()

DB_PATH = DATA_DIR / "qunix_leech.db"

print(f"Database location: {DB_PATH}")

# Table names
T_LAT="lat";T_PQB="pqb";T_TRI="tri";T_PRC="prc";T_THR="thr";T_MEM="mem"
T_SYS="sys";T_INT="int";T_SIG="sig";T_IPC="ipc";T_PIP="pip";T_SKT="skt"
T_FIL="fil";T_INO="ino";T_DIR="dir";T_NET="net";T_QMS="qms";T_ENT="ent"
T_CLK="clk";T_REG="reg";T_INS="ins";T_STK="stk";T_HEP="hep";T_TLB="tlb"
T_PGT="pgt";T_BIN="bin";T_QEX="qex"

app = Flask(__name__)

def get_db():
    """Get database connection"""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}. Run qunix-leech-builder.py first.")
    return sqlite3.connect(str(DB_PATH))


# ═══════════════════════════════════════════════════════════════════════════
# WEB ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """Get system status"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get counts
        c.execute(f'SELECT COUNT(*) FROM {T_LAT}')
        lattice_count = c.fetchone()[0]
        
        c.execute(f'SELECT COUNT(*) FROM {T_PQB}')
        qubit_count = c.fetchone()[0]
        
        c.execute(f'SELECT COUNT(*) FROM {T_TRI}')
        triangle_count = c.fetchone()[0]
        
        c.execute(f'SELECT COUNT(*) FROM {T_ENT}')
        entanglement_count = c.fetchone()[0]
        
        c.execute(f'SELECT COUNT(*) FROM {T_BIN}')
        program_count = c.fetchone()[0]
        
        c.execute(f'SELECT COUNT(*) FROM {T_PRC}')
        process_count = c.fetchone()[0]
        
        # Get metadata
        c.execute("SELECT key, val FROM meta")
        metadata = dict(c.fetchall())
        
        # Get kernel state
        c.execute("SELECT val FROM meta WHERE key='kernel_state'")
        row = c.fetchone()
        kernel_state = row[0] if row else "NOT_BOOTED"
        
        conn.close()
        
        return jsonify({
            'success': True,
            'lattice_points': lattice_count,
            'qubits': qubit_count,
            'triangles': triangle_count,
            'entanglements': entanglement_count,
            'programs': program_count,
            'processes': process_count,
            'kernel_state': kernel_state,
            'metadata': metadata,
            'database_path': str(DB_PATH),
            'database_size': os.path.getsize(DB_PATH) if DB_PATH.exists() else 0
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/qubits')
def api_qubits():
    """Get qubit information"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        c.execute(f'''
            SELECT qid, lid, typ, ar, ai, br, bi, gat, adr
            FROM {T_PQB}
            ORDER BY qid
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        qubits = []
        for row in c.fetchall():
            qid, lid, typ, ar, ai, br, bi, gate, adr = row
            alpha = complex(ar, ai)
            beta = complex(br, bi)
            prob_0 = abs(alpha)**2
            prob_1 = abs(beta)**2
            
            qubits.append({
                'qid': qid,
                'lid': lid,
                'type': typ,
                'alpha_real': ar,
                'alpha_imag': ai,
                'beta_real': br,
                'beta_imag': bi,
                'prob_0': prob_0,
                'prob_1': prob_1,
                'gate': gate,
                'address': adr
            })
        
        conn.close()
        
        return jsonify({'success': True, 'qubits': qubits})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/qubit/<int:qid>')
def api_qubit_detail(qid):
    """Get detailed qubit information"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute(f'''
            SELECT qid, lid, typ, ar, ai, br, bi, phs, gat, adr, bps
            FROM {T_PQB}
            WHERE qid = ?
        ''', (qid,))
        
        row = c.fetchone()
        
        if not row:
            return jsonify({'success': False, 'error': 'Qubit not found'}), 404
        
        qid, lid, typ, ar, ai, br, bi, phs, gate, adr, bps = row
        alpha = complex(ar, ai)
        beta = complex(br, bi)
        
        # Get entanglements
        c.execute(f'''
            SELECT qb, typ, str FROM {T_ENT} WHERE qa = ?
            UNION
            SELECT qa, typ, str FROM {T_ENT} WHERE qb = ?
        ''', (qid, qid))
        
        entanglements = []
        for other_qid, ent_type, strength in c.fetchall():
            entanglements.append({
                'qubit': other_qid,
                'type': ent_type,
                'strength': strength
            })
        
        # Get lattice coordinates
        c.execute(f'SELECT crd, nrm FROM {T_LAT} WHERE lid = ?', (lid,))
        lat_row = c.fetchone()
        
        coords = None
        norm = None
        if lat_row:
            import zlib
            crd_blob, norm = lat_row
            coord_array = np.frombuffer(zlib.decompress(crd_blob), dtype=np.float32)
            coords = coord_array.tolist()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'qubit': {
                'qid': qid,
                'lid': lid,
                'type': typ,
                'alpha': {'real': ar, 'imag': ai},
                'beta': {'real': br, 'imag': bi},
                'prob_0': abs(alpha)**2,
                'prob_1': abs(beta)**2,
                'phase': phs,
                'gate': gate,
                'address': adr,
                'basis': bps,
                'entanglements': entanglements,
                'lattice_coords': coords[:10] if coords else None,  # First 10 dims
                'lattice_norm': norm
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/entanglements')
def api_entanglements():
    """Get entanglement network"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        limit = int(request.args.get('limit', 500))
        
        c.execute(f'''
            SELECT eid, qa, qb, typ, str, tms
            FROM {T_ENT}
            ORDER BY eid DESC
            LIMIT ?
        ''', (limit,))
        
        entanglements = []
        for eid, qa, qb, typ, strength, tms in c.fetchall():
            entanglements.append({
                'id': eid,
                'qubit_a': qa,
                'qubit_b': qb,
                'type': typ,
                'strength': strength,
                'timestamp': tms
            })
        
        conn.close()
        
        return jsonify({'success': True, 'entanglements': entanglements})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/programs')
def api_programs():
    """Get compiled programs"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute(f'''
            SELECT bid, nam, typ, size, loop_enabled, crt
            FROM {T_BIN}
            ORDER BY bid
        ''')
        
        programs = []
        for bid, nam, typ, size, loop_enabled, crt in c.fetchall():
            programs.append({
                'bid': bid,
                'name': nam,
                'type': typ,
                'size': size,
                'loop_enabled': bool(loop_enabled),
                'created': crt
            })
        
        conn.close()
        
        return jsonify({'success': True, 'programs': programs})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/metaprograms')
def api_metaprograms():
    """Get metaprogram status"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get metaprograms
        c.execute(f'''
            SELECT bid, nam, typ, size, loop_enabled, crt
            FROM {T_BIN}
            WHERE typ = 'metaprogram'
            ORDER BY bid
        ''')
        
        metaprograms = []
        for bid, nam, typ, size, loop_enabled, crt in c.fetchall():
            # Get linked process
            c.execute(f'''
                SELECT p.pid, p.sta, l.iteration, l.continue_flag
                FROM {T_PRC} p
                JOIN loop_state l ON p.pid = l.pid
                WHERE l.bid = ?
            ''', (bid,))
            
            proc_row = c.fetchone()
            
            if proc_row:
                pid, status, iteration, cont_flag = proc_row
            else:
                pid = None
                status = 'NOT_LINKED'
                iteration = 0
                cont_flag = 0
            
            # Get mutation count
            c.execute('SELECT COUNT(*) FROM mutation_history WHERE source_bid = ?', (bid,))
            mutation_count = c.fetchone()[0]
            
            metaprograms.append({
                'bid': bid,
                'name': nam,
                'type': typ,
                'size': size,
                'loop_enabled': bool(loop_enabled),
                'created': crt,
                'pid': pid,
                'status': status,
                'iteration': iteration,
                'running': bool(cont_flag),
                'mutations': mutation_count
            })
        
        conn.close()
        
        return jsonify({'success': True, 'metaprograms': metaprograms})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/processes')
def api_processes():
    """Get process list"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute(f'''
            SELECT pid, nam, sta, pri, crt
            FROM {T_PRC}
            ORDER BY pid
        ''')
        
        processes = []
        for pid, nam, sta, pri, crt in c.fetchall():
            # Get thread info
            c.execute(f'''
                SELECT tid, pc, sp
                FROM {T_THR}
                WHERE pid = ?
            ''', (pid,))
            
            threads = []
            for tid, pc, sp in c.fetchall():
                threads.append({
                    'tid': tid,
                    'pc': pc,
                    'sp': sp
                })
            
            processes.append({
                'pid': pid,
                'name': nam,
                'status': sta,
                'priority': pri,
                'created': crt,
                'threads': threads
            })
        
        conn.close()
        
        return jsonify({'success': True, 'processes': processes})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/measurements')
def api_measurements():
    """Get quantum measurements"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        limit = int(request.args.get('limit', 100))
        
        c.execute(f'''
            SELECT mid, typ, cnt, tms
            FROM {T_QMS}
            ORDER BY mid DESC
            LIMIT ?
        ''', (limit,))
        
        measurements = []
        for mid, typ, cnt, tms in c.fetchall():
            try:
                content = json.loads(cnt)
            except:
                content = cnt
            
            measurements.append({
                'id': mid,
                'type': typ,
                'content': content,
                'timestamp': tms
            })
        
        conn.close()
        
        return jsonify({'success': True, 'measurements': measurements})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/kernel_log')
def api_kernel_log():
    """Get kernel log entries"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        limit = int(request.args.get('limit', 50))
        
        c.execute('''
            SELECT log_id, timestamp, event_type, details, qubits_involved
            FROM kernel_log
            ORDER BY log_id DESC
            LIMIT ?
        ''', (limit,))
        
        logs = []
        for log_id, ts, evt, details, qubits in c.fetchall():
            try:
                qubit_list = json.loads(qubits) if qubits else []
            except:
                qubit_list = []
            
            logs.append({
                'id': log_id,
                'timestamp': ts,
                'event_type': evt,
                'details': details,
                'qubits': qubit_list
            })
        
        conn.close()
        
        return jsonify({'success': True, 'logs': logs})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/output_channel')
def api_output_channel():
    """Get output channel messages"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        limit = int(request.args.get('limit', 100))
        
        c.execute('''
            SELECT msg_id, timestamp, source, level, message
            FROM output_channel
            ORDER BY msg_id DESC
            LIMIT ?
        ''', (limit,))
        
        messages = []
        for msg_id, ts, src, lvl, msg in c.fetchall():
            messages.append({
                'id': msg_id,
                'timestamp': ts,
                'source': src,
                'level': lvl,
                'message': msg
            })
        
        conn.close()
        
        return jsonify({'success': True, 'messages': messages})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/patches')
def api_patches():
    """Get patch status"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            SELECT patch_id, target_prog, description, applied, sandbox_tested, tms
            FROM patches
            ORDER BY patch_id DESC
            LIMIT 50
        ''')
        
        patches = []
        for patch_id, target, desc, applied, tested, tms in c.fetchall():
            patches.append({
                'id': patch_id,
                'target': target,
                'description': desc,
                'applied': bool(applied),
                'tested': bool(tested),
                'timestamp': tms
            })
        
        conn.close()
        
        return jsonify({'success': True, 'patches': patches})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/genealogy')
def api_genealogy():
    """Get program genealogy (quine evolution)"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            SELECT vid, parent_bid, child_bid, generation, fitness, tms
            FROM prog_versions
            ORDER BY generation, vid
            LIMIT 100
        ''')
        
        versions = []
        for vid, parent, child, gen, fitness, tms in c.fetchall():
            versions.append({
                'id': vid,
                'parent_bid': parent,
                'child_bid': child,
                'generation': gen,
                'fitness': fitness,
                'timestamp': tms
            })
        
        conn.close()
        
        return jsonify({'success': True, 'versions': versions})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/triangles')
def api_triangles():
    """Get triangle (W-state quadruple) information"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        limit = int(request.args.get('limit', 100))
        
        c.execute(f'''
            SELECT tid, v0, v1, v2, v3, fid, crt
            FROM {T_TRI}
            ORDER BY tid
            LIMIT ?
        ''', (limit,))
        
        triangles = []
        for tid, v0, v1, v2, v3, fid, crt in c.fetchall():
            triangles.append({
                'tid': tid,
                'vertices': [v0, v1, v2, v3],
                'fidelity': fid,
                'created': crt
            })
        
        conn.close()
        
        return jsonify({'success': True, 'triangles': triangles})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        print("Run qunix-leech-builder.py first to build the system")
        exit(1)
    
    print(f"\n{'='*70}")
    print(f"QUNIX Web Interface")
    print(f"{'='*70}")
    print(f"Database: {DB_PATH}")
    print(f"Size: {os.path.getsize(DB_PATH) / 1024 / 1024:.2f} MB")
    print(f"{'='*70}\n")
    
    # Get host and port from environment (for Render deployment)
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    
    app.run(host=host, port=port, debug=True)
