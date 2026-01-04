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
        
        # Get initial row counts before insertion
        initial_counts = _get_table_row_counts()
        logger.info(f"Initial row counts - Parts: {initial_counts['parts']}, Tools: {initial_counts['tools']}")
        
        # Track expected counts from input data
        expected_parts = len(supply_data.get('parts', []))
        expected_tools = len(supply_data.get('tools', []))
        logger.info(f"Expected to process - Parts: {expected_parts}, Tools: {expected_tools}")
        
        # 1. Insert parts
        if 'parts' in supply_data:
            _insert_parts(supply_data['parts'], system_user_id)
        
        # 2. Insert tools
        if 'tools' in supply_data:
            _insert_tools(supply_data['tools'], system_user_id)
        
        # Note: Part demands are inserted as part of maintenance actions, not here
        # Standalone part demands in inventory.json are skipped
        
        # 3. Insert storerooms
        storerooms_data = debug_data.get('Storerooms', [])
        if storerooms_data:
            _insert_storerooms(storerooms_data, system_user_id)
        
        # 4. Insert purchase orders
        purchase_orders_data = debug_data.get('PurchaseOrders', [])
        if purchase_orders_data:
            _insert_purchase_orders(purchase_orders_data, system_user_id)
        
        db.session.commit()
        logger.info("Successfully inserted inventory debug data")
        
        # Verify row counts after insertion
        final_counts = _get_table_row_counts()
        _verify_row_counts(initial_counts, final_counts, expected_parts, expected_tools)
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to insert inventory debug data: {e}")
        raise


def _insert_parts(parts_data, system_user_id):
    """Insert or update parts using find_or_create_from_dict"""
    from app.data.core.supply.part_definition import PartDefinition
    
    for part_data in parts_data:
        # Make a copy to avoid modifying the original
        part_data = part_data.copy()
        
        # Map unit_cost to last_unit_cost if present
        if 'unit_cost' in part_data and 'last_unit_cost' not in part_data:
            part_data['last_unit_cost'] = part_data.pop('unit_cost')
        
        # Remove fields that shouldn't be in PartDefinition
        # These are inventory-specific fields that don't belong in the part definition
        inventory_fields = ['current_stock_level', 'minimum_stock_level', 'maximum_stock_level']
        for field in inventory_fields:
            part_data.pop(field, None)
        
        # Find or create the part
        part, created = PartDefinition.find_or_create_from_dict(
            part_data,
            user_id=system_user_id,
            lookup_fields=['part_number'],
            commit=False  # Don't commit yet, we'll update if needed
        )
        
        if created:
            logger.debug(f"Created new part: {part.part_number}")
        else:
            # Update existing part with new data, especially last_unit_cost
            updated = False
            for key, value in part_data.items():
                # Skip audit fields and fields that are None
                if key in ['created_by_id', 'updated_by_id', 'created_at', 'updated_at']:
                    continue
                if value is None:
                    continue
                
                # Update the field if it's different
                if hasattr(part, key) and getattr(part, key) != value:
                    setattr(part, key, value)
                    updated = True
                    logger.debug(f"Updated {key} for part {part.part_number}: {getattr(part, key)} -> {value}")
            
            if updated:
                part.updated_by_id = system_user_id
                logger.info(f"Updated existing part: {part.part_number}")
            else:
                logger.debug(f"Part {part.part_number} already up to date")


def _insert_tools(tools_data, system_user_id):
    """Insert tools using find_or_create_from_dict"""
    from app.data.core.supply.tool_definition import ToolDefinition
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
        
        ToolDefinition.find_or_create_from_dict(
            tool_data,
            user_id=system_user_id,
            lookup_fields=['tool_name']
        )
        logger.debug(f"Inserted tool: {tool_data.get('tool_name')}")


# Part demands are inserted as part of maintenance actions, not as standalone inventory items


