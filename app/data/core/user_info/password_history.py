"""
Password History Model
Tracks password history to prevent password reuse
"""

from app import db
from datetime import datetime


class PasswordHistory(db.Model):
    """
    Stores historical passwords for each user to prevent reuse
    
    This model helps enforce password history policies by storing hashed
    versions of previous passwords. When a user changes their password,
    the system can check against this history to prevent reusing recent passwords.
    """
    __tablename__ = 'password_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to User
    user = db.relationship('User', backref=db.backref('password_history', lazy='dynamic', cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<PasswordHistory user_id={self.user_id} created_at={self.created_at}>'
