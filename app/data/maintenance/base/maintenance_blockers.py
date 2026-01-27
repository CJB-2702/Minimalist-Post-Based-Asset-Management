from app.data.core.user_created_base import UserCreatedBase
from app import db
from sqlalchemy.orm import relationship

class MaintenanceBlocker(UserCreatedBase):
    __tablename__ = 'maintenance_blockers'

    maintenance_action_set_id = db.Column(db.Integer, db.ForeignKey('maintenance_action_sets.id'), nullable=False)
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
        return f'<MaintenanceBlocker {self.id}: {self.reason}>'
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
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
    
 