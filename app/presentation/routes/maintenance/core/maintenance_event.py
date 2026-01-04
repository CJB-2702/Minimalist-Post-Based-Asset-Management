"""
Maintenance work and edit routes for maintenance events
"""
import traceback
from datetime import datetime

from flask import Blueprint, render_template, abort, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user

from app import db
from app.logger import get_logger
from app.buisness.core.event_context import EventContext
from app.buisness.maintenance.base.structs.action_struct import ActionStruct
from app.buisness.maintenance.base.structs.maintenance_action_set_struct import MaintenanceActionSetStruct
from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
from app.buisness.maintenance.factories.action_factory import ActionFactory
from app.data.core.asset_info.asset import Asset
from app.data.core.event_info.event import Event
from app.data.core.supply.part_definition import PartDefinition
from app.data.core.supply.tool_definition import ToolDefinition
from app.data.core.user_info.user import User
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.action_tools import ActionTool
from app.data.maintenance.base.maintenance_blockers import MaintenanceBlocker
from app.data.maintenance.planning.maintenance_plans import MaintenancePlan
from app.data.maintenance.base.part_demands import PartDemand
from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem
from app.services.maintenance.assign_monitor_service import AssignMonitorService

logger = get_logger("asset_management.routes.maintenance")

# Create blueprint for maintenance event work/edit routes
maintenance_event_bp = Blueprint('maintenance_event', __name__, url_prefix='/maintenance/maintenance-event')


@maintenance_event_bp.route('/<int:event_id>')
@maintenance_event_bp.route('/<int:event_id>/')
@maintenance_event_bp.route('/<int:event_id>/view')
@login_required
def view_maintenance_event(event_id):
    """View detailed information about a maintenance event"""
    logger.info(f"Viewing maintenance event for event_id={event_id}")
    
    try:
        # Get the event
        event = Event.query.get(event_id)
        if not event:
            logger.warning(f"Event {event_id} not found")
            abort(404)
        
        # Get the maintenance action set by event_id (ONE-TO-ONE relationship)
        maintenance_context = MaintenanceContext.from_event(event_id)
        if not maintenance_context:
            logger.warning(f"No maintenance action set found for event_id={event_id}")
            abort(404)
        maintenance_struct = maintenance_context.struct
        if not maintenance_struct:
            logger.warning(f"No maintenance action set found for event_id={event_id}")
            abort(404)
        
        # Get actions with their structs for convenient access
        action_structs = [ActionStruct(action) for action in maintenance_struct.actions]
        
        # Calculate action status counts
        completed_count = sum(1 for a in action_structs if a.action.status == 'Complete')
        in_progress_count = sum(1 for a in action_structs if a.action.status == 'In Progress')
        
        # Get blockers for display
        blockers = maintenance_struct.blockers if hasattr(maintenance_struct, 'blockers') else []
        active_blockers = [d for d in blockers if d.end_date is None]
        
        # Get meter reading if available
        meter_reading = None
        if maintenance_struct.maintenance_action_set and maintenance_struct.maintenance_action_set.meter_reading_id:
            from app.data.core.asset_info.meter_history import MeterHistory
            meter_reading = MeterHistory.query.get(maintenance_struct.maintenance_action_set.meter_reading_id)
        
        return render_template(
            'maintenance/base/view_maintenance_event.html',
            maintenance=maintenance_struct,
            maintenance_context=maintenance_context,
            event=event,
            actions=action_structs,
            completed_count=completed_count,
            in_progress_count=in_progress_count,
            blockers=blockers,
            active_blockers=active_blockers,
            meter_reading=meter_reading,
        )
        
    except ImportError as e:
        logger.error(f"Could not import maintenance modules: {e}")
        abort(500)
    except Exception as e:
        logger.error(f"Error viewing maintenance event {event_id}: {e}")
        abort(500)


@maintenance_event_bp.route('/<int:event_id>/work')
@login_required
def work_maintenance_event(event_id):
    """Work on a maintenance event (perform maintenance)"""
    logger.info(f"Working on maintenance event for event_id={event_id}")
    
    try:
        # Get the maintenance action set by event_id (ONE-TO-ONE relationship)
        maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
        
        if not maintenance_struct:
            logger.warning(f"No maintenance action set found for event_id={event_id}")
            abort(404)
        
        # Check if maintenance is in Delayed or Blocked status - redirect to view page
        if maintenance_struct.status in ['Delayed', 'Blocked']:
            flash('Work is paused due to blocked status. Please end the blocked status to continue work.', 'warning')
            return redirect(url_for('maintenance_event.view_maintenance_event', event_id=event_id))
        
        # Get the event
        event = Event.query.get(event_id)
        if not event:
            logger.warning(f"Event {event_id} not found")
            abort(404)
        
        # Check if event status is complete - redirect to view page
        if event.status and event.status.lower() == 'complete':
            return redirect(url_for('maintenance_event.view_maintenance_event', event_id=event_id))
        
        # Get actions with their structs
        action_structs = [ActionStruct(action) for action in maintenance_struct.actions]
        
        # Get context for business logic
        maintenance_context = MaintenanceContext.from_event(event_id)
        
        # Get asset if available
        asset = maintenance_struct.asset if hasattr(maintenance_struct, 'asset') else None
        
        # Get blockers for display
        blockers = maintenance_struct.blockers if hasattr(maintenance_struct, 'blockers') else []
        active_blockers = [d for d in blockers if d.end_date is None]
        
        # Check if there are active blockers - redirect to view page
        if active_blockers:
            flash('Work is paused due to active blockers. Please end the blocked status to continue work.', 'warning')
            return redirect(url_for('maintenance_event.view_maintenance_event', event_id=event_id))
        
        # Get parts for part demand dropdown
        parts = PartDefinition.query.filter_by(status='Active').order_by(PartDefinition.part_name).all()
        users = User.query.order_by(User.username).all()
        
        # Get blocker allowable values for dropdowns
        from app.data.maintenance.base.maintenance_blockers import MaintenanceBlocker
        blocker_instance = MaintenanceBlocker()  # Temporary instance to access properties
        allowable_capability_statuses = blocker_instance.allowable_capability_statuses
        allowable_reasons = blocker_instance.allowable_reasons
        
        # Check if all actions are in terminal states
        all_actions_terminal = maintenance_context.all_actions_in_terminal_states()
        
        return render_template(
            'maintenance/base/work_maintenance_event.html',
            maintenance=maintenance_struct,
            maintenance_context=maintenance_context,
            event=event,
            actions=action_structs,
            asset=asset,
            blockers=blockers,
            active_blockers=active_blockers,
            parts=parts,
            users=users,
            all_actions_terminal=all_actions_terminal,
            allowable_capability_statuses=allowable_capability_statuses,
            allowable_reasons=allowable_reasons,
        )
        
    except ImportError as e:
        logger.error(f"Could not import maintenance modules: {e}")
        abort(500)
    except Exception as e:
        logger.error(f"Error working on maintenance event {event_id}: {e}")
        abort(500)


