"""
Inventory Movement Service
Presentation service for inventory movement history and traceability queries.
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from flask_sqlalchemy.pagination import Pagination
from app.data.inventory.base import InventoryMovement
from app.data.core.major_location import MajorLocation
from app.data.core.supply.part import Part


class InventoryMovementService:
    """
    Service for inventory movement presentation data.
    
    Provides methods for:
    - Building filtered movement queries
    - Getting movement history
    - Getting traceability chains (read-only view)
    """
    
    @staticmethod
    def get_list_data(
        page: int = 1,
        per_page: int = 20,
        part_id: Optional[int] = None,
        location_id: Optional[int] = None,
        movement_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Tuple[Pagination, Dict[str, Any]]:
        """
        Get paginated inventory movements with filters.
        
        Args:
            page: Page number
            per_page: Items per page
            part_id: Filter by part
            location_id: Filter by location
            movement_type: Filter by movement type (Arrival, Issue, Transfer, etc.)
            date_from: Filter by date from
            date_to: Filter by date to
            
        Returns:
            Tuple of (pagination_object, form_options_dict)
        """
        query = InventoryMovement.query
        
        if part_id:
            query = query.filter_by(part_id=part_id)
        
        if location_id:
            query = query.filter_by(major_location_id=location_id)
        
        if movement_type:
            query = query.filter_by(movement_type=movement_type)
        
        if date_from:
            query = query.filter(InventoryMovement.movement_date >= date_from)
        
        if date_to:
            query = query.filter(InventoryMovement.movement_date <= date_to)
        
        # Order by movement date (most recent first)
        query = query.order_by(InventoryMovement.movement_date.desc())
        
        # Pagination
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Get form options
        form_options = {
            'movement_types': ['Arrival', 'Issue', 'Transfer', 'Return', 'Adjustment']
        }
        
        return pagination, form_options
    
    @staticmethod
    def get_movement_history(
        part_id: Optional[int] = None,
        location_id: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[InventoryMovement]:
        """
        Get movement history for part/location (read-only).
        
        Args:
            part_id: Optional part ID filter
            location_id: Optional location ID filter
            limit: Optional limit on number of results
            
        Returns:
            List of InventoryMovement objects
        """
        query = InventoryMovement.query
        
        if part_id:
            query = query.filter_by(part_id=part_id)
        
        if location_id:
            query = query.filter_by(major_location_id=location_id)
        
        query = query.order_by(InventoryMovement.movement_date.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_traceability_chain(initial_arrival_id: int) -> List[InventoryMovement]:
        """
        Get full traceability chain for an arrival (read-only view).
        
        This provides a read-only view of the traceability chain.
        For operations that modify the chain, use InventoryManager.
        
        Args:
            initial_arrival_id: Part arrival ID
            
        Returns:
            List of InventoryMovement objects in chronological order
        """
        return InventoryMovement.query.filter_by(
            initial_arrival_id=initial_arrival_id
        ).order_by(InventoryMovement.movement_date).all()
    
    @staticmethod
    def get_movements_from_arrival(arrival_id: int) -> List[InventoryMovement]:
        """
        Get all movements originating from an arrival (read-only).
        
        Args:
            arrival_id: Part arrival ID
            
        Returns:
            List of InventoryMovement objects
        """
        return InventoryMovement.query.filter_by(
            initial_arrival_id=arrival_id
        ).order_by(InventoryMovement.movement_date).all()
    
    @staticmethod
    def get_movements_by_demand(part_demand_id: int) -> List[InventoryMovement]:
        """
        Get all movements associated with a part demand (read-only).
        
        Args:
            part_demand_id: Part demand ID
            
        Returns:
            List of InventoryMovement objects
        """
        return InventoryMovement.query.filter_by(
            part_demand_id=part_demand_id
        ).order_by(InventoryMovement.movement_date).all()



