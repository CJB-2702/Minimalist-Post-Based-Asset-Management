from app import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime, timedelta
from app.buisness.core.data_insertion_mixin import DataInsertionMixin

class User(UserMixin, DataInsertionMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_system = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Password policy fields
    password_changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_password_change_notification = db.Column(db.DateTime)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    
    # Relationships (no backrefs)
    created_assets = db.relationship('Asset', foreign_keys='Asset.created_by_id')
    updated_assets = db.relationship('Asset', foreign_keys='Asset.updated_by_id')
    created_locations = db.relationship('MajorLocation', foreign_keys='MajorLocation.created_by_id')
    updated_locations = db.relationship('MajorLocation', foreign_keys='MajorLocation.updated_by_id')
    created_asset_types = db.relationship('AssetType', foreign_keys='AssetType.created_by_id')
    updated_asset_types = db.relationship('AssetType', foreign_keys='AssetType.updated_by_id')
    created_make_models = db.relationship('MakeModel', foreign_keys='MakeModel.created_by_id')
    updated_make_models = db.relationship('MakeModel', foreign_keys='MakeModel.updated_by_id')
    events = db.relationship('Event', foreign_keys='Event.user_id')
    created_comments = db.relationship('Comment', foreign_keys='Comment.created_by_id')
    updated_comments = db.relationship('Comment', foreign_keys='Comment.updated_by_id')
    created_attachments = db.relationship('Attachment', foreign_keys='Attachment.created_by_id')
    updated_attachments = db.relationship('Attachment', foreign_keys='Attachment.updated_by_id')
    
    def set_password(self, password, check_history=True):
        """
        Set user password with history checking and policy enforcement
        
        Args:
            password: The new password to set
            check_history: Whether to check password history (default True)
            
        Raises:
            ValueError: If password is in history or matches current password
        """
        from app.data.core.user_info.password_history import PasswordHistory
        from flask import current_app
        
        # Check against current password first
        if check_history and self.id and self.password_hash:
            if check_password_hash(self.password_hash, password):
                raise ValueError("Password cannot be the same as your current password")
        
        # Check password history if enabled
        if check_history and self.id:
            # Get password history count from config
            history_count = current_app.config.get('PASSWORD_HISTORY_COUNT', 5)
            recent_passwords = PasswordHistory.query.filter_by(
                user_id=self.id
            ).order_by(
                PasswordHistory.created_at.desc()
            ).limit(history_count).all()
            
            # Check if new password matches any recent password
            for old_password in recent_passwords:
                if check_password_hash(old_password.password_hash, password):
                    raise ValueError(f"Password cannot be the same as any of your last {history_count} passwords")
        
        # Set new password
        new_hash = generate_password_hash(password)
        
        # Save old password to history if user exists and password is changing
        if self.id and self.password_hash and self.password_hash != new_hash:
            history_entry = PasswordHistory(
                user_id=self.id,
                password_hash=self.password_hash
            )
            db.session.add(history_entry)
        
        self.password_hash = new_hash
        self.password_changed_at = datetime.utcnow()
        self.failed_login_attempts = 0
        self.locked_until = None
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_password_expired(self, expiration_days=None):
        """
        Check if password has expired
        
        Args:
            expiration_days: Number of days before password expires (uses config if None)
            
        Returns:
            bool: True if password is expired
        """
        from flask import current_app
        
        if not self.password_changed_at:
            return True  # Force change if never set
        
        # System users don't have password expiration
        if self.is_system:
            return False
        
        if expiration_days is None:
            expiration_days = current_app.config.get('PASSWORD_EXPIRATION_DAYS', 90)
        
        expiration_date = self.password_changed_at + timedelta(days=expiration_days)
        return datetime.utcnow() > expiration_date
    
    def days_until_password_expires(self, expiration_days=None):
        """
        Get number of days until password expires
        
        Args:
            expiration_days: Number of days before password expires (uses config if None)
            
        Returns:
            int: Days until expiration (negative if already expired)
        """
        from flask import current_app
        
        if not self.password_changed_at or self.is_system:
            return None
        
        if expiration_days is None:
            expiration_days = current_app.config.get('PASSWORD_EXPIRATION_DAYS', 90)
        
        expiration_date = self.password_changed_at + timedelta(days=expiration_days)
        days_remaining = (expiration_date - datetime.utcnow()).days
        return days_remaining
    
    def is_locked(self):
        """Check if account is locked due to failed login attempts"""
        if not self.locked_until:
            return False
        return datetime.utcnow() < self.locked_until
    
    def increment_failed_login(self, max_attempts=None, lockout_minutes=None):
        """
        Increment failed login attempts and lock account if threshold reached
        
        Args:
            max_attempts: Maximum failed attempts before lockout (uses config if None)
            lockout_minutes: Minutes to lock account (uses config if None)
        """
        from flask import current_app
        from app.logger import get_logger
        
        if max_attempts is None:
            max_attempts = current_app.config.get('MAX_FAILED_LOGIN_ATTEMPTS', 5)
        if lockout_minutes is None:
            lockout_minutes = current_app.config.get('ACCOUNT_LOCKOUT_MINUTES', 30)
        
        self.failed_login_attempts += 1
        
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)
            logger = get_logger("asset_management.auth")
            logger.warning(f"Account locked for user {self.username} after {max_attempts} failed attempts")
    
    def reset_failed_login(self):
        """Reset failed login attempts on successful login"""
        self.failed_login_attempts = 0
        self.locked_until = None
    
    def is_authenticated(self):
        return self.is_active
    
    def __repr__(self):
        return f'<User {self.username}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id)) 