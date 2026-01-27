"""
Maintenance Blocker Manager
Business logic for managing blockers in maintenance events.
"""

from typing import List, Optional
from datetime import datetime
from app import db
from app.buisness.maintenance.base.structs.maintenance_action_set_struct import MaintenanceActionSetStruct
from app.data.maintenance.base.maintenance_blockers import MaintenanceBlocker


class MaintenanceBlockerManager:
    """
    Manages blockers for a maintenance event.
    
    Accepts MaintenanceActionSetStruct to leverage:
    - Cached blocker list
    - Convenience properties (asset_id, status, etc.)
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
        self._maintenance_action_set_id = struct.maintenance_action_set_id
    
    @property
    def blockers(self) -> List[MaintenanceBlocker]:
        """Get blockers (uses struct's cached list)"""
        return self._struct.blockers
    
    @property
    def active_blockers(self) -> List[MaintenanceBlocker]:
        """Get active blockers (filters struct's cached list)"""
        return [b for b in self._struct.blockers if b.end_date is None]
    
    def add_blocker(
        self,
        reason: str,
        notes: Optional[str] = None,
        start_time: Optional[datetime] = None,
        billable_hours_lost: Optional[float] = None,
        priority: str = 'Medium',
        user_id: Optional[int] = None
    ) -> MaintenanceBlocker:
        """
        Add a blocker to the maintenance event.
        
        Args:
            reason: Reason for blocker
            notes: Additional notes
            start_time: Start time of blocker (defaults to now)
            billable_hours_lost: Billable hours lost
            priority: Priority level (Low, Medium, High, Critical)
            user_id: ID of user adding the blocker
            
        Returns:
            Created MaintenanceBlocker instance
        """
        blocker = MaintenanceBlocker(
            maintenance_action_set_id=self._maintenance_action_set_id,
            reason=reason,
            notes=notes,
            start_date=start_time or datetime.utcnow(),
            billable_hours=billable_hours_lost,
            priority=priority,
            created_by_id=user_id,
            updated_by_id=user_id
        )
        
        # Update maintenance action set status to Blocked
        if self._maintenance_action_set.status in ['Planned', 'In Progress']:
            self._maintenance_action_set.status = 'Blocked'
            if notes:
                self._maintenance_action_set.blocker_notes = notes
        
        db.session.add(blocker)
        db.session.commit()
        self._struct.refresh()
        
        # Add comment to event
        comment_text = f"Blocker added: {reason}"
        if notes:
            comment_text += f". Notes: {notes}"
        self._struct.add_comment(
            user_id=user_id or 0,  # Use 0 if no user_id provided (system)
            content=comment_text,
            is_human_made=bool(user_id)  # Human-made if user_id provided
        )
        
        return blocker
    
    def end_blocker(
        self,
        blocker_id: int,
        user_id: Optional[int] = None,
        blocked_status_start_date: Optional[datetime] = None,
        blocked_status_end_date: Optional[datetime] = None
    ) -> MaintenanceBlocker:
        """
        End an active blocked status.
        
        Args:
            blocker_id: ID of the blocked status to end
            user_id: ID of user ending the blocked status
            blocked_status_start_date: Optional start date to update (if provided)
            blocked_status_end_date: Optional end date to set (defaults to now if not provided)
            
        Returns:
            Updated MaintenanceBlocker instance
        """
        blocker = MaintenanceBlocker.query.get(blocker_id)
        if not blocker:
            raise ValueError(f"Blocker {blocker_id} not found")
        
        if blocker.end_date:
            # Blocker already ended
            return blocker
        
        # Update blocker start date if provided
        if blocked_status_start_date:
            blocker.start_date = blocked_status_start_date
        
        # End the blocker - use provided end date or default to now
        blocker.end_date = blocked_status_end_date if blocked_status_end_date else datetime.utcnow()
        if user_id:
            blocker.updated_by_id = user_id
        
        # Update maintenance status back to In Progress if currently Blocked
        # Check if there are other active blockers (excluding the one we're ending)
        if self._maintenance_action_set.status == 'Blocked':
            # Count active blockers excluding the one we're ending
            remaining_active = len([b for b in self.active_blockers if b.id != blocker_id])
            if remaining_active == 0:  # No more active blockers after this one ends
                self._maintenance_action_set.status = 'In Progress'
        
        db.session.commit()
        self._struct.refresh()
        
        # Add comment to event
        comment_text = "Blocker ended. Maintenance work resumed."
        self._struct.add_comment(
            user_id=user_id or 0,  # Use 0 if no user_id provided (system)
            content=comment_text,
            is_human_made=bool(user_id)  # Human-made if user_id provided
        )
        
        return blocker
    
    def update_blocker(
        self,
        blocker_id: int,
        reason: Optional[str] = None,
        notes: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        billable_hours: Optional[float] = None,
        priority: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> MaintenanceBlocker:
        """
        Update blocked status details.
        
        Args:
            blocker_id: Blocked status ID to update
            reason: Update reason
            notes: Update notes
            start_date: Update start date
            end_date: Update end date (ending blocked status)
            billable_hours: Update billable hours
            priority: Update priority
            user_id: ID of user making the update
            
        Returns:
            Updated MaintenanceBlocker instance
            
        Raises:
            ValueError: If blocked status not found or doesn't belong to this maintenance event
        """
        blocker = MaintenanceBlocker.query.get(blocker_id)
        if not blocker:
            raise ValueError(f"Blocked status {blocker_id} not found")
        
        if blocker.maintenance_action_set_id != self._maintenance_action_set_id:
            raise ValueError(f"Blocked status {blocker_id} does not belong to this maintenance event")
        
        # Update fields
        if reason is not None:
            blocker.reason = reason
        if start_date is not None:
            blocker.start_date = start_date
        if end_date is not None:
            blocker.end_date = end_date
        if billable_hours is not None:
            blocker.billable_hours = billable_hours
        if notes is not None:
            blocker.notes = notes
        if priority is not None:
            blocker.priority = priority
        if user_id:
            blocker.updated_by_id = user_id
        
        # If ending blocked status, update maintenance status
        if end_date is not None and blocker.end_date:
            if self._maintenance_action_set.status == 'Blocked':
                # Count active blockers excluding the one we're updating
                remaining_active = len([b for b in self.active_blockers if b.id != blocker_id])
                if remaining_active == 0:  # No more active blockers after this one ends
                    self._maintenance_action_set.status = 'In Progress'
        
        db.session.commit()
        self._struct.refresh()
        
        # Add comment to event if blocker was updated
        comment_parts = []
        if reason is not None:
            comment_parts.append(f"Reason: {reason}")
        if end_date is not None:
            comment_parts.append("Blocker ended")
        
        if comment_parts:
            comment_text = f"Blocker updated: {'. '.join(comment_parts)}"
            self._struct.add_comment(
                user_id=user_id or 0,  # Use 0 if no user_id provided (system)
                content=comment_text,
                is_human_made=bool(user_id)  # Human-made if user_id provided
            )
        
        return blocker
    

