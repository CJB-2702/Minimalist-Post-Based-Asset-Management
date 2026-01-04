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
    quantity_accepted = db.Column(db.Float, default=0.0)
    quantity_rejected = db.Column(db.Float, default=0.0)
    unit_cost = db.Column(db.Float, nullable=False)
    
    # Line Details
    line_number = db.Column(db.Integer, nullable=False)
    expected_delivery_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Pending')  # Pending/Ordered/Shipped/Complete/Cancelled

    is_fake_for_inventory_adjustments = db.Column(db.Boolean, default=False)
    
    # Relationships
    purchase_order = db.relationship('PurchaseOrderHeader', back_populates='purchase_order_lines')
    part = db.relationship('PartDefinition')
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
    
    @property
    def quantity_received_total(self) -> float:
        """
        Total quantity accounted for on this PO line.

        Convention used by inventory lifecycle:
        - accepted + rejected counts toward line completion
        """
        return (self.quantity_accepted or 0.0) + (self.quantity_rejected or 0.0)
    
    @property
    def line_total(self) -> float:
        """
        Calculate the total cost for this line item.
        
        Returns:
            float: quantity_ordered * unit_cost
        """
        return (self.quantity_ordered or 0.0) * (self.unit_cost or 0.0)
    
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

