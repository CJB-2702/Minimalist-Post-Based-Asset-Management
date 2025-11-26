#!/usr/bin/env python3
"""
Core Debug Data Insertion
Inserts debug data for core module (users, locations, asset types, make/models, assets)

Uses factories and contexts for data creation.
"""

from app import db
from app.logger import get_logger

logger = get_logger("asset_management.debug.core")


def insert_core_debug_data(debug_data, system_user_id):
    """
    Insert debug data for core module
    
    Args:
        debug_data (dict): Debug data from JSON file
        system_user_id (int): System user ID for audit fields
    
    Raises:
        Exception: If insertion fails (fail-fast)
    """
    if not debug_data:
        logger.info("No core debug data to insert")
        return
    
    logger.info("Inserting core debug data...")
    
    try:
        # Insert users
        if 'Core' in debug_data and 'Users' in debug_data['Core']:
            _insert_users(debug_data['Core']['Users'], system_user_id)
        
        # Insert locations
        if 'Core' in debug_data and 'Locations' in debug_data['Core']:
            _insert_locations(debug_data['Core']['Locations'], system_user_id)
        
        # Insert asset types
        if 'Core' in debug_data and 'Asset_Types' in debug_data['Core']:
            _insert_asset_types(debug_data['Core']['Asset_Types'], system_user_id)
        
        # Insert make/models
        if 'Core' in debug_data and 'Make_Models' in debug_data['Core']:
            _insert_make_models(debug_data['Core']['Make_Models'], system_user_id)
        
        # Insert assets
        if 'Core' in debug_data and 'Assets' in debug_data['Core']:
            _insert_assets(debug_data['Core']['Assets'], system_user_id)
        
        # Insert supply (parts and tools) - now part of core
        if 'Core' in debug_data and 'Supply' in debug_data['Core']:
            _insert_supply(debug_data['Core']['Supply'], system_user_id)
        
        db.session.commit()
        logger.info("Successfully inserted core debug data")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to insert core debug data: {e}")
        raise


def _insert_users(users_data, system_user_id):
    """Insert users using find_or_create_from_dict"""
    from app.data.core.user_info.user import User
    
    for user_key, user_data in users_data.items():
        # Skip if user already exists (by ID or username)
        if 'id' in user_data:
            existing = User.query.filter_by(id=user_data['id']).first()
            if existing:
                logger.debug(f"User {user_data.get('username')} already exists, skipping")
                continue
        
        User.find_or_create_from_dict(
            user_data,
            user_id=system_user_id,
            lookup_fields=['username']
        )
        logger.debug(f"Inserted user: {user_data.get('username')}")


def _insert_locations(locations_data, system_user_id):
    """Insert locations using find_or_create_from_dict"""
    from app.data.core.major_location import MajorLocation
    
    for loc_key, loc_data in locations_data.items():
        # Skip if location already exists (by name)
        if 'name' in loc_data:
            existing = MajorLocation.query.filter_by(name=loc_data['name']).first()
            if existing:
                logger.debug(f"Location {loc_data['name']} already exists, skipping")
                continue
        
        MajorLocation.find_or_create_from_dict(
            loc_data,
            user_id=system_user_id,
            lookup_fields=['name']
        )
        logger.debug(f"Inserted location: {loc_data.get('name')}")


def _insert_asset_types(asset_types_data, system_user_id):
    """Insert asset types using find_or_create_from_dict"""
    from app.data.core.asset_info.asset_type import AssetType
    
    for type_key, type_data in asset_types_data.items():
        # Skip if asset type already exists (by name)
        if 'name' in type_data:
            existing = AssetType.query.filter_by(name=type_data['name']).first()
            if existing:
                logger.debug(f"Asset type {type_data['name']} already exists, skipping")
                continue
        
        AssetType.find_or_create_from_dict(
            type_data,
            user_id=system_user_id,
            lookup_fields=['name']
        )
        logger.debug(f"Inserted asset type: {type_data.get('name')}")


def _insert_make_models(make_models_data, system_user_id):
    """Insert make/models using MakeModelContext.create_from_dict()"""
    from app.data.core.asset_info.asset_type import AssetType
    from app.buisness.core.make_model_context import MakeModelContext
    
    for model_key, model_data in make_models_data.items():
        # Handle asset_type_name reference
        if 'asset_type_name' in model_data:
            asset_type_name = model_data.pop('asset_type_name')
            asset_type = AssetType.query.filter_by(name=asset_type_name).first()
            if asset_type:
                model_data['asset_type_id'] = asset_type.id
            else:
                logger.warning(f"Asset type '{asset_type_name}' not found for make/model {model_data.get('make')} {model_data.get('model')}")
                continue
        
        # Use MakeModelContext to create make/model (handles duplicate checking via lookup_fields)
        MakeModelContext.create_from_dict(
            make_model_data=model_data,
            created_by_id=system_user_id,
            commit=False,  # Commit all at once at the end
            lookup_fields=['make', 'model', 'year']
        )
        logger.debug(f"Inserted make/model: {model_data.get('make')} {model_data.get('model')}")


def _insert_assets(assets_data, system_user_id):
    """Insert assets using AssetContext.create()"""
    from app.data.core.major_location import MajorLocation
    from app.data.core.asset_info.make_model import MakeModel
    from app.buisness.core.asset_context import AssetContext
    
    for asset_key, asset_data in assets_data.items():
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
            existing = Asset.query.filter_by(serial_number=asset_data['serial_number']).first()
            if existing:
                logger.debug(f"Asset with serial_number '{asset_data['serial_number']}' already exists, skipping")
                continue
        
        # Use AssetContext.create() to create asset
        AssetContext.create(
            created_by_id=system_user_id,
            commit=False,  # Commit all at once at the end
            enable_detail_insertion=True,
            **asset_data
        )
        logger.debug(f"Inserted asset: {asset_data.get('name')}")


def _insert_supply(supply_data, system_user_id):
    """Insert supply data (parts and tools) - now part of core"""
    from app.data.core.supply.part import Part
    from app.data.core.supply.tool import Tool
    from app.data.core.user_info.user import User
    from datetime import datetime
    
    # Insert parts
    if 'parts' in supply_data:
        for part_data in supply_data['parts']:
            Part.find_or_create_from_dict(
                part_data,
                user_id=system_user_id,
                lookup_fields=['part_number']
            )
            logger.debug(f"Inserted part: {part_data.get('part_number')}")
    
    # Insert tools
    if 'tools' in supply_data:
        for tool_data in supply_data['tools']:
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

