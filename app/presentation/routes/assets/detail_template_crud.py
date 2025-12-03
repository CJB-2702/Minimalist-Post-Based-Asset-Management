"""
Detail Template CRUD Routes
Simple direct CRUD operations for detail table template models
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.logger import get_logger
from app.data.assets.detail_table_templates.asset_details_from_asset_type import AssetDetailTemplateByAssetType
from app.data.assets.detail_table_templates.asset_details_from_model_type import AssetDetailTemplateByModelType
from app.data.assets.detail_table_templates.model_detail_table_template import ModelDetailTableTemplate
from app.data.core.asset_info.asset_type import AssetType
from app.data.core.asset_info.make_model import MakeModel
from app.buisness.assets.factories.detail_factory import DetailFactory
from app.services.assets.asset_detail_service import AssetDetailService
from app import db

bp = Blueprint('detail_template_crud', __name__)
logger = get_logger("asset_management.routes.assets.detail_template_crud")


# ============================================================================
# AssetDetailTemplateByAssetType CRUD
# ============================================================================

@bp.route('/asset-detail-template-by-asset-type/')
@login_required
def list_asset_detail_template_by_asset_type():
    """List all AssetDetailTemplateByAssetType records"""
    records = AssetDetailTemplateByAssetType.query.order_by(
        AssetDetailTemplateByAssetType.asset_type_id,
        AssetDetailTemplateByAssetType.detail_table_type
    ).all()
    
    # Get asset types and detail types for display
    asset_types = {at.id: at for at in AssetType.query.all()}
    available_detail_types = {
        dt['type']: dt['name'] 
        for dt in AssetDetailService.get_available_asset_detail_types()
    }
    
    return render_template('assets/detail_template_crud/asset_detail_template_by_asset_type/list.html',
                         records=records,
                         asset_types=asset_types,
                         available_detail_types=available_detail_types)


@bp.route('/asset-detail-template-by-asset-type/create', methods=['GET', 'POST'])
@login_required
def create_asset_detail_template_by_asset_type():
    """Create new AssetDetailTemplateByAssetType record"""
    if request.method == 'POST':
        try:
            asset_type_id = request.form.get('asset_type_id', type=int)
            detail_table_type = request.form.get('detail_table_type')
            many_to_one = request.form.get('many_to_one') == 'on'
            
            if not asset_type_id:
                flash('Asset Type is required', 'error')
                return render_template('assets/detail_template_crud/asset_detail_template_by_asset_type/create.html',
                                     asset_types=AssetType.query.all(),
                                     available_detail_types=AssetDetailService.get_available_asset_detail_types())
            
            if not detail_table_type:
                flash('Detail Table Type is required', 'error')
                return render_template('assets/detail_template_crud/asset_detail_template_by_asset_type/create.html',
                                     asset_types=AssetType.query.all(),
                                     available_detail_types=AssetDetailService.get_available_asset_detail_types())
            
            # Check for duplicate
            existing = AssetDetailTemplateByAssetType.query.filter_by(
                asset_type_id=asset_type_id,
                detail_table_type=detail_table_type
            ).first()
            
            if existing:
                flash(f'Template already exists for this asset type and detail table type', 'error')
                return render_template('assets/detail_template_crud/asset_detail_template_by_asset_type/create.html',
                                     asset_types=AssetType.query.all(),
                                     available_detail_types=AssetDetailService.get_available_asset_detail_types())
            
            record = AssetDetailTemplateByAssetType(
                asset_type_id=asset_type_id,
                detail_table_type=detail_table_type,
                many_to_one=many_to_one,
                created_by_id=current_user.id,
                updated_by_id=current_user.id
            )
            db.session.add(record)
            db.session.commit()
            
            flash('Template created successfully', 'success')
            return redirect(url_for('assets.detail_template_crud.list_asset_detail_template_by_asset_type'))
        except Exception as e:
            flash(f'Error creating template: {str(e)}', 'error')
            logger.error(f"Error creating AssetDetailTemplateByAssetType: {e}")
            db.session.rollback()
    
    return render_template('assets/detail_template_crud/asset_detail_template_by_asset_type/create.html',
                         asset_types=AssetType.query.all(),
                         available_detail_types=AssetDetailService.get_available_asset_detail_types())


@bp.route('/asset-detail-template-by-asset-type/<int:id>')
@login_required
def detail_asset_detail_template_by_asset_type(id):
    """View AssetDetailTemplateByAssetType record details"""
    record = AssetDetailTemplateByAssetType.query.get_or_404(id)
    asset_type = AssetType.query.get(record.asset_type_id) if record.asset_type_id else None
    available_detail_types = {
        dt['type']: dt['name'] 
        for dt in AssetDetailService.get_available_asset_detail_types()
    }
    
    return render_template('assets/detail_template_crud/asset_detail_template_by_asset_type/detail.html',
                         record=record,
                         asset_type=asset_type,
                         available_detail_types=available_detail_types)


@bp.route('/asset-detail-template-by-asset-type/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_asset_detail_template_by_asset_type(id):
    """Edit AssetDetailTemplateByAssetType record"""
    record = AssetDetailTemplateByAssetType.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            asset_type_id = request.form.get('asset_type_id', type=int)
            detail_table_type = request.form.get('detail_table_type')
            many_to_one = request.form.get('many_to_one') == 'on'
            
            if not asset_type_id:
                flash('Asset Type is required', 'error')
                return render_template('assets/detail_template_crud/asset_detail_template_by_asset_type/edit.html',
                                     record=record,
                                     asset_types=AssetType.query.all(),
                                     available_detail_types=AssetDetailService.get_available_asset_detail_types())
            
            if not detail_table_type:
                flash('Detail Table Type is required', 'error')
                return render_template('assets/detail_template_crud/asset_detail_template_by_asset_type/edit.html',
                                     record=record,
                                     asset_types=AssetType.query.all(),
                                     available_detail_types=AssetDetailService.get_available_asset_detail_types())
            
            # Check for duplicate (excluding current record)
            existing = AssetDetailTemplateByAssetType.query.filter(
                AssetDetailTemplateByAssetType.asset_type_id == asset_type_id,
                AssetDetailTemplateByAssetType.detail_table_type == detail_table_type,
                AssetDetailTemplateByAssetType.id != id
            ).first()
            
            if existing:
                flash(f'Template already exists for this asset type and detail table type', 'error')
                return render_template('assets/detail_template_crud/asset_detail_template_by_asset_type/edit.html',
                                     record=record,
                                     asset_types=AssetType.query.all(),
                                     available_detail_types=AssetDetailService.get_available_asset_detail_types())
            
            record.asset_type_id = asset_type_id
            record.detail_table_type = detail_table_type
            record.many_to_one = many_to_one
            record.updated_by_id = current_user.id
            
            db.session.commit()
            flash('Template updated successfully', 'success')
            return redirect(url_for('assets.detail_template_crud.detail_asset_detail_template_by_asset_type', id=id))
        except Exception as e:
            flash(f'Error updating template: {str(e)}', 'error')
            logger.error(f"Error updating AssetDetailTemplateByAssetType: {e}")
            db.session.rollback()
    
    return render_template('assets/detail_template_crud/asset_detail_template_by_asset_type/edit.html',
                         record=record,
                         asset_types=AssetType.query.all(),
                         available_detail_types=AssetDetailService.get_available_asset_detail_types())


@bp.route('/asset-detail-template-by-asset-type/<int:id>/delete', methods=['POST'])
@login_required
def delete_asset_detail_template_by_asset_type(id):
    """Delete AssetDetailTemplateByAssetType record"""
    record = AssetDetailTemplateByAssetType.query.get_or_404(id)
    
    try:
        db.session.delete(record)
        db.session.commit()
        flash('Template deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting template: {str(e)}', 'error')
        logger.error(f"Error deleting AssetDetailTemplateByAssetType: {e}")
        db.session.rollback()
    
    return redirect(url_for('assets.detail_template_crud.list_asset_detail_template_by_asset_type'))


# ============================================================================
# AssetDetailTemplateByModelType CRUD
# ============================================================================

@bp.route('/asset-detail-template-by-model-type/')
@login_required
def list_asset_detail_template_by_model_type():
    """List all AssetDetailTemplateByModelType records"""
    records = AssetDetailTemplateByModelType.query.order_by(
        AssetDetailTemplateByModelType.make_model_id,
        AssetDetailTemplateByModelType.detail_table_type
    ).all()
    
    # Get make models and detail types for display
    make_models = {mm.id: mm for mm in MakeModel.query.all()}
    available_detail_types = {
        dt['type']: dt['name'] 
        for dt in AssetDetailService.get_available_asset_detail_types()
    }
    
    return render_template('assets/detail_template_crud/asset_detail_template_by_model_type/list.html',
                         records=records,
                         make_models=make_models,
                         available_detail_types=available_detail_types)


@bp.route('/asset-detail-template-by-model-type/create', methods=['GET', 'POST'])
@login_required
def create_asset_detail_template_by_model_type():
    """Create new AssetDetailTemplateByModelType record"""
    if request.method == 'POST':
        try:
            make_model_id = request.form.get('make_model_id', type=int)
            detail_table_type = request.form.get('detail_table_type')
            many_to_one = request.form.get('many_to_one') == 'on'
            
            if not make_model_id:
                flash('Make/Model is required', 'error')
                return render_template('assets/detail_template_crud/asset_detail_template_by_model_type/create.html',
                                     make_models=MakeModel.query.all(),
                                     available_detail_types=AssetDetailService.get_available_asset_detail_types())
            
            if not detail_table_type:
                flash('Detail Table Type is required', 'error')
                return render_template('assets/detail_template_crud/asset_detail_template_by_model_type/create.html',
                                     make_models=MakeModel.query.all(),
                                     available_detail_types=AssetDetailService.get_available_asset_detail_types())
            
            # Check for duplicate
            existing = AssetDetailTemplateByModelType.query.filter_by(
                make_model_id=make_model_id,
                detail_table_type=detail_table_type
            ).first()
            
            if existing:
                flash(f'Template already exists for this make/model and detail table type', 'error')
                return render_template('assets/detail_template_crud/asset_detail_template_by_model_type/create.html',
                                     make_models=MakeModel.query.all(),
                                     available_detail_types=AssetDetailService.get_available_asset_detail_types())
            
            record = AssetDetailTemplateByModelType(
                make_model_id=make_model_id,
                detail_table_type=detail_table_type,
                many_to_one=many_to_one,
                created_by_id=current_user.id,
                updated_by_id=current_user.id
            )
            db.session.add(record)
            db.session.commit()
            
            flash('Template created successfully', 'success')
            return redirect(url_for('assets.detail_template_crud.list_asset_detail_template_by_model_type'))
        except Exception as e:
            flash(f'Error creating template: {str(e)}', 'error')
            logger.error(f"Error creating AssetDetailTemplateByModelType: {e}")
            db.session.rollback()
    
    return render_template('assets/detail_template_crud/asset_detail_template_by_model_type/create.html',
                         make_models=MakeModel.query.all(),
                         available_detail_types=AssetDetailService.get_available_asset_detail_types())


@bp.route('/asset-detail-template-by-model-type/<int:id>')
@login_required
def detail_asset_detail_template_by_model_type(id):
    """View AssetDetailTemplateByModelType record details"""
    record = AssetDetailTemplateByModelType.query.get_or_404(id)
    make_model = MakeModel.query.get(record.make_model_id) if record.make_model_id else None
    available_detail_types = {
        dt['type']: dt['name'] 
        for dt in AssetDetailService.get_available_asset_detail_types()
    }
    
    return render_template('assets/detail_template_crud/asset_detail_template_by_model_type/detail.html',
                         record=record,
                         make_model=make_model,
                         available_detail_types=available_detail_types)


@bp.route('/asset-detail-template-by-model-type/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_asset_detail_template_by_model_type(id):
    """Edit AssetDetailTemplateByModelType record"""
    record = AssetDetailTemplateByModelType.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            make_model_id = request.form.get('make_model_id', type=int)
            detail_table_type = request.form.get('detail_table_type')
            many_to_one = request.form.get('many_to_one') == 'on'
            
            if not make_model_id:
                flash('Make/Model is required', 'error')
                return render_template('assets/detail_template_crud/asset_detail_template_by_model_type/edit.html',
                                     record=record,
                                     make_models=MakeModel.query.all(),
                                     available_detail_types=AssetDetailService.get_available_asset_detail_types())
            
            if not detail_table_type:
                flash('Detail Table Type is required', 'error')
                return render_template('assets/detail_template_crud/asset_detail_template_by_model_type/edit.html',
                                     record=record,
                                     make_models=MakeModel.query.all(),
                                     available_detail_types=AssetDetailService.get_available_asset_detail_types())
            
            # Check for duplicate (excluding current record)
            existing = AssetDetailTemplateByModelType.query.filter(
                AssetDetailTemplateByModelType.make_model_id == make_model_id,
                AssetDetailTemplateByModelType.detail_table_type == detail_table_type,
                AssetDetailTemplateByModelType.id != id
            ).first()
            
            if existing:
                flash(f'Template already exists for this make/model and detail table type', 'error')
                return render_template('assets/detail_template_crud/asset_detail_template_by_model_type/edit.html',
                                     record=record,
                                     make_models=MakeModel.query.all(),
                                     available_detail_types=AssetDetailService.get_available_asset_detail_types())
            
            record.make_model_id = make_model_id
            record.detail_table_type = detail_table_type
            record.many_to_one = many_to_one
            record.updated_by_id = current_user.id
            
            db.session.commit()
            flash('Template updated successfully', 'success')
            return redirect(url_for('assets.detail_template_crud.detail_asset_detail_template_by_model_type', id=id))
        except Exception as e:
            flash(f'Error updating template: {str(e)}', 'error')
            logger.error(f"Error updating AssetDetailTemplateByModelType: {e}")
            db.session.rollback()
    
    return render_template('assets/detail_template_crud/asset_detail_template_by_model_type/edit.html',
                         record=record,
                         make_models=MakeModel.query.all(),
                         available_detail_types=AssetDetailService.get_available_asset_detail_types())


@bp.route('/asset-detail-template-by-model-type/<int:id>/delete', methods=['POST'])
@login_required
def delete_asset_detail_template_by_model_type(id):
    """Delete AssetDetailTemplateByModelType record"""
    record = AssetDetailTemplateByModelType.query.get_or_404(id)
    
    try:
        db.session.delete(record)
        db.session.commit()
        flash('Template deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting template: {str(e)}', 'error')
        logger.error(f"Error deleting AssetDetailTemplateByModelType: {e}")
        db.session.rollback()
    
    return redirect(url_for('assets.detail_template_crud.list_asset_detail_template_by_model_type'))


# ============================================================================
# ModelDetailTableTemplate CRUD
# ============================================================================

@bp.route('/model-detail-table-template/')
@login_required
def list_model_detail_table_template():
    """List all ModelDetailTableTemplate records"""
    records = ModelDetailTableTemplate.query.order_by(
        ModelDetailTableTemplate.asset_type_id,
        ModelDetailTableTemplate.detail_table_type
    ).all()
    
    # Get asset types and detail types for display
    asset_types = {at.id: at for at in AssetType.query.all()}
    available_detail_types = {
        dt['type']: dt['name'] 
        for dt in AssetDetailService.get_available_model_detail_types()
    }
    
    return render_template('assets/detail_template_crud/model_detail_table_template/list.html',
                         records=records,
                         asset_types=asset_types,
                         available_detail_types=available_detail_types)


@bp.route('/model-detail-table-template/create', methods=['GET', 'POST'])
@login_required
def create_model_detail_table_template():
    """Create new ModelDetailTableTemplate record"""
    if request.method == 'POST':
        try:
            asset_type_id = request.form.get('asset_type_id', type=int) or None
            detail_table_type = request.form.get('detail_table_type')
            
            if not detail_table_type:
                flash('Detail Table Type is required', 'error')
                return render_template('assets/detail_template_crud/model_detail_table_template/create.html',
                                     asset_types=AssetType.query.all(),
                                     available_detail_types=AssetDetailService.get_available_model_detail_types())
            
            # Check for duplicate
            existing = ModelDetailTableTemplate.query.filter_by(
                asset_type_id=asset_type_id,
                detail_table_type=detail_table_type
            ).first()
            
            if existing:
                flash(f'Template already exists for this asset type and detail table type', 'error')
                return render_template('assets/detail_template_crud/model_detail_table_template/create.html',
                                     asset_types=AssetType.query.all(),
                                     available_detail_types=AssetDetailService.get_available_model_detail_types())
            
            record = ModelDetailTableTemplate(
                asset_type_id=asset_type_id,
                detail_table_type=detail_table_type,
                created_by_id=current_user.id,
                updated_by_id=current_user.id
            )
            db.session.add(record)
            db.session.commit()
            
            flash('Template created successfully', 'success')
            return redirect(url_for('assets.detail_template_crud.list_model_detail_table_template'))
        except Exception as e:
            flash(f'Error creating template: {str(e)}', 'error')
            logger.error(f"Error creating ModelDetailTableTemplate: {e}")
            db.session.rollback()
    
    return render_template('assets/detail_template_crud/model_detail_table_template/create.html',
                         asset_types=AssetType.query.all(),
                         available_detail_types=AssetDetailService.get_available_model_detail_types())


@bp.route('/model-detail-table-template/<int:id>')
@login_required
def detail_model_detail_table_template(id):
    """View ModelDetailTableTemplate record details"""
    record = ModelDetailTableTemplate.query.get_or_404(id)
    asset_type = AssetType.query.get(record.asset_type_id) if record.asset_type_id else None
    available_detail_types = {
        dt['type']: dt['name'] 
        for dt in AssetDetailService.get_available_model_detail_types()
    }
    
    return render_template('assets/detail_template_crud/model_detail_table_template/detail.html',
                         record=record,
                         asset_type=asset_type,
                         available_detail_types=available_detail_types)


@bp.route('/model-detail-table-template/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_model_detail_table_template(id):
    """Edit ModelDetailTableTemplate record"""
    record = ModelDetailTableTemplate.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            asset_type_id = request.form.get('asset_type_id', type=int) or None
            detail_table_type = request.form.get('detail_table_type')
            
            if not detail_table_type:
                flash('Detail Table Type is required', 'error')
                return render_template('assets/detail_template_crud/model_detail_table_template/edit.html',
                                     record=record,
                                     asset_types=AssetType.query.all(),
                                     available_detail_types=AssetDetailService.get_available_model_detail_types())
            
            # Check for duplicate (excluding current record)
            existing = ModelDetailTableTemplate.query.filter(
                ModelDetailTableTemplate.asset_type_id == asset_type_id,
                ModelDetailTableTemplate.detail_table_type == detail_table_type,
                ModelDetailTableTemplate.id != id
            ).first()
            
            if existing:
                flash(f'Template already exists for this asset type and detail table type', 'error')
                return render_template('assets/detail_template_crud/model_detail_table_template/edit.html',
                                     record=record,
                                     asset_types=AssetType.query.all(),
                                     available_detail_types=AssetDetailService.get_available_model_detail_types())
            
            record.asset_type_id = asset_type_id
            record.detail_table_type = detail_table_type
            record.updated_by_id = current_user.id
            
            db.session.commit()
            flash('Template updated successfully', 'success')
            return redirect(url_for('assets.detail_template_crud.detail_model_detail_table_template', id=id))
        except Exception as e:
            flash(f'Error updating template: {str(e)}', 'error')
            logger.error(f"Error updating ModelDetailTableTemplate: {e}")
            db.session.rollback()
    
    return render_template('assets/detail_template_crud/model_detail_table_template/edit.html',
                         record=record,
                         asset_types=AssetType.query.all(),
                         available_detail_types=AssetDetailService.get_available_model_detail_types())


@bp.route('/model-detail-table-template/<int:id>/delete', methods=['POST'])
@login_required
def delete_model_detail_table_template(id):
    """Delete ModelDetailTableTemplate record"""
    record = ModelDetailTableTemplate.query.get_or_404(id)
    
    try:
        db.session.delete(record)
        db.session.commit()
        flash('Template deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting template: {str(e)}', 'error')
        logger.error(f"Error deleting ModelDetailTableTemplate: {e}")
        db.session.rollback()
    
    return redirect(url_for('assets.detail_template_crud.list_model_detail_table_template'))

