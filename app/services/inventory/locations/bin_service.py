"""
Bin Service

Handles data collection and summary functions for the presentation layer.
CRUD operations are handled by the business layer (LocationContext).
"""

from typing import Optional, List, Dict, Any
from app import db
from app.data.inventory.locations.bin import Bin


class BinService:
    """Service for data collection and summaries for bins"""
    
    @staticmethod
    def get_bin(bin_id: int) -> Optional[Bin]:
        """
        Get a bin by ID (for display purposes)
        
        Args:
            bin_id: ID of the bin
            
        Returns:
            Bin instance or None
        """
        return Bin.query.get(bin_id)
    
    @staticmethod
    def get_bins_by_location(location_id: int) -> List[Bin]:
        """
        Get all bins for a location (for display purposes)
        
        Args:
            location_id: ID of the location
            
        Returns:
            List of Bin instances
        """
        return Bin.query.filter_by(location_id=location_id).order_by(Bin.bin_tag).all()
    
    @staticmethod
    def get_bin_inventory_summary(bin_id: int) -> Dict[str, Any]:
        """
        Get inventory summary for a bin
        
        Args:
            bin_id: ID of the bin
            
        Returns:
            Dictionary with inventory summary data
        """
        from app.data.inventory.inventory.active_inventory import ActiveInventory
        from sqlalchemy import func
        
        bin_obj = Bin.query.get(bin_id)
        if not bin_obj:
            raise ValueError(f"Bin with ID {bin_id} not found")
        
        # Get inventory count and total quantity
        inventory_summary = db.session.query(
            func.count(ActiveInventory.id).label('inventory_count'),
            func.sum(ActiveInventory.quantity_on_hand).label('total_quantity')
        ).filter(ActiveInventory.bin_id == bin_id).first()
        
        return {
            'bin_id': bin_id,
            'bin_tag': bin_obj.bin_tag,
            'full_path': bin_obj.full_path,
            'inventory_count': inventory_summary.inventory_count or 0,
            'total_quantity': float(inventory_summary.total_quantity or 0)
        }
