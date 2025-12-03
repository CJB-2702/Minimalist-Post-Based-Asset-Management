#!/usr/bin/env python3
"""
Smog Record Detail Table
Store smog test records for assets
"""

from app.data.assets.asset_detail_virtual import AssetDetailVirtual
from app.data.core.event_info.event import Event
from app import db
from datetime import datetime
from sqlalchemy.ext.declarative import declared_attr

class SmogRecord(AssetDetailVirtual):
    """
    Store smog test records for assets
    """
    __tablename__ = 'smog_record'
    
    # Smog test information fields
    smog_date = db.Column(db.Date, nullable=True)
    test_station = db.Column(db.String(200), nullable=True)
    certificate_number = db.Column(db.String(100), nullable=True)
    result = db.Column(db.String(50), nullable=True)  # e.g., "Pass", "Fail"
    expiration_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        """String representation of the smog record"""
        return f'<SmogRecord Asset:{self.asset_id} Date:{self.smog_date} Result:{self.result}>'
    
    @property
    def is_expired(self):
        """Check if smog certificate is expired"""
        if self.expiration_date:
            return self.expiration_date < datetime.now().date()
        return None
    
    @property
    def days_until_expiration(self):
        """Calculate days until expiration"""
        if self.expiration_date:
            days = (self.expiration_date - datetime.now().date()).days
            return days
        return None