def _insert_storerooms(storerooms_data, system_user_id):
    """Insert storerooms using StoreroomFactory"""
    from app.buisness.inventory.locations.storeroom_factory import StoreroomFactory
    from app.buisness.inventory.locations.storeroom_context import StoreroomContext
    from app.data.core.major_location import MajorLocation
    from app.data.inventory.inventory.storeroom import Storeroom
    from pathlib import Path
    
    # Get the debug data directory path
    debug_data_dir = Path(__file__).parent / 'data'
    
    for storeroom_data in storerooms_data:
        # Make a copy to avoid modifying the original
        storeroom_data = storeroom_data.copy()
        
        # Look up major_location_id from major_location_name
        major_location_name = storeroom_data.pop('major_location_name', None)
        if not major_location_name:
            logger.warning(f"Storeroom {storeroom_data.get('room_name')} missing major_location_name, skipping")
            continue
        
        major_location = MajorLocation.query.filter_by(name=major_location_name).first()
        if not major_location:
            logger.warning(f"Major location '{major_location_name}' not found for storeroom {storeroom_data.get('room_name')}, skipping")
            continue
        
        room_name = storeroom_data.get('room_name')
        address = storeroom_data.get('address', '')
        
        # Check if storeroom already exists
        existing_storeroom = Storeroom.query.filter_by(
            room_name=room_name,
            major_location_id=major_location.id
        ).first()
        
        if existing_storeroom:
            logger.debug(f"Storeroom {room_name} at {major_location.name} already exists (ID: {existing_storeroom.id})")
            storeroom_context = StoreroomContext(existing_storeroom.id)
        else:
            # Create storeroom based on type
            if room_name == 'main_storeroom' and major_location_name == 'LosAngelesOffice':
                # Use SVG layout for Los Angeles main storeroom
                svg_file_path = debug_data_dir / 'LosAngelesMainStoreroom.svg'
                if not svg_file_path.exists():
                    logger.warning(f"SVG file not found: {svg_file_path}, creating storeroom without SVG")
                    storeroom_context = StoreroomFactory.create_storeroom(
                        form_fields={
                            'room_name': room_name,
                            'major_location_id': major_location.id,
                            'address': address
                        },
                        user_id=system_user_id
                    )
                else:
                    # Read SVG file
                    with open(svg_file_path, 'r', encoding='utf-8') as f:
                        svg_content = f.read()
                    
                    # Create storeroom with SVG layout
                    storeroom_context = StoreroomFactory.create_storeroom_from_svg(
                        form_fields={
                            'room_name': room_name,
                            'major_location_id': major_location.id,
                            'address': address
                        },
                        svg_xml=svg_content,
                        user_id=system_user_id
                    )
                    logger.info(f"Created storeroom with SVG layout: {room_name} at {major_location.name} (ID: {storeroom_context.storeroom.id})")
                    
                    # Find location 1-1 and add bin layout
                    location_1_1 = None
                    for loc_ctx in storeroom_context.locations:
                        if loc_ctx.location.location == '1-1':
                            location_1_1 = loc_ctx
                            break
                    
                    if location_1_1:
                        bin_layout_file_path = debug_data_dir / 'bin_layout_example.svg'
                        if bin_layout_file_path.exists():
                            # Read bin layout SVG
                            with open(bin_layout_file_path, 'r', encoding='utf-8') as f:
                                bin_layout_svg = f.read()
                            
                            # Add bin layout to location 1-1
                            try:
                                StoreroomFactory.create_storeroom_location_from_svg(
                                    location_id=location_1_1.location_id,
                                    svg_xml=bin_layout_svg,
                                    user_id=system_user_id
                                )
                                logger.info(f"Added bin layout to location 1-1 in {room_name}")
                            except Exception as e:
                                logger.warning(f"Failed to add bin layout to location 1-1: {e}")
                        else:
                            logger.warning(f"Bin layout SVG file not found: {bin_layout_file_path}")
                    else:
                        logger.warning(f"Location 1-1 not found in storeroom {room_name}, skipping bin layout")
            else:
                # Use regular creation for other storerooms (e.g., San Diego annex)
                storeroom_context = StoreroomFactory.create_storeroom(
                    form_fields={
                        'room_name': room_name,
                        'major_location_id': major_location.id,
                        'address': address
                    },
                    user_id=system_user_id
                )
                logger.info(f"Created storeroom: {room_name} at {major_location.name} (ID: {storeroom_context.storeroom.id})")
        
        db.session.flush()


