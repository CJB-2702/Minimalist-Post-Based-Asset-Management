#!/usr/bin/env python3
"""
Maintenance Debug Data Insertion
Inserts debug data for maintenance module (templates, plans, action sets)

Uses factories and contexts for data creation.
"""

from app import db
from app.logger import get_logger
from datetime import datetime

logger = get_logger("asset_management.debug.maintenance")


def insert_maintenance_debug_data(debug_data, system_user_id):
    """
    Insert debug data for maintenance module
    
    Args:
        debug_data (dict): Debug data from JSON file
        system_user_id (int): System user ID for audit fields
    
    Raises:
        Exception: If insertion fails (fail-fast)
    """
    if not debug_data:
        logger.info("No maintenance debug data to insert")
        return
    
    logger.info("Inserting maintenance debug data...")
    
    try:
        maintenance_data = debug_data.get('Maintenance', {})
        
        # Insert in dependency order
        # 1. Proto action items (no dependencies)
        if 'proto_action_items' in maintenance_data:
            _insert_proto_action_items(maintenance_data['proto_action_items'], system_user_id)
            db.session.flush()  # Flush so proto action items are available for part demands
        
        # 2. Template action sets (no dependencies)
        if 'template_actions' in maintenance_data:
            _insert_template_action_sets(maintenance_data['template_actions'], system_user_id)
            db.session.flush()  # Flush so template action sets are available for template action items
        
        # 3. Template action items (depends on template action sets and proto action items)
        if 'template_action_items' in maintenance_data:
            _insert_template_action_items(maintenance_data['template_action_items'], system_user_id)
            db.session.flush()  # Flush so template action items are available for part demands and tools
        
        # 4. Proto part demands (depends on proto action items and parts)
        if 'proto_part_demands' in maintenance_data:
            _insert_proto_part_demands(maintenance_data['proto_part_demands'], system_user_id)
        
        # 5. Proto action tools (depends on proto action items and tools)
        if 'proto_action_tools' in maintenance_data:
            _insert_proto_action_tools(maintenance_data['proto_action_tools'], system_user_id)
            db.session.flush()  # Flush so proto tools are available for copying to templates
        
        # 6. Template part demands (depends on template action items and parts)
        if 'template_part_demands' in maintenance_data:
            _insert_template_part_demands(maintenance_data['template_part_demands'], system_user_id)
        
        # 7. Copy proto tools to template tools for template action items that reference proto action items
        _copy_proto_tools_to_template_tools(system_user_id)
        
        # 8. Template action tools (depends on template action items and tools) - explicit ones from JSON
        if 'template_action_tools' in maintenance_data:
            _insert_template_action_tools(maintenance_data['template_action_tools'], system_user_id)
        
        # 8. Maintenance plans (depends on template action sets and asset types)
        if 'maintenance_plans' in maintenance_data:
            _insert_maintenance_plans(maintenance_data['maintenance_plans'], system_user_id)
        
        # 9. Maintenance action sets/events (depends on maintenance plans, assets, actions, parts)
        if 'maintenance_events' in maintenance_data:
            _insert_maintenance_action_sets(maintenance_data['maintenance_events'], system_user_id)
        
        db.session.commit()
        logger.info("Successfully inserted maintenance debug data")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to insert maintenance debug data: {e}")
        raise


def _insert_proto_action_items(items_data, system_user_id):
    """Insert proto action items"""
    from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem
    
    for item_data in items_data:
        # Remove template-specific fields
        item_data = {k: v for k, v in item_data.items() 
                    if k not in ['template_action_set_task_name', 'sequence_order']}
        
        ProtoActionItem.find_or_create_from_dict(
            item_data,
            user_id=system_user_id,
            lookup_fields=['action_name', 'revision']
        )
        logger.debug(f"Inserted proto action item: {item_data.get('action_name')}")


