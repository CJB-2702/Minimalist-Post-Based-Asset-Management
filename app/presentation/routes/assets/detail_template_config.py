"""
Detail Template Configuration Routes
Routes for configuring which detail tables auto-create for asset types and make/models
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
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

bp = Blueprint('detail_template_config', __name__)
logger = get_logger("asset_management.routes.assets.detail_template_config")


@bp.route('/configure/asset-type/<int:asset_type_id>', methods=['GET', 'POST'])
@login_required
def configure_asset_type(asset_type_id):
    """Configure detail table templates for an asset type"""
    asset_type = AssetType.query.get_or_404(asset_type_id)
    
    if request.method == 'POST':
        try:
            # Get existing configurations
            existing_configs = {
                config.detail_table_type: config
                for config in AssetDetailTemplateByAssetType.query.filter_by(asset_type_id=asset_type_id).all()
            }
            
            # Process form data
            detail_types = request.form.getlist('detail_types')
            many_to_one_flags = {}
            
            for detail_type in detail_types:
                many_to_one_key = f'many_to_one_{detail_type}'
                many_to_one_flags[detail_type] = request.form.get(many_to_one_key) == 'on'
            
            # Remove configurations that are no longer selected
            for existing_type, config in existing_configs.items():
                if existing_type not in detail_types:
                    db.session.delete(config)
            
            # Add or update configurations
            for detail_type in detail_types:
                if detail_type in existing_configs:
                    # Update existing
                    config = existing_configs[detail_type]
                    config.many_to_one = many_to_one_flags.get(detail_type, False)
                    config.updated_by_id = current_user.id
                else:
                    # Create new
                    config = AssetDetailTemplateByAssetType(
                        asset_type_id=asset_type_id,
                        detail_table_type=detail_type,
                        many_to_one=many_to_one_flags.get(detail_type, False),
                        created_by_id=current_user.id,
                        updated_by_id=current_user.id
                    )
                    db.session.add(config)
            
            db.session.commit()
            flash(f'Detail table templates configured successfully for {asset_type.name}', 'success')
            logger.info(f"User {current_user.username} configured detail templates for asset type {asset_type_id}")
            
            # Redirect based on source
            if request.form.get('redirect_to') == 'create_asset':
                return redirect(url_for('core_assets.create'))
            elif request.form.get('redirect_to') == 'create_make_model':
                return redirect(url_for('make_models.create'))
            else:
                return redirect(url_for('detail_template_config.configure_asset_type', asset_type_id=asset_type_id))
                
        except Exception as e:
            flash(f'Error configuring detail templates: {str(e)}', 'error')
            logger.error(f"Error configuring detail templates: {e}")
            db.session.rollback()
    
    # Get existing configurations
    existing_configs = {
        config.detail_table_type: config
        for config in AssetDetailTemplateByAssetType.query.filter_by(asset_type_id=asset_type_id).all()
    }
    
    # Get available detail types
    available_types = AssetDetailService.get_available_asset_detail_types()
    
    return render_template('assets/detail_template_config/configure_asset_type.html',
                         asset_type=asset_type,
                         available_types=available_types,
                         existing_configs=existing_configs)


@bp.route('/configure/make-model/<int:make_model_id>', methods=['GET', 'POST'])
@login_required
def configure_make_model(make_model_id):
    """Configure detail table templates for a make/model"""
    make_model = MakeModel.query.get_or_404(make_model_id)
    
    if request.method == 'POST':
        try:
            # Get existing configurations
            existing_configs = {
                config.detail_table_type: config
                for config in AssetDetailTemplateByModelType.query.filter_by(make_model_id=make_model_id).all()
            }
            
            # Process form data
            detail_types = request.form.getlist('detail_types')
            many_to_one_flags = {}
            
            for detail_type in detail_types:
                many_to_one_key = f'many_to_one_{detail_type}'
                many_to_one_flags[detail_type] = request.form.get(many_to_one_key) == 'on'
            
            # Remove configurations that are no longer selected
            for existing_type, config in existing_configs.items():
                if existing_type not in detail_types:
                    db.session.delete(config)
            
            # Add or update configurations
            for detail_type in detail_types:
                if detail_type in existing_configs:
                    # Update existing
                    config = existing_configs[detail_type]
                    config.many_to_one = many_to_one_flags.get(detail_type, False)
                    config.updated_by_id = current_user.id
                else:
                    # Create new
                    config = AssetDetailTemplateByModelType(
                        make_model_id=make_model_id,
                        detail_table_type=detail_type,
                        many_to_one=many_to_one_flags.get(detail_type, False),
                        created_by_id=current_user.id,
                        updated_by_id=current_user.id
                    )
                    db.session.add(config)
            
            db.session.commit()
            flash(f'Detail table templates configured successfully for {make_model.make} {make_model.model}', 'success')
            logger.info(f"User {current_user.username} configured detail templates for make/model {make_model_id}")
            
            # Redirect based on source
            if request.form.get('redirect_to') == 'create_asset':
                return redirect(url_for('core_assets.create'))
            elif request.form.get('redirect_to') == 'create_make_model':
                return redirect(url_for('make_models.create'))
            else:
                return redirect(url_for('detail_template_config.configure_make_model', make_model_id=make_model_id))
                
        except Exception as e:
            flash(f'Error configuring detail templates: {str(e)}', 'error')
            logger.error(f"Error configuring detail templates: {e}")
            db.session.rollback()
    
    # Get existing configurations
    existing_configs = {
        config.detail_table_type: config
        for config in AssetDetailTemplateByModelType.query.filter_by(make_model_id=make_model_id).all()
    }
    
    # Get available detail types
    available_types = AssetDetailService.get_available_asset_detail_types()
    
    return render_template('assets/detail_template_config/configure_make_model.html',
                         make_model=make_model,
                         available_types=available_types,
                         existing_configs=existing_configs)


@bp.route('/configure/model-detail-template/asset-type/<int:asset_type_id>', methods=['GET', 'POST'])
@login_required
def configure_model_detail_template(asset_type_id):
    """Configure model detail table templates for an asset type"""
    asset_type = AssetType.query.get_or_404(asset_type_id)
    
    if request.method == 'POST':
        try:
            # Get existing configurations
            existing_configs = {
                config.detail_table_type: config
                for config in ModelDetailTableTemplate.query.filter_by(asset_type_id=asset_type_id).all()
            }
            
            # Process form data
            detail_types = request.form.getlist('detail_types')
            
            # Remove configurations that are no longer selected
            for existing_type, config in existing_configs.items():
                if existing_type not in detail_types:
                    db.session.delete(config)
            
            # Add or update configurations
            for detail_type in detail_types:
                if detail_type not in existing_configs:
                    # Create new
                    config = ModelDetailTableTemplate(
                        asset_type_id=asset_type_id,
                        detail_table_type=detail_type,
                        created_by_id=current_user.id,
                        updated_by_id=current_user.id
                    )
                    db.session.add(config)
            
            db.session.commit()
            flash(f'Model detail table templates configured successfully for {asset_type.name}', 'success')
            logger.info(f"User {current_user.username} configured model detail templates for asset type {asset_type_id}")
            
            # Redirect based on source
            if request.form.get('redirect_to') == 'create_make_model':
                return redirect(url_for('make_models.create'))
            else:
                return redirect(url_for('detail_template_config.configure_model_detail_template', asset_type_id=asset_type_id))
                
        except Exception as e:
            flash(f'Error configuring model detail templates: {str(e)}', 'error')
            logger.error(f"Error configuring model detail templates: {e}")
            db.session.rollback()
    
    # Get existing configurations
    existing_configs = {
        config.detail_table_type: config
        for config in ModelDetailTableTemplate.query.filter_by(asset_type_id=asset_type_id).all()
    }
    
    # Get available model detail types (non-asset detail types)
    available_types = AssetDetailService.get_available_model_detail_types()
    
    return render_template('assets/detail_template_config/configure_model_detail_template.html',
                         asset_type=asset_type,
                         available_types=available_types,
                         existing_configs=existing_configs)


@bp.route('/ajax/get-templates/<entity_type>/<int:entity_id>', methods=['GET'])
@login_required
def get_templates_ajax(entity_type, entity_id):
    """Get configured templates for an entity (asset_type or make_model) via AJAX"""
    try:
        if entity_type == 'asset_type':
            configs = AssetDetailTemplateByAssetType.query.filter_by(asset_type_id=entity_id).all()
            entity = AssetType.query.get_or_404(entity_id)
            entity_name = entity.name
        elif entity_type == 'make_model':
            configs = AssetDetailTemplateByModelType.query.filter_by(make_model_id=entity_id).all()
            entity = MakeModel.query.get_or_404(entity_id)
            entity_name = f"{entity.make} {entity.model}"
        else:
            return jsonify({'error': 'Invalid entity type'}), 400
        
        template_list = [
            {
                'detail_table_type': config.detail_table_type,
                'name': config.detail_table_type.replace('_', ' ').title(),
                'many_to_one': config.many_to_one
            }
            for config in configs
        ]
        
        return jsonify({
            'entity_name': entity_name,
            'templates': template_list
        })
    except Exception as e:
        logger.error(f"Error getting templates via AJAX: {e}")
        return jsonify({'error': str(e)}), 500

