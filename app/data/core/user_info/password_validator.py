"""
Password validation utility for enhanced security
Implements password strength requirements to prevent weak passwords
"""

import re


class PasswordValidator:
    """Enhanced password validation"""
    
    MIN_LENGTH = 8
    MAX_LENGTH = 128
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    
    @classmethod
    def validate(cls, password, user=None, check_history=True):
        """
        Validate password strength and history
        
        Args:
            password (str): The password to validate
            user: User object to check password history (optional)
            check_history (bool): Whether to check password history (default True)
        
        Returns:
            tuple: (is_valid, error_message)
                is_valid (bool): True if password meets all requirements
                error_message (str): Error message if validation fails, empty string if valid
        """
        if not password:
            return False, "Password is required"
        
        if len(password) < cls.MIN_LENGTH:
            return False, f"Password must be at least {cls.MIN_LENGTH} characters"
        
        if len(password) > cls.MAX_LENGTH:
            return False, f"Password must be less than {cls.MAX_LENGTH} characters"
        
        if cls.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if cls.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if cls.REQUIRE_DIGIT and not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        
        if cls.REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            return False, "Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)"
        
        # Check password history if user is provided
        if user and check_history and user.id:
            from werkzeug.security import check_password_hash
            from app.data.core.user_info.password_history import PasswordHistory
            from flask import current_app
            
            history_count = current_app.config.get('PASSWORD_HISTORY_COUNT', 5)
            recent_passwords = PasswordHistory.query.filter_by(
                user_id=user.id
            ).order_by(
                PasswordHistory.created_at.desc()
            ).limit(history_count).all()
            
            # Check if new password matches any recent password
            for old_password in recent_passwords:
                if check_password_hash(old_password.password_hash, password):
                    return False, f"Password cannot be the same as any of your last {history_count} passwords"
        
        return True, ""
    
    @classmethod
    def get_requirements_text(cls):
        """
        Get a human-readable description of password requirements
        
        Returns:
            str: Description of all password requirements
        """
        requirements = [
            f"At least {cls.MIN_LENGTH} characters long",
            f"No more than {cls.MAX_LENGTH} characters"
        ]
        
        if cls.REQUIRE_UPPERCASE:
            requirements.append("At least one uppercase letter (A-Z)")
        
        if cls.REQUIRE_LOWERCASE:
            requirements.append("At least one lowercase letter (a-z)")
        
        if cls.REQUIRE_DIGIT:
            requirements.append("At least one digit (0-9)")
        
        if cls.REQUIRE_SPECIAL:
            requirements.append("At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)")
        
        return "Password must contain:\n" + "\n".join(f"• {req}" for req in requirements)
