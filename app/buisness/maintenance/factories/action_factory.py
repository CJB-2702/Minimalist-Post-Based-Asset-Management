"""
Action Factory
Factory for creating Action records from TemplateActionItem and ProtoActionItem records.
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
from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem
from app.data.maintenance.proto_templates.proto_part_demands import ProtoPartDemand
from app.data.maintenance.proto_templates.proto_action_tools import ProtoActionTool

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
        commit: bool = True,
        copy_part_demands: bool = True,
        copy_tools: bool = True
    ) -> Action:
        """
        Create Action from TemplateActionItem.
        
        Args:
            template_action_item_id: Template action item ID to copy from
            maintenance_action_set_id: Maintenance action set ID to associate with
            user_id: User ID creating the action
            commit: Whether to commit the transaction (default: True)
            copy_part_demands: Whether to copy part demands from template (default: True)
            copy_tools: Whether to copy tools from template (default: True)
            
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
        
        # Create PartDemand records from TemplatePartDemand if requested
        if copy_part_demands:
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
        
        # Create ActionTool records from TemplateActionTool if requested
        if copy_tools:
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
    
    @classmethod
    def create_from_proto_action_item(
        cls,
        proto_action_item_id: int,
        maintenance_action_set_id: int,
        sequence_order: int,
        user_id: Optional[int] = None,
        commit: bool = True,
        copy_part_demands: bool = True,
        copy_tools: bool = True,
        action_name: Optional[str] = None,
        description: Optional[str] = None,
        estimated_duration: Optional[float] = None,
        expected_billable_hours: Optional[float] = None,
        safety_notes: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Action:
        """
        Create Action from ProtoActionItem.
        
        Args:
            proto_action_item_id: Proto action item ID to copy from
            maintenance_action_set_id: Maintenance action set ID to associate with
            sequence_order: Sequence order for the action (proto items don't have sequence_order)
            user_id: User ID creating the action
            commit: Whether to commit the transaction (default: True)
            copy_part_demands: Whether to copy part demands from proto (default: True)
            copy_tools: Whether to copy tools from proto (default: True)
            action_name: Override action name (default: use proto action_name)
            description: Override description (default: use proto description)
            estimated_duration: Override estimated duration (default: use proto estimated_duration)
            expected_billable_hours: Override expected billable hours (default: use proto expected_billable_hours)
            safety_notes: Override safety notes (default: use proto safety_notes)
            notes: Override notes (default: use proto notes)
            
        Returns:
            Created Action instance
            
        Raises:
            ValueError: If proto action item not found
        """
        # Get proto action item
        proto_action_item = ProtoActionItem.query.get_or_404(proto_action_item_id)
        
        if not user_id:
            user_id = proto_action_item.created_by_id
        
        # Create Action
        action = Action(
            # Parent reference - REQUIRED
            maintenance_action_set_id=maintenance_action_set_id,
            
            # Note: Action model does NOT have proto_action_item_id field
            # Only template_action_item_id exists. Proto actions are standalone.
            # Sequence order - provided as parameter (proto items don't have sequence_order)
            sequence_order=sequence_order,
            
            # Copy action details from VirtualActionItem, with overrides
            action_name=action_name or proto_action_item.action_name,
            description=description or proto_action_item.description,
            estimated_duration=estimated_duration if estimated_duration is not None else proto_action_item.estimated_duration,
            expected_billable_hours=expected_billable_hours if expected_billable_hours is not None else proto_action_item.expected_billable_hours,
            safety_notes=safety_notes or proto_action_item.safety_notes,
            notes=notes or proto_action_item.notes,
            
            # Execution tracking - initialize
            status='Not Started',
            
            # Audit fields
            created_by_id=user_id,
            updated_by_id=user_id
        )
        
        db.session.add(action)
        db.session.flush()  # Get action ID for part demands and tools
        
        # Create PartDemand records from ProtoPartDemand if requested
        if copy_part_demands:
            # NO proto reference - standalone copy
            for proto_part_demand in proto_action_item.proto_part_demands:
                part_demand = PartDemand(
                    # Parent reference - REQUIRED
                    action_id=action.id,
                    
                    # Copy data from VirtualPartDemand - NO proto reference
                    part_id=proto_part_demand.part_id,
                    quantity_required=proto_part_demand.quantity_required,
                    notes=proto_part_demand.notes,
                    expected_cost=proto_part_demand.expected_cost,
                    
                    # Execution tracking - initialize
                    status='Planned',
                    priority='Medium',
                    sequence_order=proto_part_demand.sequence_order,
                    
                    # Audit fields
                    created_by_id=user_id,
                    updated_by_id=user_id
                )
                db.session.add(part_demand)
        
        # Create ActionTool records from ProtoActionTool if requested
        if copy_tools:
            # NO proto reference - standalone copy
            for proto_action_tool in proto_action_item.proto_action_tools:
                action_tool = ActionTool(
                    # Parent reference - REQUIRED
                    action_id=action.id,
                    
                    # Copy data from VirtualActionTool - NO proto reference
                    tool_id=proto_action_tool.tool_id,
                    quantity_required=proto_action_tool.quantity_required,
                    notes=proto_action_tool.notes,
                    
                    # Execution tracking - initialize
                    status='Planned',
                    priority='Medium',
                    sequence_order=proto_action_tool.sequence_order,
                    
                    # Audit fields
                    created_by_id=user_id,
                    updated_by_id=user_id
                )
                db.session.add(action_tool)
        
        if commit:
            db.session.commit()
            logger.info(f"Created Action {action.id} from proto action item {proto_action_item_id}")
        else:
            db.session.flush()
            logger.info(f"Created Action {action.id} from proto action item {proto_action_item_id} (not committed)")
        
        return action
