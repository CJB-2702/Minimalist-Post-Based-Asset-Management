#!/usr/bin/env python3
"""
Debug Data Manager
Central controller for debug data insertion

Handles:
- Loading debug data JSON files
- Checking if data is already present
- Orchestrating module-specific insertion functions
- Following build order: core → assets → dispatching → maintenance → inventory
- Fail-fast error handling
"""

from pathlib import Path
import json
from app import db
from app.logger import get_logger

logger = get_logger("asset_management.debug_data_manager")


def insert_debug_data(enabled=True, phase='all'):
    """
    Insert debug data for specified phase(s)
    
    Args:
        enabled (bool): Whether to insert debug data (default: True)
        phase (str): Phase to insert ('phase1', 'phase2', ..., 'all')
    
    Returns:
        dict: Summary of inserted data
    
    Raises:
        Exception: If any debug data insertion fails (fail-fast)
    """
    if not enabled:
        logger.info("Debug data insertion is disabled")
        return {}
    
    logger.info(f"Starting debug data insertion for phase: {phase}")
    
    # Get system user for audit fields
    from app.data.core.user_info.user import User
    system_user = User.query.filter_by(username='system').first()
    if not system_user:
        logger.error("System user not found - cannot insert debug data without system user")
        raise Exception("System user not found - critical data must be inserted first")
    
    system_user_id = system_user.id
    
    summary = {}
    
    # Follow build order: core (includes supply/parts/tools) → assets → dispatching → inventory → maintenance
    # Phase mapping: phase1=core, phase2=assets, phase3=dispatching, phase4=inventory, phase5/6=maintenance
    # Note: Supply (parts/tools) is now part of core module
    modules_to_insert = _get_modules_for_phase(phase)
    
    for module_name in modules_to_insert:
        try:
            # Load debug data file
            debug_data = _load_debug_data_file(module_name)
            if not debug_data:
                logger.info(f"No debug data file found for {module_name}, skipping")
                summary[module_name] = {'status': 'skipped', 'reason': 'file_not_found'}
                continue
            
            # Check if data already present
            if _check_debug_data_present(module_name, debug_data):
                logger.info(f"Debug data for {module_name} already present, skipping")
                summary[module_name] = {'status': 'skipped', 'reason': 'data_present'}
                continue
            
            # Insert debug data for this module
            logger.info(f"Inserting debug data for {module_name}...")
            _insert_module_debug_data(module_name, debug_data, system_user_id)
            summary[module_name] = {'status': 'inserted'}
            logger.info(f"Successfully inserted debug data for {module_name}")
            
        except Exception as e:
            logger.error(f"Failed to insert debug data for {module_name}: {e}")
            db.session.rollback()
            raise
    
    logger.info("Debug data insertion completed successfully")
    return summary


def _get_modules_for_phase(phase):
    """
    Get list of modules to insert based on phase
    
    Args:
        phase (str): Phase identifier
    
    Returns:
        list: List of module names in build order
    """
    # Build order: core (includes supply/parts/tools) → assets → dispatching → inventory → maintenance
    # Note: Supply (parts/tools) is now part of core module, so core must come before maintenance
    all_modules = ['core', 'assets', 'dispatching', 'inventory', 'maintenance']
    
    if phase == 'all':
        return all_modules
    elif phase == 'phase1':
        return ['core']
    elif phase == 'phase2':
        return ['core', 'assets']
    elif phase == 'phase3':
        return ['core', 'assets', 'dispatching']
    elif phase == 'phase4':
        return ['core', 'assets', 'dispatching', 'inventory', 'maintenance']
    elif phase in ['phase5', 'phase6']:
        return all_modules
    else:
        # Unknown phase, return all modules
        logger.warning(f"Unknown phase '{phase}', inserting all modules")
        return all_modules


