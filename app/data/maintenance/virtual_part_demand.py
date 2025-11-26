from app.data.core.user_created_base import UserCreatedBase
from app import db

class VirtualPartDemand(UserCreatedBase):
    """Virtual part demands created from templates"""
    __abstract__ = True

    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    quantity_required = db.Column(db.Float, nullable=False, default=1.0)
    expected_cost = db.Column(db.Float, nullable=True)
    
    # Note: Relationship to Part is defined in concrete subclasses (PartDemand, TemplatePartDemand)
    
    @classmethod
    def get_column_dict(cls) -> set:
        """Get set of column names for this model (excluding audit fields)."""
        return {
            'part_id', 'notes', 'quantity_required', 'expected_cost'
        }