# ============================================================================
# Work Page Interactivity Routes
# ============================================================================



def _create_action_common_logic(event_id, action_name, description, estimated_duration, expected_billable_hours,
                                safety_notes, notes, insert_position, after_action_id, copy_part_demands, copy_tools):
    """Common logic for creating actions - handles sequence order calculation and shifting"""
    # Get maintenance struct
    maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
    if not maintenance_struct:
        flash('Maintenance event not found', 'error')
        return None, None
    
    maintenance_context = MaintenanceContext.from_event(event_id)
    
    # Calculate sequence order based on insert position
    sequence_order = maintenance_context._calculate_sequence_order(
        insert_position=insert_position,
        after_action_id=after_action_id
    )
    
    # If inserting at beginning or after, need to shift existing actions
    if insert_position in ['beginning', 'after']:
        actions = maintenance_struct.actions
        if insert_position == 'beginning':
            # Shift all actions up by 1
            for action in actions:
                action.sequence_order += 1
            sequence_order = 1
        else:  # after
            # Shift actions after target down by 1
            target_sequence = None
            for action in actions:
                if action.id == after_action_id:
                    target_sequence = action.sequence_order
                    break
            if target_sequence is not None:
                for action in actions:
                    if action.sequence_order > target_sequence:
                        action.sequence_order += 1
                sequence_order = target_sequence + 1
    
    return maintenance_struct, sequence_order


@maintenance_event_bp.route('/<int:event_id>/create-blank-action', methods=['POST'])
@login_required
def create_blank_action(event_id):
    """Create a blank action for maintenance event"""
    try:
        # ===== FORM PARSING SECTION =====
        action_name = request.form.get('actionName', '').strip()
        description = request.form.get('actionDescription', '').strip()
        estimated_duration_str = request.form.get('estimatedDuration', '').strip()
        expected_billable_hours_str = request.form.get('expectedBillableHours', '').strip()
        safety_notes = request.form.get('safetyNotes', '').strip()
        notes = request.form.get('notes', '').strip()
        
        # Insert position
        insert_position = request.form.get('insertPosition', 'end').strip()
        after_action_id_str = request.form.get('afterActionId', '').strip()
        
        # ===== LIGHT VALIDATION SECTION =====
        if not action_name:
            flash('Action name is required', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        if insert_position not in ['end', 'beginning', 'after']:
            flash('Invalid insert position', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        if insert_position == 'after' and not after_action_id_str:
            flash('After action ID is required when inserting after a specific action', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # ===== DATA TYPE CONVERSION SECTION =====
        after_action_id = None
        if after_action_id_str:
            try:
                after_action_id = int(after_action_id_str)
            except ValueError:
                pass
        
        estimated_duration = None
        if estimated_duration_str:
            try:
                estimated_duration = float(estimated_duration_str)
            except ValueError:
                pass
        
        expected_billable_hours = None
        if expected_billable_hours_str:
            try:
                expected_billable_hours = float(expected_billable_hours_str)
            except ValueError:
                pass
        
        # ===== BUSINESS LOGIC SECTION =====
        maintenance_struct, sequence_order = _create_action_common_logic(
            event_id, action_name, description, estimated_duration, expected_billable_hours,
            safety_notes, notes, insert_position, after_action_id, False, False
        )
        
        if not maintenance_struct:
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # Create blank action
        action = Action(
            maintenance_action_set_id=maintenance_struct.maintenance_action_set_id,
            sequence_order=sequence_order,
            action_name=action_name,
            description=description if description else None,
            estimated_duration=estimated_duration,
            expected_billable_hours=expected_billable_hours,
            safety_notes=safety_notes if safety_notes else None,
            notes=notes if notes else None,
            status='Not Started',
            created_by_id=current_user.id,
            updated_by_id=current_user.id
        )
        db.session.add(action)
        db.session.commit()
        
        # Generate automated comment
        if maintenance_struct.event_id:
            event_context = EventContext(maintenance_struct.event_id)
            comment_text = f"Action created: '{action.action_name}' by {current_user.username}"
            event_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=False  # Automated comment
            )
            db.session.commit()
        
        flash('Action created successfully', 'success')
        return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error creating blank action: {e}")
        traceback.print_exc()
        flash('Error creating action', 'error')
        return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))


