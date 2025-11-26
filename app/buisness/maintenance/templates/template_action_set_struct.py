"""
Template Action Set Struct
Data wrapper around TemplateActionSet for convenient access.
Provides cached access and convenience methods - NO business logic.
"""

from typing import List, Optional, Union
from app.data.maintenance.templates.template_action_sets import TemplateActionSet
from app.data.maintenance.templates.template_actions import TemplateActionItem
from app.data.maintenance.templates.template_part_demands import TemplatePartDemand
from app.data.maintenance.templates.template_action_tools import TemplateActionTool
from app.data.maintenance.templates.template_action_set_attachments import TemplateActionSetAttachment
from app.data.maintenance.templates.template_action_attachments import TemplateActionAttachment


class TemplateActionSetStruct:
    """
    Data wrapper around TemplateActionSet for convenient access.
    Provides cached access and convenience methods - NO business logic.
    
    For business logic: Use TemplateMaintenanceContext
    """
    
    def __init__(self, template_action_set: Union[TemplateActionSet, int]):
        """
        Initialize TemplateActionSetStruct with TemplateActionSet instance or ID.
        
        Args:
            template_action_set: TemplateActionSet instance or ID
        """
        if isinstance(template_action_set, int):
            self._template_action_set = TemplateActionSet.query.get_or_404(template_action_set)
            self._template_action_set_id = template_action_set
        else:
            self._template_action_set = template_action_set
            self._template_action_set_id = template_action_set.id
        
        # Cache for lazy loading
        self._template_action_items = None
        self._template_part_demands = None
        self._template_action_tools = None
        self._action_set_attachments = None
        self._action_attachments = None
    
    @property
    def template_action_set(self) -> TemplateActionSet:
        """Get the TemplateActionSet instance"""
        return self._template_action_set
    
    @property
    def template_action_set_id(self) -> int:
        """Get the template action set ID"""
        return self._template_action_set_id
    
    @property
    def id(self) -> int:
        """Get the template action set ID (alias)"""
        return self._template_action_set_id
    
    @property
    def template_action_items(self) -> List[TemplateActionItem]:
        """
        Get all template action items for this template action set, ordered by sequence_order.
        
        Returns:
            List of TemplateActionItem instances
        """
        if self._template_action_items is None:
            self._template_action_items = sorted(
                self._template_action_set.template_action_items,
                key=lambda tai: tai.sequence_order
            )
        return self._template_action_items
    
    @property
    def template_part_demands(self) -> List[TemplatePartDemand]:
        """
        Get all template part demands for template action items in this template action set.
        
        Returns:
            List of TemplatePartDemand instances
        """
        if self._template_part_demands is None:
            self._template_part_demands = []
            for action_item in self.template_action_items:
                self._template_part_demands.extend(action_item.template_part_demands)
        return self._template_part_demands
    
    @property
    def template_action_tools(self) -> List[TemplateActionTool]:
        """
        Get all template action tools for template action items in this template action set.
        
        Returns:
            List of TemplateActionTool instances
        """
        if self._template_action_tools is None:
            self._template_action_tools = []
            for action_item in self.template_action_items:
                self._template_action_tools.extend(action_item.template_action_tools)
        return self._template_action_tools
    
    @property
    def action_set_attachments(self) -> List[TemplateActionSetAttachment]:
        """
        Get all action set level attachments for this template action set.
        
        Returns:
            List of TemplateActionSetAttachment instances
        """
        if self._action_set_attachments is None:
            self._action_set_attachments = sorted(
                self._template_action_set.template_action_set_attachments,
                key=lambda att: att.sequence_order
            )
        return self._action_set_attachments
    
    @property
    def action_attachments(self) -> List[TemplateActionAttachment]:
        """
        Get all action level attachments for template action items in this template action set.
        
        Returns:
            List of TemplateActionAttachment instances
        """
        if self._action_attachments is None:
            self._action_attachments = []
            for action_item in self.template_action_items:
                self._action_attachments.extend(action_item.template_action_attachments)
        return self._action_attachments
    
    # Convenience properties for common fields
    @property
    def task_name(self) -> str:
        """Get the task name"""
        return self._template_action_set.task_name
    
    @property
    def description(self) -> Optional[str]:
        """Get the description"""
        return self._template_action_set.description
    
    @property
    def revision(self) -> Optional[str]:
        """Get the revision"""
        return self._template_action_set.revision
    
    @property
    def is_active(self) -> bool:
        """Get whether template is active"""
        return self._template_action_set.is_active
    
    @property
    def prior_revision_id(self) -> Optional[int]:
        """Get the prior revision ID"""
        return self._template_action_set.prior_revision_id
    
    @property
    def prior_revision(self):
        """Get the prior revision"""
        return self._template_action_set.prior_revision
    
    @classmethod
    def from_id(cls, template_action_set_id: int) -> 'TemplateActionSetStruct':
        """
        Create TemplateActionSetStruct from ID.
        
        Args:
            template_action_set_id: Template action set ID
            
        Returns:
            TemplateActionSetStruct instance
        """
        return cls(template_action_set_id)
    
    @classmethod
    def from_task_name(cls, task_name: str, active_only: bool = True) -> Optional['TemplateActionSetStruct']:
        """
        Create TemplateActionSetStruct from task name.
        
        Args:
            task_name: Task name to search for
            active_only: If True, only search active templates
            
        Returns:
            TemplateActionSetStruct instance or None if not found
        """
        query = TemplateActionSet.query.filter_by(task_name=task_name)
        if active_only:
            query = query.filter_by(is_active=True)
        template_action_set = query.first()
        if template_action_set:
            return cls(template_action_set)
        return None
    
    def refresh(self):
        """Refresh cached data from database"""
        from app import db
        db.session.refresh(self._template_action_set)
        self._template_action_items = None
        self._template_part_demands = None
        self._template_action_tools = None
        self._action_set_attachments = None
        self._action_attachments = None
    
    def __repr__(self):
        revision_str = f' rev={self.revision}' if self.revision else ''
        return f'<TemplateActionSetStruct id={self._template_action_set_id} task_name="{self.task_name}"{revision_str}>'

