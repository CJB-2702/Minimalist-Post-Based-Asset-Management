"""
Maintenance Context
Business logic context manager for maintenance events.
Provides management methods, statistics, and workflow management.
"""

from typing import Optional, Union, Dict, Any
from datetime import datetime
from app import db
from app.buisness.maintenance.base.structs.maintenance_action_set_struct import MaintenanceActionSetStruct
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.core.event_info.event import Event
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
        
        # Lazy-initialized managers (all use the same struct)
        self._blocker_manager = None
        self._limitation_manager = None
        self._billable_hours_manager = None
        self._assignment_manager = None
        self._action_orchestrator = None
        self._action_creation_manager = None
        self._blocker_creation_manager = None

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
        if self.maintenance_action_set.status in ['Planned', 'In Progress', 'Blocked']:
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
                        content="Auto-assigned to user (completed maintenance)",
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
    
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize maintenance action set to dictionary.
        
        Returns:
            Dictionary representation of maintenance action set
        """
        billable_hours_manager = self.get_billable_hours_manager()
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
            'actual_billable_hours': billable_hours_manager.actual_hours,
            'calculated_billable_hours': billable_hours_manager.calculated_hours,
            'billable_hours_warning': billable_hours_manager.get_warning(),
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
        blocker_notes: Optional[str] = None
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
            blocker_notes: blocker notes
            
        Returns:
            self for chaining
        """
        # Map field names to their values and processing functions
        # Fields that need falsy-to-None conversion
        falsy_to_none_fields = {'asset_id', 'maintenance_plan_id', 'staff_count', 'labor_hours', 'parts_cost', 'actual_billable_hours', 'assigned_user_id', 'assigned_by_id', 'completed_by_id'}
        # Fields that are nullable and can be explicitly set to None (to clear them)
        nullable_fields = {'estimated_duration', 'description', 'planned_start_datetime', 'start_date', 'end_date', 'completion_notes', 'blocker_notes'}
        
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
            'blocker_notes': blocker_notes,
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
    
    def get_blocker_manager(self):
        """Get MaintenanceBlockerManager (lazy initialization)"""
        if self._blocker_manager is None:
            from app.buisness.maintenance.base.capablities_and_blockers.maintenance_blocker_manager import MaintenanceBlockerManager
            self._blocker_manager = MaintenanceBlockerManager(self._struct)
        return self._blocker_manager
    
    def get_limitation_manager(self):
        """Get AssetLimitationManager (lazy initialization)"""
        if self._limitation_manager is None:
            from app.buisness.maintenance.base.capablities_and_blockers.asset_limitation_manager import AssetLimitationManager
            self._limitation_manager = AssetLimitationManager(self.maintenance_action_set_id)
        return self._limitation_manager
    
    def get_billable_hours_manager(self):
        """Get BillableHoursManager (lazy initialization)"""
        if self._billable_hours_manager is None:
            from app.buisness.maintenance.base.billable_hours_manager import BillableHoursManager
            self._billable_hours_manager = BillableHoursManager(self._struct)
        return self._billable_hours_manager
    
    def get_assignment_manager(self):
        """Get MaintenanceAssignmentManager (lazy initialization)"""
        if self._assignment_manager is None:
            from app.buisness.maintenance.base.maintenance_assignment_manager import MaintenanceAssignmentManager
            self._assignment_manager = MaintenanceAssignmentManager(self._struct)
        return self._assignment_manager
    
    def get_action_orchestrator(self):
        """Get MaintenanceActionOrchestrator (lazy initialization)"""
        if self._action_orchestrator is None:
            from app.buisness.maintenance.base.action_managment.maintenance_action_orchestrator import MaintenanceActionOrchestrator
            self._action_orchestrator = MaintenanceActionOrchestrator(self._struct)
        return self._action_orchestrator

    def get_action_creation_manager(self):
        """Get MaintenanceActionCreationManager (lazy initialization)"""
        if self._action_creation_manager is None:
            from app.buisness.maintenance.base.action_managment.maintenance_action_creation_manager import MaintenanceActionCreationManager
            self._action_creation_manager = MaintenanceActionCreationManager(self)
        return self._action_creation_manager

    def get_blocker_creation_manager(self):
        """Get MaintenanceBlockerCreationManager (lazy initialization)"""
        if self._blocker_creation_manager is None:
            from app.buisness.maintenance.base.capablities_and_blockers.maintenance_blocker_creation_manager import MaintenanceBlockerCreationManager
            self._blocker_creation_manager = MaintenanceBlockerCreationManager(self)
        return self._blocker_creation_manager
    
    
    def refresh(self):
        """Refresh cached data from database"""
        self._struct.refresh()
        self._event_context = None
        # Managers will use refreshed struct data on next access
        # No need to recreate managers - they reference the struct
    

    # Properties (Statistics and Cached Data) ================================
    
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


    def __repr__(self):
        return f'<MaintenanceContext id={self.maintenance_action_set_id} task_name="{self._struct.task_name}" status={self._struct.status}>'

