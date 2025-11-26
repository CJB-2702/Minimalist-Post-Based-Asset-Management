from pathlib import Path
from app import db
from app.data.core.user_created_base import UserCreatedBase
from datetime import datetime

class PartArrival(UserCreatedBase):
    """Individual parts received in a package"""
    __tablename__ = 'part_arrivals'
    
    # Foreign Keys
    package_header_id = db.Column(db.Integer, db.ForeignKey('package_headers.id'), nullable=False)
    purchase_order_line_id = db.Column(db.Integer, db.ForeignKey('purchase_order_lines.id'), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    
    # Quantities
    quantity_received = db.Column(db.Float, nullable=False)
    quantity_accepted = db.Column(db.Float, default=0.0)
    quantity_rejected = db.Column(db.Float, default=0.0)
    
    # Quality and Inspection
    condition = db.Column(db.String(20), default='Good')  # Good/Damaged/Mixed
    inspection_notes = db.Column(db.Text, nullable=True)
    received_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Pending')  # Pending/Inspected/Accepted/Rejected
    
    # Relationships
    package_header = db.relationship('PackageHeader', back_populates='part_arrivals')
    purchase_order_line = db.relationship('PurchaseOrderLine', back_populates='part_arrivals')
    part = db.relationship('Part')
    # Specify foreign_keys since there are multiple FK paths
    inventory_movements = db.relationship(
        'InventoryMovement',
        foreign_keys='InventoryMovement.part_arrival_id',
        back_populates='part_arrival',
        lazy='dynamic'
    )
    
    # For traceability: movements that reference this as initial arrival
    initial_movements = db.relationship(
        'InventoryMovement',
        foreign_keys='InventoryMovement.initial_arrival_id',
        back_populates='initial_arrival',
        lazy='dynamic'
    )
    
    def __repr__(self):
        return f'<PartArrival {self.id}: Part {self.part_id}, Qty {self.quantity_received}>'
    
    # Properties
    @property
    def is_inspected(self):
        """Check if inspected"""
        return self.status in ['Inspected', 'Accepted', 'Rejected']
    
    @property
    def is_accepted(self):
        """Check if accepted"""
        return self.status == 'Accepted'
    
    @property
    def acceptance_rate(self):
        """Calculate acceptance rate"""
        if self.quantity_received > 0:
            return (self.quantity_accepted / self.quantity_received) * 100
        return 0
    
    # Methods
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'package_header_id': self.package_header_id,
            'purchase_order_line_id': self.purchase_order_line_id,
            'part_id': self.part_id,
            'quantity_received': self.quantity_received,
            'quantity_accepted': self.quantity_accepted,
            'quantity_rejected': self.quantity_rejected,
            'condition': self.condition,
            'inspection_notes': self.inspection_notes,
            'received_date': self.received_date.isoformat() if self.received_date else None,
            'status': self.status,
            'acceptance_rate': self.acceptance_rate,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by_id': self.created_by_id
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        return cls(
            package_header_id=data.get('package_header_id'),
            purchase_order_line_id=data.get('purchase_order_line_id'),
            part_id=data.get('part_id'),
            quantity_received=data.get('quantity_received'),
            quantity_accepted=data.get('quantity_accepted', 0.0),
            quantity_rejected=data.get('quantity_rejected', 0.0),
            condition=data.get('condition', 'Good'),
            inspection_notes=data.get('inspection_notes'),
            received_date=data.get('received_date'),
            status=data.get('status', 'Pending'),
            created_by_id=data.get('created_by_id')
        )

