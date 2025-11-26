"""
Template Action Context
Business logic context manager for template action items.
Provides template action management and statistics.
"""

from typing import List, Optional, Union, Dict, Any
from app import db
from app.buisness.maintenance.templates.template_action_item_struct import TemplateActionItemStruct
from app.data.maintenance.templates.template_actions import TemplateActionItem


class TemplateActionContext:
    """
    Business logic context manager for template action items.
    
    Wraps TemplateActionItemStruct (which wraps TemplateActionItem)
    Provides template action management and statistics.
    """
    
    def __init__(self, template_action_item: Union[TemplateActionItem, TemplateActionItemStruct, int]):
        """
        Initialize TemplateActionContext with TemplateActionItem, TemplateActionItemStruct, or ID.
        
        Args:
            template_action_item: TemplateActionItem instance, TemplateActionItemStruct, or ID
        """
        if isinstance(template_action_item, TemplateActionItemStruct):
            self._struct = template_action_item
        elif isinstance(template_action_item, TemplateActionItem):
            self._struct = TemplateActionItemStruct(template_action_item)
        else:
            self._struct = TemplateActionItemStruct(template_action_item)
        
        self._template_action_item_id = self._struct.template_action_item_id
    
    @property
    def struct(self) -> TemplateActionItemStruct:
        """Get the underlying TemplateActionItemStruct"""
        return self._struct
    
    @property
    def template_action_item(self) -> TemplateActionItem:
        """Get the TemplateActionItem instance"""
        return self._struct.template_action_item
    
    @property
    def template_action_item_id(self) -> int:
        """Get the template action item ID"""
        return self._template_action_item_id
    
    # Statistics
    @property
    def total_part_demands(self) -> int:
        """Get total number of template part demands"""
        return len(self._struct.template_part_demands)
    
    @property
    def total_action_tools(self) -> int:
        """Get total number of template action tools"""
        return len(self._struct.template_action_tools)
    
    @property
    def total_attachments(self) -> int:
        """Get total number of template action attachments"""
        return len(self._struct.template_action_attachments)
    
    # Query methods
    @staticmethod
    def get_by_template_action_set(template_action_set_id: int) -> List['TemplateActionContext']:
        """
        Get all template action items for a template action set.
        
        Args:
            template_action_set_id: Template action set ID
            
        Returns:
            List of TemplateActionContext instances, ordered by sequence_order
        """
        action_items = TemplateActionItem.query.filter_by(
            template_action_set_id=template_action_set_id
        ).order_by(TemplateActionItem.sequence_order).all()
        return [TemplateActionContext(ai) for ai in action_items]
    
    @staticmethod
    def get_by_proto_action_item(proto_action_item_id: int) -> List['TemplateActionContext']:
        """
        Get all template action items that reference a proto action item.
        
        Args:
            proto_action_item_id: Proto action item ID
            
        Returns:
            List of TemplateActionContext instances
        """
        action_items = TemplateActionItem.query.filter_by(
            proto_action_item_id=proto_action_item_id
        ).all()
        return [TemplateActionContext(ai) for ai in action_items]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize template action item to dictionary.
        
        Returns:
            Dictionary representation of template action item
        """
        return {
            'id': self._template_action_item_id,
            'action_name': self._struct.action_name,
            'description': self._struct.description,
            'sequence_order': self._struct.sequence_order,
            'template_action_set_id': self._struct.template_action_set_id,
            'proto_action_item_id': self._struct.proto_action_item_id,
            'is_required': self._struct.is_required,
            'estimated_duration': self.template_action_item.estimated_duration,
            'expected_billable_hours': self.template_action_item.expected_billable_hours,
            'minimum_staff_count': self.template_action_item.minimum_staff_count,
            'revision': self._struct.revision,
            'total_part_demands': self.total_part_demands,
            'total_action_tools': self.total_action_tools,
            'total_attachments': self.total_attachments,
        }
    
    def refresh(self):
        """Refresh cached data from database"""
        self._struct.refresh()
    
    def __repr__(self):
        return f'<TemplateActionContext id={self._template_action_item_id} action_name="{self._struct.action_name}" sequence_order={self._struct.sequence_order}>'

