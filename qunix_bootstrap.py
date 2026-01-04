#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║                    QUNIX BOOTSTRAP & PATH MANAGER                         ║
║          Automatic database initialization and path resolution           ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

This script:
  1. Detects available persistent storage locations
  2. Creates database if missing
  3. Runs builder automatically if needed
  4. Launches dev_cli.py with correct environment
"""

import os
import sys
import subprocess
from pathlib import Path
import shutil

# ANSI Colors
class C:
    H='\033[95m';B='\033[94m';C='\033[96m';G='\033[92m';Y='\033[93m'
    R='\033[91m';E='\033[0m';Q='\033[38;5;213m';W='\033[97m';M='\033[35m'
    O='\033[38;5;208m';BOLD='\033[1m';GRAY='\033[90m'


def find_persistent_storage():
    """
    Find the best persistent storage location
    Priority order:
      1. /data (Render.com persistent disk)
      2. /datasets (HuggingFace Spaces)
      3. ~/qunix_data (user home directory)
      4. ./qunix_data (current directory fallback)
    """
    print(f"\n{C.BOLD}{C.C}═══ QUNIX PATH RESOLVER ═══{C.E}\n")
    
    candidates = [
        Path("/data"),
        Path("/datasets"),
        Path.home() / "qunix_data",
        Path.cwd() / "qunix_data"
    ]
    
    for path in candidates:
        print(f"{C.C}Checking: {path}{C.E}")
        
        # Check if exists or can be created
        if path.exists():
            if os.access(str(path), os.W_OK):
                print(f"  {C.G}✓ Exists and writable{C.E}")
                return path
            else:
                print(f"  {C.Y}⚠ Exists but not writable{C.E}")
        else:
            # Try to create it
            try:
                path.mkdir(parents=True, exist_ok=True)
                print(f"  {C.G}✓ Created successfully{C.E}")
                return path
            except Exception as e:
                print(f"  {C.R}✗ Cannot create: {e}{C.E}")
    
    # Absolute fallback
    fallback = Path.cwd()
    print(f"{C.Y}⚠ Using current directory as fallback: {fallback}{C.E}")
    return fallback


def check_database(data_dir: Path) -> bool:
    """Check if database exists and is valid"""
    db_path = data_dir / "qunix_leech.db"
    
    if not db_path.exists():
        return False
    
    # Quick validation - check file size
    size_mb = db_path.stat().st_size / (1024 * 1024)
    
    if size_mb < 0.1:  # Too small to be valid
        print(f"{C.Y}⚠ Database exists but appears invalid (only {size_mb:.2f} MB){C.E}")
        return False
    
    print(f"{C.G}✓ Found valid database: {db_path} ({size_mb:.2f} MB){C.E}")
    return True


def run_builder(data_dir: Path):
    """Run the QUNIX builder to create database"""
    print(f"\n{C.BOLD}{C.M}{'═'*70}{C.E}")
    print(f"{C.BOLD}{C.M}          RUNNING QUNIX BUILDER - FIRST TIME SETUP          {C.E}")
    print(f"{C.BOLD}{C.M}{'═'*70}{C.E}\n")
    
    # Find builder script
    builder_candidates = [
        Path(__file__).parent / "qunix-leech-builder.py",
        Path.cwd() / "qunix-leech-builder.py",
        Path("/opt/render/project/src/qunix-leech-builder.py"),
    ]
    
    builder_path = None
    for candidate in builder_candidates:
        if candidate.exists():
            builder_path = candidate
            break
    
    if not builder_path:
        print(f"{C.R}ERROR: Cannot find qunix-leech-builder.py{C.E}")
        print(f"{C.Y}Searched in:{C.E}")
        for c in builder_candidates:
            print(f"  {c}")
        sys.exit(1)
    
    print(f"{C.C}Using builder: {builder_path}{C.E}\n")
    
    # Set environment variable for builder
    env = os.environ.copy()
    env['RENDER_DISK_PATH'] = str(data_dir)
    
    # Run builder
    try:
        result = subprocess.run(
            [sys.executable, str(builder_path)],
            env=env,
            check=True
        )
        
        print(f"\n{C.BOLD}{C.G}✓ BUILDER COMPLETED SUCCESSFULLY{C.E}\n")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n{C.R}ERROR: Builder failed with code {e.returncode}{C.E}")
        return False
    except Exception as e:
        print(f"\n{C.R}ERROR: {e}{C.E}")
        return False


def launch_dev_cli(data_dir: Path):
    """Launch dev_cli.py with correct environment"""
    print(f"\n{C.BOLD}{C.C}{'═'*70}{C.E}")
    print(f"{C.BOLD}{C.C}          LAUNCHING QUNIX DEVELOPMENT TOOLS          {C.E}")
    print(f"{C.BOLD}{C.C}{'═'*70}{C.E}\n")
    
    # Find dev_cli script
    cli_candidates = [
        Path(__file__).parent / "dev_cli.py",
        Path.cwd() / "dev_cli.py",
        Path("/opt/render/project/src/dev_cli.py"),
    ]
    
    cli_path = None
    for candidate in cli_candidates:
        if candidate.exists():
            cli_path = candidate
            break
    
    if not cli_path:
        print(f"{C.R}ERROR: Cannot find dev_cli.py{C.E}")
        sys.exit(1)
    
    print(f"{C.C}Using CLI: {cli_path}{C.E}")
    print(f"{C.C}Data directory: {data_dir}{C.E}\n")
    
    # Set environment and run
    env = os.environ.copy()
    env['RENDER_DISK_PATH'] = str(data_dir)
    
    try:
        # Pass through any command-line arguments
        args = [sys.executable, str(cli_path)] + sys.argv[1:]
        
        result = subprocess.run(args, env=env)
        return result.returncode
        
    except KeyboardInterrupt:
        print(f"\n{C.Y}Interrupted{C.E}")
        return 130
    except Exception as e:
        print(f"\n{C.R}ERROR: {e}{C.E}")
        return 1


def main():
    """Main bootstrap logic"""
    
    print(f"""
{C.BOLD}{C.W}{'═'*70}{C.E}
{C.BOLD}{C.W}                    QUNIX QUANTUM OS BOOTSTRAP                    {C.E}
{C.BOLD}{C.W}{'═'*70}{C.E}
    """)
    
    # Step 1: Find persistent storage
    data_dir = find_persistent_storage()
    db_path = data_dir / "qunix_leech.db"
    
    print(f"\n{C.BOLD}Configuration:{C.E}")
    print(f"  Data directory: {C.C}{data_dir}{C.E}")
    print(f"  Database path:  {C.C}{db_path}{C.E}")
    
    # Step 2: Check if database exists
    db_exists = check_database(data_dir)
    
    # Step 3: Build if needed
    if not db_exists:
        print(f"\n{C.Y}⚠ Database not found - running builder...{C.E}")
        
        # Ask for confirmation unless in non-interactive mode
        if sys.stdin.isatty():
            response = input(f"\n{C.C}Build QUNIX database now? This will take 30-60 seconds. (y/n): {C.E}")
            if response.lower() != 'y':
                print(f"{C.R}Cannot proceed without database{C.E}")
                sys.exit(1)
        
        if not run_builder(data_dir):
            print(f"\n{C.R}Database build failed{C.E}")
            sys.exit(1)
        
        # Verify it was created
        if not check_database(data_dir):
            print(f"\n{C.R}Database was not created successfully{C.E}")
            sys.exit(1)
    
    # Step 4: Launch dev_cli
    return launch_dev_cli(data_dir)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{C.Y}Bootstrap interrupted{C.E}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{C.R}Fatal error: {e}{C.E}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