def _insert_purchase_orders(purchase_orders_data, system_user_id):
    """Insert purchase orders with their lines"""
    from app.buisness.inventory.ordering.purchase_order_factory import PurchaseOrderFactory
    from app.data.inventory.ordering.purchase_order_header import PurchaseOrderHeader
    from app.data.core.major_location import MajorLocation
    
    for po_data in purchase_orders_data:
        # Check if purchase order already exists (by vendor_name and major_location_name)
        vendor_name = po_data.get('vendor_name')
        major_location_name = po_data.get('major_location_name')
        
        if vendor_name:
            query = PurchaseOrderHeader.query.filter_by(vendor_name=vendor_name)
            
            if major_location_name:
                major_location = MajorLocation.query.filter_by(name=major_location_name).first()
                if major_location:
                    query = query.filter_by(major_location_id=major_location.id)
            
            existing_po = query.first()
            if existing_po:
                logger.debug(f"Purchase order for vendor '{vendor_name}' at location '{major_location_name}' already exists (PO: {existing_po.po_number}), skipping")
                continue
        
        # Create purchase order from dictionary
        # created_by_id is optional - factory will use system user if not provided
        po_context = PurchaseOrderFactory.create_from_dict(
            po_data=po_data,
            created_by_id=system_user_id,  # Will fall back to system user if None
            lookup_location_by_name=True
        )
        
        # Count lines that were successfully added
        lines_count = len([line for line in po_context.lines if line.status != 'Cancelled'])
        logger.info(f"Created purchase order: {po_context.header.po_number} with {lines_count} lines")


def _get_table_row_counts():
    """
    Get current row counts for parts and tools tables.
    
    Returns:
        dict: Dictionary with 'parts' and 'tools' counts
    """
    from app.data.core.supply.part_definition import PartDefinition
    from app.data.core.supply.tool_definition import ToolDefinition
    
    return {
        'parts': PartDefinition.query.count(),
        'tools': ToolDefinition.query.count()
    }


def _verify_row_counts(initial_counts, final_counts, expected_parts, expected_tools):
    """
    Verify that row counts are correct after insertion.
    
    Args:
        initial_counts (dict): Initial row counts before insertion
        final_counts (dict): Final row counts after insertion
        expected_parts (int): Number of parts expected to be processed
        expected_tools (int): Number of tools expected to be processed
    
    Raises:
        Exception: If row counts don't match expectations
    """
    parts_added = final_counts['parts'] - initial_counts['parts']
    tools_added = final_counts['tools'] - initial_counts['tools']
    
    logger.info("=" * 60)
    logger.info("ROW COUNT VERIFICATION")
    logger.info("=" * 60)
    logger.info(f"Parts table:")
    logger.info(f"  Initial count: {initial_counts['parts']}")
    logger.info(f"  Final count: {final_counts['parts']}")
    logger.info(f"  Rows added: {parts_added}")
    logger.info(f"  Expected to process: {expected_parts}")
    
    logger.info(f"Tools table:")
    logger.info(f"  Initial count: {initial_counts['tools']}")
    logger.info(f"  Final count: {final_counts['tools']}")
    logger.info(f"  Rows added: {tools_added}")
    logger.info(f"  Expected to process: {expected_tools}")
    
    # Verify that we didn't lose any rows (shouldn't happen, but good to check)
    if final_counts['parts'] < initial_counts['parts']:
        error_msg = f"Parts count decreased from {initial_counts['parts']} to {final_counts['parts']}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    if final_counts['tools'] < initial_counts['tools']:
        error_msg = f"Tools count decreased from {initial_counts['tools']} to {final_counts['tools']}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    # Note: We don't require exact matches because find_or_create_from_dict may skip duplicates
    # But we should verify that at least some rows were added if we expected to process data
    if expected_parts > 0 and parts_added == 0:
        logger.warning(f"Expected to process {expected_parts} parts but no new rows were added (may all be duplicates)")
    
    if expected_tools > 0 and tools_added == 0:
        logger.warning(f"Expected to process {expected_tools} tools but no new rows were added (may all be duplicates)")
    
    # Verify that we didn't add more rows than expected (shouldn't happen)
    if parts_added > expected_parts:
        error_msg = f"Added {parts_added} parts but only expected to process {expected_parts}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    if tools_added > expected_tools:
        error_msg = f"Added {tools_added} tools but only expected to process {expected_tools}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    logger.info("=" * 60)
    logger.info("Row count verification passed")
    logger.info("=" * 60)

