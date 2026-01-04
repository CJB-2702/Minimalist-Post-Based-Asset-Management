"""
Part Service
Presentation service for part-related queries (stock status, demands).
"""

from typing import Dict, List, Optional, Any
from app.data.maintenance.base.part_demands import PartDemand
from app.data.core.supply.part_definition import PartDefinition
from app.services.inventory.inventory.inventory_service import InventoryService


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
    def get_stock_summary(part_id: int) -> Dict[str, Any]:
        """
        Get comprehensive stock summary for a part.
        
        Combines inventory data with part info.
        
        Args:
            part_id: Part ID
            
        Returns:
            Dictionary with comprehensive stock information
        """
        # Get inventory summary across all locations
        inventory_summary = InventoryService.get_stock_summary(part_id)
        
        return inventory_summary
    
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



