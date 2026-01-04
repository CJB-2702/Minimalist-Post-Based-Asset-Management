from app import db
from app.data.core.user_created_base import UserCreatedBase
from datetime import datetime

class PartArrival(UserCreatedBase):
    """
    Individual parts received in a package.

    Conventions used by the inventory lifecycle:
    - Accepted vs rejected is represented by `status` plus `quantity_received`.
      If a receipt is partially rejected, it should be split into two PartArrival rows:
      one Accepted (qty accepted) and one Rejected (qty rejected).
    - Only Accepted receipts create inventory movements / affect ActiveInventory.
    """
    __tablename__ = 'part_arrivals'
    
    # Foreign Keys
    package_header_id = db.Column(db.Integer, db.ForeignKey('package_headers.id'), nullable=False)
    # Nullable to support "unlinked" arrivals (e.g., ad-hoc receipts not tied to a PO line).
    purchase_order_line_id = db.Column(db.Integer, db.ForeignKey('purchase_order_lines.id'), nullable=True)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    
    # Location Fields
    # Hard link to major location (required) - derived from package_header but can be overridden
    major_location_id = db.Column(db.Integer, db.ForeignKey('major_locations.id'), nullable=False)
    # Optional storeroom assignment
    storeroom_id = db.Column(db.Integer, db.ForeignKey('storerooms.id'), nullable=True)
    
    # Quantities
    quantity_received = db.Column(db.Float, nullable=False)
    quantity_linked_to_purchase_order_line = db.Column(db.Float, default=0.0)
    
    
    # Quality and Inspection
    condition = db.Column(db.String(20), default='Good')  # Good/Damaged/Mixed
    inspection_notes = db.Column(db.Text, nullable=True)
    received_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Pending')  # Pending/Arrived/Accepted/Rejected
    
    # Relationships
    package_header = db.relationship('PackageHeader', back_populates='part_arrivals')
    purchase_order_line = db.relationship('PurchaseOrderLine', back_populates='part_arrivals')
    part = db.relationship('PartDefinition')
    major_location = db.relationship('MajorLocation')
    storeroom = db.relationship('Storeroom')
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

