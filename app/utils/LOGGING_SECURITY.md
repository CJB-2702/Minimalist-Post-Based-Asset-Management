# Logging Security Guidelines

## Overview

This document provides guidelines for secure logging practices to prevent accidental exposure of sensitive data in application logs.

## Critical Rule: Never Log Sensitive Data

**NEVER log the following directly:**
- Passwords (in any form)
- Authentication tokens
- API keys
- Credit card numbers
- Social Security Numbers
- Session IDs
- CSRF tokens
- Any other PII or credentials

## Using the Logging Sanitizer

### Basic Usage

When logging form data, always sanitize it first:

```python
from app.utils.logging_sanitizer import sanitize_form_data

# ❌ UNSAFE - Don't do this
logger.info(f"Form data: {dict(request.form)}")

# ✅ SAFE - Always sanitize first
logger.info(f"Form data: {sanitize_form_data(request.form)}")
```

### Sanitizing Dictionaries

```python
from app.utils.logging_sanitizer import sanitize_dict

user_data = {
    'username': 'admin',
    'password': 'secret123',
    'email': 'admin@example.com'
}

# ✅ SAFE - Sanitize before logging
logger.info(f"User data: {sanitize_dict(user_data)}")
# Output: User data: {'username': 'admin', 'password': '[REDACTED]', 'email': 'admin@example.com'}
```

### Exception Handling

Be careful with exception logging - exceptions might contain sensitive data:

```python
try:
    user.set_password(password)
except Exception as e:
    # ❌ UNSAFE - Exception message might contain password
    logger.error(f"Error: {e}")
    
    # ✅ SAFER - Use exception type and sanitized message
    from app.utils.logging_sanitizer import sanitize_exception_message
    logger.error(f"Error updating password: {sanitize_exception_message(e)}")
```

## Sensitive Fields

The sanitizer automatically redacts these field names (case-insensitive):

- `password`, `pwd`, `passwd`
- `current_password`, `new_password`, `old_password`
- `password_confirm`, `confirm_password`
- `token`, `auth_token`, `access_token`, `refresh_token`
- `api_key`, `apikey`
- `secret`
- `session_id`
- `csrf_token`
- `credit_card`, `creditcard`
- `cvv`
- `ssn`, `social_security`

## Best Practices

### 1. Authentication Logging

```python
# ✅ GOOD - Log username, not password
logger.warning(f"Failed login attempt for username: {username}")

# ✅ GOOD - Log actions, not credentials
logger.info(f"User {username} changed password")

# ❌ BAD - Never log the actual password
logger.info(f"Password changed to: {new_password}")  # NEVER DO THIS
```

### 2. Form Data Logging

```python
from app.utils.logging_sanitizer import sanitize_form_data

# Always sanitize before logging form data
if request.method == 'POST':
    logger.debug(f"Received form data: {sanitize_form_data(request.form)}")
```

### 3. Debug Logging

```python
# ❌ BAD - Print statements in production code
print(f"Form data: {request.form}")  # NEVER DO THIS

# ✅ GOOD - Use proper logging with sanitization
from app.utils.logging_sanitizer import sanitize_form_data
logger.debug(f"Form data: {sanitize_form_data(request.form)}")
```

### 4. Request Arguments

```python
# Request arguments don't typically contain passwords, but be cautious
# If you're logging request.args, consider what params might be sensitive

# Generally safe (but verify your use case)
logger.debug(f"Search params: {dict(request.args)}")

# If unsure, sanitize it
from app.utils.logging_sanitizer import sanitize_dict
logger.debug(f"Params: {sanitize_dict(dict(request.args))}")
```

## Code Review Checklist

When reviewing code, check for:

- [ ] No raw `print(request.form)` statements
- [ ] No `logger.*(dict(request.form))` without sanitization
- [ ] No `logger.*(...password...)` that logs actual passwords
- [ ] Exception messages don't expose sensitive data
- [ ] Debug statements use proper logging, not print
- [ ] Form data logging uses `sanitize_form_data()`
- [ ] Dictionary logging uses `sanitize_dict()` when appropriate

## Testing

Run the test suite to verify sanitization works:

```bash
python test_logging_sanitizer.py
```

Expected output:
```
✓ ALL TESTS PASSED
The logging sanitizer is working correctly.
Passwords and sensitive data will be redacted from logs.
```

## Production Monitoring

### Log Review

Periodically audit logs for sensitive data exposure:

```bash
# Search for potential password leaks in logs
grep -i "password.*:" /var/log/asset_management/*.log | grep -v "\[REDACTED\]"

# Should return no results. If it does, investigate immediately.
```

### Adding New Sensitive Fields

If you identify new sensitive field names, add them to `SENSITIVE_FIELDS` in `app/utils/logging_sanitizer.py`:

```python
SENSITIVE_FIELDS = {
    'password',
    # ... existing fields ...
    'new_sensitive_field',  # Add new field here
}
```

Then run tests to verify:

```bash
python test_logging_sanitizer.py
```

## Emergency Response

If you discover sensitive data has been logged:

1. **Immediate Action:**
   - Rotate any exposed credentials immediately
   - Clear or redact the affected log files
   - Notify security team

2. **Investigation:**
   - Identify the source of the leak
   - Check how long the leak has existed
   - Review who had access to the logs

3. **Remediation:**
   - Fix the code to use proper sanitization
   - Add tests to prevent regression
   - Update documentation if needed
   - Consider security audit of related code

## Questions?

Contact the security team or review the implementation in:
- `app/utils/logging_sanitizer.py` - Core implementation
- `test_logging_sanitizer.py` - Test suite and examples
- `SECURITY_ASSESSMENT.md` - Security audit results
