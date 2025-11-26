"""
Core models build module for the Asset Management System
Handles building and initializing core foundation models and data
"""

from app import db
from app.logger import get_logger

logger = get_logger("asset_management.models.core")

def build_models():
    """
    Build core models - this is a no-op since models are imported
    when the app is created, which registers them with SQLAlchemy
    """
    import app.data.core.user_info.user
    import app.data.core.major_location
    import app.data.core.asset_info.asset_type
    import app.data.core.asset_info.make_model
    import app.data.core.asset_info.asset
    import app.data.core.event_info.event
    import app.data.core.event_info.attachment
    import app.data.core.event_info.comment
    
    # Initialize attachment sequence
    from app.data.core.sequences import AttachmentIDManager
    AttachmentIDManager.create_sequence_if_not_exists()
    
    # Initialize event detail sequence
    from app.data.core.sequences import EventDetailIDManager
    EventDetailIDManager.create_sequence_if_not_exists()
    
    logger.info("Core models build completed")
    pass


def create_system_initialization_event(system_user_id=None, force_create=False):
    """
    Create system initialization event only if it's the first time or if forced
    
    Args:
        system_user_id (int, optional): System user ID for audit fields
        force_create (bool): Force creation even if event exists (for system failures)
    """
    from app.data.core.event_info.event import Event
    
    # Check if system initialization event already exists
    existing_event = Event.query.filter_by(
        event_type='System',
        description='System initialized with core data'
    ).first()
    
    if existing_event and not force_create:
        logger.info("System initialization event already exists, skipping creation")
        return existing_event
    
    # Create system initialization event
    event_data = {
        'event_type': 'System',
        'description': 'System initialized with core data'
    }
    
    event = Event.find_or_create_from_dict(
        event_data,
        user_id=system_user_id,
        lookup_fields=['event_type', 'description']
    )
    
    if event[1]:  # If newly created
        logger.info("Created system initialization event")
    else:
        logger.info("System initialization event already existed")
    
    return event[0]


def create_system_failure_event(system_user_id=None, error_message=None):
    """
    Create system failure event to indicate system initialization problems
    
    Args:
        system_user_id (int, optional): System user ID for audit fields
        error_message (str, optional): Error message to include in description
    """
    from app.data.core.event_info.event import Event
    
    description = 'System initialization failed'
    if error_message:
        description += f': {error_message}'
    
    # Create system failure event
    event_data = {
        'event_type': 'System',
        'description': description
    }
    
    event = Event.find_or_create_from_dict(
        event_data,
        user_id=system_user_id,
        lookup_fields=['event_type', 'description']
    )
    
    if event[1]:  # If newly created
        logger.warning(f"Created system failure event: {description}")
    else:
        logger.warning(f"System failure event already existed: {description}")
    
    return event[0]


# Data insertion functions have been removed
# All test/debug data insertion is now handled by app/debug/debug_data_manager.py
# Critical data insertion is handled by app/build.py insert_critical_data()
# This file now only contains table creation logic (build_models) and utility functions 