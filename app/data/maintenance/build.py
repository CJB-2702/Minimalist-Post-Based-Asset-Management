"""
Maintenance models build module for the Asset Management System
Handles building and initializing maintenance models and data
"""

from app import db
from app.logger import get_logger
from datetime import datetime

logger = get_logger("asset_management.models.maintenance")

def build_models():
    """
    Build maintenance models - this is a no-op since models are imported
    when the app is created, which registers them with SQLAlchemy
    """
    # Import virtual base classes
    import app.data.maintenance.virtual_action_item
    import app.data.maintenance.virtual_action_set
    import app.data.maintenance.virtual_part_demand
    import app.data.maintenance.virtual_action_tool
    
    # Import base models
    import app.data.maintenance.base.actions
    import app.data.maintenance.base.maintenance_action_sets
    import app.data.maintenance.planning.maintenance_plans
    import app.data.maintenance.base.maintenance_blockers
    import app.data.maintenance.base.asset_limitation_records
    import app.data.maintenance.base.part_demands
    import app.data.maintenance.base.action_tools
    
    # Import template models
    import app.data.maintenance.templates.template_action_sets
    import app.data.maintenance.templates.template_actions
    import app.data.maintenance.templates.template_part_demands
    import app.data.maintenance.templates.template_action_tools
    import app.data.maintenance.templates.template_action_set_attachments
    import app.data.maintenance.templates.template_action_attachments
    
    # Import proto models
    import app.data.maintenance.proto_templates.proto_actions
    import app.data.maintenance.proto_templates.proto_part_demands
    import app.data.maintenance.proto_templates.proto_action_tools
    import app.data.maintenance.proto_templates.proto_action_attachments
    
    # Note: Factories are business logic and are located in app/buisness/maintenance/factories/
    # They are not needed for model building
    
    # Note: Utilities are business logic and are located in app/buisness/maintenance/utils/
    # They are not needed for model building
    
    # Create all tables to ensure they exist
    db.create_all()
    
    logger.info("Maintenance models build completed")


# Data insertion functions have been removed
# All test/debug data insertion is now handled by app/debug/debug_data_manager.py
# This file now only contains table creation logic (build_models) and utility functions


# All _init_* data insertion functions have been removed
# All test/debug data insertion is now handled by app/debug/debug_data_manager.py
# This file now only contains table creation logic (build_models) and utility functions


def create_maintenance_from_template(template_action_set_id, asset_id, user_id, **kwargs):
    """
    Convenience function to create maintenance from template using factories
    
    Args:
        template_action_set_id (int): ID of the template to use
        asset_id (int): ID of the asset to maintain
        user_id (int): ID of the user creating the maintenance
        **kwargs: Additional parameters for maintenance creation
    
    Returns:
        dict: Created maintenance objects
    """
    # This will be implemented in business layer factories
    # For now, just raise NotImplementedError
    raise NotImplementedError("This function will be implemented in business layer factories")


def get_template_preview(template_action_set_id):
    """
    Convenience function to get template preview
    
    Args:
        template_action_set_id (int): ID of the template to preview
    
    Returns:
        dict: Template preview information
    """
    # This will be implemented in business layer
    # For now, just raise NotImplementedError
    raise NotImplementedError("This function will be implemented in business layer")
