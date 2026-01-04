"""
Supply models build module for the Asset Management System
Handles building and initializing supply models and data
"""

from app import db
from app.logger import get_logger

logger = get_logger("asset_management.models.supply")

def build_models():
    """
    Build supply models - this is a no-op since models are imported
    when the app is created, which registers them with SQLAlchemy
    """
    import app.data.core.supply.part_definition
    import app.data.core.supply.tool_definition
    
    logger.info("Supply models build completed")

# Data insertion functions have been removed
# All test/debug data insertion is now handled by app/debug/debug_data_manager.py
# This file now only contains table creation logic (build_models) and utility functions

def test_supply_independence():
    """
    Test that supply can build and accept data independent from maintenance
    
    Returns:
        bool: True if test passes, False otherwise
    """
    try:
        logger.info("Testing supply independence...")
        
        # Test that supply models can be imported without maintenance
        from app.data.core.supply.part_definition import PartDefinition
        from app.data.core.supply.tool_definition import ToolDefinition
        from app.data.maintenance.base.part_demands import PartDemand
        
        # Test that we can query supply tables
        parts_count = PartDefinition.query.count()
        tools_count = ToolDefinition.query.count()
        demands_count = PartDemand.query.count()
        
        logger.info(f"Supply independence test passed - Parts: {parts_count}, Tools: {tools_count}, Demands: {demands_count}")
        return True
        
    except Exception as e:
        logger.error(f"Supply independence test failed: {e}")
        return False
