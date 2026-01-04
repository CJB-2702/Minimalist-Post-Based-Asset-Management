"""
Bin Model

Represents individual storage containers within a location.
Lowest level in the storage hierarchy: Storeroom → Location → Bin
"""

from app import db
from app.data.core.user_created_base import UserCreatedBase


class Bin(UserCreatedBase):
    """Individual storage container within a location"""
    __tablename__ = 'bins'
    
    # Basic Fields
    bin_tag = db.Column(db.String(50), nullable=False)  # Bin identifier (e.g., "Bin-A1", "Drawer-3")
    svg_element_id = db.Column(db.String(100), nullable=True)  # Links to SVG element ID for visual layouts
    
    # Foreign Keys
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    
    # Relationships
    location = db.relationship('Location', back_populates='bins')
    
    # Unique constraint: bin_tag must be unique within a location
    __table_args__ = (
        db.UniqueConstraint('location_id', 'bin_tag', name='uix_location_bin_tag'),
    )
    
    def __repr__(self):
        return f'<Bin {self.bin_tag} in {self.location.display_name if self.location else "Unknown"}>'
    
    @property
    def full_path(self):
        """Get full hierarchical path for this bin"""
        if self.location and self.location.storeroom:
            return f"{self.location.storeroom.room_name} > {self.location.display_name or self.location.location} > {self.bin_tag}"
        return self.bin_tag
    
    def to_dict(self, include_relationships=False, include_audit_fields=True):
        """
        Convert model instance to dictionary
        
        Args:
            include_relationships (bool): Whether to include relationship data
            include_audit_fields (bool): Whether to include audit fields
            
        Returns:
            dict: Dictionary representation of the model
        """
        result = super().to_dict(include_relationships=include_relationships, 
                                include_audit_fields=include_audit_fields)
        
        # Add computed properties
        result['full_path'] = self.full_path
        
        return result
    
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



