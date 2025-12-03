#!/usr/bin/env python3
"""
Assets Debug Data Insertion
Inserts debug data for assets module (asset details, model details)

Uses factories and contexts for data creation.
"""

from app import db
from app.logger import get_logger
from datetime import datetime
from app.buisness.core.asset_context import AssetContext
from app.buisness.core.make_model_context import MakeModelContext

logger = get_logger("asset_management.debug.assets")


def insert_assets_debug_data(debug_data, system_user_id):
    """
    Insert debug data for assets module
    
    Args:
        debug_data (dict): Debug data from JSON file
        system_user_id (int): System user ID for audit fields
    
    Raises:
        Exception: If insertion fails (fail-fast)
    """
    if not debug_data:
        logger.info("No assets debug data to insert")
        return
    
    logger.info("Inserting assets debug data...")
    
    try:
        asset_details = debug_data.get('Asset_Details', {})
        
        # 1. Insert detail table templates
        if 'Detail_Table_Templates' in asset_details:
            _insert_detail_table_templates(asset_details['Detail_Table_Templates'], system_user_id)
        
        # 2. Insert models for automatic detail insertion
        if 'Models_for_automatic_detail_insertion' in asset_details:
            _insert_models_for_automatic_detail_insertion(
                asset_details['Models_for_automatic_detail_insertion'], 
                system_user_id
            )
        
        # 3. Insert assets for automatic detail insertion
        if 'Assets_for_automatic_detail_insertion' in asset_details:
            _insert_assets_for_automatic_detail_insertion(
                asset_details['Assets_for_automatic_detail_insertion'],
                system_user_id
            )
        
        # 4. Insert model details
        if 'Model_Details' in asset_details:
            _insert_model_details(asset_details['Model_Details'], system_user_id)
        
        db.session.commit()
        logger.info("Successfully inserted assets debug data")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to insert assets debug data: {e}")
        raise


def _insert_detail_table_templates(templates_data, system_user_id):
    """Insert detail table template configurations"""
    from app.data.assets.detail_table_templates.asset_details_from_asset_type import AssetDetailTemplateByAssetType
    from app.data.assets.detail_table_templates.asset_details_from_model_type import AssetDetailTemplateByModelType
    from app.data.assets.detail_table_templates.model_detail_table_template import ModelDetailTableTemplate
    from app.data.core.asset_info.asset_type import AssetType
    from app.data.core.asset_info.make_model import MakeModel
    
    # Insert Asset_details_from_asset_type
    if 'Asset_details_from_asset_type' in templates_data:
        for config_data in templates_data['Asset_details_from_asset_type']:
            asset_type_name = config_data.get('asset_type_name')
            
            # AssetDetailTemplateByAssetType requires asset_type_id (NOT NULL constraint)
            # Skip global templates (asset_type_name is None)
            if not asset_type_name:
                logger.debug(f"Skipping global template for AssetDetailTemplateByAssetType (requires asset_type_id)")
                continue
            
            asset_type = AssetType.query.filter_by(name=asset_type_name).first()
            if not asset_type:
                logger.warning(f"Asset type '{asset_type_name}' not found, skipping template")
                continue
            
            # Check if already exists
            existing = AssetDetailTemplateByAssetType.query.filter_by(
                asset_type_id=asset_type.id,
                detail_table_type=config_data['detail_table_type']
            ).first()
            
            if not existing:
                template = AssetDetailTemplateByAssetType(
                    asset_type_id=asset_type.id,
                    detail_table_type=config_data['detail_table_type'],
                    many_to_one=config_data.get('many_to_one', False),
                    created_by_id=system_user_id
                )
                db.session.add(template)
                logger.debug(f"Created asset type template: {asset_type_name} -> {config_data['detail_table_type']} (many_to_one={config_data.get('many_to_one', False)})")
    
    # Insert Asset_details_from_model_type
    if 'Asset_details_from_model_type' in templates_data:
        for config_data in templates_data['Asset_details_from_model_type']:
            make = config_data.get('make')
            model = config_data.get('model')
            
            make_model = MakeModel.query.filter_by(make=make, model=model).first()
            if not make_model:
                logger.warning(f"Make/model '{make} {model}' not found, skipping template")
                continue
            
            # Check if already exists
            existing = AssetDetailTemplateByModelType.query.filter_by(
                make_model_id=make_model.id,
                detail_table_type=config_data['detail_table_type']
            ).first()
            
            if not existing:
                template = AssetDetailTemplateByModelType(
                    make_model_id=make_model.id,
                    detail_table_type=config_data['detail_table_type'],
                    many_to_one=config_data.get('many_to_one', False),
                    created_by_id=system_user_id
                )
                db.session.add(template)
                logger.debug(f"Created model type template: {make} {model} -> {config_data['detail_table_type']} (many_to_one={config_data.get('many_to_one', False)})")
    
    # Insert Model_detail_table_template
    if 'Model_detail_table_template' in templates_data:
        for config_data in templates_data['Model_detail_table_template']:
            asset_type_name = config_data.get('asset_type_name')
            asset_type_id = None
            
            if asset_type_name:
                asset_type = AssetType.query.filter_by(name=asset_type_name).first()
                if asset_type:
                    asset_type_id = asset_type.id
                else:
                    logger.warning(f"Asset type '{asset_type_name}' not found, skipping template")
                    continue
            
            # Check if already exists
            existing = ModelDetailTableTemplate.query.filter_by(
                asset_type_id=asset_type_id,
                detail_table_type=config_data['detail_table_type']
            ).first()
            
            if not existing:
                template = ModelDetailTableTemplate(
                    asset_type_id=asset_type_id,
                    detail_table_type=config_data['detail_table_type'],
                    created_by_id=system_user_id
                )
                db.session.add(template)
                logger.debug(f"Created model detail template: {asset_type_name or 'Global'} -> {config_data['detail_table_type']}")


