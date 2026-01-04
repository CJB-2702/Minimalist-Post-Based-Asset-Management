"""
Part Context
Provides a clean interface for managing parts and their related data.
"""

from typing import List, Optional, Union
from app import db
from app.data.core.supply.part_definition import PartDefinition
from app.data.maintenance.base.part_demands import PartDemand


class PartContext:
    """
    Context manager for part operations.
    
    Provides a clean interface for:
    - Accessing part, part demands, stock status
    """
    
    def __init__(self, part: Union[PartDefinition, int]):
        """
        Initialize PartContext with a PartDefinition instance or ID.
        
        Args:
            part: PartDefinition instance or part ID
        """
        if isinstance(part, int):
            self._part = PartDefinition.query.get_or_404(part)
            self._part_id = part
        else:
            self._part = part
            self._part_id = part.id
        
        # Cache for lazy loading
        self._part_demands = None
    
    @property
    def part(self) -> PartDefinition:
        """Get the PartDefinition instance"""
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
    def demand_count(self) -> int:
        """Get the count of part demands for this part"""
        return len(self.part_demands)




