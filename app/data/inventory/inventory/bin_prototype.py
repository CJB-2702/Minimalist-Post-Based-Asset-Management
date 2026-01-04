"""
BinPrototype Base Class

Base class for bin-level inventory tracking with hierarchical location structure.
Used as a mixin for ActiveInventory to track physical bin locations.
"""

from app import db


class BinPrototype:
    """
    Base class for bin-level tracking.
    
    Provides hierarchical location tracking through Location and Bin foreign keys.
    Supports optional location/bin assignment for flexibility.
    """
    
    # Foreign Keys
    major_location_id = db.Column(db.Integer, db.ForeignKey('major_locations.id'), nullable=False)
    storeroom_id = db.Column(db.Integer, db.ForeignKey('storerooms.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)
    bin_id = db.Column(db.Integer, db.ForeignKey('bins.id'), nullable=True)
    
    # Note: Relationships are defined in the inheriting class (ActiveInventory)
    
    # Properties
    @property
    def location_string(self):
        """Get location identifier string"""
        if hasattr(self, '_location') and self._location:
            return self._location.display_name or self._location.location
        if self.location_id:
            # Try to access location relationship if available
            if hasattr(self, 'location') and self.location:
                return self.location.display_name or self.location.location
        return "Unassigned"
    
    @property
    def bin_string(self):
        """Get bin tag string"""
        if hasattr(self, '_bin') and self._bin:
            return self._bin.bin_tag
        if self.bin_id:
            # Try to access bin relationship if available
            if hasattr(self, 'bin') and self.bin:
                return self.bin.bin_tag
        return "Unassigned"
    
    @property
    def full_location_path(self):
        """Get full hierarchical path (e.g., 'Los Angeles Main > Shelf 3-1 > Bin A1')"""
        parts = []
        
        # Get storeroom
        if hasattr(self, 'storeroom') and self.storeroom:
            parts.append(self.storeroom.room_name)
        
        # Get location
        location_str = self.location_string
        if location_str != "Unassigned":
            parts.append(location_str)
        
        # Get bin
        bin_str = self.bin_string
        if bin_str != "Unassigned":
            parts.append(bin_str)
        
        if not parts:
            return "Unassigned"
        
        return " > ".join(parts)
    
    @property
    def is_assigned(self):
        """Check if location/bin is assigned"""
        return self.location_id is not None or self.bin_id is not None
    
    def to_dict(self, include_relationships=False, include_audit_fields=True):
        """
        Convert model instance to dictionary
        
        Args:
            include_relationships (bool): Whether to include relationship data
            include_audit_fields (bool): Whether to include audit fields
            
        Returns:
            dict: Dictionary representation of the model
        """
        from datetime import datetime
        from sqlalchemy import inspect
        
        result = {}
        mapper = inspect(self.__class__)
        
        for column in mapper.columns:
            value = getattr(self, column.key, None)
            
            # Handle datetime serialization
            if isinstance(value, datetime):
                result[column.key] = value.isoformat()
            else:
                result[column.key] = value
        
        return result
    
    @classmethod
    def from_dict(cls, data_dict, user_id=None, skip_fields=None):
        """
        Create a model instance from a dictionary
        
        Args:
            data_dict (dict): Dictionary containing model data
            user_id (int, optional): User ID for audit fields (not used for BinPrototype)
            skip_fields (list, optional): Fields to skip during creation
            
        Returns:
            Model instance (not saved to database)
        """
        from sqlalchemy import inspect
        from datetime import datetime
        
        if skip_fields is None:
            skip_fields = []
        
        # Get model columns
        mapper = inspect(cls)
        columns = {c.key: c for c in mapper.columns}
        
        # Filter data to only include valid columns
        filtered_data = {}
        for key, value in data_dict.items():
            if key in columns and key not in skip_fields:
                # Handle datetime strings
                if isinstance(value, str) and key in ['created_at', 'updated_at']:
                    try:
                        filtered_data[key] = datetime.fromisoformat(value)
                    except (ValueError, AttributeError):
                        filtered_data[key] = value
                else:
                    filtered_data[key] = value
        
        # Create instance
        instance = cls(**filtered_data)
        
        return instance

