#!/usr/bin/env python3
"""
Asset Detail Virtual Base Class
Base class for all asset-specific detail tables
"""

from app.data.core.user_created_base import UserCreatedBase
from app import db
from sqlalchemy.ext.declarative import declared_attr
from app.data.core.sequences import AssetDetailIDManager

class AssetDetailVirtual(UserCreatedBase):
    """
    Base class for all asset-specific detail tables
    Provides common functionality for asset detail tables
    Uses shared global row ID sequence across all detail tables
    """
    __abstract__ = True
    
    # Common field for all asset detail tables
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    all_asset_detail_id = db.Column(db.Integer, nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=True)
    
    # Relationship to Asset
    @declared_attr
    def asset(cls):
        # Use the class name to create a unique backref
        backref_name = f'{cls.__name__.lower()}_details'
        return db.relationship('Asset', backref=backref_name)
    
    # Relationship to Event
    @declared_attr
    def event(cls):
        return db.relationship('Event', backref=f'{cls.__name__.lower()}_details')
    
    def __repr__(self):
        """String representation of the asset detail table"""
        return f'<{self.__class__.__name__} Asset:{self.asset_id} GlobalID:{self.all_asset_detail_id}>'
    
    def __init__(self, *args, **kwargs):
        """Initialize the asset detail record with global row ID assignment"""
        # Assign global row ID before calling parent constructor
        if 'all_asset_detail_id' not in kwargs:
            kwargs['all_asset_detail_id'] = AssetDetailIDManager.get_next_asset_detail_id()
        super().__init__(*args, **kwargs)