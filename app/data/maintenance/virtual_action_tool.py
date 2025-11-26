from app.data.core.user_created_base import UserCreatedBase
from app import db

class VirtualActionTool(UserCreatedBase):
    """
    Virtual base class for action tool requirements
    Shared fields for ActionTool, TemplateActionTool, and ProtoActionTool
    """
    __abstract__ = True
    
    tool_id = db.Column(db.Integer, db.ForeignKey('tools.id'), nullable=False)
    quantity_required = db.Column(db.Integer, default=1)
    notes = db.Column(db.Text, nullable=True)
    
    # Note: Relationship to Tool is defined in concrete subclasses (ActionTool, TemplateActionTool, ProtoActionTool)
    
    @classmethod
    def get_column_dict(cls) -> set:
        """Get set of column names for this model (excluding audit fields)."""
        return {
            'tool_id', 'quantity_required', 'notes'
        }

