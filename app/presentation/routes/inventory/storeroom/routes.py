"""
Storeroom Designer Routes

Handles routes for storeroom, location, and bin management (Phase 1: Forms-based).
Phase 2 will add SVG upload and parsing functionality.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import login_required, current_user
from app import db
from app.logger import get_logger
from app.data.inventory.inventory.storeroom import Storeroom
from app.data.core.major_location import MajorLocation
from app.services.inventory.storerom_visual_tools import StoreroomVisualTools
from app.buisness.inventory.locations.storeroom_context import StoreroomContext
from app.buisness.inventory.locations.storeroom_factory import StoreroomFactory
from app.services.inventory.locations.location_service import LocationService

logger = get_logger("asset_management.routes.inventory.storeroom")

# Import inventory_bp from main module
from app.presentation.routes.inventory.main import inventory_bp

@inventory_bp.route('/storeroom/index')
@login_required
def storeroom_index():
    """List all storerooms with creation form"""
    logger.info(f"Storeroom index accessed by {current_user.username}")
    
    # Get all storerooms with location counts
    storerooms = Storeroom.query.filter_by(is_active=True).all()
    
    # Calculate bin counts for each storeroom
    storeroom_bin_counts = {}
    for storeroom in storerooms:
        total_bins = sum(len(location.bins) for location in storeroom.locations)
        storeroom_bin_counts[storeroom.id] = total_bins
    
    # Get major locations for dropdown
    major_locations = MajorLocation.query.filter_by(is_active=True).order_by(MajorLocation.name).all()
    
    return render_template('inventory/storeroom/index.html',
                         storerooms=storerooms,
                         storeroom_bin_counts=storeroom_bin_counts,
                         major_locations=major_locations)
    
@inventory_bp.route('/storeroom/create', methods=['GET', 'POST'])
@login_required
def storeroom_create():
    """Create new storeroom"""
    if request.method == 'GET':
    # Get major locations for dropdown
        major_locations = MajorLocation.query.filter_by(is_active=True).order_by(MajorLocation.name).all()
        return render_template('inventory/storeroom/create.html',
                             major_locations=major_locations)
    
    # POST - create storeroom
    room_name = request.form.get('room_name', '').strip()
    major_location_id = request.form.get('major_location_id', type=int)
    address = request.form.get('address', '').strip()
    svg_file = request.files.get('svg_file')
    
    if not room_name:
        flash('Storeroom name is required', 'error')
        return redirect(url_for('inventory.storeroom_create'))
    
    if not major_location_id:
        flash('Major location is required', 'error')
        return redirect(url_for('inventory.storeroom_create'))
    
    try:
        form_fields = {
            'room_name': room_name,
            'major_location_id': major_location_id,
            'address': address
        }
        
        # Check if SVG file is provided
        if svg_file and svg_file.filename:
            svg_content = svg_file.read().decode('utf-8')
            # Create storeroom with SVG
            storeroom_context = StoreroomFactory.create_storeroom_from_svg(
                form_fields=form_fields,
                svg_xml=svg_content,
                user_id=current_user.id
            )
            flash(f'Storeroom "{room_name}" created with {len(storeroom_context.locations)} locations from SVG', 'success')
        else:
            # Create storeroom without SVG
            storeroom_context = StoreroomFactory.create_storeroom(
                form_fields=form_fields,
                user_id=current_user.id
        )
        flash(f'Storeroom "{room_name}" created successfully', 'success')
    
        db.session.commit()
        logger.info(f"Storeroom '{room_name}' created by {current_user.username}")
    
        return redirect(url_for('inventory.storeroom_build', storeroom_id=storeroom_context.storeroom_id))
    except ValueError as e:
        flash(str(e), 'error')
    db.session.rollback()
    return redirect(url_for('inventory.storeroom_create'))
    
@inventory_bp.route('/storeroom/<int:storeroom_id>/build')
@login_required
def storeroom_build(storeroom_id):
    """Build/manage storeroom with locations and bins (interactive creation, HTMX-enabled)"""
    storeroom_context = StoreroomContext(storeroom_id)
    selected_location_id = request.args.get('location_id', type=int)
    selected_bin_id = request.args.get('bin_id', type=int)
    
    # Get all locations for this storeroom using shared service
    locations = StoreroomVisualTools.load_storeroom_locations(storeroom_id, load_bins=False)
    
    # Get selected location if provided
    selected_location = None
    if selected_location_id:
        selected_location = StoreroomVisualTools.get_selected_location(
        selected_location_id,
        storeroom_id
    )
    # Load bins if location is selected
    if selected_location and selected_location.bins:
        _ = selected_location.bins  # Trigger lazy load
    
    logger.info(f"Storeroom {storeroom_id} build page accessed by {current_user.username}")
    
    # Prepare template context
    template_context = {
    'storeroom': storeroom_context.storeroom,
    'locations': locations,
    'selected_location': selected_location,
    'location_id': selected_location_id,
    'bin_id': selected_bin_id
    }
    
    # Check if this is an HTMX request
    is_htmx = request.headers.get('HX-Request') == 'true'
    
    if is_htmx:
        # Return partial template for HTMX requests
        logger.debug(f"Returning HTMX partial for storeroom_build")
        return render_template('inventory/storeroom/build_partials.html', **template_context)
    else:
        # Return full page for normal requests
        return render_template('inventory/storeroom/build.html', **template_context)
    
@inventory_bp.route('/storeroom/<int:storeroom_id>/view-svg')
@login_required
def storeroom_view_svg(storeroom_id):
    """View processed SVG layout for storeroom"""
    storeroom = Storeroom.query.get_or_404(storeroom_id)
    
    if not storeroom.svg_content:
        flash('No processed SVG layout available for this storeroom', 'warning')
        return redirect(url_for('inventory.storeroom_build', storeroom_id=storeroom_id))
    
    logger.info(f"Storeroom {storeroom_id} processed SVG viewed by {current_user.username}")
    
    return Response(
    storeroom.svg_content,
    mimetype='image/svg+xml',
    headers={'Content-Disposition': f'inline; filename="storeroom_{storeroom_id}_layout.svg"'}
    )
    
@inventory_bp.route('/storeroom/<int:storeroom_id>/view-raw-svg')
@login_required
def storeroom_view_raw_svg(storeroom_id):
    """View raw (original) SVG layout for storeroom"""
    storeroom = Storeroom.query.get_or_404(storeroom_id)
    
    if not storeroom.raw_svg:
        flash('No raw SVG layout available for this storeroom', 'warning')
        return redirect(url_for('inventory.storeroom_build', storeroom_id=storeroom_id))
    
    logger.info(f"Storeroom {storeroom_id} raw SVG viewed by {current_user.username}")
    
    return Response(
    storeroom.raw_svg,
    mimetype='image/svg+xml',
    headers={'Content-Disposition': f'inline; filename="storeroom_{storeroom_id}_raw_layout.svg"'}
    )
    
@inventory_bp.route('/storeroom/<int:storeroom_id>/view')
@login_required
def storeroom_view(storeroom_id):
    """View storeroom summary (read-only)"""
    storeroom_context = StoreroomContext(storeroom_id)
    
    # Get all locations with their bins using shared service
    locations = StoreroomVisualTools.load_storeroom_locations(storeroom_id, load_bins=True)
    
    logger.info(f"Storeroom {storeroom_id} summary viewed by {current_user.username}")
    
    return render_template('inventory/storeroom/view.html',
                         storeroom=storeroom_context.storeroom,
                         locations=locations)
    
@inventory_bp.route('/storeroom/<int:storeroom_id>/edit', methods=['GET', 'POST'])
@login_required
def storeroom_edit(storeroom_id):
    """Edit storeroom details"""
    storeroom = Storeroom.query.get_or_404(storeroom_id)
    
    if request.method == 'GET':
        major_locations = MajorLocation.query.filter_by(is_active=True).order_by(MajorLocation.name).all()
        return render_template('inventory/storeroom/edit.html',
                             storeroom=storeroom,
                             major_locations=major_locations)
    
    # POST - update storeroom
    room_name = request.form.get('room_name', '').strip()
    major_location_id = request.form.get('major_location_id', type=int)
    address = request.form.get('address', '').strip()
    
    if not room_name:
        flash('Storeroom name is required', 'error')
        return redirect(url_for('inventory.storeroom_edit', storeroom_id=storeroom_id))
    
    if not major_location_id:
        flash('Major location is required', 'error')
        return redirect(url_for('inventory.storeroom_edit', storeroom_id=storeroom_id))
    
    # Check if changing major location with existing inventory
    if major_location_id != storeroom.major_location_id:
        inventory_count = storeroom.active_inventory.count()
        if inventory_count > 0:
            flash(f'Cannot change major location: {inventory_count} active inventory records exist', 'error')
            return redirect(url_for('inventory.storeroom_edit', storeroom_id=storeroom_id))
    
    storeroom.room_name = room_name
    storeroom.major_location_id = major_location_id
    storeroom.address = address
    storeroom.updated_by_id = current_user.id
    
    db.session.commit()
    
    logger.info(f"Storeroom {storeroom_id} updated by {current_user.username}")
    flash(f'Storeroom "{room_name}" updated successfully', 'success')
    
    return redirect(url_for('inventory.storeroom_view', storeroom_id=storeroom_id))
    
@inventory_bp.route('/storeroom/<int:storeroom_id>/delete', methods=['POST'])
@login_required
def storeroom_delete(storeroom_id):
    """Delete storeroom"""
    storeroom = Storeroom.query.get_or_404(storeroom_id)
    
    # Check for existing inventory
    inventory_count = storeroom.active_inventory.count()
    if inventory_count > 0:
        flash(f'Cannot delete storeroom: {inventory_count} active inventory records exist', 'error')
        return redirect(url_for('inventory.storeroom_build', storeroom_id=storeroom_id))
    
    storeroom_name = storeroom.room_name
    db.session.delete(storeroom)
    db.session.commit()
    
    logger.info(f"Storeroom {storeroom_id} deleted by {current_user.username}")
    flash(f'Storeroom "{storeroom_name}" deleted successfully', 'success')
    
    return redirect(url_for('inventory.storeroom_index'))
    
@inventory_bp.route('/storeroom/<int:storeroom_id>/add-location', methods=['POST'])
@login_required
def storeroom_add_location(storeroom_id):
    """Manually add location to storeroom"""
    storeroom_context = StoreroomContext(storeroom_id)
    
    location_name = request.form.get('location_name', '').strip()
    display_name = request.form.get('display_name', '').strip() or location_name
    
    if not location_name:
        flash('Location name is required', 'error')
        return redirect(url_for('inventory.storeroom_build', storeroom_id=storeroom_id))
    
    try:
        location_context = StoreroomFactory.create_storeroom_location(
        storeroom_id=storeroom_id,
        form_fields={
                'location': location_name,
                'display_name': display_name
        },
        user_id=current_user.id
        )
        db.session.commit()
    
        logger.info(f"Location '{display_name}' added to storeroom {storeroom_id} by {current_user.username}")
        flash(f'Location "{display_name}" added successfully', 'success')
    
        return redirect(url_for('inventory.storeroom_build', storeroom_id=storeroom_id, location_id=location_context.location_id))
    except ValueError as e:
        flash(str(e), 'error')
    db.session.rollback()
    return redirect(url_for('inventory.storeroom_build', storeroom_id=storeroom_id))
    
@inventory_bp.route('/storeroom/<int:storeroom_id>/upload-layout', methods=['POST'])
@login_required
def storeroom_upload_layout(storeroom_id):
    """Upload or replace storeroom SVG layout"""
    storeroom_context = StoreroomContext(storeroom_id)
    svg_file = request.files.get('svg_file')
    
    if not svg_file or not svg_file.filename:
        flash('SVG file is required', 'error')
        return redirect(url_for('inventory.storeroom_build', storeroom_id=storeroom_id))
    
    try:
        svg_content = svg_file.read().decode('utf-8')
    
        # Preprocess SVG - validates, cleans labels, adds JavaScript, and scales
        try:
            processed_svg, location_labels = StoreroomFactory.preprocess_svg(svg_content)
        except ValueError as e:
            flash(f'SVG preprocessing failed: {e}', 'error')
            return redirect(url_for('inventory.storeroom_build', storeroom_id=storeroom_id))
        
        # Store raw SVG
        storeroom_context.storeroom.raw_svg = svg_content
        db.session.flush()
        
        # Get existing location identifiers to avoid duplicates
        existing_locations = {loc.location: loc for loc in [lc.location for lc in storeroom_context.locations]}
        
        # Create new locations from cleaned labels
        new_location_contexts = []
        new_count = 0
        updated_count = 0
        
        for label in location_labels:
            if label not in existing_locations:
                # Create new location
                loc_ctx = storeroom_context.add_location(
                    location=label,
                    display_name=label,
                    svg_element_id=label,  # Temporarily set to label
                    user_id=current_user.id
                )
                new_location_contexts.append(loc_ctx)
                new_count += 1
            else:
                # Update existing location's SVG element ID
                existing_loc = existing_locations[label]
                existing_loc.svg_element_id = label  # Will be updated in postprocessing
                updated_count += 1
        
        db.session.flush()
        
        # Postprocess SVG to update element IDs to database IDs
        all_location_contexts = list(storeroom_context.locations)
        try:
            postprocessed_svg = StoreroomFactory.postprocess_svg(processed_svg, all_location_contexts)
            storeroom_context.storeroom.svg_content = postprocessed_svg
            
            # Update svg_element_ids to match new database IDs
            for loc_ctx in all_location_contexts:
                loc_ctx.location.svg_element_id = str(loc_ctx.location_id)
            
            db.session.flush()
        except Exception as e:
            logger.warning(f"SVG postprocessing failed: {e}")
            # Still save the processed (but not postprocessed) SVG
            storeroom_context.storeroom.svg_content = processed_svg
        
        db.session.commit()
        
        logger.info(f"Storeroom {storeroom_id} layout uploaded by {current_user.username}: {new_count} new locations, {updated_count} existing")
        flash(f'Storeroom layout uploaded: {new_count} new locations added, {updated_count} existing locations updated', 'success')
    except ValueError as e:
        flash(str(e), 'error')
        db.session.rollback()
    except Exception as e:
        logger.error(f"Failed to upload storeroom layout: {e}")
        flash(f'Failed to upload layout: {e}', 'error')
        db.session.rollback()
    
    return redirect(url_for('inventory.storeroom_build', storeroom_id=storeroom_id))
    
@inventory_bp.route('/storeroom/location/<int:location_id>/delete', methods=['POST'])
@login_required
def location_delete(location_id):
    """Delete location"""
    location = LocationService.get_location(location_id)
    if not location:
        flash('Location not found', 'error')
        return redirect(url_for('inventory.storeroom_index'))
    
    storeroom_id = location.storeroom_id
    location_name = location.display_name or location.location
    
    try:
        storeroom_context = StoreroomContext(storeroom_id)
        storeroom_context.remove_location(location_id)
        db.session.commit()
    
        logger.info(f"Location {location_id} deleted by {current_user.username}")
        flash(f'Location "{location_name}" deleted successfully', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    db.session.rollback()
    
    return redirect(url_for('inventory.storeroom_build', storeroom_id=storeroom_id))
    
@inventory_bp.route('/storeroom/location/<int:location_id>/add-bin', methods=['POST'])
@login_required
def location_add_bin(location_id):
    """Manually add bin to location"""
    location = LocationService.get_location(location_id)
    if not location:
        flash('Location not found', 'error')
        return redirect(url_for('inventory.storeroom_index'))
    
    bin_tag = request.form.get('bin_tag', '').strip()
    
    if not bin_tag:
        flash('Bin tag is required', 'error')
        return redirect(url_for('inventory.storeroom_build', 
                              storeroom_id=location.storeroom_id,
                              location_id=location_id))
    
    try:
        location_context = StoreroomContext(location.storeroom_id).get_location_context(location_id)
        if not location_context:
            raise ValueError(f"Location {location_id} not found in storeroom")
    
        location_context.add_bin(bin_tag=bin_tag, user_id=current_user.id)
        db.session.commit()
    
        logger.info(f"Bin '{bin_tag}' added to location {location_id} by {current_user.username}")
        flash(f'Bin "{bin_tag}" added successfully', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    db.session.rollback()
    
    return redirect(url_for('inventory.storeroom_build',
                          storeroom_id=location.storeroom_id,
                          location_id=location_id))
    
@inventory_bp.route('/storeroom/location/<int:location_id>/upload-bin-layout', methods=['POST'])
@login_required
def location_upload_bin_layout(location_id):
    """Upload bin layout SVG to location"""
    location = LocationService.get_location(location_id)
    if not location:
        flash('Location not found', 'error')
        return redirect(url_for('inventory.storeroom_index'))
    
    svg_file = request.files.get('svg_file')
    
    if not svg_file or not svg_file.filename:
        flash('SVG file is required', 'error')
        return redirect(url_for('inventory.storeroom_build',
                              storeroom_id=location.storeroom_id,
                              location_id=location_id))
    
    try:
        svg_content = svg_file.read().decode('utf-8')
    
    # Use factory to add bin layout and create bins
        location_context = StoreroomFactory.create_storeroom_location_from_svg(
        location_id=location_id,
        svg_xml=svg_content,
        user_id=current_user.id
        )
    
        db.session.commit()
    
        bin_count = len(location_context.bins)
        logger.info(f"Bin layout uploaded to location {location_id} by {current_user.username}: {bin_count} bins")
        flash(f'Bin layout uploaded: {bin_count} bins added', 'success')
    except ValueError as e:
        flash(str(e), 'error')
        db.session.rollback()
    except Exception as e:
        logger.error(f"Failed to upload bin layout: {e}")
        flash(f'Failed to upload bin layout: {e}', 'error')
        db.session.rollback()
    
    return redirect(url_for('inventory.storeroom_build',
                          storeroom_id=location.storeroom_id,
                          location_id=location_id))
    
@inventory_bp.route('/storeroom/location/bin/<int:bin_id>/delete', methods=['POST'])
@login_required
def bin_delete(bin_id):
    """Delete bin"""
    from app.services.inventory.locations.bin_service import BinService
    bin_obj = BinService.get_bin(bin_id)
    if not bin_obj:
        flash('Bin not found', 'error')
        return redirect(url_for('inventory.storeroom_index'))
    
    location_id = bin_obj.location_id
    storeroom_id = bin_obj.location.storeroom_id
    bin_tag = bin_obj.bin_tag
    
    try:
        storeroom_context = StoreroomContext(storeroom_id)
        location_context = storeroom_context.get_location_context(location_id)
        if not location_context:
            raise ValueError(f"Location {location_id} not found in storeroom")
    
        location_context.remove_bin(bin_id)
        db.session.commit()
    
        logger.info(f"Bin {bin_id} deleted by {current_user.username}")
        flash(f'Bin "{bin_tag}" deleted successfully', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    db.session.rollback()
    
    return redirect(url_for('inventory.storeroom_build',
                          storeroom_id=storeroom_id,
                          location_id=location_id))

