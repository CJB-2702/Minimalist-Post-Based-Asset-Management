"""
Maintenance work and edit routes for maintenance events
"""
import traceback
from datetime import datetime

from flask import Blueprint, render_template, abort, request, flash, redirect, url_for, send_from_directory
from flask_login import login_required, current_user

from app.logger import get_logger
from app.buisness.maintenance.base.structs.action_struct import ActionStruct
from app.buisness.maintenance.base.structs.maintenance_action_set_struct import MaintenanceActionSetStruct
from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
from app.data.core.asset_info.asset import Asset
from app.data.core.event_info.event import Event
from app.data.core.supply.part_definition import PartDefinition
from app.data.core.supply.tool_definition import ToolDefinition
from app.data.core.user_info.user import User
from app.data.maintenance.base.maintenance_blockers import MaintenanceBlocker
from app.data.maintenance.planning.maintenance_plans import MaintenancePlan

logger = get_logger("asset_management.routes.maintenance")

# Create blueprint for maintenance event edit portal
maintenance_event_bp = Blueprint('maintenance_event_edit', __name__, url_prefix='/maintenance/maintenance-event')

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
            return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
        if insert_position not in ['end', 'beginning', 'after']:
            flash('Invalid insert position', 'error')
            return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
        if insert_position == 'after' and not after_action_id_str:
            flash('After action ID is required when inserting after a specific action', 'error')
            return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
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
        maintenance_context = MaintenanceContext.from_event(event_id)
        maintenance_context.get_action_creation_manager().create_blank_action(
            action_name=action_name,
            description=description or None,
            estimated_duration=estimated_duration,
            expected_billable_hours=expected_billable_hours,
            safety_notes=safety_notes or None,
            notes=notes or None,
            insert_position=insert_position,
            after_action_id=after_action_id,
            user_id=current_user.id,
            username=current_user.username,
        )
        
        flash('Action created successfully', 'success')
        return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error creating blank action: {e}")
        traceback.print_exc()
        flash('Error creating action', 'error')
        return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))


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
            from app.utils.logging_sanitizer import sanitize_form_data
            logger.warning(f"Proto action item ID missing in form data. Form data: {sanitize_form_data(request.form)}")
            flash('Proto action item ID is required', 'error')
            return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
        if insert_position not in ['end', 'beginning', 'after']:
            flash('Invalid insert position', 'error')
            return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
        if insert_position == 'after' and not after_action_id_str:
            flash('After action ID is required when inserting after a specific action', 'error')
            return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
        # ===== DATA TYPE CONVERSION SECTION =====
        proto_action_item_id = None
        if proto_action_item_id_str:
            try:
                proto_action_item_id = int(proto_action_item_id_str)
            except ValueError:
                flash('Invalid proto action item ID', 'error')
                return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
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
        maintenance_context = MaintenanceContext.from_event(event_id)
        maintenance_context.get_action_creation_manager().create_from_proto_action_item(
            proto_action_item_id=proto_action_item_id,
            action_name=action_name,
            description=description or None,
            estimated_duration=estimated_duration,
            expected_billable_hours=expected_billable_hours,
            safety_notes=safety_notes or None,
            notes=notes or None,
            insert_position=insert_position,
            after_action_id=after_action_id,
            copy_part_demands=copy_part_demands,
            copy_tools=copy_tools,
            user_id=current_user.id,
            username=current_user.username,
        )
        
        flash('Action created successfully', 'success')
        return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error creating action from proto: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        traceback.print_exc()
        flash(f'Error creating action from proto: {str(e)}', 'error')
        return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))


