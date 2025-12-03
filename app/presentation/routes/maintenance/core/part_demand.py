"""
Part demand management routes
"""
from flask import Blueprint, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from app.logger import get_logger
from app import db
from app.data.maintenance.base.part_demands import PartDemand
from app.buisness.maintenance.base.maintenance_action_set_struct import MaintenanceActionSetStruct
from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
from app.buisness.core.event_context import EventContext

logger = get_logger("asset_management.routes.maintenance")

# Import maintenance_bp from main maintenance routes
from app.presentation.routes.maintenance.main import maintenance_bp


@maintenance_bp.route('/part-demand/<int:part_demand_id>/issue', methods=['POST'])
@login_required
def issue_part_demand(part_demand_id):
    """Issue a part demand (any user can issue)"""
    try:
        part_demand = PartDemand.query.get_or_404(part_demand_id)
        
        # Get action to access maintenance_action_set_id
        from app.data.maintenance.base.actions import Action
        action = Action.query.get_or_404(part_demand.action_id)
        
        # Create MaintenanceContext from action's maintenance_action_set_id
        maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
        struct: MaintenanceActionSetStruct = maintenance_context.struct
        
        # Update status to Issued
        part_demand.status = 'Issued'
        db.session.commit()
        
        # Generate automated comment
        if struct.event_id:
            event_context = EventContext(struct.event_id)
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
        return redirect(url_for('maintenance_event.work_maintenance_event', event_id=struct.event_id))
        
    except Exception as e:
        logger.error(f"Error issuing part demand: {e}")
        flash('Error issuing part', 'error')
        # Try to get event_id for redirect, but don't fail if we can't
        try:
            part_demand = PartDemand.query.get(part_demand_id)
            if part_demand:
                from app.data.maintenance.base.actions import Action
                action = Action.query.get(part_demand.action_id)
                if action:
                    maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
                    struct: MaintenanceActionSetStruct = maintenance_context.struct
                    if struct.event_id:
                        return redirect(url_for('maintenance_event.work_maintenance_event', event_id=struct.event_id))
        except:
            pass
        abort(404)


@maintenance_bp.route('/part-demand/<int:part_demand_id>/cancel', methods=['POST'])
@login_required
def cancel_part_demand(part_demand_id):
    """Cancel a part demand (technician can cancel if not issued)"""
    try:
        part_demand = PartDemand.query.get_or_404(part_demand_id)
        
        # Get action to access maintenance_action_set_id
        from app.data.maintenance.base.actions import Action
        action = Action.query.get_or_404(part_demand.action_id)
        
        # Create MaintenanceContext from action's maintenance_action_set_id
        maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
        struct: MaintenanceActionSetStruct = maintenance_context.struct
        
        # Check if already issued
        if part_demand.status == 'Issued':
            flash('Cannot cancel an issued part demand', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=struct.event_id))
        
        # Require cancellation comment
        cancellation_comment = request.form.get('cancellation_comment', '').strip()
        if not cancellation_comment:
            flash('Cancellation comment is required', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=struct.event_id))
        
        # Update status
        part_demand.status = 'Cancelled by Technician'
        db.session.commit()
        
        # Generate automated comment
        if struct.event_id:
            event_context = EventContext(struct.event_id)
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
        return redirect(url_for('maintenance_event.work_maintenance_event', event_id=struct.event_id))
        
    except Exception as e:
        logger.error(f"Error cancelling part demand: {e}")
        flash('Error cancelling part demand', 'error')
        # Try to get event_id for redirect, but don't fail if we can't
        try:
            part_demand = PartDemand.query.get(part_demand_id)
            if part_demand:
                from app.data.maintenance.base.actions import Action
                action = Action.query.get(part_demand.action_id)
                if action:
                    maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
                    struct: MaintenanceActionSetStruct = maintenance_context.struct
                    if struct.event_id:
                        return redirect(url_for('maintenance_event.work_maintenance_event', event_id=struct.event_id))
        except:
            pass
        abort(404)


