"""
Maintenance main routes - Portal splash page
"""
from flask import Blueprint, render_template, abort, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from app.logger import get_logger
from app import db

logger = get_logger("asset_management.routes.maintenance")

# Create maintenance blueprint
maintenance_bp = Blueprint('maintenance', __name__, url_prefix='/maintenance')

@maintenance_bp.route('/')
@maintenance_bp.route('/index')
@login_required
def index():
    """Maintenance portal splash page - Choose between technician, manager, and fleet portals"""
    logger.info("Maintenance splash page accessed")
    
    # Get basic maintenance stats if models are available
    stats = {}
    try:
        from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
        from app.data.maintenance.base.actions import Action
        
        stats = {
            'total_maintenance_events': MaintenanceActionSet.query.count(),
            'in_progress_events': MaintenanceActionSet.query.filter_by(status='In Progress').count(),
            'planned_events': MaintenanceActionSet.query.filter_by(status='Planned').count(),
            'completed_events': MaintenanceActionSet.query.filter_by(status='Complete').count(),
        }
    except ImportError:
        logger.warning("Maintenance models not available")
        stats = {
            'total_maintenance_events': 0,
            'in_progress_events': 0,
            'planned_events': 0,
            'completed_events': 0,
        }
    
    return render_template('maintenance/splash.html', stats=stats)


@maintenance_bp.route('/maintenance-event/<int:event_id>')
@maintenance_bp.route('/maintenance-event/<int:event_id>/view')
@login_required
def view_maintenance_event(event_id):
    """View detailed information about a maintenance event"""
    logger.info(f"Viewing maintenance event for event_id={event_id}")
    
    try:
        from app.buisness.maintenance.base.maintenance_action_set_struct import MaintenanceActionSetStruct
        from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
        from app.buisness.maintenance.base.action_struct import ActionStruct
        from app.data.core.event_info.event import Event
        
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
        
        # Get actions with their structs for convenient access
        action_structs = [ActionStruct(action) for action in maintenance_struct.actions]
        
        # Get context for business logic if needed
        maintenance_context = MaintenanceContext(maintenance_struct)
        
        # Calculate action status counts
        completed_count = sum(1 for a in action_structs if a.action.status == 'Complete')
        in_progress_count = sum(1 for a in action_structs if a.action.status == 'In Progress')
        
        # Get delays for display
        delays = maintenance_struct.delays if hasattr(maintenance_struct, 'delays') else []
        active_delays = [d for d in delays if d.delay_end_date is None]
        
        return render_template(
            'maintenance/view_maintenance_event.html',
            maintenance=maintenance_struct,
            maintenance_context=maintenance_context,
            event=event,
            actions=action_structs,
            completed_count=completed_count,
            in_progress_count=in_progress_count,
            delays=delays,
            active_delays=active_delays,
        )
        
    except ImportError as e:
        logger.error(f"Could not import maintenance modules: {e}")
        abort(500)
    except Exception as e:
        logger.error(f"Error viewing maintenance event {event_id}: {e}")
        abort(500)


