"""
Maintenance Assignment Manager
Business logic for managing assignments in maintenance events.
"""

from typing import Optional
from datetime import datetime
from app import db
from app.buisness.maintenance.base.structs.maintenance_action_set_struct import MaintenanceActionSetStruct
from app.data.core.user_info.user import User


class MaintenanceAssignmentManager:
    """
    Manages assignment of maintenance events to technicians.
    
    Accepts MaintenanceActionSetStruct to leverage:
    - Convenience properties (assigned_user_id, etc.)
    - Consistent data access patterns
    """
    
    def __init__(self, struct: MaintenanceActionSetStruct):
        """
        Initialize with MaintenanceActionSetStruct.
        
        Args:
            struct: MaintenanceActionSetStruct containing maintenance event data
        """
        self._struct = struct
        self._maintenance_action_set = struct.maintenance_action_set
    
    @property
    def assigned_user_id(self) -> Optional[int]:
        """Get assigned user ID (from struct)"""
        return self._struct.assigned_user_id
    
    @property
    def assigned_user(self):
        """Get assigned user (from struct)"""
        return self._struct.assigned_user
    
    def is_assigned(self) -> bool:
        """Check if maintenance is assigned"""
        return self._struct.assigned_user_id is not None
    
    def assign(
        self,
        assigned_user_id: int,
        assigned_by_id: int,
        planned_start_datetime: Optional[datetime] = None,
        priority: Optional[str] = None,
        notes: Optional[str] = None
    ) -> str:
        """
        Assign or reassign the maintenance event to a technician.
        
        Updates assignment fields, optional fields if provided, and returns
        a comment text documenting the assignment.
        
        Args:
            assigned_user_id: User ID to assign the maintenance to
            assigned_by_id: User ID of the manager assigning the maintenance
            planned_start_datetime: Optional planned start datetime to update
            priority: Optional priority to update
            notes: Optional assignment notes to include in comment
            
        Returns:
            Comment text documenting the assignment
            
        Raises:
            ValueError: If technician not found or not active
        """
        # Validate technician
        technician = User.query.get(assigned_user_id)
        if not technician or not technician.is_active:
            raise ValueError(f"Technician {assigned_user_id} not found or not active")
        
        # Update assignment
        self._maintenance_action_set.assigned_user_id = assigned_user_id
        self._maintenance_action_set.assigned_by_id = assigned_by_id
        
        # Update optional fields
        if planned_start_datetime is not None:
            self._maintenance_action_set.planned_start_datetime = planned_start_datetime
        if priority is not None:
            self._maintenance_action_set.priority = priority
        
        # Build comment text
        comment_parts = [f"Assigned to {technician.username}"]
        if notes:
            comment_parts.append(f"Notes: {notes}")
        
        comment_text = " | ".join(comment_parts)
        
        db.session.commit()
        self._struct.refresh()
        
        # Add comment to event
        self._struct.add_comment(
            user_id=assigned_by_id,
            content=comment_text,
            is_human_made=True  # Manual assignment
        )
        
        return comment_text
    
    def auto_assign(self, user_id: int, reason: str) -> bool:
        """
        Auto-assign if not already assigned.
        
        Args:
            user_id: User ID to assign to
            reason: Reason for auto-assignment (for comment)
            
        Returns:
            True if assignment occurred, False if already assigned
        """
        if self.is_assigned():
            return False
        
        # Validate user
        user = User.query.get(user_id)
        if not user or not user.is_active:
            return False
        
        # Assign
        self._maintenance_action_set.assigned_user_id = user_id
        self._maintenance_action_set.assigned_by_id = user_id
        
        db.session.commit()
        self._struct.refresh()
        
        # Add comment to event
        user = User.query.get(user_id)
        username = user.username if user else f"User {user_id}"
        comment_text = f"Auto-assigned to {username}. {reason}"
        self._struct.add_comment(
            user_id=user_id,
            content=comment_text,
            is_human_made=False  # Automated assignment
        )
        
        return True
    
    def should_auto_assign(self) -> bool:
        """Check if auto-assignment should occur (not already assigned)"""
        return not self.is_assigned()
    
    def validate_assignment(self, user_id: int) -> None:
        """
        Validate user can be assigned (active, has role, etc.).
        
        Args:
            user_id: User ID to validate
            
        Raises:
            ValueError: If user cannot be assigned
        """
        user = User.query.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        if not user.is_active:
            raise ValueError(f"User {user_id} is not active")
        # Add more validation as needed (role checks, etc.)