def _insert_template_action_sets(templates_data, system_user_id):
    """Insert template action sets"""
    from app.data.maintenance.templates.template_action_sets import TemplateActionSet
    
    for template_data in templates_data:
        TemplateActionSet.find_or_create_from_dict(
            template_data,
            user_id=system_user_id,
            lookup_fields=['task_name', 'revision']
        )
        logger.debug(f"Inserted template action set: {template_data.get('task_name')}")


def _insert_template_action_items(items_data, system_user_id):
    """Insert template action items"""
    from app.data.maintenance.templates.template_actions import TemplateActionItem
    from app.data.maintenance.templates.template_action_sets import TemplateActionSet
    from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem
    
    for item_data in items_data:
        # Handle template_action_set_task_name reference
        if 'template_action_set_task_name' in item_data:
            task_name = item_data.pop('template_action_set_task_name')
            template_action_set = TemplateActionSet.query.filter_by(task_name=task_name).first()
            if template_action_set:
                item_data['template_action_set_id'] = template_action_set.id
            else:
                logger.warning(f"Template action set '{task_name}' not found")
                continue
        
        # Handle proto_action_item reference (optional)
        if 'proto_action_item_action_name' in item_data:
            action_name = item_data.pop('proto_action_item_action_name')
            proto_action_item = ProtoActionItem.query.filter_by(action_name=action_name).first()
            if proto_action_item:
                item_data['proto_action_item_id'] = proto_action_item.id
        
        TemplateActionItem.find_or_create_from_dict(
            item_data,
            user_id=system_user_id,
            lookup_fields=['action_name', 'template_action_set_id', 'sequence_order']
        )
        logger.debug(f"Inserted template action item: {item_data.get('action_name')}")


def _insert_proto_part_demands(demands_data, system_user_id):
    """Insert proto part demands"""
    from app.data.maintenance.proto_templates.proto_part_demands import ProtoPartDemand
    from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem
    from app.data.core.supply.part import Part
    
    for demand_data in demands_data:
        # Make a copy to avoid modifying the original
        demand_data = demand_data.copy()
        
        # Handle proto_action_item reference
        if 'proto_action_item_action_name' in demand_data:
            action_name = demand_data.pop('proto_action_item_action_name')
            # Query for proto action item - try without revision first, then with revision if specified
            proto_action_item = ProtoActionItem.query.filter_by(action_name=action_name).first()
            
            if not proto_action_item:
                # Try to find by action_name only (revision might be None)
                proto_action_item = ProtoActionItem.query.filter(
                    ProtoActionItem.action_name == action_name
                ).first()
            
            if proto_action_item:
                demand_data['proto_action_item_id'] = proto_action_item.id
                logger.debug(f"Found proto action item '{action_name}' (id={proto_action_item.id})")
            else:
                logger.warning(f"Proto action item '{action_name}' not found - available items: {[item.action_name for item in ProtoActionItem.query.all()]}")
                continue
        
        # Handle part_number reference
        if 'part_number' in demand_data:
            part_number = demand_data.pop('part_number')
            part = Part.query.filter_by(part_number=part_number).first()
            if part:
                demand_data['part_id'] = part.id
                logger.debug(f"Found part '{part_number}' (id={part.id})")
            else:
                logger.warning(f"Part '{part_number}' not found")
                continue
        
        # Check if already exists
        existing = ProtoPartDemand.query.filter_by(
            proto_action_item_id=demand_data.get('proto_action_item_id'),
            part_id=demand_data.get('part_id'),
            sequence_order=demand_data.get('sequence_order', 1)
        ).first()
        
        if existing:
            logger.debug(f"Proto part demand already exists for action_id={demand_data.get('proto_action_item_id')}, part_id={demand_data.get('part_id')}")
            continue
        
        # Create the proto part demand
        proto_part_demand, created = ProtoPartDemand.find_or_create_from_dict(
            demand_data,
            user_id=system_user_id,
            lookup_fields=['proto_action_item_id', 'part_id', 'sequence_order']
        )
        
        if created:
            logger.info(f"Inserted proto part demand: action_id={demand_data.get('proto_action_item_id')}, part_id={demand_data.get('part_id')}, qty={demand_data.get('quantity_required')}")
        else:
            logger.debug(f"Proto part demand already existed")


