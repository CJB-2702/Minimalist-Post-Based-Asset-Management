#!/usr/bin/env python3
"""
Purchase Information Detail Table
Store purchase-related information for assets
"""

from app.data.assets.asset_detail_virtual import AssetDetailVirtual
from app.data.core.event_info.event import Event
from app import db
from datetime import datetime
from sqlalchemy.ext.declarative import declared_attr

class PurchaseInfo(AssetDetailVirtual):
    """
    Store purchase-related information for assets
    """
    __tablename__ = 'purchase_info'
    
    # Purchase information fields
    purchase_date = db.Column(db.Date, nullable=True)
    purchase_price = db.Column(db.Float, nullable=True)
    purchase_vendor = db.Column(db.String(200), nullable=True)
    purchase_order_number = db.Column(db.String(100), nullable=True)
    warranty_start_date = db.Column(db.Date, nullable=True)
    warranty_end_date = db.Column(db.Date, nullable=True)
    purchase_notes = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        """String representation of the purchase info"""
        return f'<PurchaseInfo Asset:{self.asset_id} Vendor:{self.purchase_vendor}>'
    
 
    
    @property
    def warranty_days_remaining(self):
        """Calculate warranty days remaining"""
        if self.warranty_end_date:
            remaining = (self.warranty_end_date - datetime.now().date()).days
            return max(0, remaining)
        return None
    
    @property
    def is_under_warranty(self):
        """Check if asset is still under warranty"""
        return self.warranty_days_remaining and self.warranty_days_remaining > 0 