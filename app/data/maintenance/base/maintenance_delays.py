from app.data.core.user_created_base import UserCreatedBase
from app import db
from datetime import datetime
from sqlalchemy.orm import relationship

class MaintenanceDelay(UserCreatedBase):
    __tablename__ = 'maintenance_delays'

    maintenance_action_set_id = db.Column(db.Integer, db.ForeignKey('maintenance_action_sets.id'), nullable=False)
    delay_type = db.Column(db.String(20), nullable=True)
    delay_reason = db.Column(db.Text, nullable=True)
    delay_start_date = db.Column(db.DateTime, nullable=True)
    delay_end_date = db.Column(db.DateTime, nullable=True)
    delay_billable_hours = db.Column(db.Float, nullable=True)
    delay_notes = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(20), nullable=False, default='Medium')  # Low, Medium, High, Critical
    
    # Relationships
    maintenance_action_set = relationship('MaintenanceActionSet', back_populates='delays')
    
    def __repr__(self):
        return f'<MaintenanceDelay {self.id}: {self.delay_type} - {self.delay_reason}>'
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
 