"""
Template Action Item Struct
Data wrapper around TemplateActionItem for convenient access.
Provides cached access and convenience methods - NO business logic.
"""

from typing import List, Optional, Union
from app.data.maintenance.templates.template_actions import TemplateActionItem
from app.data.maintenance.templates.template_part_demands import TemplatePartDemand
from app.data.maintenance.templates.template_action_tools import TemplateActionTool
from app.data.maintenance.templates.template_action_attachments import TemplateActionAttachment


class TemplateActionItemStruct:
    """
    Data wrapper around TemplateActionItem for convenient access.
    Provides cached access and convenience methods - NO business logic.
    
    For business logic: Use TemplateActionContext
    """
    
    def __init__(self, template_action_item: Union[TemplateActionItem, int]):
        """
        Initialize TemplateActionItemStruct with TemplateActionItem instance or ID.
        
        Args:
            template_action_item: TemplateActionItem instance or ID
        """
        if isinstance(template_action_item, int):
            self._template_action_item = TemplateActionItem.query.get_or_404(template_action_item)
            self._template_action_item_id = template_action_item
        else:
            self._template_action_item = template_action_item
            self._template_action_item_id = template_action_item.id
        
        # Cache for lazy loading
        self._template_part_demands = None
        self._template_action_tools = None
        self._template_action_attachments = None
    
    @property
    def template_action_item(self) -> TemplateActionItem:
        """Get the TemplateActionItem instance"""
        return self._template_action_item
    
    @property
    def template_action_item_id(self) -> int:
        """Get the template action item ID"""
        return self._template_action_item_id
    
    @property
    def id(self) -> int:
        """Get the template action item ID (alias)"""
        return self._template_action_item_id
    
    @property
    def template_part_demands(self) -> List[TemplatePartDemand]:
        """
        Get all template part demands for this template action item, ordered by sequence_order.
        
        Returns:
            List of TemplatePartDemand instances
        """
        if self._template_part_demands is None:
            self._template_part_demands = sorted(
                self._template_action_item.template_part_demands,
                key=lambda tpd: tpd.sequence_order
            )
        return self._template_part_demands
    
    @property
    def template_action_tools(self) -> List[TemplateActionTool]:
        """
        Get all template action tools for this template action item, ordered by sequence_order.
        
        Returns:
            List of TemplateActionTool instances
        """
        if self._template_action_tools is None:
            self._template_action_tools = sorted(
                self._template_action_item.template_action_tools,
                key=lambda tat: tat.sequence_order
            )
        return self._template_action_tools
    
    @property
    def template_action_attachments(self) -> List[TemplateActionAttachment]:
        """
        Get all template action attachments for this template action item, ordered by sequence_order.
        
        Returns:
            List of TemplateActionAttachment instances
        """
        if self._template_action_attachments is None:
            self._template_action_attachments = sorted(
                self._template_action_item.template_action_attachments,
                key=lambda att: att.sequence_order
            )
        return self._template_action_attachments
    
    # Convenience properties for common fields
    @property
    def action_name(self) -> str:
        """Get the action name"""
        return self._template_action_item.action_name
    
    @property
    def description(self) -> Optional[str]:
        """Get the description"""
        return self._template_action_item.description
    
    @property
    def sequence_order(self) -> int:
        """Get the sequence order"""
        return self._template_action_item.sequence_order
    
    @property
    def template_action_set_id(self) -> int:
        """Get the template action set ID"""
        return self._template_action_item.template_action_set_id
    
    @property
    def template_action_set(self):
        """Get the associated TemplateActionSet"""
        return self._template_action_item.template_action_set
    
    @property
    def proto_action_item_id(self) -> Optional[int]:
        """Get the proto action item ID"""
        return self._template_action_item.proto_action_item_id
    
    @property
    def proto_action_item(self):
        """Get the associated ProtoActionItem"""
        return self._template_action_item.proto_action_item
    
    @property
    def is_required(self) -> bool:
        """Get whether action is required"""
        return self._template_action_item.is_required
    
    @property
    def revision(self) -> Optional[str]:
        """Get the revision"""
        return self._template_action_item.revision
    
    @classmethod
    def from_id(cls, template_action_item_id: int) -> 'TemplateActionItemStruct':
        """
        Create TemplateActionItemStruct from ID.
        
        Args:
            template_action_item_id: Template action item ID
            
        Returns:
            TemplateActionItemStruct instance
        """
        return cls(template_action_item_id)
    
    def refresh(self):
        """Refresh cached data from database"""
        from app import db
        db.session.refresh(self._template_action_item)
        self._template_part_demands = None
        self._template_action_tools = None
        self._template_action_attachments = None
    
    def __repr__(self):
        return f'<TemplateActionItemStruct id={self._template_action_item_id} action_name="{self.action_name}" sequence_order={self.sequence_order}>'

