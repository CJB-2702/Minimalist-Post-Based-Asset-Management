"""
Tool Context
Provides a clean interface for managing tools and their related data.
Handles complexity of Tool vs IssuableTool distinction.
"""

from typing import Optional, Union
from app import db
from app.data.core.supply.tool import Tool
from app.data.core.supply.issuable_tool import IssuableTool
from app.data.core.user_info.user import User


class ToolContext:
    """
    Context manager for tool operations.
    
    Provides a clean interface for:
    - Accessing tool, issuable tool, assigned user
    - Handling Tool vs IssuableTool abstraction
    """
    
    def __init__(self, tool: Union[Tool, int]):
        """
        Initialize ToolContext with a Tool instance or ID.
        
        Args:
            tool: Tool instance or tool ID
        """
        if isinstance(tool, int):
            self._tool = Tool.query.get_or_404(tool)
            self._tool_id = tool
        else:
            self._tool = tool
            self._tool_id = tool.id
        
        # Check if this is an IssuableTool
        self._issuable_tool = None
        self._is_issuable = None
    
    @property
    def tool(self) -> Tool:
        """Get the Tool instance"""
        return self._tool
    
    @property
    def tool_id(self) -> int:
        """Get the tool ID"""
        return self._tool_id
    
    @property
    def issuable_tool(self) -> Optional[IssuableTool]:
        """Get the IssuableTool instance if this tool is issuable"""
        if self._issuable_tool is None:
            self._issuable_tool = IssuableTool.query.get(self._tool_id)
        return self._issuable_tool
    
    @property
    def is_issuable(self) -> bool:
        """Check if this tool is an IssuableTool"""
        if self._is_issuable is None:
            self._is_issuable = self.issuable_tool is not None
        return self._is_issuable
    
    @property
    def assigned_to(self) -> Optional[User]:
        """Get the user this tool is assigned to (if issuable and assigned)"""
        if self.is_issuable and self.issuable_tool:
            return self.issuable_tool.assigned_to
        return None
    
    @property
    def status(self) -> Optional[str]:
        """Get the tool status (from IssuableTool if available)"""
        if self.is_issuable and self.issuable_tool:
            return self.issuable_tool.status
        return None
    
    @property
    def serial_number(self) -> Optional[str]:
        """Get the serial number (from IssuableTool if available)"""
        if self.is_issuable and self.issuable_tool:
            return self.issuable_tool.serial_number
        return None
    
    @property
    def location(self) -> Optional[str]:
        """Get the location (from IssuableTool if available)"""
        if self.is_issuable and self.issuable_tool:
            return self.issuable_tool.location
        return None
    
    @property
    def next_calibration_date(self) -> Optional:
        """Get the next calibration date (from IssuableTool if available)"""
        if self.is_issuable and self.issuable_tool:
            return self.issuable_tool.next_calibration_date
        return None
    
    @property
    def last_calibration_date(self) -> Optional:
        """Get the last calibration date (from IssuableTool if available)"""
        if self.is_issuable and self.issuable_tool:
            return self.issuable_tool.last_calibration_date
        return None




