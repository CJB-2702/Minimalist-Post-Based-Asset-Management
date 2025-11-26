"""
Active Inventory Service
Presentation service for active inventory list and queries.
"""

from typing import Dict, List, Optional, Tuple, Any
from flask_sqlalchemy.pagination import Pagination
from app.data.inventory.base import ActiveInventory
from app.data.core.major_location import MajorLocation
from app.data.core.supply.part import Part


class ActiveInventoryService:
    """
    Service for active inventory presentation data.
    
    Provides methods for:
    - Building filtered active inventory queries
    - Getting stock level information
    - Finding low stock and out of stock items
    """
    
    @staticmethod
    def get_list_data(
        page: int = 1,
        per_page: int = 20,
        part_id: Optional[int] = None,
        location_id: Optional[int] = None,
        low_stock_only: bool = False,
        out_of_stock_only: bool = False
    ) -> Tuple[Pagination, Dict[str, Any]]:
        """
        Get paginated active inventory with filters.
        
        Args:
            page: Page number
            per_page: Items per page
            part_id: Filter by part
            location_id: Filter by location
            low_stock_only: Filter for low stock items only
            out_of_stock_only: Filter for out of stock items only
            
        Returns:
            Tuple of (pagination_object, form_options_dict)
        """
        query = ActiveInventory.query
        
        if part_id:
            query = query.filter_by(part_id=part_id)
        
        if location_id:
            query = query.filter_by(major_location_id=location_id)
        
        if low_stock_only:
            # Join with Part to access minimum_stock_level
            query = query.join(Part).filter(
                ActiveInventory.quantity_on_hand <= Part.minimum_stock_level,
                ActiveInventory.quantity_on_hand > 0
            )
        
        if out_of_stock_only:
            query = query.filter(ActiveInventory.quantity_on_hand <= 0)
        
        # Order by quantity_on_hand ascending (lowest first)
        query = query.order_by(ActiveInventory.quantity_on_hand.asc())
        
        # Pagination
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Get form options
        form_options = {
            'locations': MajorLocation.query.all()
            # Parts can be very large, consider pagination or search for form options
        }
        
        return pagination, form_options
    
    @staticmethod
    def get_by_part_and_location(part_id: int, location_id: int) -> Optional[ActiveInventory]:
        """
        Get active inventory for specific part and location.
        
        Args:
            part_id: Part ID
            location_id: Location ID
            
        Returns:
            ActiveInventory object or None if not found
        """
        return ActiveInventory.query.filter_by(
            part_id=part_id,
            major_location_id=location_id
        ).first()
    
    @staticmethod
    def get_low_stock_items(threshold: Optional[float] = None) -> List[ActiveInventory]:
        """
        Get items that are low on stock.
        
        Args:
            threshold: Optional custom threshold (uses part.minimum_stock_level if None)
            
        Returns:
            List of ActiveInventory objects
        """
        query = ActiveInventory.query.join(Part)
        
        if threshold is not None:
            query = query.filter(
                ActiveInventory.quantity_on_hand <= threshold,
                ActiveInventory.quantity_on_hand > 0
            )
        else:
            query = query.filter(
                ActiveInventory.quantity_on_hand <= Part.minimum_stock_level,
                ActiveInventory.quantity_on_hand > 0
            )
        
        return query.all()
    
    @staticmethod
    def get_out_of_stock_items() -> List[ActiveInventory]:
        """
        Get items that are out of stock.
        
        Returns:
            List of ActiveInventory objects
        """
        return ActiveInventory.query.filter(
            ActiveInventory.quantity_on_hand <= 0
        ).all()
    
    @staticmethod
    def get_stock_levels_by_location(location_id: int) -> Dict[int, Dict[str, float]]:
        """
        Get stock levels for all parts at a location.
        
        Args:
            location_id: Location ID
            
        Returns:
            Dictionary mapping part_id to stock level info
        """
        inventory_list = ActiveInventory.query.filter_by(
            major_location_id=location_id
        ).all()
        
        return {
            inv.part_id: {
                'on_hand': inv.quantity_on_hand,
                'allocated': inv.quantity_allocated,
                'available': inv.quantity_available
            }
            for inv in inventory_list
        }



