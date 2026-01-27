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
from app.data.core.event_info.event import Event
from app.data.core.supply.part_definition import PartDefinition
from app.data.core.user_info.user import User
from app.data.maintenance.base.maintenance_blockers import MaintenanceBlocker
from app.services.maintenance.maintenance_work_portal_service import MaintenanceWorkPortalService

logger = get_logger("asset_management.routes.maintenance")

# Create blueprint for maintenance event work portal
maintenance_event_bp = Blueprint('maintenance_event_work', __name__, url_prefix='/maintenance/maintenance-event')


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
            return redirect(url_for('maintenance_event_view.view_maintenance_event', event_id=event_id))
        
        # Get the event
        event = Event.query.get(event_id)
        if not event:
            logger.warning(f"Event {event_id} not found")
            abort(404)
        
        # Check if event status is complete - redirect to view page
        if event.status and event.status.lower() == 'complete':
            return redirect(url_for('maintenance_event_view.view_maintenance_event', event_id=event_id))
        
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
            return redirect(url_for('maintenance_event_view.view_maintenance_event', event_id=event_id))
        
        # Get limitation records for display
        limitation_records = maintenance_struct.limitation_records if hasattr(maintenance_struct, 'limitation_records') else []
        active_limitations = [lr for lr in limitation_records if lr.is_active]
        
        # Get parts for part demand dropdown
        parts = PartDefinition.query.filter_by(status='Active').order_by(PartDefinition.part_name).all()
        users = User.query.order_by(User.username).all()
        
        # Get blocker allowable values for dropdowns
        from app.data.maintenance.base.maintenance_blockers import MaintenanceBlocker
        blocker_instance = MaintenanceBlocker()  # Temporary instance to access properties
        allowable_reasons = blocker_instance.allowable_reasons
        
        # Get limitation allowable values for dropdowns
        from app.data.maintenance.base.asset_limitation_records import AssetLimitationRecord
        limitation_instance = AssetLimitationRecord()  # Temporary instance to access properties
        allowable_limitation_statuses = limitation_instance.allowable_capability_statuses
        
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
            limitation_records=limitation_records,
            active_limitations=active_limitations,
            parts=parts,
            users=users,
            all_actions_terminal=all_actions_terminal,
            allowable_reasons=allowable_reasons,
            allowable_limitation_statuses=allowable_limitation_statuses,
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
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        if not start_date_str or not end_date_str:
            flash('Both start and end dates are required', 'error')
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        if not billable_hours_str:
            flash('Billable hours is required', 'error')
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        # ===== DATA TYPE CONVERSION SECTION =====
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date format', 'error')
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        try:
            billable_hours = float(billable_hours_str)
        except ValueError:
            flash('Invalid billable hours value', 'error')
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        # Additional validation after conversion
        if end_date < start_date:
            flash('End date must be after start date', 'error')
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        if billable_hours < 0.2:
            flash('Billable hours must be at least 0.2 hours (12 minutes)', 'error')
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        # ===== METER VALIDATION SECTION =====
        # Validate meter verification toggle is checked
        if not meter_verification_toggle:
            flash('Meter verification is required. Please confirm the meters are correct.', 'error')
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
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
        MaintenanceWorkPortalService(event_id).complete_from_work_portal(
            user_id=current_user.id,
            username=current_user.username,
            completion_comment=completion_comment,
            start_date=start_date,
            end_date=end_date,
            billable_hours=billable_hours,
            meter1=meter1,
            meter2=meter2,
            meter3=meter3,
            meter4=meter4,
        )
        
        flash('Maintenance completed successfully', 'success')
        return redirect(url_for('maintenance_event_view.view_maintenance_event', event_id=event_id))
        
    except ValueError as e:
        # Handle meter validation errors specifically
        error_message = str(e)
        if 'meter' in error_message.lower() or 'verification' in error_message.lower():
            flash(f'Meter verification failed: {error_message}', 'error')
        else:
            flash(f'Validation error: {error_message}', 'error')
        logger.warning(f"Meter validation failed for event {event_id}: {e}")
        return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error completing maintenance: {e}", exc_info=True)
        flash('Error completing maintenance', 'error')
        return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))




@maintenance_event_bp.route('/<int:event_id>/blocker/create', methods=['POST'])
@login_required
def create_blocker(event_id):
    """Create a blocked status for maintenance event"""
    try:
        # ===== FORM PARSING SECTION =====
        reason = request.form.get('reason', '').strip()
        notes = request.form.get('notes', '').strip()
        start_time_str = request.form.get('start_time', '').strip()
        billable_hours_lost_str = request.form.get('billable_hours_lost', '').strip()
        event_priority = request.form.get('event_priority', '').strip()
        comment_to_add_to_event = request.form.get('comment_to_add_to_event', '').strip()
        
        # ===== LIGHT VALIDATION SECTION =====
        blocker_instance = MaintenanceBlocker()  # Temporary instance to access properties
        allowable_reasons = blocker_instance.allowable_reasons
        
        if not reason or reason not in allowable_reasons:
            flash('Valid reason is required', 'error')
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        # ===== DATA TYPE CONVERSION SECTION =====
        start_time = None
        if start_time_str:
            try:
                start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid start time format', 'error')
                return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        billable_hours_lost = None
        if billable_hours_lost_str:
            try:
                billable_hours_lost = float(billable_hours_lost_str)
                if billable_hours_lost < 0:
                    flash('Billable hours lost must be non-negative', 'error')
                    return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
            except ValueError:
                pass  # Ignore invalid values
        
        # ===== BUSINESS LOGIC SECTION =====
        maintenance_context = MaintenanceContext.from_event(event_id)
        maintenance_context.get_blocker_creation_manager().create_blocker(
            reason=reason,
            notes=notes or None,
            start_time=start_time,
            billable_hours_lost=billable_hours_lost,
            user_id=current_user.id,
            username=current_user.username,
            event_priority=event_priority or None,
            comment_to_add_to_event=comment_to_add_to_event or None,
        )
        
        flash('Blocked status created successfully', 'success')
        return redirect(url_for('maintenance_event_view.view_maintenance_event', event_id=event_id))
        
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
    except Exception as e:
        logger.error(f"Error creating blocked status: {e}")
        import traceback
        traceback.print_exc()
        flash('Error creating blocked status', 'error')
        return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))


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

