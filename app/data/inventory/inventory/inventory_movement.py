from app import db
from app.data.core.user_created_base import UserCreatedBase
from datetime import datetime

class InventoryMovement(UserCreatedBase):
    """
    Audit trail for all inventory changes with complete traceability chain.

    Conventions:
    - `quantity_delta` is positive for increases and negative for decreases.
    - Bin location tracking uses both "from" and "to" location fields for full traceability.
    """
    __tablename__ = 'inventory_movements'
    
    # Core Fields
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    
    # Movement Details
    movement_type = db.Column(db.String(30), nullable=False)  # Receipt/Issue/Adjustment/BinTransfer/Relocation/Return
    quantity_delta = db.Column('quantity', db.Float, nullable=False)
    movement_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Reference Fields
    reference_type = db.Column(db.String(50), nullable=True)
    reference_id = db.Column(db.Integer, nullable=True)

    # "From" location fields (source of movement)
    from_major_location_id = db.Column(db.Integer, db.ForeignKey('major_locations.id'), nullable=True)
    from_storeroom_id = db.Column(db.Integer, db.ForeignKey('storerooms.id'), nullable=True)
    from_location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)
    from_bin_id = db.Column(db.Integer, db.ForeignKey('bins.id'), nullable=True)

    # "To" location fields (destination of movement) - mirrors BinPrototype structure
    to_major_location_id = db.Column(db.Integer, db.ForeignKey('major_locations.id'), nullable=True)
    to_storeroom_id = db.Column(db.Integer, db.ForeignKey('storerooms.id'), nullable=True)
    to_location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)
    to_bin_id = db.Column(db.Integer, db.ForeignKey('bins.id'), nullable=True)
    
    # For compatibility with BinPrototype-expecting code, create aliases
    major_location_id = db.synonym('to_major_location_id')
    storeroom_id = db.synonym('to_storeroom_id') 
    location_id = db.synonym('to_location_id')
    bin_id = db.synonym('to_bin_id')
    
    # Cost and Notes
    unit_cost = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Specific References
    part_arrival_id = db.Column(db.Integer, db.ForeignKey('part_arrivals.id'), nullable=True)
    part_issue_id = db.Column(db.Integer, db.ForeignKey('part_issues.id'), nullable=True)
    
    # TRACEABILITY CHAIN FIELDS
    # Links to the original part arrival that introduced this inventory
    initial_arrival_id = db.Column(db.Integer, db.ForeignKey('part_arrivals.id'), nullable=True)
    # Links to the immediately preceding movement in the chain
    previous_movement_id = db.Column(db.Integer, db.ForeignKey('inventory_movements.id'), nullable=True)
    
    # Relationships
    part = db.relationship('PartDefinition')
    
    # "From" relationships
    from_major_location = db.relationship('MajorLocation', foreign_keys=[from_major_location_id])
    from_storeroom = db.relationship('Storeroom', foreign_keys=[from_storeroom_id])
    from_location = db.relationship('Location', foreign_keys=[from_location_id])
    from_bin = db.relationship('Bin', foreign_keys=[from_bin_id])
    
    # "To" relationships
    to_major_location = db.relationship('MajorLocation', foreign_keys=[to_major_location_id])
    to_storeroom = db.relationship('Storeroom', foreign_keys=[to_storeroom_id])
    to_location = db.relationship('Location', foreign_keys=[to_location_id])
    to_bin = db.relationship('Bin', foreign_keys=[to_bin_id])
    
    # Alias relationships for BinPrototype compatibility
    storeroom = db.relationship('Storeroom', foreign_keys=[to_storeroom_id], viewonly=True)
    location = db.relationship('Location', foreign_keys=[to_location_id], viewonly=True)
    
    # Direct movement references
    part_arrival = db.relationship('PartArrival', foreign_keys=[part_arrival_id], back_populates='inventory_movements')
    part_issue_ref = db.relationship('PartIssue', foreign_keys=[part_issue_id])
    
    # Traceability chain relationships
    initial_arrival = db.relationship(
        'PartArrival',
        foreign_keys=[initial_arrival_id],
        back_populates='initial_movements'
    )
    previous_movement = db.relationship(
        'InventoryMovement',
        remote_side='InventoryMovement.id',
        foreign_keys=[previous_movement_id],
        backref='subsequent_movements'
    )
    
    def __repr__(self):
        return f'<InventoryMovement {self.movement_type}: Part {self.part_id}, ΔQty {self.quantity_delta}>'
    
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

