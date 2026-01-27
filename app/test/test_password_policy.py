"""
Test script for password policy enforcement
Tests password complexity, history, expiration, and account lockout
"""

import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Set SECRET_KEY if not set (for testing)
if not os.environ.get('SECRET_KEY'):
    os.environ['SECRET_KEY'] = 'test_secret_key_for_password_policy_testing'

from app import create_app, db
from app.data.core.user_info.user import User
from app.data.core.user_info.password_history import PasswordHistory
from app.data.core.user_info.password_validator import PasswordValidator

def test_password_complexity():
    """Test password complexity requirements"""
    print("\n" + "="*60)
    print("TEST 1: Password Complexity")
    print("="*60)
    
    test_cases = [
        ("short", False, "Too short"),
        ("NoDigit!", False, "Missing digit"),
        ("nouppercase1!", False, "Missing uppercase"),
        ("NOLOWERCASE1!", False, "Missing lowercase"),
        ("NoSpecialChar1", False, "Missing special character"),
        ("ValidPass1!", True, "Valid password"),
        ("AnotherValid99@", True, "Valid password with special chars"),
    ]
    
    passed = 0
    failed = 0
    
    for password, should_pass, description in test_cases:
        is_valid, error_msg = PasswordValidator.validate(password)
        
        if should_pass and is_valid:
            print(f"✓ PASS: {description} - '{password}'")
            passed += 1
        elif not should_pass and not is_valid:
            print(f"✓ PASS: {description} - '{password}' correctly rejected: {error_msg}")
            passed += 1
        else:
            print(f"✗ FAIL: {description} - '{password}' - Expected {should_pass}, got {is_valid}")
            if error_msg:
                print(f"  Error: {error_msg}")
            failed += 1
    
    print(f"\nComplexity Tests: {passed} passed, {failed} failed")
    return failed == 0

def test_password_history():
    """Test password history checking"""
    print("\n" + "="*60)
    print("TEST 2: Password History")
    print("="*60)
    
    app = create_app()
    
    with app.app_context():
        # Delete existing test user to start fresh
        existing_user = User.query.filter_by(username='test_password_history').first()
        if existing_user:
            # Delete password history first
            PasswordHistory.query.filter_by(user_id=existing_user.id).delete()
            db.session.delete(existing_user)
            db.session.commit()
            print("✓ Deleted existing test user for fresh test")
        
        # Create a fresh test user
        test_user = User(
            username='test_password_history',
            email='test_history@example.com',
            is_active=True,
            is_admin=False
        )
        test_user.set_password('InitialPass1!', check_history=False)
        db.session.add(test_user)
        db.session.commit()
        print("✓ Created fresh test user")
        
        # Test changing password to same password
        try:
            test_user.set_password('InitialPass1!', check_history=True)
            print("✗ FAIL: Should not allow reusing current password")
            return False
        except ValueError as e:
            print(f"✓ PASS: Correctly rejected reusing current password: {e}")
        
        # Change password successfully
        test_user.set_password('NewPassword2@', check_history=True)
        db.session.commit()
        print("✓ PASS: Successfully changed to new password")
        
        # Try to change back to previous password
        try:
            test_user.set_password('InitialPass1!', check_history=True)
            print("✗ FAIL: Should not allow reusing previous password")
            return False
        except ValueError as e:
            print(f"✓ PASS: Correctly rejected reusing previous password: {e}")
        
        # Check password history count
        history_count = PasswordHistory.query.filter_by(user_id=test_user.id).count()
        print(f"✓ Password history entries: {history_count}")
        
        print("\nPassword History Tests: All passed")
        return True

