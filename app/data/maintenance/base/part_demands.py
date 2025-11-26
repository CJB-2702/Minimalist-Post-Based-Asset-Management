from app.data.maintenance.virtual_part_demand import VirtualPartDemand
from app import db
from sqlalchemy.orm import relationship
from datetime import datetime

class PartDemand(VirtualPartDemand):
    """
    Parts required for actions during maintenance execution
    Standalone copy - NO template reference (allows real-world substitution)
    Traceable via parent Action -> TemplateActionItem
    """
    __tablename__ = 'part_demands'
    
    # Parent reference - REQUIRED
    action_id = db.Column(db.Integer, db.ForeignKey('actions.id'), nullable=False)
    
    # Execution tracking
    status = db.Column(db.String(20), nullable=False, default='Planned')
    priority = db.Column(db.String(20), nullable=False, default='Medium')  # Low, Medium, High, Critical
    sequence_order = db.Column(db.Integer, nullable=False, default=1)
    
    # Approval workflow
    requested_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    maintenance_approval_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    maintenance_approval_date = db.Column(db.DateTime, nullable=True)
    supply_approval_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    supply_approval_date = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    action = relationship('Action', back_populates='part_demands')
    part = relationship('Part', foreign_keys='PartDemand.part_id', lazy='select')
    
    # User relationships
    requested_by = relationship('User', foreign_keys=[requested_by_id], backref='requested_part_demands')
    maintenance_approval_by = relationship('User', foreign_keys=[maintenance_approval_by_id], backref='maintenance_approved_part_demands')
    supply_approval_by = relationship('User', foreign_keys=[supply_approval_by_id], backref='supply_approved_part_demands')
    
    def __repr__(self):
        return f'<PartDemand {self.id}: Part {self.part_id} x{self.quantity_required} - {self.status}>'
