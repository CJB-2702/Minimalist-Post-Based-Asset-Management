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
from app.buisness.core.event_context import EventContext


class MaintenanceContext:
    """
    Business logic context manager for maintenance events.
    
    Wraps MaintenanceActionSetStruct (which wraps MaintenanceActionSet)
    Provides business logic, management methods, and workflow management.
    """
    
    def __init__(self, maintenance_action_set: Union[MaintenanceActionSet, MaintenanceActionSetStruct, int]):
        """
        Initialize MaintenanceContext with MaintenanceActionSet, MaintenanceActionSetStruct, or ID.
        
        Args:
            maintenance_action_set: MaintenanceActionSet instance, MaintenanceActionSetStruct, or ID
        """
        if isinstance(maintenance_action_set, MaintenanceActionSetStruct):
            self._struct = maintenance_action_set
        elif isinstance(maintenance_action_set, MaintenanceActionSet):
            self._struct = MaintenanceActionSetStruct(maintenance_action_set)
        else:
            self._struct = MaintenanceActionSetStruct(maintenance_action_set)
        
        self._maintenance_action_set_id = self._struct.maintenance_action_set_id
        self._event_context = None
    
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
        return self._maintenance_action_set_id
    
    @property
    def event_context(self) -> EventContext:
        """Get the EventContext for the associated event"""
        if self._event_context is None and self._struct.event_id:
            self._event_context = EventContext(self._struct.event_id)
        return self._event_context
    
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
            db.session.commit()
            self.refresh()
        return self
    
    def complete(self, user_id: Optional[int] = None, notes: Optional[str] = None) -> 'MaintenanceContext':
        """
        Complete the maintenance event.
        
        Args:
            user_id: ID of user completing the maintenance
            notes: Completion notes
            
        Returns:
            self for chaining
        """
        if self.maintenance_action_set.status in ['Planned', 'In Progress', 'Delayed']:
            self.maintenance_action_set.status = 'Complete'
            self.maintenance_action_set.end_date = datetime.utcnow()
            if user_id:
                self.maintenance_action_set.completed_by_id = user_id
            if notes:
                self.maintenance_action_set.completion_notes = notes
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
            maintenance_action_set_id=self._maintenance_action_set_id,
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
        
        db.session.add(delay)
        db.session.commit()
        self.refresh()
        
        return delay
    
    def add_comment(self, user_id: int, content: str, is_private: bool = False) -> 'MaintenanceContext':
        """
        Add a comment to the associated event.
        
        Args:
            user_id: ID of user adding comment
            content: Comment content
            is_private: Whether comment is private
            
        Returns:
            self for chaining
        """
        if self.event_context:
            self.event_context.add_comment(user_id, content, is_private)
        return self
    
    # Statistics
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
    
    def update_actual_billable_hours_auto(self) -> bool:
        """
        Auto-update actual_billable_hours if calculated sum is greater than current value.
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
    
    # Query methods
    @staticmethod
    def get_all() -> List['MaintenanceContext']:
        """
        Get all maintenance action sets.
        
        Returns:
            List of MaintenanceContext instances
        """
        action_sets = MaintenanceActionSet.query.all()
        return [MaintenanceContext(mas) for mas in action_sets]
    
    @staticmethod
    def get_by_status(status: str) -> List['MaintenanceContext']:
        """
        Get maintenance action sets by status.
        
        Args:
            status: Status to filter by
            
        Returns:
            List of MaintenanceContext instances
        """
        action_sets = MaintenanceActionSet.query.filter_by(status=status).all()
        return [MaintenanceContext(mas) for mas in action_sets]
    
    @staticmethod
    def get_by_asset(asset_id: int) -> List['MaintenanceContext']:
        """
        Get maintenance action sets by asset.
        
        Args:
            asset_id: Asset ID to filter by
            
        Returns:
            List of MaintenanceContext instances
        """
        action_sets = MaintenanceActionSet.query.filter_by(asset_id=asset_id).all()
        return [MaintenanceContext(mas) for mas in action_sets]
    
    @staticmethod
    def get_by_user(user_id: int, assigned: bool = True) -> List['MaintenanceContext']:
        """
        Get maintenance action sets by assigned user.
        
        Args:
            user_id: User ID to filter by
            assigned: If True, filter by assigned_user_id; if False, filter by completed_by_id
            
        Returns:
            List of MaintenanceContext instances
        """
        if assigned:
            action_sets = MaintenanceActionSet.query.filter_by(assigned_user_id=user_id).all()
        else:
            action_sets = MaintenanceActionSet.query.filter_by(completed_by_id=user_id).all()
        return [MaintenanceContext(mas) for mas in action_sets]
    
    @staticmethod
    def get_by_event_id(event_id: int) -> Optional['MaintenanceContext']:
        """
        Get maintenance action set by event ID.
        Since there's only one MaintenanceActionSet per Event (ONE-TO-ONE), returns single instance.
        
        Args:
            event_id: Event ID
            
        Returns:
            MaintenanceContext instance or None if not found
        """
        struct = MaintenanceActionSetStruct.from_event_id(event_id)
        if struct:
            return MaintenanceContext(struct)
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize maintenance action set to dictionary.
        
        Returns:
            Dictionary representation of maintenance action set
        """
        return {
            'id': self._maintenance_action_set_id,
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
        safety_review_required: Optional[bool] = None,
        staff_count: Optional[int] = None,
        labor_hours: Optional[float] = None,
        completion_notes: Optional[str] = None
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
            safety_review_required: Whether safety review is required (from VirtualActionSet)
            staff_count: Staff count (from VirtualActionSet)
            labor_hours: Labor hours (from VirtualActionSet)
            completion_notes: Completion notes
            
        Returns:
            self for chaining
        """
        if task_name is not None:
            self.maintenance_action_set.task_name = task_name
        if description is not None:
            self.maintenance_action_set.description = description
        if estimated_duration is not None:
            self.maintenance_action_set.estimated_duration = estimated_duration
        if asset_id is not None:
            self.maintenance_action_set.asset_id = asset_id if asset_id else None
        if maintenance_plan_id is not None:
            self.maintenance_action_set.maintenance_plan_id = maintenance_plan_id if maintenance_plan_id else None
        if status is not None:
            self.maintenance_action_set.status = status
        if priority is not None:
            self.maintenance_action_set.priority = priority
        if planned_start_datetime is not None:
            self.maintenance_action_set.planned_start_datetime = planned_start_datetime
        if safety_review_required is not None:
            self.maintenance_action_set.safety_review_required = safety_review_required
        if staff_count is not None:
            self.maintenance_action_set.staff_count = staff_count if staff_count else None
        if labor_hours is not None:
            self.maintenance_action_set.labor_hours = labor_hours if labor_hours else None
        if completion_notes is not None:
            self.maintenance_action_set.completion_notes = completion_notes
        
        db.session.commit()
        self.refresh()
        return self
    
    def refresh(self):
        """Refresh cached data from database"""
        self._struct.refresh()
        self._event_context = None
    
    def __repr__(self):
        return f'<MaintenanceContext id={self._maintenance_action_set_id} task_name="{self._struct.task_name}" status={self._struct.status}>'

