"""
Location Model

Represents a specific storage area within a storeroom (shelf, rack, pallet space).
Intermediate level between Storeroom and Bin in the hierarchy.
"""

from app import db
from app.data.core.user_created_base import UserCreatedBase


class Location(UserCreatedBase):
    """Physical storage location within a storeroom"""
    __tablename__ = 'locations'
    
    # Basic Fields
    location = db.Column(db.String(50), nullable=False)  # Location identifier (e.g., "3-1", "Shelf A")
    display_name = db.Column(db.String(100), nullable=True)  # User-friendly name
    svg_element_id = db.Column(db.String(100), nullable=True)  # Links to SVG element ID for visual layouts
    bin_layout_svg = db.Column(db.Text, nullable=True)  # Stores bin layout SVG XML
    
    # Foreign Keys
    storeroom_id = db.Column(db.Integer, db.ForeignKey('storerooms.id'), nullable=False)
    
    # Relationships
    storeroom = db.relationship('Storeroom', back_populates='locations')
    bins = db.relationship('Bin', back_populates='location', cascade='all, delete-orphan', lazy='select')
    
    # Note: No unique constraint on (storeroom_id, location) to allow multiple movements
    # and active inventory rows with same location identifier
    
    def __repr__(self):
        return f'<Location {self.display_name or self.location} in {self.storeroom.room_name if self.storeroom else "Unknown"}>'
    
    @property
    def bin_count(self):
        """Get count of bins in this location"""
        return len(self.bins) if self.bins else 0
    
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
        result['bin_count'] = self.bin_count
        
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

