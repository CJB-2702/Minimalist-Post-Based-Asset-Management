"""
Billable Hours Manager
Business logic for managing billable hours in maintenance events.
"""

from typing import Optional, Dict, Any
from app import db
from app.buisness.maintenance.base.structs.maintenance_action_set_struct import MaintenanceActionSetStruct


class BillableHoursManager:
    """
    Manages billable hours calculations and tracking.
    
    Accepts MaintenanceActionSetStruct to leverage:
    - Cached actions list for calculations
    - Convenience properties
    - Consistent data access patterns
    """
    
    def __init__(self, struct: MaintenanceActionSetStruct):
        """
        Initialize with MaintenanceActionSetStruct.
        
        Args:
            struct: MaintenanceActionSetStruct containing actions and maintenance data
        """
        self._struct = struct
        self._maintenance_action_set = struct.maintenance_action_set
    
    @property
    def calculated_hours(self) -> float:
        """Sum of all action billable hours (from struct's cached actions)"""
        return sum(a.billable_hours or 0 for a in self._struct.actions)
    
    @property
    def actual_hours(self) -> Optional[float]:
        """Get actual billable hours from maintenance_action_set"""
        if not hasattr(self._maintenance_action_set, 'actual_billable_hours'):
            return None
        return self._maintenance_action_set.actual_billable_hours
    
    def auto_update_if_greater(self) -> bool:
        """
        Auto-update actual_billable_hours if calculated sum is greater than current value.
        This implements the auto-update behavior when action billable hours change.
        
        Returns:
            True if update occurred, False otherwise
        """
        # Check if the attribute exists (handles cases where DB migration hasn't run)
        if not hasattr(self._maintenance_action_set, 'actual_billable_hours'):
            return False
        
        calculated = self.calculated_hours
        current = self.actual_hours or 0
        if calculated > current:
            self._maintenance_action_set.actual_billable_hours = calculated
            db.session.commit()
            self._struct.refresh()
            return True
        return False
    
    def set_actual_hours(self, manual_value: float, user_id: Optional[int] = None) -> None:
        """
        Manually set actual_billable_hours (allows override of calculated sum).
        
        Args:
            manual_value: Manual value to set (must be non-negative)
            user_id: Optional user ID for comment attribution
            
        Raises:
            ValueError: If manual_value is negative or attribute doesn't exist
        """
        if not hasattr(self._maintenance_action_set, 'actual_billable_hours'):
            raise ValueError("actual_billable_hours field not available. Database migration may be required.")
        if manual_value < 0:
            raise ValueError("Billable hours must be non-negative")
        
        old_value = self.actual_hours
        self._maintenance_action_set.actual_billable_hours = manual_value
        db.session.commit()
        self._struct.refresh()
        
        # Add comment to event
        if old_value != manual_value:
            comment_text = f"Billable hours updated: {manual_value:.2f}h"
            if old_value is not None:
                comment_text += f" (was {old_value:.2f}h)"
            self._struct.add_comment(
                user_id=user_id or 0,  # Use 0 if no user_id provided (system)
                content=comment_text,
                is_human_made=bool(user_id)  # Human-made if user_id provided
            )
    
    def sync_to_calculated(self, user_id: Optional[int] = None) -> None:
        """
        Reset actual_billable_hours to calculated sum.
        Used when user clicks "sync to sum" button.
        
        Args:
            user_id: Optional user ID for comment attribution
            
        Raises:
            ValueError: If attribute doesn't exist
        """
        if not hasattr(self._maintenance_action_set, 'actual_billable_hours'):
            raise ValueError("actual_billable_hours field not available. Database migration may be required.")
        
        old_value = self.actual_hours
        calculated = self.calculated_hours
        self._maintenance_action_set.actual_billable_hours = calculated
        db.session.commit()
        self._struct.refresh()
        
        # Add comment to event
        if old_value != calculated:
            comment_text = f"Billable hours synced to calculated sum: {calculated:.2f}h"
            if old_value is not None:
                comment_text += f" (was {old_value:.2f}h)"
            self._struct.add_comment(
                user_id=user_id or 0,  # Use 0 if no user_id provided (system)
                content=comment_text,
                is_human_made=bool(user_id)  # Human-made if user_id provided
            )
    
    def get_warning(self) -> Optional[str]:
        """
        Get warning message if actual_billable_hours is outside expected range.
        
        Warning conditions:
        - If actual < calculated (less than sum)
        - If actual > calculated * 4 (more than 4x sum)
        
        Returns:
            Warning message string or None if no warning needed
        """
        if not hasattr(self._maintenance_action_set, 'actual_billable_hours'):
            return None
        
        calculated = self.calculated_hours
        actual = self.actual_hours
        
        if actual is None:
            return None
        
        if actual < calculated:
            return f"Actual billable hours ({actual:.2f}) is less than calculated sum ({calculated:.2f})"
        elif calculated > 0 and actual > calculated * 4:
            return f"Actual billable hours ({actual:.2f}) is more than 4x the calculated sum ({calculated:.2f})"
        
        return None
    
    def validate_hours(self) -> Dict[str, Any]:
        """
        Get full validation report for billable hours.
        
        Returns:
            Dictionary with validation results
        """
        calculated = self.calculated_hours
        actual = self.actual_hours
        
        return {
            'calculated_hours': calculated,
            'actual_hours': actual,
            'warning': self.get_warning(),
            'is_synced': actual is not None and actual == calculated,
            'is_override': actual is not None and actual != calculated,
        }

