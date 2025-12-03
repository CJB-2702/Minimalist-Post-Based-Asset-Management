"""
Delay management routes
"""
from flask import Blueprint, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from datetime import datetime
from app.logger import get_logger
from app import db
from app.data.maintenance.base.maintenance_delays import MaintenanceDelay
from app.buisness.maintenance.base.maintenance_action_set_struct import MaintenanceActionSetStruct
from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
from app.buisness.core.event_context import EventContext

logger = get_logger("asset_management.routes.maintenance")

# Import maintenance_bp from main maintenance routes
from app.presentation.routes.maintenance.main import maintenance_bp


@maintenance_bp.route('/delay/<int:delay_id>/end', methods=['POST'])
@login_required
def end_delay(delay_id):
    """End an active delay"""
    try:
        delay = MaintenanceDelay.query.get_or_404(delay_id)
        
        if delay.delay_end_date:
            flash('Delay is already ended', 'warning')
            # Get event_id from delay's maintenance_action_set for redirect
            maintenance_context = MaintenanceContext.from_maintenance_action_set(delay.maintenance_action_set_id)
            struct: MaintenanceActionSetStruct = maintenance_context.struct
            if struct.event_id:
                return redirect(url_for('maintenance_event.view_maintenance_event', event_id=struct.event_id))
            abort(404)
        
        # Get form data
        delay_start_date_str = request.form.get('delay_start_date')
        delay_end_date_str = request.form.get('delay_end_date')
        comment = request.form.get('comment', '').strip()
        
        # Parse dates
        delay_start_date = None
        if delay_start_date_str:
            try:
                delay_start_date = datetime.strptime(delay_start_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid delay start date format', 'error')
                # Get event_id from delay's maintenance_action_set for redirect
                maintenance_context = MaintenanceContext.from_maintenance_action_set(delay.maintenance_action_set_id)
                struct: MaintenanceActionSetStruct = maintenance_context.struct
                if struct.event_id:
                    return redirect(url_for('maintenance_event.view_maintenance_event', event_id=struct.event_id))
                abort(404)
        
        delay_end_date = None
        if delay_end_date_str:
            try:
                delay_end_date = datetime.strptime(delay_end_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid delay end date format', 'error')
                # Get event_id from delay's maintenance_action_set for redirect
                maintenance_context = MaintenanceContext.from_maintenance_action_set(delay.maintenance_action_set_id)
                struct: MaintenanceActionSetStruct = maintenance_context.struct
                if struct.event_id:
                    return redirect(url_for('maintenance_event.view_maintenance_event', event_id=struct.event_id))
                abort(404)
        
        # Create MaintenanceContext from delay's maintenance_action_set_id
        maintenance_context = MaintenanceContext.from_maintenance_action_set(delay.maintenance_action_set_id)
        struct: MaintenanceActionSetStruct = maintenance_context.struct
        
        # Use context manager to end delay (will sync Event.status)
        maintenance_context.end_delay(
            delay_id=delay_id, 
            user_id=current_user.id,
            delay_start_date=delay_start_date,
            delay_end_date=delay_end_date
        )
        
        # Generate comment - use user's comment if provided, otherwise use automated one
        if struct.event_id:
            event_context = EventContext(struct.event_id)
            if comment:
                comment_text = f"Delay ended by {current_user.username}. {comment}"
                event_context.add_comment(
                    user_id=current_user.id,
                    content=comment_text,
                    is_human_made=True
                )
            else:
                comment_text = f"Delay ended by {current_user.username}. Maintenance work resumed."
                event_context.add_comment(
                    user_id=current_user.id,
                    content=comment_text,
                    is_human_made=False  # Automated comment
                )
            db.session.commit()
        
        flash('Delay ended successfully. Work can now continue.', 'success')
        return redirect(url_for('maintenance_event.view_maintenance_event', event_id=struct.event_id))
        
    except Exception as e:
        logger.error(f"Error ending delay: {e}")
        flash('Error ending delay', 'error')
        # Try to get event_id for redirect, but don't fail if we can't
        try:
            delay = MaintenanceDelay.query.get(delay_id)
            if delay:
                maintenance_context = MaintenanceContext.from_maintenance_action_set(delay.maintenance_action_set_id)
                struct: MaintenanceActionSetStruct = maintenance_context.struct
                if struct.event_id:
                    return redirect(url_for('maintenance_event.view_maintenance_event', event_id=struct.event_id))
        except:
            pass
        abort(404)


@maintenance_bp.route('/delay/<int:delay_id>/update', methods=['POST'])
@login_required
def update_delay(delay_id):
    """Update delay details"""
    try:
        # Get delay first
        delay = MaintenanceDelay.query.get_or_404(delay_id)
        
        # Create MaintenanceContext from delay's maintenance_action_set_id
        maintenance_context = MaintenanceContext.from_maintenance_action_set(delay.maintenance_action_set_id)
        struct: MaintenanceActionSetStruct = maintenance_context.struct
        
        # Get event_id from struct for redirects
        event_id = struct.event_id
        if not event_id:
            flash('Maintenance event not found', 'error')
            abort(404)
        
        # ===== FORM PARSING SECTION =====
        delay_type = request.form.get('delay_type', '').strip()
        delay_reason = request.form.get('delay_reason', '').strip()
        delay_start_date_str = request.form.get('delay_start_date', '').strip()
        delay_end_date_str = request.form.get('delay_end_date', '').strip()
        delay_billable_hours_str = request.form.get('delay_billable_hours', '').strip()
        delay_notes = request.form.get('delay_notes', '').strip()
        priority = request.form.get('priority', '').strip()
        
        # ===== LIGHT VALIDATION SECTION =====
        if delay_type and delay_type not in ['Work in Delay', 'Cancellation Requested']:
            flash('Invalid delay type', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        if delay_reason and not delay_reason:
            flash('Delay reason cannot be empty', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # ===== DATA TYPE CONVERSION SECTION =====
        delay_start_date = None
        if delay_start_date_str:
            try:
                delay_start_date = datetime.strptime(delay_start_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid delay start date format', 'error')
                return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        delay_end_date = None
        if delay_end_date_str:
            try:
                delay_end_date = datetime.strptime(delay_end_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid delay end date format', 'error')
                return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        delay_billable_hours = None
        if delay_billable_hours_str:
            try:
                delay_billable_hours = float(delay_billable_hours_str)
                if delay_billable_hours < 0:
                    flash('Billable hours must be non-negative', 'error')
                    return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
            except ValueError:
                pass  # Ignore invalid values
        
        if priority and priority not in ['Low', 'Medium', 'High', 'Critical']:
            priority = None  # Use existing value if invalid
        
        # Convert empty strings to None
        delay_type = delay_type if delay_type else None
        delay_reason = delay_reason if delay_reason else None
        delay_notes = delay_notes if delay_notes else None
        priority = priority if priority else None
        
        # Build update dict with only non-None values
        update_kwargs = {}
        if delay_type is not None:
            update_kwargs['delay_type'] = delay_type
        if delay_reason is not None:
            update_kwargs['delay_reason'] = delay_reason
        if delay_start_date is not None:
            update_kwargs['delay_start_date'] = delay_start_date
        if delay_end_date is not None:
            update_kwargs['delay_end_date'] = delay_end_date
        if delay_billable_hours is not None:
            update_kwargs['delay_billable_hours'] = delay_billable_hours
        if delay_notes is not None:
            update_kwargs['delay_notes'] = delay_notes
        if priority is not None:
            update_kwargs['priority'] = priority
        
        # Update delay
        try:
            maintenance_context.update_delay(delay_id=delay_id, **update_kwargs)
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # Generate automated comment
        if struct.event_id:
            event_context = EventContext(struct.event_id)
            comment_text = f"Delay updated by {current_user.username}."
            if delay_reason:
                comment_text += f" Reason: {delay_reason}"
            event_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=True
            )
            db.session.commit()
        
        flash('Delay updated successfully', 'success')
        return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error updating delay: {e}")
        import traceback
        traceback.print_exc()
        flash('Error updating delay', 'error')
        # Try to get event_id for redirect, but don't fail if we can't
        try:
            delay = MaintenanceDelay.query.get(delay_id)
            if delay:
                maintenance_context = MaintenanceContext.from_maintenance_action_set(delay.maintenance_action_set_id)
                struct: MaintenanceActionSetStruct = maintenance_context.struct
                if struct.event_id:
                    return redirect(url_for('maintenance_event.render_edit_page', event_id=struct.event_id))
        except:
            pass
        abort(404)

