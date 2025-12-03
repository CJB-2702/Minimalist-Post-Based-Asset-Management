"""
Portal User Data Model
Stores user-specific portal settings and cached data for QoL features.
Settings are user preferences, while cache stores computed/aggregated data.
"""

from app import db
from app.data.core.user_created_base import UserCreatedBase


class PortalUserData(UserCreatedBase):
    """
    Stores user-specific portal settings and cached data.
    
    Settings (JSON dicts) - User preferences that persist across sessions
    Cache (JSON dicts) - Computed/aggregated data that can be regenerated
    """
    __tablename__ = 'portal_user_data'
    
    # Foreign Key - one-to-one relationship with User
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    
    # Settings (JSON dicts) - User preferences
    general_settings = db.Column(db.JSON, default=dict)
    core_settings = db.Column(db.JSON, default=dict)
    maintenance_settings = db.Column(db.JSON, default=dict)
    # TODO: implement inventory_settings, supply_settings, etc. as needed
    
    # Cache (JSON dicts) - Computed/aggregated data
    general_cache = db.Column(db.JSON, default=dict)
    core_cache = db.Column(db.JSON, default=dict)
    maintenance_cache = db.Column(db.JSON, default=dict)
    # TODO: implement inventory_cache, supply_cache, etc. as needed
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id])
    
    def __repr__(self):
        return f'<PortalUserData user_id={self.user_id}>'

