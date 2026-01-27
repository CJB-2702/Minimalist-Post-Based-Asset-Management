from app.data.core.user_created_base import UserCreatedBase
from app import db
from datetime import datetime
from sqlalchemy.orm import relationship

class AssetLimitationRecord(UserCreatedBase):
    """
    Asset Limitation Record - tracks operational capability limitations over time.
    
    This model tracks when an asset has degraded operational capability,
    separate from maintenance progress. It maintains a history of capability
    limitations and their resolutions.
    """
    __tablename__ = 'asset_limitation_records'

    # Core fields
    maintenance_action_set_id = db.Column(db.Integer, db.ForeignKey('maintenance_action_sets.id'), nullable=False)
    
    # Limitation details
    status = db.Column(db.String(100), nullable=False)  # Full mission capability status
    limitation_description = db.Column(db.Text, nullable=True)  # What is limited
    temporary_modifications = db.Column(db.Text, nullable=True)  # Procedural/hardware compensations
    
    # Timing
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)  # NULL = still active
    
    # Optional linkage to blocker (if blocker caused this limitation)
    maintenance_blocker_id = db.Column(db.Integer, db.ForeignKey('maintenance_blockers.id'), nullable=True)
    
    # Relationships
    maintenance_action_set = relationship('MaintenanceActionSet', back_populates='limitation_records')
    maintenance_blocker = relationship('MaintenanceBlocker', backref='limitation_records')
    
    def __repr__(self):
        active_str = "ACTIVE" if not self.end_time else "CLOSED"
        return f'<AssetLimitationRecord {self.id}: {self.status} - {active_str}>'
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    @property
    def is_active(self):
        """Check if this limitation record is currently active"""
        return self.end_time is None
    
    @property
    def allowable_capability_statuses(self):
        """List of allowable capability statuses"""
        return [
            'Non Mission Capable',
            'Partially Mission Capable - Functional Limitations',
            'Partially Mission Capable - Temporary Compensation',
            'Fully Mission Capable - Temporary Compensation'
        ]
    
    @property
    def is_degraded(self):
        """Check if this limitation represents a degraded state (without compensation)"""
        degraded_statuses = [
            'Non Mission Capable',
            'Partially Mission Capable - Functional Limitations'
        ]
        return self.status in degraded_statuses
    
    @property
    def requires_modification(self):
        """Check if this status requires temporary modifications"""
        compensation_statuses = [
            'Partially Mission Capable - Temporary Compensation',
            'Fully Mission Capable - Temporary Compensation'
        ]
        return self.status in compensation_statuses
