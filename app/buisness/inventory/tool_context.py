"""
Tool Context
Provides a clean interface for managing tools and their related data.
"""

from typing import Union
from app.data.core.supply.tool_definition import ToolDefinition


class ToolContext:
    """
    Context manager for tool operations.
    
    Provides a clean interface for:
    - Accessing tool information
    """
    
    def __init__(self, tool: Union[ToolDefinition, int]):
        """
        Initialize ToolContext with a ToolDefinition instance or ID.
        
        Args:
            tool: ToolDefinition instance or tool ID
        """
        if isinstance(tool, int):
            self._tool = ToolDefinition.query.get_or_404(tool)
            self._tool_id = tool
        else:
            self._tool = tool
            self._tool_id = tool.id
    
    @property
    def tool(self) -> ToolDefinition:
        """Get the ToolDefinition instance"""
        return self._tool
    
    @property
    def tool_id(self) -> int:
        """Get the tool ID"""
        return self._tool_id




