#!/usr/bin/env python3
"""
Script to clean up Python cache files, database files, and attachments

This script is automatically run on Docker container startup via docker-entrypoint.sh
to ensure a clean runtime environment. It removes:
- __pycache__ directories
- .pyc files (compiled Python)
- .log files
- .db files (database files - ALL DATA WILL BE LOST)
- All files in instance/large_attachments/ (ALL ATTACHMENTS WILL BE LOST)

⚠️  WARNING: This script DELETES ALL DATABASE DATA AND ATTACHMENTS!
This is useful for development/testing environments that need a fresh start daily.
"""

from pathlib import Path
import shutil

def clear_data():
    """Recursively delete cache files, database files, and attachments"""
    print("=== Cleaning up Python cache, database files, and attachments ===")
    print("⚠️  WARNING: All database data and attachments will be deleted!")
    
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

    # Remove .log files
    print("\n4. Removing .log files...")
    log_count = 0
    for log_file in current_dir.rglob('*.log'):
        try:
            log_file.unlink()
            print(f"   ✓ Removed: {log_file}")
            log_count += 1
        except Exception as e:
            print(f"   ✗ Failed to remove {log_file}: {e}")
    
    print(f"   Total .log files removed: {log_count}")
    
    # Remove database files from instance directory
    print("\n5. Removing database files from instance/ (.db, .sqlite, .sqlite3)...")
    db_patterns = ['*.db', '*.sqlite', '*.sqlite3']
    db_files_removed = 0
    instance_dir = current_dir / 'instance'
    if instance_dir.exists():
        for pattern in db_patterns:
            for db_file in instance_dir.rglob(pattern):
                try:
                    db_file.unlink()
                    print(f"   ✓ Removed: {db_file}")
                    db_files_removed += 1
                except Exception as e:
                    print(f"   ✗ Failed to remove {db_file}: {e}")
    print(f"   Total database files removed: {db_files_removed}")
    
    # Remove all files and directories in instance/large_attachments/
    print("\n6. Removing attachment files from instance/large_attachments/...")
    attachments_dir = instance_dir / 'large_attachments'
    attachments_removed = 0
    if attachments_dir.exists():
        try:
            # Count all items (files and dirs) before deletion for reporting
            for item in attachments_dir.rglob('*'):
                attachments_removed += 1
            
            # Remove entire directory and recreate it
            shutil.rmtree(attachments_dir)
            attachments_dir.mkdir(parents=True, exist_ok=True)
            print(f"   ✓ Removed all files and directories from {attachments_dir}")
            print(f"   Total attachment items removed: {attachments_removed}")
        except Exception as e:
            print(f"   ✗ Failed to remove attachments: {e}")
    else:
        # Create directory if it doesn't exist
        attachments_dir.mkdir(parents=True, exist_ok=True)
        print(f"   ℹ Directory {attachments_dir} doesn't exist, created it")
        print(f"   Total attachment items removed: 0")
    
    # Summary
    total_removed = pycache_count + db_count + pyc_count + log_count + db_files_removed + attachments_removed
    print(f"\n=== Cleanup Complete ===")
    print(f"Total items removed: {total_removed}")
    print(f"  - __pycache__ directories: {pycache_count}")
    print(f"  - .db files (cache): {db_count}")
    print(f"  - .pyc files: {pyc_count}")
    print(f"  - .log files: {log_count}")
    print(f"  - Database files (instance/): {db_files_removed}")
    print(f"  - Attachment files/directories: {attachments_removed}")
    print("\n⚠️  All database data and attachments have been deleted!")
    
    return total_removed

if __name__ == '__main__':
    clear_data() 