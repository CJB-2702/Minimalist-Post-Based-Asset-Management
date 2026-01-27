#!/usr/bin/env python3
"""
Test runner for maintenance page loads
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from app import create_app
from app.test.maintenance.pageloads import check_all_routes

def main():
    """Run pageload tests"""
    print("\n" + "=" * 60)
    print("MAINTENANCE MODULE PAGE LOAD TESTS")
    print("=" * 60 + "\n")
    
    # Create app and test client
    app = create_app()
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        # Create a test user and login
        with app.app_context():
            from app.data.core.user_info.user import User
            from app import db
            
            # Check if test user exists, create if not
            test_user = User.query.filter_by(username='test').first()
            if not test_user:
                test_user = User(
                    username='test',
                    email='test@example.com'
                )
                test_user.set_password('test123')
                db.session.add(test_user)
                db.session.commit()
                print("✓ Created test user")
            else:
                print("✓ Using existing test user")
        
        # Login
        response = client.post('/login', data={
            'username': 'test',
            'password': 'test123'
        }, follow_redirects=True)
        
        if response.status_code != 200:
            print("✗ Failed to login test user")
            sys.exit(1)
        print("✓ Logged in test user")
        print("✓ Using event ID 8 (created during app initialization)")
        
        # Run tests
        print("\nTesting routes...")
        print("-" * 60)
        results = check_all_routes(client)
        
        # Display results
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(f"Passed: {len(results['passed'])}")
        print(f"Failed: {len(results['failed'])}")
        
        if results['failed']:
            print("\n" + "=" * 60)
            print("FAILED ROUTES")
            print("=" * 60)
            for route in results['failed']:
                error = results['errors'].get(route, 'Unknown error')
                print(f"  ✗ {route}")
                print(f"    Error: {error}")
        
        if results['passed']:
            print("\n" + "=" * 60)
            print("PASSED ROUTES")
            print("=" * 60)
            for route in results['passed']:
                print(f"  ✓ {route}")
        
        # Summary
        print("\n" + "=" * 60)
        if results['failed']:
            print("✗ SOME TESTS FAILED")
            print("=" * 60 + "\n")
            sys.exit(1)
        else:
            print("✓ ALL TESTS PASSED")
            print("=" * 60 + "\n")
            sys.exit(0)

if __name__ == '__main__':
    main()
