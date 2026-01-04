"""
Action management routes for maintenance events
Routes handling actions within maintenance events
"""
from flask import request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from datetime import datetime
from urllib.parse import urlparse
from app.logger import get_logger
from app import db

from app.buisness.maintenance.base.structs.maintenance_action_set_struct import MaintenanceActionSetStruct
from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
from app.data.maintenance.base.actions import Action
from app.buisness.core.event_context import EventContext
from app.buisness.maintenance.base.action_context import ActionContext
import traceback 
from app.data.maintenance.base.part_demands import PartDemand
from app.data.maintenance.base.action_tools import ActionTool
from app.data.core.supply.part_definition import PartDefinition
from app.data.core.supply.tool_definition import ToolDefinition


logger = get_logger("asset_management.routes.maintenance.action_managment")

# Import maintenance_bp from main maintenance routes
from app.presentation.routes.maintenance.main import maintenance_bp


def get_redirect_url(event_id, default_endpoint='maintenance_event.work_maintenance_event'):
    """
    Get redirect URL, checking in order:
    1. redirect_to form/query parameter
    2. request.referrer (if valid internal URL)
    3. default endpoint with event_id
    
    Args:
        event_id: Event ID for default redirect
        default_endpoint: Default endpoint name if no redirect found
        
    Returns:
        Redirect response or URL string
    """
    # Check for explicit redirect_to parameter
    redirect_to = request.form.get('redirect_to') or request.args.get('redirect_to')
    if redirect_to:
        # Validate it's an internal URL (no external domains)
        parsed = urlparse(redirect_to)
        if not parsed.netloc or parsed.netloc == request.host:
            return redirect_to
    
    # Check referrer
    referrer = request.referrer
    if referrer:
        parsed = urlparse(referrer)
        # Only use referrer if it's from the same host (internal redirect)
        if not parsed.netloc or parsed.netloc == request.host:
            return referrer
    
    # Fall back to default
    return url_for(default_endpoint, event_id=event_id)

