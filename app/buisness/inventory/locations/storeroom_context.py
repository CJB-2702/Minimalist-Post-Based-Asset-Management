"""
Storeroom Context

Business wrapper around a Storeroom that manages its locations.
"""

from typing import List, Optional, Dict, Any
from app import db
from app.data.inventory.inventory.storeroom import Storeroom
from app.data.inventory.locations.location import Location
from app.data.inventory.inventory.active_inventory import ActiveInventory
from app.buisness.inventory.locations.location_context import LocationContext


class StoreroomContext:
    """
    Business wrapper around a Storeroom that manages its locations.
    
    Handles adding, removing, and getting locations for a storeroom.
    """
    
    def __init__(self, storeroom_id: int):
        """
        Initialize storeroom context
        
        Args:
            storeroom_id: ID of the storeroom
        """
        self.storeroom_id = storeroom_id
    
    @property
    def storeroom(self) -> Storeroom:
        """Get the storeroom instance"""
        storeroom = Storeroom.query.get(self.storeroom_id)
        if not storeroom:
            raise ValueError(f"Storeroom with ID {self.storeroom_id} not found")
        return storeroom
    
    @property
    def locations(self) -> List[LocationContext]:
        """Get all location contexts for this storeroom"""
        location_records = Location.query.filter_by(storeroom_id=self.storeroom_id).order_by(Location.location).all()
        return [LocationContext(loc.id) for loc in location_records]
    
    def get_location_context(self, location_id: int) -> Optional[LocationContext]:
        """
        Get a specific location context by ID
        
        Args:
            location_id: ID of the location
            
        Returns:
            LocationContext instance or None if not found
        """
        location = Location.query.get(location_id)
        if location and location.storeroom_id == self.storeroom_id:
            return LocationContext(location_id)
        return None
    
    def add_location(self, location: str, display_name: Optional[str] = None,
                    svg_element_id: Optional[str] = None, user_id: Optional[int] = None) -> LocationContext:
        """
        Add a new location to this storeroom
        
        Args:
            location: Location identifier
            display_name: Optional display name (defaults to location)
            svg_element_id: Optional SVG element ID for visual layouts
            user_id: ID of user creating the location
            
        Returns:
            LocationContext for the created location
        """
        # Create location
        location_obj = Location(
            storeroom_id=self.storeroom_id,
            location=location,
            display_name=display_name or location,
            svg_element_id=svg_element_id,
            created_by_id=user_id,
            updated_by_id=user_id
        )
        
        db.session.add(location_obj)
        db.session.flush()
        
        return LocationContext(location_obj.id)
    
    def remove_location(self, location_id: int) -> bool:
        """
        Remove a location from this storeroom
        
        Args:
            location_id: ID of the location to remove
            
        Returns:
            True if removed successfully
            
        Raises:
            ValueError: If location doesn't exist, doesn't belong to this storeroom, or has inventory
        """
        location = Location.query.get(location_id)
        if not location:
            raise ValueError(f"Location with ID {location_id} not found")
        
        if location.storeroom_id != self.storeroom_id:
            raise ValueError(f"Location {location_id} does not belong to storeroom {self.storeroom_id}")
        
        # Check for active inventory
        inventory_count = ActiveInventory.query.filter_by(location_id=location_id).count()
        if inventory_count > 0:
            raise ValueError(f"Cannot delete location: {inventory_count} active inventory records exist")
        
        db.session.delete(location)
        db.session.flush()
        
        return True
    
    def update_location(self, location_id: int, location: Optional[str] = None,
                       display_name: Optional[str] = None, svg_element_id: Optional[str] = None,
                       bin_layout_svg: Optional[str] = None, user_id: Optional[int] = None) -> LocationContext:
        """
        Update a location in this storeroom
        
        Args:
            location_id: ID of the location to update
            location: New location identifier (optional)
            display_name: New display name (optional)
            svg_element_id: New SVG element ID (optional)
            bin_layout_svg: New bin layout SVG (optional)
            user_id: ID of user updating the location
            
        Returns:
            LocationContext for the updated location
            
        Raises:
            ValueError: If location doesn't exist
        """
        location_obj = Location.query.get(location_id)
        if not location_obj or location_obj.storeroom_id != self.storeroom_id:
            raise ValueError(f"Location with ID {location_id} not found in this storeroom")
        
        # Update fields
        if location is not None:
            location_obj.location = location
        if display_name is not None:
            location_obj.display_name = display_name
        if svg_element_id is not None:
            location_obj.svg_element_id = svg_element_id
        if bin_layout_svg is not None:
            location_obj.bin_layout_svg = bin_layout_svg
        if user_id is not None:
            location_obj.updated_by_id = user_id
        
        db.session.flush()
        
        return LocationContext(location_id)