def _insert_proto_action_tools(tools_data, system_user_id):
    """Insert proto action tools"""
    from app.data.maintenance.proto_templates.proto_action_tools import ProtoActionTool
    from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem
    from app.data.core.supply.tool import Tool
    
    for tool_data in tools_data:
        # Make a copy to avoid modifying the original
        tool_data = tool_data.copy()
        
        # Handle proto_action_item reference
        if 'proto_action_item_action_name' in tool_data:
            action_name = tool_data.pop('proto_action_item_action_name')
            proto_action_item = ProtoActionItem.query.filter_by(action_name=action_name).first()
            
            if not proto_action_item:
                # Try to find by action_name only (revision might be None)
                proto_action_item = ProtoActionItem.query.filter(
                    ProtoActionItem.action_name == action_name
                ).first()
            
            if proto_action_item:
                tool_data['proto_action_item_id'] = proto_action_item.id
                logger.debug(f"Found proto action item '{action_name}' (id={proto_action_item.id})")
            else:
                logger.warning(f"Proto action item '{action_name}' not found - available items: {[item.action_name for item in ProtoActionItem.query.all()]}")
                continue
        
        # Handle tool_name reference
        if 'tool_name' in tool_data:
            tool_name = tool_data.pop('tool_name')
            tool = Tool.query.filter_by(tool_name=tool_name).first()
            if tool:
                tool_data['tool_id'] = tool.id
                logger.debug(f"Found tool '{tool_name}' (id={tool.id})")
            else:
                logger.warning(f"Tool '{tool_name}' not found")
                continue
        
        # Check if already exists
        existing = ProtoActionTool.query.filter_by(
            proto_action_item_id=tool_data.get('proto_action_item_id'),
            tool_id=tool_data.get('tool_id'),
            sequence_order=tool_data.get('sequence_order', 1)
        ).first()
        
        if existing:
            logger.debug(f"Proto action tool already exists for action_id={tool_data.get('proto_action_item_id')}, tool_id={tool_data.get('tool_id')}")
            continue
        
        # Create the proto action tool
        proto_action_tool, created = ProtoActionTool.find_or_create_from_dict(
            tool_data,
            user_id=system_user_id,
            lookup_fields=['proto_action_item_id', 'tool_id', 'sequence_order']
        )
        
        if created:
            logger.info(f"Inserted proto action tool: action_id={tool_data.get('proto_action_item_id')}, tool_id={tool_data.get('tool_id')}, qty={tool_data.get('quantity_required')}")
        else:
            logger.debug(f"Proto action tool already existed")


def _insert_template_part_demands(demands_data, system_user_id):
    """Insert template part demands"""
    from app.data.maintenance.templates.template_part_demands import TemplatePartDemand
    from app.data.maintenance.templates.template_actions import TemplateActionItem
    from app.data.core.supply.part import Part
    
    for demand_data in demands_data:
        # Handle template_action_item reference
        if 'template_action_item_action_name' in demand_data:
            action_name = demand_data.pop('template_action_item_action_name')
            template_action_item = TemplateActionItem.query.filter_by(action_name=action_name).first()
            if template_action_item:
                demand_data['template_action_item_id'] = template_action_item.id
            else:
                logger.warning(f"Template action item '{action_name}' not found")
                continue
        
        # Handle part_number reference
        if 'part_number' in demand_data:
            part_number = demand_data.pop('part_number')
            part = Part.query.filter_by(part_number=part_number).first()
            if part:
                demand_data['part_id'] = part.id
            else:
                logger.warning(f"Part '{part_number}' not found")
                continue
        
        TemplatePartDemand.find_or_create_from_dict(
            demand_data,
            user_id=system_user_id,
            lookup_fields=['template_action_item_id', 'part_id']
        )
        logger.debug(f"Inserted template part demand")