@maintenance_bp.route('/action/<int:action_id>/update-status', methods=['POST'])
@login_required
def update_action_status(action_id):
    """Update action status with comment generation and part demand management"""
    try:
        
        
        # Get action first
        action = Action.query.get_or_404(action_id)
        old_status = action.status
        
        # Create MaintenanceContext from action's maintenance_action_set_id
        maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
        struct: MaintenanceActionSetStruct = maintenance_context.struct
        
        # Get event_id from struct for redirects
        event_id = struct.event_id
        if not event_id:
            flash('Maintenance event not found', 'error')
            abort(404)
        
        # ===== FORM PARSING SECTION =====
        # Parse form fields
        new_status = request.form.get('status', '').strip()
        comment = request.form.get('comment', '').strip()
        edited_comment = request.form.get('edited_comment', '').strip()
        billable_hours_str = request.form.get('billable_hours', '').strip()
        completion_notes = request.form.get('completion_notes', '').strip()
        issue_part_demands_str = request.form.get('issue_part_demands', 'false').strip()
        part_demand_action = request.form.get('part_demand_action', 'leave_as_is').strip()
        
        # Convert and validate data types
        # Use edited comment if provided, otherwise use original comment
        # If edited_comment exists, it means user edited it, so mark as human-made
        final_comment = edited_comment if edited_comment else comment
        is_human_made = bool(edited_comment)
        
        # Parse billable hours
        billable_hours = None
        if billable_hours_str:
            try:
                billable_hours = float(billable_hours_str)
                if billable_hours < 0:
                    billable_hours = None
            except ValueError:
                pass  # Ignore invalid values
        
        # Parse issue_part_demands (boolean)
        issue_part_demands = issue_part_demands_str.lower() == 'true'
        
        # Parse part demand actions (boolean flags)
        duplicate_part_demands = part_demand_action == 'duplicate'
        cancel_part_demands = part_demand_action == 'cancel'
        
        # ===== LIGHT VALIDATION SECTION =====
        # Validate status
        valid_statuses = ['Not Started', 'In Progress', 'Complete', 'Failed', 'Skipped', 'Blocked']
        if new_status not in valid_statuses:
            flash('Invalid status', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        # Check if comment is required
        requires_comment = new_status in ['Blocked', 'Failed'] or (old_status in ['Complete', 'Failed'] and new_status in ['Complete', 'Failed'])
        if requires_comment and not final_comment:
            flash(f'Comment is required when marking action as {new_status}', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        # ===== BUSINESS LOGIC SECTION =====
        action_orchestrator = maintenance_context.get_action_orchestrator()
        comment_text = action_orchestrator.update_action_status(
            action_id=action_id,
            user_id=current_user.id,
            username=current_user.username,
            new_status=new_status,
            old_status=old_status,
            final_comment=final_comment,
            is_human_made=is_human_made,
            billable_hours=billable_hours,
            completion_notes=completion_notes,
            issue_part_demands=issue_part_demands,
            duplicate_part_demands=duplicate_part_demands,
            cancel_part_demands=cancel_part_demands
        )
        
        # Comments are now automatically added by MaintenanceActionOrchestrator
        # Sync event status
        maintenance_context._sync_event_status()
        
        flash(f'Action status updated to {new_status}', 'success')
        return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error updating action status: {e}")
        
        traceback.print_exc()
        flash('Error updating action status', 'error')
        # Try to get event_id for redirect, but don't fail if we can't
        try:
            
            action = Action.query.get(action_id)
            if action:
                maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
                struct: MaintenanceActionSetStruct = maintenance_context.struct
                if struct.event_id:
                    return redirect(url_for('maintenance_event.work_maintenance_event', event_id=struct.event_id))
        except:
            pass
        abort(404)

@maintenance_bp.route('/action/<int:action_id>/update', methods=['POST'])
@login_required
def edit_action(action_id):
    """Full update action form to update all editable fields"""
    try:
        
        
        
        # Get action first
        action = Action.query.get_or_404(action_id)
        old_status = action.status
        
        # Create MaintenanceContext from action's maintenance_action_set_id
        maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
        struct: MaintenanceActionSetStruct = maintenance_context.struct
        
        # Get event_id from struct for redirects
        event_id = struct.event_id
        if not event_id:
            flash('Maintenance event not found', 'error')
            abort(404)
        
        # ===== FORM PARSING SECTION =====
        # Parse all form fields
        # Check redirect target (for edit page vs work page)
        redirect_target = request.form.get('redirect_to', 'work').strip()
        reset_to_in_progress_str = request.form.get('reset_to_in_progress', 'false').strip()
        status_str = request.form.get('status', '').strip()
        scheduled_start_time_str = request.form.get('scheduled_start_time', '').strip()
        start_time_str = request.form.get('start_time', '').strip()
        end_time_str = request.form.get('end_time', '').strip()
        billable_hours_str = request.form.get('billable_hours', '').strip()
        estimated_duration_str = request.form.get('estimated_duration', '').strip()
        expected_billable_hours_str = request.form.get('expected_billable_hours', '').strip()
        completion_notes = request.form.get('completion_notes', '').strip()
        action_name = request.form.get('action_name', '').strip()
        description = request.form.get('description', '').strip()
        safety_notes = request.form.get('safety_notes', '').strip()
        notes = request.form.get('notes', '').strip()
        assigned_user_id_str = request.form.get('assigned_user_id', '').strip()
        sequence_order_str = request.form.get('sequence_order', '').strip()
        maintenance_action_set_id_str = request.form.get('maintenance_action_set_id', '').strip()
        
        # ===== DATA TYPE CONVERSION SECTION =====
        # Prepare update dictionary
        updates = {}
        
        # Convert reset_to_in_progress (boolean)
        reset_to_in_progress = reset_to_in_progress_str.lower() == 'true'
        if reset_to_in_progress:
            updates['reset_to_in_progress'] = True
        
        # Convert status (string)
        if status_str:
            updates['status'] = status_str
        
        # Convert datetime fields
        if scheduled_start_time_str:
            try:
                updates['scheduled_start_time'] = datetime.strptime(scheduled_start_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid scheduled start time format', 'error')
                return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        elif 'scheduled_start_time' in request.form:  # Explicitly cleared
            updates['scheduled_start_time'] = None
        
        if start_time_str:
            try:
                updates['start_time'] = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid start time format', 'error')
                return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        elif 'start_time' in request.form:  # Explicitly cleared
            updates['start_time'] = None
        
        if end_time_str:
            try:
                end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
                updates['end_time'] = end_time
            except ValueError:
                flash('Invalid end time format', 'error')
                return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        elif 'end_time' in request.form and not reset_to_in_progress:  # Explicitly cleared
            updates['end_time'] = None
        
        # Convert numeric fields
        if billable_hours_str:
            try:
                billable_hours = float(billable_hours_str)
                if billable_hours < 0:
                    flash('Billable hours must be non-negative', 'error')
                    return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
                updates['billable_hours'] = billable_hours
            except ValueError:
                flash('Invalid billable hours value', 'error')
                return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        elif 'billable_hours' in request.form:  # Explicitly cleared
            updates['billable_hours'] = None
        
        if estimated_duration_str:
            try:
                estimated_duration = float(estimated_duration_str)
                if estimated_duration < 0:
                    flash('Estimated duration must be non-negative', 'error')
                    return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
                updates['estimated_duration'] = estimated_duration
            except ValueError:
                flash('Invalid estimated duration value', 'error')
                return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        elif 'estimated_duration' in request.form:  # Explicitly cleared
            updates['estimated_duration'] = None
        
        if expected_billable_hours_str:
            try:
                expected_billable_hours = float(expected_billable_hours_str)
                if expected_billable_hours < 0:
                    flash('Expected billable hours must be non-negative', 'error')
                    return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
                updates['expected_billable_hours'] = expected_billable_hours
            except ValueError:
                flash('Invalid expected billable hours value', 'error')
                return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        elif 'expected_billable_hours' in request.form:  # Explicitly cleared
            updates['expected_billable_hours'] = None
        
        # Convert text fields
        if completion_notes or 'completion_notes' in request.form:
            updates['completion_notes'] = completion_notes if completion_notes else None
        
        if action_name:
            updates['action_name'] = action_name
        
        if description or 'description' in request.form:
            updates['description'] = description if description else None
        
        if safety_notes or 'safety_notes' in request.form:
            updates['safety_notes'] = safety_notes if safety_notes else None
        
        if notes or 'notes' in request.form:
            updates['notes'] = notes if notes else None
        
        # Convert assigned_user_id (integer)
        if assigned_user_id_str:
            try:
                assigned_user_id = int(assigned_user_id_str)
                updates['assigned_user_id'] = assigned_user_id
            except ValueError:
                flash('Invalid assigned user ID', 'error')
                return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        elif 'assigned_user_id' in request.form:  # Explicitly cleared
            updates['assigned_user_id'] = None
        
        # Convert sequence_order (integer)
        if sequence_order_str:
            try:
                sequence_order = int(sequence_order_str)
                if sequence_order < 1:
                    flash('Sequence order must be at least 1', 'error')
                    return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
                updates['sequence_order'] = sequence_order
            except ValueError:
                flash('Invalid sequence order value', 'error')
                return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        # Convert maintenance_action_set_id (integer)
        if maintenance_action_set_id_str:
            try:
                maintenance_action_set_id = int(maintenance_action_set_id_str)
                if maintenance_action_set_id == action.maintenance_action_set_id:
                    updates['maintenance_action_set_id'] = maintenance_action_set_id
            except ValueError:
                pass  # Ignore invalid values
        
        # ===== LIGHT VALIDATION SECTION =====
        # Validate: end_time must be after start_time
        if updates.get('end_time') and updates.get('start_time') and updates['end_time'] < updates['start_time']:
            flash('End time must be after start time', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        # ===== BUSINESS LOGIC SECTION =====
        # Delegate all business logic to action orchestrator
        action_orchestrator = maintenance_context.get_action_orchestrator()
        comment_text = action_orchestrator.edit_action(
            action_id=action_id,
            user_id=current_user.id,
            username=current_user.username,
            updates=updates,
            old_status=old_status
        )
        
        # Comments are now automatically added by MaintenanceActionOrchestrator
        # Sync event status
        maintenance_context._sync_event_status()
        
        flash('Action updated successfully', 'success')
        
        # Redirect based on source
        if redirect_target == 'edit':
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        else:
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
    except ValueError as e:
        flash(str(e), 'error')
        # Try to get event_id for redirect
        try:
            
            action = Action.query.get(action_id)
            if action:
                maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
                struct: MaintenanceActionSetStruct = maintenance_context.struct
                event_id = struct.event_id if struct else None
                if event_id:
                    if redirect_target == 'edit':
                        return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
                    else:
                        return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        except:
            pass
        abort(404)
    except Exception as e:
        logger.error(f"Error editing action: {e}")
        
        traceback.print_exc()
        flash('Error updating action', 'error')
        # Try to get event_id for redirect
        try:
            
            action = Action.query.get(action_id)
            if action:
                maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
                struct: MaintenanceActionSetStruct = maintenance_context.struct
                event_id = struct.event_id if struct else None
                if event_id:
                    if redirect_target == 'edit':
                        return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
                    else:
                        return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        except:
            pass
        abort(404)

@maintenance_bp.route('/action/<int:action_id>/update-billable-hours', methods=['POST'])
@login_required
def update_action_billable_hours(action_id):
    """Update action billable hours"""
    try:
        
        
        # Get action first
        action = Action.query.get_or_404(action_id)
        
        # Create MaintenanceContext from action's maintenance_action_set_id
        maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
        struct: MaintenanceActionSetStruct = maintenance_context.struct
        
        # Get event_id from struct for redirects
        event_id = struct.event_id
        if not event_id:
            flash('Maintenance event not found', 'error')
            abort(404)
        
        # ===== FORM PARSING SECTION =====
        billable_hours_str = request.form.get('billable_hours', '').strip()
        
        # ===== LIGHT VALIDATION SECTION =====
        if not billable_hours_str:
            flash('Billable hours is required', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        # ===== DATA TYPE CONVERSION SECTION =====
        try:
            billable_hours = float(billable_hours_str)
            if billable_hours < 0:
                flash('Billable hours must be non-negative', 'error')
                return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        except ValueError:
            flash('Invalid billable hours value', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
        # ===== BUSINESS LOGIC SECTION =====
        action.billable_hours = billable_hours
        db.session.commit()
        
        # Auto-update MaintenanceActionSet billable hours if sum is greater
        billable_hours_manager = maintenance_context.get_billable_hours_manager()
        billable_hours_manager.auto_update_if_greater()
        
        flash('Billable hours updated', 'success')
        return redirect(url_for('maintenance_event.work_maintenance_event', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error updating action billable hours: {e}")
        flash('Error updating billable hours', 'error')
        # Try to get event_id for redirect, but don't fail if we can't
        try:
            
            action = Action.query.get(action_id)
            if action:
                maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
                struct: MaintenanceActionSetStruct = maintenance_context.struct
                if struct.event_id:
                    return redirect(url_for('maintenance_event.work_maintenance_event', event_id=struct.event_id))
        except:
            pass
        abort(404)

@maintenance_bp.route('/action/<int:action_id>/part-demand/create', methods=['POST'])
@login_required
def create_part_demand(action_id):
    """Create a new part demand for an action"""
    try:
        
        
        
        # Get action first
        
        action = Action.query.get_or_404(action_id)
        
        # Create MaintenanceContext from action's maintenance_action_set_id
        maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
        struct: MaintenanceActionSetStruct = maintenance_context.struct
        
        # Get event_id from struct for redirects
        event_id = struct.event_id
        if not event_id:
            flash('Maintenance event not found', 'error')
            abort(404)
        
        # ===== FORM PARSING SECTION =====
        part_id_str = request.form.get('part_id', '').strip()
        quantity_str = request.form.get('quantity_required', '').strip()
        notes = request.form.get('notes', '').strip()
        
        # ===== LIGHT VALIDATION SECTION =====
        if not part_id_str or not quantity_str:
            flash('Part and quantity are required', 'error')
            return redirect(get_redirect_url(event_id))
        
        # ===== DATA TYPE CONVERSION SECTION =====
        try:
            part_id = int(part_id_str)
            quantity = float(quantity_str)
        except ValueError:
            flash('Invalid part ID or quantity', 'error')
            return redirect(get_redirect_url(event_id))
        
        if quantity <= 0:
            flash('Quantity must be greater than 0', 'error')
            return redirect(get_redirect_url(event_id))
        
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
        if struct.event_id:
            event_context = EventContext(struct.event_id)
            
            part = PartDefinition.query.get(part_id)
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
        return redirect(get_redirect_url(event_id))
        
    except Exception as e:
        logger.error(f"Error creating part demand: {e}")
        flash('Error creating part demand', 'error')
        # Try to get event_id for redirect, but don't fail if we can't
        try:
            action = Action.query.get(action_id)
            if action:
                maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
                struct: MaintenanceActionSetStruct = maintenance_context.struct
                if struct.event_id:
                    return redirect(get_redirect_url(struct.event_id))
        except:
            pass
        abort(404)

@maintenance_bp.route('/action/<int:action_id>/tool/create', methods=['POST'])
@login_required
def create_action_tool(action_id):
    """Create a new tool requirement for an action"""
    try:
        
        
        
        
        # Get action first
        action = Action.query.get_or_404(action_id)
        
        # Create MaintenanceContext from action's maintenance_action_set_id
        maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
        struct: MaintenanceActionSetStruct = maintenance_context.struct
        
        # Get event_id from struct for redirects
        event_id = struct.event_id
        if not event_id:
            flash('Maintenance event not found', 'error')
            abort(404)
        
        # ===== FORM PARSING SECTION =====
        tool_id_str = request.form.get('tool_id', '').strip()
        
        # ===== LIGHT VALIDATION SECTION =====
        if not tool_id_str:
            flash('Tool ID is required', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # ===== DATA TYPE CONVERSION SECTION =====
        try:
            tool_id = int(tool_id_str)
        except ValueError:
            flash('Invalid tool ID', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # Verify tool exists
        
        tool = ToolDefinition.query.get(tool_id)
        if not tool:
            flash('Tool not found', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # ===== BUSINESS LOGIC SECTION =====
        # Create action tool
        action_tool = ActionTool(
            action_id=action_id,
            tool_id=tool_id,
            quantity_required=1,  # Default
            status='Planned',
            priority='Medium',
            sequence_order=1,  # Default, can be updated later
            created_by_id=current_user.id,
            updated_by_id=current_user.id
        )
        db.session.add(action_tool)
        db.session.commit()
        
        # Generate automated comment
        if struct.event_id:
            event_context = EventContext(struct.event_id)
            tool_name = tool.tool_name if tool else f"Tool #{tool_id}"
            comment_text = f"Tool requirement created: {tool_name} for action '{action.action_name}' by {current_user.username}"
            event_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=False  # Automated comment
            )
            db.session.commit()
        
        flash('Tool requirement created successfully', 'success')
        return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error creating tool requirement: {e}")
        
        traceback.print_exc()
        flash('Error creating tool requirement', 'error')
        # Try to get event_id for redirect, but don't fail if we can't
        try:
            
            action = Action.query.get(action_id)
            if action:
                maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
                struct: MaintenanceActionSetStruct = maintenance_context.struct
                if struct.event_id:
                    return redirect(url_for('maintenance_event.render_edit_page', event_id=struct.event_id))
        except:
            pass
        abort(404)


@maintenance_bp.route('/action/<int:action_id>/delete', methods=['POST'])
@login_required
def delete_action(action_id):
    """Delete an action and renumber remaining actions"""
    try:
        

        
        # Get action
        action = Action.query.get_or_404(action_id)
        
        # Create MaintenanceContext from action's maintenance_action_set_id
        maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
        struct: MaintenanceActionSetStruct = maintenance_context.struct
        
        # Get event_id from struct for redirects
        event_id = struct.event_id
        if not event_id:
            flash('Maintenance event not found', 'error')
            abort(404)
        
        # Get action name before deletion
        action_name = action.action_name
        
        # Delete action (cascade will delete part demands and tools)
        db.session.delete(action)
        db.session.commit()
        
        # Renumber remaining actions atomically
        maintenance_context._renumber_actions_atomic()
        
        # Generate automated comment
        if struct.event_id:
            event_context = EventContext(struct.event_id)
            comment_text = f"Action deleted: '{action_name}' by {current_user.username}"
            event_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=False  # Automated comment
            )
            db.session.commit()
        
        flash('Action deleted successfully', 'success')
        return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error deleting action: {e}")
        
        traceback.print_exc()
        flash('Error deleting action', 'error')
        # Try to get event_id for redirect, but don't fail if we can't
        try:
            
            action = Action.query.get(action_id)
            if action:
                maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
                struct: MaintenanceActionSetStruct = maintenance_context.struct
                if struct.event_id:
                    return redirect(url_for('maintenance_event.render_edit_page', event_id=struct.event_id))
        except:
            pass
        abort(404)

@maintenance_bp.route('/action/<int:action_id>/move-up', methods=['POST'])
@login_required
def move_action_up(action_id):
    """Move action up in sequence (decrease sequence_order)"""
    try:
        
        
        
        # Get action
        action = Action.query.get_or_404(action_id)
        
        # Create MaintenanceContext from action's maintenance_action_set_id
        maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
        struct: MaintenanceActionSetStruct = maintenance_context.struct
        
        # Get event_id from struct for redirects
        event_id = struct.event_id
        if not event_id:
            flash('Maintenance event not found', 'error')
            abort(404)
        
        # Get current sequence order
        current_order = action.sequence_order
        if current_order <= 1:
            flash('Action is already at the top', 'warning')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # Move up (decrease sequence_order)
        new_order = current_order - 1
        action_context = ActionContext(action)
        action_context.reorder_action(new_order)
        
        flash('Action moved up successfully', 'success')
        return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error moving action up: {e}")
        flash('Error moving action up', 'error')
        # Try to get event_id for redirect, but don't fail if we can't
        try:
            
            action = Action.query.get(action_id)
            if action:
                maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
                struct: MaintenanceActionSetStruct = maintenance_context.struct
                if struct.event_id:
                    return redirect(url_for('maintenance_event.render_edit_page', event_id=struct.event_id))
        except:
            pass
        abort(404)

@maintenance_bp.route('/action/<int:action_id>/move-down', methods=['POST'])
@login_required
def move_action_down(action_id):
    """Move action down in sequence (increase sequence_order)"""
    try:
        
        
        
        # Get action
        action = Action.query.get_or_404(action_id)
        
        # Create MaintenanceContext from action's maintenance_action_set_id
        maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
        struct: MaintenanceActionSetStruct = maintenance_context.struct
        
        # Get event_id from struct for redirects
        event_id = struct.event_id
        if not event_id:
            flash('Maintenance event not found', 'error')
            abort(404)
        
        # Get current sequence order and max order
        current_order = action.sequence_order
        max_order = len(struct.actions)
        
        if current_order >= max_order:
            flash('Action is already at the bottom', 'warning')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # Move down (increase sequence_order)
        new_order = current_order + 1
        action_context = ActionContext(action)
        action_context.reorder_action(new_order)
        
        flash('Action moved down successfully', 'success')
        return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error moving action down: {e}")
        flash('Error moving action down', 'error')
        # Try to get event_id for redirect, but don't fail if we can't
        try:
            
            action = Action.query.get(action_id)
            if action:
                maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
                struct: MaintenanceActionSetStruct = maintenance_context.struct
                if struct.event_id:
                    return redirect(url_for('maintenance_event.render_edit_page', event_id=struct.event_id))
        except:
            pass
        abort(404)
