from app.data.maintenance.virtual_action_tool import VirtualActionTool
from app import db
from sqlalchemy.orm import relationship
from datetime import datetime

class ActionTool(VirtualActionTool):
    """
    Tools required for actions during maintenance execution
    Standalone copy - NO template reference (allows real-world substitution)
    Traceable via parent Action -> TemplateActionItem
    """
    __tablename__ = 'action_tools'
    
    # Parent reference - REQUIRED
    action_id = db.Column(db.Integer, db.ForeignKey('actions.id'), nullable=False)
    
    # Execution tracking
    status = db.Column(db.String(20), nullable=False, default='Planned')
    priority = db.Column(db.String(20), nullable=False, default='Medium')  # Low, Medium, High, Critical
    sequence_order = db.Column(db.Integer, nullable=False, default=1)
    
    # Assignment tracking
    assigned_to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_date = db.Column(db.DateTime, nullable=True)
    returned_date = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    action = relationship('Action', back_populates='action_tools')
    tool = relationship('Tool', foreign_keys='ActionTool.tool_id', lazy='select')
    
    # User relationships
    assigned_to_user = relationship('User', foreign_keys=[assigned_to_user_id], backref='assigned_action_tools')
    assigned_by = relationship('User', foreign_keys=[assigned_by_id], backref='assigned_action_tools_by_me')
    
    def __repr__(self):
        return f'<ActionTool {self.id}: Tool {self.tool_id} x{self.quantity_required} - {self.status}>'