def _copy_proto_tools_to_template_tools(system_user_id):
    """
    Copy proto action tools to template action tools for template action items that reference proto action items.
    
    This ensures that when a TemplateActionItem references a ProtoActionItem, all proto tools are automatically
    copied to TemplateActionTools. This follows the design pattern where templates copy data from proto (standalone copies).
    """
    from app.data.maintenance.templates.template_actions import TemplateActionItem
    from app.data.maintenance.templates.template_action_tools import TemplateActionTool
    from app.data.maintenance.proto_templates.proto_action_tools import ProtoActionTool
    
    # Get all template action items that reference proto action items
    template_action_items = TemplateActionItem.query.filter(
        TemplateActionItem.proto_action_item_id.isnot(None)
    ).all()
    
    copied_count = 0
    skipped_count = 0
    
    for template_action_item in template_action_items:
        if not template_action_item.proto_action_item_id:
            continue
        
        # Get all proto action tools for the referenced proto action item
        proto_action_tools = ProtoActionTool.query.filter_by(
            proto_action_item_id=template_action_item.proto_action_item_id
        ).order_by(ProtoActionTool.sequence_order).all()
        
        for proto_tool in proto_action_tools:
            # Check if template action tool already exists
            existing = TemplateActionTool.query.filter_by(
                template_action_item_id=template_action_item.id,
                tool_id=proto_tool.tool_id,
                sequence_order=proto_tool.sequence_order
            ).first()
            
            if existing:
                skipped_count += 1
                logger.debug(f"Template action tool already exists for template_action_item_id={template_action_item.id}, tool_id={proto_tool.tool_id}")
                continue
            
            # Copy proto tool to template tool (standalone copy, no foreign key to proto)
            template_tool = TemplateActionTool(
                template_action_item_id=template_action_item.id,
                tool_id=proto_tool.tool_id,
                quantity_required=proto_tool.quantity_required,
                notes=proto_tool.notes,
                is_required=proto_tool.is_required,
                sequence_order=proto_tool.sequence_order,
                created_by_id=system_user_id,
                updated_by_id=system_user_id
            )
            db.session.add(template_tool)
            copied_count += 1
            logger.debug(f"Copied proto tool (id={proto_tool.id}) to template tool for template_action_item_id={template_action_item.id}, tool_id={proto_tool.tool_id}")
    
    if copied_count > 0 or skipped_count > 0:
        logger.info(f"Copied {copied_count} proto tools to template tools (skipped {skipped_count} existing)")


def _insert_template_action_tools(tools_data, system_user_id):
    """Insert template action tools (explicit ones from JSON, in addition to auto-copied ones)"""
    from app.data.maintenance.templates.template_action_tools import TemplateActionTool
    from app.data.maintenance.templates.template_actions import TemplateActionItem
    from app.data.core.supply.tool import Tool
    
    for tool_data in tools_data:
        # Make a copy to avoid modifying the original
        tool_data = tool_data.copy()
        
        # Handle template_action_item reference
        if 'template_action_item_action_name' in tool_data:
            action_name = tool_data.pop('template_action_item_action_name')
            template_action_item = TemplateActionItem.query.filter_by(action_name=action_name).first()
            if template_action_item:
                tool_data['template_action_item_id'] = template_action_item.id
            else:
                logger.warning(f"Template action item '{action_name}' not found")
                continue
        
        # Handle tool_name reference
        if 'tool_name' in tool_data:
            tool_name = tool_data.pop('tool_name')
            tool = Tool.query.filter_by(tool_name=tool_name).first()
            if tool:
                tool_data['tool_id'] = tool.id
            else:
                logger.warning(f"Tool '{tool_name}' not found")
                continue
        
        # Check if already exists (might have been auto-copied from proto)
        existing = TemplateActionTool.query.filter_by(
            template_action_item_id=tool_data.get('template_action_item_id'),
            tool_id=tool_data.get('tool_id'),
            sequence_order=tool_data.get('sequence_order', 1)
        ).first()
        
        if existing:
            logger.debug(f"Template action tool already exists (possibly auto-copied from proto), skipping")
            continue
        
        TemplateActionTool.find_or_create_from_dict(
            tool_data,
            user_id=system_user_id,
            lookup_fields=['template_action_item_id', 'tool_id', 'sequence_order']
        )
        logger.debug(f"Inserted explicit template action tool")


