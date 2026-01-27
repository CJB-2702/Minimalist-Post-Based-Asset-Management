from app import db
from app.data.core.user_created_base import UserCreatedBase
from datetime import datetime

class ArrivalLine(UserCreatedBase):
    """
    Individual parts received in a package.
    
    Each arrival line represents a quantity of a part that was received.
    Arrivals create inventory movements and affect ActiveInventory.
    """
    __tablename__ = 'part_arrivals'
    
    # Foreign Keys
    package_header_id = db.Column(db.Integer, db.ForeignKey('package_headers.id'), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    
    # Location Fields
    # Hard link to major location (required) - derived from package_header but can be overridden
    major_location_id = db.Column(db.Integer, db.ForeignKey('major_locations.id'), nullable=False)
    # Optional storeroom assignment
    storeroom_id = db.Column(db.Integer, db.ForeignKey('storerooms.id'), nullable=True)
    
    # Quantities
    quantity_received = db.Column(db.Float, nullable=False)
    
    
    # Quality and Inspection
    condition = db.Column(db.String(20), default='Good')  # Good/Damaged/Mixed
    inspection_notes = db.Column(db.Text, nullable=True)
    received_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Received')  # Pending/Received/Processed
    
    # Relationships
    package_header = db.relationship('ArrivalHeader', back_populates='part_arrivals')
    part = db.relationship('PartDefinition')
    major_location = db.relationship('MajorLocation')
    storeroom = db.relationship('Storeroom')
    
    # Many-to-many relationship with PurchaseOrderLine through ArrivalPurchaseOrderLink
    po_line_links = db.relationship(
        'ArrivalPurchaseOrderLink',
        back_populates='arrival_line',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
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
    
    @property
    def linked_purchase_order_lines(self):
        """Get all purchase order lines linked to this arrival."""
        return [link.purchase_order_line for link in self.po_line_links.all()]
    
    @property
    def total_quantity_linked(self) -> float:
        """Calculate total quantity linked across all PO line links."""
        return sum(link.quantity_linked for link in self.po_line_links.all())
    
    @property
    def quantity_available_for_linking(self) -> float:
        """Calculate quantity available for linking to additional PO lines."""
        return self.quantity_received - self.total_quantity_linked
    
    def __repr__(self):
        return f'<ArrivalLine {self.id}: Part {self.part_id}, Qty {self.quantity_received}>'
    
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

