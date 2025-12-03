"""
Maintenance Plan CRUD routes
Routes for managing maintenance plans
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.logger import get_logger
from app import db
from app.data.maintenance.planning.maintenance_plans import MaintenancePlan
from app.data.core.asset_info.asset_type import AssetType
from app.data.core.asset_info.make_model import MakeModel
from app.data.maintenance.templates.template_action_sets import TemplateActionSet
from app.buisness.maintenance.planning.maintenance_planner import MaintenancePlanner
from app.buisness.maintenance.planning.maintenance_plan_context import MaintenancePlanContext
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet

logger = get_logger("asset_management.routes.maintenance.planning")

# Create blueprint for maintenance plan routes
bp = Blueprint('maintenance_plan', __name__)


@bp.route('/manager/maintenance-plans')
@login_required
def list_plans():
    """List all maintenance plans"""
    plans = MaintenancePlan.query.order_by(MaintenancePlan.name).all()
    
    return render_template('maintenance/planning/maintenance_plans/list.html', 
                         plans=plans)


@bp.route('/maintenance-plan/<int:plan_id>/view')
@login_required
def view_plan(plan_id):
    """View maintenance plan details"""
    plan = MaintenancePlan.query.get_or_404(plan_id)
    
    # Get template action set if exists
    template_action_set = None
    template_action_items = []
    if plan.template_action_set_id:
        template_action_set = TemplateActionSet.query.get(plan.template_action_set_id)
        if template_action_set:
            template_action_items = template_action_set.template_action_items
    
    return render_template('maintenance/planning/maintenance_plans/view.html',
                         plan=plan,
                         template_action_set=template_action_set,
                         template_action_items=template_action_items)


@bp.route('/maintenance-plan/<int:plan_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_plan(plan_id):
    """Edit maintenance plan"""
    plan = MaintenancePlan.query.get_or_404(plan_id)
    
    if request.method == 'POST':
        try:
            # Gather update data
            plan.name = request.form.get('name')
            plan.description = request.form.get('description')
            plan.asset_type_id = request.form.get('asset_type_id', type=int)
            plan.model_id = request.form.get('model_id', type=int) or None
            plan.status = request.form.get('status')
            plan.template_action_set_id = request.form.get('template_action_set_id', type=int)
            plan.frequency_type = request.form.get('frequency_type')
            plan.delta_days = request.form.get('delta_days', type=float) or None
            plan.delta_m1 = request.form.get('delta_m1', type=float) or None
            plan.delta_m2 = request.form.get('delta_m2', type=float) or None
            plan.delta_m3 = request.form.get('delta_m3', type=float) or None
            plan.delta_m4 = request.form.get('delta_m4', type=float) or None
            
            plan.updated_by_id = current_user.id
            
            db.session.commit()
            
            flash('Maintenance plan updated successfully', 'success')
            logger.info(f"User {current_user.username} updated maintenance plan: {plan.name} (ID: {plan.id})")
            return redirect(url_for('maintenance_plan.view_plan', plan_id=plan.id))
            
        except Exception as e:
            flash(f'Error updating maintenance plan: {str(e)}', 'error')
            logger.error(f"Error updating maintenance plan: {e}")
            db.session.rollback()
    
    # Get form options
    asset_types = AssetType.query.order_by(AssetType.name).all()
    make_models = MakeModel.query.order_by(MakeModel.make, MakeModel.model).all()
    template_action_sets = TemplateActionSet.query.filter_by(is_active=True).order_by(TemplateActionSet.task_name).all()
    
    # Filter make models by selected asset type if set
    make_model_options = []
    if plan.asset_type_id:
        make_model_options = [m for m in make_models if m.asset_type_id == plan.asset_type_id]
    else:
        make_model_options = make_models
    
    return render_template('maintenance/planning/maintenance_plans/edit.html',
                         plan=plan,
                         asset_types=asset_types,
                         make_models=make_model_options,
                         template_action_sets=template_action_sets)


@bp.route('/maintenance-plan/create', methods=['GET', 'POST'])
@login_required
def create_plan():
    """Create new maintenance plan"""
    if request.method == 'POST':
        try:
            # Gather form data
            plan = MaintenancePlan(
                name=request.form.get('name'),
                description=request.form.get('description'),
                asset_type_id=request.form.get('asset_type_id', type=int),
                model_id=request.form.get('model_id', type=int) or None,
                status=request.form.get('status', 'Active'),
                template_action_set_id=request.form.get('template_action_set_id', type=int),
                frequency_type=request.form.get('frequency_type'),
                delta_days=request.form.get('delta_days', type=float) or None,
                delta_m1=request.form.get('delta_m1', type=float) or None,
                delta_m2=request.form.get('delta_m2', type=float) or None,
                delta_m3=request.form.get('delta_m3', type=float) or None,
                delta_m4=request.form.get('delta_m4', type=float) or None,
                created_by_id=current_user.id,
                updated_by_id=current_user.id
            )
            
            db.session.add(plan)
            db.session.commit()
            
            flash('Maintenance plan created successfully', 'success')
            logger.info(f"User {current_user.username} created maintenance plan: {plan.name} (ID: {plan.id})")
            return redirect(url_for('maintenance_plan.view_plan', plan_id=plan.id))
            
        except Exception as e:
            flash(f'Error creating maintenance plan: {str(e)}', 'error')
            logger.error(f"Error creating maintenance plan: {e}")
            db.session.rollback()
    
    # Get form options
    asset_types = AssetType.query.order_by(AssetType.name).all()
    make_models = MakeModel.query.order_by(MakeModel.make, MakeModel.model).all()
    template_action_sets = TemplateActionSet.query.filter_by(is_active=True).order_by(TemplateActionSet.task_name).all()
    
    return render_template('maintenance/planning/maintenance_plans/create.html',
                         asset_types=asset_types,
                         make_models=make_models,
                         template_action_sets=template_action_sets)


@bp.route('/search-template-action-sets')
@login_required
def search_template_action_sets():
    """HTMX endpoint to return template action set search results"""
    try:
        search = request.args.get('search', '').strip().lower()
        limit = request.args.get('limit', type=int, default=20)
        
        # Get all active template action sets
        template_sets = TemplateActionSet.query.filter_by(is_active=True).order_by(TemplateActionSet.task_name).all()
        
        # Filter by search term
        filtered_sets = []
        if search:
            for tas in template_sets:
                if (search in (tas.task_name or '').lower() or 
                    (tas.description and search in tas.description.lower())):
                    filtered_sets.append(tas)
        else:
            filtered_sets = template_sets
        
        # Limit results
        total_count = len(filtered_sets)
        showing_sets = filtered_sets[:limit]
        
        return render_template(
            'maintenance/planning/maintenance_plans/search_template_action_sets.html',
            template_action_sets=showing_sets,
            total_count=total_count,
            showing=len(showing_sets),
            search=search
        )
    except Exception as e:
        logger.error(f"Error in template action sets search: {e}")
        return render_template(
            'maintenance/planning/maintenance_plans/search_template_action_sets.html',
            template_action_sets=[],
            total_count=0,
            showing=0,
            search=search or '',
            error=str(e)
        ), 500


@bp.route('/preview-template-action-set/<int:template_action_set_id>')
@login_required
def preview_template_action_set(template_action_set_id):
    """HTMX endpoint to return template action set preview with actions"""
    try:
        # Get template action set
        template_set = TemplateActionSet.query.get_or_404(template_action_set_id)
        
        # Get template action items ordered by sequence_order
        template_items = sorted(
            template_set.template_action_items,
            key=lambda tai: tai.sequence_order
        )
        
        return render_template(
            'maintenance/planning/maintenance_plans/preview_template_action_set.html',
            template_action_set=template_set,
            template_action_items=template_items
        )
    except Exception as e:
        logger.error(f"Error previewing template action set: {e}")
        return f'<div class="alert alert-danger">Error loading template preview: {str(e)}</div>', 500


@bp.route('/maintenance-plan/<int:plan_id>/plan')
@login_required
def plan_maintenance(plan_id):
    """Display assets that need maintenance for a specific plan"""
    plan = MaintenancePlan.query.get_or_404(plan_id)
    
    # Create planner and get results
    planner = MaintenancePlanner.from_plan_id(plan_id)
    results = planner.get_assets_needing_maintenance()
    
    # Check for existing events for each result
    asset_event_map = {}
    for result in results:
        existing_event = (
            MaintenanceActionSet.query
            .filter_by(
                asset_id=result.asset_id,
                maintenance_plan_id=plan_id
            )
            .filter(MaintenanceActionSet.status.in_(['Planned', 'In Progress']))
            .first()
        )
        if existing_event:
            asset_event_map[result.asset_id] = existing_event
    
    return render_template(
        'maintenance/planning/maintenance_plans/plan.html',
        plan=plan,
        results=results,
        asset_event_map=asset_event_map
    )


@bp.route('/maintenance-plan/<int:plan_id>/create-event', methods=['POST'])
@login_required
def create_maintenance_event(plan_id):
    """Create a maintenance event for a specific asset and plan"""
    plan = MaintenancePlan.query.get_or_404(plan_id)
    asset_id = request.form.get('asset_id', type=int)
    
    if not asset_id:
        flash('Asset ID is required', 'error')
        return redirect(url_for('maintenance_plan.plan_maintenance', plan_id=plan_id))
    
    try:
        # Check for existing event
        existing_event = (
            MaintenanceActionSet.query
            .filter_by(
                asset_id=asset_id,
                maintenance_plan_id=plan_id
            )
            .filter(MaintenanceActionSet.status.in_(['Planned', 'In Progress']))
            .first()
        )
        
        if existing_event:
            flash(f'Maintenance event already exists (ID: {existing_event.id})', 'warning')
            return redirect(url_for('maintenance_plan.plan_maintenance', plan_id=plan_id))
        
        # Create plan context and create event
        plan_context = MaintenancePlanContext(plan_id)
        maintenance_event = plan_context.create_maintenance_event(
            asset_id=asset_id,
            planned_start_datetime=None,  # Will default to now
            user_id=current_user.id
        )
        
        if maintenance_event:
            flash(f'Maintenance event created successfully (ID: {maintenance_event.id})', 'success')
            logger.info(f"User {current_user.username} created maintenance event {maintenance_event.id} for asset {asset_id}, plan {plan_id}")
        else:
            flash('Failed to create maintenance event', 'error')
            logger.error(f"Failed to create maintenance event for asset {asset_id}, plan {plan_id}")
        
    except Exception as e:
        flash(f'Error creating maintenance event: {str(e)}', 'error')
        logger.error(f"Error creating maintenance event: {e}")
        db.session.rollback()
    
    return redirect(url_for('maintenance_plan.plan_maintenance', plan_id=plan_id))