def _insert_maintenance_plans(plans_data, system_user_id):
    """Insert maintenance plans"""
    from app.data.maintenance.planning.maintenance_plans import MaintenancePlan
    from app.data.core.asset_info.asset_type import AssetType
    from app.data.core.asset_info.make_model import MakeModel
    from app.data.maintenance.templates.template_action_sets import TemplateActionSet
    
    for plan_data in plans_data:
        # Handle asset_type_name reference
        if 'asset_type_name' in plan_data:
            asset_type_name = plan_data.pop('asset_type_name')
            asset_type = AssetType.query.filter_by(name=asset_type_name).first()
            if asset_type:
                plan_data['asset_type_id'] = asset_type.id
            else:
                logger.warning(f"Asset type '{asset_type_name}' not found")
                continue
        
        # Handle make_model_name reference (format: "Toyota Corolla")
        if 'make_model_name' in plan_data:
            make_model_name = plan_data.pop('make_model_name')
            # Split by space, first part is make, rest is model
            parts = make_model_name.split(' ', 1)
            if len(parts) == 2:
                make, model = parts
                make_model = MakeModel.query.filter_by(make=make, model=model).first()
                if make_model:
                    plan_data['model_id'] = make_model.id
                else:
                    logger.warning(f"Make/Model '{make_model_name}' not found")
            else:
                logger.warning(f"Invalid make_model_name format: '{make_model_name}' (expected 'Make Model')")
        
        # Handle template_action_set reference
        if 'template_action_set_task_name' in plan_data:
            task_name = plan_data.pop('template_action_set_task_name')
            template_action_set = TemplateActionSet.query.filter_by(task_name=task_name).first()
            if template_action_set:
                plan_data['template_action_set_id'] = template_action_set.id
            else:
                logger.warning(f"Template action set '{task_name}' not found")
                continue
        
        # Convert frequency_type from display format to database format
        if 'frequency_type' in plan_data:
            freq_type = plan_data['frequency_type']
            if freq_type == 'Time-based':
                # Check if delta_hours exists, if so use 'hours', otherwise 'days'
                if 'delta_hours' in plan_data and plan_data.get('delta_hours'):
                    plan_data['frequency_type'] = 'hours'
                    # Convert delta_hours to delta_days if needed
                    if 'delta_days' not in plan_data or not plan_data.get('delta_days'):
                        plan_data['delta_days'] = plan_data.get('delta_hours', 0) / 24
                else:
                    plan_data['frequency_type'] = 'days'
            elif freq_type.startswith('Meter'):
                # Extract meter number (e.g., "Meter 1" -> "meter1")
                meter_num = freq_type.split()[-1] if len(freq_type.split()) > 1 else '1'
                plan_data['frequency_type'] = f'meter{meter_num}'
        
        # Remove delta_hours if it exists (we use delta_days for time-based)
        if 'delta_hours' in plan_data:
            delta_hours = plan_data.pop('delta_hours')
            if 'delta_days' not in plan_data or not plan_data.get('delta_days'):
                plan_data['delta_days'] = delta_hours / 24
        
        MaintenancePlan.find_or_create_from_dict(
            plan_data,
            user_id=system_user_id,
            lookup_fields=['name']
        )
        logger.debug(f"Inserted maintenance plan: {plan_data.get('name')}")


