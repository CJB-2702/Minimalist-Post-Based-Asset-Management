from app.data.core.user_created_base import UserCreatedBase
from app import db
from datetime import datetime
from sqlalchemy import Index

class MeterHistory(UserCreatedBase):
    """
    Meter History - Tracks meter readings for assets over time.
    
    This model stores historical meter readings (meter1-4) for assets,
    allowing tracking of meter changes over time. Meter history records
    can be linked to maintenance events via MaintenanceActionSet.meter_reading_id.
    """
    __tablename__ = 'meter_history'
    
    # Asset reference - REQUIRED
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    
    # Meter values (all nullable, but all four are stored for consistency)
    meter1 = db.Column(db.Float, nullable=True)
    meter2 = db.Column(db.Float, nullable=True)
    meter3 = db.Column(db.Float, nullable=True)
    meter4 = db.Column(db.Float, nullable=True)
    
    # Recording information
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    asset = db.relationship('Asset', backref='meter_history_records', lazy='select')
    recorded_by = db.relationship('User', foreign_keys=[recorded_by_id], backref='recorded_meter_history')
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_meter_history_asset_id', 'asset_id'),
        Index('idx_meter_history_recorded_at', 'recorded_at'),
    )
    
    def __repr__(self):
        return f'<MeterHistory {self.id}: Asset {self.asset_id} at {self.recorded_at}>'

