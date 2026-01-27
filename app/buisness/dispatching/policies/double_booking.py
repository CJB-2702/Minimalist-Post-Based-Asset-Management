"""
Double Booking Specification

Prevents overlapping dispatches for the same asset.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from app import db
from app.buisness.dispatching.errors import DoubleBookingError

if TYPE_CHECKING:
    from app.data.dispatching.outcomes.standard_dispatch import StandardDispatch


class DoubleBookingSpecification:
    """
    Specification pattern for detecting double-booking conflicts.
    
    Validates that an asset is not dispatched for overlapping time periods.
    """
    
    @classmethod
    def check(
        cls,
        asset_id: int,
        scheduled_start: datetime,
        scheduled_end: datetime,
        exclude_dispatch_id: Optional[int] = None
    ) -> None:
        """
        Check for double-booking conflicts.
        
        Args:
            asset_id: The asset being dispatched
            scheduled_start: Start time of the dispatch
            scheduled_end: End time of the dispatch
            exclude_dispatch_id: Optional dispatch ID to exclude (for updates)
            
        Raises:
            DoubleBookingError: If a conflict is detected
        """
        if not asset_id:
            # No asset specified, no conflict possible
            return
        
        conflicts = cls.find_conflicts(
            asset_id,
            scheduled_start,
            scheduled_end,
            exclude_dispatch_id
        )
        
        if conflicts:
            conflict_details = cls._format_conflicts(conflicts)
            raise DoubleBookingError(
                f"Asset {asset_id} is already dispatched during the requested time period. "
                f"Conflicts: {conflict_details}"
            )
    
    @classmethod
    def find_conflicts(
        cls,
        asset_id: int,
        scheduled_start: datetime,
        scheduled_end: datetime,
        exclude_dispatch_id: Optional[int] = None
    ) -> list:
        """
        Find conflicting dispatches for an asset.
        
        Args:
            asset_id: The asset being dispatched
            scheduled_start: Start time of the dispatch
            scheduled_end: End time of the dispatch
            exclude_dispatch_id: Optional dispatch ID to exclude (for updates)
            
        Returns:
            list: List of conflicting StandardDispatch objects
        """
        from app.data.dispatching.outcomes.standard_dispatch import StandardDispatch
        
        # Query for overlapping dispatches
        query = StandardDispatch.query.filter(
            StandardDispatch.asset_dispatched_id == asset_id,
            StandardDispatch.cancelled == False,
            # Overlap condition: (start1 < end2) AND (end1 > start2)
            StandardDispatch.scheduled_start < scheduled_end,
            StandardDispatch.scheduled_end > scheduled_start
        )
        
        # Exclude the current dispatch if updating
        if exclude_dispatch_id:
            query = query.filter(StandardDispatch.id != exclude_dispatch_id)
        
        return query.all()
    
    @classmethod
    def has_conflicts(
        cls,
        asset_id: int,
        scheduled_start: datetime,
        scheduled_end: datetime,
        exclude_dispatch_id: Optional[int] = None
    ) -> bool:
        """
        Check if conflicts exist without raising an exception.
        
        Args:
            asset_id: The asset being dispatched
            scheduled_start: Start time of the dispatch
            scheduled_end: End time of the dispatch
            exclude_dispatch_id: Optional dispatch ID to exclude (for updates)
            
        Returns:
            bool: True if conflicts exist
        """
        conflicts = cls.find_conflicts(
            asset_id,
            scheduled_start,
            scheduled_end,
            exclude_dispatch_id
        )
        return len(conflicts) > 0
    
    @classmethod
    def _format_conflicts(cls, conflicts: list) -> str:
        """Format conflict list for error message"""
        if not conflicts:
            return "None"
        
        conflict_strs = []
        for conflict in conflicts[:3]:  # Show up to 3 conflicts
            conflict_strs.append(
                f"Dispatch ID {conflict.id} "
                f"({conflict.scheduled_start.strftime('%Y-%m-%d %H:%M')} to "
                f"{conflict.scheduled_end.strftime('%Y-%m-%d %H:%M')})"
            )
        
        if len(conflicts) > 3:
            conflict_strs.append(f"... and {len(conflicts) - 3} more")
        
        return "; ".join(conflict_strs)
