"""
Make/Model management routes
CRUD operations for MakeModel model
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from app.logger import get_logger
from flask_login import login_required, current_user
from app.data.core.asset_info.make_model import MakeModel
from app.data.core.asset_info.asset import Asset
from app.buisness.assets.factories.make_model_factory import MakeModelFactory
from app.services.core.make_model_service import MakeModelService
from app import db

bp = Blueprint('make_models', __name__)
logger = get_logger("asset_management.routes.bp")

@bp.route('/make-models')
@login_required
def list():
    """List all make/models"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Use service to get list data
    make_models, count_dicts, filter_options = MakeModelService.get_list_data(
        request=request,
        page=page,
        per_page=per_page
    )
    
    return render_template('core/make_models/list.html', 
                         make_models=make_models,
                         asset_types=filter_options['asset_types'],
                         asset_counts=count_dicts['asset_counts'])

@bp.route('/make-models/<int:make_model_id>')
@login_required
def detail(make_model_id):
    """View make/model details"""
    # Use service to get detail data
    detail_data = MakeModelService.get_detail_data(make_model_id)
    
    return render_template('core/make_models/detail.html', 
                         make_model=detail_data['make_model'],
                         assets=detail_data['assets'])

@bp.route('/make-models/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new make/model using MakeModelFactory"""
    if request.method == 'POST':
        try:
            # Gather form data
            make_model_data = {
                'make': request.form.get('make'),
                'model': request.form.get('model'),
                'year': request.form.get('year', type=int),
                'revision': request.form.get('revision'),
                'description': request.form.get('description'),
                'asset_type_id': request.form.get('asset_type_id', type=int),
                'is_active': request.form.get('is_active') == 'on'
            }
            
            # Use MakeModelFactory to create the make/model
            factory = MakeModelFactory()
            make_model = factory.create_make_model(
                created_by_id=current_user.id,
                commit=True,
                **make_model_data
            )
            
            flash('Make/Model created successfully', 'success')
            logger.info(f"User {current_user.username} created make/model: {make_model.make} {make_model.model} (ID: {make_model.id})")
            return redirect(url_for('make_models.detail', make_model_id=make_model.id))
            
        except ValueError as e:
            flash(str(e), 'error')
            logger.warning(f"Make/Model creation failed: {e}")
        except Exception as e:
            flash(f'Error creating make/model: {str(e)}', 'error')
            logger.error(f"Unexpected error creating make/model: {e}")
            db.session.rollback()
    
    # Get form options from service
    form_options = MakeModelService.get_form_options()
    return render_template('core/make_models/create.html', asset_types=form_options['asset_types'])

# ROUTE_TYPE: SIMPLE_CRUD (EDIT)
# EXCEPTION: Direct ORM usage allowed for simple EDIT operations on MakeModel
# This route performs basic update operations with minimal business logic.
# Rationale: Using MakeModelFactory for validation is acceptable, but direct ORM would also be fine for simple edits.
# NOTE: CREATE/DELETE operations should use domain managers - see create() and delete() routes
@bp.route('/make-models/<int:make_model_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(make_model_id):
    """Edit make/model using MakeModelFactory"""
    make_model = MakeModel.query.get_or_404(make_model_id)
    
    if request.method == 'POST':
        try:
            # Gather update data
            update_data = {
                'make': request.form.get('make'),
                'model': request.form.get('model'),
                'year': request.form.get('year', type=int),
                'revision': request.form.get('revision'),
                'description': request.form.get('description'),
                'asset_type_id': request.form.get('asset_type_id', type=int),
                'is_active': request.form.get('is_active') == 'on'
            }
            
            # Use MakeModelFactory to update the make/model
            MakeModelFactory.update_make_model(
                make_model=make_model,
                updated_by_id=current_user.id,
                commit=True,
                **update_data
            )
            
            flash('Make/Model updated successfully', 'success')
            logger.info(f"User {current_user.username} updated make/model: {make_model.make} {make_model.model} (ID: {make_model.id})")
            return redirect(url_for('make_models.detail', make_model_id=make_model.id))
            
        except ValueError as e:
            flash(str(e), 'error')
            logger.warning(f"Make/Model update failed: {e}")
        except Exception as e:
            flash(f'Error updating make/model: {str(e)}', 'error')
            logger.error(f"Unexpected error updating make/model: {e}")
            db.session.rollback()
    
    # Get form options from service
    form_options = MakeModelService.get_form_options()
    return render_template('core/make_models/edit.html', 
                         make_model=make_model,
                         asset_types=form_options['asset_types'],
                         Asset=Asset)

@bp.route('/make-models/<int:make_model_id>/delete', methods=['POST'])
@login_required
def delete(make_model_id):
    """Delete make/model"""
    make_model = MakeModel.query.get_or_404(make_model_id)
    
    # Check if make/model has assets
    if Asset.query.filter_by(make_model_id=make_model.id).count() > 0:
        flash('Cannot delete make/model with assets', 'error')
        return redirect(url_for('make_models.detail', make_model_id=make_model.id))
    
    db.session.delete(make_model)
    db.session.commit()
    
    flash('Make/Model deleted successfully', 'success')
    return redirect(url_for('make_models.list')) 