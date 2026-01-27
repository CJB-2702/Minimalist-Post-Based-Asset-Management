"""
Move Inventory GUI Routes

Generic move-parts GUI with split-screen interface: form on left (1/3), visual selector on right (2/3).
"""
from flask import render_template, request, flash, redirect, url_for, Response
from flask_login import login_required, current_user
from app import db
from app.logger import get_logger
from app.services.inventory.storerom_visual_tools import StoreroomVisualTools
from app.services.inventory.locations.storeroom_layout_service import StoreroomLayoutService
from app.buisness.inventory.inventory.inventory_manager import InventoryManager
from app.buisness.inventory.locations.storeroom_context import StoreroomContext
from app.buisness.inventory.locations.location_context import LocationContext
from app.data.inventory.inventory.active_inventory import ActiveInventory
from app.data.inventory.inventory.storeroom import Storeroom
from app.data.core.major_location import MajorLocation
from app.data.inventory.locations.location import Location
from app.data.inventory.locations.bin import Bin
from sqlalchemy.orm import joinedload

# Import inventory_bp from main module
from app.presentation.routes.inventory.main import inventory_bp

logger = get_logger("asset_management.routes.inventory.inventory.move_gui")


@inventory_bp.route('/move-inventory-gui')
@login_required
def move_inventory_gui():
    """Move Inventory GUI - visual destination selector (HTMX-enabled for scroll preservation)"""
    logger.info(f"Move Inventory GUI accessed by {current_user.username}")
    
    initial_active_inventory_id = request.args.get('initial_active_inventory_id', type=int)
    major_location_id = request.args.get('major_location_id', type=int)
    storeroom_id = request.args.get('storeroom', type=int) or request.args.get('storeroom_id', type=int)
    location_id = request.args.get('location', type=int) or request.args.get('location_id', type=int)
    bin_id = request.args.get('bin', type=int) or request.args.get('bin_id', type=int)
    
    if not initial_active_inventory_id:
        flash('Active inventory ID is required', 'error')
        return redirect(url_for('inventory.active_inventory_view'))
    
    # Get active inventory record with relationships
    active_inventory = ActiveInventory.query.options(
        joinedload(ActiveInventory.part),
        joinedload(ActiveInventory.storeroom).joinedload(Storeroom.major_location),
        joinedload(ActiveInventory.location),
        joinedload(ActiveInventory.bin)
    ).get_or_404(initial_active_inventory_id)
    
    # Default to current inventory's location if parameters are not provided in URL
    if not major_location_id and active_inventory.storeroom and active_inventory.storeroom.major_location_id:
        major_location_id = active_inventory.storeroom.major_location_id
    if not storeroom_id and active_inventory.storeroom_id:
        storeroom_id = active_inventory.storeroom_id
    if not location_id and active_inventory.location_id:
        location_id = active_inventory.location_id
    if not bin_id and active_inventory.bin_id:
        bin_id = active_inventory.bin_id
    
    # Get all major locations for dropdown
    major_locations = MajorLocation.query.filter_by(is_active=True).order_by(MajorLocation.name).all()
    
    # Get storerooms based on major_location_id filter
    storerooms_query = Storeroom.query.options(joinedload(Storeroom.major_location)).filter_by(is_active=True)
    if major_location_id:
        storerooms_query = storerooms_query.filter_by(major_location_id=major_location_id)
    storerooms = storerooms_query.order_by(Storeroom.room_name).all()
    
    # Calculate available quantity
    available_quantity = (active_inventory.quantity_on_hand or 0.0) - (active_inventory.quantity_allocated or 0.0)
    
    # Load location viewer data if storeroom_id is provided
    selected_storeroom, locations, scaled_svg_content = StoreroomVisualTools.prepare_location_viewer_data(
        storeroom_id,
        max_svg_height=800
    )
    
    # Load bin viewer data if location_id is provided
    selected_location, bins_list = StoreroomVisualTools.prepare_bin_viewer_data(
        location_id,
        storeroom_id
    )
    
    # Prepare template context
    template_context = {
        'active_inventory': active_inventory,
        'available_quantity': available_quantity,
        'major_locations': major_locations,
        'storerooms': storerooms,
        'major_location_id': major_location_id,
        'storeroom_id': storeroom_id,
        'location_id': location_id,
        'bin_id': bin_id,
        'selected_storeroom': selected_storeroom,
        'locations': locations,
        'scaled_svg_content': scaled_svg_content,
        'selected_location': selected_location,
        'bins_list': bins_list
    }
    
    # Check if this is an HTMX request
    is_htmx = request.headers.get('HX-Request') == 'true'
    
    if is_htmx:
        # Return partial template with out-of-band swaps for HTMX
        logger.debug(f"Returning HTMX partial for move_inventory_gui")
        return render_template('inventory/inventory/move_inventory_gui_partials.html', **template_context)
    else:
        # Return full page for normal requests
        return render_template('inventory/inventory/move_inventory_gui.html', **template_context)

