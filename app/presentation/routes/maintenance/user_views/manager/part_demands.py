"""
Part Demands Routes
Routes for viewing and managing part demands in the manager portal
"""

from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from app.logger import get_logger
from app import db
from app.services.maintenance.part_demand_service import PartDemandService
from app.services.maintenance.part_demand_search_service import PartDemandSearchService

logger = get_logger("asset_management.routes.maintenance.manager.part_demands")

# Use the existing manager_bp from main.py
from app.presentation.routes.maintenance.user_views.manager.main import manager_bp


@manager_bp.route('/part-demands')
@login_required
def part_demands():
    """Part demands portal - View and approve part demands"""
    logger.info(f"Part demands portal accessed by {current_user.username}")
    
    # Get filter parameters
    part_id = request.args.get('part_id', type=int)
    part_description = request.args.get('part_description', '').strip() or None
    maintenance_event_id = request.args.get('maintenance_event_id', type=int)
    asset_id = request.args.get('asset_id', type=int)
    assigned_to_id = request.args.get('assigned_to_id', type=int)
    major_location_id = request.args.get('major_location_id', type=int)
    status = request.args.get('status', '').strip() or None
    sort_by = request.args.get('sort_by', '').strip() or None
    
    # Get date range parameters
    created_from_str = request.args.get('created_from', '').strip()
    created_to_str = request.args.get('created_to', '').strip()
    updated_from_str = request.args.get('updated_from', '').strip()
    updated_to_str = request.args.get('updated_to', '').strip()
    maintenance_event_created_from_str = request.args.get('maintenance_event_created_from', '').strip()
    maintenance_event_created_to_str = request.args.get('maintenance_event_created_to', '').strip()
    maintenance_event_updated_from_str = request.args.get('maintenance_event_updated_from', '').strip()
    maintenance_event_updated_to_str = request.args.get('maintenance_event_updated_to', '').strip()
    
    created_from = None
    created_to = None
    updated_from = None
    updated_to = None
    maintenance_event_created_from = None
    maintenance_event_created_to = None
    maintenance_event_updated_from = None
    maintenance_event_updated_to = None
    
    if created_from_str:
        try:
            # Handle date-only format (YYYY-MM-DD) or datetime format
            if 'T' in created_from_str or '+' in created_from_str or 'Z' in created_from_str:
                created_from = datetime.fromisoformat(created_from_str.replace('Z', '+00:00'))
            else:
                # Date-only format, set to start of day
                created_from = datetime.strptime(created_from_str, '%Y-%m-%d')
        except (ValueError, AttributeError):
            pass
    
    if created_to_str:
        try:
            # Handle date-only format (YYYY-MM-DD) or datetime format
            if 'T' in created_to_str or '+' in created_to_str or 'Z' in created_to_str:
                created_to = datetime.fromisoformat(created_to_str.replace('Z', '+00:00'))
            else:
                # Date-only format, set to end of day
                created_to = datetime.strptime(created_to_str, '%Y-%m-%d')
        except (ValueError, AttributeError):
            pass
    
    if updated_from_str:
        try:
            # Handle date-only format (YYYY-MM-DD) or datetime format
            if 'T' in updated_from_str or '+' in updated_from_str or 'Z' in updated_from_str:
                updated_from = datetime.fromisoformat(updated_from_str.replace('Z', '+00:00'))
            else:
                # Date-only format, set to start of day
                updated_from = datetime.strptime(updated_from_str, '%Y-%m-%d')
        except (ValueError, AttributeError):
            pass
    
    if updated_to_str:
        try:
            # Handle date-only format (YYYY-MM-DD) or datetime format
            if 'T' in updated_to_str or '+' in updated_to_str or 'Z' in updated_to_str:
                updated_to = datetime.fromisoformat(updated_to_str.replace('Z', '+00:00'))
            else:
                # Date-only format, set to end of day
                updated_to = datetime.strptime(updated_to_str, '%Y-%m-%d')
        except (ValueError, AttributeError):
            pass
    
    # Parse maintenance event date range parameters
    if maintenance_event_created_from_str:
        try:
            if 'T' in maintenance_event_created_from_str or '+' in maintenance_event_created_from_str or 'Z' in maintenance_event_created_from_str:
                maintenance_event_created_from = datetime.fromisoformat(maintenance_event_created_from_str.replace('Z', '+00:00'))
            else:
                maintenance_event_created_from = datetime.strptime(maintenance_event_created_from_str, '%Y-%m-%d')
        except (ValueError, AttributeError):
            pass
    
    if maintenance_event_created_to_str:
        try:
            if 'T' in maintenance_event_created_to_str or '+' in maintenance_event_created_to_str or 'Z' in maintenance_event_created_to_str:
                maintenance_event_created_to = datetime.fromisoformat(maintenance_event_created_to_str.replace('Z', '+00:00'))
            else:
                maintenance_event_created_to = datetime.strptime(maintenance_event_created_to_str, '%Y-%m-%d')
        except (ValueError, AttributeError):
            pass
    
    if maintenance_event_updated_from_str:
        try:
            if 'T' in maintenance_event_updated_from_str or '+' in maintenance_event_updated_from_str or 'Z' in maintenance_event_updated_from_str:
                maintenance_event_updated_from = datetime.fromisoformat(maintenance_event_updated_from_str.replace('Z', '+00:00'))
            else:
                maintenance_event_updated_from = datetime.strptime(maintenance_event_updated_from_str, '%Y-%m-%d')
        except (ValueError, AttributeError):
            pass
    
    if maintenance_event_updated_to_str:
        try:
            if 'T' in maintenance_event_updated_to_str or '+' in maintenance_event_updated_to_str or 'Z' in maintenance_event_updated_to_str:
                maintenance_event_updated_to = datetime.fromisoformat(maintenance_event_updated_to_str.replace('Z', '+00:00'))
            else:
                maintenance_event_updated_to = datetime.strptime(maintenance_event_updated_to_str, '%Y-%m-%d')
        except (ValueError, AttributeError):
            pass
    
    # Get filtered part demands
    try:
        part_demands_list = PartDemandSearchService.get_filtered_part_demands(
            part_id=part_id,
            part_description=part_description,
            maintenance_event_id=maintenance_event_id,
            asset_id=asset_id,
            assigned_to_id=assigned_to_id,
            major_location_id=major_location_id,
            status=status,
            sort_by=sort_by,
            created_from=created_from,
            created_to=created_to,
            updated_from=updated_from,
            updated_to=updated_to,
            maintenance_event_created_from=maintenance_event_created_from,
            maintenance_event_created_to=maintenance_event_created_to,
            maintenance_event_updated_from=maintenance_event_updated_from,
            maintenance_event_updated_to=maintenance_event_updated_to
        )
    except Exception as e:
        logger.error(f"Error loading part demands: {e}")
        part_demands_list = []
        flash('Error loading part demands', 'error')
    
    # Get filter options
    try:
        from app.data.core.supply.part_definition import PartDefinition
        from app.data.core.asset_info.asset import Asset
        from app.data.core.major_location import MajorLocation
        from app.data.core.user_info.user import User
        from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
        from app.data.maintenance.base.part_demands import PartDemand
        
        # Get unique statuses
        statuses = db.session.query(PartDemand.status).distinct().all()
        status_options = [s[0] for s in statuses if s[0]]
        
        # Get users for assigned_to filter
        users = User.query.filter_by(is_active=True).order_by(User.username).all()
        
        # Get major locations
        locations = MajorLocation.query.filter_by(is_active=True).order_by(MajorLocation.name).all()
        
    except Exception as e:
        logger.warning(f"Could not load filter options: {e}")
        status_options = []
        users = []
        locations = []
    
    return render_template(
        'maintenance/user_views/manager/part_demands.html',
        part_demands=part_demands_list,
        status_options=status_options,
        users=users,
        locations=locations,
        filters={
            'part_id': part_id,
            'part_description': part_description or '',
            'maintenance_event_id': maintenance_event_id,
            'asset_id': asset_id,
            'assigned_to_id': assigned_to_id,
            'major_location_id': major_location_id,
            'status': status,
            'sort_by': sort_by,
            'created_from': created_from_str,
            'created_to': created_to_str,
            'updated_from': updated_from_str,
            'updated_to': updated_to_str,
            'maintenance_event_created_from': maintenance_event_created_from_str,
            'maintenance_event_created_to': maintenance_event_created_to_str,
            'maintenance_event_updated_from': maintenance_event_updated_from_str,
            'maintenance_event_updated_to': maintenance_event_updated_to_str
        }
    )


