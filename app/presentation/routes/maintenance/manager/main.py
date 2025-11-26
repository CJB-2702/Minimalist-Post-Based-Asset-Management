"""
Manager Portal Main Routes
Dashboard and main navigation for maintenance managers
"""

from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.logger import get_logger
from app.buisness.maintenance import (
    MaintenanceContext,
    TemplateMaintenanceContext,
    ProtoActionContext,
)

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
    
    return render_template('maintenance/manager/dashboard.html', stats=stats)


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
        'maintenance/manager/view_maintenance.html',
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
    return render_template('maintenance/manager/plan_maintenance.html')


@manager_bp.route('/build-maintenance')
@login_required
def build_maintenance():
    """Build maintenance - Create and manage templates and prototypes"""
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
        'maintenance/manager/build_maintenance.html',
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
    return render_template('maintenance/manager/assign_monitor.html')


@manager_bp.route('/approve-review')
@login_required
def approve_review():
    """Approve and review - Approve part demands, review delays"""
    logger.info(f"Approve & review accessed by {current_user.username}")
    return render_template('maintenance/manager/approve_review.html')

