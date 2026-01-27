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

# Create blueprint for maintenance event management routes
maintenance_event_bp = Blueprint('maintenance_event_mgmt', __name__, url_prefix='/maintenance/maintenance-event')


@maintenance_event_bp.route('/<int:event_id>/update-datetime', methods=['POST'])
@login_required
def update_maintenance_datetime(event_id):
    """Update maintenance start/end dates"""
    try:
        # ===== FORM PARSING SECTION =====
        start_date_str = request.form.get('start_date', '').strip()
        end_date_str = request.form.get('end_date', '').strip()
        
        # ===== DATA TYPE CONVERSION SECTION =====
        start_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid start date format', 'error')
                return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        end_date = None
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid end date format', 'error')
                return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        # ===== LIGHT VALIDATION SECTION =====
        # Validate: end_date must be after start_date
        if end_date and start_date and end_date < start_date:
            flash('End date must be after start date', 'error')
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        # ===== BUSINESS LOGIC SECTION =====
        maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
        if not maintenance_struct:
            abort(404)
        
        if start_date:
            maintenance_struct.maintenance_action_set.start_date = start_date
        if end_date:
            maintenance_struct.maintenance_action_set.end_date = end_date
        
        db.session.commit()
        flash('Maintenance dates updated', 'success')
        return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error updating maintenance datetime: {e}")
        flash('Error updating maintenance dates', 'error')
        return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))


@maintenance_event_bp.route('/<int:event_id>/update-billable-hours', methods=['POST'])
@login_required


def update_maintenance_billable_hours(event_id):
    """Update maintenance total billable hours"""
    try:
        # ===== FORM PARSING SECTION =====
        billable_hours_str = request.form.get('actual_billable_hours', '').strip()
        
        # ===== LIGHT VALIDATION SECTION =====
        if not billable_hours_str:
            flash('Billable hours is required', 'error')
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        # ===== DATA TYPE CONVERSION SECTION =====
        try:
            billable_hours = float(billable_hours_str)
        except ValueError:
            flash('Invalid billable hours value', 'error')
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        # ===== BUSINESS LOGIC SECTION =====
        maintenance_struct = MaintenanceActionSetStruct.from_event_id(event_id)
        if not maintenance_struct:
            abort(404)
        
        maintenance_context = MaintenanceContext.from_event(event_id)
        try:
            billable_hours_manager = maintenance_context.get_billable_hours_manager()
            billable_hours_manager.set_actual_hours(billable_hours, user_id=current_user.id)
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
        flash('Maintenance billable hours updated', 'success')
        return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))
        
    except Exception as e:
        logger.error(f"Error updating maintenance billable hours: {e}")
        flash('Error updating billable hours', 'error')
        return redirect(url_for('maintenance_event_work.work_maintenance_event', event_id=event_id))