@maintenance_bp.route('/maintenance-event/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_maintenance_event(event_id):
    """Edit a maintenance event"""
    logger.info(f"Editing maintenance event for event_id={event_id}")
    
    try:
        from app.buisness.maintenance.base.maintenance_action_set_struct import MaintenanceActionSetStruct
        from app.buisness.maintenance.base.action_struct import ActionStruct
        from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
        from app.data.core.event_info.event import Event
        from app.data.core.asset_info.asset import Asset
        from app.data.maintenance.base.maintenance_plans import MaintenancePlan
        
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
        
        # Handle POST request (form submission)
        if request.method == 'POST':
            maintenance_context = MaintenanceContext(maintenance_struct)
            
            # Parse form data - all fields from VirtualActionSet and MaintenanceActionSet
            task_name = request.form.get('task_name', '').strip()
            description = request.form.get('description', '').strip() or None
            estimated_duration_str = request.form.get('estimated_duration', '').strip()
            asset_id_str = request.form.get('asset_id', '').strip()
            maintenance_plan_id_str = request.form.get('maintenance_plan_id', '').strip()
            status = request.form.get('status', '').strip()
            priority = request.form.get('priority', '').strip()
            planned_start_datetime_str = request.form.get('planned_start_datetime', '').strip()
            safety_review_required = request.form.get('safety_review_required') == 'on'
            staff_count_str = request.form.get('staff_count', '').strip()
            labor_hours_str = request.form.get('labor_hours', '').strip()
            completion_notes = request.form.get('completion_notes', '').strip() or None
            
            # Parse optional numeric fields
            estimated_duration = None
            if estimated_duration_str:
                try:
                    estimated_duration = float(estimated_duration_str)
                except ValueError:
                    flash('Invalid estimated duration', 'error')
                    return redirect(url_for('maintenance.edit_maintenance_event', event_id=event_id))
            
            asset_id = None
            if asset_id_str:
                try:
                    asset_id = int(asset_id_str)
                except ValueError:
                    flash('Invalid asset ID', 'error')
                    return redirect(url_for('maintenance.edit_maintenance_event', event_id=event_id))
            
            maintenance_plan_id = None
            if maintenance_plan_id_str:
                try:
                    maintenance_plan_id = int(maintenance_plan_id_str)
                except ValueError:
                    flash('Invalid maintenance plan ID', 'error')
                    return redirect(url_for('maintenance.edit_maintenance_event', event_id=event_id))
            
            staff_count = None
            if staff_count_str:
                try:
                    staff_count = int(staff_count_str)
                except ValueError:
                    flash('Invalid staff count', 'error')
                    return redirect(url_for('maintenance.edit_maintenance_event', event_id=event_id))
            
            labor_hours = None
            if labor_hours_str:
                try:
                    labor_hours = float(labor_hours_str)
                except ValueError:
                    flash('Invalid labor hours', 'error')
                    return redirect(url_for('maintenance.edit_maintenance_event', event_id=event_id))
            
            # Parse datetime
            planned_start_datetime = None
            if planned_start_datetime_str:
                try:
                    planned_start_datetime = datetime.strptime(planned_start_datetime_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    flash('Invalid planned start datetime format', 'error')
                    return redirect(url_for('maintenance.edit_maintenance_event', event_id=event_id))
            
            # Update maintenance action set details
            maintenance_context.update_action_set_details(
                task_name=task_name,
                description=description,
                estimated_duration=estimated_duration,
                asset_id=asset_id,
                maintenance_plan_id=maintenance_plan_id,
                status=status,
                priority=priority,
                planned_start_datetime=planned_start_datetime,
                safety_review_required=safety_review_required,
                staff_count=staff_count,
                labor_hours=labor_hours,
                completion_notes=completion_notes
            )
            
            flash('Maintenance event updated successfully', 'success')
            # Reload the page (redirect back to edit page)
            return redirect(url_for('maintenance.edit_maintenance_event', event_id=event_id))
        
        # Handle GET request (display form)
        # Get actions with their structs
        action_structs = [ActionStruct(action) for action in maintenance_struct.actions]
        
        # Get related data for dropdowns
        assets = Asset.query.order_by(Asset.name).all()
        maintenance_plans = MaintenancePlan.query.order_by(MaintenancePlan.name).all()
        
        return render_template(
            'maintenance/edit_maintenance_event.html',
            maintenance=maintenance_struct,
            event=event,
            actions=action_structs,
            assets=assets,
            maintenance_plans=maintenance_plans,
        )
        
    except ImportError as e:
        logger.error(f"Could not import maintenance modules: {e}")
        abort(500)
    except Exception as e:
        logger.error(f"Error editing maintenance event {event_id}: {e}")
        abort(500)


@maintenance_bp.route('/maintenance-event/<int:event_id>/work')
@login_required
def work_maintenance_event(event_id):
    """Work on a maintenance event (perform maintenance)"""
    logger.info(f"Working on maintenance event for event_id={event_id}")
    
    try:
        from app.buisness.maintenance.base.maintenance_action_set_struct import MaintenanceActionSetStruct
        from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
        from app.buisness.maintenance.base.action_struct import ActionStruct
        from app.data.core.event_info.event import Event
        
        # Get the maintenance action set by event_id (ONE-TO-ONE relationship)
        maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
        
        if not maintenance_struct:
            logger.warning(f"No maintenance action set found for event_id={event_id}")
            abort(404)
        
        # Check if maintenance is in Delayed status - redirect to view page
        if maintenance_struct.status == 'Delayed':
            flash('Work is paused due to delay. Please end the delay to continue work.', 'warning')
            return redirect(url_for('maintenance.view_maintenance_event', event_id=event_id))
        
        # Get the event
        event = Event.query.get(event_id)
        if not event:
            logger.warning(f"Event {event_id} not found")
            abort(404)
        
        # Get actions with their structs
        action_structs = [ActionStruct(action) for action in maintenance_struct.actions]
        
        # Get context for business logic
        maintenance_context = MaintenanceContext(maintenance_struct)
        
        # Get asset if available
        asset = maintenance_struct.asset if hasattr(maintenance_struct, 'asset') else None
        
        # Get delays for display
        delays = maintenance_struct.delays if hasattr(maintenance_struct, 'delays') else []
        active_delays = [d for d in delays if d.delay_end_date is None]
        
        # Get parts for part demand dropdown
        from app.data.core.supply.part import Part
        from app.data.core.user_info.user import User
        parts = Part.query.filter_by(status='Active').order_by(Part.part_name).all()
        users = User.query.order_by(User.username).all()
        
        # Check if all actions are in terminal states
        all_actions_terminal = maintenance_context.all_actions_in_terminal_states()
        
        return render_template(
            'maintenance/work_maintenance_event.html',
            maintenance=maintenance_struct,
            maintenance_context=maintenance_context,
            event=event,
            actions=action_structs,
            asset=asset,
            delays=delays,
            active_delays=active_delays,
            parts=parts,
            users=users,
            all_actions_terminal=all_actions_terminal,
        )
        
    except ImportError as e:
        logger.error(f"Could not import maintenance modules: {e}")
        abort(500)
    except Exception as e:
        logger.error(f"Error working on maintenance event {event_id}: {e}")
        abort(500)


@maintenance_bp.route('/maintenance-template/<int:template_set_id>')
@maintenance_bp.route('/maintenance-template/<int:template_set_id>/view')
@login_required
def view_maintenance_template(template_set_id):
    """View detailed information about a maintenance template"""
    logger.info(f"Viewing maintenance template for template_set_id={template_set_id}")
    
    try:
        from app.buisness.maintenance.templates.template_action_set_struct import TemplateActionSetStruct
        from app.buisness.maintenance.templates.template_maintenance_context import TemplateMaintenanceContext
        from app.buisness.maintenance.templates.template_action_item_struct import TemplateActionItemStruct
        
        # Get the template action set
        template_struct = TemplateActionSetStruct(template_set_id)
        
        if not template_struct:
            logger.warning(f"No template action set found for template_set_id={template_set_id}")
            abort(404)
        
        # Get template action items with their structs for convenient access
        action_item_structs = [TemplateActionItemStruct(item) for item in template_struct.template_action_items]
        
        # Get context for business logic if needed
        template_context = TemplateMaintenanceContext(template_struct)
        
        # Collect unique proto actions referenced by template action items
        from app.buisness.maintenance.proto_templates.proto_action_item_struct import ProtoActionItemStruct
        proto_actions_dict = {}  # {proto_id: {'struct': ProtoActionItemStruct, 'referenced_by': [TemplateActionItem]}}
        
        for action_item in template_struct.template_action_items:
            if action_item.proto_action_item:
                proto_id = action_item.proto_action_item.id
                if proto_id not in proto_actions_dict:
                    proto_actions_dict[proto_id] = {
                        'struct': ProtoActionItemStruct(action_item.proto_action_item),
                        'referenced_by': []
                    }
                proto_actions_dict[proto_id]['referenced_by'].append(action_item)
        
        # Convert to list for template
        proto_actions = list(proto_actions_dict.values())
        
        return render_template(
            'maintenance/view_maintenance_template.html',
            template=template_struct,
            template_context=template_context,
            action_items=action_item_structs,
            proto_actions=proto_actions,
        )
        
    except ImportError as e:
        logger.error(f"Could not import maintenance template modules: {e}")
        abort(500)
    except Exception as e:
        logger.error(f"Error viewing maintenance template {template_set_id}: {e}")
        import traceback
        traceback.print_exc()
        abort(500)


@maintenance_bp.route('/proto-actions/<int:proto_action_id>')
@maintenance_bp.route('/proto-actions/<int:proto_action_id>/view')
@login_required
def view_proto_action(proto_action_id):
    """View detailed information about a proto action"""
    logger.info(f"Viewing proto action for proto_action_id={proto_action_id}")
    
    try:
        from app.buisness.maintenance.proto_templates.proto_action_item_struct import ProtoActionItemStruct
        from app.buisness.maintenance.proto_templates.proto_action_context import ProtoActionContext
        from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem
        
        # Get the proto action item
        proto_struct = ProtoActionItemStruct(proto_action_id)
        
        if not proto_struct:
            logger.warning(f"No proto action item found for proto_action_id={proto_action_id}")
            abort(404)
        
        # Get context for business logic
        proto_context = ProtoActionContext(proto_struct)
        
        # Get template action items that reference this proto action
        template_action_items = proto_struct.proto_action_item.template_action_items.all()
        
        return render_template(
            'maintenance/view_proto_action.html',
            proto=proto_struct,
            proto_context=proto_context,
            template_action_items=template_action_items,
        )
        
    except ImportError as e:
        logger.error(f"Could not import proto action modules: {e}")
        abort(500)
    except Exception as e:
        logger.error(f"Error viewing proto action {proto_action_id}: {e}")
        import traceback
        traceback.print_exc()
        abort(500)


# ============================================================================
# Work Page Interactivity Routes
# ============================================================================

@maintenance_bp.route('/maintenance-event/<int:event_id>/action/<int:action_id>/update-status', methods=['POST'])
@login_required
def update_action_status(event_id, action_id):
    """Update action status with comment generation and part demand management"""
    try:
        from app.buisness.maintenance.base.action_context import ActionContext
        from app.buisness.maintenance.base.maintenance_action_set_struct import MaintenanceActionSetStruct
        from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
        from app.buisness.core.event_context import EventContext
        from app.data.maintenance.base.actions import Action
        
        action = Action.query.get_or_404(action_id)
        old_status = action.status
        new_status = request.form.get('status', '').strip()
        comment = request.form.get('comment', '').strip()
        edited_comment = request.form.get('edited_comment', '').strip()
        
        # Use edited comment if provided, otherwise use original comment
        # If edited_comment exists, it means user edited it, so mark as human-made
        final_comment = edited_comment if edited_comment else comment
        is_human_made = bool(edited_comment)  # If edited_comment is provided, user edited it
        
        # Validate status transition
        valid_statuses = ['Not Started', 'In Progress', 'Complete', 'Failed', 'Skipped', 'Blocked']
        if new_status not in valid_statuses:
            flash('Invalid status', 'error')
            return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        # Check if comment is required
        requires_comment = new_status in ['Blocked', 'Failed'] or (old_status in ['Complete', 'Failed'] and new_status in ['Complete', 'Failed'])
        if requires_comment and not final_comment:
            flash(f'Comment is required when marking action as {new_status}', 'error')
            return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        # Get action context
        action_context = ActionContext(action)
        
        # Get billable hours if provided
        billable_hours = None
        billable_hours_str = request.form.get('billable_hours', '').strip()
        if billable_hours_str:
            try:
                billable_hours = float(billable_hours_str)
                if billable_hours < 0:
                    billable_hours = None
            except ValueError:
                pass  # Ignore invalid values
        
        # Get completion notes if provided
        completion_notes = request.form.get('completion_notes', '').strip()
        
        # Track part demand actions for comment generation
        part_demand_actions = []
        
        # Handle status-specific logic using ActionContext methods
        if new_status == 'Complete':
            # Get part demand option
            issue_part_demands = request.form.get('issue_part_demands', 'false').lower() == 'true'
            # Count part demands before (using action context)
            part_demands_before = len([pd for pd in action_context._struct.part_demands if pd.status != 'Issued'])
            action_context.mark_complete(
                user_id=current_user.id,
                billable_hours=billable_hours,
                notes=completion_notes or final_comment,
                issue_part_demands=issue_part_demands
            )
            if issue_part_demands and part_demands_before > 0:
                part_demand_actions.append(f"Issued {part_demands_before} part demand(s)")
        elif new_status == 'Failed':
            # Get part demand options
            duplicate_part_demands = request.form.get('duplicate_part_demands', 'false').lower() == 'true'
            cancel_part_demands = request.form.get('cancel_part_demands', 'false').lower() == 'true'
            # Count part demands before (using action context)
            part_demands_to_duplicate = len([pd for pd in action_context._struct.part_demands if pd.status != 'Issued'])
            part_demands_to_cancel = len([pd for pd in action_context._struct.part_demands if pd.status not in ['Issued', 'Cancelled by Technician', 'Cancelled by Supply']])
            action_context.mark_failed(
                user_id=current_user.id,
                billable_hours=billable_hours,
                notes=completion_notes or final_comment,
                duplicate_part_demands=duplicate_part_demands,
                cancel_part_demands=cancel_part_demands
            )
            if duplicate_part_demands and part_demands_to_duplicate > 0:
                part_demand_actions.append(f"Duplicated {part_demands_to_duplicate} part demand(s)")
            if cancel_part_demands and part_demands_to_cancel > 0:
                part_demand_actions.append(f"Cancelled {part_demands_to_cancel} part demand(s)")
        elif new_status == 'Skipped':
            # Get part demand option
            cancel_part_demands = request.form.get('cancel_part_demands', 'false').lower() == 'true'
            # Count part demands before (using action context)
            part_demands_to_cancel = len([pd for pd in action_context._struct.part_demands if pd.status not in ['Issued', 'Cancelled by Technician', 'Cancelled by Supply']])
            action_context.mark_skipped(
                user_id=current_user.id,
                notes=completion_notes or final_comment,
                cancel_part_demands=cancel_part_demands
            )
            if cancel_part_demands and part_demands_to_cancel > 0:
                part_demand_actions.append(f"Cancelled {part_demands_to_cancel} part demand(s)")
        elif new_status == 'In Progress':
            # Update timestamps
            if not action.start_time:
                action.start_time = datetime.utcnow()
            action.status = new_status
            db.session.commit()
        elif new_status == 'Blocked':
            # Update status
            action.status = new_status
            db.session.commit()
        else:
            # For other statuses, just update the status
            action.status = new_status
            db.session.commit()
        
        # Generate comment on Event
        maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
        if maintenance_struct and maintenance_struct.event_id:
            event_context = EventContext(maintenance_struct.event_id)
            comment_text = f"[Action: {action.action_name}] Status changed from {old_status} to {new_status} by {current_user.username}"
            if final_comment:
                comment_text += f". Note: {final_comment}"
            if part_demand_actions:
                comment_text += f". Part demands: {', '.join(part_demand_actions)}"
            event_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=is_human_made
            )
            db.session.commit()
        
        flash(f'Action status updated to {new_status}', 'success')
        return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error updating action status: {e}")
        import traceback
        traceback.print_exc()
        flash('Error updating action status', 'error')
        return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))