def test_account_lockout():
    """Test account lockout after failed login attempts"""
    print("\n" + "="*60)
    print("TEST 3: Account Lockout")
    print("="*60)
    
    app = create_app()
    
    with app.app_context():
        # Create a test user
        test_user = User.query.filter_by(username='test_lockout').first()
        if not test_user:
            test_user = User(
                username='test_lockout',
                email='test_lockout@example.com',
                is_active=True,
                is_admin=False
            )
            test_user.set_password('TestPass1!', check_history=False)
            db.session.add(test_user)
            db.session.commit()
            print("✓ Created test user")
        else:
            # Reset the user's lockout status
            test_user.failed_login_attempts = 0
            test_user.locked_until = None
            db.session.commit()
            print("✓ Using existing test user (reset lockout)")
        
        # Simulate failed login attempts
        max_attempts = app.config.get('MAX_FAILED_LOGIN_ATTEMPTS', 5)
        print(f"✓ Max failed attempts: {max_attempts}")
        
        for i in range(max_attempts):
            test_user.increment_failed_login()
            db.session.commit()
            print(f"  Attempt {i+1}: Failed login attempts = {test_user.failed_login_attempts}")
        
        # Check if account is locked
        if test_user.is_locked():
            lockout_minutes = app.config.get('ACCOUNT_LOCKOUT_MINUTES', 30)
            print(f"✓ PASS: Account correctly locked after {max_attempts} failed attempts")
            print(f"  Locked until: {test_user.locked_until}")
            print(f"  Lockout duration: {lockout_minutes} minutes")
        else:
            print("✗ FAIL: Account should be locked")
            return False
        
        # Test reset on successful login
        test_user.reset_failed_login()
        db.session.commit()
        
        if test_user.failed_login_attempts == 0 and test_user.locked_until is None:
            print("✓ PASS: Failed login attempts reset correctly")
        else:
            print("✗ FAIL: Failed login attempts not reset")
            return False
        
        print("\nAccount Lockout Tests: All passed")
        return True

def test_password_expiration():
    """Test password expiration checking"""
    print("\n" + "="*60)
    print("TEST 4: Password Expiration")
    print("="*60)
    
    app = create_app()
    
    with app.app_context():
        # Create a test user
        test_user = User.query.filter_by(username='test_expiration').first()
        if not test_user:
            test_user = User(
                username='test_expiration',
                email='test_expiration@example.com',
                is_active=True,
                is_admin=False,
                is_system=False
            )
            test_user.set_password('TestPass1!', check_history=False)
            db.session.add(test_user)
            db.session.commit()
            print("✓ Created test user")
        else:
            # Reset test user to non-system
            test_user.is_system = False
            db.session.commit()
            print("✓ Using existing test user (reset to non-system)")
        
        expiration_days = app.config.get('PASSWORD_EXPIRATION_DAYS', 90)
        print(f"✓ Password expiration days: {expiration_days}")
        
        # Test with fresh password (should not be expired)
        test_user.password_changed_at = datetime.utcnow()
        db.session.commit()
        
        if not test_user.is_password_expired():
            print("✓ PASS: Fresh password is not expired")
        else:
            print("✗ FAIL: Fresh password should not be expired")
            return False
        
        # Test with old password (should be expired)
        test_user.password_changed_at = datetime.utcnow() - timedelta(days=expiration_days + 1)
        db.session.commit()
        
        if test_user.is_password_expired():
            print("✓ PASS: Old password is correctly marked as expired")
        else:
            print("✗ FAIL: Old password should be expired")
            return False
        
        # Test days until expiration
        test_user.password_changed_at = datetime.utcnow() - timedelta(days=expiration_days - 7)
        db.session.commit()
        
        days_remaining = test_user.days_until_password_expires()
        if days_remaining and 6 <= days_remaining <= 8:  # Allow some tolerance
            print(f"✓ PASS: Days until expiration calculated correctly: {days_remaining} days")
        else:
            print(f"✗ FAIL: Days until expiration incorrect: {days_remaining} (expected ~7)")
            return False
        
        # Test system user exemption
        test_user.is_system = True
        test_user.password_changed_at = datetime.utcnow() - timedelta(days=expiration_days + 100)
        db.session.commit()
        
        if not test_user.is_password_expired():
            print("✓ PASS: System user is exempt from password expiration")
        else:
            print("✗ FAIL: System user should be exempt from expiration")
            return False
        
        print("\nPassword Expiration Tests: All passed")
        return True

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("PASSWORD POLICY ENFORCEMENT TEST SUITE")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Password Complexity", test_password_complexity()))
    results.append(("Password History", test_password_history()))
    results.append(("Account Lockout", test_account_lockout()))
    results.append(("Password Expiration", test_password_expiration()))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} test suites passed")
    
    if passed == total:
        print("\n🎉 All password policy tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test suite(s) failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
