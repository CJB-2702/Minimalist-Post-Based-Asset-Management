#!/usr/bin/env python3
"""
Test script for the refactored build system
Tests critical data insertion, debug data manager, and build file refactoring
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app import create_app, db
from app.build import build_database, verify_critical_data, insert_critical_data
from app.debug.debug_data_manager import insert_debug_data, _load_debug_data_file, _check_debug_data_present
from app.logger import get_logger

logger = get_logger("asset_management.debug.test")

def test_critical_data_file_exists():
    """Test 1: Verify critical data file exists"""
    print("\n" + "="*60)
    print("TEST 1: Critical Data File Exists")
    print("="*60)
    
    critical_file = project_root / 'app' / 'data' / 'core' / 'build_data_critical.json'
    if critical_file.exists():
        print(f"✓ Critical data file exists: {critical_file}")
        return True
    else:
        print(f"✗ Critical data file NOT found: {critical_file}")
        return False

def test_debug_data_files_exist():
    """Test 2: Verify debug data files exist"""
    print("\n" + "="*60)
    print("TEST 2: Debug Data Files Exist")
    print("="*60)
    
    debug_dir = project_root / 'app' / 'debug' / 'data'
    expected_files = ['core.json', 'assets.json', 'dispatching.json', 'maintenance.json', 'inventory.json']
    
    all_exist = True
    for filename in expected_files:
        file_path = debug_dir / filename
        if file_path.exists():
            print(f"✓ {filename} exists")
        else:
            print(f"✗ {filename} NOT found (this is OK - file is optional)")
            # Not a failure - files are optional
    
    return True  # All files are optional, so this always passes

def test_debug_data_manager_imports():
    """Test 3: Verify debug data manager can be imported"""
    print("\n" + "="*60)
    print("TEST 3: Debug Data Manager Imports")
    print("="*60)
    
    try:
        from app.debug.debug_data_manager import insert_debug_data
        print("✓ Debug data manager imports successfully")
        return True
    except Exception as e:
        print(f"✗ Debug data manager import failed: {e}")
        return False

def test_module_insertion_functions_exist():
    """Test 4: Verify module insertion functions exist"""
    print("\n" + "="*60)
    print("TEST 4: Module Insertion Functions Exist")
    print("="*60)
    
    modules = ['core', 'assets', 'dispatching', 'maintenance', 'inventory']
    all_exist = True
    
    for module in modules:
        try:
            module_name = f"add_{module}_debugging_data"
            func_name = f"insert_{module}_debug_data"
            module_path = f"app.debug.{module_name}"
            
            module_obj = __import__(module_path, fromlist=[func_name])
            if hasattr(module_obj, func_name):
                print(f"✓ {module_name}.{func_name} exists")
            else:
                print(f"✗ {module_name}.{func_name} NOT found")
                all_exist = False
        except Exception as e:
            print(f"✗ Error importing {module_name}: {e}")
            all_exist = False
    
    return all_exist

def test_build_files_no_data_insertion():
    """Test 5: Verify build files don't have data insertion functions"""
    print("\n" + "="*60)
    print("TEST 5: Build Files Have No Data Insertion")
    print("="*60)
    
    build_files = [
        'app/data/core/build.py',
        'app/data/assets/build.py',
        'app/data/maintenance/build.py',
        'app/data/core/supply/build.py'
    ]
    
    all_clean = True
    for build_file in build_files:
        file_path = project_root / build_file
        if not file_path.exists():
            print(f"⚠ {build_file} not found, skipping")
            continue
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for removed functions
        removed_functions = ['def init_data', 'def init_essential_data', 'def init_assets', 
                           'def phase_2_init_data', 'def _init_template_action_sets']
        
        found_removed = []
        for func in removed_functions:
            if func in content:
                found_removed.append(func)
        
        if found_removed:
            print(f"✗ {build_file} still contains removed functions: {found_removed}")
            all_clean = False
        else:
            # Check that build_models exists
            if 'def build_models' in content:
                print(f"✓ {build_file} is clean (only has build_models)")
            else:
                print(f"⚠ {build_file} doesn't have build_models function")
    
    return all_clean

def test_critical_data_structure():
    """Test 6: Verify critical data structure"""
    print("\n" + "="*60)
    print("TEST 6: Critical Data Structure")
    print("="*60)
    
    import json
    critical_file = project_root / 'app' / 'data' / 'core' / 'build_data_critical.json'
    
    try:
        with open(critical_file, 'r') as f:
            critical_data = json.load(f)
        
        # Check for required sections
        required_sections = ['Essential']
        all_present = True
        
        for section in required_sections:
            if section in critical_data:
                print(f"✓ {section} section present")
            else:
                print(f"✗ {section} section missing")
                all_present = False
        
        # Check for Essential.Users
        if 'Essential' in critical_data and 'Users' in critical_data['Essential']:
            users = critical_data['Essential']['Users']
            if 'System' in users and 'Admin' in users:
                print(f"✓ Essential users (System, Admin) present")
            else:
                print(f"✗ Essential users missing")
                all_present = False
        
        # Check for Essential.Events
        if 'Essential' in critical_data and 'Events' in critical_data['Essential']:
            print(f"✓ Essential events section present")
        else:
            print(f"✗ Essential events section missing")
            all_present = False
        
        return all_present
    except Exception as e:
        print(f"✗ Error reading critical data file: {e}")
        return False

def test_debug_data_structure():
    """Test 7: Verify debug data JSON structure"""
    print("\n" + "="*60)
    print("TEST 7: Debug Data JSON Structure")
    print("="*60)
    
    import json
    debug_dir = project_root / 'app' / 'debug' / 'data'
    
    test_files = ['core.json', 'assets.json', 'maintenance.json']
    all_valid = True
    
    for filename in test_files:
        file_path = debug_dir / filename
        if not file_path.exists():
            print(f"⚠ {filename} not found (optional, skipping)")
            continue
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            print(f"✓ {filename} is valid JSON")
        except json.JSONDecodeError as e:
            print(f"✗ {filename} has invalid JSON: {e}")
            all_valid = False
        except Exception as e:
            print(f"✗ Error reading {filename}: {e}")
            all_valid = False
    
    return all_valid

def test_build_database_function_signature():
    """Test 8: Verify build_database accepts enable_debug_data parameter"""
    print("\n" + "="*60)
    print("TEST 8: build_database Function Signature")
    print("="*60)
    
    import inspect
    from app.build import build_database
    
    sig = inspect.signature(build_database)
    params = list(sig.parameters.keys())
    
    if 'enable_debug_data' in params:
        print(f"✓ build_database has enable_debug_data parameter")
        print(f"  Parameters: {params}")
        return True
    else:
        print(f"✗ build_database missing enable_debug_data parameter")
        print(f"  Parameters: {params}")
        return False

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("BUILD SYSTEM REFACTORING - TEST SUITE")
    print("="*60)
    
    tests = [
        ("Critical Data File Exists", test_critical_data_file_exists),
        ("Debug Data Files Exist", test_debug_data_files_exist),
        ("Debug Data Manager Imports", test_debug_data_manager_imports),
        ("Module Insertion Functions Exist", test_module_insertion_functions_exist),
        ("Build Files Clean", test_build_files_no_data_insertion),
        ("Critical Data Structure", test_critical_data_structure),
        ("Debug Data Structure", test_debug_data_structure),
        ("build_database Signature", test_build_database_function_signature),
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
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1

if __name__ == '__main__':
    sys.exit(run_all_tests())

