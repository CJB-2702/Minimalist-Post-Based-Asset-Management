"""
Template Builder Memory
Data model for storing draft template builds before submission.
"""

from app.data.core.user_created_base import UserCreatedBase
from app import db
from sqlalchemy.orm import relationship
import json


class TemplateBuilderMemory(UserCreatedBase):
    """
    Stores draft template builds in JSON format.
    Allows users to incrementally build templates before committing to production.
    """
    __tablename__ = 'template_build_memory'
    
    # Core fields
    name = db.Column(db.String(200), nullable=False)
    build_type = db.Column(db.String(50), nullable=True)  # e.g., "Preventive", "Corrective", "Inspection", "Overhaul"
    build_status = db.Column(db.String(20), default='Initialized', nullable=False)  # Initialized, In Progress, Ready for Review, Submitted, Abandoned
    
    # If this is a revision, we need to store the template_action_set_id
    # ONLY STORE THE SRC_REVISION_ID IF THIS IS A REVISION
    is_revision = db.Column(db.Boolean, default=False, nullable=False)
    src_revision_id = db.Column(db.Integer, db.ForeignKey('template_action_sets.id'), nullable=True)
    src_revision_number = db.Column(db.Integer, nullable=True)
    
    # Template reference (set after submission)
    template_action_set_id = db.Column(db.Integer, db.ForeignKey('template_action_sets.id'), nullable=True)
    
    # Relationships
    template_action_set = relationship('TemplateActionSet', foreign_keys=[template_action_set_id], lazy='select')
    
    # Build state stored as JSON
    build_state = db.Column(db.Text, nullable=True)  # JSON string containing complete template structure
    
    def get_build_state_dict(self) -> dict:
        """
        Deserialize build_state JSON to Python dict.
        
        Returns:
            dict: Build state as dictionary, or empty dict if None/empty
        """
        if not self.build_state:
            return {}
        try:
            return json.loads(self.build_state)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_build_state_dict(self, state_dict: dict):
        """
        Serialize build state dict to JSON string.
        
        Args:
            state_dict: Dictionary containing build state
        """
        self.build_state = json.dumps(state_dict) if state_dict else None
    
    def __repr__(self):
        return f'<TemplateBuilderMemory {self.id}: {self.name} ({self.build_status})>'

