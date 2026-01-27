"""
Action Context
Business logic context manager for individual actions.
Provides action lifecycle management, statistics, and completion tracking.
"""

from typing import List, Optional, Union, Dict, Any
from datetime import datetime
from app import db
from app.buisness.maintenance.base.structs.action_struct import ActionStruct
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.part_demands import PartDemand
from app.data.maintenance.base.action_tools import ActionTool


class ActionContext:
    """
    Business logic context manager for individual actions.
    
    Wraps ActionStruct (which wraps Action)
    Provides action lifecycle management, statistics, and completion tracking.
    """
    
    def __init__(self, action: Union[Action, ActionStruct, int]):
        """
        Initialize ActionContext with Action, ActionStruct, or ID.
        
        Args:
            action: Action instance, ActionStruct, or ID
        """
        if isinstance(action, ActionStruct):
            self._struct = action
        elif isinstance(action, Action):
            self._struct = ActionStruct(action)
        else:
            self._struct = ActionStruct(action)
        
        self._action_id = self._struct.action_id
    
    @property
    def struct(self) -> ActionStruct:
        """Get the underlying ActionStruct"""
        return self._struct
    
    @property
    def action(self) -> Action:
        """Get the Action instance"""
        return self._struct.action
    
    @property
    def action_id(self) -> int:
        """Get the action ID"""
        return self._action_id
    
    def _handle_user_assignment(self, user_id: Optional[int], new_status: str) -> None:
        """
        Handle user assignment and completed_by_id for status changes.
        
        Args:
            user_id: ID of user making the change (optional)
            new_status: New status being set
        """
        # If no user is assigned and a user_id is provided, assign the user
        if self.action.assigned_user_id is None and user_id is not None:
            self.action.assigned_user_id = user_id
            if self.action.assigned_by_id is None:
                self.action.assigned_by_id = user_id
        
        # For terminal conditions, set completed_by_id
        terminal_statuses = ['Complete', 'Failed', 'Skipped']
        if new_status in terminal_statuses:
            # Use provided user_id, or fall back to assigned_user_id
            completed_by = user_id if user_id is not None else self.action.assigned_user_id
            if completed_by is not None:
                self.action.completed_by_id = completed_by
    
    # Management methods
    def start(self, user_id: Optional[int] = None) -> 'ActionContext':
        """
        Start the action.
        
        Args:
            user_id: ID of user starting the action
            
        Returns:
            self for chaining
        """
        if self.action.status == 'Not Started':
            self.action.status = 'In Progress'
            self.action.start_time = datetime.utcnow()
            self._handle_user_assignment(user_id, 'In Progress')
            db.session.commit()
            self.refresh()
        return self
    
    def complete(
        self,
        user_id: Optional[int] = None,
        billable_hours: Optional[float] = None,
        notes: Optional[str] = None
    ) -> 'ActionContext':
        """
        Complete the action.
        
        Args:
            user_id: ID of user completing the action
            billable_hours: Billable hours for the action
            notes: Completion notes
            
        Returns:
            self for chaining
        """
        if self.action.status in ['Not Started', 'In Progress']:
            self.action.status = 'Complete'
            self.action.end_time = datetime.utcnow()
            if billable_hours is not None:
                self.action.billable_hours = billable_hours
            if notes:
                self.action.completion_notes = notes
            self._handle_user_assignment(user_id, 'Complete')
            db.session.commit()
            self.refresh()
        return self
    
    def assign(self, user_id: int, assigned_by_id: Optional[int] = None) -> 'ActionContext':
        """
        Assign the action to a user.
        
        Args:
            user_id: ID of user to assign to
            assigned_by_id: ID of user making the assignment (defaults to user_id)
            
        Returns:
            self for chaining
        """
        self.action.assigned_user_id = user_id
        self.action.assigned_by_id = assigned_by_id or user_id
        db.session.commit()
        self.refresh()
        return self
    
    def mark_complete(
        self,
        user_id: Optional[int] = None,
        billable_hours: Optional[float] = None,
        notes: Optional[str] = None,
        issue_part_demands: bool = True
    ) -> 'ActionContext':
        """
        Mark action as complete and optionally issue all part demands.
        
        Args:
            user_id: ID of user completing the action
            billable_hours: Billable hours for the action
            notes: Completion notes
            issue_part_demands: If True, automatically issue all non-issued part demands
            
        Returns:
            self for chaining
        """
        if self.action.status in ['Not Started', 'In Progress', 'Blocked']:
            self.action.status = 'Complete'
            self.action.end_time = datetime.utcnow()
            if billable_hours is not None:
                self.action.billable_hours = billable_hours
            if notes:
                self.action.completion_notes = notes
            
            # Issue all part demands if requested
            if issue_part_demands:
                for part_demand in self._struct.part_demands:
                    if part_demand.status != 'Issued':
                        part_demand.status = 'Issued'
            
            self._handle_user_assignment(user_id, 'Complete')
            db.session.commit()
            self.refresh()

        return self
    
    def mark_failed(
        self,
        user_id: Optional[int] = None,
        billable_hours: Optional[float] = None,
        notes: Optional[str] = None,
        duplicate_part_demands: bool = False,
        cancel_part_demands: bool = False
    ) -> 'ActionContext':
        """
        Mark action as failed with options for part demand management.
        
        Args:
            user_id: ID of user marking action as failed
            billable_hours: Billable hours for the action
            notes: Failure notes
            duplicate_part_demands: If True, create copies of all part demands (parts may have been consumed)
            cancel_part_demands: If True, cancel all non-issued part demands (task failed before start)
            
        Returns:
            self for chaining
        """
        if self.action.status in ['Not Started', 'In Progress', 'Blocked']:
            self.action.status = 'Failed'
            self.action.end_time = datetime.utcnow()
            if billable_hours is not None:
                self.action.billable_hours = billable_hours
            if notes:
                self.action.completion_notes = notes
            
            # Handle part demands based on options
            if duplicate_part_demands:
                # Create copies of all part demands for the same action
                for part_demand in self._struct.part_demands:
                    if part_demand.status != 'Issued':
                        # Create a duplicate part demand
                        duplicate = PartDemand(
                            action_id=self._action_id,
                            part_id=part_demand.part_id,
                            quantity_required=part_demand.quantity_required,
                            notes=f"Duplicated from failed action. Original: {part_demand.notes or 'N/A'}",
                            expected_cost=part_demand.expected_cost,
                            status='Pending Manager Approval',
                            priority=part_demand.priority,
                            sequence_order=part_demand.sequence_order,
                            requested_by_id=user_id,
                            created_by_id=user_id,
                            updated_by_id=user_id
                        )
                        db.session.add(duplicate)
            
            if cancel_part_demands:
                # Cancel all non-issued part demands
                for part_demand in self._struct.part_demands:
                    if part_demand.status not in ['Issued', 'Cancelled by Technician', 'Cancelled by Supply']:
                        part_demand.status = 'Cancelled by Technician'
            
            self._handle_user_assignment(user_id, 'Failed')
            db.session.commit()
            self.refresh()

        return self
    
    def mark_skipped(
        self,
        user_id: Optional[int] = None,
        notes: Optional[str] = None,
        cancel_part_demands: bool = True
    ) -> 'ActionContext':
        """
        Mark action as skipped and optionally cancel part demands.
        
        Args:
            user_id: ID of user skipping the action
            notes: Skip notes
            cancel_part_demands: If True, cancel all non-issued part demands
            
        Returns:
            self for chaining
        """
        if self.action.status in ['Not Started', 'In Progress']:
            self.action.status = 'Skipped'
            if notes:
                self.action.completion_notes = notes
            
            # Cancel part demands if requested
            if cancel_part_demands:
                for part_demand in self._struct.part_demands:
                    if part_demand.status not in ['Issued', 'Cancelled by Technician', 'Cancelled by Supply']:
                        part_demand.status = 'Cancelled by Technician'
            
            self._handle_user_assignment(user_id, 'Skipped')
            db.session.commit()
            self.refresh()
            

        return self
    
    # Statistics
    @property
    def total_part_demands(self) -> int:
        """Get total number of part demands"""
        return len(self._struct.part_demands)
    
    @property
    def total_action_tools(self) -> int:
        """Get total number of action tools"""
        return len(self._struct.action_tools)
    
    @property
    def is_complete(self) -> bool:
        """Check if action is complete"""
        return self.action.status == 'Complete'
    
    @property
    def is_in_progress(self) -> bool:
        """Check if action is in progress"""
        return self.action.status == 'In Progress'
    
    @property
    def duration(self) -> Optional[float]:
        """
        Get action duration in hours.
        
        Returns:
            Duration in hours or None if not started/completed
        """
        if self.action.start_time and self.action.end_time:
            delta = self.action.end_time - self.action.start_time
            return delta.total_seconds() / 3600
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize action to dictionary.
        
        Returns:
            Dictionary representation of action
        """
        return {
            'id': self._action_id,
            'action_name': self._struct.action_name,
            'description': self._struct.description,
            'status': self._struct.status,
            'sequence_order': self._struct.sequence_order,
            'maintenance_action_set_id': self._struct.maintenance_action_set_id,
            'template_action_item_id': self._struct.template_action_item_id,
            'start_time': self.action.start_time.isoformat() if self.action.start_time else None,
            'end_time': self.action.end_time.isoformat() if self.action.end_time else None,
            'billable_hours': self.action.billable_hours,
            'estimated_duration': self.action.estimated_duration,
            'assigned_user_id': self._struct.assigned_user_id,
            'total_part_demands': self.total_part_demands,
            'total_action_tools': self.total_action_tools,
            'is_complete': self.is_complete,
            'duration': self.duration,
        }
    
    def reorder_action(self, new_sequence_order: int) -> 'ActionContext':
        """
        Reorder this action to a new sequence position within its maintenance action set.
        Shifts other actions as needed.
        
        Args:
            new_sequence_order: New sequence order position (1-based)
            
        Returns:
            self for chaining
            
        Raises:
            ValueError: If new_sequence_order is invalid
        """
        if new_sequence_order < 1:
            raise ValueError("Sequence order must be at least 1")
        
        current_order = self.action.sequence_order
        maintenance_action_set_id = self.action.maintenance_action_set_id
        
        # Get all actions in the same maintenance action set, ordered by sequence_order
        all_actions = Action.query.filter_by(
            maintenance_action_set_id=maintenance_action_set_id
        ).order_by(Action.sequence_order).all()
        
        max_order = len(all_actions)
        if new_sequence_order > max_order:
            raise ValueError(f"Sequence order cannot exceed {max_order} (number of actions in set)")
        
        # If order hasn't changed, do nothing
        if current_order == new_sequence_order:
            return self
        
        # Remove this action from the list temporarily
        other_actions = [a for a in all_actions if a.id != self.action.id]
        
        # Reorder: shift actions up or down
        if new_sequence_order < current_order:
            # Moving earlier: shift actions from new_position to current_position-1 forward
            for action in other_actions:
                if new_sequence_order <= action.sequence_order < current_order:
                    action.sequence_order += 1
        else:
            # Moving later: shift actions from current_position+1 to new_position backward
            for action in other_actions:
                if current_order < action.sequence_order <= new_sequence_order:
                    action.sequence_order -= 1
        
        # Set new order for this action
        self.action.sequence_order = new_sequence_order
        
        db.session.commit()
        self.refresh()
        return self
    
    def edit_action(
        self,
        status: Optional[str] = None,
        scheduled_start_time: Optional[datetime] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        billable_hours: Optional[float] = None,
        completion_notes: Optional[str] = None,
        assigned_user_id: Optional[int] = None,
        action_name: Optional[str] = None,
        description: Optional[str] = None,
        estimated_duration: Optional[float] = None,
        expected_billable_hours: Optional[float] = None,
        safety_notes: Optional[str] = None,
        notes: Optional[str] = None,
        sequence_order: Optional[int] = None,
        maintenance_action_set_id: Optional[int] = None,
        reset_to_in_progress: bool = False,
        user_id: Optional[int] = None
    ) -> 'ActionContext':
        """
        Edit action with all updatable fields.
        
        Args:
            status: Action status
            scheduled_start_time: Scheduled start time
            start_time: Actual start time
            end_time: End time
            billable_hours: Billable hours
            completion_notes: Completion notes
            assigned_user_id: Assigned user ID
            action_name: Action name (from VirtualActionItem)
            description: Description (from VirtualActionItem)
            estimated_duration: Estimated duration in hours (from VirtualActionItem)
            expected_billable_hours: Expected billable hours (from VirtualActionItem)
            safety_notes: Safety notes (from VirtualActionItem)
            notes: General notes (from VirtualActionItem)
            sequence_order: New sequence order (will trigger reordering)
            maintenance_action_set_id: If provided, set to this action's maintenance_action_set_id
            reset_to_in_progress: If True, reset status to In Progress and clear end_time
            user_id: ID of user making the change (used for assignment and completed_by_id)
            
        Returns:
            self for chaining
        """
        # Handle reset to In Progress
        if reset_to_in_progress:
            terminal_states = ['Complete', 'Failed', 'Skipped']
            if self.action.status in terminal_states:
                self.action.status = 'In Progress'
                self.action.end_time = None
        
        # Update VirtualActionItem fields
        if action_name is not None:
            self.action.action_name = action_name
        if description is not None:
            self.action.description = description
        if estimated_duration is not None:
            self.action.estimated_duration = estimated_duration
        if expected_billable_hours is not None:
            self.action.expected_billable_hours = expected_billable_hours
        if safety_notes is not None:
            self.action.safety_notes = safety_notes
        if notes is not None:
            self.action.notes = notes
        
        # Update Action-specific fields
        if status is not None:
            self.action.status = status
        if scheduled_start_time is not None:
            self.action.scheduled_start_time = scheduled_start_time
        if start_time is not None:
            self.action.start_time = start_time
        if end_time is not None:
            self.action.end_time = end_time
        if billable_hours is not None:
            self.action.billable_hours = billable_hours
        if completion_notes is not None:
            self.action.completion_notes = completion_notes
        if assigned_user_id is not None:
            self.action.assigned_user_id = assigned_user_id
            if self.action.assigned_by_id is None:
                self.action.assigned_by_id = assigned_user_id
        
        # Handle user assignment and completed_by_id for status changes
        if status is not None:
            # Use user_id if provided, otherwise use assigned_user_id from the update
            effective_user_id = user_id if user_id is not None else (assigned_user_id if assigned_user_id is not None else None)
            self._handle_user_assignment(effective_user_id, status)
        
        # Handle maintenance_action_set_id (set to self if provided)
        if maintenance_action_set_id is not None:
            self.action.maintenance_action_set_id = maintenance_action_set_id
        
        # Handle sequence order reordering
        if sequence_order is not None and sequence_order != self.action.sequence_order:
            self.reorder_action(sequence_order)
        
        db.session.commit()
        self.refresh()
        
        return self
    

    def refresh(self):
        """Refresh cached data from database"""
        self._struct.refresh()
    
    def __repr__(self):
        return f'<ActionContext id={self._action_id} action_name="{self._struct.action_name}" status={self._struct.status}>'

