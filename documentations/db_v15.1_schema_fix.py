#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║     QUNIX COMPREHENSIVE SCHEMA RECONCILIATION TOOL v2.0                   ║
║     Recursively find all schema conflicts and fix them                    ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import sqlite3
import sys
import re
from pathlib import Path
from collections import defaultdict

class C:
    G='\033[92m'; R='\033[91m'; Y='\033[93m'; C='\033[96m'
    BOLD='\033[1m'; E='\033[0m'; M='\033[35m'; GRAY='\033[90m'

class SchemaReconciler:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
        self.issues = []
        self.fixes = []
        
    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
    def scan_all_tables(self):
        """Recursively scan all tables and their columns"""
        print(f"\n{C.BOLD}{C.C}╔════════════════════════════════════════════════════════════╗{C.E}")
        print(f"{C.BOLD}{C.C}║  SCANNING ALL TABLES IN DATABASE                          ║{C.E}")
        print(f"{C.BOLD}{C.C}╚════════════════════════════════════════════════════════════╝{C.E}\n")
        
        c = self.conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in c.fetchall()]
        
        table_info = {}
        
        for table in tables:
            c.execute(f"PRAGMA table_info({table})")
            cols = [(row[1], row[2]) for row in c.fetchall()]
            
            c.execute(f"SELECT COUNT(*) FROM {table}")
            count = c.fetchone()[0]
            
            table_info[table] = {
                'columns': cols,
                'count': count
            }
            
            print(f"{C.C}{table:<40}{C.E} {count:>10,} rows")
            for col_name, col_type in cols:
                print(f"  {C.GRAY}├─{C.E} {col_name:<35} {col_type}")
        
        return table_info
    
    def find_qubit_related_items(self, table_info):
        """Find all qubit-related columns and tables"""
        print(f"\n{C.BOLD}{C.C}╔════════════════════════════════════════════════════════════╗{C.E}")
        print(f"{C.BOLD}{C.C}║  FINDING ALL QUBIT-RELATED SCHEMA ITEMS                    ║{C.E}")
        print(f"{C.BOLD}{C.C}╚════════════════════════════════════════════════════════════╝{C.E}\n")
        
        qubit_patterns = [
            r'qubit', r'qbit', r'quantum', r'q_', r'^q$',
            r'require.*qubit', r'allocated', r'allocation'
        ]
        
        qubit_items = defaultdict(list)
        
        for table, info in table_info.items():
            # Check table name
            for pattern in qubit_patterns:
                if re.search(pattern, table, re.IGNORECASE):
                    qubit_items['tables'].append(table)
                    break
            
            # Check column names
            for col_name, col_type in info['columns']:
                for pattern in qubit_patterns:
                    if re.search(pattern, col_name, re.IGNORECASE):
                        qubit_items['columns'].append(f"{table}.{col_name} ({col_type})")
                        break
        
        print(f"{C.C}Qubit-related TABLES ({len(qubit_items['tables'])})::{C.E}")
        for table in sorted(set(qubit_items['tables'])):
            print(f"  • {table}")
        
        print(f"\n{C.C}Qubit-related COLUMNS ({len(qubit_items['columns'])})::{C.E}")
        for col in sorted(set(qubit_items['columns'])):
            print(f"  • {col}")
        
        return qubit_items
    
    def analyze_command_registry_variations(self, table_info):
        """Find all variations of 'requires_qubits' type columns"""
        print(f"\n{C.BOLD}{C.C}╔════════════════════════════════════════════════════════════╗{C.E}")
        print(f"{C.BOLD}{C.C}║  ANALYZING COMMAND REGISTRY VARIATIONS                     ║{C.E}")
        print(f"{C.BOLD}{C.C}╚════════════════════════════════════════════════════════════╝{C.E}\n")
        
        if 'command_registry' not in table_info:
            print(f"{C.R}✗ command_registry table NOT FOUND!{C.E}")
            self.issues.append("command_registry table missing")
            return {}
        
        cols = {col[0]: col[1] for col in table_info['command_registry']['columns']}
        
        print(f"{C.C}Current command_registry columns ({len(cols)}):{C.E}")
        for col_name, col_type in sorted(cols.items()):
            print(f"  • {col_name:<35} {col_type}")
        
        # Find variations of "requires_qubits"
        variations = {
            'requires_qubits': 'requires_qubits',
            'cmd_requires_qubits': 'cmd_requires_qubits', 
            'qubit_count': 'qubit_count',
            'num_qubits': 'num_qubits',
        }
        
        print(f"\n{C.C}Checking for qubit requirement columns:{C.E}")
        found = {}
        for canonical, variant in variations.items():
            if variant in cols:
                print(f"  {C.G}✓{C.E} Found: {variant}")
                found[variant] = cols[variant]
            else:
                print(f"  {C.GRAY}✗{C.E} Missing: {variant}")
        
        return found
    
    def check_handler_table_references(self):
        """Check what columns command_handlers expects"""
        print(f"\n{C.BOLD}{C.C}╔════════════════════════════════════════════════════════════╗{C.E}")
        print(f"{C.BOLD}{C.C}║  ANALYZING COMMAND_HANDLERS REFERENCES                     ║{C.E}")
        print(f"{C.BOLD}{C.C}╚════════════════════════════════════════════════════════════╝{C.E}\n")
        
        c = self.conn.cursor()
        
        # Check if command_handlers exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='command_handlers'")
        if not c.fetchone():
            print(f"{C.R}✗ command_handlers table does NOT exist{C.E}")
            self.issues.append("command_handlers table missing")
            return
        
        c.execute("PRAGMA table_info(command_handlers)")
        cols = {row[1]: row[2] for row in c.fetchall()}
        
        print(f"{C.C}command_handlers columns ({len(cols)}):{C.E}")
        for col_name, col_type in sorted(cols.items()):
            print(f"  • {col_name:<35} {col_type}")
        
        # Check for qubit-related columns in handlers
        handler_qubit_cols = ['requires_qubits', 'qubit_count', 'num_qubits']
        
        print(f"\n{C.C}Checking handler qubit columns:{C.E}")
        for col in handler_qubit_cols:
            if col in cols:
                print(f"  {C.G}✓{C.E} {col}")
            else:
                print(f"  {C.GRAY}✗{C.E} {col} (missing)")
    
    def extract_db_executor_expectations(self):
        """Parse qunix_db_executor.py to see what it expects"""
        print(f"\n{C.BOLD}{C.C}╔════════════════════════════════════════════════════════════╗{C.E}")
        print(f"{C.BOLD}{C.C}║  CHECKING DB_EXECUTOR EXPECTATIONS                         ║{C.E}")
        print(f"{C.BOLD}{C.C}╚════════════════════════════════════════════════════════════╝{C.E}\n")
        
        executor_file = Path('qunix_db_executor.py')
        
        if not executor_file.exists():
            print(f"{C.Y}⚠ qunix_db_executor.py not found in current directory{C.E}")
            return {}
        
        content = executor_file.read_text()
        
        # Find SELECT queries
        select_pattern = r'SELECT\s+(.+?)\s+FROM\s+(\w+)'
        matches = re.findall(select_pattern, content, re.IGNORECASE | re.DOTALL)
        
        expectations = defaultdict(set)
        
        for cols, table in matches:
            # Clean up column list
            cols = cols.replace('\n', ' ').replace(',', ' ')
            col_list = [c.strip() for c in re.split(r'\s+', cols) if c.strip() and c.strip() != 'FROM']
            
            for col in col_list:
                # Remove aliases and functions
                col = re.sub(r'\s+as\s+\w+', '', col, flags=re.IGNORECASE)
                col = re.sub(r'^\w+\((.+)\)$', r'\1', col)
                
                if col and not col.upper() in ['SELECT', 'WHERE', 'AND', 'OR']:
                    expectations[table.lower()].add(col)
        
        print(f"{C.C}DB Executor expects these columns:{C.E}\n")
        for table, cols in sorted(expectations.items()):
            print(f"{C.BOLD}{table}:{C.E}")
            for col in sorted(cols):
                print(f"  • {col}")
            print()
        
        return expectations
    
    def create_unified_schema(self, table_info):
        """Create a unified schema with all necessary columns"""
        print(f"\n{C.BOLD}{C.C}╔════════════════════════════════════════════════════════════╗{C.E}")
        print(f"{C.BOLD}{C.C}║  CREATING UNIFIED SCHEMA FIX                               ║{C.E}")
        print(f"{C.BOLD}{C.C}╚════════════════════════════════════════════════════════════╝{C.E}\n")
        
        c = self.conn.cursor()
        
        # Define canonical schema for command_registry
        canonical_command_registry = {
            'cmd_id': 'INTEGER PRIMARY KEY',
            'cmd_name': 'TEXT NOT NULL',
            'cmd_opcode': 'BLOB',
            'cmd_category': 'TEXT',
            'cmd_description': 'TEXT',
            'cmd_requires_qubits': 'INTEGER DEFAULT 0',  # CANONICAL NAME
            'gate_name': 'TEXT',
            'cmd_enabled': 'INTEGER DEFAULT 1',
            'cmd_use_count': 'INTEGER DEFAULT 0',
            'cmd_last_used': 'REAL',
        }
        
        # Get current columns
        if 'command_registry' in table_info:
            current_cols = {col[0]: col[1] for col in table_info['command_registry']['columns']}
        else:
            current_cols = {}
        
        print(f"{C.C}Adding missing columns to command_registry:{C.E}\n")
        
        for col_name, col_def in canonical_command_registry.items():
            if col_name in current_cols:
                print(f"  {C.G}✓{C.E} {col_name:<30} (exists)")
            else:
                print(f"  {C.Y}+{C.E} {col_name:<30} (adding)")
                
                # Extract just the type and default for ALTER TABLE
                type_match = re.match(r'(\w+(?:\([^)]+\))?)\s*(.*)', col_def)
                if type_match:
                    col_type = type_match.group(1)
                    constraints = type_match.group(2)
                    
                    try:
                        sql = f"ALTER TABLE command_registry ADD COLUMN {col_name} {col_type}"
                        if 'DEFAULT' in constraints:
                            default_match = re.search(r'DEFAULT\s+(\S+)', constraints)
                            if default_match:
                                sql += f" DEFAULT {default_match.group(1)}"
                        
                        c.execute(sql)
                        self.fixes.append(f"Added column: command_registry.{col_name}")
                        print(f"    {C.GRAY}SQL: {sql}{C.E}")
                    except sqlite3.OperationalError as e:
                        print(f"    {C.R}Failed: {e}{C.E}")
                        self.issues.append(f"Could not add {col_name}: {e}")
        
        # Define canonical schema for command_handlers
        canonical_command_handlers = {
            'handler_id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'cmd_id': 'INTEGER NOT NULL',
            'handler_type': 'TEXT NOT NULL',
            'qasm_code': 'TEXT',
            'sql_query': 'TEXT',
            'python_code': 'TEXT',
            'method_name': 'TEXT',
            'context_map': 'TEXT',
            'result_formatter': 'TEXT',
            'priority': 'INTEGER DEFAULT 100',
            'requires_qubits': 'INTEGER DEFAULT 0',  # CANONICAL NAME
            'qubit_count': 'INTEGER DEFAULT 0',
            'enabled': 'INTEGER DEFAULT 1',
        }
        
        # Create command_handlers if missing
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='command_handlers'")
        if not c.fetchone():
            print(f"\n{C.Y}Creating command_handlers table...{C.E}")
            
            cols_def = ', '.join([f"{name} {defn}" for name, defn in canonical_command_handlers.items()])
            c.execute(f"CREATE TABLE command_handlers ({cols_def})")
            self.fixes.append("Created command_handlers table")
            print(f"  {C.G}✓{C.E} Created command_handlers")
        else:
            # Add missing columns to existing table
            c.execute("PRAGMA table_info(command_handlers)")
            current_handler_cols = {row[1]: row[2] for row in c.fetchall()}
            
            print(f"\n{C.C}Adding missing columns to command_handlers:{C.E}\n")
            
            for col_name, col_def in canonical_command_handlers.items():
                if col_name in current_handler_cols:
                    print(f"  {C.G}✓{C.E} {col_name:<30} (exists)")
                else:
                    print(f"  {C.Y}+{C.E} {col_name:<30} (adding)")
                    
                    type_match = re.match(r'(\w+(?:\([^)]+\))?)\s*(.*)', col_def)
                    if type_match:
                        col_type = type_match.group(1)
                        constraints = type_match.group(2)
                        
                        try:
                            sql = f"ALTER TABLE command_handlers ADD COLUMN {col_name} {col_type}"
                            if 'DEFAULT' in constraints:
                                default_match = re.search(r'DEFAULT\s+(\S+)', constraints)
                                if default_match:
                                    sql += f" DEFAULT {default_match.group(1)}"
                            
                            c.execute(sql)
                            self.fixes.append(f"Added column: command_handlers.{col_name}")
                            print(f"    {C.GRAY}SQL: {sql}{C.E}")
                        except sqlite3.OperationalError as e:
                            print(f"    {C.R}Failed: {e}{C.E}")
        
        # Create other essential tables
        print(f"\n{C.C}Creating essential tables:{C.E}\n")
        
        essential_tables = {
            'quantum_command_circuits': """
                CREATE TABLE IF NOT EXISTS quantum_command_circuits (
                    circuit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cmd_name TEXT NOT NULL,
                    circuit_name TEXT,
                    num_qubits INTEGER NOT NULL,
                    qasm_code TEXT NOT NULL,
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                )
            """,
            'cpu_qubit_allocator': """
                CREATE TABLE IF NOT EXISTS cpu_qubit_allocator (
                    qubit_id INTEGER PRIMARY KEY,
                    allocated INTEGER DEFAULT 0,
                    allocated_to_pid INTEGER,
                    allocation_time REAL,
                    usage_count INTEGER DEFAULT 0
                )
            """,
            'command_execution_log': """
                CREATE TABLE IF NOT EXISTS command_execution_log (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cmd_name TEXT,
                    arguments TEXT,
                    execution_time_ms REAL,
                    success INTEGER,
                    return_value TEXT,
                    timestamp REAL DEFAULT (strftime('%s', 'now'))
                )
            """,
        }
        
        for table_name, create_sql in essential_tables.items():
            c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if c.fetchone():
                print(f"  {C.G}✓{C.E} {table_name:<30} (exists)")
            else:
                c.execute(create_sql)
                self.fixes.append(f"Created table: {table_name}")
                print(f"  {C.Y}+{C.E} {table_name:<30} (created)")
        
        self.conn.commit()
    
    def populate_qubit_allocator(self):
        """Populate cpu_qubit_allocator from q table"""
        print(f"\n{C.C}Populating cpu_qubit_allocator...{C.E}")
        
        c = self.conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM cpu_qubit_allocator")
        current_count = c.fetchone()[0]
        
        if current_count > 0:
            print(f"  {C.G}✓{C.E} Already populated ({current_count:,} qubits)")
            return
        
        try:
            c.execute("""
                INSERT INTO cpu_qubit_allocator (qubit_id, allocated, usage_count)
                SELECT i, 0, 0 FROM q
            """)
            self.conn.commit()
            
            c.execute("SELECT COUNT(*) FROM cpu_qubit_allocator")
            count = c.fetchone()[0]
            
            print(f"  {C.G}✓{C.E} Populated with {count:,} qubits from q table")
            self.fixes.append(f"Populated cpu_qubit_allocator with {count} qubits")
        except Exception as e:
            print(f"  {C.R}✗{C.E} Failed: {e}")
            self.issues.append(f"Could not populate cpu_qubit_allocator: {e}")
    
    def verify_executor_queries(self):
        """Test actual queries from db_executor"""
        print(f"\n{C.BOLD}{C.C}╔════════════════════════════════════════════════════════════╗{C.E}")
        print(f"{C.BOLD}{C.C}║  VERIFYING DB_EXECUTOR QUERIES                             ║{C.E}")
        print(f"{C.BOLD}{C.C}╚════════════════════════════════════════════════════════════╝{C.E}\n")
        
        c = self.conn.cursor()
        
        # Test 1: _lookup_command query
        print(f"{C.C}Test 1: _lookup_command() query{C.E}")
        try:
            c.execute("""
                SELECT cmd_id, cmd_name, cmd_opcode, cmd_category, cmd_requires_qubits, gate_name
                FROM command_registry 
                WHERE cmd_name = ? AND cmd_enabled = 1
            """, ('help',))
            row = c.fetchone()
            if row:
                print(f"  {C.G}✓{C.E} Query works! Found: {dict(row)}")
            else:
                print(f"  {C.Y}⚠{C.E} Query works but 'help' command not found")
        except sqlite3.OperationalError as e:
            print(f"  {C.R}✗{C.E} Query FAILED: {e}")
            self.issues.append(f"_lookup_command query failed: {e}")
        
        # Test 2: _get_handler query
        print(f"\n{C.C}Test 2: _get_handler() query{C.E}")
        try:
            c.execute("""
                SELECT handler_id, handler_type, qasm_code, sql_query, python_code,
                       context_map, result_formatter, requires_qubits, qubit_count
                FROM command_handlers
                WHERE cmd_id = ? AND enabled = 1
                ORDER BY priority DESC
                LIMIT 1
            """, (1,))
            print(f"  {C.G}✓{C.E} Query syntax is valid")
        except sqlite3.OperationalError as e:
            print(f"  {C.R}✗{C.E} Query FAILED: {e}")
            self.issues.append(f"_get_handler query failed: {e}")
        
        # Test 3: Qubit allocator query
        print(f"\n{C.C}Test 3: Qubit allocator query{C.E}")
        try:
            c.execute("""
                SELECT qubit_id FROM cpu_qubit_allocator
                WHERE allocated = 0 LIMIT 5
            """)
            rows = c.fetchall()
            print(f"  {C.G}✓{C.E} Found {len(rows)} free qubits")
        except sqlite3.OperationalError as e:
            print(f"  {C.R}✗{C.E} Query FAILED: {e}")
            self.issues.append(f"Qubit allocator query failed: {e}")
    
    def print_summary(self):
        """Print final summary"""
        print(f"\n{C.BOLD}{'='*70}{C.E}")
        print(f"{C.BOLD}{C.C}RECONCILIATION SUMMARY{C.E}")
        print(f"{C.BOLD}{'='*70}{C.E}\n")
        
        if self.fixes:
            print(f"{C.G}Applied {len(self.fixes)} fixes:{C.E}")
            for i, fix in enumerate(self.fixes, 1):
                print(f"  {i}. {fix}")
        else:
            print(f"{C.Y}No fixes were needed{C.E}")
        
        if self.issues:
            print(f"\n{C.R}Found {len(self.issues)} issues:{C.E}")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
        else:
            print(f"\n{C.G}No issues found!{C.E}")
        
        print(f"\n{C.BOLD}{'='*70}{C.E}")
        
        if not self.issues:
            print(f"{C.BOLD}{C.G}✅ DATABASE IS READY!{C.E}\n")
            print(f"You can now run:")
            print(f"  python qunix_cpu.py --db {self.db_path}\n")
        else:
            print(f"{C.BOLD}{C.Y}⚠ SOME ISSUES REMAIN{C.E}\n")
            print(f"Consider running:")
            print(f"  python db_patch_cpu_1.py {self.db_path}\n")
    
    def close(self):
        if self.conn:
            self.conn.commit()
            self.conn.close()

