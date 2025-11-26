from app.data.core.user_created_base import UserCreatedBase
from app import db

class VirtualActionSet(UserCreatedBase):
    """
    Virtual base class for action sets
    Shared fields for MaintenanceActionSet and TemplateActionSet
    """
    __abstract__ = True
    
    task_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    estimated_duration = db.Column(db.Float, nullable=True)  # in hours
    safety_review_required = db.Column(db.Boolean, default=False)
    staff_count = db.Column(db.Integer, nullable=True)
    parts_cost = db.Column(db.Float, nullable=True)
    labor_hours = db.Column(db.Float, nullable=True)
    
    @classmethod
    def get_column_dict(cls) -> set:
        """Get set of column names for this model (excluding audit fields)."""
        return {
            'task_name', 'description', 'estimated_duration', 'safety_review_required',
            'staff_count', 'parts_cost', 'labor_hours'
        }