@maintenance_bp.route('/maintenance-event/<int:event_id>/action/<int:action_id>/update', methods=['POST'])
@login_required
def edit_action(event_id, action_id):
    """Full update action form to update all editable fields"""
    try:
        from app.data.maintenance.base.actions import Action
        from app.buisness.maintenance.base.maintenance_action_set_struct import MaintenanceActionSetStruct
        from app.buisness.core.event_context import EventContext
        from app.buisness.maintenance.base.action_context import ActionContext
        from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
        
        action = Action.query.get_or_404(action_id)
        old_status = action.status
        
        # Get maintenance struct and event context
        maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
        if not maintenance_struct or not maintenance_struct.event_id:
            flash('Maintenance event not found', 'error')
            return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        event_context = EventContext(maintenance_struct.event_id)
        action_context = ActionContext(action)
        
        # Prepare update dictionary
        updates = {}
        
        # Check if reset to In Progress is requested
        reset_to_in_progress = request.form.get('reset_to_in_progress', 'false').lower() == 'true'
        if reset_to_in_progress:
            updates['reset_to_in_progress'] = True
        
        # Parse status
        status_str = request.form.get('status', '').strip()
        if status_str:
            updates['status'] = status_str
        
        # Parse datetime fields
        scheduled_start_time_str = request.form.get('scheduled_start_time', '').strip()
        if scheduled_start_time_str:
            try:
                updates['scheduled_start_time'] = datetime.strptime(scheduled_start_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid scheduled start time format', 'error')
                return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        elif 'scheduled_start_time' in request.form:  # Explicitly cleared
            updates['scheduled_start_time'] = None
        
        start_time_str = request.form.get('start_time', '').strip()
        if start_time_str:
            try:
                updates['start_time'] = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid start time format', 'error')
                return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        elif 'start_time' in request.form:  # Explicitly cleared
            updates['start_time'] = None
        
        end_time_str = request.form.get('end_time', '').strip()
        if end_time_str:
            try:
                end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
                # Validate: end_time must be after start_time
                if updates.get('start_time') and end_time < updates['start_time']:
                    flash('End time must be after start time', 'error')
                    return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
                updates['end_time'] = end_time
            except ValueError:
                flash('Invalid end time format', 'error')
                return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        elif 'end_time' in request.form and not reset_to_in_progress:  # Explicitly cleared
            updates['end_time'] = None
        
        # Parse numeric fields
        billable_hours_str = request.form.get('billable_hours', '').strip()
        if billable_hours_str:
            try:
                billable_hours = float(billable_hours_str)
                if billable_hours < 0:
                    flash('Billable hours must be non-negative', 'error')
                    return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
                updates['billable_hours'] = billable_hours
            except ValueError:
                flash('Invalid billable hours value', 'error')
                return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        elif 'billable_hours' in request.form:  # Explicitly cleared
            updates['billable_hours'] = None
        
        estimated_duration_str = request.form.get('estimated_duration', '').strip()
        if estimated_duration_str:
            try:
                estimated_duration = float(estimated_duration_str)
                if estimated_duration < 0:
                    flash('Estimated duration must be non-negative', 'error')
                    return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
                updates['estimated_duration'] = estimated_duration
            except ValueError:
                flash('Invalid estimated duration value', 'error')
                return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        elif 'estimated_duration' in request.form:  # Explicitly cleared
            updates['estimated_duration'] = None
        
        expected_billable_hours_str = request.form.get('expected_billable_hours', '').strip()
        if expected_billable_hours_str:
            try:
                expected_billable_hours = float(expected_billable_hours_str)
                if expected_billable_hours < 0:
                    flash('Expected billable hours must be non-negative', 'error')
                    return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
                updates['expected_billable_hours'] = expected_billable_hours
            except ValueError:
                flash('Invalid expected billable hours value', 'error')
                return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        elif 'expected_billable_hours' in request.form:  # Explicitly cleared
            updates['expected_billable_hours'] = None
        
        # Parse text fields
        completion_notes = request.form.get('completion_notes', '').strip()
        if completion_notes or 'completion_notes' in request.form:
            updates['completion_notes'] = completion_notes if completion_notes else None
        
        action_name = request.form.get('action_name', '').strip()
        if action_name:
            updates['action_name'] = action_name
        
        description = request.form.get('description', '').strip()
        if description or 'description' in request.form:
            updates['description'] = description if description else None
        
        safety_notes = request.form.get('safety_notes', '').strip()
        if safety_notes or 'safety_notes' in request.form:
            updates['safety_notes'] = safety_notes if safety_notes else None
        
        notes = request.form.get('notes', '').strip()
        if notes or 'notes' in request.form:
            updates['notes'] = notes if notes else None
        
        # Parse assigned_user_id
        assigned_user_id_str = request.form.get('assigned_user_id', '').strip()
        if assigned_user_id_str:
            try:
                assigned_user_id = int(assigned_user_id_str)
                updates['assigned_user_id'] = assigned_user_id
            except ValueError:
                flash('Invalid assigned user ID', 'error')
                return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        elif 'assigned_user_id' in request.form:  # Explicitly cleared
            updates['assigned_user_id'] = None
        
        # Parse sequence_order
        sequence_order_str = request.form.get('sequence_order', '').strip()
        if sequence_order_str:
            try:
                sequence_order = int(sequence_order_str)
                if sequence_order < 1:
                    flash('Sequence order must be at least 1', 'error')
                    return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
                updates['sequence_order'] = sequence_order
            except ValueError:
                flash('Invalid sequence order value', 'error')
                return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        # Handle maintenance_action_set_id (set to self if provided)
        maintenance_action_set_id_str = request.form.get('maintenance_action_set_id', '').strip()
        if maintenance_action_set_id_str:
            try:
                maintenance_action_set_id = int(maintenance_action_set_id_str)
                if maintenance_action_set_id == action.maintenance_action_set_id:
                    updates['maintenance_action_set_id'] = maintenance_action_set_id
            except ValueError:
                pass  # Ignore invalid values
        
        # Apply updates using ActionContext
        action_context.edit_action(**updates)
        
        # Generate comment if status changed or reset
        comment_parts = []
        if reset_to_in_progress and old_status in ['Complete', 'Failed', 'Skipped']:
            comment_parts.append(f"Status reset from {old_status} to In Progress (for retry)")
        elif updates.get('status') and updates['status'] != old_status:
            comment_parts.append(f"Status changed from {old_status} to {updates['status']}")
        
        if comment_parts:
            comment_text = f"[Action: {action.action_name}] " + ". ".join(comment_parts) + f" by {current_user.username}"
            event_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=True
            )
        
        # Auto-update MaintenanceActionSet billable hours if sum is greater
        maintenance_context = MaintenanceContext(maintenance_struct)
        maintenance_context.update_actual_billable_hours_auto()
        
        flash('Action updated successfully', 'success')
        return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
    except Exception as e:
        logger.error(f"Error editing action: {e}")
        import traceback
        traceback.print_exc()
        flash('Error updating action', 'error')
        return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))


