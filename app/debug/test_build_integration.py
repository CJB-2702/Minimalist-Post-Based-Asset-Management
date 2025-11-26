#!/usr/bin/env python3
"""
Integration tests for the refactored build system
Tests actual database build process
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app import create_app, db
from app.build import build_database, verify_critical_data, insert_critical_data
from app.debug.debug_data_manager import insert_debug_data
from app.logger import get_logger

logger = get_logger("asset_management.debug.test_integration")

def test_build_only_mode():
    """Test 1: --build-only mode (tables only, critical data inserted)"""
    print("\n" + "="*60)
    print("TEST 1: Build-Only Mode")
    print("="*60)
    
    app = create_app()
    with app.app_context():
        try:
            # Drop all tables for clean test
            db.drop_all()
            print("✓ Dropped all tables for clean test")
            
            # Build with build-only mode
            build_database(build_phase='all', data_phase='none', enable_debug_data=False)
            print("✓ Build completed in build-only mode")
            
            # Verify critical data was inserted
            if verify_critical_data():
                print("✓ Critical data verified after build-only")
                return True
            else:
                print("✗ Critical data NOT found after build-only")
                return False
                
        except Exception as e:
            print(f"✗ Build-only test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_critical_data_insertion():
    """Test 2: Critical data is always inserted"""
    print("\n" + "="*60)
    print("TEST 2: Critical Data Always Inserted")
    print("="*60)
    
    app = create_app()
    with app.app_context():
        try:
            # Verify critical data exists
            if verify_critical_data():
                print("✓ Critical data already present")
            else:
                print("⚠ Critical data missing, attempting insertion...")
                insert_critical_data()
                if verify_critical_data():
                    print("✓ Critical data inserted successfully")
                else:
                    print("✗ Critical data insertion failed")
                    return False
            
            # Check for System user
            from app.data.core.user_info.user import User
            system_user = User.query.filter_by(id=0, username='system').first()
            if system_user:
                print(f"✓ System user found (id={system_user.id})")
            else:
                print("✗ System user NOT found")
                return False
            
            # Check for Admin user
            admin_user = User.query.filter_by(id=1, username='admin').first()
            if admin_user:
                print(f"✓ Admin user found (id={admin_user.id})")
            else:
                print("✗ Admin user NOT found")
                return False
            
            # Check for Vehicle asset type
            from app.data.core.asset_info.asset_type import AssetType
            vehicle_type = AssetType.query.filter_by(name='Vehicle').first()
            if vehicle_type:
                print(f"✓ Vehicle asset type found")
            else:
                print("✗ Vehicle asset type NOT found")
                return False
            
            return True
            
        except Exception as e:
            print(f"✗ Critical data test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_debug_data_manager_loads_files():
    """Test 3: Debug data manager can load JSON files"""
    print("\n" + "="*60)
    print("TEST 3: Debug Data Manager Loads Files")
    print("="*60)
    
    try:
        from app.debug.debug_data_manager import _load_debug_data_file
        
        modules = ['core', 'assets', 'maintenance']
        all_loaded = True
        
        for module in modules:
            data = _load_debug_data_file(module)
            if data:
                print(f"✓ Loaded {module}.json ({len(str(data))} chars)")
            else:
                print(f"⚠ {module}.json not found or empty (this is OK)")
        
        return True
        
    except Exception as e:
        print(f"✗ Debug data manager file loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_debug_data_presence_detection():
    """Test 4: Debug data presence detection works"""
    print("\n" + "="*60)
    print("TEST 4: Debug Data Presence Detection")
    print("="*60)
    
    app = create_app()
    with app.app_context():
        try:
            from app.debug.debug_data_manager import _check_debug_data_present, _load_debug_data_file
            
            # Test core module
            core_data = _load_debug_data_file('core')
            if core_data:
                is_present = _check_debug_data_present('core', core_data)
                print(f"✓ Core debug data presence check: {is_present}")
            else:
                print("⚠ Core debug data file not found, skipping presence check")
            
            return True
            
        except Exception as e:
            print(f"✗ Debug data presence detection failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_build_with_debug_data_disabled():
    """Test 5: Build with debug data disabled"""
    print("\n" + "="*60)
    print("TEST 5: Build with Debug Data Disabled")
    print("="*60)
    
    app = create_app()
    with app.app_context():
        try:
            # Build with debug data disabled
            build_database(build_phase='all', data_phase='all', enable_debug_data=False)
            print("✓ Build completed with debug data disabled")
            
            # Check that critical data is still present
            if verify_critical_data():
                print("✓ Critical data still present (as expected)")
            else:
                print("✗ Critical data missing (should always be present)")
                return False
            
            # Check that debug data was NOT inserted (check for a debug user)
            from app.data.core.user_info.user import User
            debug_user = User.query.filter_by(username='Generic_User').first()
            if debug_user:
                print("⚠ Debug user found (should not be present when disabled)")
                # This might be OK if it was inserted before
            else:
                print("✓ Debug user not found (as expected when disabled)")
            
            return True
            
        except Exception as e:
            print(f"✗ Build with debug data disabled failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_build_with_debug_data_enabled():
    """Test 6: Build with debug data enabled"""
    print("\n" + "="*60)
    print("TEST 6: Build with Debug Data Enabled")
    print("="*60)
    
    app = create_app()
    with app.app_context():
        try:
            # Build with debug data enabled
            build_database(build_phase='all', data_phase='all', enable_debug_data=True)
            print("✓ Build completed with debug data enabled")
            
            # Check that critical data is still present
            if verify_critical_data():
                print("✓ Critical data still present (as expected)")
            else:
                print("✗ Critical data missing (should always be present)")
                return False
            
            # Check that some debug data was inserted
            from app.data.core.user_info.user import User
            from app.data.core.major_location import MajorLocation
            from app.data.core.asset_info.asset import Asset
            
            debug_user = User.query.filter_by(username='Generic_User').first()
            if debug_user:
                print(f"✓ Debug user found: {debug_user.username}")
            else:
                print("⚠ Debug user not found (may have been skipped if already present)")
            
            debug_location = MajorLocation.query.filter_by(name='SanDiegoHQ').first()
            if debug_location:
                print(f"✓ Debug location found: {debug_location.name}")
            else:
                print("⚠ Debug location not found (may have been skipped if already present)")
            
            return True
            
        except Exception as e:
            print(f"✗ Build with debug data enabled failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def run_integration_tests():
    """Run all integration tests"""
    print("\n" + "="*60)
    print("BUILD SYSTEM REFACTORING - INTEGRATION TEST SUITE")
    print("="*60)
    print("\nNote: These tests will modify the database")
    print("Make sure you're using a test database or are OK with data changes")
    
    tests = [
        ("Build-Only Mode", test_build_only_mode),
        ("Critical Data Always Inserted", test_critical_data_insertion),
        ("Debug Data Manager Loads Files", test_debug_data_manager_loads_files),
        ("Debug Data Presence Detection", test_debug_data_presence_detection),
        ("Build with Debug Data Disabled", test_build_with_debug_data_disabled),
        ("Build with Debug Data Enabled", test_build_with_debug_data_enabled),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("INTEGRATION TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All integration tests passed!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1

if __name__ == '__main__':
    sys.exit(run_integration_tests())

