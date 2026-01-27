"""
Request Intent Lock Policy

Enforces immutability of request intent fields after first outcome assignment.

Field Categories:
- ALWAYS_LOCKED: Cannot be changed after request creation (e.g., requested_for)
- LOCKED_AFTER_OUTCOME: Locked once active_outcome_type is set (core request details)
- ALWAYS_EDITABLE: Can be edited at any time (operational details)
"""

from typing import Dict, Any, Set, TYPE_CHECKING
from app.buisness.dispatching.errors import RequestIntentLockError

if TYPE_CHECKING:
    from app.data.dispatching.request import DispatchRequest


class RequestIntentLockPolicy:
    """
    Enforces request intent immutability after outcome assignment.
    
    Core request fields (scheduling, asset type, location) become locked once an 
    outcome is assigned. Operational details (dispatch scope, meter usage, notes, 
    people info) remain editable to allow for adjustments during fulfillment.
    """
    
    # Fields that are ALWAYS locked after request creation
    ALWAYS_LOCKED: Set[str] = {
        'requested_for',  # Cannot change who the request is for
        'requested_by',   # Cannot change who created the request
    }
    
    # Fields that become locked after first outcome assignment (core request details)
    LOCKED_AFTER_OUTCOME: Set[str] = {
        'desired_start',        # Scheduling constraints
        'desired_end',
        'asset_type_id',        # Asset requirements
        'asset_subclass_text',
        'requested_asset_id',
        'major_location_id',    # Location requirements
    }
    
    # Fields that remain editable even after outcome assignment (operational details)
    ALWAYS_EDITABLE: Set[str] = {
        'dispatch_scope',       # Can be adjusted as plans evolve
        'estimated_meter_usage',
        'activity_location',    # Specific location details
        'num_people',          # People involved can change
        'names_freeform',
        'notes',               # Notes can always be updated
    }
    
    @classmethod
    def check(cls, request: 'DispatchRequest', updates: Dict[str, Any]) -> None:
        """
        Check if updates violate the intent lock policy.
        
        Args:
            request: The dispatch request being updated
            updates: Dictionary of field names and new values
            
        Raises:
            RequestIntentLockError: If locked fields are being modified
        """
        # Check for always-locked fields (regardless of outcome status)
        always_locked_updates = set(updates.keys()) & cls.ALWAYS_LOCKED
        if always_locked_updates:
            raise RequestIntentLockError(
                f"Cannot modify permanently locked fields after request creation. "
                f"Attempted to modify: {', '.join(sorted(always_locked_updates))}."
            )
        
        # If no active outcome, only always-locked fields are restricted
        if not request.active_outcome_type:
            return
        
        # Check if any outcome-locked fields are being updated
        locked_field_updates = set(updates.keys()) & cls.LOCKED_AFTER_OUTCOME
        
        if locked_field_updates:
            raise RequestIntentLockError(
                f"Cannot modify core request fields after outcome assignment. "
                f"Attempted to modify: {', '.join(sorted(locked_field_updates))}. "
                f"Create a follow-up request instead (previous_request_id)."
            )
    
    @classmethod
    def is_locked(cls, request: 'DispatchRequest') -> bool:
        """
        Check if request has outcome-locked fields.
        
        Args:
            request: The dispatch request
            
        Returns:
            bool: True if core intent fields are locked due to outcome assignment
        """
        return request.active_outcome_type is not None
    
    @classmethod
    def get_locked_fields(cls, request: 'DispatchRequest' = None) -> Set[str]:
        """
        Get set of field names that are currently locked.
        
        Args:
            request: Optional request to check outcome status
            
        Returns:
            Set of field names that are currently locked
        """
        locked = cls.ALWAYS_LOCKED.copy()
        if request and request.active_outcome_type:
            locked.update(cls.LOCKED_AFTER_OUTCOME)
        return locked
    
    @classmethod
    def get_editable_fields(cls, request: 'DispatchRequest' = None) -> Set[str]:
        """
        Get set of field names that are currently editable.
        
        Args:
            request: Optional request to check outcome status
            
        Returns:
            Set of field names that can be edited
        """
        if request and request.active_outcome_type:
            # After outcome: only always-editable fields
            return cls.ALWAYS_EDITABLE.copy()
        else:
            # Before outcome: always-editable + outcome-locked fields
            editable = cls.ALWAYS_EDITABLE.copy()
            editable.update(cls.LOCKED_AFTER_OUTCOME)
            return editable
    
    @classmethod
    def is_field_editable(cls, field_name: str, request: 'DispatchRequest' = None) -> bool:
        """
        Check if a specific field is editable.
        
        Args:
            field_name: Name of the field to check
            request: Optional request to check outcome status
            
        Returns:
            bool: True if the field can be edited
        """
        # Always-locked fields are never editable
        if field_name in cls.ALWAYS_LOCKED:
            return False
        
        # Always-editable fields are always editable
        if field_name in cls.ALWAYS_EDITABLE:
            return True
        
        # Outcome-locked fields depend on outcome status
        if field_name in cls.LOCKED_AFTER_OUTCOME:
            return request is None or request.active_outcome_type is None
        
        # Unknown fields default to editable
        return True
