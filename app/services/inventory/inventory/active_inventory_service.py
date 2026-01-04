"""
Active Inventory Service
Presentation service for active inventory list and queries.
"""

from typing import Dict, List, Optional, Tuple, Any
from flask_sqlalchemy.pagination import Pagination
from app import db
from app.data.inventory.inventory import ActiveInventory
from app.data.core.major_location import MajorLocation
from app.data.core.supply.part_definition import PartDefinition
from app.data.inventory.inventory.storeroom import Storeroom
from sqlalchemy.orm import joinedload


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
        per_page: int = 50,
        part_id: Optional[int] = None,
        part_number: Optional[str] = None,
        part_name: Optional[str] = None,
        location_id: Optional[int] = None,
        storeroom_id: Optional[int] = None,
        low_stock_only: bool = False,
        out_of_stock_only: bool = False,
        has_stock_only: bool = False,
        search: Optional[str] = None
    ) -> Tuple[Pagination, Dict[str, Any]]:
        """
        Get paginated active inventory with filters.
        
        Args:
            page: Page number
            per_page: Items per page
            part_id: Filter by part ID
            part_number: Filter by part number (partial match)
            part_name: Filter by part name (partial match)
            location_id: Filter by major location (via storeroom)
            storeroom_id: Filter by storeroom
            low_stock_only: Filter for low stock items only (0 < qty <= 10)
            out_of_stock_only: Filter for out of stock items only (qty <= 0)
            has_stock_only: Filter for items with stock (qty > 0)
            search: General search across part number and name
            
        Returns:
            Tuple of (pagination_object, form_options_dict)
        """
        from sqlalchemy.orm import joinedload
        
        query = ActiveInventory.query.options(
            joinedload(ActiveInventory.part),
            joinedload(ActiveInventory.storeroom).joinedload(Storeroom.major_location),
            joinedload(ActiveInventory.location),
            joinedload(ActiveInventory.bin)
        )
        
        if part_id:
            query = query.filter_by(part_id=part_id)
        
        # Build part-related filters
        part_filters = []
        if part_number:
            part_filters.append(PartDefinition.part_number.ilike(f'%{part_number}%'))
        if part_name:
            part_filters.append(PartDefinition.part_name.ilike(f'%{part_name}%'))
        if search:
            part_filters.append(
                db.or_(
                    PartDefinition.part_number.ilike(f'%{search}%'),
                    PartDefinition.part_name.ilike(f'%{search}%')
                )
            )
        
        if part_filters:
            query = query.join(PartDefinition).filter(db.or_(*part_filters))
        
        if location_id:
            # Filter by location via storeroom relationship
            query = query.join(Storeroom).filter(Storeroom.major_location_id == location_id)
        
        if storeroom_id:
            query = query.filter_by(storeroom_id=storeroom_id)
        
        if low_stock_only:
            # Filter for low stock items (quantity > 0 but low)
            query = query.filter(
                ActiveInventory.quantity_on_hand > 0,
                ActiveInventory.quantity_on_hand <= 10  # Simple threshold
            )
        
        if out_of_stock_only:
            query = query.filter(ActiveInventory.quantity_on_hand <= 0)
        
        if has_stock_only:
            query = query.filter(ActiveInventory.quantity_on_hand > 0)
        
        # Order by quantity_on_hand ascending (lowest first), then by part number
        # Use distinct() to avoid duplicates from joins, and join PartDefinition if needed for ordering
        if not part_filters:
            query = query.join(PartDefinition)
        query = query.distinct().order_by(
            ActiveInventory.quantity_on_hand.asc(),
            PartDefinition.part_number.asc()
        )
        
        # Pagination
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Get form options
        form_options = {
            'locations': MajorLocation.query.filter_by(is_active=True).order_by(MajorLocation.name.asc()).all(),
            'storerooms': Storeroom.query.order_by(Storeroom.room_name.asc()).all()
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
            threshold: Custom threshold (defaults to 10 if None)
            
        Returns:
            List of ActiveInventory objects
        """
        if threshold is None:
            threshold = 10
        
        query = ActiveInventory.query.filter(
            ActiveInventory.quantity_on_hand <= threshold,
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



