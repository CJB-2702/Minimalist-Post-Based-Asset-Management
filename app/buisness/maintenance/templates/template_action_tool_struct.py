"""
Template Action Tool Struct
Data wrapper around TemplateActionTool for convenient access.
Provides cached access and convenience methods - NO business logic.
"""

from typing import Optional, Union
from app.data.maintenance.templates.template_action_tools import TemplateActionTool


class TemplateActionToolStruct:
    """
    Data wrapper around TemplateActionTool for convenient access.
    Provides cached access and convenience methods - NO business logic.
    """
    
    def __init__(self, template_action_tool: Union[TemplateActionTool, int]):
        """
        Initialize TemplateActionToolStruct with TemplateActionTool instance or ID.
        
        Args:
            template_action_tool: TemplateActionTool instance or ID
        """
        if isinstance(template_action_tool, int):
            self._template_action_tool = TemplateActionTool.query.get_or_404(template_action_tool)
            self._template_action_tool_id = template_action_tool
        else:
            self._template_action_tool = template_action_tool
            self._template_action_tool_id = template_action_tool.id
    
    @property
    def template_action_tool(self) -> TemplateActionTool:
        """Get the TemplateActionTool instance"""
        return self._template_action_tool
    
    @property
    def template_action_tool_id(self) -> int:
        """Get the template action tool ID"""
        return self._template_action_tool_id
    
    @property
    def id(self) -> int:
        """Get the template action tool ID (alias)"""
        return self._template_action_tool_id
    
    # Convenience properties for common fields
    @property
    def tool_id(self) -> int:
        """Get the tool ID"""
        return self._template_action_tool.tool_id
    
    @property
    def tool(self):
        """Get the associated Tool"""
        return self._template_action_tool.tool
    
    @property
    def quantity_required(self) -> int:
        """Get the quantity required"""
        return self._template_action_tool.quantity_required
    
    @property
    def is_required(self) -> bool:
        """Get whether tool is required"""
        return self._template_action_tool.is_required
    
    @property
    def template_action_item_id(self) -> int:
        """Get the template action item ID"""
        return self._template_action_tool.template_action_item_id
    
    @property
    def template_action_item(self):
        """Get the associated TemplateActionItem"""
        return self._template_action_tool.template_action_item
    
    @classmethod
    def from_id(cls, template_action_tool_id: int) -> 'TemplateActionToolStruct':
        """
        Create TemplateActionToolStruct from ID.
        
        Args:
            template_action_tool_id: Template action tool ID
            
        Returns:
            TemplateActionToolStruct instance
        """
        return cls(template_action_tool_id)
    
    def refresh(self):
        """Refresh cached data from database"""
        from app import db
        db.session.refresh(self._template_action_tool)
    
    def __repr__(self):
        return f'<TemplateActionToolStruct id={self._template_action_tool_id} tool_id={self.tool_id} quantity={self.quantity_required}>'

