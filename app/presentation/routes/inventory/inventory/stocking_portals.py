"""
Stocking portal routes - Initial stocking and stocking GUI
"""
from flask import request, render_template, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.logger import get_logger
from app.services.inventory.locations.storeroom_layout_service import StoreroomLayoutService
from app.buisness.inventory.inventory.inventory_manager import InventoryManager
from app.buisness.inventory.locations.storeroom_context import StoreroomContext
from app.data.inventory.inventory.active_inventory import ActiveInventory
from app.data.inventory.inventory.storeroom import Storeroom
from app.data.inventory.locations.location import Location
from app.data.inventory.locations.bin import Bin
from app.data.core.major_location import MajorLocation
from app.data.core.supply.part_definition import PartDefinition
from sqlalchemy.orm import joinedload
from sqlalchemy import or_

logger = get_logger("asset_management.routes.inventory.stocking_portals")

# Import inventory_bp from main module
from app.presentation.routes.inventory.main import inventory_bp


# Initial Stocking Portal
@inventory_bp.route('/initial-stocking')
@login_required
def initial_stocking():
    """Initial stocking portal - select storeroom and unassigned inventory"""
    logger.info(f"Initial stocking portal accessed by {current_user.username}")
    
    # Get filter parameters
    storeroom_id = request.args.get('storeroom_id', type=int)
    major_location_id = request.args.get('major_location_id', type=int)
    part_search = request.args.get('part_search', '').strip() or None
    
    # Get all major locations for dropdown
    major_locations = MajorLocation.query.filter_by(is_active=True).order_by(MajorLocation.name.asc()).all()
    
    # Get all storerooms for dropdown (filtered by major location if provided)
    storerooms_query = Storeroom.query
    if major_location_id:
        storerooms_query = storerooms_query.filter_by(major_location_id=major_location_id)
    storerooms = storerooms_query.order_by(Storeroom.room_name.asc()).all()
    
    # Get unassigned inventory with filters
    unassigned_inventory = []
    if storeroom_id:
        query = ActiveInventory.query.filter_by(
            storeroom_id=storeroom_id,
            location_id=None,
            bin_id=None
        ).filter(
            ActiveInventory.quantity_on_hand > 0
        )
        
        # Apply part search filter if provided
        if part_search:
            query = query.join(PartDefinition).filter(
                or_(
                    PartDefinition.part_number.ilike(f'%{part_search}%'),
                    PartDefinition.part_name.ilike(f'%{part_search}%')
                )
            )
        
        unassigned_inventory = query.options(
            joinedload(ActiveInventory.part),
            joinedload(ActiveInventory.storeroom).joinedload(Storeroom.major_location)
        ).order_by(
            ActiveInventory.part_id.asc()
        ).all()
    
    return render_template('inventory/inventory/initial_stocking.html',
                         major_locations=major_locations,
                         storerooms=storerooms,
                         selected_storeroom_id=storeroom_id,
                         selected_major_location_id=major_location_id,
                         part_search=part_search,
                         unassigned_inventory=unassigned_inventory)
    

# Stocking GUI
@inventory_bp.route('/stocking-gui')
@login_required
def stocking_gui():
    """Stocking GUI - assign inventory to locations"""
    logger.info(f"Stocking GUI accessed by {current_user.username}")
    
    storeroom_id = request.args.get('storeroom_id', type=int)
    inventory_ids_str = request.args.get('inventory_ids', '')
    
    if not storeroom_id:
        flash('Storeroom ID is required', 'error')
        return redirect(url_for('inventory.initial_stocking'))
    
    # Parse inventory IDs
    inventory_ids = []
    if inventory_ids_str:
        try:
            inventory_ids = [int(id.strip()) for id in inventory_ids_str.split(',') if id.strip()]
        except ValueError:
            flash('Invalid inventory IDs', 'error')
            return redirect(url_for('inventory.initial_stocking', storeroom_id=storeroom_id))
    
    if not inventory_ids:
        flash('No inventory items selected', 'error')
        return redirect(url_for('inventory.initial_stocking', storeroom_id=storeroom_id))
    
    # Get storeroom and locations
    storeroom = Storeroom.query.get_or_404(storeroom_id)
    storeroom_context = StoreroomContext(storeroom_id)
    location_contexts = storeroom_context.locations
    locations = [loc_ctx.location for loc_ctx in location_contexts]
    
    # Load bins for each location
    for location in locations:
        location.bins  # Trigger lazy load
    
    # Get inventory items
    inventory_items = ActiveInventory.query.filter(
        ActiveInventory.id.in_(inventory_ids),
        ActiveInventory.storeroom_id == storeroom_id,
        ActiveInventory.location_id.is_(None),
        ActiveInventory.bin_id.is_(None)
    ).options(
        joinedload(ActiveInventory.part),
        joinedload(ActiveInventory.storeroom).joinedload(Storeroom.major_location)
    ).all()
    
    if not inventory_items:
        flash('No valid unassigned inventory items found', 'error')
        return redirect(url_for('inventory.initial_stocking', storeroom_id=storeroom_id))
    
    # Scale SVG for display if it exists
    scaled_svg_content = None
    if storeroom.svg_content:
        try:
            scaled_svg_content = StoreroomLayoutService.scale_svg_for_display(
                storeroom.svg_content,
                max_height=800
            )
        except Exception as e:
            logger.warning(f"Failed to scale SVG for display: {e}")
            scaled_svg_content = storeroom.svg_content  # Fallback to original
    
    # Create a temporary storeroom object with scaled SVG for template
    # We'll pass the scaled content separately to avoid modifying the original
    return render_template('inventory/inventory/stocking_gui.html',
                         storeroom=storeroom,
                         locations=locations,
                         inventory_items=inventory_items,
                         scaled_svg_content=scaled_svg_content)
    