@maintenance_event_bp.route('/<int:event_id>/create-from-proto-action', methods=['POST'])
@login_required
def create_from_proto_action(event_id):
    """Create an action from a proto action item"""
    try:
        # ===== FORM PARSING SECTION =====
        action_name = request.form.get('actionName', '').strip()
        description = request.form.get('actionDescription', '').strip()
        estimated_duration_str = request.form.get('estimatedDuration', '').strip()
        expected_billable_hours_str = request.form.get('expectedBillableHours', '').strip()
        safety_notes = request.form.get('safetyNotes', '').strip()
        notes = request.form.get('notes', '').strip()
        
        # Source references
        proto_action_item_id_str = request.form.get('proto_action_item_id', '').strip()
        
        # Insert position
        insert_position = request.form.get('insertPosition', 'end').strip()
        after_action_id_str = request.form.get('afterActionId', '').strip()
        
        # Copy options
        copy_part_demands = request.form.get('copyPartDemands', 'false').strip().lower() == 'true'
        copy_tools = request.form.get('copyTools', 'false').strip().lower() == 'true'
        
        # ===== LIGHT VALIDATION SECTION =====
        if not proto_action_item_id_str:
            logger.warning(f"Proto action item ID missing in form data. Form data: {dict(request.form)}")
            flash('Proto action item ID is required', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        if insert_position not in ['end', 'beginning', 'after']:
            flash('Invalid insert position', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        if insert_position == 'after' and not after_action_id_str:
            flash('After action ID is required when inserting after a specific action', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # ===== DATA TYPE CONVERSION SECTION =====
        proto_action_item_id = None
        if proto_action_item_id_str:
            try:
                proto_action_item_id = int(proto_action_item_id_str)
            except ValueError:
                flash('Invalid proto action item ID', 'error')
                return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        after_action_id = None
        if after_action_id_str:
            try:
                after_action_id = int(after_action_id_str)
            except ValueError:
                pass
        
        estimated_duration = None
        if estimated_duration_str:
            try:
                estimated_duration = float(estimated_duration_str)
            except ValueError:
                pass
        
        expected_billable_hours = None
        if expected_billable_hours_str:
            try:
                expected_billable_hours = float(expected_billable_hours_str)
            except ValueError:
                pass
        
        # ===== BUSINESS LOGIC SECTION =====
        maintenance_struct, sequence_order = _create_action_common_logic(
            event_id, action_name, description, estimated_duration, expected_billable_hours,
            safety_notes, notes, insert_position, after_action_id, copy_part_demands, copy_tools
        )
        
        if not maintenance_struct:
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # Create action from proto using ActionFactory
        action = ActionFactory.create_from_proto_action_item(
            proto_action_item_id=proto_action_item_id,
            maintenance_action_set_id=maintenance_struct.maintenance_action_set_id,
            sequence_order=sequence_order,
            user_id=current_user.id,
            commit=False,
            copy_part_demands=copy_part_demands,
            copy_tools=copy_tools,
            action_name=action_name,
            description=description,
            estimated_duration=estimated_duration,
            expected_billable_hours=expected_billable_hours,
            safety_notes=safety_notes,
            notes=notes
        )
        
        db.session.commit()
        
        # Generate automated comment
        if maintenance_struct.event_id:
            event_context = EventContext(maintenance_struct.event_id)
            comment_text = f"Action created from proto: '{action.action_name}' by {current_user.username}"
            event_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=False  # Automated comment
            )
            db.session.commit()
        
        flash('Action created successfully', 'success')
        return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error creating action from proto: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        traceback.print_exc()
        flash(f'Error creating action from proto: {str(e)}', 'error')
        return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))


@maintenance_event_bp.route('/<int:event_id>/create-from-template-action', methods=['POST'])
@login_required
def create_from_template_action(event_id):
    """Create an action from a template action item"""
    try:
        # ===== FORM PARSING SECTION =====
        action_name = request.form.get('actionName', '').strip()
        description = request.form.get('actionDescription', '').strip()
        estimated_duration_str = request.form.get('estimatedDuration', '').strip()
        expected_billable_hours_str = request.form.get('expectedBillableHours', '').strip()
        safety_notes = request.form.get('safetyNotes', '').strip()
        notes = request.form.get('notes', '').strip()
        
        # Source references
        template_action_item_id_str = request.form.get('template_action_item_id', '').strip()
        
        # Insert position
        insert_position = request.form.get('insertPosition', 'end').strip()
        after_action_id_str = request.form.get('afterActionId', '').strip()
        
        # Copy options
        copy_part_demands = request.form.get('copyPartDemands', 'false').strip().lower() == 'true'
        copy_tools = request.form.get('copyTools', 'false').strip().lower() == 'true'
        
        # ===== LIGHT VALIDATION SECTION =====
        if not template_action_item_id_str:
            flash('Template action item ID is required', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        if insert_position not in ['end', 'beginning', 'after']:
            flash('Invalid insert position', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        if insert_position == 'after' and not after_action_id_str:
            flash('After action ID is required when inserting after a specific action', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # ===== DATA TYPE CONVERSION SECTION =====
        template_action_item_id = None
        if template_action_item_id_str:
            try:
                template_action_item_id = int(template_action_item_id_str)
            except ValueError:
                flash('Invalid template action item ID', 'error')
                return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        after_action_id = None
        if after_action_id_str:
            try:
                after_action_id = int(after_action_id_str)
            except ValueError:
                pass
        
        estimated_duration = None
        if estimated_duration_str:
            try:
                estimated_duration = float(estimated_duration_str)
            except ValueError:
                pass
        
        expected_billable_hours = None
        if expected_billable_hours_str:
            try:
                expected_billable_hours = float(expected_billable_hours_str)
            except ValueError:
                pass
        
        # ===== BUSINESS LOGIC SECTION =====
        maintenance_struct, sequence_order = _create_action_common_logic(
            event_id, action_name, description, estimated_duration, expected_billable_hours,
            safety_notes, notes, insert_position, after_action_id, copy_part_demands, copy_tools
        )
        
        if not maintenance_struct:
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # Create action from template using ActionFactory
        action = ActionFactory.create_from_template_action_item(
            template_action_item_id=template_action_item_id,
            maintenance_action_set_id=maintenance_struct.maintenance_action_set_id,
            user_id=current_user.id,
            commit=False,
            copy_part_demands=copy_part_demands,
            copy_tools=copy_tools
        )
        # Update sequence order (factory uses template's sequence_order, but we may need a different one)
        action.sequence_order = sequence_order
        
        db.session.commit()
        
        # Generate automated comment
        if maintenance_struct.event_id:
            event_context = EventContext(maintenance_struct.event_id)
            comment_text = f"Action created from template: '{action.action_name}' by {current_user.username}"
            event_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=False  # Automated comment
            )
            db.session.commit()
        
        flash('Action created successfully', 'success')
        return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error creating action from template: {e}")
        traceback.print_exc()
        flash('Error creating action', 'error')
        return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))


