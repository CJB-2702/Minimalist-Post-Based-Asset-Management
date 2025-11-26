#!/usr/bin/env python3
"""
Dispatching Debug Data Insertion
Inserts debug data for dispatching module

Uses factories and contexts for data creation.
"""

from app import db
from app.logger import get_logger
from datetime import datetime

logger = get_logger("asset_management.debug.dispatching")


def insert_dispatching_debug_data(debug_data, system_user_id):
    """
    Insert debug data for dispatching module
    
    Args:
        debug_data (dict): Debug data from JSON file
        system_user_id (int): System user ID for audit fields
    
    Raises:
        Exception: If insertion fails (fail-fast)
    """
    if not debug_data:
        logger.info("No dispatching debug data to insert")
        return
    
    logger.info("Inserting dispatching debug data...")
    
    try:
        dispatching_data = debug_data.get('Dispatching', {})
        
        # 1. Insert users
        if 'Users' in dispatching_data:
            _insert_dispatching_users(dispatching_data['Users'], system_user_id)
        
        # 2. Insert dispatch detail table sets
        if 'Dispatch_Detail_Table_Sets' in dispatching_data:
            _insert_dispatch_detail_table_sets(
                dispatching_data['Dispatch_Detail_Table_Sets'],
                system_user_id
            )
        
        # 3. Insert example dispatches
        if 'Example_Dispatches' in dispatching_data:
            _insert_example_dispatches(
                dispatching_data['Example_Dispatches'],
                system_user_id
            )
        
        db.session.commit()
        logger.info("Successfully inserted dispatching debug data")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to insert dispatching debug data: {e}")
        raise


def _insert_dispatching_users(users_data, system_user_id):
    """Insert dispatching users"""
    from app.data.core.user_info.user import User
    
    for user_key, user_data in users_data.items():
        User.find_or_create_from_dict(
            user_data,
            user_id=system_user_id,
            lookup_fields=['username']
        )
        logger.debug(f"Inserted dispatching user: {user_data.get('username')}")


def _insert_dispatch_detail_table_sets(sets_data, system_user_id):
    """Insert dispatch detail table set configurations"""
    # Note: These models may not exist yet - this is a placeholder
    # Implementation depends on actual dispatching models
    logger.info("Dispatch detail table sets insertion - models may need to be implemented")
    # TODO: Implement when dispatching models are available


def _insert_example_dispatches(dispatches_data, system_user_id):
    """Insert example dispatch records"""
    # Note: These models may not exist yet - this is a placeholder
    # Implementation depends on actual dispatching models
    logger.info("Example dispatches insertion - models may need to be implemented")
    # TODO: Implement when dispatching models are available

