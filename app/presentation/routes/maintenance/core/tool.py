"""
Tool requirement management routes for maintenance actions
"""
from flask import request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from app.logger import get_logger
from app import db
from app.data.maintenance.base.action_tools import ActionTool
from app.data.maintenance.base.actions import Action
from app.buisness.maintenance.base.maintenance_action_set_struct import MaintenanceActionSetStruct
from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
from app.buisness.core.event_context import EventContext

logger = get_logger("asset_management.routes.maintenance.tool")

# Import maintenance_bp from main maintenance routes
from app.presentation.routes.maintenance.main import maintenance_bp

@maintenance_bp.route('/action/<int:action_id>/tool/<int:tool_id>/update', methods=['POST'])
@login_required
def update_action_tool(action_id, tool_id):
    """Update tool requirement details"""
    try:
        # Get action tool (tool_id here is ActionTool.id, not Tool.id)
        action_tool = ActionTool.query.get_or_404(tool_id)
        
        # Get action first
        action = Action.query.get_or_404(action_id)
        
        # Verify action tool belongs to this action
        if action_tool.action_id != action_id:
            flash('Tool requirement does not belong to this action', 'error')
            # Get event_id for redirect
            maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
            struct: MaintenanceActionSetStruct = maintenance_context.struct
            if struct.event_id:
                return redirect(url_for('maintenance_event.render_edit_page', event_id=struct.event_id))
            abort(404)
        
        # Create MaintenanceContext from action's maintenance_action_set_id
        maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
        struct: MaintenanceActionSetStruct = maintenance_context.struct
        
        # Get event_id from struct for redirects
        event_id = struct.event_id
        if not event_id:
            flash('Maintenance event not found', 'error')
            abort(404)
        
        # ===== FORM PARSING SECTION =====
        tool_id_new_str = request.form.get('tool_id', '').strip()  # Update to different tool
        quantity_required_str = request.form.get('quantity_required', '').strip()
        status = request.form.get('status', '').strip()
        priority = request.form.get('priority', '').strip()
        notes = request.form.get('notes', '').strip()
        
        # ===== LIGHT VALIDATION SECTION =====
        valid_statuses = ['Planned', 'Assigned', 'Returned', 'Missing']
        if status and status not in valid_statuses:
            flash('Invalid status', 'error')
            return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        valid_priorities = ['Low', 'Medium', 'High', 'Critical']
        if priority and priority not in valid_priorities:
            priority = None  # Use existing value if invalid
        
        # ===== DATA TYPE CONVERSION SECTION =====
        tool_id_new = None
        if tool_id_new_str:
            try:
                tool_id_new = int(tool_id_new_str)
                # Verify tool exists
                from app.data.core.supply.tool import Tool
                tool = Tool.query.get(tool_id_new)
                if not tool:
                    flash('Tool not found', 'error')
                    return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
            except ValueError:
                flash('Invalid tool ID', 'error')
                return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
        quantity_required = None
        if quantity_required_str:
            try:
                quantity_required = int(quantity_required_str)
                if quantity_required < 1:
                    flash('Quantity must be at least 1', 'error')
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
        if tool_id_new is not None:
            action_tool.tool_id = tool_id_new
        if quantity_required is not None:
            action_tool.quantity_required = quantity_required
        if status is not None:
            action_tool.status = status
        if priority is not None:
            action_tool.priority = priority
        if notes is not None:
            action_tool.notes = notes
        
        action_tool.updated_by_id = current_user.id
        db.session.commit()
        
        # Generate automated comment
        if struct.event_id:
            event_context = EventContext(struct.event_id)
            from app.data.core.supply.tool import Tool
            tool = Tool.query.get(action_tool.tool_id)
            tool_name = tool.tool_name if tool else f"Tool #{action_tool.tool_id}"
            comment_text = f"Tool requirement updated: {tool_name} for action '{action.action_name}' by {current_user.username}"
            if status:
                comment_text += f". Status: {status}"
            event_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=True
            )
            db.session.commit()
        
        flash('Tool requirement updated successfully', 'success')
        return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error updating tool requirement: {e}")
        import traceback
        traceback.print_exc()
        flash('Error updating tool requirement', 'error')
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

@maintenance_bp.route('/action/<int:action_id>/tool/<int:tool_id>/delete', methods=['POST'])
@login_required
def delete_action_tool(action_id, tool_id):
    """Delete tool requirement"""
    try:
        # Get action tool (tool_id here is ActionTool.id, not Tool.id)
        action_tool = ActionTool.query.get_or_404(tool_id)
        
        # Get action first
        action = Action.query.get_or_404(action_id)
        
        # Verify action tool belongs to this action
        if action_tool.action_id != action_id:
            flash('Tool requirement does not belong to this action', 'error')
            # Get event_id for redirect
            maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
            struct: MaintenanceActionSetStruct = maintenance_context.struct
            if struct.event_id:
                return redirect(url_for('maintenance_event.render_edit_page', event_id=struct.event_id))
            abort(404)
        
        # Create MaintenanceContext from action's maintenance_action_set_id
        maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
        struct: MaintenanceActionSetStruct = maintenance_context.struct
        
        # Get event_id from struct for redirects
        event_id = struct.event_id
        if not event_id:
            flash('Maintenance event not found', 'error')
            abort(404)
        
        # Get tool info before deletion
        from app.data.core.supply.tool import Tool
        tool = Tool.query.get(action_tool.tool_id)
        tool_name = tool.tool_name if tool else f"Tool #{action_tool.tool_id}"
        
        # Delete action tool
        db.session.delete(action_tool)
        db.session.commit()
        
        # Generate automated comment
        if struct.event_id:
            event_context = EventContext(struct.event_id)
            comment_text = f"Tool requirement deleted: {tool_name} from action '{action.action_name}' by {current_user.username}"
            event_context.add_comment(
                user_id=current_user.id,
                content=comment_text,
                is_human_made=False  # Automated comment
            )
            db.session.commit()
        
        flash('Tool requirement deleted successfully', 'success')
        return redirect(url_for('maintenance_event.render_edit_page', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error deleting tool requirement: {e}")
        import traceback
        traceback.print_exc()
        flash('Error deleting tool requirement', 'error')
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
