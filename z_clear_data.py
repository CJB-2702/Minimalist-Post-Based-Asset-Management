#!/usr/bin/env python3
"""
Script to clean up Python cache files and database files
"""

from pathlib import Path
import shutil

def clear_data():
    """Recursively delete all __pycache__ directories and .db files"""
    print("=== Cleaning up Python cache and database files ===")
    
    # Get current directory
    current_dir = Path.cwd()
    print(f"Cleaning directory: {current_dir}")
    
    # Find and remove __pycache__ directories
    print("\n1. Removing __pycache__ directories...")
    pycache_count = 0
    for pycache_dir in current_dir.rglob('__pycache__'):
        try:
            shutil.rmtree(pycache_dir)
            print(f"   ✓ Removed: {pycache_dir}")
            pycache_count += 1
        except Exception as e:
            print(f"   ✗ Failed to remove {pycache_dir}: {e}")
    
    print(f"   Total __pycache__ directories removed: {pycache_count}")
    
    # Find and remove .db files
    print("\n2. Removing .db files...")
    db_count = 0
    for db_file in current_dir.rglob('*.db'):
        try:
            db_file.unlink()
            print(f"   ✓ Removed: {db_file}")
            db_count += 1
        except Exception as e:
            print(f"   ✗ Failed to remove {db_file}: {e}")
    
    print(f"   Total .db files removed: {db_count}")
    
    # Also remove .pyc files (compiled Python files)
    print("\n3. Removing .pyc files...")
    pyc_count = 0
    for pyc_file in current_dir.rglob('*.pyc'):
        try:
            pyc_file.unlink()
            print(f"   ✓ Removed: {pyc_file}")
            pyc_count += 1

            
        except Exception as e:
            print(f"   ✗ Failed to remove {pyc_file}: {e}")
    
    print(f"   Total .pyc files removed: {pyc_count}")

    # Also remove .pyc files (compiled Python files)
    print("\n3. Removing .log files...")
    log_count = 0
    for log_file in current_dir.rglob('*.log'):
        try:
            log_file.unlink()
            print(f"   ✓ Removed: {log_file}")
            log_count += 1
        except Exception as e:
            print(f"   ✗ Failed to remove {log_file}: {e}")
    
    print(f"   Total .log files removed: {log_count}")
    
    # Summary
    total_removed = pycache_count + db_count + pyc_count
    print(f"\n=== Cleanup Complete ===")
    print(f"Total items removed: {total_removed}")
    print(f"  - __pycache__ directories: {pycache_count}")
    print(f"  - .db files: {db_count}")
    print(f"  - .pyc files: {pyc_count}")
    
    return total_removed

if __name__ == '__main__':
    clear_data() 