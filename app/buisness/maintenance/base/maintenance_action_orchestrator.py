"""
Maintenance Action Orchestrator
Coordinates action status changes with maintenance event state.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from app import db
from app.buisness.maintenance.base.structs.maintenance_action_set_struct import MaintenanceActionSetStruct
from app.buisness.maintenance.base.action_context import ActionContext
from app.data.maintenance.base.actions import Action


class MaintenanceActionOrchestrator:
    """
    Orchestrates action status changes and coordinates with maintenance event.
    
    Accepts MaintenanceActionSetStruct to leverage:
    - Cached actions list
    - Convenience properties
    - Consistent data access patterns
    
    NOTE: This orchestrator deliberately uses the anti-pattern of calling
    other managers directly (e.g., MaintenanceAssignmentManager) for
    incremental refactoring. This will be refactored later to coordinate
    through MaintenanceContext.
    """
    
    def __init__(self, struct: MaintenanceActionSetStruct):
        """
        Initialize with MaintenanceActionSetStruct.
        
        Args:
            struct: MaintenanceActionSetStruct containing actions and maintenance data
        """
        self._struct = struct
        self._maintenance_action_set = struct.maintenance_action_set
    
    def find_action(self, action_id: int) -> Optional[Action]:
        """Find action in struct's cached actions list"""
        for action in self._struct.actions:
            if action.id == action_id:
                return action
        return None
    
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
    ) -> str:
        """
        Update action status by delegating to ActionContext and coordinating with maintenance event.
        
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
            Comment text to add to event
            
        Raises:
            ValueError: If action not found or doesn't belong to this maintenance event
        """
        # Find the action in this maintenance event
        action = self.find_action(action_id)
        if not action:
            raise ValueError(f"Action {action_id} not found in this maintenance event")
        
        # Get ActionContext for the action
        action_context = ActionContext(action)
        
        # Get action info for comments
        action_prefix = f"[Action #{action.sequence_order}: {action.action_name}]"
        
        # Determine which status update function to use based on status transition
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
        
        # Auto-assign event if not assigned (unless skipping)
        # DELIBERATE ANTI-PATTERN: Calling manager directly
        if self._maintenance_action_set.assigned_user_id is None and new_status != 'Skipped':
            from app.buisness.maintenance.base.maintenance_assignment_manager import MaintenanceAssignmentManager
            assignment_manager = MaintenanceAssignmentManager(self._struct)
            if assignment_manager.auto_assign(user_id, f"Auto-assigned to {username} (action status updated)"):
                comment_text += f" | {action_prefix} Auto-assigned to {username} (action status updated)"
        
        # Update event status to "In Progress" if currently "Planned"
        if self._maintenance_action_set.status == 'Planned':
            self._maintenance_action_set.status = 'In Progress'
            if not self._maintenance_action_set.start_date:
                self._maintenance_action_set.start_date = datetime.utcnow()
        
        # Auto-update billable hours if sum is greater
        # DELIBERATE ANTI-PATTERN: Calling manager directly
        from app.buisness.maintenance.base.billable_hours_manager import BillableHoursManager
        billable_hours_manager = BillableHoursManager(self._struct)
        billable_hours_manager.auto_update_if_greater()
        
        # Add comment to event BEFORE commit (so it's in the same transaction)
        if comment_text:
            comment_parts = comment_text.split(' | ')
            for part in comment_parts:
                if part.strip():
                    self._struct.add_comment(
                        user_id=user_id,
                        content=part.strip(),
                        is_human_made=is_human_made
                    )
        
        db.session.commit()
        self._struct.refresh()
        
        return comment_text
    
    def edit_action(
        self,
        action_id: int,
        user_id: int,
        username: str,
        updates: Dict[str, Any],
        old_status: Optional[str] = None
    ) -> str:
        """
        Edit an action and handle all associated business logic.
        
        Applies updates to the action, generates comments for status changes,
        and auto-updates billable hours.
        
        Args:
            action_id: ID of the action to edit
            user_id: ID of user making the edit
            username: Username of user making the edit (for comment attribution)
            updates: Dictionary of field updates to apply (passed to ActionContext.edit_action)
            old_status: Previous status of the action (for generating status change comments)
            
        Returns:
            Comment text to add to event
            
        Raises:
            ValueError: If action not found or doesn't belong to this maintenance event
        """
        # Find the action in this maintenance event
        action = self.find_action(action_id)
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
        comment_text = ""
        if comment_parts:
            action_prefix = f"[Action #{action.sequence_order}: {action.action_name}]"
            comment_text = f"{action_prefix} " + ". ".join(comment_parts) + f" by {username}"
        
        # Auto-assign event if not assigned (unless skipping)
        # DELIBERATE ANTI-PATTERN: Calling manager directly
        if status_changed and self._maintenance_action_set.assigned_user_id is None and new_status != 'Skipped':
            from app.buisness.maintenance.base.maintenance_assignment_manager import MaintenanceAssignmentManager
            assignment_manager = MaintenanceAssignmentManager(self._struct)
            if assignment_manager.auto_assign(user_id, f"Auto-assigned to {username} (action status updated)"):
                action_prefix = f"[Action #{action.sequence_order}: {action.action_name}]"
                comment_text += f" | {action_prefix} Auto-assigned to {username} (action status updated)"
        
        # Update event status to "In Progress" if currently "Planned" and status changed
        if status_changed and self._maintenance_action_set.status == 'Planned':
            self._maintenance_action_set.status = 'In Progress'
            if not self._maintenance_action_set.start_date:
                self._maintenance_action_set.start_date = datetime.utcnow()
        
        # Auto-update billable hours if sum is greater
        # DELIBERATE ANTI-PATTERN: Calling manager directly
        from app.buisness.maintenance.base.billable_hours_manager import BillableHoursManager
        billable_hours_manager = BillableHoursManager(self._struct)
        billable_hours_manager.auto_update_if_greater()
        
        # Add comment to event BEFORE commit (so it's in the same transaction)
        if comment_text:
            comment_parts = comment_text.split(' | ')
            for part in comment_parts:
                if part.strip():
                    self._struct.add_comment(
                        user_id=user_id,
                        content=part.strip(),
                        is_human_made=True  # User-initiated action edit
                    )
        
        db.session.commit()
        self._struct.refresh()
        
        return comment_text

