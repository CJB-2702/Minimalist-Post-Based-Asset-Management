"""
Maintenance Context
Business logic context manager for maintenance events.
Provides management methods, statistics, and workflow management.
"""

from typing import List, Optional, Union, Dict, Any
from datetime import datetime
from app import db
from app.buisness.maintenance.base.maintenance_action_set_struct import MaintenanceActionSetStruct
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.maintenance_delays import MaintenanceDelay
from app.data.core.event_info.event import Event
from app.data.core.asset_info.meter_history import MeterHistory
from app.buisness.core.event_context import EventContext
from app.buisness.core.asset_context import AssetContext


class MaintenanceContext:
    """
    Business logic context manager for maintenance events.
    
    Wraps MaintenanceActionSetStruct (which wraps MaintenanceActionSet)
    Provides business logic, management methods, and workflow management.
    """
    
    def __init__(self, maintenance_action_set_struct:  MaintenanceActionSetStruct):
        """
        Initialize MaintenanceContext with MaintenanceActionSet, MaintenanceActionSetStruct, or Event.
        
        Args:
            maintenance_action_set_struct: MaintenanceActionSetStruct instance
        """

        self._struct = maintenance_action_set_struct
        self._event_context = None
       
        

    @classmethod
    def from_event(cls, event: Union[Event, int]) -> 'MaintenanceContext':
        """
        Create MaintenanceContext from Event instance or event_id.
        
        Args:
            event: Event instance or event_id (int)
            
        Returns:
            MaintenanceContext instance
            
        Raises:
            ValueError: If event not found or no maintenance action set exists for event
        """
        if isinstance(event, int):
            event_id = event
        else:
            event_id = event.id
        
        return cls(MaintenanceActionSetStruct.from_event_id(event_id))
    
    @classmethod
    def from_maintenance_action_set(cls, maintenance_action_set: Union[MaintenanceActionSet, int]) -> 'MaintenanceContext':
        """
        Create MaintenanceContext from MaintenanceActionSet instance or ID.
        
        Args:
            maintenance_action_set: MaintenanceActionSet instance or ID (int)
            
        Returns:
            MaintenanceContext instance
            
        Raises:
            ValueError: If maintenance action set not found
        """
        if isinstance(maintenance_action_set, int):
            struct = MaintenanceActionSetStruct.from_maintenance_action_set_id(maintenance_action_set)
        else:
            struct = MaintenanceActionSetStruct(maintenance_action_set)
        
        return cls(struct)
    
    @classmethod
    def from_maintenance_struct(cls, struct: MaintenanceActionSetStruct) -> 'MaintenanceContext':
        """
        Create MaintenanceContext from MaintenanceActionSetStruct instance.
        
        Args:
            struct: MaintenanceActionSetStruct instance
            
        Returns:
            MaintenanceContext instance
        """
        return cls(struct)
    
    @property
    def struct(self) -> MaintenanceActionSetStruct:
        """Get the underlying MaintenanceActionSetStruct"""
        return self._struct
    
    @property
    def maintenance_action_set(self) -> MaintenanceActionSet:
        """Get the MaintenanceActionSet instance"""
        return self._struct.maintenance_action_set
    
    @property
    def maintenance_action_set_id(self) -> int:
        """Get the maintenance action set ID"""
        return self.struct.maintenance_action_set_id
    
    @property
    def event_id(self) -> int:
        """Get the event ID"""
        return self.struct.event_id
    
    @property
    def event_context(self) -> EventContext:
        """Get the EventContext for the associated event"""
        if self._event_context is None and self._struct.event_id:
            self._event_context = EventContext(self._struct.event_id)
        return self._event_context
    
    def _sync_event_status(self):
        """
        Sync Event.status with MaintenanceActionSet.status.
        Maps maintenance statuses to event statuses.
        """
        if not self._struct.event_id:
            return
        
        event = Event.query.get(self._struct.event_id)
        if not event:
            return
        
        # Map maintenance status to event status
        maintenance_status = self.maintenance_action_set.status
        if maintenance_status:
            event.status = maintenance_status

    # Management methods
    def start(self, user_id: Optional[int] = None) -> 'MaintenanceContext':
        """
        Start the maintenance event.
        
        Args:
            user_id: ID of user starting the maintenance
            
        Returns:
            self for chaining
        """
        if self.maintenance_action_set.status == 'Planned':
            self.maintenance_action_set.status = 'In Progress'
            self.maintenance_action_set.start_date = datetime.utcnow()
            if user_id:
                self.maintenance_action_set.assigned_by_id = user_id
            self._sync_event_status()
            db.session.commit()
            self.refresh()
        return self
    
    def complete(
        self,
        user_id: Optional[int] = None,
        notes: Optional[str] = None,
        meter1: Optional[float] = None,
        meter2: Optional[float] = None,
        meter3: Optional[float] = None,
        meter4: Optional[float] = None
    ) -> 'MaintenanceContext':
        """
        Complete the maintenance event.
        
        Requires meter verification before completion. Meter history record is created
        and linked to the maintenance event. If meter verification fails, the entire
        transaction is rolled back (no partial state).
        
        Args:
            user_id: ID of user completing the maintenance
            notes: Completion notes
            meter1-4: Meter values (required for completion). All four must be provided
                     (can be None, but must be explicitly passed)
            
        Returns:
            self for chaining
            
        Raises:
            ValueError: If meter verification fails or meters are not provided
        """
        if self.maintenance_action_set.status in ['Planned', 'In Progress', 'Delayed']:
            # Record meters BEFORE completing (with commit=False for transaction safety)
            # This ensures meter history is created in the same transaction as completion
            # If validation fails, entire transaction is rolled back
            try:
                asset_context = AssetContext(self._struct.asset_id)
                meter_history = asset_context.update_meters(
                    meter1=meter1,
                    meter2=meter2,
                    meter3=meter3,
                    meter4=meter4,
                    updated_by_id=user_id,
                    validate=True,  # Always validate for maintenance completion
                    commit=False  # Don't commit yet - wait for full completion
                )
                
                # Link MaintenanceActionSet to MeterHistory
                self.maintenance_action_set.meter_reading_id = meter_history.id
            except ValueError as e:
                # Re-raise with context
                raise ValueError(f"Meter verification failed: {str(e)}")
            
            # Now complete the maintenance event
            self.maintenance_action_set.status = 'Complete'
            self.maintenance_action_set.end_date = datetime.utcnow()
            if user_id:
                self.maintenance_action_set.completed_by_id = user_id
                # Auto-assign if not already assigned
                if self.maintenance_action_set.assigned_user_id is None:
                    self.maintenance_action_set.assigned_user_id = user_id
                    self.maintenance_action_set.assigned_by_id = user_id
                    # Add comment about auto-assignment
                    self.add_comment(
                        user_id=user_id,
                        content=f"Auto-assigned to user (completed maintenance)",
                        is_human_made=False
                    )
            if notes:
                self.maintenance_action_set.completion_notes = notes
            self._sync_event_status()
            
            # Commit entire transaction (meter history + asset meters + maintenance event)
            # If this fails, entire transaction is rolled back (meter history, asset meters, maintenance event)
            db.session.commit()
            self.refresh()
        return self
    
    def cancel(self, user_id: Optional[int] = None, notes: Optional[str] = None) -> 'MaintenanceContext':
        """
        Cancel the maintenance event.
        
        Args:
            user_id: ID of user canceling the maintenance
            notes: Cancellation notes
            
        Returns:
            self for chaining
        """
        if self.maintenance_action_set.status in ['Planned', 'In Progress']:
            self.maintenance_action_set.status = 'Cancelled'
            self.maintenance_action_set.end_date = datetime.utcnow()
            if notes:
                self.maintenance_action_set.completion_notes = notes
            self._sync_event_status()
            db.session.commit()
            self.refresh()
        return self
    
    def add_delay(
        self,
        delay_type: str,
        delay_reason: str,
        delay_start_date: Optional[datetime] = None,
        delay_billable_hours: Optional[float] = None,
        delay_notes: Optional[str] = None,
        priority: str = 'Medium',
        user_id: Optional[int] = None
    ) -> MaintenanceDelay:
        """
        Add a delay to the maintenance event.
        
        Args:
            delay_type: Type of delay
            delay_reason: Reason for delay
            delay_start_date: Start date of delay (defaults to now)
            delay_billable_hours: Billable hours for delay
            delay_notes: Additional notes
            priority: Priority level (Low, Medium, High, Critical)
            user_id: ID of user adding the delay
            
        Returns:
            Created MaintenanceDelay instance
        """
        delay = MaintenanceDelay(
            maintenance_action_set_id=self.maintenance_action_set_id,
            delay_type=delay_type,
            delay_reason=delay_reason,
            delay_start_date=delay_start_date or datetime.utcnow(),
            delay_billable_hours=delay_billable_hours,
            delay_notes=delay_notes,
            priority=priority,
            created_by_id=user_id,
            updated_by_id=user_id
        )
        
        # Update maintenance action set status to Delayed
        if self.maintenance_action_set.status in ['Planned', 'In Progress']:
            self.maintenance_action_set.status = 'Delayed'
            if delay_notes:
                self.maintenance_action_set.delay_notes = delay_notes
            self._sync_event_status()
        
        db.session.add(delay)
        db.session.commit()
        self.refresh()
        
        return delay
    
    def end_delay(
        self, 
        delay_id: int, 
        user_id: Optional[int] = None,
        delay_start_date: Optional[datetime] = None,
        delay_end_date: Optional[datetime] = None
    ) -> 'MaintenanceContext':
        """
        End an active delay and update maintenance status back to In Progress.
        
        Args:
            delay_id: ID of the delay to end
            user_id: ID of user ending the delay
            delay_start_date: Optional start date to update (if provided)
            delay_end_date: Optional end date to set (defaults to now if not provided)
            
        Returns:
            self for chaining
        """
        delay = MaintenanceDelay.query.get(delay_id)
        if not delay:
            return self
        
        if delay.delay_end_date:
            # Delay already ended
            return self
        
        # Update delay start date if provided
        if delay_start_date:
            delay.delay_start_date = delay_start_date
        
        # End the delay - use provided end date or default to now
        delay.delay_end_date = delay_end_date if delay_end_date else datetime.utcnow()
        if user_id:
            delay.updated_by_id = user_id
        
        # Update maintenance status back to In Progress if currently Delayed
        if self.maintenance_action_set.status == 'Delayed':
            self.maintenance_action_set.status = 'In Progress'
            self._sync_event_status()
        
        db.session.commit()
        self.refresh()
        
        return self
    
    def add_comment(self, user_id: int, content: str, is_human_made: bool = False) -> 'MaintenanceContext':
        """
        Add a comment to the associated event.
        
        Args:
            user_id: ID of user adding comment
            content: Comment content
            is_human_made: Whether comment was manually inserted by a human (default: False)
            
        Returns:
            self for chaining
        """
        if self.event_context:
            self.event_context.add_comment(user_id, content, is_human_made)
        return self
    
    def assign_event(
        self,
        assigned_user_id: int,
        assigned_by_id: int,
        planned_start_datetime: Optional[datetime] = None,
        priority: Optional[str] = None,
        notes: Optional[str] = None
    ) -> 'MaintenanceContext':
        """
        Assign or reassign the maintenance event to a technician.
        
        Updates assignment fields, optional fields if provided, and adds a comment
        documenting the assignment.
        
        Args:
            assigned_user_id: User ID to assign the maintenance to
            assigned_by_id: User ID of the manager assigning the maintenance
            planned_start_datetime: Optional planned start datetime to update
            priority: Optional priority to update
            notes: Optional assignment notes to include in comment
            
        Returns:
            self for chaining
            
        Raises:
            ValueError: If technician not found or not active
        """
        from app.data.core.user_info.user import User
        
        # Validate technician
        technician = User.query.get(assigned_user_id)
        if not technician or not technician.is_active:
            raise ValueError(f"Technician {assigned_user_id} not found or not active")
        
        # Update assignment
        self.maintenance_action_set.assigned_user_id = assigned_user_id
        self.maintenance_action_set.assigned_by_id = assigned_by_id
        
        # Update optional fields
        if planned_start_datetime is not None:
            self.maintenance_action_set.planned_start_datetime = planned_start_datetime
        if priority is not None:
            self.maintenance_action_set.priority = priority
        
        # Build comment text
        comment_parts = [f"Assigned to {technician.username}"]
        if notes:
            comment_parts.append(f"Notes: {notes}")
        
        comment_text = " | ".join(comment_parts)
        self.add_comment(
            user_id=assigned_by_id,
            content=comment_text,
            is_human_made=True
        )
        
        db.session.commit()
        self.refresh()
        
        return self
    
    def update_action_status(
        self,
        action_id: int,
        user_id: int,
        username: str,
        new_status: str,
        old_status: str,
        final_comment: Optional[str] = None,
        is_human_made: bool = False,
        billable_hours: Optional[float] = None,
        completion_notes: Optional[str] = None,
        issue_part_demands: bool = False,
        duplicate_part_demands: bool = False,
        cancel_part_demands: bool = False
    ) -> 'MaintenanceContext':
        """
        Update action status by delegating to the appropriate ActionContext method.
        
        Determines which status update function to use (start, mark_complete, mark_failed, mark_skipped)
        based on the status transition, then generates a comment on behalf of the action.
        
        Args:
            action_id: ID of the action to update
            user_id: ID of user making the update
            username: Username of user making the update (for comment attribution)
            new_status: New status to set
            old_status: Current status of the action
            final_comment: Optional comment text to include
            is_human_made: Whether the comment is human-made (default: False)
            billable_hours: Optional billable hours for the action
            completion_notes: Optional completion notes
            issue_part_demands: If True, issue all part demands (for mark_complete)
            duplicate_part_demands: If True, duplicate part demands (for mark_failed)
            cancel_part_demands: If True, cancel part demands (for mark_failed or mark_skipped)
            
        Returns:
            self for chaining
            
        Raises:
            ValueError: If action not found or doesn't belong to this maintenance event
        """
        from app.buisness.maintenance.base.action_context import ActionContext
        from app import db
        
        # Find the action in this maintenance event
        action = None
        for a in self._struct.actions:
            if a.id == action_id:
                action = a
                break
        
        if not action:
            raise ValueError(f"Action {action_id} not found in this maintenance event")
        
        # Get ActionContext for the action
        action_context = ActionContext(action)
        
        # Determine which status update function to use based on status transition
        status_changed = new_status != old_status
        
        # Get action info for comments
        action_prefix = f"[Action #{action.sequence_order}: {action.action_name}]"
        
        if new_status == 'In Progress' and old_status == 'Not Started':
            # Starting the action
            action_context.start(user_id=user_id)
            comment_text = f"{action_prefix} Status changed from {old_status} to {new_status}"
            
        elif new_status == 'Complete':
            # Completing the action
            action_context.mark_complete(
                user_id=user_id,
                billable_hours=billable_hours,
                notes=completion_notes,
                issue_part_demands=issue_part_demands
            )
            comment_text = f"{action_prefix} Status changed from {old_status} to {new_status}"
            
        elif new_status == 'Failed':
            # Marking as failed
            action_context.mark_failed(
                user_id=user_id,
                billable_hours=billable_hours,
                notes=completion_notes,
                duplicate_part_demands=duplicate_part_demands,
                cancel_part_demands=cancel_part_demands
            )
            comment_text = f"{action_prefix} Status changed from {old_status} to {new_status}"
            
        elif new_status == 'Skipped':
            # Marking as skipped
            action_context.mark_skipped(
                user_id=user_id,
                notes=completion_notes,
                cancel_part_demands=cancel_part_demands
            )
            comment_text = f"{action_prefix} Status changed from {old_status} to {new_status}"
            
        else:
            # For other status changes, use edit_action
            action_context.edit_action(status=new_status, user_id=user_id)
            comment_text = f"{action_prefix} Status changed from {old_status} to {new_status}"
        

        if final_comment:
            # Enhance final_comment with action info if it doesn't already include it
            if action_prefix not in final_comment:
                comment_text = f"{action_prefix} {final_comment}"
            else:
                comment_text = final_comment
  
        
        # Generate comment on behalf of the action
        self.add_comment(
            user_id=user_id,
            content=comment_text,
            is_human_made=is_human_made
        )
        
        # Auto-assign event if not assigned (unless skipping)
        if self.maintenance_action_set.assigned_user_id is None and new_status != 'Skipped':
            self.maintenance_action_set.assigned_user_id = user_id
            self.maintenance_action_set.assigned_by_id = user_id
            # Add comment about auto-assignment
            action_prefix = f"[Action #{action.sequence_order}: {action.action_name}]"
            self.add_comment(
                user_id=user_id,
                content=f"{action_prefix} Auto-assigned to {username} (action status updated)",
                is_human_made=False
            )
        
        # Update event status to "In Progress" if currently "Planned"
        if self.maintenance_action_set.status == 'Planned':
            self.maintenance_action_set.status = 'In Progress'
            if not self.maintenance_action_set.start_date:
                self.maintenance_action_set.start_date = datetime.utcnow()
            self._sync_event_status()
        
        db.session.commit()
        
        # Auto-update MaintenanceActionSet billable hours if sum is greater
        self.update_actual_billable_hours_auto()
        
        return self
    
    def edit_action(
        self,
        action_id: int,
        user_id: int,
        username: str,
        updates: Dict[str, Any],
        old_status: Optional[str] = None
    ) -> 'MaintenanceContext':
        """
        Edit an action and handle all associated business logic.
        
        Applies updates to the action, generates comments for status changes,
        and auto-updates billable hours. This centralizes all action editing
        business logic in the maintenance context.
        
        Args:
            action_id: ID of the action to edit
            user_id: ID of user making the edit
            username: Username of user making the edit (for comment attribution)
            updates: Dictionary of field updates to apply (passed to ActionContext.edit_action)
            old_status: Previous status of the action (for generating status change comments)
            
        Returns:
            self for chaining
            
        Raises:
            ValueError: If action not found or doesn't belong to this maintenance event
        """
        from app.buisness.maintenance.base.action_context import ActionContext
        from app import db
        
        # Find the action in this maintenance event
        action = None
        for a in self._struct.actions:
            if a.id == action_id:
                action = a
                break
        
        if not action:
            raise ValueError(f"Action {action_id} not found in this maintenance event")
        
        # Get old status if not provided
        if old_status is None:
            old_status = action.status
        
        # Create ActionContext and apply updates
        # Add user_id to updates if not already present
        updates_with_user = updates.copy()
        if 'user_id' not in updates_with_user:
            updates_with_user['user_id'] = user_id
        
        action_context = ActionContext(action)
        action_context.edit_action(**updates_with_user)
        
        # Generate comment if status changed or reset
        comment_parts = []
        reset_to_in_progress = updates.get('reset_to_in_progress', False)
        new_status = updates.get('status')
        status_changed = new_status and new_status != old_status
        
        if reset_to_in_progress and old_status in ['Complete', 'Failed', 'Skipped']:
            comment_parts.append(f"Status reset from {old_status} to In Progress (for retry)")
        elif status_changed:
            comment_parts.append(f"Status changed from {old_status} to {new_status}")
        
        # Add comment if status changed
        if comment_parts:
            action_prefix = f"[Action #{action.sequence_order}: {action.action_name}]"
            comment_text = f"{action_prefix} " + ". ".join(comment_parts) + f" by {username}"
            self.add_action_comment(
                action_id=action_id,
                user_id=user_id,
                content=comment_text,
                is_human_made=True
            )
        
        # Auto-assign event if not assigned (unless skipping)
        if status_changed and self.maintenance_action_set.assigned_user_id is None and new_status != 'Skipped':
            self.maintenance_action_set.assigned_user_id = user_id
            self.maintenance_action_set.assigned_by_id = user_id
            # Add comment about auto-assignment
            action_prefix = f"[Action #{action.sequence_order}: {action.action_name}]"
            self.add_comment(
                user_id=user_id,
                content=f"{action_prefix} Auto-assigned to {username} (action status updated)",
                is_human_made=False
            )
        
        # Update event status to "In Progress" if currently "Planned" and status changed
        if status_changed and self.maintenance_action_set.status == 'Planned':
            self.maintenance_action_set.status = 'In Progress'
            if not self.maintenance_action_set.start_date:
                self.maintenance_action_set.start_date = datetime.utcnow()
            self._sync_event_status()
        
        db.session.commit()
        
        # Auto-update MaintenanceActionSet billable hours if sum is greater
        self.update_actual_billable_hours_auto()
        
        return self
    
    
    def update_actual_billable_hours_auto(self) -> bool:
        """
        Auto-update actual_billable_hours if calculated sum of all individual actions is greater than current value.
        This implements the auto-update behavior when action billable hours change.
        
        Returns:
            True if update occurred, False otherwise
        """
        # Check if the attribute exists (handles cases where DB migration hasn't run)
        if not hasattr(self.maintenance_action_set, 'actual_billable_hours'):
            return False
        
        calculated = self.calculated_billable_hours
        current = self.maintenance_action_set.actual_billable_hours or 0
        if calculated > current:
            self.maintenance_action_set.actual_billable_hours = calculated
            db.session.commit()
            self.refresh()
            return True
        return False
    
    def set_actual_billable_hours(self, manual_value: float) -> 'MaintenanceContext':
        """
        Manually set actual_billable_hours (allows override of calculated sum).
        
        Args:
            manual_value: Manual value to set (must be non-negative)
            
        Returns:
            self for chaining
            
        Raises:
            ValueError: If manual_value is negative or attribute doesn't exist
        """
        if not hasattr(self.maintenance_action_set, 'actual_billable_hours'):
            raise ValueError("actual_billable_hours field not available. Database migration may be required.")
        if manual_value < 0:
            raise ValueError("Billable hours must be non-negative")
        self.maintenance_action_set.actual_billable_hours = manual_value
        db.session.commit()
        self.refresh()
        return self
    
    def sync_actual_billable_hours_to_calculated(self) -> 'MaintenanceContext':
        """
        Reset actual_billable_hours to calculated sum.
        Used when user clicks "sync to sum" button.
        
        Returns:
            self for chaining
            
        Raises:
            ValueError: If attribute doesn't exist
        """
        if not hasattr(self.maintenance_action_set, 'actual_billable_hours'):
            raise ValueError("actual_billable_hours field not available. Database migration may be required.")
        self.maintenance_action_set.actual_billable_hours = self.calculated_billable_hours
        db.session.commit()
        self.refresh()
        return self
    
    def get_billable_hours_warning(self) -> Optional[str]:
        """
        Get warning message if actual_billable_hours is outside expected range.
        
        Warning conditions:
        - If actual < calculated (less than sum)
        - If actual > calculated * 4 (more than 4x sum)
        
        Returns:
            Warning message string or None if no warning needed
        """
        if not hasattr(self.maintenance_action_set, 'actual_billable_hours'):
            return None
        
        calculated = self.calculated_billable_hours
        actual = self.maintenance_action_set.actual_billable_hours
        
        if actual is None:
            return None
        
        if actual < calculated:
            return f"Actual billable hours ({actual:.2f}) is less than calculated sum ({calculated:.2f})"
        elif calculated > 0 and actual > calculated * 4:
            return f"Actual billable hours ({actual:.2f}) is more than 4x the calculated sum ({calculated:.2f})"
        
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize maintenance action set to dictionary.
        
        Returns:
            Dictionary representation of maintenance action set
        """
        return {
            'id': self.maintenance_action_set_id,
            'task_name': self._struct.task_name,
            'description': self._struct.description,
            'status': self._struct.status,
            'priority': self._struct.priority,
            'asset_id': self._struct.asset_id,
            'event_id': self._struct.event_id,
            'planned_start_datetime': self._struct.planned_start_datetime.isoformat() if self._struct.planned_start_datetime else None,
            'start_date': self.maintenance_action_set.start_date.isoformat() if self.maintenance_action_set.start_date else None,
            'end_date': self.maintenance_action_set.end_date.isoformat() if self.maintenance_action_set.end_date else None,
            'total_actions': self.total_actions,
            'completed_actions': self.completed_actions,
            'completion_percentage': self.completion_percentage,
            'total_part_demands': self.total_part_demands,
            'assigned_user_id': self._struct.assigned_user_id,
            'actual_billable_hours': self.actual_billable_hours,
            'calculated_billable_hours': self.calculated_billable_hours,
            'billable_hours_warning': self.get_billable_hours_warning(),
        }
    
    def update_action_set_details(
        self,
        task_name: Optional[str] = None,
        description: Optional[str] = None,
        estimated_duration: Optional[float] = None,
        asset_id: Optional[int] = None,
        maintenance_plan_id: Optional[int] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        planned_start_datetime: Optional[datetime] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        safety_review_required: Optional[bool] = None,
        staff_count: Optional[int] = None,
        labor_hours: Optional[float] = None,
        parts_cost: Optional[float] = None,
        actual_billable_hours: Optional[float] = None,
        assigned_user_id: Optional[int] = None,
        assigned_by_id: Optional[int] = None,
        completed_by_id: Optional[int] = None,
        completion_notes: Optional[str] = None,
        delay_notes: Optional[str] = None
    ) -> 'MaintenanceContext':
        """
        Update maintenance action set details.
        
        All fields are inherited from VirtualActionSet or defined in MaintenanceActionSet.
        Description is a column from VirtualActionSet and can be set directly.
        
        Args:
            task_name: Task name (from VirtualActionSet)
            description: Description (from VirtualActionSet)
            estimated_duration: Estimated duration in hours (from VirtualActionSet)
            asset_id: Asset ID (from EventDetailVirtual)
            maintenance_plan_id: Maintenance plan ID
            status: Status
            priority: Priority
            planned_start_datetime: Planned start datetime
            start_date: Actual start date
            end_date: Actual end date
            safety_review_required: Whether safety review is required (from VirtualActionSet)
            staff_count: Staff count (from VirtualActionSet)
            labor_hours: Labor hours (from VirtualActionSet)
            parts_cost: Parts cost (from VirtualActionSet)
            actual_billable_hours: Actual billable hours
            assigned_user_id: Assigned user ID
            assigned_by_id: User ID who assigned the maintenance
            completed_by_id: User ID who completed the maintenance
            completion_notes: Completion notes
            delay_notes: Delay notes
            
        Returns:
            self for chaining
        """
        # Map field names to their values and processing functions
        # Fields that need falsy-to-None conversion
        falsy_to_none_fields = {'asset_id', 'maintenance_plan_id', 'staff_count', 'labor_hours', 'parts_cost', 'actual_billable_hours', 'assigned_user_id', 'assigned_by_id', 'completed_by_id'}
        # Fields that are nullable and can be explicitly set to None (to clear them)
        nullable_fields = {'estimated_duration', 'description', 'planned_start_datetime', 'start_date', 'end_date', 'completion_notes', 'delay_notes'}
        
        field_mappings = {
            'task_name': task_name,
            'description': description,
            'estimated_duration': estimated_duration,
            'asset_id': asset_id,
            'maintenance_plan_id': maintenance_plan_id,
            'status': status,
            'priority': priority,
            'planned_start_datetime': planned_start_datetime,
            'start_date': start_date,
            'end_date': end_date,
            'safety_review_required': safety_review_required,
            'staff_count': staff_count,
            'labor_hours': labor_hours,
            'parts_cost': parts_cost,
            'actual_billable_hours': actual_billable_hours,
            'assigned_user_id': assigned_user_id,
            'assigned_by_id': assigned_by_id,
            'completed_by_id': completed_by_id,
            'completion_notes': completion_notes,
            'delay_notes': delay_notes,
        }
        
        # Iterate through mappings and set values
        # Only update fields that were explicitly provided (in field_mappings with non-None value, or nullable fields that can be None)
        for field_name, value in field_mappings.items():
            # Skip if not provided (None and not in nullable fields list)
            # For nullable fields, allow None to clear the field
            if value is not None or field_name in nullable_fields:
                # Handle fields that need falsy-to-None conversion
                final_value = (value if value else None) if field_name in falsy_to_none_fields else value
                setattr(self.maintenance_action_set, field_name, final_value)
                # Special handling for status to sync event status
                if field_name == 'status':
                    self._sync_event_status()
        
        db.session.commit()
        self.refresh()
        return self
    
    def _calculate_sequence_order(
        self,
        insert_position: str = 'end',
        after_action_id: Optional[int] = None
    ) -> int:
        """
        Calculate sequence order for new action based on insert position.
        
        Args:
            insert_position: 'end', 'beginning', or 'after'
            after_action_id: Action ID to insert after (if 'after')
            
        Returns:
            Calculated sequence_order
            
        Raises:
            ValueError: If insert_position is invalid or after_action_id not found
        """
        actions = self._struct.actions
        if not actions:
            return 1
        
        if insert_position == 'end':
            max_sequence = max([a.sequence_order for a in actions], default=0)
            return max_sequence + 1
        elif insert_position == 'beginning':
            return 1
        elif insert_position == 'after':
            if not after_action_id:
                raise ValueError("after_action_id required when insert_position is 'after'")
            
            # Find target action
            target_action = None
            for action in actions:
                if action.id == after_action_id:
                    target_action = action
                    break
            
            if not target_action:
                raise ValueError(f"Action {after_action_id} not found in maintenance event")
            
            return target_action.sequence_order + 1
        else:
            raise ValueError(f"Invalid insert_position: {insert_position}")
    
    def _renumber_actions_atomic(self) -> None:
        """
        Renumber all actions atomically to ensure no gaps or duplicates.
        Actions are sorted by current sequence_order and assigned consecutive orders starting at 1.
        """
        actions = sorted(self._struct.actions, key=lambda a: a.sequence_order)
        for idx, action in enumerate(actions, start=1):
            action.sequence_order = idx
        db.session.commit()
        self.refresh()
    
    def update_delay(
        self,
        delay_id: int,
        delay_type: Optional[str] = None,
        delay_reason: Optional[str] = None,
        delay_start_date: Optional[datetime] = None,
        delay_end_date: Optional[datetime] = None,
        delay_billable_hours: Optional[float] = None,
        delay_notes: Optional[str] = None,
        priority: Optional[str] = None
    ) -> MaintenanceDelay:
        """
        Update delay details.
        
        Args:
            delay_id: Delay ID to update
            delay_type: Update delay type
            delay_reason: Update delay reason
            delay_start_date: Update start date
            delay_end_date: Update end date (ending delay)
            delay_billable_hours: Update billable hours
            delay_notes: Update notes
            priority: Update priority
            
        Returns:
            Updated MaintenanceDelay instance
            
        Raises:
            ValueError: If delay not found or doesn't belong to this maintenance event
        """
        delay = MaintenanceDelay.query.get(delay_id)
        if not delay:
            raise ValueError(f"Delay {delay_id} not found")
        
        if delay.maintenance_action_set_id != self.maintenance_action_set_id:
            raise ValueError(f"Delay {delay_id} does not belong to this maintenance event")
        
        # Update fields
        if delay_type is not None:
            delay.delay_type = delay_type
        if delay_reason is not None:
            delay.delay_reason = delay_reason
        if delay_start_date is not None:
            delay.delay_start_date = delay_start_date
        if delay_end_date is not None:
            delay.delay_end_date = delay_end_date
        if delay_billable_hours is not None:
            delay.delay_billable_hours = delay_billable_hours
        if delay_notes is not None:
            delay.delay_notes = delay_notes
        if priority is not None:
            delay.priority = priority
        
        # If ending delay, update maintenance status
        if delay_end_date is not None and delay.delay_end_date:
            if self.maintenance_action_set.status == 'Delayed':
                self.maintenance_action_set.status = 'In Progress'
                self._sync_event_status()
        
        db.session.commit()
        self.refresh()
        
        return delay
    
    def refresh(self):
        """Refresh cached data from database"""
        self._struct.refresh()
        self._event_context = None
    

    def all_actions_in_terminal_states(self) -> bool:
        """
        Check if all actions are in terminal states (Complete, Failed, or Skipped).
        
        Returns:
            True if all actions are in terminal states, False otherwise
        """
        terminal_states = {'Complete', 'Failed', 'Skipped'}
        if self.total_actions == 0:
            return True  # No actions means all are "terminal" (vacuous truth)
        return all(action.status in terminal_states for action in self._struct.actions)



    # Statistics ================================
    @property
    def total_actions(self) -> int:
        """Get total number of actions"""
        return len(self._struct.actions)
    
    @property
    def completed_actions(self) -> int:
        """Get number of completed actions"""
        return len([a for a in self._struct.actions if a.status == 'Complete'])
    
    @property
    def completion_percentage(self) -> float:
        """Get completion percentage of actions"""
        if self.total_actions == 0:
            return 0.0
        return (self.completed_actions / self.total_actions) * 100
    
    @property
    def total_part_demands(self) -> int:
        """Get total number of part demands"""
        return len(self._struct.part_demands)
    
    @property
    def active_delays(self) -> List[MaintenanceDelay]:
        """Get active delays (those without end date)"""
        return [d for d in self._struct.delays if d.delay_end_date is None]
    

    
    # Billable Hours Management
    @property
    def calculated_billable_hours(self) -> float:
        """
        Calculate sum of all action billable hours.
        
        Returns:
            Sum of all action.billable_hours (treating None as 0)
        """
        return sum(a.billable_hours or 0 for a in self._struct.actions)
    
    @property
    def actual_billable_hours(self) -> Optional[float]:
        """
        Get actual billable hours for the maintenance event.
        
        Returns:
            Actual billable hours or None if not set or attribute doesn't exist
        """
        if not hasattr(self.maintenance_action_set, 'actual_billable_hours'):
            return None
        return self.maintenance_action_set.actual_billable_hours


    def __repr__(self):
        return f'<MaintenanceContext id={self.maintenance_action_set_id} task_name="{self._struct.task_name}" status={self._struct.status}>'

