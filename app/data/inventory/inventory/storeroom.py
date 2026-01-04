"""
Storeroom Model

Represents a physical storeroom/warehouse room within a major location.
Storerooms contain bins where inventory is stored.
"""

from app import db
from app.data.core.user_created_base import UserCreatedBase


class Storeroom(UserCreatedBase):
    """Physical storeroom/warehouse room within a major location"""
    __tablename__ = 'storerooms'
    
    # Basic Fields
    room_name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.Text, nullable=True)
    raw_svg = db.Column(db.Text, nullable=True)  # Stores original uploaded SVG before processing
    svg_content = db.Column(db.Text, nullable=True)  # Stores processed storeroom layout SVG XML (scaled)
    
    # Foreign Keys
    major_location_id = db.Column(db.Integer, db.ForeignKey('major_locations.id'), nullable=False)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    major_location = db.relationship('MajorLocation')
    active_inventory = db.relationship('ActiveInventory', back_populates='storeroom', lazy='dynamic')
    locations = db.relationship('Location', back_populates='storeroom', cascade='all, delete-orphan', lazy='dynamic')
    
    def __repr__(self):
        return f'<Storeroom {self.room_name} at {self.major_location.name if self.major_location else "Unknown"}>'
    
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




