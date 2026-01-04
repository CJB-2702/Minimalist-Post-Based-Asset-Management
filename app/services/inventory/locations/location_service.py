"""
Location Service

Handles data collection and summary functions for the presentation layer.
CRUD operations are handled by the business layer (LocationContext, StoreroomContext).
"""

from typing import Optional, List, Dict, Any
from app import db
from app.data.inventory.locations.location import Location
from app.buisness.inventory.locations.storeroom_context import StoreroomContext
from app.buisness.inventory.locations.location_context import LocationContext


class LocationService:
    """Service for data collection and summaries for locations"""
    
    @staticmethod
    def get_location(location_id: int) -> Optional[Location]:
        """
        Get a location by ID (for display purposes)
        
        Args:
            location_id: ID of the location
            
        Returns:
            Location instance or None
        """
        return Location.query.get(location_id)
    
    @staticmethod
    def get_locations_by_storeroom(storeroom_id: int) -> List[Location]:
        """
        Get all locations for a storeroom (for display purposes)
        
        Args:
            storeroom_id: ID of the storeroom
            
        Returns:
            List of Location instances
        """
        return Location.query.filter_by(storeroom_id=storeroom_id).order_by(Location.location).all()
    
    @staticmethod
    def get_location_inventory_summary(location_id: int) -> Dict[str, Any]:
        """
        Get inventory summary for a location
        
        Args:
            location_id: ID of the location
            
        Returns:
            Dictionary with inventory summary data
        """
        from app.data.inventory.inventory.active_inventory import ActiveInventory
        from sqlalchemy import func
        
        location = Location.query.get(location_id)
        if not location:
            raise ValueError(f"Location with ID {location_id} not found")
        
        # Get inventory count and total quantity
        inventory_summary = db.session.query(
            func.count(ActiveInventory.id).label('inventory_count'),
            func.sum(ActiveInventory.quantity_on_hand).label('total_quantity')
        ).filter(ActiveInventory.location_id == location_id).first()
        
        return {
            'location_id': location_id,
            'location': location.location,
            'display_name': location.display_name,
            'bin_count': location.bin_count,
            'inventory_count': inventory_summary.inventory_count or 0,
            'total_quantity': float(inventory_summary.total_quantity or 0)
        }
