"""
Asset Limitation Records management routes
"""
from flask import request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from datetime import datetime
from app.logger import get_logger
from app import db
from app.data.maintenance.base.asset_limitation_records import AssetLimitationRecord
from app.buisness.maintenance.base.maintenance_context import MaintenanceContext

logger = get_logger("asset_management.routes.maintenance.limitations")

# Import maintenance_bp from main maintenance routes
from app.presentation.routes.maintenance.main import maintenance_bp


@maintenance_bp.route('/limitation/<int:limitation_id>/close', methods=['POST'])
@login_required
def close_limitation(limitation_id):
    """Close an active asset limitation record"""
    try:
        limitation = AssetLimitationRecord.query.get_or_404(limitation_id)
        
        # Get maintenance context
        maintenance_context = MaintenanceContext.from_maintenance_action_set(limitation.maintenance_action_set_id)
        event_id = maintenance_context.event_id
        
        if limitation.end_time:
            flash('Limitation is already closed', 'warning')
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        # Get form data
        start_time_str = request.form.get('start_time', '').strip()
        end_time_str = request.form.get('end_time', '').strip()
        comment = request.form.get('comment', '').strip()
        
        # Validate required fields
        if not start_time_str:
            flash('Start time is required', 'error')
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        if not end_time_str:
            flash('End time is required', 'error')
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        # Parse times
        try:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid start time format', 'error')
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        try:
            end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid end time format', 'error')
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        # Close limitation record using manager
        limitation_manager = maintenance_context.get_limitation_manager()
        limitation_manager.close_record(
            record_id=limitation_id,
            start_time=start_time,
            end_time=end_time,
            user_id=current_user.id
        )
        
        # Add comment to event
        if comment:
            comment_text = f"Asset limitation closed by {current_user.username}. {comment}"
            maintenance_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=True
            )
        else:
            comment_text = f"Asset limitation closed by {current_user.username}. Asset capability restored."
            maintenance_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=False
            )
        db.session.commit()
        
        flash('Asset limitation closed successfully', 'success')
        return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
    except ValueError as e:
        logger.error(f"Validation error closing limitation: {e}")
        flash(str(e), 'error')
        try:
            limitation = AssetLimitationRecord.query.get(limitation_id)
            if limitation:
                maintenance_context = MaintenanceContext.from_maintenance_action_set(limitation.maintenance_action_set_id)
                return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=maintenance_context.event_id))
        except Exception:
            pass
        abort(404)
    except Exception as e:
        logger.error(f"Error closing limitation: {e}")
        import traceback
        traceback.print_exc()
        flash('Error closing limitation', 'error')
        try:
            limitation = AssetLimitationRecord.query.get(limitation_id)
            if limitation:
                maintenance_context = MaintenanceContext.from_maintenance_action_set(limitation.maintenance_action_set_id)
                return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=maintenance_context.event_id))
        except Exception:
            pass
        abort(404)


@maintenance_bp.route('/maintenance-event/<int:event_id>/limitation/create', methods=['POST'])
@login_required
def create_limitation(event_id):
    """Create a new asset limitation record for a maintenance event"""
    try:
        # Get maintenance context from event_id
        maintenance_context = MaintenanceContext.from_event(event_id)
        
        # Get form data
        status = request.form.get('limitation_status', '').strip()
        limitation_description = request.form.get('limitation_description', '').strip()
        temporary_modifications = request.form.get('temporary_modifications', '').strip()
        start_time_str = request.form.get('start_time', '').strip()
        comment = request.form.get('comment', '').strip()
        link_to_blocker = request.form.get('link_to_blocker') == 'true'
        
        # Validate required fields
        if not status:
            flash('Limitation status is required', 'error')
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        if not start_time_str:
            flash('Start time is required', 'error')
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        # Parse start time
        try:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid start time format', 'error')
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        # Get active blocker if linking is requested
        active_blocker_id = None
        if link_to_blocker:
            active_blockers = [b for b in maintenance_context.struct.blockers if b.end_date is None]
            if active_blockers:
                active_blocker_id = active_blockers[0].id
        
        # Create limitation record using manager
        limitation_manager = maintenance_context.get_limitation_manager()
        try:
            limitation_manager.create_record(
                status=status,
                limitation_description=limitation_description if limitation_description else None,
                temporary_modifications=temporary_modifications if temporary_modifications else None,
                start_time=start_time,
                maintenance_blocker_id=active_blocker_id,
                user_id=current_user.id
            )
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        # Add comment to event
        if comment:
            comment_text = f"Asset limitation created by {current_user.username}: {status}. {comment}"
            maintenance_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=True
            )
        else:
            comment_text = f"Asset limitation created by {current_user.username}: {status}"
            maintenance_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=False
            )
        db.session.commit()
        
        flash('Asset limitation created successfully', 'success')
        return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
    except ValueError as e:
        logger.error(f"Validation error creating limitation: {e}")
        flash(str(e), 'error')
        return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
    except Exception as e:
        logger.error(f"Error creating limitation: {e}")
        import traceback
        traceback.print_exc()
        flash('Error creating limitation', 'error')
        return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
