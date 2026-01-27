"""
Asset Dispatchability Policy

Validates that an asset can be dispatched (work order constraints).
"""

from typing import TYPE_CHECKING
from app.buisness.dispatching.errors import AssetDispatchabilityError

if TYPE_CHECKING:
    from app.data.core.asset_info.asset import Asset


class AssetDispatchabilityPolicy:
    """
    Specification pattern for asset dispatchability validation.
    
    A StandardDispatch outcome cannot be set to "In Progress" while the asset
    has a work order in "In Progress" or "Blocked" status.
    
    This ensures that maintenance/repair work takes priority over dispatch operations.
    
    NOTE: This is currently a stub implementation that always returns True.
    Will be implemented when work order integration is complete.
    """
    
    @classmethod
    def check(cls, asset_id: int, target_status: str) -> None:
        """
        Check if an asset can be dispatched to the target status.
        
        Args:
            asset_id: The asset being dispatched
            target_status: The target resolution_status for the dispatch
            
        Raises:
            AssetDispatchabilityError: If asset cannot be dispatched (stub - never raised)
        """
        # Stub implementation - always allow dispatch
        # TODO: Implement work order conflict checking when work order module is integrated
        
        # Future implementation should:
        # 1. Query work orders for the asset
        # 2. Check if any work orders are in "In Progress" or "Blocked" status
        # 3. If target_status is "In Progress" and conflicting work orders exist, raise error
        
        pass
    
    @classmethod
    def can_dispatch(cls, asset_id: int, target_status: str) -> bool:
        """
        Check if an asset can be dispatched without raising an exception.
        
        Args:
            asset_id: The asset being dispatched
            target_status: The target resolution_status for the dispatch
            
        Returns:
            bool: True if asset can be dispatched (stub - always True)
        """
        # Stub implementation - always return True
        return True
    
    @classmethod
    def get_blocking_work_orders(cls, asset_id: int) -> list:
        """
        Get list of work orders blocking dispatch.
        
        Args:
            asset_id: The asset being checked
            
        Returns:
            list: List of blocking work orders (stub - always empty)
        """
        # Stub implementation - return empty list
        # TODO: Query and return actual blocking work orders
        return []
