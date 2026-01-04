"""
Maintenance Action Set Struct
Data wrapper around MaintenanceActionSet for convenient access.
Provides cached access and convenience methods - NO business logic.
"""

from typing import List, Optional, Union, Dict, Any
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.part_demands import PartDemand
from app.data.maintenance.base.action_tools import ActionTool
from app.data.maintenance.base.maintenance_blockers import MaintenanceBlocker
from app.data.core.event_info.event import Event


class MaintenanceActionSetStruct:
    """
    Data wrapper around MaintenanceActionSet for convenient access.
    Provides cached access and convenience methods - NO business logic.
    
    For business logic: Use MaintenanceContext
    """
    
    def __init__(self, maintenance_action_set: MaintenanceActionSet):
        """
        Initialize MaintenanceActionSetStruct with MaintenanceActionSet instance or ID.
        
        Args:
            maintenance_action_set: MaintenanceActionSet instance or ID
        """
        if isinstance(maintenance_action_set, int):
            raise ValueError("MaintenanceActionSetStruct does not accept int as an argument")
        
        self._maintenance_action_set = maintenance_action_set
        self._maintenance_action_set_id = maintenance_action_set.id
        
        # Cache for lazy loading
        self._actions = None
        self._part_demands = None
        self._action_tools = None
        self._blockers = None
        self._event = None
        
    @classmethod
    def from_maintenance_action_set_id(cls, maintenance_action_set_id: int) -> 'MaintenanceActionSetStruct':
        """
        Create MaintenanceActionSetStruct from ID.
        
        Args:
            maintenance_action_set_id: Maintenance action set ID
            
        Returns:
            MaintenanceActionSetStruct instance
        """

        maintenance_action_set = MaintenanceActionSet.query.get_or_404(maintenance_action_set_id)
        if not maintenance_action_set:
            raise ValueError(f"Maintenance action set with id {maintenance_action_set_id} not found")
        return cls(maintenance_action_set)
    
    @classmethod
    def from_event_id(cls, event_id: int) -> Optional['MaintenanceActionSetStruct']:
        """
        Create MaintenanceActionSetStruct from event ID.
        Since there's only one MaintenanceActionSet per Event (ONE-TO-ONE), returns the single instance.
        
        Args:
            event_id: Event ID
            
        Returns:
            MaintenanceActionSetStruct instance or None if not found
        """
        maintenance_action_set = MaintenanceActionSet.query.filter_by(event_id=event_id).first()
        if maintenance_action_set:
            return cls(maintenance_action_set)
        return None
    
    
    @property
    def maintenance_action_set(self) -> MaintenanceActionSet:
        """Get the MaintenanceActionSet instance"""
        return self._maintenance_action_set
    
    @property
    def maintenance_action_set_id(self) -> int:
        """Get the maintenance action set ID"""
        return self._maintenance_action_set_id
    
    @property
    def id(self) -> int:
        """Get the maintenance action set ID (alias)"""
        return self._maintenance_action_set_id
    
    @property
    def event(self) -> Optional[Event]:
        """Get the associated Event"""
        if self._event is None:
            self._event = self._maintenance_action_set.event
        return self._event
    
    @property
    def event_id(self) -> Optional[int]:
        """Get the event ID"""
        return self._maintenance_action_set.event_id
    
    @property
    def actions(self) -> List[Action]:
        """
        Get all actions for this maintenance action set, ordered by sequence_order.
        
        Returns:
            List of Action instances
        """
        if self._actions is None:
            self._actions = sorted(
                self._maintenance_action_set.actions,
                key=lambda a: a.sequence_order
            )
        return self._actions
    
    @property
    def part_demands(self) -> List[PartDemand]:
        """
        Get all part demands for actions in this maintenance action set.
        
        Returns:
            List of PartDemand instances
        """
        if self._part_demands is None:
            self._part_demands = []
            for action in self.actions:
                self._part_demands.extend(action.part_demands)
        return self._part_demands
    
    @property
    def action_tools(self) -> List[ActionTool]:
        """
        Get all action tools for actions in this maintenance action set.
        
        Returns:
            List of ActionTool instances
        """
        if self._action_tools is None:
            self._action_tools = []
            for action in self.actions:
                self._action_tools.extend(action.action_tools)
        return self._action_tools
    
    @property
    def blockers(self) -> List[MaintenanceBlocker]:
        """
        Get all blockers for this maintenance action set.
        
        Returns:
            List of MaintenanceBlocker instances
        """
        if self._blockers is None:
            self._blockers = list(self._maintenance_action_set.blockers)
        return self._blockers
    
    # Convenience properties for common fields
    @property
    def task_name(self) -> str:
        """Get the task name"""
        return self._maintenance_action_set.task_name
    
    @property
    def description(self) -> Optional[str]:
        """Get the description"""
        return self._maintenance_action_set.description
    
    @property
    def status(self) -> str:
        """Get the status"""
        return self._maintenance_action_set.status
    
    @property
    def priority(self) -> str:
        """Get the priority"""
        return self._maintenance_action_set.priority
    
    @property
    def asset_id(self) -> Optional[int]:
        """Get the asset ID"""
        return self._maintenance_action_set.asset_id
    
    @property
    def asset(self):
        """Get the associated Asset"""
        return self._maintenance_action_set.asset
    
    @property
    def planned_start_datetime(self):
        """Get the planned start datetime"""
        return self._maintenance_action_set.planned_start_datetime
    
    @property
    def template_action_set_id(self) -> Optional[int]:
        """Get the template action set ID"""
        return self._maintenance_action_set.template_action_set_id
    
    @property
    def template_action_set(self):
        """Get the associated TemplateActionSet"""
        return self._maintenance_action_set.template_action_set
    
    @property
    def assigned_user_id(self) -> Optional[int]:
        """Get the assigned user ID"""
        return self._maintenance_action_set.assigned_user_id
    
    @property
    def assigned_user(self):
        """Get the assigned user"""
        return self._maintenance_action_set.assigned_user

    def add_comment(
        self,
        user_id: int,
        content: str,
        is_human_made: bool = False
    ):
        """
        Add a comment to the associated event.
        
        Delegates to EventContext.add_comment() for business logic.
        This is a convenience method that allows managers to add comments
        without needing direct access to EventContext.
        
        Args:
            user_id: ID of user adding comment
            content: Comment content
            is_human_made: Whether comment was manually inserted by a human (default: False)
            
        Returns:
            Created Comment instance or None if no event_id
        """
        if not self.event_id:
            return None
        
        from app.buisness.core.event_context import EventContext
        event_context = EventContext(self.event_id)
        return event_context.add_comment(user_id, content, is_human_made)

    def refresh(self):
        """Refresh cached data from database"""
        from app import db
        db.session.refresh(self._maintenance_action_set)
        self._actions = None
        self._part_demands = None
        self._action_tools = None
        self._blockers = None
        self._event = None
    
    def __repr__(self):
        return f'<MaintenanceActionSetStruct id={self._maintenance_action_set_id} task_name="{self.task_name}" status={self.status}>'

