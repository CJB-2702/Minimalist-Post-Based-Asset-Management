from app import db
from app.data.core.user_created_base import UserCreatedBase

class PartDemandPurchaseOrderLink(UserCreatedBase):
    """Association table linking part demands to purchase order lines"""
    __tablename__ = 'part_demand_purchase_order_links'
    
    # Foreign Keys
    part_demand_id = db.Column(db.Integer, db.ForeignKey('part_demands.id'), nullable=False)
    purchase_order_line_id = db.Column(db.Integer, db.ForeignKey('purchase_order_lines.id'), nullable=False)
    
    # Allocation Details
    quantity_allocated = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    part_demand = db.relationship('PartDemand')
    purchase_order_line = db.relationship('PurchaseOrderLine')
    
    def __repr__(self):
        return f'<PartDemandPOLine Demand:{self.part_demand_id} POLine:{self.purchase_order_line_id} Qty:{self.quantity_allocated}>'
    
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

