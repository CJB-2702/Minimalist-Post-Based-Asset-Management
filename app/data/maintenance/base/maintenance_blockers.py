from app.data.core.user_created_base import UserCreatedBase
from app import db
from datetime import datetime
from sqlalchemy.orm import relationship

class MaintenanceBlocker(UserCreatedBase):
    __tablename__ = 'maintenance_blockers'

    maintenance_action_set_id = db.Column(db.Integer, db.ForeignKey('maintenance_action_sets.id'), nullable=False)
    mission_capability_status = db.Column(db.String(20), nullable=True)
    reason = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    billable_hours = db.Column(db.Float, nullable=True)
    expected_resolution_date = db.Column(db.DateTime, nullable=True)
    priority = db.Column(db.String(20), nullable=False, default='Medium')  # Low, Medium, High, Critical
    
    # Relationships
    maintenance_action_set = relationship('MaintenanceActionSet', back_populates='blockers')
    
    def __repr__(self):
        return f'<MaintenanceBlocker {self.id}: {self.mission_capability_status} - {self.reason}>'
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def allowable_capability_statuses(self):
        return [
            'Fully Mission Capable',
            'Mission Capable - Ignorable Damage or Issue',
            'Mission Capable - Temporary Procedural or Hardware Work Arounds',
            'Partially Mission Capable - Functional Limitations',
            'Non Mission Capable'
        ]
    
    @property
    def allowable_reasons(self):
        return [
            'Parts Not Available',
            'Equipment Unavailable',
            'Staff Not Available',
            'Facility Not Available',
            'Safety Concerns',
            'Major Issues Discovered',
            'Other'
        ]
    
 