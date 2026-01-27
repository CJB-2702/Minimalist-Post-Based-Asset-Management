"""
Test the logging sanitizer utility.
Run this to verify passwords and sensitive data are properly redacted from logs.
"""

from app.utils.logging_sanitizer import sanitize_dict, sanitize_form_data, SENSITIVE_FIELDS
from werkzeug.datastructures import ImmutableMultiDict


def test_sanitize_dict():
    """Test dictionary sanitization"""
    print("Testing sanitize_dict()...")
    
    # Test basic password redaction
    test_data = {
        'username': 'admin',
        'password': 'secret123',
        'email': 'admin@example.com'
    }
    result = sanitize_dict(test_data)
    assert result['username'] == 'admin', "Username should not be redacted"
    assert result['password'] == '[REDACTED]', "Password should be redacted"
    assert result['email'] == 'admin@example.com', "Email should not be redacted"
    print("✓ Basic password redaction works")
    
    # Test multiple sensitive fields
    test_data = {
        'username': 'admin',
        'password': 'secret123',
        'confirm_password': 'secret123',
        'api_key': 'abcd1234',
        'token': 'xyz789'
    }
    result = sanitize_dict(test_data)
    assert result['password'] == '[REDACTED]', "password should be redacted"
    assert result['confirm_password'] == '[REDACTED]', "confirm_password should be redacted"
    assert result['api_key'] == '[REDACTED]', "api_key should be redacted"
    assert result['token'] == '[REDACTED]', "token should be redacted"
    print("✓ Multiple sensitive fields redacted")
    
    # Test case insensitivity
    test_data = {
        'Password': 'secret123',
        'PASSWORD': 'secret456',
        'PaSsWoRd': 'secret789'
    }
    result = sanitize_dict(test_data)
    assert result['Password'] == '[REDACTED]', "Password (title case) should be redacted"
    assert result['PASSWORD'] == '[REDACTED]', "PASSWORD (upper case) should be redacted"
    assert result['PaSsWoRd'] == '[REDACTED]', "PaSsWoRd (mixed case) should be redacted"
    print("✓ Case-insensitive redaction works")
    
    # Test nested dictionaries
    test_data = {
        'user': {
            'username': 'admin',
            'password': 'secret123'
        },
        'settings': {
            'theme': 'dark'
        }
    }
    result = sanitize_dict(test_data)
    assert result['user']['username'] == 'admin', "Nested username should not be redacted"
    assert result['user']['password'] == '[REDACTED]', "Nested password should be redacted"
    assert result['settings']['theme'] == 'dark', "Non-sensitive nested value should not be redacted"
    print("✓ Nested dictionary redaction works")
    
    print()


def test_sanitize_form_data():
    """Test Flask form data sanitization"""
    print("Testing sanitize_form_data()...")
    
    # Simulate Flask request.form
    form_data = ImmutableMultiDict([
        ('username', 'admin'),
        ('password', 'secret123'),
        ('email', 'admin@example.com')
    ])
    
    result = sanitize_form_data(form_data)
    assert result['username'] == 'admin', "Username should not be redacted"
    assert result['password'] == '[REDACTED]', "Password should be redacted"
    assert result['email'] == 'admin@example.com', "Email should not be redacted"
    print("✓ Form data sanitization works")
    
    print()


def test_all_sensitive_fields():
    """Verify all sensitive fields are properly configured"""
    print("Testing all sensitive field patterns...")
    
    test_data = {}
    for field in SENSITIVE_FIELDS:
        test_data[field] = f"sensitive_{field}_value"
    
    result = sanitize_dict(test_data)
    
    for field in SENSITIVE_FIELDS:
        assert result[field] == '[REDACTED]', f"Field '{field}' should be redacted"
    
    print(f"✓ All {len(SENSITIVE_FIELDS)} sensitive fields are properly redacted")
    print(f"  Sensitive fields: {', '.join(sorted(SENSITIVE_FIELDS))}")
    print()


def test_safe_logging_example():
    """Demonstrate safe logging practice"""
    print("Demonstrating safe logging practice...")
    print()
    
    # Simulated login form data
    login_form = {
        'username': 'admin',
        'password': 'SuperSecret123!',
        'remember_me': 'true'
    }
    
    print("❌ UNSAFE: Logging raw form data")
    print(f"   Login attempt: {login_form}")
    print()
    
    print("✓ SAFE: Logging sanitized form data")
    sanitized = sanitize_dict(login_form)
    print(f"   Login attempt: {sanitized}")
    print()


if __name__ == '__main__':
    print("=" * 60)
    print("LOGGING SANITIZER TEST SUITE")
    print("=" * 60)
    print()
    
    try:
        test_sanitize_dict()
        test_sanitize_form_data()
        test_all_sensitive_fields()
        test_safe_logging_example()
        
        print("=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        print()
        print("The logging sanitizer is working correctly.")
        print("Passwords and sensitive data will be redacted from logs.")
        
    except AssertionError as e:
        print("=" * 60)
        print("❌ TEST FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        raise
