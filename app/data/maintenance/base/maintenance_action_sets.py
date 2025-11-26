from app.data.core.event_info.event import EventDetailVirtual
from app.data.maintenance.virtual_action_set import VirtualActionSet
from app import db
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy

class MaintenanceActionSet(EventDetailVirtual, VirtualActionSet):
    """
    Maintenance Action Set - Container for a maintenance event
    Only one MaintenanceActionSet per Event (ONE-TO-ONE relationship)
    """
    __tablename__ = 'maintenance_action_sets'
    
    # Event coupling - REQUIRED, ONE-TO-ONE
    # event_id inherited from EventDetailVirtual (REQUIRED)
    # asset_id inherited from EventDetailVirtual
    
    # Template reference
    template_action_set_id = db.Column(db.Integer, db.ForeignKey('template_action_sets.id'), nullable=True)
    maintenance_plan_id = db.Column(db.Integer, db.ForeignKey('maintenance_plans.id'), nullable=True)
    
    # Planning
    planned_start_datetime = db.Column(db.DateTime, nullable=True)
    
    # Execution tracking
    status = db.Column(db.String(20), default='Planned')
    priority = db.Column(db.String(20), default='Medium')
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    actual_billable_hours = db.Column(db.Float, nullable=True)
    
    # Assignment
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    completed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Notes
    completion_notes = db.Column(db.Text, nullable=True)
    delay_notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    asset = relationship('Asset', foreign_keys='MaintenanceActionSet.asset_id', lazy='select')
    maintenance_plan = relationship('MaintenancePlan', back_populates='maintenance_action_sets', lazy='select')
    template_action_set = relationship('TemplateActionSet', foreign_keys=[template_action_set_id], back_populates='maintenance_action_sets', lazy='select', overlaps='maintenance_action_sets')
    actions = relationship('Action', back_populates='maintenance_action_set', lazy='selectin', order_by='Action.sequence_order', cascade='all, delete-orphan')
    delays = relationship('MaintenanceDelay', back_populates='maintenance_action_set', lazy='selectin', cascade='all, delete-orphan')
    
    # User relationships
    assigned_user = relationship('User', foreign_keys=[assigned_user_id], backref='assigned_maintenance_action_sets')
    assigned_by = relationship('User', foreign_keys=[assigned_by_id], backref='assigned_maintenance_action_sets_by_me')
    completed_by = relationship('User', foreign_keys=[completed_by_id], backref='completed_maintenance_action_sets')
    
    # Association proxies for easier access
    action_names = association_proxy('actions', 'action_name')
    action_statuses = association_proxy('actions', 'status')
    
    def __repr__(self):
        return f'<MaintenanceActionSet {self.id}: {self.task_name} - {self.status}>'
    
    # Class attributes for EventDetailVirtual
    event_type = 'maintenance'
    

    
    def create_event(self):
        """Create event for this maintenance action set"""
        from app.data.core.event_info.event import Event
        # Use created_by_id from UserCreatedBase
        if self.asset_id:
            self.event_id = Event.add_event(
                event_type=self.event_type,
                description=self.description,
                user_id=self.created_by_id,
                asset_id=self.asset_id
            )
        else:
            self.event_id = Event.add_event(
                event_type=self.event_type,
                description=self.description,
                user_id=self.created_by_id
            )