@maintenance_event_bp.route('/<int:event_id>/create-from-template-action', methods=['POST'])
@login_required
def create_from_template_action(event_id):
    """Create an action from a template action item"""
    try:
        # ===== FORM PARSING SECTION =====
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
            return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
        if insert_position not in ['end', 'beginning', 'after']:
            flash('Invalid insert position', 'error')
            return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
        if insert_position == 'after' and not after_action_id_str:
            flash('After action ID is required when inserting after a specific action', 'error')
            return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
        # ===== DATA TYPE CONVERSION SECTION =====
        template_action_item_id = None
        if template_action_item_id_str:
            try:
                template_action_item_id = int(template_action_item_id_str)
            except ValueError:
                flash('Invalid template action item ID', 'error')
                return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
        after_action_id = None
        if after_action_id_str:
            try:
                after_action_id = int(after_action_id_str)
            except ValueError:
                pass
        
        # ===== BUSINESS LOGIC SECTION =====
        maintenance_context = MaintenanceContext.from_event(event_id)
        maintenance_context.get_action_creation_manager().create_from_template_action_item(
            template_action_item_id=template_action_item_id,
            insert_position=insert_position,
            after_action_id=after_action_id,
            copy_part_demands=copy_part_demands,
            copy_tools=copy_tools,
            user_id=current_user.id,
            username=current_user.username,
        )
        
        flash('Action created successfully', 'success')
        return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error creating action from template: {e}")
        traceback.print_exc()
        flash('Error creating action', 'error')
        return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))


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
            return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
        if insert_position not in ['end', 'beginning', 'after']:
            flash('Invalid insert position', 'error')
            return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
        if insert_position == 'after' and not after_action_id_str:
            flash('After action ID is required when inserting after a specific action', 'error')
            return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
        # ===== DATA TYPE CONVERSION SECTION =====
        source_action_id = None
        if source_action_id_str:
            try:
                source_action_id = int(source_action_id_str)
            except ValueError:
                flash('Invalid source action ID', 'error')
                return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
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
        maintenance_context = MaintenanceContext.from_event(event_id)
        maintenance_context.get_action_creation_manager().duplicate_from_current_action(
            source_action_id=source_action_id,
            action_name=action_name or None,
            description=description or None,
            estimated_duration=estimated_duration,
            expected_billable_hours=expected_billable_hours,
            safety_notes=safety_notes or None,
            notes=notes or None,
            insert_position=insert_position,
            after_action_id=after_action_id,
            copy_part_demands=copy_part_demands,
            copy_tools=copy_tools,
            user_id=current_user.id,
            username=current_user.username,
        )
        
        flash('Action created successfully', 'success')
        return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error creating action from current action: {e}")
        traceback.print_exc()
        flash('Error creating action', 'error')
        return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))



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
        
        # Get limitation records for display
        limitation_records = maintenance_struct.limitation_records if hasattr(maintenance_struct, 'limitation_records') else []
        active_limitations = [lr for lr in limitation_records if lr.is_active]
        
        # Get parts and tools for dropdowns
        parts = PartDefinition.query.filter_by(status='Active').order_by(PartDefinition.part_name).all()
        tools = ToolDefinition.query.order_by(ToolDefinition.tool_name).all()
        users = User.query.order_by(User.username).all()
        
        # Get blocker allowable values for dropdowns
        blocker_instance = MaintenanceBlocker()  # Temporary instance to access properties
        allowable_reasons = blocker_instance.allowable_reasons
        
        # Get limitation allowable values for dropdowns
        from app.data.maintenance.base.asset_limitation_records import AssetLimitationRecord
        limitation_instance = AssetLimitationRecord()  # Temporary instance to access properties
        allowable_limitation_statuses = limitation_instance.allowable_capability_statuses
        
        # Get maintenance context for summaries
        maintenance_context = MaintenanceContext.from_event(event_id)
        
        # Get asset for capability status display
        asset = maintenance_struct.asset
        
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
            limitation_records=limitation_records,
            active_limitations=active_limitations,
            parts=parts,
            tools=tools,
            users=users,
            allowable_reasons=allowable_reasons,
            allowable_limitation_statuses=allowable_limitation_statuses,
            asset=asset,
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
                    return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
            except ValueError:
                flash('Invalid estimated duration', 'error')
                return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        # If empty string, estimated_duration stays None (will clear the field via nullable_fields logic)
        
        # Convert staff_count (integer)
        staff_count = None
        if staff_count_str:
            try:
                staff_count = int(staff_count_str)
            except ValueError:
                flash('Invalid staff count', 'error')
                return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
        # Convert labor_hours (float)
        labor_hours = None
        if labor_hours_str:
            try:
                labor_hours = float(labor_hours_str)
            except ValueError:
                flash('Invalid labor hours', 'error')
                return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
        # Convert parts_cost (float)
        parts_cost = None
        if parts_cost_str:
            try:
                parts_cost = float(parts_cost_str)
            except ValueError:
                flash('Invalid parts cost', 'error')
                return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
        # Convert actual_billable_hours (float)
        actual_billable_hours = None
        if actual_billable_hours_str:
            try:
                actual_billable_hours = float(actual_billable_hours_str)
            except ValueError:
                flash('Invalid actual billable hours', 'error')
                return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
        # Convert planned_start_datetime (datetime)
        planned_start_datetime = None
        if planned_start_datetime_str:
            try:
                planned_start_datetime = datetime.strptime(planned_start_datetime_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid planned start datetime format', 'error')
                return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
        # Convert start_date (datetime)
        start_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid start date format', 'error')
                return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
        # Convert end_date (datetime)
        end_date = None
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid end date format', 'error')
                return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
        # Convert assigned_user_id (integer)
        assigned_user_id = None
        if assigned_user_id_str:
            try:
                assigned_user_id = int(assigned_user_id_str)
            except ValueError:
                flash('Invalid assigned user ID', 'error')
                return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
        # Convert assigned_by_id (integer)
        assigned_by_id = None
        if assigned_by_id_str:
            try:
                assigned_by_id = int(assigned_by_id_str)
            except ValueError:
                flash('Invalid assigned by ID', 'error')
                return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
        # Convert completed_by_id (integer)
        completed_by_id = None
        if completed_by_id_str:
            try:
                completed_by_id = int(completed_by_id_str)
            except ValueError:
                flash('Invalid completed by ID', 'error')
                return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
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
        return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
    except ImportError as e:
        logger.error(f"Could not import maintenance modules: {e}")
        abort(500)
    except Exception as e:
        logger.error(f"Error updating maintenance action set for event {event_id}: {e}")
        abort(500)





@maintenance_event_bp.route('/static/js/edit_maintenance.js')
def serve_edit_maintenance_js():
    """Serve the edit maintenance JavaScript file"""
    import os
    from flask import current_app
    
    # Get the path to the templates directory
    templates_dir = os.path.join(
        current_app.root_path,
        'presentation',
        'templates',
        'maintenance',
        'base',
        'edit_maintenance_components'
    )
    
    return send_from_directory(templates_dir, 'edit_maintenance.js', mimetype='application/javascript')