@manager_bp.route('/part-demands/approve', methods=['POST'])
@login_required
def approve_part_demand():
    """Approve a single part demand"""
    try:
        part_demand_id = request.form.get('part_demand_id', type=int)
        notes = request.form.get('notes', '').strip() or None
        
        if not part_demand_id:
            flash('Part demand ID is required', 'error')
            return redirect(url_for('manager_portal.part_demands'))
        
        result = PartDemandService.approve_part_demand(
            part_demand_id=part_demand_id,
            user_id=current_user.id,
            notes=notes
        )
        
        flash(result['message'], 'success')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        logger.error(f"Error approving part demand: {e}")
        flash('Error approving part demand', 'error')
    
    # Preserve filter parameters from form
    filter_params = {}
    for key in ['part_id', 'part_description', 'maintenance_event_id', 'asset_id', 
                'assigned_to_id', 'major_location_id', 'status', 'sort_by',
                'created_from', 'created_to', 'updated_from', 'updated_to',
                'maintenance_event_created_from', 'maintenance_event_created_to',
                'maintenance_event_updated_from', 'maintenance_event_updated_to']:
        value = request.form.get(key)
        if value:
            filter_params[key] = value
    
    return redirect(url_for('manager_portal.part_demands', **filter_params))


@manager_bp.route('/part-demands/reject', methods=['POST'])
@login_required
def reject_part_demand():
    """Reject a single part demand"""
    try:
        part_demand_id = request.form.get('part_demand_id', type=int)
        reason = request.form.get('reason', '').strip()
        
        if not part_demand_id:
            flash('Part demand ID is required', 'error')
            return redirect(url_for('manager_portal.part_demands'))
        
        if not reason:
            flash('Rejection reason is required', 'error')
            return redirect(url_for('manager_portal.part_demands'))
        
        result = PartDemandService.reject_part_demand(
            part_demand_id=part_demand_id,
            user_id=current_user.id,
            reason=reason
        )
        
        flash(result['message'], 'success')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        logger.error(f"Error rejecting part demand: {e}")
        flash('Error rejecting part demand', 'error')
    
    # Preserve filter parameters from form
    filter_params = {}
    for key in ['part_id', 'part_description', 'maintenance_event_id', 'asset_id', 
                'assigned_to_id', 'major_location_id', 'status', 'sort_by',
                'created_from', 'created_to', 'updated_from', 'updated_to',
                'maintenance_event_created_from', 'maintenance_event_created_to',
                'maintenance_event_updated_from', 'maintenance_event_updated_to']:
        value = request.form.get(key)
        if value:
            filter_params[key] = value
    
    return redirect(url_for('manager_portal.part_demands', **filter_params))