@maintenance_bp.route('/maintenance-event/<int:event_id>/action/<int:action_id>/update-billable-hours', methods=['POST'])
@login_required
def update_action_billable_hours(event_id, action_id):
    """Update action billable hours"""
    try:
        from app.data.maintenance.base.actions import Action
        from app.buisness.maintenance.base.maintenance_action_set_struct import MaintenanceActionSetStruct
        from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
        
        action = Action.query.get_or_404(action_id)
        
        billable_hours_str = request.form.get('billable_hours', '').strip()
        if not billable_hours_str:
            flash('Billable hours is required', 'error')
            return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        try:
            billable_hours = float(billable_hours_str)
            if billable_hours < 0:
                flash('Billable hours must be non-negative', 'error')
                return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
            action.billable_hours = billable_hours
        except ValueError:
            flash('Invalid billable hours value', 'error')
            return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        db.session.commit()
        
        # Auto-update MaintenanceActionSet billable hours if sum is greater
        maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
        if maintenance_struct:
            maintenance_context = MaintenanceContext(maintenance_struct)
            maintenance_context.update_actual_billable_hours_auto()
        
        flash('Billable hours updated', 'success')
        return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error updating action billable hours: {e}")
        flash('Error updating billable hours', 'error')
        return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))


@maintenance_bp.route('/maintenance-event/<int:event_id>/update-datetime', methods=['POST'])
@login_required
def update_maintenance_datetime(event_id):
    """Update maintenance start/end dates"""
    try:
        from app.buisness.maintenance.base.maintenance_action_set_struct import MaintenanceActionSetStruct
        
        maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
        if not maintenance_struct:
            abort(404)
        
        # Update start_date
        start_date_str = request.form.get('start_date', '').strip()
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
                maintenance_struct.maintenance_action_set.start_date = start_date
            except ValueError:
                flash('Invalid start date format', 'error')
                return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        # Update end_date
        end_date_str = request.form.get('end_date', '').strip()
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
                # Validate: end_date must be after start_date
                if maintenance_struct.maintenance_action_set.start_date and end_date < maintenance_struct.maintenance_action_set.start_date:
                    flash('End date must be after start date', 'error')
                    return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
                maintenance_struct.maintenance_action_set.end_date = end_date
            except ValueError:
                flash('Invalid end date format', 'error')
                return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        db.session.commit()
        flash('Maintenance dates updated', 'success')
        return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error updating maintenance datetime: {e}")
        flash('Error updating maintenance dates', 'error')
        return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))


