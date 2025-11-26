#!/usr/bin/env python3
"""
Vehicle Registration Detail Table
Store vehicle registration and licensing information
"""

from app.data.assets.asset_detail_virtual import AssetDetailVirtual
from app import db
from datetime import datetime

class VehicleRegistration(AssetDetailVirtual):
    """
    Store vehicle registration and licensing information
    """
    __tablename__ = 'vehicle_registration'
    
    # Vehicle registration fields
    license_plate = db.Column(db.String(20), nullable=True)
    registration_number = db.Column(db.String(50), nullable=True)
    registration_expiry = db.Column(db.Date, nullable=True)
    vin_number = db.Column(db.String(17), nullable=True)  # VIN is 17 characters
    state_registered = db.Column(db.String(2), nullable=True)  # State abbreviation
    registration_status = db.Column(db.String(50), default='Active')
    insurance_provider = db.Column(db.String(200), nullable=True)
    insurance_policy_number = db.Column(db.String(100), nullable=True)
    insurance_expiry = db.Column(db.Date, nullable=True)
    
    def __repr__(self):
        """String representation of the vehicle registration"""
        return f'<VehicleRegistration Asset:{self.asset_id} Plate:{self.license_plate}>'
    
    @property
    def registration_days_remaining(self):
        """Calculate registration days remaining"""
        if self.registration_expiry:
            remaining = (self.registration_expiry - datetime.now().date()).days
            return remaining
        return None
    
    @property
    def insurance_days_remaining(self):
        """Calculate insurance days remaining"""
        if self.insurance_expiry:
            remaining = (self.insurance_expiry - datetime.now().date()).days
            return remaining
        return None
    
    @property
    def is_registration_expired(self):
        """Check if registration is expired"""
        return self.registration_days_remaining and self.registration_days_remaining < 0
    
    @property
    def is_insurance_expired(self):
        """Check if insurance is expired"""
        return self.insurance_days_remaining and self.insurance_days_remaining < 0
    
    @property
    def is_registration_expiring_soon(self):
        """Check if registration is expiring within 30 days"""
        return self.registration_days_remaining and 0 <= self.registration_days_remaining <= 30
    
    @property
    def is_insurance_expiring_soon(self):
        """Check if insurance is expiring within 30 days"""
        return self.insurance_days_remaining and 0 <= self.insurance_days_remaining <= 30 