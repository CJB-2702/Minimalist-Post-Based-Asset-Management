"""
Part Service
Presentation service for part-related queries (stock status, demands).
"""

from typing import Dict, List, Optional, Any
from app.data.maintenance.base.part_demands import PartDemand
from app.data.core.supply.part import Part
from app.services.inventory.inventory_service import InventoryService


class PartService:
    """
    Service for part-related presentation data.
    
    Provides methods for:
    - Getting part demands
    - Getting stock status
    - Getting stock summaries
    """
    
    @staticmethod
    def get_part_demands(part_id: int) -> List[PartDemand]:
        """
        Get all part demands for a part (read-only).
        
        Args:
            part_id: Part ID
            
        Returns:
            List of PartDemand objects
        """
        return PartDemand.query.filter_by(
            part_id=part_id
        ).order_by(PartDemand.created_at.desc()).all()
    
    @staticmethod
    def get_recent_demands(part_id: int, limit: int = 10) -> List[PartDemand]:
        """
        Get recent part demands for a part (read-only).
        
        Args:
            part_id: Part ID
            limit: Maximum number of demands to return
            
        Returns:
            List of recent PartDemand objects
        """
        return PartDemand.query.filter_by(
            part_id=part_id
        ).order_by(PartDemand.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_stock_status(part_id: int) -> Dict[str, Any]:
        """
        Get stock status for a part.
        
        Args:
            part_id: Part ID
            
        Returns:
            Dictionary with stock status information
        """
        part = Part.query.get(part_id)
        if not part:
            return {'error': 'Part not found'}
        
        current_stock = part.current_stock_level or 0
        minimum_stock = part.minimum_stock_level or 0
        
        is_low_stock = minimum_stock > 0 and current_stock <= minimum_stock
        is_out_of_stock = current_stock <= 0
        
        if is_out_of_stock:
            stock_status = 'out'
        elif is_low_stock:
            stock_status = 'low'
        else:
            stock_status = 'in_stock'
        
        return {
            'part_id': part_id,
            'current_stock_level': current_stock,
            'minimum_stock_level': minimum_stock,
            'is_low_stock': is_low_stock,
            'is_out_of_stock': is_out_of_stock,
            'stock_status': stock_status
        }
    
    @staticmethod
    def get_stock_summary(part_id: int) -> Dict[str, Any]:
        """
        Get comprehensive stock summary for a part.
        
        Combines inventory data with part info.
        
        Args:
            part_id: Part ID
            
        Returns:
            Dictionary with comprehensive stock information
        """
        # Get basic stock status
        stock_status = PartService.get_stock_status(part_id)
        
        # Get inventory summary across all locations
        inventory_summary = InventoryService.get_stock_summary(part_id)
        
        # Combine information
        return {
            **stock_status,
            **inventory_summary
        }
    
    @staticmethod
    def get_demand_count(part_id: int) -> int:
        """
        Get count of part demands for a part.
        
        Args:
            part_id: Part ID
            
        Returns:
            Count of part demands
        """
        return PartDemand.query.filter_by(part_id=part_id).count()