@maintenance_bp.route('/maintenance-event/<int:event_id>/update-billable-hours', methods=['POST'])
@login_required
def update_maintenance_billable_hours(event_id):
    """Update maintenance total billable hours"""
    try:
        from app.buisness.maintenance.base.maintenance_action_set_struct import MaintenanceActionSetStruct
        from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
        
        maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
        if not maintenance_struct:
            abort(404)
        
        maintenance_context = MaintenanceContext(maintenance_struct)
        
        billable_hours_str = request.form.get('actual_billable_hours', '').strip()
        if not billable_hours_str:
            flash('Billable hours is required', 'error')
            return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        try:
            billable_hours = float(billable_hours_str)
            maintenance_context.set_actual_billable_hours(billable_hours)
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        flash('Maintenance billable hours updated', 'success')
        return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error updating maintenance billable hours: {e}")
        flash('Error updating billable hours', 'error')
        return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))


@maintenance_bp.route('/maintenance-event/<int:event_id>/complete', methods=['POST'])
@login_required
def complete_maintenance(event_id):
    """Complete maintenance event with validation"""
    try:
        from app.buisness.maintenance.base.maintenance_action_set_struct import MaintenanceActionSetStruct
        from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
        from app.buisness.core.event_context import EventContext
        
        maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
        if not maintenance_struct:
            abort(404)
        
        # Validate required fields
        completion_comment = request.form.get('completion_comment', '').strip()
        if not completion_comment:
            flash('Completion comment is required', 'error')
            return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        # Check all actions are in terminal states
        blocked_actions = [a for a in maintenance_struct.actions if a.status == 'Blocked']
        if blocked_actions:
            flash('Cannot complete maintenance. Please resolve all blocked actions first.', 'error')
            return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        # Validate dates
        start_date_str = request.form.get('actual_start_date', '').strip()
        end_date_str = request.form.get('actual_end_date', '').strip()
        
        if not start_date_str or not end_date_str:
            flash('Both start and end dates are required', 'error')
            return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
            if end_date < start_date:
                flash('End date must be after start date', 'error')
                return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        except ValueError:
            flash('Invalid date format', 'error')
            return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        # Validate billable hours
        billable_hours_str = request.form.get('actual_billable_hours', '').strip()
        if not billable_hours_str:
            flash('Billable hours is required', 'error')
            return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        try:
            billable_hours = float(billable_hours_str)
            if billable_hours < 0.2:
                flash('Billable hours must be at least 0.2 hours (12 minutes)', 'error')
                return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        except ValueError:
            flash('Invalid billable hours value', 'error')
            return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        # Update maintenance
        maintenance_context = MaintenanceContext(maintenance_struct)
        maintenance_struct.maintenance_action_set.start_date = start_date
        maintenance_struct.maintenance_action_set.end_date = end_date
        maintenance_context.set_actual_billable_hours(billable_hours)
        maintenance_struct.maintenance_action_set.completion_notes = completion_comment
        maintenance_struct.maintenance_action_set.status = 'Complete'
        maintenance_struct.maintenance_action_set.completed_by_id = current_user.id
        
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
        return redirect(url_for('maintenance.view_maintenance_event', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error completing maintenance: {e}")
        flash('Error completing maintenance', 'error')
        return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))


