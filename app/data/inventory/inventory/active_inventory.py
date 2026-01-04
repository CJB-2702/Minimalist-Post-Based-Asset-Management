from app import db
from app.data.core.user_created_base import UserCreatedBase
from app.data.inventory.inventory.bin_prototype import BinPrototype


class ActiveInventory(BinPrototype, UserCreatedBase):
    """
    Current inventory levels by part and bin location.
    
    Inherits from BinPrototype to track physical bin locations within storerooms.
    Major location is derived from storeroom.major_location_id.
    """
    __tablename__ = 'active_inventory'
    
    # Foreign Keys
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    
    # Quantities
    quantity_on_hand = db.Column(db.Float, default=0.0)
    quantity_allocated = db.Column(db.Float, default=0.0)
    
    # Tracking
    last_movement_date = db.Column(db.DateTime, nullable=True)
    # Stored average unit cost (kept as existing DB column name `st_avg` for compatibility)
    unit_cost_avg = db.Column('st_avg', db.Float, nullable=True)
    
    # Unique constraint: part + storeroom + location + bin
    # Allows same part in multiple bins within a storeroom
    # location_id and bin_id can be NULL to allow storeroom-level inventory
    __table_args__ = (
        db.UniqueConstraint(
            'part_id', 
            'storeroom_id', 
            'location_id',
            'bin_id',
            name='uix_part_storeroom_location_bin'
        ),
    )
    
    # Relationships
    part = db.relationship('PartDefinition')
    storeroom = db.relationship('Storeroom', back_populates='active_inventory')
    location = db.relationship('Location', foreign_keys='ActiveInventory.location_id')
    bin = db.relationship('Bin', foreign_keys='ActiveInventory.bin_id')
    
    def __repr__(self):
        return f'<ActiveInventory Part:{self.part_id} Storeroom:{self.storeroom_id} Qty:{self.quantity_on_hand}>'
    
    # Properties
    @property
    def major_location_id(self):
        """Derive major location from storeroom"""
        if self.storeroom and self.storeroom.major_location_id:
            return self.storeroom.major_location_id
        return None
    
    @property
    def major_location(self):
        """Get major location from storeroom"""
        if self.storeroom and self.storeroom.major_location:
            return self.storeroom.major_location
        return None
    
    # NOTE: All business logic for adjustments, availability, low stock, and value calculations
    # should live in the business layer (inventory managers/services).
    
    def to_dict(self, include_relationships=False, include_audit_fields=True):
        """
        Convert model instance to dictionary
        
        Args:
            include_relationships (bool): Whether to include relationship data
            include_audit_fields (bool): Whether to include audit fields
            
        Returns:
            dict: Dictionary representation of the model
        """
        # Call UserCreatedBase.to_dict() directly to ensure proper handling
        # of relationships and audit fields (BinPrototype fields are included as columns)
        return UserCreatedBase.to_dict(self, include_relationships=include_relationships, 
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
        # Call UserCreatedBase.from_dict() directly to ensure proper handling
        return UserCreatedBase.from_dict(cls, data_dict, user_id=user_id, skip_fields=skip_fields)