@manager_bp.route('/part-demands/bulk-approve', methods=['POST'])
@login_required
def bulk_approve_part_demands():
    """Bulk approve multiple part demands"""
    try:
        part_demand_ids = request.form.getlist('part_demand_ids', type=int)
        notes = request.form.get('notes', '').strip() or None
        
        if not part_demand_ids:
            flash('No part demands selected', 'error')
            # Preserve filter parameters
            filter_params = {}
            for key in ['part_id', 'part_description', 'maintenance_event_id', 'asset_id', 
                        'assigned_to_id', 'major_location_id', 'status', 'sort_by']:
                value = request.form.get(key)
                if value:
                    filter_params[key] = value
            return redirect(url_for('manager_portal.part_demands', **filter_params))
        
        result = PartDemandService.bulk_approve_part_demands(
            part_demand_ids=part_demand_ids,
            user_id=current_user.id,
            notes=notes
        )
        
        flash(result['message'], 'success')
        if result['errors']:
            for error in result['errors'][:5]:  # Show first 5 errors
                flash(error, 'warning')
    except Exception as e:
        logger.error(f"Error bulk approving part demands: {e}")
        flash('Error bulk approving part demands', 'error')
    
    # Preserve filter parameters from form
    filter_params = {}
    for key in ['part_id', 'part_description', 'maintenance_event_id', 'asset_id', 
                'assigned_to_id', 'major_location_id', 'status', 'sort_by',
                'created_from', 'created_to', 'updated_from', 'updated_to',
                'maintenance_event_created_from', 'maintenance_event_created_to',
                'maintenance_event_updated_from', 'maintenance_event_updated_to']:
        value = request.form.get(key)
        if value:
            filter_params[key] = value
    
    return redirect(url_for('manager_portal.part_demands', **filter_params))