@maintenance_bp.route('/maintenance-event/<int:event_id>/action/<int:action_id>/part-demand/create', methods=['POST'])
@login_required
def create_part_demand(event_id, action_id):
    """Create a new part demand for an action"""
    try:
        from app.data.maintenance.base.part_demands import PartDemand
        from app.buisness.maintenance.base.maintenance_action_set_struct import MaintenanceActionSetStruct
        from app.buisness.core.event_context import EventContext
        
        part_id = request.form.get('part_id', '').strip()
        quantity_str = request.form.get('quantity_required', '').strip()
        notes = request.form.get('notes', '').strip()
        
        if not part_id or not quantity_str:
            flash('Part and quantity are required', 'error')
            return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        try:
            part_id = int(part_id)
            quantity = float(quantity_str)
            if quantity <= 0:
                flash('Quantity must be greater than 0', 'error')
                return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        except ValueError:
            flash('Invalid part ID or quantity', 'error')
            return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        # Create part demand
        part_demand = PartDemand(
            action_id=action_id,
            part_id=part_id,
            quantity_required=quantity,
            notes=notes,
            status='Pending Manager Approval',
            requested_by_id=current_user.id,
            created_by_id=current_user.id,
            updated_by_id=current_user.id
        )
        db.session.add(part_demand)
        db.session.commit()
        
        # Generate automated comment
        maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
        if maintenance_struct and maintenance_struct.event_id:
            event_context = EventContext(maintenance_struct.event_id)
            from app.data.core.supply.part import Part
            part = Part.query.get(part_id)
            part_name = part.part_name if part else f"Part #{part_id}"
            comment_text = f"Part demand created: {part_name} x{quantity} by {current_user.username}"
            if notes:
                comment_text += f". Notes: {notes}"
            event_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=False  # Automated comment
            )
            db.session.commit()
        
        flash('Part demand created successfully', 'success')
        return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error creating part demand: {e}")
        flash('Error creating part demand', 'error')
        return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))


