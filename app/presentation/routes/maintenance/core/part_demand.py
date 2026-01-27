"""
Part demand management routes
"""
from flask import request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from app.logger import get_logger

# Import maintenance_bp from main maintenance routes
from app.presentation.routes.maintenance.main import maintenance_bp

from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.part_demands import PartDemand
from app.services.maintenance.maintenance_supply_workflow import MaintenanceSupplyWorkflowService

logger = get_logger("asset_management.routes.maintenance")

def _redirect_from_part_demand(part_demand_id: int, endpoint: str):
    """
    Best-effort redirect helper for error cases where the service raised
    before we had an `event_id` available in the route.
    """
    try:
        part_demand = PartDemand.query.get(part_demand_id)
        if not part_demand:
            return None
        action = Action.query.get(part_demand.action_id)
        if not action:
            return None
        maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
        if maintenance_context.event_id:
            return redirect(url_for(endpoint, event_id=maintenance_context.event_id))
    except Exception:
        return None
    return None


@maintenance_bp.route('/part-demand/<int:part_demand_id>/issue', methods=['POST'])
@login_required
def issue_part_demand(part_demand_id):
    """Issue a part demand (any user can issue)"""
    try:
        event_id = MaintenanceSupplyWorkflowService.issue_part_demand(
            part_demand_id=part_demand_id,
            user_id=current_user.id,
            username=current_user.username,
        )
        
        flash('Part issued successfully', 'success')
        return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
    except ValueError as e:
        flash(str(e), 'error')
        redirect_resp = _redirect_from_part_demand(part_demand_id, 'maintenance_event_work.work_maintenance_event')
        if redirect_resp:
            return redirect_resp
    except Exception as e:
        logger.error(f"Error issuing part demand: {e}")
        flash('Error issuing part', 'error')
        redirect_resp = _redirect_from_part_demand(part_demand_id, 'maintenance_event_work.work_maintenance_event')
        if redirect_resp:
            return redirect_resp
        abort(404)


@maintenance_bp.route('/part-demand/<int:part_demand_id>/cancel', methods=['POST'])
@login_required
def cancel_part_demand(part_demand_id):
    """Cancel a part demand (technician can cancel if not issued)"""
    try:
        cancellation_comment = request.form.get('cancellation_comment', '').strip()
        event_id = MaintenanceSupplyWorkflowService.cancel_part_demand_by_technician(
            part_demand_id=part_demand_id,
            user_id=current_user.id,
            username=current_user.username,
            reason=cancellation_comment,
        )
        
        flash('Part demand cancelled successfully', 'success')
        return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
    except ValueError as e:
        flash(str(e), 'error')
        redirect_resp = _redirect_from_part_demand(part_demand_id, 'maintenance_event_work.work_maintenance_event')
        if redirect_resp:
            return redirect_resp
    except Exception as e:
        logger.error(f"Error cancelling part demand: {e}")
        flash('Error cancelling part demand', 'error')
        redirect_resp = _redirect_from_part_demand(part_demand_id, 'maintenance_event_work.work_maintenance_event')
        if redirect_resp:
            return redirect_resp
        abort(404)


@maintenance_bp.route('/part-demand/<int:part_demand_id>/undo', methods=['POST'])
@login_required
def undo_part_demand(part_demand_id):
    """Undo a cancelled part demand - reset it back to Planned status"""
    try:
        event_id = MaintenanceSupplyWorkflowService.undo_part_demand(
            part_demand_id=part_demand_id,
            user_id=current_user.id,
            username=current_user.username,
        )
        
        flash('Part demand reset to planned successfully', 'success')
        return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
    except ValueError as e:
        flash(str(e), 'error')
        redirect_resp = _redirect_from_part_demand(part_demand_id, 'maintenance_event_work.work_maintenance_event')
        if redirect_resp:
            return redirect_resp
    except Exception as e:
        logger.error(f"Error undoing part demand: {e}")
        flash('Error undoing part demand', 'error')
        redirect_resp = _redirect_from_part_demand(part_demand_id, 'maintenance_event_work.work_maintenance_event')
        if redirect_resp:
            return redirect_resp
        abort(404)


@maintenance_bp.route('/part-demand/<int:part_demand_id>/update', methods=['POST'])
@login_required
def update_part_demand(part_demand_id):
    """Update part demand details"""
    try:
        # ===== FORM PARSING SECTION =====
        # Note: part_id should NOT be editable per requirements
        quantity_required_str = request.form.get('quantity_required', '').strip()
        status = request.form.get('status', '').strip() or None
        priority = request.form.get('priority', '').strip() or None
        notes = request.form.get('notes', '').strip() or None
        
        # ===== DATA TYPE CONVERSION SECTION =====
        quantity_required = None
        if quantity_required_str:
            try:
                quantity_required = float(quantity_required_str)
                if quantity_required <= 0:
                    flash('Quantity must be greater than 0', 'error')
                    redirect_resp = _redirect_from_part_demand(part_demand_id, 'maintenance_event_edit.render_edit_page')
                    if redirect_resp:
                        return redirect_resp
                    abort(404)
            except ValueError:
                flash('Invalid quantity value', 'error')
                redirect_resp = _redirect_from_part_demand(part_demand_id, 'maintenance_event_edit.render_edit_page')
                if redirect_resp:
                    return redirect_resp
                abort(404)
        
        # ===== BUSINESS LOGIC SECTION =====
        event_id = MaintenanceSupplyWorkflowService.update_part_demand(
            part_demand_id=part_demand_id,
            user_id=current_user.id,
            username=current_user.username,
            quantity_required=quantity_required,
            status=status,
            priority=priority,
            notes=notes,
        )
        
        flash('Part demand updated successfully', 'success')
        return redirect(url_for('maintenance_event_edit.render_edit_page', event_id=event_id))
        
    except ValueError as e:
        flash(str(e), 'error')
        redirect_resp = _redirect_from_part_demand(part_demand_id, 'maintenance_event_edit.render_edit_page')
        if redirect_resp:
            return redirect_resp
    except Exception as e:
        logger.error(f"Error updating part demand: {e}")
        import traceback
        traceback.print_exc()
        flash('Error updating part demand', 'error')
        redirect_resp = _redirect_from_part_demand(part_demand_id, 'maintenance_event_edit.render_edit_page')
        if redirect_resp:
            return redirect_resp
        abort(404)
