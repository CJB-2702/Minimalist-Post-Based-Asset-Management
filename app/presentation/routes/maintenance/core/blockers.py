"""
blocked_status management routes
"""
from flask import Blueprint, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from datetime import datetime
from app.logger import get_logger
from app import db
from app.data.maintenance.base.maintenance_blockers import MaintenanceBlocker
from app.buisness.maintenance.base.structs.maintenance_action_set_struct import MaintenanceActionSetStruct
from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
from app.buisness.core.event_context import EventContext

logger = get_logger("asset_management.routes.maintenance")

# Import maintenance_bp from main maintenance routes
from app.presentation.routes.maintenance.main import maintenance_bp


@maintenance_bp.route('/blocked_status/<int:blocked_status_id>/end', methods=['POST'])
@login_required
def end_blocked_status(blocked_status_id):
    """End an active blocked status"""
    try:
        blocked_status = MaintenanceBlocker.query.get_or_404(blocked_status_id)
        
        if blocked_status.end_date:
            flash('Blocked status is already ended', 'warning')
            # Get event_id from blocked_status's maintenance_action_set for redirect
            maintenance_context = MaintenanceContext.from_maintenance_action_set(blocked_status.maintenance_action_set_id)
            struct: MaintenanceActionSetStruct = maintenance_context.struct
            if struct.event_id:
                return redirect(url_for('maintenance_event.view_maintenance_event', event_id=struct.event_id))
            abort(404)
        
        # Get form data (all required fields)
        blocked_status_start_date_str = request.form.get('blocked_status_start_date', '').strip()
        blocked_status_end_date_str = request.form.get('blocked_status_end_date', '').strip()
        blocked_status_billable_hours_str = request.form.get('blocked_status_billable_hours', '').strip()
        blocked_status_notes = request.form.get('blocked_status_notes', '').strip()
        comment = request.form.get('comment', '').strip()
        
        # Validate required fields
        if not blocked_status_start_date_str:
            flash('Start time is required', 'error')
            maintenance_context = MaintenanceContext.from_maintenance_action_set(blocked_status.maintenance_action_set_id)
            struct: MaintenanceActionSetStruct = maintenance_context.struct
            if struct.event_id:
                return redirect(url_for('maintenance_event.view_maintenance_event', event_id=struct.event_id))
            abort(404)
        
        if not blocked_status_end_date_str:
            flash('End time is required', 'error')
            maintenance_context = MaintenanceContext.from_maintenance_action_set(blocked_status.maintenance_action_set_id)
            struct: MaintenanceActionSetStruct = maintenance_context.struct
            if struct.event_id:
                return redirect(url_for('maintenance_event.view_maintenance_event', event_id=struct.event_id))
            abort(404)
        
        if not blocked_status_billable_hours_str:
            flash('Billable hours lost is required', 'error')
            maintenance_context = MaintenanceContext.from_maintenance_action_set(blocked_status.maintenance_action_set_id)
            struct: MaintenanceActionSetStruct = maintenance_context.struct
            if struct.event_id:
                return redirect(url_for('maintenance_event.view_maintenance_event', event_id=struct.event_id))
            abort(404)
        
        # Parse dates
        try:
            blocked_status_start_date = datetime.strptime(blocked_status_start_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid blocked start date format', 'error')
            maintenance_context = MaintenanceContext.from_maintenance_action_set(blocked_status.maintenance_action_set_id)
            struct: MaintenanceActionSetStruct = maintenance_context.struct
            if struct.event_id:
                return redirect(url_for('maintenance_event.view_maintenance_event', event_id=struct.event_id))
            abort(404)
        
        try:
            blocked_status_end_date = datetime.strptime(blocked_status_end_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid blocked end date format', 'error')
            maintenance_context = MaintenanceContext.from_maintenance_action_set(blocked_status.maintenance_action_set_id)
            struct: MaintenanceActionSetStruct = maintenance_context.struct
            if struct.event_id:
                return redirect(url_for('maintenance_event.view_maintenance_event', event_id=struct.event_id))
            abort(404)
        
        # Parse billable hours (required, allows 0)
        try:
            blocked_status_billable_hours = float(blocked_status_billable_hours_str)
            if blocked_status_billable_hours < 0:
                flash('Billable hours must be zero or greater', 'error')
                maintenance_context = MaintenanceContext.from_maintenance_action_set(blocked_status.maintenance_action_set_id)
                struct: MaintenanceActionSetStruct = maintenance_context.struct
                if struct.event_id:
                    return redirect(url_for('maintenance_event.view_maintenance_event', event_id=struct.event_id))
                abort(404)
        except ValueError:
            flash('Invalid billable hours format', 'error')
            maintenance_context = MaintenanceContext.from_maintenance_action_set(blocked_status.maintenance_action_set_id)
            struct: MaintenanceActionSetStruct = maintenance_context.struct
            if struct.event_id:
                return redirect(url_for('maintenance_event.view_maintenance_event', event_id=struct.event_id))
            abort(404)
        
        # Create MaintenanceContext from blocked_status's maintenance_action_set_id
        maintenance_context = MaintenanceContext.from_maintenance_action_set(blocked_status.maintenance_action_set_id)
        struct: MaintenanceActionSetStruct = maintenance_context.struct
        
        # Get blocker manager and end blocked_status
        blocker_manager = maintenance_context.get_blocker_manager()
        blocker_manager.end_blocker(
            blocker_id=blocked_status_id, 
            user_id=current_user.id,
            blocked_status_start_date=blocked_status_start_date,
            blocked_status_end_date=blocked_status_end_date
        )
        
        # Update notes, billable hours, and start date (all required fields are always provided)
        blocker_manager.update_blocker(
            blocker_id=blocked_status_id,
            billable_hours=blocked_status_billable_hours,
            start_date=blocked_status_start_date,
            notes=blocked_status_notes
        )
        
        # Sync event status
        maintenance_context._sync_event_status()
        
        # Generate comment - use user's comment if provided, otherwise use automated one
        if struct.event_id:
            event_context = EventContext(struct.event_id)
            if comment:
                comment_text = f"Blocked status ended by {current_user.username}. {comment}"
                event_context.add_comment(
                    user_id=current_user.id,
                    content=comment_text,
                    is_human_made=True
                )
            else:
                comment_text = f"Blocked status ended by {current_user.username}. Maintenance work resumed."
                event_context.add_comment(
                    user_id=current_user.id,
                    content=comment_text,
                    is_human_made=False  # Automated comment
                )
            db.session.commit()
        
        # Update asset blocked status after ending blocker
        blocker_manager.update_asset_blocked_status()
        
        flash('Blocked status ended successfully. Work can now continue.', 'success')
        return redirect(url_for('maintenance_event.view_maintenance_event', event_id=struct.event_id))
        
    except Exception as e:
        logger.error(f"Error ending blocked status: {e}")
        flash('Error ending blocked status', 'error')
        # Try to get event_id for redirect, but don't fail if we can't
        try:
            blocked_status = MaintenanceBlocker.query.get(blocked_status_id)
            if blocked_status:
                maintenance_context = MaintenanceContext.from_maintenance_action_set(blocked_status.maintenance_action_set_id)
                struct: MaintenanceActionSetStruct = maintenance_context.struct
                if struct.event_id:
                    return redirect(url_for('maintenance_event.view_maintenance_event', event_id=struct.event_id))
        except:
            pass
        abort(404)


@maintenance_bp.route('/blocked_status/<int:blocked_status_id>/update', methods=['POST'])
@login_required
def update_blocked_status(blocked_status_id):
    """Update blocked_status details"""
    try:
        # Get blocked_status first
        blocked_status = MaintenanceBlocker.query.get_or_404(blocked_status_id)
        
        # Create MaintenanceContext from blocked_status's maintenance_action_set_id
        maintenance_context = MaintenanceContext.from_maintenance_action_set(blocked_status.maintenance_action_set_id)
        struct: MaintenanceActionSetStruct = maintenance_context.struct
        
        # Get blocker manager
        blocker_manager = maintenance_context.get_blocker_manager()
        
        # Get event_id from struct for redirects
        event_id = struct.event_id
        if not event_id:
            flash('Maintenance event not found', 'error')
            abort(404)
        
        # ===== FORM PARSING SECTION =====
        blocked_status_type = request.form.get('blocked_status_type', '').strip()
        blocked_status_reason = request.form.get('blocked_status_reason', '').strip()
        blocked_status_start_date_str = request.form.get('blocked_status_start_date', '').strip()
        blocked_status_end_date_str = request.form.get('blocked_status_end_date', '').strip()
        blocked_status_billable_hours_str = request.form.get('blocked_status_billable_hours', '').strip()
        blocked_status_notes = request.form.get('blocked_status_notes', '').strip()
        priority = request.form.get('priority', '').strip()
        
        # ===== LIGHT VALIDATION SECTION =====
        if blocked_status_type and blocked_status_type not in ['Work in blocked_status', 'Cancellation Requested']:
            flash('Invalid blocked_status type', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        if blocked_status_reason and not blocked_status_reason:
            flash('blocked_status reason cannot be empty', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # ===== DATA TYPE CONVERSION SECTION =====
        blocked_status_start_date = None
        if blocked_status_start_date_str:
            try:
                blocked_status_start_date = datetime.strptime(blocked_status_start_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid blocked_status start date format', 'error')
                return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        blocked_status_end_date = None
        if blocked_status_end_date_str:
            try:
                blocked_status_end_date = datetime.strptime(blocked_status_end_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid blocked_status end date format', 'error')
                return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        blocked_status_billable_hours = None
        if blocked_status_billable_hours_str:
            try:
                blocked_status_billable_hours = float(blocked_status_billable_hours_str)
                if blocked_status_billable_hours < 0:
                    flash('Billable hours must be non-negative', 'error')
                    return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
            except ValueError:
                pass  # Ignore invalid values
        
        if priority and priority not in ['Low', 'Medium', 'High', 'Critical']:
            priority = None  # Use existing value if invalid
        
        # Convert empty strings to None
        blocked_status_type = blocked_status_type if blocked_status_type else None
        blocked_status_reason = blocked_status_reason if blocked_status_reason else None
        blocked_status_notes = blocked_status_notes if blocked_status_notes else None
        priority = priority if priority else None
        
        # Update blocked_status using blocker manager
        try:
            blocker_manager.update_blocker(
                blocker_id=blocked_status_id,
                mission_capability_status=blocked_status_type,
                reason=blocked_status_reason,
                start_date=blocked_status_start_date,
                end_date=blocked_status_end_date,
                billable_hours=blocked_status_billable_hours,
                notes=blocked_status_notes,
                priority=priority
            )
            # Sync event status if blocker was ended
            if blocked_status_end_date is not None:
                maintenance_context._sync_event_status()
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # Generate automated comment
        if struct.event_id:
            event_context = EventContext(struct.event_id)
            comment_text = f"blocked_status updated by {current_user.username}."
            if blocked_status_reason:
                comment_text += f" Reason: {blocked_status_reason}"
            event_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=True
            )
            db.session.commit()
        
        flash('blocked_status updated successfully', 'success')
        return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error updating blocked_status: {e}")
        import traceback
        traceback.print_exc()
        flash('Error updating blocked_status', 'error')
        # Try to get event_id for redirect, but don't fail if we can't
        try:
            blocked_status = MaintenanceBlocker.query.get(blocked_status_id)
            if blocked_status:
                maintenance_context = MaintenanceContext.from_maintenance_action_set(blocked_status.maintenance_action_set_id)
                struct: MaintenanceActionSetStruct = maintenance_context.struct
                if struct.event_id:
                    return redirect(url_for('maintenance_event.render_edit_page', event_id=struct.event_id))
        except:
            pass
        abort(404)