@maintenance_bp.route('/maintenance-event/<int:event_id>/part-demand/<int:part_demand_id>/issue', methods=['POST'])
@login_required
def issue_part_demand(event_id, part_demand_id):
    """Issue a part demand (any user can issue)"""
    try:
        from app.data.maintenance.base.part_demands import PartDemand
        from app.buisness.maintenance.base.maintenance_action_set_struct import MaintenanceActionSetStruct
        from app.buisness.core.event_context import EventContext
        
        part_demand = PartDemand.query.get_or_404(part_demand_id)
        
        # Update status to Issued
        part_demand.status = 'Issued'
        db.session.commit()
        
        # Generate automated comment
        maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
        if maintenance_struct and maintenance_struct.event_id:
            event_context = EventContext(maintenance_struct.event_id)
            from app.data.core.supply.part import Part
            part = Part.query.get(part_demand.part_id)
            part_name = part.part_name if part else f"Part #{part_demand.part_id}"
            comment_text = f"Part issued: {part_name} x{part_demand.quantity_required} by {current_user.username}"
            event_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=False  # Automated comment
            )
            db.session.commit()
        
        flash('Part issued successfully', 'success')
        return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error issuing part demand: {e}")
        flash('Error issuing part', 'error')
        return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))


@maintenance_bp.route('/maintenance-event/<int:event_id>/part-demand/<int:part_demand_id>/cancel', methods=['POST'])
@login_required
def cancel_part_demand(event_id, part_demand_id):
    """Cancel a part demand (technician can cancel if not issued)"""
    try:
        from app.data.maintenance.base.part_demands import PartDemand
        from app.buisness.maintenance.base.maintenance_action_set_struct import MaintenanceActionSetStruct
        from app.buisness.core.event_context import EventContext
        
        part_demand = PartDemand.query.get_or_404(part_demand_id)
        
        # Check if already issued
        if part_demand.status == 'Issued':
            flash('Cannot cancel an issued part demand', 'error')
            return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        # Require cancellation comment
        cancellation_comment = request.form.get('cancellation_comment', '').strip()
        if not cancellation_comment:
            flash('Cancellation comment is required', 'error')
            return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        # Update status
        part_demand.status = 'Cancelled by Technician'
        db.session.commit()
        
        # Generate automated comment
        maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
        if maintenance_struct and maintenance_struct.event_id:
            event_context = EventContext(maintenance_struct.event_id)
            from app.data.core.supply.part import Part
            part = Part.query.get(part_demand.part_id)
            part_name = part.part_name if part else f"Part #{part_demand.part_id}"
            comment_text = f"Part demand cancelled: {part_name} x{part_demand.quantity_required} by {current_user.username}. Reason: {cancellation_comment}"
            event_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=False  # Automated comment
            )
            db.session.commit()
        
        flash('Part demand cancelled successfully', 'success')
        return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error cancelling part demand: {e}")
        flash('Error cancelling part demand', 'error')
        return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))


