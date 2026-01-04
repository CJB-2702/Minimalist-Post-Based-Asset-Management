"""
Asset Type management routes
CRUD operations for AssetType model
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from app.logger import get_logger
from flask_login import login_required, current_user
from app.data.core.asset_info.asset_type import AssetType
from app.data.core.asset_info.make_model import MakeModel
from app.data.core.asset_info.asset import Asset
from app.services.core.asset_type_service import AssetTypeService
from app import db

bp = Blueprint('asset_types', __name__)
logger = get_logger("asset_management.routes.bp")

@bp.route('/asset-types')
@login_required
def list():
    """List all asset types"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Use service to get list data
    asset_types, count_dicts, filter_options = AssetTypeService.get_list_data(
        request=request,
        page=page,
        per_page=per_page
    )
    
    return render_template('core/asset_types/list.html', 
                         asset_types=asset_types,
                         categories=filter_options['categories'],
                         asset_type_counts=count_dicts['asset_type_counts'],
                         make_model_counts=count_dicts['make_model_counts'])

@bp.route('/asset-types/<int:asset_type_id>')
@login_required
def detail(asset_type_id):
    """View asset type details"""
    # Use service to get detail data
    detail_data = AssetTypeService.get_detail_data(asset_type_id)
    
    return render_template('core/asset_types/detail.html', 
                         asset_type=detail_data['asset_type'],
                         make_models=detail_data['make_models'],
                         assets=detail_data['assets'],
                         Asset=Asset,
                         MakeModel=MakeModel)

@bp.route('/asset-types/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new asset type"""
    if request.method == 'POST':
        # Validate form data
        name = request.form.get('name')
        description = request.form.get('description')
        category = request.form.get('category')
        is_active = request.form.get('is_active') == 'on'
        
        # Check if name already exists
        if AssetType.query.filter_by(name=name).first():
            flash('Asset type name already exists', 'error')
            return render_template('core/asset_types/create.html')
        
        # Create new asset type
        asset_type = AssetType(
            name=name,
            description=description,
            category=category,
            is_active=is_active,
            created_by_id=current_user.id,
            updated_by_id=current_user.id
        )
        
        db.session.add(asset_type)
        db.session.commit()
        
        flash('Asset type created successfully', 'success')
        return redirect(url_for('asset_types.detail', asset_type_id=asset_type.id))
    
    return render_template('core/asset_types/create.html')

# ROUTE_TYPE: SIMPLE_CRUD (EDIT)
# EXCEPTION: Direct ORM usage allowed for simple EDIT operations on AssetType
# This route performs basic update operations with minimal business logic.
# Rationale: Simple asset type update doesn't require domain abstraction.
# NOTE: CREATE/DELETE operations should use domain managers - see create() and delete() routes
@bp.route('/asset-types/<int:asset_type_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(asset_type_id):
    """Edit asset type"""
    asset_type = AssetType.query.get_or_404(asset_type_id)
    
    if request.method == 'POST':
        # Validate form data
        name = request.form.get('name')
        description = request.form.get('description')
        category = request.form.get('category')
        is_active = request.form.get('is_active') == 'on'
        
        # Check if name already exists (excluding current asset type)
        existing_asset_type = AssetType.query.filter_by(name=name).first()
        if existing_asset_type and existing_asset_type.id != asset_type.id:
            flash('Asset type name already exists', 'error')
            # Get counts for template
            total_make_models = MakeModel.query.filter_by(asset_type_id=asset_type.id).count()
            active_make_models = MakeModel.query.filter_by(asset_type_id=asset_type.id, is_active=True).count()
            inactive_make_models = MakeModel.query.filter_by(asset_type_id=asset_type.id, is_active=False).count()
            return render_template('core/asset_types/edit.html', 
                                 asset_type=asset_type, 
                                 Asset=Asset, 
                                 MakeModel=MakeModel,
                                 total_make_models=total_make_models,
                                 active_make_models=active_make_models,
                                 inactive_make_models=inactive_make_models)
        
        # Update asset type
        asset_type.name = name
        asset_type.description = description
        asset_type.category = category
        asset_type.is_active = is_active
        asset_type.updated_by_id = current_user.id
        
        db.session.commit()
        
        flash('Asset type updated successfully', 'success')
        return redirect(url_for('asset_types.detail', asset_type_id=asset_type.id))
    
    # Get counts for template
    total_make_models = MakeModel.query.filter_by(asset_type_id=asset_type.id).count()
    active_make_models = MakeModel.query.filter_by(asset_type_id=asset_type.id, is_active=True).count()
    inactive_make_models = MakeModel.query.filter_by(asset_type_id=asset_type.id, is_active=False).count()
    
    return render_template('core/asset_types/edit.html', 
                         asset_type=asset_type, 
                         Asset=Asset, 
                         MakeModel=MakeModel,
                         total_make_models=total_make_models,
                         active_make_models=active_make_models,
                         inactive_make_models=inactive_make_models)

@bp.route('/asset-types/<int:asset_type_id>/delete', methods=['POST'])
@login_required
def delete(asset_type_id):
    """Delete asset type"""
    asset_type = AssetType.query.get_or_404(asset_type_id)
    
    # Check if asset type has make/models
    if MakeModel.query.filter_by(asset_type_id=asset_type.id).count() > 0:
        flash('Cannot delete asset type with make/models', 'error')
        return redirect(url_for('asset_types.detail', asset_type_id=asset_type.id))
    
    db.session.delete(asset_type)
    db.session.commit()
    
    flash('Asset type deleted successfully', 'success')
    return redirect(url_for('asset_types.list')) 