def _insert_models_for_automatic_detail_insertion(models_data, system_user_id):
    """Insert models using MakeModelContext.create_from_dict()"""
    from app.data.core.asset_info.asset_type import AssetType
    from app.buisness.core.make_model_context import MakeModelContext
    
    for model_data in models_data:
        # Set default asset type to Vehicle if not specified
        if 'asset_type_name' not in model_data and 'asset_type_id' not in model_data:
            asset_type = AssetType.query.filter_by(name='Vehicle').first()
            if asset_type:
                model_data['asset_type_id'] = asset_type.id
        
        # Use MakeModelContext to create make/model
        MakeModelContext.create_from_dict(
            make_model_data=model_data,
            created_by_id=system_user_id,
            commit=False,
            lookup_fields=['make', 'model', 'year']
        )
        logger.debug(f"Created model: {model_data.get('make')} {model_data.get('model')}")


def _insert_assets_for_automatic_detail_insertion(assets_data, system_user_id):
    """Insert assets using AssetContext.create()"""
    from app.data.core.major_location import MajorLocation
    from app.data.core.asset_info.make_model import MakeModel
    
    for asset_data in assets_data:
        # Handle major_location_name reference
        if 'major_location_name' in asset_data:
            major_location_name = asset_data.pop('major_location_name')
            major_location = MajorLocation.query.filter_by(name=major_location_name).first()
            if major_location:
                asset_data['major_location_id'] = major_location.id
            else:
                logger.warning(f"Major location '{major_location_name}' not found for asset {asset_data.get('name', 'Unknown')}")
                continue
        
        # Handle make/model reference
        if 'make' in asset_data and 'model' in asset_data:
            make = asset_data.pop('make')
            model = asset_data.pop('model')
            year = asset_data.pop('year', None) if 'year' in asset_data else None
            
            make_model_query = MakeModel.query.filter_by(make=make, model=model)
            if year is not None:
                make_model_query = make_model_query.filter_by(year=year)
            
            make_model = make_model_query.first()
            if make_model:
                asset_data['make_model_id'] = make_model.id
            else:
                logger.warning(f"Make/model '{make} {model}' not found for asset {asset_data.get('name', 'Unknown')}")
                continue
        
        # Check if asset already exists by serial_number
        if 'serial_number' in asset_data:
            from app.data.core.asset_info.asset import Asset
            existing_asset = Asset.query.filter_by(serial_number=asset_data['serial_number']).first()
            if existing_asset:
                logger.debug(f"Asset with serial_number '{asset_data['serial_number']}' already exists, skipping")
                continue
        
        # Use AssetContext.create() to create asset
        AssetContext.create(
            created_by_id=system_user_id,
            commit=False,
            enable_detail_insertion=True,
            **asset_data
        )
        logger.debug(f"Created asset: {asset_data.get('name')}")


def _insert_model_details(model_details_data, system_user_id):
    """Insert model detail records (emissions_info, model_info)"""
    from app.data.core.asset_info.make_model import MakeModel
    from app.data.assets.model_details.emissions_info import EmissionsInfo
    from app.data.assets.model_details.model_info import ModelInfo
    
    for detail_key, detail_data in model_details_data.items():
        make = detail_data.get('make')
        model = detail_data.get('model')
        detail_type = detail_data.get('detail_type')
        
        if not make or not model or not detail_type:
            logger.warning(f"Skipping {detail_key} - missing make, model, or detail_type")
            continue
        
        # Find the make/model
        make_model = MakeModel.query.filter_by(make=make, model=model).first()
        if not make_model:
            logger.warning(f"Make/model not found for {make} {model}")
            continue
        
        # Remove meta fields
        detail_record_data = {k: v for k, v in detail_data.items() 
                            if k not in ['make', 'model', 'detail_type']}
        
        # Convert date strings
        detail_record_data = _convert_date_strings(detail_record_data)
        
        # Add audit fields
        detail_record_data['make_model_id'] = make_model.id
        detail_record_data['created_by_id'] = system_user_id
        detail_record_data['updated_by_id'] = system_user_id
        
        # Create the appropriate detail record
        if detail_type == 'emissions_info':
            existing = EmissionsInfo.query.filter_by(make_model_id=make_model.id).first()
            if not existing:
                detail_record = EmissionsInfo(**detail_record_data)
                db.session.add(detail_record)
                logger.debug(f"Created emissions_info for {make} {model}")
        elif detail_type == 'model_info':
            existing = ModelInfo.query.filter_by(make_model_id=make_model.id).first()
            if not existing:
                detail_record = ModelInfo(**detail_record_data)
                db.session.add(detail_record)
                logger.debug(f"Created model_info for {make} {model}")


def _convert_date_strings(data):
    """Convert date strings to date objects"""
    result = data.copy()
    for key, value in result.items():
        if isinstance(value, str) and ('date' in key.lower() or 'expiry' in key.lower()):
            try:
                result[key] = datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                pass  # Keep original if parsing fails
    return result