def _load_debug_data_file(module_name):
    """
    Load debug data JSON file for a module
    
    Args:
        module_name (str): Name of module ('core', 'assets', etc.)
    
    Returns:
        dict: Debug data or None if file doesn't exist
    """
    debug_dir = Path(__file__).parent / 'data'
    debug_file = debug_dir / f'{module_name}.json'
    
    if not debug_file.exists():
        return None
    
    try:
        with open(debug_file, 'r') as f:
            data = json.load(f)
        logger.debug(f"Loaded debug data file: {debug_file}")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {debug_file}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading {debug_file}: {e}")
        raise


def _check_debug_data_present(module_name, debug_data):
    """
    Check if debug data for a module is already present
    
    Uses simple ID-based checks as specified in requirements.
    All debug data should specify IDs for presence detection.
    
    Args:
        module_name (str): Name of module ('core', 'assets', etc.)
        debug_data (dict): Debug data from JSON file
    
    Returns:
        bool: True if data present, False otherwise
    """
    # Simple checks based on module type
    # Each module should have key records with IDs that we can check
    
    if module_name == 'core':
        # Check for users, locations, assets, parts, tools by ID/name
        from app.data.core.user_info.user import User
        from app.data.core.major_location import MajorLocation
        from app.data.core.asset_info.asset import Asset
        from app.data.core.supply.part_definition import PartDefinition
        from app.data.core.supply.tool_definition import ToolDefinition
        
        # Check users
        if 'Users' in debug_data.get('Core', {}):
            for user_key, user_data in debug_data['Core']['Users'].items():
                if 'id' in user_data:
                    if User.query.filter_by(id=user_data['id']).first():
                        return True
        
        # Check locations
        if 'Locations' in debug_data.get('Core', {}):
            for loc_key, loc_data in debug_data['Core']['Locations'].items():
                # Locations don't have IDs in JSON, check by name
                if 'name' in loc_data:
                    if MajorLocation.query.filter_by(name=loc_data['name']).first():
                        return True
        
        # Check assets
        if 'Assets' in debug_data.get('Core', {}):
            for asset_key, asset_data in debug_data['Core']['Assets'].items():
                if 'id' in asset_data:
                    if Asset.query.filter_by(id=asset_data['id']).first():
                        return True
                # Also check by name
                if 'name' in asset_data:
                    if Asset.query.filter_by(name=asset_data['name']).first():
                        return True
        
        # Check supply (parts and tools) - now part of core
        if 'Supply' in debug_data.get('Core', {}):
            # Check parts
            if 'parts' in debug_data['Core']['Supply']:
                for part_data in debug_data['Core']['Supply']['parts']:
                    part_number = part_data.get('part_number')
                    if part_number:
                        if PartDefinition.query.filter_by(part_number=part_number).first():
                            return True
            
            # Check tools
            if 'tools' in debug_data['Core']['Supply']:
                for tool_data in debug_data['Core']['Supply']['tools']:
                    tool_name = tool_data.get('tool_name')
                    if tool_name:
                        if ToolDefinition.query.filter_by(tool_name=tool_name).first():
                            return True
    
    elif module_name == 'assets':
        # Check for asset details by checking if any assets have detail records
        # This is a simplified check - can be enhanced later
        from app.data.core.asset_info.asset import Asset
        assets = Asset.query.all()
        if assets:
            # If we have assets, assume details might be present
            # More specific checks can be added in module-specific function
            return False  # For now, always try to insert
    
    elif module_name == 'dispatching':
        # Check for dispatch records
        # Simplified check - can be enhanced
        return False
    
    elif module_name == 'maintenance':
        # Check for specific maintenance debug data
        # Check if proto part demands AND proto action tools exist (more specific check)
        from app.data.maintenance.proto_templates.proto_part_demands import ProtoPartDemand
        from app.data.maintenance.proto_templates.proto_action_tools import ProtoActionTool
        from app.data.core.supply.part_definition import PartDefinition
        from app.data.core.supply.tool_definition import ToolDefinition
        
        proto_part_demand_exists = False
        proto_action_tool_exists = False
        
        # Check if the specific proto part demand from debug data exists
        if 'Maintenance' in debug_data and 'proto_part_demands' in debug_data['Maintenance']:
            for demand_data in debug_data['Maintenance']['proto_part_demands']:
                part_number = demand_data.get('part_number')
                action_name = demand_data.get('proto_action_item_action_name')
                
                if part_number and action_name:
                    part = PartDefinition.query.filter_by(part_number=part_number).first()
                    if part:
                        from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem
                        proto_action_item = ProtoActionItem.query.filter_by(action_name=action_name).first()
                        if proto_action_item:
                            existing = ProtoPartDemand.query.filter_by(
                                proto_action_item_id=proto_action_item.id,
                                part_id=part.id
                            ).first()
                            if existing:
                                proto_part_demand_exists = True
                                break
        
        # Check if the specific proto action tool from debug data exists
        if 'Maintenance' in debug_data and 'proto_action_tools' in debug_data['Maintenance']:
            for tool_data in debug_data['Maintenance']['proto_action_tools']:
                tool_name = tool_data.get('tool_name')
                action_name = tool_data.get('proto_action_item_action_name')
                
                if tool_name and action_name:
                    tool = ToolDefinition.query.filter_by(tool_name=tool_name).first()
                    if tool:
                        from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem
                        proto_action_item = ProtoActionItem.query.filter_by(action_name=action_name).first()
                        if proto_action_item:
                            existing = ProtoActionTool.query.filter_by(
                                proto_action_item_id=proto_action_item.id,
                                tool_id=tool.id
                            ).first()
                            if existing:
                                proto_action_tool_exists = True
                                break
        
        # Only return True if BOTH proto part demands AND proto action tools exist
        # This ensures we insert if either is missing
        if proto_part_demand_exists and proto_action_tool_exists:
            return True
        
        # Fallback: if checks didn't find both, return False to allow insertion
        return False
    
    elif module_name == 'inventory':
        # Check for inventory records - specifically purchase orders
        from app.data.inventory.purchasing.purchase_order_header import PurchaseOrderHeader
        from app.data.core.major_location import MajorLocation
        
        # Check if purchase orders from debug data already exist
        if 'PurchaseOrders' in debug_data:
            for po_data in debug_data['PurchaseOrders']:
                vendor_name = po_data.get('vendor_name')
                major_location_name = po_data.get('major_location_name')
                
                if vendor_name:
                    # Check if a PO with this vendor and location already exists
                    query = PurchaseOrderHeader.query.filter_by(vendor_name=vendor_name)
                    
                    if major_location_name:
                        major_location = MajorLocation.query.filter_by(name=major_location_name).first()
                        if major_location:
                            query = query.filter_by(major_location_id=major_location.id)
                    
                    existing_po = query.first()
                    if existing_po:
                        return True
        
        return False
    
    return False


