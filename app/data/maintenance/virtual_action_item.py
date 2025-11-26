from app.data.core.user_created_base import UserCreatedBase
from app import db

class VirtualActionItem(UserCreatedBase):
    """Virtual action items created from templates"""
    __abstract__ = True
    
    action_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)   
    estimated_duration = db.Column(db.Float, nullable=True)  # in hours
    expected_billable_hours = db.Column(db.Float, nullable=True)
    safety_notes = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    @classmethod
    def get_column_dict(cls) -> set:
        """Get set of column names for this model (excluding audit fields)."""
        return  {
            'action_name', 'description', 'estimated_duration', 'expected_billable_hours',
            'safety_notes', 'notes'
        }