"""
Location Context

Business wrapper around a Location that manages its bins.
"""

from typing import List, Optional, Dict, Any
from app import db
from app.data.inventory.locations.location import Location
from app.data.inventory.locations.bin import Bin
from app.data.inventory.inventory.active_inventory import ActiveInventory


class LocationContext:
    """
    Business wrapper around a Location that manages its bins.
    
    Handles adding, removing, and getting bins for a location.
    """
    
    def __init__(self, location_id: int):
        """
        Initialize location context
        
        Args:
            location_id: ID of the location
        """
        self.location_id = location_id
    
    @property
    def location(self) -> Location:
        """Get the location instance"""
        location = Location.query.get(self.location_id)
        if not location:
            raise ValueError(f"Location with ID {self.location_id} not found")
        return location
    
    @property
    def bins(self) -> List[Bin]:
        """Get all bins for this location"""
        return list(self.location.bins)
    
    def get_bin(self, bin_id: int) -> Optional[Bin]:
        """
        Get a specific bin by ID
        
        Args:
            bin_id: ID of the bin
            
        Returns:
            Bin instance or None if not found
        """
        bin_obj = Bin.query.get(bin_id)
        if bin_obj and bin_obj.location_id == self.location_id:
            return bin_obj
        return None
    
    def add_bin(self, bin_tag: str, svg_element_id: Optional[str] = None, user_id: Optional[int] = None) -> Bin:
        """
        Add a new bin to this location
        
        Args:
            bin_tag: Bin identifier tag
            svg_element_id: Optional SVG element ID for visual layouts
            user_id: ID of user creating the bin
            
        Returns:
            Created Bin instance
            
        Raises:
            ValueError: If bin_tag already exists in this location
        """
        # Check for duplicate bin_tag within location
        existing_bin = Bin.query.filter_by(
            location_id=self.location_id,
            bin_tag=bin_tag
        ).first()
        
        if existing_bin:
            raise ValueError(f"Bin with tag '{bin_tag}' already exists in this location")
        
        # Create bin
        bin_obj = Bin(
            location_id=self.location_id,
            bin_tag=bin_tag,
            svg_element_id=svg_element_id,
            created_by_id=user_id,
            updated_by_id=user_id
        )
        
        db.session.add(bin_obj)
        db.session.flush()
        
        return bin_obj
    
    def remove_bin(self, bin_id: int) -> bool:
        """
        Remove a bin from this location
        
        Args:
            bin_id: ID of the bin to remove
            
        Returns:
            True if removed successfully
            
        Raises:
            ValueError: If bin doesn't exist, doesn't belong to this location, or has inventory
        """
        bin_obj = Bin.query.get(bin_id)
        if not bin_obj:
            raise ValueError(f"Bin with ID {bin_id} not found")
        
        if bin_obj.location_id != self.location_id:
            raise ValueError(f"Bin {bin_id} does not belong to location {self.location_id}")
        
        # Check for active inventory
        inventory_count = ActiveInventory.query.filter_by(bin_id=bin_id).count()
        if inventory_count > 0:
            raise ValueError(f"Cannot delete bin: {inventory_count} active inventory records exist")
        
        db.session.delete(bin_obj)
        db.session.flush()
        
        return True
    
    def update_bin(self, bin_id: int, bin_tag: Optional[str] = None, 
                   svg_element_id: Optional[str] = None, user_id: Optional[int] = None) -> Bin:
        """
        Update a bin in this location
        
        Args:
            bin_id: ID of the bin to update
            bin_tag: New bin tag (optional)
            svg_element_id: New SVG element ID (optional)
            user_id: ID of user updating the bin
            
        Returns:
            Updated Bin instance
            
        Raises:
            ValueError: If bin doesn't exist or validation fails
        """
        bin_obj = self.get_bin(bin_id)
        if not bin_obj:
            raise ValueError(f"Bin with ID {bin_id} not found in this location")
        
        # Update fields
        if bin_tag is not None:
            # Check for duplicate if changing bin_tag
            if bin_tag != bin_obj.bin_tag:
                existing_bin = Bin.query.filter_by(
                    location_id=self.location_id,
                    bin_tag=bin_tag
                ).first()
                
                if existing_bin:
                    raise ValueError(f"Bin with tag '{bin_tag}' already exists in this location")
                
                bin_obj.bin_tag = bin_tag
        
        if svg_element_id is not None:
            bin_obj.svg_element_id = svg_element_id
        
        if user_id is not None:
            bin_obj.updated_by_id = user_id
        
        db.session.flush()
        
        return bin_obj