def main():
    if len(sys.argv) < 2:
        print(f"\nUsage: {sys.argv[0]} <database_path>\n")
        sys.exit(1)
    
    db_path = Path(sys.argv[1])
    
    if not db_path.exists():
        print(f"\n{C.R}✗ Database not found: {db_path}{C.E}\n")
        sys.exit(1)
    
    print(f"\n{C.BOLD}{C.M}╔══════════════════════════════════════════════════════════════╗{C.E}")
    print(f"{C.BOLD}{C.M}║  QUNIX COMPREHENSIVE SCHEMA RECONCILIATION v2.0              ║{C.E}")
    print(f"{C.BOLD}{C.M}╚══════════════════════════════════════════════════════════════╝{C.E}")
    
    print(f"\nDatabase: {C.C}{db_path}{C.E}")
    print(f"Size: {C.C}{db_path.stat().st_size / (1024*1024):.1f} MB{C.E}")
    
    reconciler = SchemaReconciler(db_path)
    
    try:
        reconciler.connect()
        
        # Step 1: Scan everything
        table_info = reconciler.scan_all_tables()
        
        # Step 2: Find all qubit-related items
        qubit_items = reconciler.find_qubit_related_items(table_info)
        
        # Step 3: Analyze command_registry variations
        qubit_cols = reconciler.analyze_command_registry_variations(table_info)
        
        # Step 4: Check handler table
        reconciler.check_handler_table_references()
        
        # Step 5: Extract executor expectations
        executor_expectations = reconciler.extract_db_executor_expectations()
        
        # Step 6: Create unified schema
        reconciler.create_unified_schema(table_info)
        
        # Step 7: Populate qubit allocator
        reconciler.populate_qubit_allocator()
        
        # Step 8: Verify all queries work
        reconciler.verify_executor_queries()
        
        # Step 9: Print summary
        reconciler.print_summary()
        
    except KeyboardInterrupt:
        print(f"\n{C.Y}Interrupted{C.E}\n")
        return 130
    except Exception as e:
        print(f"\n{C.R}Error: {e}{C.E}\n")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        reconciler.close()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())