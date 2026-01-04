from app import db
from app.data.core.user_created_base import UserCreatedBase
from datetime import datetime

class PurchaseOrderHeader(UserCreatedBase):
    """
    Purchase order header (a purchase order document).

    Data model only: business logic (status transitions, totals, validations) belongs in
    `app/buisness/inventory/...`.
    """
    __tablename__ = 'purchase_order_headers'
    
    # Basic Fields
    po_number = db.Column(db.String(100), unique=True, nullable=False)
    vendor_name = db.Column(db.String(200), nullable=False)
    vendor_contact = db.Column(db.String(200), nullable=True)
    
    # Dates
    order_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    expected_delivery_date = db.Column(db.Date, nullable=True)
    
    # Status and Costs
    status = db.Column(db.String(20), default='Draft')  # Draft/Ordered/Shipped/Arrived/Cancelled (conventions)
    total_cost = db.Column(db.Float, nullable=True)
    shipping_cost = db.Column(db.Float, nullable=True)
    tax_amount = db.Column(db.Float, nullable=True)
    
    # Additional Info
    notes = db.Column(db.Text, nullable=True)
    
    # Foreign Keys
    major_location_id = db.Column(db.Integer, db.ForeignKey('major_locations.id'), nullable=True)
    storeroom_id = db.Column(db.Integer, db.ForeignKey('storerooms.id'), nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=True)
    
    # Relationships
    purchase_order_lines = db.relationship('PurchaseOrderLine', back_populates='purchase_order', lazy='dynamic')
    major_location = db.relationship('MajorLocation')
    storeroom = db.relationship('Storeroom')
    event = db.relationship('Event')
    
    def __repr__(self):
        return f'<PurchaseOrderHeader {self.po_number}: {self.vendor_name}>'
    
    def to_dict(self, include_relationships=False, include_audit_fields=True):
        """
        Convert model instance to dictionary
        
        Args:
            include_relationships (bool): Whether to include relationship data
            include_audit_fields (bool): Whether to include audit fields
            
        Returns:
            dict: Dictionary representation of the model
        """
        return super().to_dict(include_relationships=include_relationships, 
                              include_audit_fields=include_audit_fields)
    
    @classmethod
    def from_dict(cls, data_dict, user_id=None, skip_fields=None):
        """
        Create a model instance from a dictionary
        
        Args:
            data_dict (dict): Dictionary containing model data
            user_id (int, optional): User ID for audit fields
            skip_fields (list, optional): Fields to skip during creation
            
        Returns:
            Model instance (not saved to database)
        """
        return super().from_dict(data_dict, user_id=user_id, skip_fields=skip_fields)