def _insert_maintenance_action_sets(events_data, system_user_id):
    """
    Insert maintenance action sets using MaintenanceFactory.
    
    This ensures proper creation order: proto actions → templates (with proto tools copied) → actions (with template tools copied).
    Uses MaintenanceFactory.create_from_template which handles all the copying automatically.
    """
    from app.buisness.maintenance.factories.maintenance_factory import MaintenanceFactory
    from app.data.core.asset_info.asset import Asset
    from app.data.maintenance.planning.maintenance_plans import MaintenancePlan
    from app.data.maintenance.templates.template_action_sets import TemplateActionSet
    
    for event_data in events_data:
        event_data = event_data.copy()
        
        # Handle asset_name reference
        asset_id = None
        if 'asset_name' in event_data:
            asset_name = event_data.pop('asset_name')
            asset = Asset.query.filter_by(name=asset_name).first()
            if asset:
                asset_id = asset.id
            else:
                logger.warning(f"Asset '{asset_name}' not found")
                continue
        
        # Handle maintenance_plan_name reference to get template_action_set_id
        template_action_set_id = None
        maintenance_plan_id = None
        if 'maintenance_plan_name' in event_data:
            plan_name = event_data.pop('maintenance_plan_name')
            maintenance_plan = MaintenancePlan.query.filter_by(name=plan_name).first()
            if maintenance_plan:
                maintenance_plan_id = maintenance_plan.id
                if maintenance_plan.template_action_set_id:
                    template_action_set_id = maintenance_plan.template_action_set_id
            else:
                logger.warning(f"Maintenance plan '{plan_name}' not found")
                continue
        
        # If no template_action_set_id from plan, try to get from event_data
        if not template_action_set_id and 'template_action_set_task_name' in event_data:
            task_name = event_data.pop('template_action_set_task_name')
            template_action_set = TemplateActionSet.query.filter_by(task_name=task_name).first()
            if template_action_set:
                template_action_set_id = template_action_set.id
            else:
                logger.warning(f"Template action set '{task_name}' not found")
                continue
        
        if not template_action_set_id:
            logger.warning(f"No template action set found for maintenance event: {event_data.get('task_name')}")
            continue
        
        # Handle datetime conversions
        planned_start_datetime = None
        if 'planned_start_datetime' in event_data:
            planned_start_datetime_str = event_data.pop('planned_start_datetime')
            if isinstance(planned_start_datetime_str, str):
                try:
                    planned_start_datetime = datetime.strptime(planned_start_datetime_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        planned_start_datetime = datetime.strptime(planned_start_datetime_str, '%Y-%m-%d')
                    except ValueError:
                        logger.warning(f"Invalid date format for planned_start_datetime")
        
        # Check if maintenance action set already exists for this asset and template
        from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
        existing = MaintenanceActionSet.query.filter_by(
            asset_id=asset_id,
            template_action_set_id=template_action_set_id
        ).first()
        
        if existing:
            logger.debug(f"Maintenance action set already exists for asset_id={asset_id}, template_action_set_id={template_action_set_id}")
            continue
        
        # Use MaintenanceFactory to create complete maintenance event from template
        # This automatically creates:
        # - MaintenanceActionSet (with Event)
        # - All Actions (from TemplateActionItems)
        # - All PartDemands (from TemplatePartDemands)
        # - All ActionTools (from TemplateActionTools)
        try:
            maintenance_action_set = MaintenanceFactory.create_from_template(
                template_action_set_id=template_action_set_id,
                asset_id=asset_id,
                planned_start_datetime=planned_start_datetime,
                maintenance_plan_id=maintenance_plan_id,
                user_id=system_user_id,
                commit=False  # Commit all at once at the end
            )
            logger.info(f"Created maintenance action set {maintenance_action_set.id} from template {template_action_set_id} for asset {asset_id}")
        except Exception as e:
            logger.error(f"Failed to create maintenance action set from template {template_action_set_id}: {e}")
            raise

