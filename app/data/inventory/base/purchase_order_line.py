from pathlib import Path
from app import db
from app.data.core.user_created_base import UserCreatedBase

class PurchaseOrderLine(UserCreatedBase):
    """Individual line items within a purchase order"""
    __tablename__ = 'purchase_order_lines'
    
    # Foreign Keys
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_order_headers.id'), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    
    # Quantities and Costs
    quantity_ordered = db.Column(db.Float, nullable=False)
    quantity_received = db.Column(db.Float, default=0.0)
    unit_cost = db.Column(db.Float, nullable=False)
    
    # Line Details
    line_number = db.Column(db.Integer, nullable=False)
    expected_delivery_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Pending')  # Pending/Partial/Complete/Cancelled
    
    # Relationships
    purchase_order = db.relationship('PurchaseOrderHeader', back_populates='purchase_order_lines')
    part = db.relationship('Part')
    # NOTE: back_populates commented out because PartDemand relationships are commented
    # to avoid circular import issues. Query via association table directly.
    part_demands = db.relationship(
        'PartDemand',
        secondary='part_demand_purchase_order_lines',
        # back_populates='purchase_order_lines',
        lazy='dynamic'
    )
    part_arrivals = db.relationship('PartArrival', back_populates='purchase_order_line', lazy='dynamic')
    
    def __repr__(self):
        return f'<PurchaseOrderLine {self.id}: Part {self.part_id}, Qty {self.quantity_ordered}>'
    
    # Properties
    @property
    def line_total(self):
        """Calculated line total"""
        return self.quantity_ordered * self.unit_cost
    
    @property
    def quantity_remaining(self):
        """Quantity not yet received"""
        return self.quantity_ordered - self.quantity_received
    
    @property
    def is_complete(self):
        """Check if fully received"""
        return self.quantity_received >= self.quantity_ordered
    
    @property
    def is_partial(self):
        """Check if partially received"""
        return 0 < self.quantity_received < self.quantity_ordered
    
    @property
    def fulfillment_percentage(self):
        """Calculate fulfillment percentage"""
        if self.quantity_ordered > 0:
            return (self.quantity_received / self.quantity_ordered) * 100
        return 0
    
    # Methods
    def calculate_line_total(self):
        """Calculate and return line total"""
        return self.line_total
    
    def update_quantity_received(self, amount):
        """Update received quantity"""
        self.quantity_received += amount
        
        # Update status based on fulfillment
        if self.is_complete:
            self.status = 'Complete'
        elif self.is_partial:
            self.status = 'Partial'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'purchase_order_id': self.purchase_order_id,
            'part_id': self.part_id,
            'quantity_ordered': self.quantity_ordered,
            'quantity_received': self.quantity_received,
            'quantity_remaining': self.quantity_remaining,
            'unit_cost': self.unit_cost,
            'line_total': self.line_total,
            'line_number': self.line_number,
            'expected_delivery_date': self.expected_delivery_date.isoformat() if self.expected_delivery_date else None,
            'notes': self.notes,
            'status': self.status,
            'fulfillment_percentage': self.fulfillment_percentage,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by_id': self.created_by_id
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        return cls(
            purchase_order_id=data.get('purchase_order_id'),
            part_id=data.get('part_id'),
            quantity_ordered=data.get('quantity_ordered'),
            quantity_received=data.get('quantity_received', 0.0),
            unit_cost=data.get('unit_cost'),
            line_number=data.get('line_number'),
            expected_delivery_date=data.get('expected_delivery_date'),
            notes=data.get('notes'),
            status=data.get('status', 'Pending'),
            created_by_id=data.get('created_by_id')
        )