# Submit Stocking Movement
@inventory_bp.route('/stocking-gui/submit', methods=['POST'])
@login_required
def submit_stocking_movement():
    """Submit stocking movement - assign inventory to location/bin"""
    try:
        data = request.get_json(silent=True) or {}
        
        logger.debug(f"Submit stocking movement request: {data}")

        inventory_ids = data.get('inventory_ids', [])
        location_id = data.get('location_id')
        if location_id:
            try:
                location_id = int(location_id)
            except (ValueError, TypeError):
                logger.error(f"Invalid location_id: {location_id}")
                return jsonify({'success': False, 'error': 'Invalid location ID'}), 400
        else:
            logger.warning("No location_id provided in request")
            return jsonify({'success': False, 'error': 'Location is required'}), 400

        bin_id = data.get('bin_id')
        if bin_id:
            try:
                bin_id = int(bin_id)
            except (ValueError, TypeError):
                logger.warning(f"Invalid bin_id: {bin_id}, setting to None")
                bin_id = None
        else:
            bin_id = None

        if not inventory_ids:
            logger.warning("No inventory_ids provided in request")
            return jsonify({'success': False, 'error': 'No inventory items selected'}), 400
        
        logger.debug(f"Processing: inventory_ids={inventory_ids}, location_id={location_id}, bin_id={bin_id}")

        # Get location to verify storeroom
        location = Location.query.get(location_id)
        if not location:
            logger.error(f"Location {location_id} not found")
            return jsonify({'success': False, 'error': f'Location {location_id} not found'}), 400
        storeroom_id = location.storeroom_id
        logger.debug(f"Location {location_id} belongs to storeroom {storeroom_id}")

        # Get storeroom for major_location_id
        storeroom = Storeroom.query.get(storeroom_id)
        if not storeroom:
            logger.error(f"Storeroom {storeroom_id} not found")
            return jsonify({'success': False, 'error': f'Storeroom {storeroom_id} not found'}), 400
        major_location_id = storeroom.major_location_id

        # Verify bin belongs to location if provided
        if bin_id:
            bin_obj = Bin.query.get(bin_id)
            if not bin_obj:
                logger.error(f"Bin {bin_id} not found")
                return jsonify({'success': False, 'error': f'Bin {bin_id} not found'}), 400
            if bin_obj.location_id != location_id:
                logger.error(f"Bin {bin_id} (location_id={bin_obj.location_id}) does not belong to location {location_id}")
                return jsonify({'success': False, 'error': 'Bin does not belong to selected location'}), 400

        # Get inventory items (allow items from any storeroom - we'll handle cross-storeroom moves)
        inventory_items = ActiveInventory.query.filter(
            ActiveInventory.id.in_(inventory_ids),
            ActiveInventory.location_id.is_(None),
            ActiveInventory.bin_id.is_(None)
        ).options(
            joinedload(ActiveInventory.storeroom).joinedload(Storeroom.major_location)
        ).all()
        
        logger.debug(f"Found {len(inventory_items)} unassigned inventory items out of {len(inventory_ids)} requested")

        if not inventory_items:
            logger.warning(f"No valid unassigned inventory items found for ids {inventory_ids}")
            return jsonify({'success': False, 'error': 'No valid unassigned inventory items found. Items may already be assigned.'}), 400

        # Create movements for each inventory item
        inventory_manager = InventoryManager()
        movements_created = 0

        for inv in inventory_items:
            from_storeroom_id = inv.storeroom_id
            from_major_location_id = inv.storeroom.major_location_id if inv.storeroom else None
            
            if not from_major_location_id:
                logger.error(f"Inventory item {inv.id} has no major location")
                continue
            
            # Check if this is a cross-storeroom move
            if from_storeroom_id != storeroom_id:
                logger.info(f"Cross-storeroom move: inventory {inv.id} from storeroom {from_storeroom_id} to {storeroom_id}")
                # Use transfer_cross_storeroom for cross-storeroom moves
                inventory_manager.transfer_cross_storeroom(
                    part_id=inv.part_id,
                    quantity_to_move=inv.quantity_on_hand,
                    from_storeroom_id=from_storeroom_id,
                    from_major_location_id=from_major_location_id,
                    from_location_id=None,
                    from_bin_id=None,
                    to_storeroom_id=storeroom_id,
                    to_major_location_id=major_location_id,
                    to_location_id=location_id,
                    to_bin_id=bin_id
                )
            else:
                # Same storeroom - use assign_unassigned_to_bin
                inventory_manager.assign_unassigned_to_bin(
                    part_id=inv.part_id,
                    storeroom_id=storeroom_id,
                    major_location_id=major_location_id,
                    quantity_to_move=inv.quantity_on_hand,
                    to_location_id=location_id,
                    to_bin_id=bin_id
                )
            movements_created += 1

        db.session.commit()

        logger.info(
            f"Stocking movement created by {current_user.username}: "
            f"{movements_created} items assigned to location {location_id}"
        )

        return jsonify({
            'success': True,
            'message': f'Successfully assigned {movements_created} item(s)',
            'storeroom_id': storeroom_id
        }), 200

    except ValueError as e:
        db.session.rollback()
        logger.error(f"Error creating stocking movement: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error creating stocking movement: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'An unexpected error occurred'}), 500
