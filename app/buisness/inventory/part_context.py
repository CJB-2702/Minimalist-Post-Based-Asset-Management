"""
Part Context
Provides a clean interface for managing parts and their related data.
"""

from typing import List, Optional, Union
from app import db
from app.data.core.supply.part import Part
from app.data.maintenance.base.part_demands import PartDemand


class PartContext:
    """
    Context manager for part operations.
    
    Provides a clean interface for:
    - Accessing part, part demands, stock status
    """
    
    def __init__(self, part: Union[Part, int]):
        """
        Initialize PartContext with a Part instance or ID.
        
        Args:
            part: Part instance or part ID
        """
        if isinstance(part, int):
            self._part = Part.query.get_or_404(part)
            self._part_id = part
        else:
            self._part = part
            self._part_id = part.id
        
        # Cache for lazy loading
        self._part_demands = None
    
    @property
    def part(self) -> Part:
        """Get the Part instance"""
        return self._part
    
    @property
    def part_id(self) -> int:
        """Get the part ID"""
        return self._part_id
    
    @property
    def part_demands(self) -> List[PartDemand]:
        """
        Get all part demands for this part.
        
        DEPRECATED: This property is deprecated. Use PartService.get_part_demands() instead.
        Kept for backward compatibility but delegates to service layer.
        """
        if self._part_demands is None:
            # Import here to avoid circular import
            from app.services.inventory.part_service import PartService
            self._part_demands = PartService.get_part_demands(self._part_id)
        return self._part_demands
    
    def get_recent_demands(self, limit: int = 10) -> List[PartDemand]:
        """
        Get recent part demands for this part.
        
        DEPRECATED: This method is deprecated. Use PartService.get_recent_demands() instead.
        Kept for backward compatibility but delegates to service layer.
        
        Args:
            limit: Maximum number of demands to return
            
        Returns:
            List of recent PartDemand instances
        """
        # Import here to avoid circular import
        from app.services.inventory.part_service import PartService
        return PartService.get_recent_demands(self._part_id, limit)
    
    @property
    def is_low_stock(self) -> bool:
        """Check if part is low on stock"""
        if self._part.minimum_stock_level is None:
            return False
        return self._part.current_stock_level <= self._part.minimum_stock_level
    
    @property
    def is_out_of_stock(self) -> bool:
        """Check if part is out of stock"""
        return self._part.current_stock_level <= 0
    
    @property
    def stock_status(self) -> str:
        """Get stock status as string"""
        if self.is_out_of_stock:
            return 'out'
        elif self.is_low_stock:
            return 'low'
        else:
            return 'in_stock'
    
    @property
    def demand_count(self) -> int:
        """Get the count of part demands for this part"""
        return len(self.part_demands)