@manager_bp.route('/part-demands/bulk-reject', methods=['POST'])
@login_required
def bulk_reject_part_demands():
    """Bulk reject multiple part demands"""
    try:
        part_demand_ids = request.form.getlist('part_demand_ids', type=int)
        reason = request.form.get('reason', '').strip()
        
        # Preserve filter parameters helper
        filter_params = {}
        for key in ['part_id', 'part_description', 'maintenance_event_id', 'asset_id', 
                    'assigned_to_id', 'major_location_id', 'status', 'sort_by']:
            value = request.form.get(key)
            if value:
                filter_params[key] = value
        
        if not part_demand_ids:
            flash('No part demands selected', 'error')
            return redirect(url_for('manager_portal.part_demands', **filter_params))
        
        if not reason:
            flash('Rejection reason is required', 'error')
            return redirect(url_for('manager_portal.part_demands', **filter_params))
        
        result = PartDemandService.bulk_reject_part_demands(
            part_demand_ids=part_demand_ids,
            user_id=current_user.id,
            reason=reason
        )
        
        flash(result['message'], 'success')
        if result['errors']:
            for error in result['errors'][:5]:  # Show first 5 errors
                flash(error, 'warning')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        logger.error(f"Error bulk rejecting part demands: {e}")
        flash('Error bulk rejecting part demands', 'error')
    
    # Preserve filter parameters from form
    filter_params = {}
    for key in ['part_id', 'part_description', 'maintenance_event_id', 'asset_id', 
                'assigned_to_id', 'major_location_id', 'status', 'sort_by',
                'created_from', 'created_to', 'updated_from', 'updated_to',
                'maintenance_event_created_from', 'maintenance_event_created_to',
                'maintenance_event_updated_from', 'maintenance_event_updated_to']:
        value = request.form.get(key)
        if value:
            filter_params[key] = value
    
    return redirect(url_for('manager_portal.part_demands', **filter_params))


@manager_bp.route('/part-demands/bulk-change-part', methods=['POST'])
@login_required
def bulk_change_part_id():
    """Bulk change part ID for multiple part demands"""
    try:
        part_demand_ids = request.form.getlist('part_demand_ids', type=int)
        new_part_id = request.form.get('new_part_id', type=int)
        
        # Preserve filter parameters helper
        filter_params = {}
        for key in ['part_id', 'part_description', 'maintenance_event_id', 'asset_id', 
                    'assigned_to_id', 'major_location_id', 'status', 'sort_by']:
            value = request.form.get(key)
            if value:
                filter_params[key] = value
        
        if not part_demand_ids:
            flash('No part demands selected', 'error')
            return redirect(url_for('manager_portal.part_demands', **filter_params))
        
        if not new_part_id:
            flash('New part ID is required', 'error')
            return redirect(url_for('manager_portal.part_demands', **filter_params))
        
        result = PartDemandService.bulk_change_part_id(
            part_demand_ids=part_demand_ids,
            new_part_id=new_part_id,
            user_id=current_user.id
        )
        
        flash(result['message'], 'success')
        if result['errors']:
            for error in result['errors'][:5]:  # Show first 5 errors
                flash(error, 'warning')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        logger.error(f"Error bulk changing part ID: {e}")
        flash('Error bulk changing part ID', 'error')
    
    # Preserve filter parameters from form
    filter_params = {}
    for key in ['part_id', 'part_description', 'maintenance_event_id', 'asset_id', 
                'assigned_to_id', 'major_location_id', 'status', 'sort_by',
                'created_from', 'created_to', 'updated_from', 'updated_to',
                'maintenance_event_created_from', 'maintenance_event_created_to',
                'maintenance_event_updated_from', 'maintenance_event_updated_to']:
        value = request.form.get(key)
        if value:
            filter_params[key] = value
    
    return redirect(url_for('manager_portal.part_demands', **filter_params))
