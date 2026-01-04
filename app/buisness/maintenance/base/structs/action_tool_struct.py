"""
Action Tool Struct
Data wrapper around ActionTool for convenient access.
Provides cached access and convenience methods - NO business logic.
"""

from typing import Optional, Union
from app.data.maintenance.base.action_tools import ActionTool


class ActionToolStruct:
    """
    Data wrapper around ActionTool for convenient access.
    Provides cached access and convenience methods - NO business logic.
    """
    
    def __init__(self, action_tool: Union[ActionTool, int]):
        """
        Initialize ActionToolStruct with ActionTool instance or ID.
        
        Args:
            action_tool: ActionTool instance or ID
        """
        if isinstance(action_tool, int):
            self._action_tool = ActionTool.query.get_or_404(action_tool)
            self._action_tool_id = action_tool
        else:
            self._action_tool = action_tool
            self._action_tool_id = action_tool.id
    
    @property
    def action_tool(self) -> ActionTool:
        """Get the ActionTool instance"""
        return self._action_tool
    
    @property
    def action_tool_id(self) -> int:
        """Get the action tool ID"""
        return self._action_tool_id
    
    @property
    def id(self) -> int:
        """Get the action tool ID (alias)"""
        return self._action_tool_id
    
    # Convenience properties for common fields
    @property
    def tool_id(self) -> int:
        """Get the tool ID"""
        return self._action_tool.tool_id
    
    @property
    def tool(self):
        """Get the associated Tool"""
        return self._action_tool.tool
    
    @property
    def quantity_required(self) -> int:
        """Get the quantity required"""
        return self._action_tool.quantity_required
    
    @property
    def status(self) -> str:
        """Get the status"""
        return self._action_tool.status
    
    @property
    def priority(self) -> str:
        """Get the priority"""
        return self._action_tool.priority
    
    @property
    def action_id(self) -> int:
        """Get the action ID"""
        return self._action_tool.action_id
    
    @property
    def action(self):
        """Get the associated Action"""
        return self._action_tool.action
    
    @property
    def assigned_to_user_id(self) -> Optional[int]:
        """Get the assigned to user ID"""
        return self._action_tool.assigned_to_user_id
    
    @property
    def assigned_to_user(self):
        """Get the user the tool is assigned to"""
        return self._action_tool.assigned_to_user
    
    @property
    def assigned_by_id(self) -> Optional[int]:
        """Get the assigned by user ID"""
        return self._action_tool.assigned_by_id
    
    @property
    def assigned_by(self):
        """Get the user who assigned the tool"""
        return self._action_tool.assigned_by
    
    @classmethod
    def from_id(cls, action_tool_id: int) -> 'ActionToolStruct':
        """
        Create ActionToolStruct from ID.
        
        Args:
            action_tool_id: Action tool ID
            
        Returns:
            ActionToolStruct instance
        """
        return cls(action_tool_id)
    
    def refresh(self):
        """Refresh cached data from database"""
        from app import db
        db.session.refresh(self._action_tool)
    
    def __repr__(self):
        return f'<ActionToolStruct id={self._action_tool_id} tool_id={self.tool_id} quantity={self.quantity_required} status={self.status}>'

