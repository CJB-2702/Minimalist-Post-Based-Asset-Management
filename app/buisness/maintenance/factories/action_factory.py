"""
Action Factory
Factory for creating Action records from TemplateActionItem records.
Handles copying action details, sequence order, and creating PartDemand and ActionTool records.
"""

from typing import List, Optional
from app import db
from app.logger import get_logger
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.part_demands import PartDemand
from app.data.maintenance.base.action_tools import ActionTool
from app.data.maintenance.templates.template_actions import TemplateActionItem
from app.data.maintenance.templates.template_part_demands import TemplatePartDemand
from app.data.maintenance.templates.template_action_tools import TemplateActionTool

logger = get_logger("asset_management.buisness.maintenance.factories")


class ActionFactory:
    """
    Factory for creating Action records from TemplateActionItem records.
    
    Responsibilities:
    - Copy action details from template
    - Copy sequence_order from template
    - Set up relationships (action set, template reference)
    - Initialize status
    - Create PartDemand records from TemplatePartDemand
    - Create ActionTool records from TemplateActionTool
    """
    
    @classmethod
    def create_from_template_action_item(
        cls,
        template_action_item_id: int,
        maintenance_action_set_id: int,
        user_id: Optional[int] = None,
        commit: bool = True
    ) -> Action:
        """
        Create Action from TemplateActionItem.
        
        Args:
            template_action_item_id: Template action item ID to copy from
            maintenance_action_set_id: Maintenance action set ID to associate with
            user_id: User ID creating the action
            commit: Whether to commit the transaction (default: True)
            
        Returns:
            Created Action instance
            
        Raises:
            ValueError: If template action item not found
        """
        # Get template action item
        template_action_item = TemplateActionItem.query.get_or_404(template_action_item_id)
        
        if not user_id:
            user_id = template_action_item.created_by_id
        
        # Create Action
        action = Action(
            # Parent reference - REQUIRED
            maintenance_action_set_id=maintenance_action_set_id,
            
            # Template reference
            template_action_item_id=template_action_item_id,
            
            # Copy sequence_order from template - REQUIRED
            sequence_order=template_action_item.sequence_order,
            
            # Copy action details from VirtualActionItem
            action_name=template_action_item.action_name,
            description=template_action_item.description,
            estimated_duration=template_action_item.estimated_duration,
            expected_billable_hours=template_action_item.expected_billable_hours,
            safety_notes=template_action_item.safety_notes,
            notes=template_action_item.notes,
            
            # Execution tracking - initialize
            status='Not Started',
            
            # Audit fields
            created_by_id=user_id,
            updated_by_id=user_id
        )
        
        db.session.add(action)
        db.session.flush()  # Get action ID for part demands and tools
        
        # Create PartDemand records from TemplatePartDemand
        # NO template reference - standalone copy
        for template_part_demand in template_action_item.template_part_demands:
            part_demand = PartDemand(
                # Parent reference - REQUIRED
                action_id=action.id,
                
                # Copy data from VirtualPartDemand - NO template reference
                part_id=template_part_demand.part_id,
                quantity_required=template_part_demand.quantity_required,
                notes=template_part_demand.notes,
                expected_cost=template_part_demand.expected_cost,
                
                # Execution tracking - initialize
                status='Planned',
                priority='Medium',
                sequence_order=template_part_demand.sequence_order,
                
                # Audit fields
                created_by_id=user_id,
                updated_by_id=user_id
            )
            db.session.add(part_demand)
        
        # Create ActionTool records from TemplateActionTool
        # NO template reference - standalone copy
        for template_action_tool in template_action_item.template_action_tools:
            action_tool = ActionTool(
                # Parent reference - REQUIRED
                action_id=action.id,
                
                # Copy data from VirtualActionTool - NO template reference
                tool_id=template_action_tool.tool_id,
                quantity_required=template_action_tool.quantity_required,
                notes=template_action_tool.notes,
                
                # Execution tracking - initialize
                status='Planned',
                priority='Medium',
                sequence_order=template_action_tool.sequence_order,
                
                # Audit fields
                created_by_id=user_id,
                updated_by_id=user_id
            )
            db.session.add(action_tool)
        
        if commit:
            db.session.commit()
            logger.info(f"Created Action {action.id} from template action item {template_action_item_id}")
        else:
            db.session.flush()
            logger.info(f"Created Action {action.id} from template action item {template_action_item_id} (not committed)")
        
        return action
    
    @classmethod
    def create_from_template_action_set(
        cls,
        template_action_set_id: int,
        maintenance_action_set_id: int,
        user_id: Optional[int] = None,
        commit: bool = True
    ) -> List[Action]:
        """
        Create all Actions from TemplateActionItems in a TemplateActionSet.
        
        Args:
            template_action_set_id: Template action set ID
            maintenance_action_set_id: Maintenance action set ID to associate with
            user_id: User ID creating the actions
            commit: Whether to commit the transaction (default: True)
            
        Returns:
            List of created Action instances, ordered by sequence_order
        """
        # Get template action set
        from app.data.maintenance.templates.template_action_sets import TemplateActionSet
        template_action_set = TemplateActionSet.query.get_or_404(template_action_set_id)
        
        # Get template action items ordered by sequence_order
        template_action_items = sorted(
            template_action_set.template_action_items,
            key=lambda tai: tai.sequence_order
        )
        
        created_actions = []
        
        for template_action_item in template_action_items:
            action = cls.create_from_template_action_item(
                template_action_item_id=template_action_item.id,
                maintenance_action_set_id=maintenance_action_set_id,
                user_id=user_id,
                commit=False  # Don't commit individual actions, commit at end
            )
            created_actions.append(action)
        
        if commit:
            db.session.commit()
            logger.info(f"Created {len(created_actions)} Actions from template action set {template_action_set_id}")
        else:
            db.session.flush()
            logger.info(f"Created {len(created_actions)} Actions from template action set {template_action_set_id} (not committed)")
        
        return created_actions
