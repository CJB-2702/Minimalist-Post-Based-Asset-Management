#!/usr/bin/env python3
"""
Inventory Debug Data Insertion
Inserts debug data for inventory module (parts, tools)

Uses factories and contexts for data creation.
"""

from app import db
from app.logger import get_logger
from datetime import datetime

logger = get_logger("asset_management.debug.inventory")


def insert_inventory_debug_data(debug_data, system_user_id):
    """
    Insert debug data for inventory module
    
    Args:
        debug_data (dict): Debug data from JSON file
        system_user_id (int): System user ID for audit fields
    
    Raises:
        Exception: If insertion fails (fail-fast)
    """
    if not debug_data:
        logger.info("No inventory debug data to insert")
        return
    
    logger.info("Inserting inventory debug data...")
    
    try:
        supply_data = debug_data.get('Supply', {})
        
        # 1. Insert parts
        if 'parts' in supply_data:
            _insert_parts(supply_data['parts'], system_user_id)
        
        # 2. Insert tools
        if 'tools' in supply_data:
            _insert_tools(supply_data['tools'], system_user_id)
        
        # Note: Part demands are inserted as part of maintenance actions, not here
        # Standalone part demands in inventory.json are skipped
        
        db.session.commit()
        logger.info("Successfully inserted inventory debug data")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to insert inventory debug data: {e}")
        raise


def _insert_parts(parts_data, system_user_id):
    """Insert parts using find_or_create_from_dict"""
    from app.data.core.supply.part import Part
    
    for part_data in parts_data:
        Part.find_or_create_from_dict(
            part_data,
            user_id=system_user_id,
            lookup_fields=['part_number']
        )
        logger.debug(f"Inserted part: {part_data.get('part_number')}")


def _insert_tools(tools_data, system_user_id):
    """Insert tools using find_or_create_from_dict"""
    from app.data.core.supply.tool import Tool
    from app.data.core.user_info.user import User
    
    for tool_data in tools_data:
        # Handle assigned_to_id reference
        if 'assigned_to_id' in tool_data and tool_data['assigned_to_id']:
            assigned_user = User.query.get(tool_data['assigned_to_id'])
            if not assigned_user:
                logger.warning(f"Assigned user {tool_data['assigned_to_id']} not found")
                tool_data['assigned_to_id'] = None
        
        # Handle date conversions
        for date_field in ['last_calibration_date', 'next_calibration_date']:
            if date_field in tool_data and tool_data[date_field]:
                try:
                    tool_data[date_field] = datetime.strptime(tool_data[date_field], '%Y-%m-%d').date()
                except ValueError:
                    logger.warning(f"Invalid date format for {date_field}")
                    tool_data.pop(date_field, None)
        
        Tool.find_or_create_from_dict(
            tool_data,
            user_id=system_user_id,
            lookup_fields=['tool_name']
        )
        logger.debug(f"Inserted tool: {tool_data.get('tool_name')}")


# Part demands are inserted as part of maintenance actions, not as standalone inventory items

