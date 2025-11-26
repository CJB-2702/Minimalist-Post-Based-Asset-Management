"""
Template Maintenance Context
Business logic context manager for template maintenance events.
Provides statistics, grouping methods, attachment access, and template management.
"""

from typing import List, Optional, Union, Dict, Any
from app import db
from app.buisness.maintenance.templates.template_action_set_struct import TemplateActionSetStruct
from app.data.maintenance.templates.template_action_sets import TemplateActionSet
from app.data.maintenance.templates.template_actions import TemplateActionItem
from app.data.maintenance.templates.template_action_set_attachments import TemplateActionSetAttachment
from app.data.maintenance.templates.template_action_attachments import TemplateActionAttachment


class TemplateMaintenanceContext:
    """
    Business logic context manager for template maintenance events.
    
    Wraps TemplateActionSetStruct (which wraps TemplateActionSet)
    Provides statistics, grouping methods, attachment access, and template management.
    """
    
    def __init__(self, template_action_set: Union[TemplateActionSet, TemplateActionSetStruct, int]):
        """
        Initialize TemplateMaintenanceContext with TemplateActionSet, TemplateActionSetStruct, or ID.
        
        Args:
            template_action_set: TemplateActionSet instance, TemplateActionSetStruct, or ID
        """
        if isinstance(template_action_set, TemplateActionSetStruct):
            self._struct = template_action_set
        elif isinstance(template_action_set, TemplateActionSet):
            self._struct = TemplateActionSetStruct(template_action_set)
        else:
            self._struct = TemplateActionSetStruct(template_action_set)
        
        self._template_action_set_id = self._struct.template_action_set_id
    
    @property
    def struct(self) -> TemplateActionSetStruct:
        """Get the underlying TemplateActionSetStruct"""
        return self._struct
    
    @property
    def template_action_set(self) -> TemplateActionSet:
        """Get the TemplateActionSet instance"""
        return self._struct.template_action_set
    
    @property
    def template_action_set_id(self) -> int:
        """Get the template action set ID"""
        return self._template_action_set_id
    
    # Statistics
    @property
    def total_action_items(self) -> int:
        """Get total number of template action items"""
        return len(self._struct.template_action_items)
    
    @property
    def total_estimated_duration(self) -> Optional[float]:
        """
        Get total estimated duration in hours.
        
        Returns:
            Sum of estimated_duration from template action set and all action items, or None
        """
        duration = self._struct.template_action_set.estimated_duration or 0.0
        for action_item in self._struct.template_action_items:
            if action_item.estimated_duration:
                duration += action_item.estimated_duration
        return duration if duration > 0 else None
    
    @property
    def total_estimated_cost(self) -> Optional[float]:
        """
        Get total estimated cost.
        
        Returns:
            Sum of parts_cost from template action set and expected_cost from part demands, or None
        """
        cost = self._struct.template_action_set.parts_cost or 0.0
        for part_demand in self._struct.template_part_demands:
            if part_demand.expected_cost:
                cost += part_demand.expected_cost * part_demand.quantity_required
        return cost if cost > 0 else None
    
    # Grouping methods
    def get_part_demands_by_action(self) -> Dict[int, List]:
        """
        Get part demands grouped by template action item.
        
        Returns:
            Dictionary mapping template_action_item_id to list of TemplatePartDemand instances
        """
        part_demands_by_action = {}
        for action_item in self._struct.template_action_items:
            part_demands_by_action[action_item.id] = list(action_item.template_part_demands)
        return part_demands_by_action
    
    def get_tools_by_action(self) -> Dict[int, List]:
        """
        Get action tools grouped by template action item.
        
        Returns:
            Dictionary mapping template_action_item_id to list of TemplateActionTool instances
        """
        tools_by_action = {}
        for action_item in self._struct.template_action_items:
            tools_by_action[action_item.id] = list(action_item.template_action_tools)
        return tools_by_action
    
    # Attachment access
    def get_action_set_attachments(self) -> List[TemplateActionSetAttachment]:
        """
        Get action set level attachments.
        
        Returns:
            List of TemplateActionSetAttachment instances
        """
        return self._struct.action_set_attachments
    
    def get_action_attachments(self, template_action_item_id: Optional[int] = None) -> List[TemplateActionAttachment]:
        """
        Get action level attachments.
        
        Args:
            template_action_item_id: Optional template action item ID to filter by
            
        Returns:
            List of TemplateActionAttachment instances
        """
        if template_action_item_id:
            # Get attachments for specific action item
            for action_item in self._struct.template_action_items:
                if action_item.id == template_action_item_id:
                    return list(action_item.template_action_attachments)
            return []
        return self._struct.action_attachments
    
    # Template management
    def activate(self) -> 'TemplateMaintenanceContext':
        """
        Activate the template.
        
        Returns:
            self for chaining
        """
        self.template_action_set.is_active = True
        db.session.commit()
        self.refresh()
        return self
    
    def deactivate(self) -> 'TemplateMaintenanceContext':
        """
        Deactivate the template.
        
        Returns:
            self for chaining
        """
        self.template_action_set.is_active = False
        db.session.commit()
        self.refresh()
        return self
    
    # Query methods
    @staticmethod
    def get_all() -> List['TemplateMaintenanceContext']:
        """
        Get all template action sets.
        
        Returns:
            List of TemplateMaintenanceContext instances
        """
        template_action_sets = TemplateActionSet.query.all()
        return [TemplateMaintenanceContext(tas) for tas in template_action_sets]
    
    @staticmethod
    def get_active() -> List['TemplateMaintenanceContext']:
        """
        Get all active template action sets.
        
        Returns:
            List of TemplateMaintenanceContext instances
        """
        template_action_sets = TemplateActionSet.query.filter_by(is_active=True).all()
        return [TemplateMaintenanceContext(tas) for tas in template_action_sets]
    
    @staticmethod
    def get_by_task_name(task_name: str, active_only: bool = True) -> Optional['TemplateMaintenanceContext']:
        """
        Get template action set by task name.
        
        Args:
            task_name: Task name to search for
            active_only: If True, only search active templates
            
        Returns:
            TemplateMaintenanceContext instance or None if not found
        """
        struct = TemplateActionSetStruct.from_task_name(task_name, active_only)
        if struct:
            return TemplateMaintenanceContext(struct)
        return None
    
    def summary(self) -> Dict[str, Any]:
        """
        Get summary of template action set.
        
        Returns:
            Dictionary with summary information
        """
        return {
            'id': self._template_action_set_id,
            'task_name': self._struct.task_name,
            'description': self._struct.description,
            'revision': self._struct.revision,
            'is_active': self._struct.is_active,
            'total_action_items': self.total_action_items,
            'total_estimated_duration': self.total_estimated_duration,
            'total_estimated_cost': self.total_estimated_cost,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize template action set to dictionary.
        
        Returns:
            Dictionary representation of template action set
        """
        return {
            'id': self._template_action_set_id,
            'task_name': self._struct.task_name,
            'description': self._struct.description,
            'revision': self._struct.revision,
            'is_active': self._struct.is_active,
            'estimated_duration': self._struct.template_action_set.estimated_duration,
            'safety_review_required': self._struct.template_action_set.safety_review_required,
            'staff_count': self._struct.template_action_set.staff_count,
            'parts_cost': self._struct.template_action_set.parts_cost,
            'labor_hours': self._struct.template_action_set.labor_hours,
            'total_action_items': self.total_action_items,
            'total_estimated_duration': self.total_estimated_duration,
            'total_estimated_cost': self.total_estimated_cost,
            'prior_revision_id': self._struct.prior_revision_id,
        }
    
    def refresh(self):
        """Refresh cached data from database"""
        self._struct.refresh()
    
    def __repr__(self):
        return f'<TemplateMaintenanceContext id={self._template_action_set_id} task_name="{self._struct.task_name}" is_active={self._struct.is_active}>'

