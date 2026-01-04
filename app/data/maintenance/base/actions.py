from app.data.maintenance.virtual_action_item import VirtualActionItem
from app import db
from sqlalchemy.orm import relationship
from datetime import datetime

class Action(VirtualActionItem):
    """
    Individual action within a maintenance event
    Sequence order is copied from template action item
    """
    __tablename__ = 'actions'
    
    # Parent reference - REQUIRED
    maintenance_action_set_id = db.Column(db.Integer, db.ForeignKey('maintenance_action_sets.id'), nullable=False)
    
    # Template reference
    template_action_item_id = db.Column(db.Integer, db.ForeignKey('template_actions.id'), nullable=True)
    
    # Sequence ordering - copied from template
    sequence_order = db.Column(db.Integer, nullable=False, default=1)
    
    # Execution tracking
    status = db.Column(db.String(20), nullable=False, default='Not Started')
    scheduled_start_time = db.Column(db.DateTime, nullable=True)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    billable_hours = db.Column(db.Float, nullable=True)
    completion_notes = db.Column(db.Text, nullable=True)
    
    # Assignment tracking
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    completed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    maintenance_action_set = relationship('MaintenanceActionSet', back_populates='actions')
    template_action_item = relationship('TemplateActionItem', foreign_keys=[template_action_item_id], back_populates='actions', lazy='select', overlaps='actions')
    part_demands = relationship('PartDemand', back_populates='action', cascade='all, delete-orphan', lazy='selectin', order_by='PartDemand.sequence_order')
    action_tools = relationship('ActionTool', back_populates='action', cascade='all, delete-orphan', lazy='selectin', order_by='ActionTool.sequence_order')
    
    
    # User relationships
    assigned_user = relationship('User', foreign_keys=[assigned_user_id], backref='assigned_actions')
    assigned_by = relationship('User', foreign_keys=[assigned_by_id], backref='assigned_actions_by_me')
    completed_by = relationship('User', foreign_keys=[completed_by_id], backref='completed_actions')
    
    def __repr__(self):
        return f'<Action {self.id}: {self.action_name} - {self.status}>'
