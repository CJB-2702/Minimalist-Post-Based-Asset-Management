"""
Logging Sanitizer Utility

Provides utilities to sanitize sensitive data before logging.
Prevents accidental logging of passwords, tokens, and other sensitive information.
"""

from typing import Dict, Any
from werkzeug.datastructures import ImmutableMultiDict


# Fields that should never be logged
SENSITIVE_FIELDS = {
    'password',
    'password_confirm',
    'confirm_password',
    'current_password',
    'new_password',
    'old_password',
    'pwd',
    'passwd',
    'secret',
    'token',
    'api_key',
    'apikey',
    'auth_token',
    'access_token',
    'refresh_token',
    'session_id',
    'csrf_token',
    'credit_card',
    'creditcard',
    'cvv',
    'ssn',
    'social_security',
}


def sanitize_dict(data: Dict[str, Any], redact_text: str = '[REDACTED]') -> Dict[str, Any]:
    """
    Sanitize a dictionary by replacing sensitive field values with redaction text.
    
    Args:
        data: Dictionary to sanitize
        redact_text: Text to use for redacted values (default: '[REDACTED]')
        
    Returns:
        Sanitized dictionary with sensitive values replaced
        
    Example:
        >>> data = {'username': 'admin', 'password': 'secret123'}
        >>> sanitize_dict(data)
        {'username': 'admin', 'password': '[REDACTED]'}
    """
    if not data:
        return data
        
    sanitized = {}
    for key, value in data.items():
        # Check if key (case-insensitive) matches any sensitive field
        if key.lower() in SENSITIVE_FIELDS:
            sanitized[key] = redact_text
        elif isinstance(value, dict):
            # Recursively sanitize nested dictionaries
            sanitized[key] = sanitize_dict(value, redact_text)
        else:
            sanitized[key] = value
            
    return sanitized


def sanitize_form_data(form_data: ImmutableMultiDict, redact_text: str = '[REDACTED]') -> Dict[str, Any]:
    """
    Sanitize Flask request.form data for safe logging.
    
    Args:
        form_data: Flask request.form (ImmutableMultiDict)
        redact_text: Text to use for redacted values (default: '[REDACTED]')
        
    Returns:
        Sanitized dictionary safe for logging
        
    Example:
        >>> from flask import request
        >>> sanitized = sanitize_form_data(request.form)
        >>> logger.info(f"Form data: {sanitized}")
    """
    return sanitize_dict(dict(form_data), redact_text)


def sanitize_exception_message(exception: Exception) -> str:
    """
    Sanitize exception messages to ensure they don't contain sensitive data.
    
    This is a basic implementation that should be enhanced based on specific needs.
    
    Args:
        exception: Exception to sanitize
        
    Returns:
        Sanitized exception message
    """
    message = str(exception)
    
    # Check for common patterns that might indicate password in message
    # This is a simple heuristic - enhance as needed
    if any(field in message.lower() for field in SENSITIVE_FIELDS):
        return f"{type(exception).__name__}: [Message contains sensitive data]"
    
    return message
