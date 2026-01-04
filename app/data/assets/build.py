"""
Asset detail models build module for the Asset Management System
Handles building and initializing asset detail models and data
"""
from app import db
from app.logger import get_logger
from datetime import datetime
from pathlib import Path

logger = get_logger("asset_management.models.assets")

# Detail table registry is now handled by the DetailFactory class

def build_models():
    """
    Build asset detail models - this is a no-op since models are imported
    when the app is created, which registers them with SQLAlchemy
    """
    # Import virtual base classes
    import app.data.assets.asset_detail_virtual
    import app.data.assets.model_detail_virtual
    
    # Import asset detail models
    import app.data.assets.asset_type_details.purchase_info
    import app.data.assets.asset_type_details.vehicle_registration
    import app.data.assets.asset_type_details.toyota_warranty_receipt
    import app.data.assets.asset_type_details.smog_record
    
    # Import model detail models
    import app.data.assets.model_details.emissions_info
    import app.data.assets.model_details.model_info
    
    # Import asset parent history
    import app.data.assets.asset_parent_history
    
    # Import detail table templates
    import app.data.assets.detail_table_templates.asset_details_from_asset_type
    import app.data.assets.detail_table_templates.asset_details_from_model_type
    import app.data.assets.detail_table_templates.model_detail_table_template
    
    # Import detail factories (now in domain layer)
    import app.buisness.assets.factories.detail_factory
    import app.buisness.assets.factories.asset_detail_factory
    import app.buisness.assets.factories.model_detail_factory
    
    # Initialize ID sequences
    from app.data.core.sequences import AssetDetailIDManager, ModelDetailIDManager
    AssetDetailIDManager.create_sequence_if_not_exists()
    ModelDetailIDManager.create_sequence_if_not_exists()
    
    # Note: Asset detail insertion is now handled automatically by AssetDetailsFactory
    # which is registered with AssetContext when the assets module is imported.
    # No manual enabling is needed - the factory pattern handles it.
    
    # Enable automatic detail insertion for models (models still use event listeners)
    from app.data.core.asset_info.make_model import MakeModel
    MakeModel.enable_automatic_detail_insertion()
    
    # Create all tables to ensure they exist
    db.create_all()
    
    logger.info("build_models: Asset Models Created")
    pass

def get_detail_table_class(table_type):
    """
    Get the detail table class for a given table type
    
    Args:
        table_type (str): The detail table type (e.g., 'purchase_info')
        
    Returns:
        class: The detail table class
    """
    from app.buisness.assets.factories.detail_factory import DetailFactory
    return DetailFactory.get_detail_table_class(table_type)

def is_asset_detail(table_type):
    """
    Check if a detail table type is an asset detail
    
    Args:
        table_type (str): The detail table type
        
    Returns:
        bool: True if it's an asset detail, False if it's a model detail
    """
    from app.buisness.assets.factories.detail_factory import DetailFactory
    return DetailFactory.is_asset_detail(table_type)

def convert_date_strings(data):
    """
    Convert date strings in data to date objects
    
    Args:
        data (dict): Data dictionary that may contain date strings
        
    Returns:
        dict: Data with date strings converted to date objects
    """
    converted_data = data.copy()
    for key, value in converted_data.items():
        if isinstance(value, str) and (key.endswith('_date') or key.endswith('_expiry')):
            try:
                converted_data[key] = datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                pass  # Keep as string if parsing fails
    return converted_data

# Data insertion functions have been removed
# All test/debug data insertion is now handled by app/debug/debug_data_manager.py
# This file now only contains table creation logic (build_models) and utility functions