@maintenance_bp.route('/part-demand/<int:part_demand_id>/undo', methods=['POST'])
@login_required
def undo_part_demand(part_demand_id):
    """Undo a cancelled part demand - reset it back to Planned status"""
    try:
        part_demand = PartDemand.query.get_or_404(part_demand_id)
        
        # Get action to access maintenance_action_set_id
        from app.data.maintenance.base.actions import Action
        action = Action.query.get_or_404(part_demand.action_id)
        
        # Create MaintenanceContext from action's maintenance_action_set_id
        maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
        struct: MaintenanceActionSetStruct = maintenance_context.struct
        
        # Only allow undo if status is cancelled
        if part_demand.status not in ['Cancelled by Technician', 'Cancelled by Supply']:
            flash('Can only undo cancelled part demands', 'error')
            return redirect(url_for('maintenance_event.work_maintenance_event', event_id=struct.event_id))
        
        # Reset status to Planned (default state)
        part_demand.status = 'Planned'
        db.session.commit()
        
        # Generate automated comment
        if struct.event_id:
            event_context = EventContext(struct.event_id)
            from app.data.core.supply.part import Part
            part = Part.query.get(part_demand.part_id)
            part_name = part.part_name if part else f"Part #{part_demand.part_id}"
            comment_text = f"Part demand reset to planned: {part_name} x{part_demand.quantity_required} by {current_user.username}"
            event_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=False  # Automated comment
            )
            db.session.commit()
        
        flash('Part demand reset to planned successfully', 'success')
        return redirect(url_for('maintenance_event.work_maintenance_event', event_id=struct.event_id))
        
    except Exception as e:
        logger.error(f"Error undoing part demand: {e}")
        flash('Error undoing part demand', 'error')
        # Try to get event_id for redirect, but don't fail if we can't
        try:
            part_demand = PartDemand.query.get(part_demand_id)
            if part_demand:
                from app.data.maintenance.base.actions import Action
                action = Action.query.get(part_demand.action_id)
                if action:
                    maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
                    struct: MaintenanceActionSetStruct = maintenance_context.struct
                    if struct.event_id:
                        return redirect(url_for('maintenance_event.work_maintenance_event', event_id=struct.event_id))
        except:
            pass
        abort(404)


@maintenance_bp.route('/part-demand/<int:part_demand_id>/update', methods=['POST'])
@login_required
def update_part_demand(part_demand_id):
    """Update part demand details"""
    try:
        # Get part demand
        part_demand = PartDemand.query.get_or_404(part_demand_id)
        
        # Get action to access maintenance_action_set_id
        from app.data.maintenance.base.actions import Action
        action = Action.query.get_or_404(part_demand.action_id)
        
        # Create MaintenanceContext from action's maintenance_action_set_id
        maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
        struct: MaintenanceActionSetStruct = maintenance_context.struct
        
        # Get event_id from struct for redirects
        event_id = struct.event_id
        if not event_id:
            flash('Maintenance event not found', 'error')
            abort(404)
        
        # ===== FORM PARSING SECTION =====
        # Note: part_id should NOT be editable per requirements
        quantity_required_str = request.form.get('quantity_required', '').strip()
        status = request.form.get('status', '').strip()
        priority = request.form.get('priority', '').strip()
        notes = request.form.get('notes', '').strip()
        
        # ===== LIGHT VALIDATION SECTION =====
        valid_statuses = [
            'Planned', 'Pending Manager Approval', 'Pending Inventory Approval',
            'Ordered', 'Issued', 'Rejected', 'Backordered',
            'Cancelled by Technician', 'Cancelled by Supply'
        ]
        if status and status not in valid_statuses:
            flash('Invalid status', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        valid_priorities = ['Low', 'Medium', 'High', 'Critical']
        if priority and priority not in valid_priorities:
            priority = None  # Use existing value if invalid
        
        # ===== DATA TYPE CONVERSION SECTION =====
        quantity_required = None
        if quantity_required_str:
            try:
                quantity_required = float(quantity_required_str)
                if quantity_required <= 0:
                    flash('Quantity must be greater than 0', 'error')
                    return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
            except ValueError:
                flash('Invalid quantity value', 'error')
                return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        # Convert empty strings to None
        status = status if status else None
        priority = priority if priority else None
        notes = notes if notes else None
        
        # ===== BUSINESS LOGIC SECTION =====
        # Update fields
        if quantity_required is not None:
            part_demand.quantity_required = quantity_required
        if status is not None:
            part_demand.status = status
        if priority is not None:
            part_demand.priority = priority
        if notes is not None:
            part_demand.notes = notes
        
        part_demand.updated_by_id = current_user.id
        db.session.commit()
        
        # Generate automated comment
        if struct.event_id:
            event_context = EventContext(struct.event_id)
            from app.data.core.supply.part import Part
            part = Part.query.get(part_demand.part_id)
            part_name = part.part_name if part else f"Part #{part_demand.part_id}"
            comment_text = f"Part demand updated: {part_name} x{part_demand.quantity_required} by {current_user.username}"
            if status:
                comment_text += f". Status: {status}"
            event_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=True
            )
            db.session.commit()
        
        flash('Part demand updated successfully', 'success')
        return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error updating part demand: {e}")
        import traceback
        traceback.print_exc()
        flash('Error updating part demand', 'error')
        # Try to get event_id for redirect, but don't fail if we can't
        try:
            part_demand = PartDemand.query.get(part_demand_id)
            if part_demand:
                from app.data.maintenance.base.actions import Action
                action = Action.query.get(part_demand.action_id)
                if action:
                    maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
                    struct: MaintenanceActionSetStruct = maintenance_context.struct
                    if struct.event_id:
                        return redirect(url_for('maintenance_event.render_edit_page', event_id=struct.event_id))
        except:
            pass
        abort(404)
