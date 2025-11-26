from pathlib import Path
from app import db
from app.data.core.user_created_base import UserCreatedBase
from datetime import datetime

class PurchaseOrderHeader(UserCreatedBase):
    """Purchase order header - represents a purchase order document"""
    __tablename__ = 'purchase_order_headers'
    
    # Basic Fields
    po_number = db.Column(db.String(100), unique=True, nullable=False)
    vendor_name = db.Column(db.String(200), nullable=False)
    vendor_contact = db.Column(db.String(200), nullable=True)
    
    # Dates
    order_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    expected_delivery_date = db.Column(db.Date, nullable=True)
    
    # Status and Costs
    status = db.Column(db.String(20), default='Draft')  # Draft/Submitted/Partial/Complete/Cancelled
    total_cost = db.Column(db.Float, nullable=True)
    shipping_cost = db.Column(db.Float, nullable=True)
    tax_amount = db.Column(db.Float, nullable=True)
    
    # Additional Info
    notes = db.Column(db.Text, nullable=True)
    
    # Foreign Keys
    major_location_id = db.Column(db.Integer, db.ForeignKey('major_locations.id'), nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=True)
    
    # Relationships
    purchase_order_lines = db.relationship('PurchaseOrderLine', back_populates='purchase_order', lazy='dynamic')
    major_location = db.relationship('MajorLocation')
    event = db.relationship('Event')
    
    def __repr__(self):
        return f'<PurchaseOrderHeader {self.po_number}: {self.vendor_name}>'
    
    # Properties
    @property
    def is_draft(self):
        """Check if status is Draft"""
        return self.status == 'Draft'
    
    @property
    def is_submitted(self):
        """Check if status is Submitted"""
        return self.status == 'Submitted'
    
    @property
    def is_complete(self):
        """Check if status is Complete"""
        return self.status == 'Complete'
    
    @property
    def is_cancelled(self):
        """Check if status is Cancelled"""
        return self.status == 'Cancelled'
    
    @property
    def lines_count(self):
        """Count of order lines"""
        return self.purchase_order_lines.count()
    
    @property
    def total_quantity(self):
        """Sum of all line quantities"""
        return sum(line.quantity_ordered for line in self.purchase_order_lines)
    
    # Methods
    def calculate_total(self):
        """Calculate total cost from lines"""
        lines_total = sum(line.line_total for line in self.purchase_order_lines)
        self.total_cost = lines_total + (self.shipping_cost or 0) + (self.tax_amount or 0)
        return self.total_cost
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'po_number': self.po_number,
            'vendor_name': self.vendor_name,
            'vendor_contact': self.vendor_contact,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'expected_delivery_date': self.expected_delivery_date.isoformat() if self.expected_delivery_date else None,
            'status': self.status,
            'total_cost': self.total_cost,
            'shipping_cost': self.shipping_cost,
            'tax_amount': self.tax_amount,
            'notes': self.notes,
            'major_location_id': self.major_location_id,
            'event_id': self.event_id,
            'lines_count': self.lines_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by_id': self.created_by_id
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        return cls(
            po_number=data.get('po_number'),
            vendor_name=data.get('vendor_name'),
            vendor_contact=data.get('vendor_contact'),
            order_date=data.get('order_date'),
            expected_delivery_date=data.get('expected_delivery_date'),
            status=data.get('status', 'Draft'),
            total_cost=data.get('total_cost'),
            shipping_cost=data.get('shipping_cost'),
            tax_amount=data.get('tax_amount'),
            notes=data.get('notes'),
            major_location_id=data.get('major_location_id'),
            event_id=data.get('event_id'),
            created_by_id=data.get('created_by_id')
        )