@maintenance_bp.route('/maintenance-event/<int:event_id>/delay/create', methods=['POST'])
@login_required
def create_delay(event_id):
    """Create a delay for maintenance event"""
    try:
        from app.buisness.maintenance.base.maintenance_action_set_struct import MaintenanceActionSetStruct
        from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
        from app.buisness.core.event_context import EventContext
        from app.data.maintenance.base.maintenance_delays import MaintenanceDelay
        
        maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
        if not maintenance_struct:
            abort(404)
        
        # Check if there's already an active delay
        active_delays = [d for d in maintenance_struct.delays if d.delay_end_date is None]
        if active_delays:
            flash('An active delay already exists. Please end the current delay before creating a new one.', 'error')
            return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        # Validate required fields
        delay_type = request.form.get('delay_type', '').strip()
        delay_reason = request.form.get('delay_reason', '').strip()
        
        if not delay_type or delay_type not in ['Work in Delay', 'Cancellation Requested']:
            flash('Valid delay type is required', 'error')
            return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        if not delay_reason:
            flash('Delay reason is required', 'error')
            return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
        # Get optional fields
        priority = request.form.get('priority', 'Medium').strip()
        delay_notes = request.form.get('delay_notes', '').strip()
        delay_billable_hours_str = request.form.get('delay_billable_hours', '').strip()
        
        delay_billable_hours = None
        if delay_billable_hours_str:
            try:
                delay_billable_hours = float(delay_billable_hours_str)
                if delay_billable_hours < 0:
                    flash('Billable hours must be non-negative', 'error')
                    return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
            except ValueError:
                pass  # Ignore invalid values
        
        # Create delay using MaintenanceContext
        maintenance_context = MaintenanceContext(maintenance_struct)
        delay = maintenance_context.add_delay(
            delay_type=delay_type,
            delay_reason=delay_reason,
            delay_notes=delay_notes,
            delay_billable_hours=delay_billable_hours,
            priority=priority,
            user_id=current_user.id
        )
        
        # Generate automated comment
        if maintenance_struct.event_id:
            event_context = EventContext(maintenance_struct.event_id)
            comment_text = f"Delay created: {delay_type} by {current_user.username}. Reason: {delay_reason}"
            event_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=False  # Automated comment
            )
            db.session.commit()
        
        flash('Delay created successfully', 'success')
        return redirect(url_for('maintenance.view_maintenance_event', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error creating delay: {e}")
        flash('Error creating delay', 'error')
        return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))


@maintenance_bp.route('/maintenance-event/<int:event_id>/delay/<int:delay_id>/end', methods=['POST'])
@login_required
def end_delay(event_id, delay_id):
    """End an active delay"""
    try:
        from app.data.maintenance.base.maintenance_delays import MaintenanceDelay
        from app.buisness.maintenance.base.maintenance_action_set_struct import MaintenanceActionSetStruct
        from app.buisness.core.event_context import EventContext
        
        delay = MaintenanceDelay.query.get_or_404(delay_id)
        
        if delay.delay_end_date:
            flash('Delay is already ended', 'warning')
            return redirect(url_for('maintenance.view_maintenance_event', event_id=event_id))
        
        # End the delay
        delay.delay_end_date = datetime.utcnow()
        
        # Update maintenance status back to In Progress
        maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
        if maintenance_struct and maintenance_struct.maintenance_action_set.status == 'Delayed':
            maintenance_struct.maintenance_action_set.status = 'In Progress'
        
        db.session.commit()
        
        # Generate automated comment
        if maintenance_struct and maintenance_struct.event_id:
            event_context = EventContext(maintenance_struct.event_id)
            comment_text = f"Delay ended by {current_user.username}. Maintenance work resumed."
            event_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=False  # Automated comment
            )
            db.session.commit()
        
        flash('Delay ended successfully. Work can now continue.', 'success')
        return redirect(url_for('maintenance.work_maintenance_event', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error ending delay: {e}")
        flash('Error ending delay', 'error')
        return redirect(url_for('maintenance.view_maintenance_event', event_id=event_id))

