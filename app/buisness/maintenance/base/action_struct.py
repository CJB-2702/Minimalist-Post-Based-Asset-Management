"""
Action Struct
Data wrapper around Action for convenient access.
Provides cached access and convenience methods - NO business logic.
"""

from typing import List, Optional, Union
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.part_demands import PartDemand
from app.data.maintenance.base.action_tools import ActionTool


class ActionStruct:
    """
    Data wrapper around Action for convenient access.
    Provides cached access and convenience methods - NO business logic.
    
    For business logic: Use ActionContext
    """
    
    def __init__(self, action: Union[Action, int]):
        """
        Initialize ActionStruct with Action instance or ID.
        
        Args:
            action: Action instance or ID
        """
        if isinstance(action, int):
            self._action = Action.query.get_or_404(action)
            self._action_id = action
        else:
            self._action = action
            self._action_id = action.id
        
        # Cache for lazy loading
        self._part_demands = None
        self._action_tools = None
    
    @property
    def action(self) -> Action:
        """Get the Action instance"""
        return self._action
    
    @property
    def action_id(self) -> int:
        """Get the action ID"""
        return self._action_id
    
    @property
    def id(self) -> int:
        """Get the action ID (alias)"""
        return self._action_id
    
    @property
    def part_demands(self) -> List[PartDemand]:
        """
        Get all part demands for this action, ordered by sequence_order.
        
        Returns:
            List of PartDemand instances
        """
        if self._part_demands is None:
            self._part_demands = sorted(
                self._action.part_demands,
                key=lambda pd: pd.sequence_order
            )
        return self._part_demands
    
    @property
    def action_tools(self) -> List[ActionTool]:
        """
        Get all action tools for this action, ordered by sequence_order.
        
        Returns:
            List of ActionTool instances
        """
        if self._action_tools is None:
            self._action_tools = sorted(
                self._action.action_tools,
                key=lambda at: at.sequence_order
            )
        return self._action_tools
    
    # Convenience properties for common fields
    @property
    def action_name(self) -> str:
        """Get the action name"""
        return self._action.action_name
    
    @property
    def description(self) -> Optional[str]:
        """Get the description"""
        return self._action.description
    
    @property
    def status(self) -> str:
        """Get the status"""
        return self._action.status
    
    @property
    def sequence_order(self) -> int:
        """Get the sequence order"""
        return self._action.sequence_order
    
    @property
    def maintenance_action_set_id(self) -> int:
        """Get the maintenance action set ID"""
        return self._action.maintenance_action_set_id
    
    @property
    def maintenance_action_set(self):
        """Get the associated MaintenanceActionSet"""
        return self._action.maintenance_action_set
    
    @property
    def template_action_item_id(self) -> Optional[int]:
        """Get the template action item ID"""
        return self._action.template_action_item_id
    
    @property
    def template_action_item(self):
        """Get the associated TemplateActionItem"""
        return self._action.template_action_item
    
    @property
    def assigned_user_id(self) -> Optional[int]:
        """Get the assigned user ID"""
        return self._action.assigned_user_id
    
    @property
    def assigned_user(self):
        """Get the assigned user"""
        return self._action.assigned_user
    
    @classmethod
    def from_id(cls, action_id: int) -> 'ActionStruct':
        """
        Create ActionStruct from ID.
        
        Args:
            action_id: Action ID
            
        Returns:
            ActionStruct instance
        """
        return cls(action_id)
    
    def refresh(self):
        """Refresh cached data from database"""
        from app import db
        db.session.refresh(self._action)
        self._part_demands = None
        self._action_tools = None
    
    def __repr__(self):
        return f'<ActionStruct id={self._action_id} action_name="{self.action_name}" status={self.status}>'

