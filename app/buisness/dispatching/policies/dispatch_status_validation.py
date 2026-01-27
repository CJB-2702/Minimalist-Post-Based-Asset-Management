"""
Dispatch Status Validation Policy

Ensures dispatch status is consistent with actual start/end dates.
"""

from typing import Optional
from datetime import datetime
from app.buisness.dispatching.errors import DispatchPolicyViolation


class DispatchStatusValidationPolicy:
    """
    Enforces dispatch status consistency with actual dates.
    
    Rules:
    1. If dispatch has actual_start → status must be "In Progress" or "Complete"
    2. If dispatch has actual_end → status must be "Complete"
    3. If status is "Planned" or "Cancelled" → cannot have actual_start or actual_end
    """
    
    @classmethod
    def validate(
        cls,
        status: str,
        actual_start: Optional[datetime],
        actual_end: Optional[datetime]
    ) -> None:
        """
        Validate dispatch status against actual dates.
        
        Args:
            status: The dispatch status
            actual_start: The actual start datetime (or None)
            actual_end: The actual end datetime (or None)
            
        Raises:
            DispatchPolicyViolation: If status is inconsistent with dates
        """
        # Rule 1: If actual_start exists, status must be In Progress or Complete
        if actual_start is not None:
            if status not in ['In Progress', 'Complete']:
                raise DispatchPolicyViolation(
                    f"Dispatch with actual start date must have status 'In Progress' or 'Complete', "
                    f"not '{status}'. Please either remove the actual start date or change the status."
                )
        
        # Rule 2: If actual_end exists, status must be Complete
        if actual_end is not None:
            if status != 'Complete':
                raise DispatchPolicyViolation(
                    f"Dispatch with actual end date must have status 'Complete', not '{status}'. "
                    f"Please either remove the actual end date or change the status to 'Complete'."
                )
        
        # Rule 3: If status is Planned or Cancelled, cannot have actual dates
        if status in ['Planned', 'Cancelled']:
            if actual_start is not None or actual_end is not None:
                date_info = []
                if actual_start:
                    date_info.append("actual start date")
                if actual_end:
                    date_info.append("actual end date")
                dates_str = " and ".join(date_info)
                
                raise DispatchPolicyViolation(
                    f"Dispatch with status '{status}' cannot have {dates_str}. "
                    f"Please remove the actual dates or change the status."
                )
    
    @classmethod
    def validate_status_transition(
        cls,
        old_status: str,
        new_status: str,
        actual_start: Optional[datetime],
        actual_end: Optional[datetime]
    ) -> None:
        """
        Validate status transition is consistent with actual dates.
        
        This is a convenience method that wraps validate() with better error context.
        
        Args:
            old_status: The current status
            new_status: The target status
            actual_start: The actual start datetime (or None)
            actual_end: The actual end datetime (or None)
            
        Raises:
            DispatchPolicyViolation: If new status is inconsistent with dates
        """
        try:
            cls.validate(new_status, actual_start, actual_end)
        except DispatchPolicyViolation as e:
            # Add context about the transition
            raise DispatchPolicyViolation(
                f"Cannot change status from '{old_status}' to '{new_status}': {str(e)}"
            )
