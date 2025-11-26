"""
Inventory Service
Presentation service for inventory availability checks and queries.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from app.data.inventory.base import (
    InventoryMovement,
    ActiveInventory
)


class InventoryService:
    """
    Service for inventory availability checks and queries.
    
    Provides read-only methods for:
    - Checking part availability
    - Querying inventory by location or part
    - Getting stock summaries
    """
    
    @staticmethod
    def check_availability(part_id: int, location_id: int, quantity: float) -> Dict[str, Any]:
        """
        Check if parts are available at location (read-only).
        
        Args:
            part_id: Part ID
            location_id: Location ID
            quantity: Required quantity
            
        Returns:
            Dictionary with availability info
        """
        active_inv = ActiveInventory.query.filter_by(
            part_id=part_id,
            major_location_id=location_id
        ).first()
        
        if not active_inv:
            return {
                'available': False,
                'quantity_on_hand': 0,
                'quantity_allocated': 0,
                'quantity_available': 0,
                'requested': quantity
            }
        
        return {
            'available': active_inv.quantity_available >= quantity,
            'quantity_on_hand': active_inv.quantity_on_hand,
            'quantity_allocated': active_inv.quantity_allocated,
            'quantity_available': active_inv.quantity_available,
            'requested': quantity
        }
    
    @staticmethod
    def get_inventory_by_location(location_id: int) -> List[ActiveInventory]:
        """
        Get all inventory at a location (read-only).
        
        Args:
            location_id: Location ID
            
        Returns:
            List of ActiveInventory objects
        """
        return ActiveInventory.query.filter_by(
            major_location_id=location_id
        ).filter(
            ActiveInventory.quantity_on_hand > 0
        ).all()
    
    @staticmethod
    def get_inventory_by_part(part_id: int) -> List[ActiveInventory]:
        """
        Get inventory for a part across all locations (read-only).
        
        Args:
            part_id: Part ID
            
        Returns:
            List of ActiveInventory objects
        """
        return ActiveInventory.query.filter_by(
            part_id=part_id
        ).filter(
            ActiveInventory.quantity_on_hand > 0
        ).all()
    
    @staticmethod
    def get_movement_history(
        part_id: Optional[int] = None,
        location_id: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[InventoryMovement]:
        """
        Get inventory movement history with optional filters (read-only).
        
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
    def get_stock_summary(part_id: int) -> Dict[str, Any]:
        """
        Get stock summary for a part across all locations.
        
        Args:
            part_id: Part ID
            
        Returns:
            Dictionary with stock summary information
        """
        inventory_list = InventoryService.get_inventory_by_part(part_id)
        
        total_on_hand = sum(inv.quantity_on_hand for inv in inventory_list)
        total_allocated = sum(inv.quantity_allocated for inv in inventory_list)
        total_available = sum(inv.quantity_available for inv in inventory_list)
        
        by_location = {
            inv.major_location_id: {
                'quantity_on_hand': inv.quantity_on_hand,
                'quantity_allocated': inv.quantity_allocated,
                'quantity_available': inv.quantity_available,
                'unit_cost_avg': inv.unit_cost_avg
            }
            for inv in inventory_list
        }
        
        return {
            'part_id': part_id,
            'total_on_hand': total_on_hand,
            'total_allocated': total_allocated,
            'total_available': total_available,
            'by_location': by_location,
            'location_count': len(by_location)
        }