@maintenance_event_bp.route('/<int:event_id>/create-from-current-action', methods=['POST'])
@login_required
def create_from_current_action(event_id):
    """Create an action by duplicating from a current action in the same maintenance event"""
    try:
        # ===== FORM PARSING SECTION =====
        action_name = request.form.get('actionName', '').strip()
        description = request.form.get('actionDescription', '').strip()
        estimated_duration_str = request.form.get('estimatedDuration', '').strip()
        expected_billable_hours_str = request.form.get('expectedBillableHours', '').strip()
        safety_notes = request.form.get('safetyNotes', '').strip()
        notes = request.form.get('notes', '').strip()
        
        # Source references
        source_action_id_str = request.form.get('source_action_id', '').strip()
        
        # Insert position
        insert_position = request.form.get('insertPosition', 'end').strip()
        after_action_id_str = request.form.get('afterActionId', '').strip()
        
        # Copy options
        copy_part_demands = request.form.get('copyPartDemands', 'false').strip().lower() == 'true'
        copy_tools = request.form.get('copyTools', 'false').strip().lower() == 'true'
        
        # ===== LIGHT VALIDATION SECTION =====
        if not source_action_id_str:
            flash('Source action ID is required', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        if insert_position not in ['end', 'beginning', 'after']:
            flash('Invalid insert position', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        if insert_position == 'after' and not after_action_id_str:
            flash('After action ID is required when inserting after a specific action', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # ===== DATA TYPE CONVERSION SECTION =====
        source_action_id = None
        if source_action_id_str:
            try:
                source_action_id = int(source_action_id_str)
            except ValueError:
                flash('Invalid source action ID', 'error')
                return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        after_action_id = None
        if after_action_id_str:
            try:
                after_action_id = int(after_action_id_str)
            except ValueError:
                pass
        
        estimated_duration = None
        if estimated_duration_str:
            try:
                estimated_duration = float(estimated_duration_str)
            except ValueError:
                pass
        
        expected_billable_hours = None
        if expected_billable_hours_str:
            try:
                expected_billable_hours = float(expected_billable_hours_str)
            except ValueError:
                pass
        
        # ===== BUSINESS LOGIC SECTION =====
        maintenance_struct, sequence_order = _create_action_common_logic(
            event_id, action_name, description, estimated_duration, expected_billable_hours,
            safety_notes, notes, insert_position, after_action_id, copy_part_demands, copy_tools
        )
        
        if not maintenance_struct:
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        source_action = Action.query.get_or_404(source_action_id)
        if source_action.maintenance_action_set_id != maintenance_struct.maintenance_action_set_id:
            flash('Source action does not belong to this maintenance event', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # Create duplicate action
        action = Action(
            maintenance_action_set_id=maintenance_struct.maintenance_action_set_id,
            template_action_item_id=source_action.template_action_item_id,
            sequence_order=sequence_order,
            action_name=action_name or source_action.action_name,
            description=description or source_action.description,
            estimated_duration=estimated_duration if estimated_duration is not None else source_action.estimated_duration,
            expected_billable_hours=expected_billable_hours if expected_billable_hours is not None else source_action.expected_billable_hours,
            safety_notes=safety_notes or source_action.safety_notes,
            notes=notes or source_action.notes,
            status='Not Started',  # Reset status
            created_by_id=current_user.id,
            updated_by_id=current_user.id
        )
        db.session.add(action)
        db.session.flush()
        
        # Copy part demands and tools if requested
        if copy_part_demands:
            for source_part_demand in source_action.part_demands:
                part_demand = PartDemand(
                    action_id=action.id,
                    part_id=source_part_demand.part_id,
                    quantity_required=source_part_demand.quantity_required,
                    notes=source_part_demand.notes,
                    expected_cost=source_part_demand.expected_cost,
                    status='Planned',  # Reset status
                    priority=source_part_demand.priority,
                    sequence_order=source_part_demand.sequence_order,
                    created_by_id=current_user.id,
                    updated_by_id=current_user.id
                )
                db.session.add(part_demand)
        
        if copy_tools:
            for source_tool in source_action.action_tools:
                action_tool = ActionTool(
                    action_id=action.id,
                    tool_id=source_tool.tool_id,
                    quantity_required=source_tool.quantity_required,
                    notes=source_tool.notes,
                    status='Planned',  # Reset status
                    priority=source_tool.priority,
                    sequence_order=source_tool.sequence_order,
                    created_by_id=current_user.id,
                    updated_by_id=current_user.id
                )
                db.session.add(action_tool)
        
        db.session.commit()
        
        # Generate automated comment
        if maintenance_struct.event_id:
            event_context = EventContext(maintenance_struct.event_id)
            comment_text = f"Action duplicated: '{action.action_name}' by {current_user.username}"
            event_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=False  # Automated comment
            )
            db.session.commit()
        
        flash('Action created successfully', 'success')
        return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error creating action from current action: {e}")
        traceback.print_exc()
        flash('Error creating action', 'error')
        return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))

@maintenance_event_bp.route('/<int:event_id>/assign', methods=['GET', 'POST'])
@login_required
def assign_event(event_id):
    """
    Assign or reassign maintenance event to technician.
    GET: Show assignment form
    POST: Process assignment (refreshes page and opens view in new tab)
    """
    logger.info(f"Assigning maintenance event for event_id={event_id}")
    
    try:
        # Get the event
        event = Event.query.get(event_id)
        if not event:
            logger.warning(f"Event {event_id} not found")
            abort(404)
        
        # Get the maintenance action set by event_id (ONE-TO-ONE relationship)
        maintenance_context = MaintenanceContext.from_event(event_id)
        maintenance_struct = maintenance_context.struct
        
        if not maintenance_struct:
            logger.warning(f"No maintenance action set found for event_id={event_id}")
            abort(404)
        
        if request.method == 'GET':
            # Get technicians for dropdown
            technicians, _ = AssignMonitorService.get_available_technicians()
            
            # Get assignment history (from comments)
            assignment_history = []
            if maintenance_context.event_context:
                comments = maintenance_context.event_context.comments
                # Filter comments that mention assignment
                for comment in comments:
                    if 'Assigned to' in comment.content or 'assigned' in comment.content.lower():
                        assignment_history.append({
                            'created_at': comment.created_at.isoformat() if comment.created_at else None,
                            'created_by': comment.created_by.username if comment.created_by else None,
                            'content': comment.content,
                        })
            
            return render_template(
                'maintenance/base/maintenance_event/assign.html',
                maintenance=maintenance_struct,
                maintenance_context=maintenance_context,
                event=event,
                technicians=technicians,
                assignment_history=assignment_history,
            )
        
        # POST: Process assignment
        try:
            assigned_user_id = request.form.get('assigned_user_id', type=int)
            notes = request.form.get('notes', '').strip() or None
            
            # Get optional fields
            planned_start_str = request.form.get('planned_start_datetime')
            planned_start_datetime = None
            if planned_start_str:
                try:
                    planned_start_datetime = datetime.fromisoformat(planned_start_str.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    pass
            
            priority = request.form.get('priority')
            
            # Validate required fields
            if not assigned_user_id:
                flash('Technician is required', 'error')
                return redirect(url_for('maintenance_event.assign_event', event_id=event_id))
            
            # Assign event
            AssignMonitorService.assign_event(
                event_id=event_id,
                assigned_user_id=assigned_user_id,
                assigned_by_id=current_user.id,
                planned_start_datetime=planned_start_datetime,
                priority=priority,
                notes=notes
            )
            
            flash('Event assigned successfully', 'success')
            
            # Redirect back to assign page with success parameter
            # JavaScript in template will open view page in new tab
            return redirect(url_for('maintenance_event.assign_event', event_id=event_id, assigned='true'))
            
        except ValueError as e:
            logger.warning(f"Validation error assigning event: {e}")
            flash(str(e), 'error')
            return redirect(url_for('maintenance_event.assign_event', event_id=event_id))
        except Exception as e:
            logger.error(f"Error assigning event: {e}")
            flash('Error assigning event. Please try again.', 'error')
            return redirect(url_for('maintenance_event.assign_event', event_id=event_id))
            
    except ImportError as e:
        logger.error(f"Could not import maintenance modules: {e}")
        abort(500)
    except Exception as e:
        logger.error(f"Error in assign event {event_id}: {e}")
        abort(500)


@maintenance_event_bp.route('/<int:event_id>/edit', methods=['GET'])
@login_required
def render_edit_page(event_id):
    """Render the edit maintenance event page"""
    logger.info(f"Rendering edit page for event_id={event_id}")
    
    try:
        # Get the maintenance action set by event_id (ONE-TO-ONE relationship)
        maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
        
        if not maintenance_struct:
            logger.warning(f"No maintenance action set found for event_id={event_id}")
            abort(404)
        
        # Get the event
        event = Event.query.get(event_id)
        if not event:
            logger.warning(f"Event {event_id} not found")
            abort(404)
        
        # Get actions with their structs (ordered by sequence_order)
        action_structs = [ActionStruct(action) for action in sorted(maintenance_struct.actions, key=lambda a: a.sequence_order)]
        
        # Get selected action ID from query parameter (for action editor panel)
        selected_action_id = request.args.get('action_id', type=int)
        selected_action_struct = None
        if selected_action_id and action_structs:
            selected_action_struct = next((a for a in action_structs if a.action_id == selected_action_id), None)
        # Default to first action if none selected or invalid
        if not selected_action_struct and action_structs:
            selected_action_struct = action_structs[0]
        
        # Get related data for dropdowns
        assets = Asset.query.order_by(Asset.name).all()
        maintenance_plans = MaintenancePlan.query.order_by(MaintenancePlan.name).all()
        
        # Get blockers
        blockers = maintenance_struct.blockers
        active_blockers = [d for d in blockers if d.end_date is None]
        
        # Get parts and tools for dropdowns
        parts = PartDefinition.query.filter_by(status='Active').order_by(PartDefinition.part_name).all()
        tools = ToolDefinition.query.order_by(ToolDefinition.tool_name).all()
        users = User.query.order_by(User.username).all()
        
        # Get maintenance context for summaries
        maintenance_context = MaintenanceContext.from_event(event_id)
        
        return render_template(
            'maintenance/base/edit_maintenance_event.html',
            maintenance=maintenance_struct,
            maintenance_context=maintenance_context,
            event=event,
            actions=action_structs,
            selected_action=selected_action_struct,
            assets=assets,
            maintenance_plans=maintenance_plans,
            blockers=blockers,
            active_blockers=active_blockers,
            parts=parts,
            tools=tools,
            users=users,
        )
        
    except ImportError as e:
        logger.error(f"Could not import maintenance modules: {e}")
        abort(500)
    except Exception as e:
        logger.error(f"Error rendering edit page for event {event_id}: {e}")
        abort(500)


@maintenance_event_bp.route('/<int:event_id>/edit', methods=['POST'])
@login_required
def edit_template_action_set(event_id):
    """Update maintenance action set details"""
    logger.info(f"Updating maintenance action set for event_id={event_id}")
    
    try:
        # Get the maintenance action set by event_id (ONE-TO-ONE relationship)
        maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
        
        if not maintenance_struct:
            logger.warning(f"No maintenance action set found for event_id={event_id}")
            abort(404)
        
        # Get the event
        event = Event.query.get(event_id)
        if not event:
            logger.warning(f"Event {event_id} not found")
            abort(404)
        
        # ===== FORM PARSING SECTION =====
        task_name = request.form.get('task_name', '').strip()
        description = request.form.get('description', '').strip()
        estimated_duration_str = request.form.get('estimated_duration', '').strip()
        status = request.form.get('status', '').strip()
        priority = request.form.get('priority', '').strip()
        planned_start_datetime_str = request.form.get('planned_start_datetime', '').strip()
        start_date_str = request.form.get('start_date', '').strip()
        end_date_str = request.form.get('end_date', '').strip()
        safety_review_required_str = request.form.get('safety_review_required', '').strip()
        staff_count_str = request.form.get('staff_count', '').strip()
        labor_hours_str = request.form.get('labor_hours', '').strip()
        parts_cost_str = request.form.get('parts_cost', '').strip()
        actual_billable_hours_str = request.form.get('actual_billable_hours', '').strip()
        assigned_user_id_str = request.form.get('assigned_user_id', '').strip()
        assigned_by_id_str = request.form.get('assigned_by_id', '').strip()
        completed_by_id_str = request.form.get('completed_by_id', '').strip()
        completion_notes = request.form.get('completion_notes', '').strip()
        blocker_notes = request.form.get('delay_notes', '').strip()  # Keep form field name for backward compatibility
        
        # ===== DATA TYPE CONVERSION SECTION =====
        # Convert description (string or None)
        description = description if description else None
        
        # Convert estimated_duration (float)
        # Allow None/empty to clear the field
        estimated_duration = None
        if estimated_duration_str:
            try:
                estimated_duration = float(estimated_duration_str)
                if estimated_duration < 0:
                    flash('Estimated duration must be non-negative', 'error')
                    return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
            except ValueError:
                flash('Invalid estimated duration', 'error')
                return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        # If empty string, estimated_duration stays None (will clear the field via nullable_fields logic)
        
        # Convert staff_count (integer)
        staff_count = None
        if staff_count_str:
            try:
                staff_count = int(staff_count_str)
            except ValueError:
                flash('Invalid staff count', 'error')
                return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # Convert labor_hours (float)
        labor_hours = None
        if labor_hours_str:
            try:
                labor_hours = float(labor_hours_str)
            except ValueError:
                flash('Invalid labor hours', 'error')
                return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # Convert parts_cost (float)
        parts_cost = None
        if parts_cost_str:
            try:
                parts_cost = float(parts_cost_str)
            except ValueError:
                flash('Invalid parts cost', 'error')
                return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # Convert actual_billable_hours (float)
        actual_billable_hours = None
        if actual_billable_hours_str:
            try:
                actual_billable_hours = float(actual_billable_hours_str)
            except ValueError:
                flash('Invalid actual billable hours', 'error')
                return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # Convert planned_start_datetime (datetime)
        planned_start_datetime = None
        if planned_start_datetime_str:
            try:
                planned_start_datetime = datetime.strptime(planned_start_datetime_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid planned start datetime format', 'error')
                return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # Convert start_date (datetime)
        start_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid start date format', 'error')
                return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # Convert end_date (datetime)
        end_date = None
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid end date format', 'error')
                return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # Convert assigned_user_id (integer)
        assigned_user_id = None
        if assigned_user_id_str:
            try:
                assigned_user_id = int(assigned_user_id_str)
            except ValueError:
                flash('Invalid assigned user ID', 'error')
                return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # Convert assigned_by_id (integer)
        assigned_by_id = None
        if assigned_by_id_str:
            try:
                assigned_by_id = int(assigned_by_id_str)
            except ValueError:
                flash('Invalid assigned by ID', 'error')
                return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # Convert completed_by_id (integer)
        completed_by_id = None
        if completed_by_id_str:
            try:
                completed_by_id = int(completed_by_id_str)
            except ValueError:
                flash('Invalid completed by ID', 'error')
                return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # Convert safety_review_required (boolean)
        safety_review_required = safety_review_required_str == 'on'
        
        # Convert completion_notes (string or None)
        completion_notes = completion_notes if completion_notes else None
        
        # Convert blocker_notes (string or None)
        blocker_notes = blocker_notes if blocker_notes else None
        
        # ===== BUSINESS LOGIC SECTION =====
        maintenance_context = MaintenanceContext.from_event(event_id)
        maintenance_context.update_action_set_details(
            task_name=task_name,
            description=description,
            estimated_duration=estimated_duration,  # Can be None to clear the field
            status=status,
            priority=priority,
            planned_start_datetime=planned_start_datetime,
            start_date=start_date,
            end_date=end_date,
            safety_review_required=safety_review_required,
            staff_count=staff_count,
            labor_hours=labor_hours,
            parts_cost=parts_cost,
            actual_billable_hours=actual_billable_hours,
            assigned_user_id=assigned_user_id,
            assigned_by_id=assigned_by_id,
            completed_by_id=completed_by_id,
            completion_notes=completion_notes,
            blocker_notes=blocker_notes
        )
        
        flash('Maintenance event updated successfully', 'success')
        # Reload the page (redirect back to edit page)
        return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
    except ImportError as e:
        logger.error(f"Could not import maintenance modules: {e}")
        abort(500)
    except Exception as e:
        logger.error(f"Error updating maintenance action set for event {event_id}: {e}")
        abort(500)



@maintenance_event_bp.route('/<int:event_id>/update-datetime', methods=['POST'])
@login_required
def update_maintenance_datetime(event_id):
    """Update maintenance start/end dates"""
    try:
        # ===== FORM PARSING SECTION =====
        start_date_str = request.form.get('start_date', '').strip()
        end_date_str = request.form.get('end_date', '').strip()
        
        # ===== DATA TYPE CONVERSION SECTION =====
        start_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid start date format', 'error')
                return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        end_date = None
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid end date format', 'error')
                return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        # ===== LIGHT VALIDATION SECTION =====
        # Validate: end_date must be after start_date
        if end_date and start_date and end_date < start_date:
            flash('End date must be after start date', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        # ===== BUSINESS LOGIC SECTION =====
        maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
        if not maintenance_struct:
            abort(404)
        
        if start_date:
            maintenance_struct.maintenance_action_set.start_date = start_date
        if end_date:
            maintenance_struct.maintenance_action_set.end_date = end_date
        
        db.session.commit()
        flash('Maintenance dates updated', 'success')
        return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error updating maintenance datetime: {e}")
        flash('Error updating maintenance dates', 'error')
        return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))


@maintenance_event_bp.route('/<int:event_id>/update-billable-hours', methods=['POST'])
@login_required
def update_maintenance_billable_hours(event_id):
    """Update maintenance total billable hours"""
    try:
        # ===== FORM PARSING SECTION =====
        billable_hours_str = request.form.get('actual_billable_hours', '').strip()
        
        # ===== LIGHT VALIDATION SECTION =====
        if not billable_hours_str:
            flash('Billable hours is required', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        # ===== DATA TYPE CONVERSION SECTION =====
        try:
            billable_hours = float(billable_hours_str)
        except ValueError:
            flash('Invalid billable hours value', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        # ===== BUSINESS LOGIC SECTION =====
        maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
        if not maintenance_struct:
            abort(404)
        
        maintenance_context = MaintenanceContext.from_event(event_id)
        try:
            billable_hours_manager = maintenance_context.get_billable_hours_manager()
            billable_hours_manager.set_actual_hours(billable_hours, user_id=current_user.id)
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        flash('Maintenance billable hours updated', 'success')
        return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error updating maintenance billable hours: {e}")
        flash('Error updating billable hours', 'error')
        return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))


@maintenance_event_bp.route('/<int:event_id>/complete', methods=['POST'])
@login_required
def complete_maintenance(event_id):
    """Complete maintenance event with validation"""
    try:
        # ===== FORM PARSING SECTION =====
        completion_comment = request.form.get('completion_comment', '').strip()
        start_date_str = request.form.get('actual_start_date', '').strip()
        end_date_str = request.form.get('actual_end_date', '').strip()
        billable_hours_str = request.form.get('actual_billable_hours', '').strip()
        
        # Extract meter values (can be empty strings, which become None)
        meter1_str = request.form.get('meter1', '').strip()
        meter2_str = request.form.get('meter2', '').strip()
        meter3_str = request.form.get('meter3', '').strip()
        meter4_str = request.form.get('meter4', '').strip()
        meter_verification_toggle = request.form.get('meter_verification_toggle')
        
        # ===== LIGHT VALIDATION SECTION =====
        if not completion_comment:
            flash('Completion comment is required', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        if not start_date_str or not end_date_str:
            flash('Both start and end dates are required', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        if not billable_hours_str:
            flash('Billable hours is required', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        # ===== DATA TYPE CONVERSION SECTION =====
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date format', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        try:
            billable_hours = float(billable_hours_str)
        except ValueError:
            flash('Invalid billable hours value', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        # Additional validation after conversion
        if end_date < start_date:
            flash('End date must be after start date', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        if billable_hours < 0.2:
            flash('Billable hours must be at least 0.2 hours (12 minutes)', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        # ===== METER VALIDATION SECTION =====
        # Validate meter verification toggle is checked
        if not meter_verification_toggle:
            flash('Meter verification is required. Please confirm the meters are correct.', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        # Convert meter strings to floats (None if empty or invalid)
        try:
            meter1 = float(meter1_str) if meter1_str else None
        except (ValueError, TypeError):
            meter1 = None
            
        try:
            meter2 = float(meter2_str) if meter2_str else None
        except (ValueError, TypeError):
            meter2 = None
            
        try:
            meter3 = float(meter3_str) if meter3_str else None
        except (ValueError, TypeError):
            meter3 = None
            
        try:
            meter4 = float(meter4_str) if meter4_str else None
        except (ValueError, TypeError):
            meter4 = None
        
        # Validate that at least one meter is provided (validation happens in AssetContext.update_meters)
        # All four meters are explicitly passed (even if None) to MaintenanceContext.complete()
        
        # ===== BUSINESS LOGIC SECTION =====
        maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
        if not maintenance_struct:
            abort(404)
        
        # Check all actions are in terminal states
        blocked_actions = [a for a in maintenance_struct.actions if a.status == 'Blocked']
        if blocked_actions:
            flash('Cannot complete maintenance. Please resolve all blocked actions first.', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        # Update maintenance using context manager
        maintenance_context = MaintenanceContext.from_event(event_id)
        # Set start_date and billable hours before completing
        maintenance_struct.maintenance_action_set.start_date = start_date
        billable_hours_manager = maintenance_context.get_billable_hours_manager()
        billable_hours_manager.set_actual_hours(billable_hours, user_id=current_user.id)
        # Use complete() method which will sync Event.status and handle meter verification
        maintenance_context.complete(
            user_id=current_user.id,
            notes=completion_comment,
            meter1=meter1,
            meter2=meter2,
            meter3=meter3,
            meter4=meter4
        )
        # Set end_date after complete() to preserve form value (complete() sets it to utcnow())
        maintenance_struct.maintenance_action_set.end_date = end_date
        db.session.commit()
        
        # Generate automated completion comment
        if maintenance_struct.event_id:
            event_context = EventContext(maintenance_struct.event_id)
            comment_text = f"Maintenance completed by {current_user.username}. {completion_comment}"
            event_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=False  # Automated comment
            )
            db.session.commit()
        
        flash('Maintenance completed successfully', 'success')
        return redirect(url_for('maintenance_event.view_maintenance_event', event_id=event_id))
        
    except ValueError as e:
        # Handle meter validation errors specifically
        error_message = str(e)
        if 'meter' in error_message.lower() or 'verification' in error_message.lower():
            flash(f'Meter verification failed: {error_message}', 'error')
        else:
            flash(f'Validation error: {error_message}', 'error')
        logger.warning(f"Meter validation failed for event {event_id}: {e}")
        return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error completing maintenance: {e}", exc_info=True)
        flash('Error completing maintenance', 'error')
        return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))


@maintenance_event_bp.route('/<int:event_id>/blocker/create', methods=['POST'])
@login_required
def create_blocker(event_id):
    """Create a blocked status for maintenance event"""
    try:
        # ===== FORM PARSING SECTION =====
        mission_capability_status = request.form.get('mission_capability_status', '').strip()
        reason = request.form.get('reason', '').strip()
        notes = request.form.get('notes', '').strip()
        start_time_str = request.form.get('start_time', '').strip()
        billable_hours_lost_str = request.form.get('billable_hours_lost', '').strip()
        event_priority = request.form.get('event_priority', '').strip()
        comment_to_add_to_event = request.form.get('comment_to_add_to_event', '').strip()
        
        # ===== LIGHT VALIDATION SECTION =====
        blocker_instance = MaintenanceBlocker()  # Temporary instance to access properties
        allowable_statuses = blocker_instance.allowable_capability_statuses
        allowable_reasons = blocker_instance.allowable_reasons
        
        if not mission_capability_status or mission_capability_status not in allowable_statuses:
            flash('Valid mission capability status is required', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        if not reason or reason not in allowable_reasons:
            flash('Valid reason is required', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        # ===== DATA TYPE CONVERSION SECTION =====
        start_time = None
        if start_time_str:
            try:
                start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid start time format', 'error')
                return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        billable_hours_lost = None
        if billable_hours_lost_str:
            try:
                billable_hours_lost = float(billable_hours_lost_str)
                if billable_hours_lost < 0:
                    flash('Billable hours lost must be non-negative', 'error')
                    return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
            except ValueError:
                pass  # Ignore invalid values
        
        # ===== BUSINESS LOGIC SECTION =====
        maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
        if not maintenance_struct:
            abort(404)
        
        # Check if there's already an active blocker
        active_blockers = [d for d in maintenance_struct.blockers if d.end_date is None]
        if active_blockers:
            flash('An active blocked status already exists. Please end the current blocker before creating a new one.', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        # Create blocker using blocker manager
        maintenance_context = MaintenanceContext(maintenance_struct)
        blocker_manager = maintenance_context.get_blocker_manager()
        blocker = blocker_manager.add_blocker(
            mission_capability_status=mission_capability_status,
            reason=reason,
            notes=notes,
            start_time=start_time,
            billable_hours_lost=billable_hours_lost,
            user_id=current_user.id
        )
        
        # Sync event status
        maintenance_context._sync_event_status()
        
        # Update event priority if provided
        if event_priority and event_priority in ['Low', 'Medium', 'High', 'Critical']:
            maintenance_context.update_action_set_details(priority=event_priority)
        
        # Update asset blocked status based on all active blockers
        blocker_manager.update_asset_blocked_status()
        
        # Generate comment - use user's comment if provided, otherwise use automated one
        if maintenance_struct.event_id:
            event_context = EventContext(maintenance_struct.event_id)
            if comment_to_add_to_event:
                comment_text = comment_to_add_to_event
                is_human_made = True
            else:
                comment_text = f"Blocked status created: {mission_capability_status} by {current_user.username}. Reason: {reason}"
                is_human_made = False
            event_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=is_human_made
            )
            db.session.commit()
        
        flash('Blocked status created successfully', 'success')
        return redirect(url_for('maintenance_event.view_maintenance_event', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error creating blocked status: {e}")
        import traceback
        traceback.print_exc()
        flash('Error creating blocked status', 'error')
        return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))



