#!/usr/bin/env python3
"""
Toyota Warranty Receipt Detail Table
Store Toyota-specific warranty and service information
"""

from app.data.assets.asset_detail_virtual import AssetDetailVirtual
from app import db

class ToyotaWarrantyReceipt(AssetDetailVirtual):
    """
    Store Toyota-specific warranty and service information
    """
    __tablename__ = 'toyota_warranty_receipt'
    
    # Toyota warranty fields
    warranty_receipt_number = db.Column(db.String(100), nullable=True)
    warranty_type = db.Column(db.String(50), nullable=True)  # basic, powertrain, etc.
    warranty_mileage_limit = db.Column(db.Integer, nullable=True)
    warranty_time_limit_months = db.Column(db.Integer, nullable=True)
    dealer_name = db.Column(db.String(200), nullable=True)
    dealer_contact = db.Column(db.String(200), nullable=True)
    dealer_phone = db.Column(db.String(20), nullable=True)
    dealer_email = db.Column(db.String(200), nullable=True)
    service_history = db.Column(db.Text, nullable=True)
    warranty_claims = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        """String representation of the Toyota warranty receipt"""
        return f'<ToyotaWarrantyReceipt Asset:{self.asset_id} Receipt:{self.warranty_receipt_number}>'
    
    @property
    def warranty_mileage_remaining(self):
        """Calculate warranty mileage remaining"""
        if self.warranty_mileage_limit and self.asset.meter1:
            remaining = self.warranty_mileage_limit - self.asset.meter1
            return max(0, remaining)
        return None
    
    @property
    def warranty_time_remaining_months(self):
        """Calculate warranty time remaining in months"""
        if self.warranty_time_limit_months and self.created_at:
            from datetime import datetime
            months_elapsed = (datetime.now() - self.created_at).days / 30.44
            remaining = self.warranty_time_limit_months - months_elapsed
            return max(0, remaining)
        return None
    
    @property
    def is_under_warranty(self):
        """Check if asset is still under Toyota warranty"""
        mileage_ok = self.warranty_mileage_remaining is None or self.warranty_mileage_remaining > 0
        time_ok = self.warranty_time_remaining_months is None or self.warranty_time_remaining_months > 0
        return mileage_ok and time_ok 