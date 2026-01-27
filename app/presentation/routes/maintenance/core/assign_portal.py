"""
Maintenance work and edit routes for maintenance events
"""
import traceback
from datetime import datetime

from flask import Blueprint, render_template, abort, request, flash, redirect, url_for, jsonify, send_from_directory
from flask_login import login_required, current_user

from app import db
from app.logger import get_logger
from app.buisness.core.event_context import EventContext
from app.buisness.maintenance.base.structs.action_struct import ActionStruct
from app.buisness.maintenance.base.structs.maintenance_action_set_struct import MaintenanceActionSetStruct
from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
from app.buisness.maintenance.factories.action_factory import ActionFactory
from app.data.core.asset_info.asset import Asset
from app.data.core.event_info.event import Event
from app.data.core.supply.part_definition import PartDefinition
from app.data.core.supply.tool_definition import ToolDefinition
from app.data.core.user_info.user import User
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.action_tools import ActionTool
from app.data.maintenance.base.maintenance_blockers import MaintenanceBlocker
from app.data.maintenance.planning.maintenance_plans import MaintenancePlan
from app.data.maintenance.base.part_demands import PartDemand
from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem
from app.services.maintenance.assign_monitor_service import AssignMonitorService

logger = get_logger("asset_management.routes.maintenance")

# Create blueprint for maintenance event assign portal
maintenance_event_bp = Blueprint('maintenance_event_assign', __name__, url_prefix='/maintenance/maintenance-event')


@maintenance_event_bp.route('/<int:event_id>/assign', methods=['GET', 'POST'])
@login_required
def assign_event(event_id):
    """
    Assign or reassign maintenance event to technician.
    GET: Show assignment form
    POST: Process assignment (refreshes page and opens view in new tab)
    """
    logger.info(f"Assigning maintenance event for event_id={event_id}")
    
    try:
        # Get the event
        event = Event.query.get(event_id)
        if not event:
            logger.warning(f"Event {event_id} not found")
            abort(404)
        
        # Get the maintenance action set by event_id (ONE-TO-ONE relationship)
        maintenance_context = MaintenanceContext.from_event(event_id)
        maintenance_struct = maintenance_context.struct
        
        if not maintenance_struct:
            logger.warning(f"No maintenance action set found for event_id={event_id}")
            abort(404)
        
        if request.method == 'GET':
            # Get technicians for dropdown
            technicians, _ = AssignMonitorService.get_available_technicians()
            
            # Get assignment history (from comments)
            assignment_history = []
            if maintenance_context.event_context:
                comments = maintenance_context.event_context.comments
                # Filter comments that mention assignment
                for comment in comments:
                    if 'Assigned to' in comment.content or 'assigned' in comment.content.lower():
                        assignment_history.append({
                            'created_at': comment.created_at.isoformat() if comment.created_at else None,
                            'created_by': comment.created_by.username if comment.created_by else None,
                            'content': comment.content,
                        })
            
            return render_template(
                'maintenance/base/maintenance_event/assign.html',
                maintenance=maintenance_struct,
                maintenance_context=maintenance_context,
                event=event,
                technicians=technicians,
                assignment_history=assignment_history,
            )
        
        # POST: Process assignment
        try:
            assigned_user_id = request.form.get('assigned_user_id', type=int)
            notes = request.form.get('notes', '').strip() or None
            
            # Get optional fields
            planned_start_str = request.form.get('planned_start_datetime')
            planned_start_datetime = None
            if planned_start_str:
                try:
                    planned_start_datetime = datetime.fromisoformat(planned_start_str.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    pass
            
            priority = request.form.get('priority')
            
            # Validate required fields
            if not assigned_user_id:
                flash('Technician is required', 'error')
                return redirect(url_for('maintenance_event_assign.assign_event', event_id=event_id))
            
            # Assign event
            AssignMonitorService.assign_event(
                event_id=event_id,
                assigned_user_id=assigned_user_id,
                assigned_by_id=current_user.id,
                planned_start_datetime=planned_start_datetime,
                priority=priority,
                notes=notes
            )
            
            flash('Event assigned successfully', 'success')
            
            # Redirect back to assign page with success parameter
            # JavaScript in template will open view page in new tab
            return redirect(url_for('maintenance_event_assign.assign_event', event_id=event_id, assigned='true'))
            
        except ValueError as e:
            logger.warning(f"Validation error assigning event: {e}")
            flash(str(e), 'error')
            return redirect(url_for('maintenance_event_assign.assign_event', event_id=event_id))
        except Exception as e:
            logger.error(f"Error assigning event: {e}")
            flash('Error assigning event. Please try again.', 'error')
            return redirect(url_for('maintenance_event_assign.assign_event', event_id=event_id))
            
    except ImportError as e:
        logger.error(f"Could not import maintenance modules: {e}")
        abort(500)
    except Exception as e:
        logger.error(f"Error in assign event {event_id}: {e}")
        abort(500)


