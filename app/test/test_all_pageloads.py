"""
Main test runner for all page load tests
Runs all module pageload tests and prints results
"""
import sys
import os

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from flask import Flask


def run_all_tests():
    """Run all page load tests and print results"""
    # Create Flask app
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    client = app.test_client()
    
    # Try to login with admin/admin123456789
    login_response = client.post('/login', data={
        'username': 'admin',
        'password': 'admin123456789'
    }, follow_redirects=True)
    
    if login_response.status_code != 200:
        print("WARNING: Could not login with admin/admin123456789. Some tests may fail due to authentication.")
        print(f"Login response status: {login_response.status_code}")
    
    # Import all test modules
    from tests.core.pageloads import check_all_routes as check_core
    from tests.assets.pageloads import check_all_routes as check_assets
    from tests.maintenance.pageloads import check_all_routes as check_maintenance
    from tests.inventory.pageloads import check_all_routes as check_inventory
    from tests.dispatching.pageloads import check_all_routes as check_dispatching
    from tests.admin.pageloads import check_all_routes as check_admin
    from tests.main.pageloads import check_all_routes as check_main
    
    # Run all tests
    all_results = {}
    
    print("=" * 80)
    print("RUNNING PAGE LOAD TESTS")
    print("=" * 80)
    print()
    
    test_modules = [
        ('Core', check_core),
        ('Assets', check_assets),
        ('Maintenance', check_maintenance),
        ('Inventory', check_inventory),
        ('Dispatching', check_dispatching),
        ('Admin', check_admin),
        ('Main', check_main),
    ]
    
    for module_name, test_func in test_modules:
        print(f"Testing {module_name} module...")
        try:
            results = test_func(client)
            all_results[module_name] = results
        except Exception as e:
            print(f"ERROR: Failed to run {module_name} tests: {e}")
            all_results[module_name] = {
                'passed': [],
                'failed': [],
                'errors': {'module_error': str(e)}
            }
        print(f"  {module_name}: {len(all_results[module_name]['passed'])} passed, {len(all_results[module_name]['failed'])} failed")
    
    print()
    print("=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)
    print()
    
    # Print pass/fail for each route
    total_passed = 0
    total_failed = 0
    
    for module_name, results in all_results.items():
        print(f"\n{module_name} Module:")
        print("-" * 80)
        
        # Print passed routes
        if results['passed']:
            print(f"PASSED ({len(results['passed'])}):")
            for route in sorted(results['passed']):
                print(f"  ✓ {route}")
        
        # Print failed routes
        if results['failed']:
            print(f"\nFAILED ({len(results['failed'])}):")
            for route in sorted(results['failed']):
                print(f"  ✗ {route}")
        
        total_passed += len(results['passed'])
        total_failed += len(results['failed'])
    
    print()
    print("=" * 80)
    print(f"TOTAL: {total_passed} passed, {total_failed} failed")
    print("=" * 80)
    print()
    
    # Print errors for failed routes
    if total_failed > 0:
        print("=" * 80)
        print("ERROR DETAILS FOR FAILED ROUTES")
        print("=" * 80)
        print()
        
        for module_name, results in all_results.items():
            if results['errors']:
                print(f"\n{module_name} Module Errors:")
                print("-" * 80)
                for route, error in sorted(results['errors'].items()):
                    print(f"  {route}:")
                    print(f"    {error}")
                    print()
    
    # Return exit code
    return 0 if total_failed == 0 else 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)

