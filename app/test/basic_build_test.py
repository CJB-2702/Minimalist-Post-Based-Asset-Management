#!/usr/bin/env python3
"""
Basic build test - clears data and starts the app
"""

import sys
import os
import subprocess

# Add project root to path
# __file__ is in app/test/, so go up two levels to get to project root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

def run_clear_data():
    """Run the clear_data.py script"""
    print("=" * 60)
    print("Step 1: Running clear_data.py")
    print("=" * 60)
    
    clear_data_path = os.path.join(os.path.dirname(__file__), 'clear_data.py')
    result = subprocess.run([sys.executable, clear_data_path], 
                          capture_output=False,
                          text=True)
    
    if result.returncode != 0:
        print(f"ERROR: clear_data.py failed with exit code {result.returncode}")
        return False
    
    print("\n✓ clear_data.py completed successfully\n")
    return True

def start_app():
    """Start the Flask app"""
    print("=" * 60)
    print("Step 2: Starting Flask app")
    print("=" * 60)
    
    try:
        from app import create_app
        app = create_app()
        
        print("\n✓ Flask app created successfully")
        print(f"✓ App name: {app.name}")
        print(f"✓ Debug mode: {app.debug}")
        print("\n✓ Basic build test passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: Failed to start app: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the basic build test"""
    print("\n" + "=" * 60)
    print("BASIC BUILD TEST")
    print("=" * 60 + "\n")
    
    # Step 1: Clear data
    if not run_clear_data():
        print("\n✗ Build test failed at clear_data step")
        sys.exit(1)
    
    # Step 2: Start app
    if not start_app():
        print("\n✗ Build test failed at app startup step")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED")
    print("=" * 60 + "\n")
    sys.exit(0)

if __name__ == '__main__':
    main()