@inventory_bp.route('/move-inventory-gui/submit', methods=['POST'])
@login_required
def submit_move_inventory_gui():
    """Submit move inventory from GUI (handles form POST)"""
    try:
        # Get data from form POST
        active_inventory_id = request.form.get('active_inventory_id', type=int)
        if not active_inventory_id:
                flash('Active inventory ID is required', 'error')
                return redirect(url_for('inventory.active_inventory_view'))
        
        source_inv = ActiveInventory.query.get_or_404(active_inventory_id)
        
        # Get destination details
        quantity = request.form.get('quantity', type=float)
        if not quantity or quantity <= 0:
                flash('Quantity must be greater than 0', 'error')
                return redirect(url_for('inventory.move_inventory_gui', initial_active_inventory_id=active_inventory_id))
        
        to_major_location_id = request.form.get('to_major_location_id', type=int)
        to_storeroom_id = request.form.get('to_storeroom_id', type=int)
        to_location_id = request.form.get('to_location_id', type=int)  # Can be None
        to_bin_id = request.form.get('to_bin_id', type=int)  # Can be None
        
        # Validate required fields
        if not to_major_location_id or not to_storeroom_id or not to_location_id:
                flash('Major location, storeroom, and location are required', 'error')
                return redirect(url_for('inventory.move_inventory_gui', initial_active_inventory_id=active_inventory_id))
        
        # Get location name if location_id provided
        to_location_name = None
        if to_location_id:
                location = Location.query.get(to_location_id)
                if not location:
                    flash('Selected location not found', 'error')
                    return redirect(url_for('inventory.move_inventory_gui', initial_active_inventory_id=active_inventory_id))
                to_location_name = location.location
        
        # Get bin tag if bin_id provided
        to_bin_tag = None
        if to_bin_id:
                bin_obj = Bin.query.get(to_bin_id)
                if not bin_obj:
                    flash('Selected bin not found', 'error')
                    return redirect(url_for('inventory.move_inventory_gui', initial_active_inventory_id=active_inventory_id))
                # Validate bin belongs to location if both provided
                if to_location_id and bin_obj.location_id != to_location_id:
                    flash('Bin does not belong to selected location', 'error')
                    return redirect(url_for('inventory.move_inventory_gui', initial_active_inventory_id=active_inventory_id))
                to_bin_tag = bin_obj.bin_tag
        
        # Validate bin requires location
        if to_bin_tag and not to_location_name:
                flash('Bin requires a location', 'error')
                return redirect(url_for('inventory.move_inventory_gui', initial_active_inventory_id=active_inventory_id))
        
        # Check sufficient quantity
        if (source_inv.quantity_on_hand or 0.0) < quantity:
                flash(f'Not enough quantity. Available: {source_inv.quantity_on_hand or 0.0}', 'error')
                return redirect(url_for('inventory.move_inventory_gui', initial_active_inventory_id=active_inventory_id))
        
        # Get source details
        from_storeroom = source_inv.storeroom
        if not from_storeroom:
                flash('Source storeroom not found', 'error')
                return redirect(url_for('inventory.move_inventory_gui', initial_active_inventory_id=active_inventory_id))
        
        from_major_location_id = from_storeroom.major_location_id
        from_storeroom_id = source_inv.storeroom_id
        from_location_id = source_inv.location_id
        from_bin_id = source_inv.bin_id
        
        # Get destination storeroom
        to_storeroom = Storeroom.query.get(to_storeroom_id)
        if not to_storeroom:
                flash('Destination storeroom not found', 'error')
                return redirect(url_for('inventory.move_inventory_gui', initial_active_inventory_id=active_inventory_id))
        
        if to_storeroom.major_location_id != to_major_location_id:
                flash('Storeroom does not belong to the specified major location', 'error')
                return redirect(url_for('inventory.move_inventory_gui', initial_active_inventory_id=active_inventory_id))
        
        # Validate: prevent transfer to self (same location)
        if (from_storeroom_id == to_storeroom_id and 
                from_location_id == to_location_id and 
                from_bin_id == to_bin_id):
                flash('Cannot transfer inventory to the same location', 'error')
                return redirect(url_for('inventory.move_inventory_gui', initial_active_inventory_id=active_inventory_id))
        
        # Perform the transfer using existing business logic
        inventory_manager = InventoryManager()
        inventory_manager.transfer_cross_storeroom(
                part_id=source_inv.part_id,
                quantity_to_move=quantity,
                from_storeroom_id=from_storeroom_id,
                from_major_location_id=from_major_location_id,
                from_location_id=from_location_id,
                from_bin_id=from_bin_id,
                to_storeroom_id=to_storeroom_id,
                to_major_location_id=to_major_location_id,
                to_location_id=to_location_id,
                to_bin_id=to_bin_id,
        )
        
        db.session.commit()
        
        logger.info(f"Inventory moved by {current_user.username} via GUI: {quantity} units of part {source_inv.part_id} from storeroom {from_storeroom_id} to storeroom {to_storeroom_id}")
        
        flash(f'Successfully moved {quantity} units', 'success')
        return redirect(url_for('inventory.active_inventory_view'))
        
    except ValueError as e:
        db.session.rollback()
        logger.error(f"Error moving inventory via GUI: {e}")
        flash(str(e), 'error')
        active_inv_id = request.form.get('active_inventory_id', type=int)
        if active_inv_id:
                return redirect(url_for('inventory.move_inventory_gui', initial_active_inventory_id=active_inv_id))
        return redirect(url_for('inventory.active_inventory_view'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error moving inventory via GUI: {e}", exc_info=True)
        flash('An unexpected error occurred', 'error')
        active_inv_id = request.form.get('active_inventory_id', type=int)
        if active_inv_id:
                return redirect(url_for('inventory.move_inventory_gui', initial_active_inventory_id=active_inv_id))
        return redirect(url_for('inventory.active_inventory_view'))

@inventory_bp.route('/move-inventory-gui/storeroom-preview/<int:storeroom_id>')
@login_required
def storeroom_preview_svg(storeroom_id):
    """Get scaled SVG preview for storeroom card (100x100)"""
    storeroom = Storeroom.query.get_or_404(storeroom_id)
    
    # Use svg_content if available, otherwise use raw_svg, otherwise return placeholder
    svg_content = storeroom.svg_content or storeroom.raw_svg
    
    if not svg_content:
        # Return a simple placeholder SVG
        placeholder_svg = '''<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
                <rect width="100" height="100" fill="#f8f9fa" stroke="#dee2e6"/>
                <text x="50" y="50" text-anchor="middle" dominant-baseline="middle" font-family="Arial" font-size="12" fill="#6c757d">No Layout</text>
        </svg>'''
        return Response(placeholder_svg, mimetype='image/svg+xml')
    
    # Scale SVG to 100x100 for card preview
    try:
        scaled_svg = StoreroomLayoutService.scale_svg_for_display(
                svg_content,
                max_height=100,
                max_width=100
        )
        return Response(scaled_svg, mimetype='image/svg+xml', headers={'Content-Disposition': f'inline; filename="storeroom_{storeroom_id}_preview.svg"'})
    except Exception as e:
        logger.warning(f"Failed to scale SVG for storeroom {storeroom_id}: {e}")
        # Return original SVG if scaling fails
        return Response(svg_content, mimetype='image/svg+xml')

