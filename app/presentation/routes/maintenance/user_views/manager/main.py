"""
Manager Portal Main Routes
Dashboard and main navigation for maintenance managers
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.logger import get_logger
from app import db
from app.buisness.maintenance import (
    MaintenanceContext,
    TemplateMaintenanceContext,
    ProtoActionContext,
)
from app.services.maintenance.part_demand_service import PartDemandService

logger = get_logger("asset_management.routes.maintenance.manager")

# Create manager portal blueprint
manager_bp = Blueprint('manager_portal', __name__, url_prefix='/maintenance/manager')


@manager_bp.route('/')
@manager_bp.route('/dashboard')
@login_required
def dashboard():
    """Manager dashboard with workflow cards"""
    logger.info(f"Manager dashboard accessed by {current_user.username}")
    
    # Get basic stats
    stats = {
        'total_maintenance_events': 0,
        'active_maintenance': 0,
        'pending_part_demands': 0,
        'total_templates': 0,
        'total_prototypes': 0,
    }
    
    try:
        from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
        from app.data.maintenance.templates.template_action_sets import TemplateActionSet
        from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem
        from app.data.maintenance.base.part_demands import PartDemand
        
        stats['total_maintenance_events'] = MaintenanceActionSet.query.count()
        stats['active_maintenance'] = MaintenanceActionSet.query.filter(
            MaintenanceActionSet.status.in_(['Planned', 'In Progress', 'Delayed'])
        ).count()
        stats['pending_part_demands'] = PartDemand.query.filter(
            PartDemand.status.in_(['Planned', 'Requested'])
        ).count()
        stats['total_templates'] = TemplateActionSet.query.filter_by(is_active=True).count()
        stats['total_prototypes'] = ProtoActionItem.query.count()
    except ImportError as e:
        logger.warning(f"Could not load maintenance stats: {e}")
    
    return render_template('maintenance/user_views/manager/dashboard.html', stats=stats)


@manager_bp.route('/view-maintenance')
@login_required
def view_maintenance():
    """View maintenance events, templates, and prototypes"""
    logger.info(f"View maintenance accessed by {current_user.username}")
    
    # Get view type from query params (events, templates, prototypes)
    view_type = request.args.get('type', 'events')
    
    maintenance_events = None
    templates = []
    prototypes = []
    
    try:
        from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
        from app.data.maintenance.templates.template_action_sets import TemplateActionSet
        from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem
        
        if view_type in ['events', 'all']:
            # Get maintenance events with pagination
            page = request.args.get('page', 1, type=int)
            per_page = 20
            
            query = MaintenanceActionSet.query.order_by(MaintenanceActionSet.created_at.desc())
            
            # Apply filters
            status_filter = request.args.get('status')
            if status_filter:
                query = query.filter_by(status=status_filter)
            
            asset_id = request.args.get('asset_id', type=int)
            if asset_id:
                query = query.filter_by(asset_id=asset_id)
            
            try:
                maintenance_events = query.paginate(
                    page=page,
                    per_page=per_page,
                    error_out=False
                )
            except Exception as e:
                logger.warning(f"Error paginating maintenance events: {e}")
                # Create an empty pagination-like object or set to None
                maintenance_events = None
        
        if view_type in ['templates', 'all']:
            # Get templates
            templates_query = TemplateActionSet.query.order_by(TemplateActionSet.task_name)
            
            # Filter by active status
            active_only = request.args.get('active_only', 'true') == 'true'
            if active_only:
                templates_query = templates_query.filter_by(is_active=True)
            
            templates = templates_query.limit(100).all()
        
        if view_type in ['prototypes', 'all']:
            # Get prototypes
            prototypes_query = ProtoActionItem.query.order_by(ProtoActionItem.action_name)
            
            # Search filter
            search = request.args.get('search')
            if search:
                prototypes_query = prototypes_query.filter(
                    ProtoActionItem.action_name.ilike(f'%{search}%')
                )
            
            prototypes = prototypes_query.limit(100).all()
            
    except ImportError as e:
        logger.warning(f"Could not load maintenance data: {e}")
    
    return render_template(
        'maintenance/user_views/manager/view_maintenance.html',
        view_type=view_type,
        maintenance_events=maintenance_events,
        templates=templates,
        prototypes=prototypes,
    )


@manager_bp.route('/plan-maintenance')
@login_required
def plan_maintenance():
    """Plan maintenance - Create plans, schedule events, manage assets due"""
    logger.info(f"Plan maintenance accessed by {current_user.username}")
    return render_template('maintenance/user_views/manager/plan_maintenance.html')


@manager_bp.route('/build-maintenance-templates')
@login_required
def build_maintenance():
    """Build maintenance templates - Create and manage templates and prototypes"""
    logger.info(f"Build maintenance accessed by {current_user.username}")
    
    # Get search parameters
    search_id = request.args.get('search_id', type=int)
    search_name = request.args.get('search_name', '').strip() or None
    asset_type_id = request.args.get('asset_type_id', type=int)
    make_model_id = request.args.get('make_model_id', type=int)
    
    # Get available templates for copying
    try:
        from app.services.maintenance.template_builder_service import TemplateBuilderService
        from app.data.core.asset_info.asset_type import AssetType
        from app.data.core.asset_info.make_model import MakeModel
        
        available_templates = TemplateBuilderService.get_available_templates(
            search_id=search_id,
            search_name=search_name,
            asset_type_id=asset_type_id,
            make_model_id=make_model_id
        )
        
        # Get asset types and make/models for dropdowns
        asset_types = AssetType.query.filter_by(is_active=True).order_by(AssetType.name).all()
        make_models = MakeModel.query.filter_by(is_active=True).order_by(MakeModel.make, MakeModel.model).all()
    except Exception as e:
        logger.warning(f"Could not load available templates: {e}")
        available_templates = []
        asset_types = []
        make_models = []
    
    return render_template(
        'maintenance/user_views/manager/build_maintenance.html',
        available_templates=available_templates,
        asset_types=asset_types,
        make_models=make_models,
        search_id=search_id,
        search_name=search_name or '',
        selected_asset_type_id=asset_type_id,
        selected_make_model_id=make_model_id
    )


@manager_bp.route('/assign-monitor')
@login_required
def assign_monitor():
    """Assign and monitor - Assign work to technicians, monitor progress"""
    logger.info(f"Assign & monitor accessed by {current_user.username}")
    return render_template('maintenance/user_views/manager/assign_monitor.html')


@manager_bp.route('/approve-review')
@login_required
def approve_review():
    """Approve and review - Approve part demands, review blockers"""
    logger.info(f"Approve & review accessed by {current_user.username}")
    return render_template('maintenance/user_views/manager/approve_review.html')


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
    
    # Get filtered part demands
    try:
        part_demands_list = PartDemandService.get_filtered_part_demands(
            part_id=part_id,
            part_description=part_description,
            maintenance_event_id=maintenance_event_id,
            asset_id=asset_id,
            assigned_to_id=assigned_to_id,
            major_location_id=major_location_id,
            status=status,
            sort_by=sort_by
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
            'sort_by': sort_by
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
                'assigned_to_id', 'major_location_id', 'status', 'sort_by']:
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
                'assigned_to_id', 'major_location_id', 'status', 'sort_by']:
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
                'assigned_to_id', 'major_location_id', 'status', 'sort_by']:
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
                'assigned_to_id', 'major_location_id', 'status', 'sort_by']:
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
                'assigned_to_id', 'major_location_id', 'status', 'sort_by']:
        value = request.form.get(key)
        if value:
            filter_params[key] = value
    
    return redirect(url_for('manager_portal.part_demands', **filter_params))

