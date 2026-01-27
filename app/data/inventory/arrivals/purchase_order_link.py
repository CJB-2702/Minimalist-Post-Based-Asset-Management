from app import db
from app.data.core.user_created_base import UserCreatedBase

class ArrivalPurchaseOrderLink(UserCreatedBase):
    """Association table linking arrival lines to purchase order lines"""
    __tablename__ = 'arrival_purchase_order_links'
    
    # Foreign Keys
    arrival_line_id = db.Column(db.Integer, db.ForeignKey('part_arrivals.id'), nullable=False)
    purchase_order_line_id = db.Column(db.Integer, db.ForeignKey('purchase_order_lines.id'), nullable=False)
    
    # Allocation Details
    quantity_linked = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    
    # Unique constraint to prevent duplicate links
    __table_args__ = (
        db.UniqueConstraint('arrival_line_id', 'purchase_order_line_id', name='uq_arrival_po_link'),
    )
    
    # Relationships
    arrival_line = db.relationship('ArrivalLine', back_populates='po_line_links')
    purchase_order_line = db.relationship('PurchaseOrderLine', back_populates='arrival_links')
    
    def __repr__(self):
        return f'<ArrivalPurchaseOrderLink Arrival:{self.arrival_line_id} POLine:{self.purchase_order_line_id} Qty:{self.quantity_linked}>'
    
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