def _insert_module_debug_data(module_name, debug_data, system_user_id):
    """
    Insert debug data for a specific module
    
    Args:
        module_name (str): Name of module
        debug_data (dict): Debug data from JSON file
        system_user_id (int): System user ID for audit fields
    
    Raises:
        Exception: If insertion fails (fail-fast)
    """
    # Import and call module-specific insertion function
    if module_name == 'core':
        from app.debug.add_core_debugging_data import insert_core_debug_data
        insert_core_debug_data(debug_data, system_user_id)
    elif module_name == 'assets':
        from app.debug.add_assets_debugging_data import insert_assets_debug_data
        insert_assets_debug_data(debug_data, system_user_id)
    elif module_name == 'dispatching':
        from app.debug.add_dispatching_debugging_data import insert_dispatching_debug_data
        insert_dispatching_debug_data(debug_data, system_user_id)
    elif module_name == 'maintenance':
        from app.debug.add_maintenance_debugging_data import insert_maintenance_debug_data
        insert_maintenance_debug_data(debug_data, system_user_id)
    elif module_name == 'inventory':
        from app.debug.add_inventory_debugging_data import insert_inventory_debug_data
        insert_inventory_debug_data(debug_data, system_user_id)
    else:
        raise ValueError(f"Unknown module: {module_name}")

