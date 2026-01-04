"""
Inventory management routes - Active inventory and movement linking
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.logger import get_logger
from app.services.inventory.inventory.active_inventory_service import ActiveInventoryService
from app.services.inventory.inventory.inventory_movement_service import InventoryMovementService
from app.services.inventory.locations.storeroom_layout_service import StoreroomLayoutService
from app.buisness.inventory.stock.inventory_manager import InventoryManager
from app.buisness.inventory.locations.storeroom_context import StoreroomContext
from app.buisness.inventory.locations.location_context import LocationContext
from app.data.inventory.inventory.active_inventory import ActiveInventory
from app.data.inventory.inventory.storeroom import Storeroom
from app.data.inventory.locations.location import Location
from app.data.inventory.locations.bin import Bin
from sqlalchemy.orm import joinedload
from datetime import datetime

logger = get_logger("asset_management.routes.inventory.inventory")


def register_inventory_routes(inventory_bp):
    """Register all inventory management routes to the inventory blueprint"""
    
    # Part Issues List
    @inventory_bp.route('/part-issues')
    @login_required
    def part_issues_list():
        """List all part issues with filters"""
        logger.info(f"Part issues list accessed by {current_user.username}")
        
        from app.data.inventory.inventory.part_issue import PartIssue
        from app.data.core.supply.part_definition import PartDefinition
        from app.data.core.user_info.user import User
        from app.data.core.asset_info.asset import Asset
        
        # Get filter parameters
        page = request.args.get('page', 1, type=int)
        issue_type = request.args.get('issue_type', '').strip() or None
        user_id = request.args.get('user_id', type=int)
        asset_id = request.args.get('asset_id', type=int)
        part_id = request.args.get('part_id', type=int)
        date_from_str = request.args.get('date_from', '').strip() or None
        date_to_str = request.args.get('date_to', '').strip() or None
        
        # Build query
        query = PartIssue.query.options(
            joinedload(PartIssue.inventory_movement)
        )
        
        if issue_type:
            query = query.filter_by(issue_type=issue_type)
        if user_id:
            query = query.filter_by(issued_to_user_id=user_id)
        if asset_id:
            query = query.filter_by(asset_id=asset_id)
        if part_id:
            query = query.filter_by(part_id=part_id)
        
        # Date filters
        if date_from_str:
            try:
                date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
                query = query.filter(PartIssue.issue_date >= date_from)
            except ValueError:
                pass
        if date_to_str:
            try:
                date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
                query = query.filter(PartIssue.issue_date <= date_to)
            except ValueError:
                pass
        
        # Order by most recent first
        query = query.order_by(PartIssue.issue_date.desc())
        
        # Paginate
        pagination = query.paginate(page=page, per_page=50, error_out=False)
        
        # Get filter options
        users = User.query.order_by(User.username).all()
        assets = Asset.query.order_by(Asset.name).all()
        
        return render_template('inventory/inventory/part_issues_list.html',
                             pagination=pagination,
                             users=users,
                             assets=assets,
                             current_filters={
                                 'issue_type': issue_type or '',
                                 'user_id': user_id,
                                 'asset_id': asset_id,
                                 'part_id': part_id,
                                 'date_from': date_from_str or '',
                                 'date_to': date_to_str or ''
                             })
    
    # Part Issue Detail View
    @inventory_bp.route('/part-issues/<int:id>/view')
    @login_required
    def part_issue_view(id):
        """View a single part issue"""
        logger.info(f"Part issue {id} viewed by {current_user.username}")
        
        from app.data.inventory.inventory.part_issue import PartIssue
        from app.data.core.supply.part_definition import PartDefinition
        from app.data.core.user_info.user import User
        from app.data.core.asset_info.asset import Asset
        
        issue = PartIssue.query.options(
            joinedload(PartIssue.inventory_movement)
        ).get_or_404(id)
        
        # Get related objects
        part = PartDefinition.query.get(issue.part_id) if issue.part_id else None
        issued_to_user = User.query.get(issue.issued_to_user_id) if issue.issued_to_user_id else None
        issued_by = User.query.get(issue.issued_by_id) if issue.issued_by_id else None
        asset = Asset.query.get(issue.asset_id) if issue.asset_id else None
        
        return render_template('inventory/inventory/part_issue_detail.html',
                             issue=issue,
                             part=part,
                             issued_to_user=issued_to_user,
                             issued_by=issued_by,
                             asset=asset)
    
    # Part Issue Edit
    @inventory_bp.route('/part-issues/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    def part_issue_edit(id):
        """Edit a part issue"""
        from app.data.inventory.inventory.part_issue import PartIssue
        from app.data.core.user_info.user import User
        from app.data.core.asset_info.asset import Asset
        
        issue = PartIssue.query.get_or_404(id)
        
        if request.method == 'POST':
            try:
                # Update editable fields
                issue.issued_to_user_id = request.form.get('issued_to_user_id', type=int) or None
                issue.asset_id = request.form.get('asset_id', type=int) or None
                issue.issue_reason = request.form.get('issue_reason', '').strip() or None
                issue.issue_notes = request.form.get('issue_notes', '').strip() or None
                issue.updated_by_id = current_user.id
                issue.updated_at = datetime.utcnow()
                
                db.session.commit()
                
                flash('Part issue updated successfully', 'success')
                logger.info(f"Part issue {id} updated by {current_user.username}")
                
                return redirect(url_for('inventory.part_issue_view', id=id))
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error updating part issue {id}: {e}", exc_info=True)
                flash(f'Error updating part issue: {str(e)}', 'error')
        
        # GET request - show form
        users = User.query.order_by(User.username).all()
        assets = Asset.query.order_by(Asset.name).all()
        
        return render_template('inventory/inventory/part_issue_edit.html',
                             issue=issue,
                             users=users,
                             assets=assets)
    
    # Issue Parts Portal
    @inventory_bp.route('/issue-parts')
    @login_required
    def issue_parts():
        """Issue parts portal - select inventory and issue to users/assets"""
        logger.info(f"Issue parts portal accessed by {current_user.username}")
        
        # Get filter parameters (same as active inventory)
        page = request.args.get('page', 1, type=int)
        part_id = request.args.get('part_id', type=int)
        part_number = request.args.get('part_number', '').strip() or None
        part_name = request.args.get('part_name', '').strip() or None
        location_id = request.args.get('location_id', type=int)
        storeroom_id = request.args.get('storeroom_id', type=int)
        search = request.args.get('search', '').strip() or None
        
        # Get paginated data - only show items with available stock
        pagination, form_options = ActiveInventoryService.get_list_data(
            page=page,
            per_page=50,
            part_id=part_id,
            part_number=part_number,
            part_name=part_name,
            location_id=location_id,
            storeroom_id=storeroom_id,
            has_stock_only=True,  # Only show items with stock
            search=search
        )
        
        # Get all users for the issue form
        from app.data.core.user_info.user import User
        users = User.query.order_by(User.username).all()
        
        # Get all assets for the issue form
        from app.data.core.asset_info.asset import Asset
        assets = Asset.query.order_by(Asset.name).all()
        
        return render_template('inventory/inventory/issue_parts.html',
                             pagination=pagination,
                             locations=form_options['locations'],
                             storerooms=form_options['storerooms'],
                             users=users,
                             assets=assets,
                             current_filters={
                                 'part_id': part_id,
                                 'part_number': part_number or '',
                                 'part_name': part_name or '',
                                 'location_id': location_id,
                                 'storeroom_id': storeroom_id,
                                 'search': search or ''
                             })
    
    # Active Inventory View
    @inventory_bp.route('/active-inventory')
    @login_required
    def active_inventory_view():
        """View and filter active inventory"""
        logger.info(f"Active inventory view accessed by {current_user.username}")
        
        # Get filter parameters
        page = request.args.get('page', 1, type=int)
        part_id = request.args.get('part_id', type=int)
        part_number = request.args.get('part_number', '').strip() or None
        part_name = request.args.get('part_name', '').strip() or None
        location_id = request.args.get('location_id', type=int)
        storeroom_id = request.args.get('storeroom_id', type=int)
        low_stock_only = request.args.get('low_stock_only', type=bool)
        out_of_stock_only = request.args.get('out_of_stock_only', type=bool)
        has_stock_only = request.args.get('has_stock_only', type=bool)
        search = request.args.get('search', '').strip() or None
        
        # Get paginated data
        pagination, form_options = ActiveInventoryService.get_list_data(
            page=page,
            per_page=50,
            part_id=part_id,
            part_number=part_number,
            part_name=part_name,
            location_id=location_id,
            storeroom_id=storeroom_id,
            low_stock_only=bool(low_stock_only),
            out_of_stock_only=bool(out_of_stock_only),
            has_stock_only=bool(has_stock_only),
            search=search
        )
        
        return render_template('inventory/inventory/active_inventory_view.html',
                             pagination=pagination,
                             locations=form_options['locations'],
                             storerooms=form_options['storerooms'],
                             current_filters={
                                 'part_id': part_id,
                                 'part_number': part_number or '',
                                 'part_name': part_name or '',
                                 'location_id': location_id,
                                 'storeroom_id': storeroom_id,
                                 'low_stock_only': low_stock_only,
                                 'out_of_stock_only': out_of_stock_only,
                                 'has_stock_only': has_stock_only,
                                 'search': search or ''
                             })
    
    # Inventory Movements View
    @inventory_bp.route('/movements')
    @login_required
    def movements_view():
        """View and filter inventory movements"""
        logger.info(f"Movements view accessed by {current_user.username}")
        
        # Get filter parameters
        page = request.args.get('page', 1, type=int)
        part_id = request.args.get('part_id', type=int)
        part_number = request.args.get('part_number', '').strip() or None
        part_name = request.args.get('part_name', '').strip() or None
        location_id = request.args.get('location_id', type=int)
        storeroom_id = request.args.get('storeroom_id', type=int)
        movement_type = request.args.get('movement_type', '').strip() or None
        date_from_str = request.args.get('date_from', '').strip() or None
        date_to_str = request.args.get('date_to', '').strip() or None
        search = request.args.get('search', '').strip() or None
        
        # Parse dates
        date_from = None
        date_to = None
        if date_from_str:
            try:
                date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
            except ValueError:
                pass
        if date_to_str:
            try:
                date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
            except ValueError:
                pass
        
        # Get paginated data
        pagination, form_options = InventoryMovementService.get_list_data(
            page=page,
            per_page=50,
            part_id=part_id,
            part_number=part_number,
            part_name=part_name,
            location_id=location_id,
            storeroom_id=storeroom_id,
            movement_type=movement_type,
            date_from=date_from,
            date_to=date_to,
            search=search
        )
        
        return render_template('inventory/inventory/movements_view.html',
                             pagination=pagination,
                             movement_types=form_options['movement_types'],
                             locations=form_options['locations'],
                             storerooms=form_options['storerooms'],
                             current_filters={
                                 'part_id': part_id,
                                 'part_number': part_number or '',
                                 'part_name': part_name or '',
                                 'location_id': location_id,
                                 'storeroom_id': storeroom_id,
                                 'movement_type': movement_type or '',
                                 'date_from': date_from_str or '',
                                 'date_to': date_to_str or '',
                                 'search': search or ''
                             })
    
    # Move Inventory
    @inventory_bp.route('/active-inventory/move', methods=['POST'])
    @login_required
    def move_inventory():
        """Move inventory from one location to another"""
        try:
            data = request.get_json()
            
            # Get source inventory
            active_inventory_id = data.get('active_inventory_id')
            if not active_inventory_id:
                return jsonify({'success': False, 'error': 'Active inventory ID is required'}), 400
            
            source_inv = ActiveInventory.query.get_or_404(active_inventory_id)
            
            # Get destination details
            quantity = float(data.get('quantity', 0))
            if quantity <= 0:
                return jsonify({'success': False, 'error': 'Quantity must be greater than 0'}), 400
            
            to_major_location_id = data.get('to_major_location_id')
            to_storeroom_id = data.get('to_storeroom_id')
            to_location_name = data.get('to_location', '').strip() if data.get('to_location') else None
            to_bin_tag = data.get('to_bin', '').strip() if data.get('to_bin') else None
            
            # Validate required fields
            if not to_major_location_id or not to_storeroom_id:
                return jsonify({'success': False, 'error': 'Major location and storeroom are required'}), 400
            
            # Validate bin requires location
            if to_bin_tag and not to_location_name:
                return jsonify({'success': False, 'error': 'Bin requires a location'}), 400
            
            # Check sufficient quantity
            if (source_inv.quantity_on_hand or 0.0) < quantity:
                return jsonify({'success': False, 'error': f'Not enough quantity. Available: {source_inv.quantity_on_hand or 0.0}'}), 400
            
            # Get source details
            from_storeroom = source_inv.storeroom
            if not from_storeroom:
                return jsonify({'success': False, 'error': 'Source storeroom not found'}), 400
            
            from_major_location_id = from_storeroom.major_location_id
            from_storeroom_id = source_inv.storeroom_id
            from_location_id = source_inv.location_id
            from_bin_id = source_inv.bin_id
            
            # Get destination storeroom
            to_storeroom = Storeroom.query.get(to_storeroom_id)
            if not to_storeroom:
                return jsonify({'success': False, 'error': 'Destination storeroom not found'}), 400
            
            if to_storeroom.major_location_id != to_major_location_id:
                return jsonify({'success': False, 'error': 'Storeroom does not belong to the specified major location'}), 400
            
            # Find or create destination location
            to_location_id = None
            if to_location_name:
                # Try to find existing location
                location = Location.query.filter_by(
                    storeroom_id=to_storeroom_id,
                    location=to_location_name
                ).first()
                
                if not location:
                    # Create new location
                    storeroom_context = StoreroomContext(to_storeroom_id)
                    location_context = storeroom_context.add_location(
                        location=to_location_name,
                        display_name=to_location_name,
                        user_id=current_user.id
                    )
                    to_location_id = location_context.location_id
                else:
                    to_location_id = location.id
            
            # Find or create destination bin
            to_bin_id = None
            if to_bin_tag:
                if not to_location_id:
                    return jsonify({'success': False, 'error': 'Location is required when specifying a bin'}), 400
                
                # Try to find existing bin
                bin_obj = Bin.query.filter_by(
                    location_id=to_location_id,
                    bin_tag=to_bin_tag
                ).first()
                
                if not bin_obj:
                    # Create new bin
                    location_context = LocationContext(to_location_id)
                    bin_obj = location_context.add_bin(
                        bin_tag=to_bin_tag,
                        user_id=current_user.id
                    )
                    to_bin_id = bin_obj.id
                else:
                    to_bin_id = bin_obj.id
            
            # Validate: prevent transfer to self (same location)
            if (from_storeroom_id == to_storeroom_id and 
                from_location_id == to_location_id and 
                from_bin_id == to_bin_id):
                return jsonify({'success': False, 'error': 'Cannot transfer inventory to the same location'}), 400
            
            # Perform the transfer
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
            
            logger.info(f"Inventory moved by {current_user.username}: {quantity} units of part {source_inv.part_id} from storeroom {from_storeroom_id} to storeroom {to_storeroom_id}")
            
            return jsonify({
                'success': True,
                'message': f'Successfully moved {quantity} units'
            }), 200
            
        except ValueError as e:
            db.session.rollback()
            logger.error(f"Error moving inventory: {e}")
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error moving inventory: {e}", exc_info=True)
            return jsonify({'success': False, 'error': 'An unexpected error occurred'}), 500
    
    # Initial Stocking Portal
    @inventory_bp.route('/initial-stocking')
    @login_required
    def initial_stocking():
        """Initial stocking portal - select storeroom and unassigned inventory"""
        logger.info(f"Initial stocking portal accessed by {current_user.username}")
        
        storeroom_id = request.args.get('storeroom_id', type=int)
        
        # Get all storerooms for dropdown
        storerooms = Storeroom.query.order_by(Storeroom.room_name.asc()).all()
        
        # Get unassigned inventory for selected storeroom
        unassigned_inventory = []
        if storeroom_id:
            unassigned_inventory = ActiveInventory.query.filter_by(
                storeroom_id=storeroom_id,
                location_id=None,
                bin_id=None
            ).filter(
                ActiveInventory.quantity_on_hand > 0
            ).options(
                joinedload(ActiveInventory.part),
                joinedload(ActiveInventory.storeroom).joinedload(Storeroom.major_location)
            ).order_by(
                ActiveInventory.part_id.asc()
            ).all()
        
        return render_template('inventory/inventory/initial_stocking.html',
                             storerooms=storerooms,
                             selected_storeroom_id=storeroom_id,
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
            data = request.get_json()
            
            inventory_ids = data.get('inventory_ids', [])
            location_id = data.get('location_id')
            if location_id:
                location_id = int(location_id)
            else:
                return jsonify({'success': False, 'error': 'Location is required'}), 400
            
            bin_id = data.get('bin_id')
            if bin_id:
                bin_id = int(bin_id)
            else:
                bin_id = None
            
            if not inventory_ids:
                return jsonify({'success': False, 'error': 'No inventory items selected'}), 400
            
            if not location_id:
                return jsonify({'success': False, 'error': 'Location is required'}), 400
            
            # Get location to verify storeroom
            location = Location.query.get_or_404(location_id)
            storeroom_id = location.storeroom_id
            
            # Get storeroom for major_location_id
            storeroom = Storeroom.query.get_or_404(storeroom_id)
            major_location_id = storeroom.major_location_id
            
            # Verify bin belongs to location if provided
            if bin_id:
                bin_obj = Bin.query.get_or_404(bin_id)
                if bin_obj.location_id != location_id:
                    return jsonify({'success': False, 'error': 'Bin does not belong to selected location'}), 400
            
            # Get inventory items
            inventory_items = ActiveInventory.query.filter(
                ActiveInventory.id.in_(inventory_ids),
                ActiveInventory.storeroom_id == storeroom_id,
                ActiveInventory.location_id.is_(None),
                ActiveInventory.bin_id.is_(None)
            ).all()
            
            if not inventory_items:
                return jsonify({'success': False, 'error': 'No valid unassigned inventory items found'}), 400
            
            # Create movements for each inventory item
            inventory_manager = InventoryManager()
            movements_created = 0
            
            for inv in inventory_items:
                # Use assign_unassigned_to_bin to create the movement
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
            
            logger.info(f"Stocking movement created by {current_user.username}: {movements_created} items assigned to location {location_id}")
            
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
    
    # Submit Issue Endpoint
    @inventory_bp.route('/submit-issue', methods=['POST'])
    @login_required
    def submit_issue():
        """Process part issue submission"""
        try:
            import json
            
            # Get form data
            issue_type = request.form.get('issue_type')
            issued_to_user_id = request.form.get('issued_to_user_id', type=int)
            asset_id = request.form.get('asset_id', type=int) or None
            issue_reason = request.form.get('issue_reason', '').strip() or None
            issue_notes = request.form.get('issue_notes', '').strip() or None
            issued_by_id = request.form.get('issued_by_id', type=int) or current_user.id
            queue_data_str = request.form.get('queue_data', '')
            date_issued_str = request.form.get('date_issued', '').strip()
            
            # Parse date_issued
            if date_issued_str:
                try:
                    issue_date = datetime.fromisoformat(date_issued_str.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    issue_date = datetime.utcnow()
            else:
                issue_date = datetime.utcnow()
            
            # Validate required fields
            if not issue_type or not issued_to_user_id:
                flash('Issue type and user are required', 'error')
                return redirect(url_for('inventory.issue_parts'))
            
            # Parse queue data
            try:
                queue_data = json.loads(queue_data_str)
            except json.JSONDecodeError:
                flash('Invalid queue data', 'error')
                return redirect(url_for('inventory.issue_parts'))
            
            if not queue_data:
                flash('No items in issue queue', 'error')
                return redirect(url_for('inventory.issue_parts'))
            
            # Import PartIssue model
            from app.data.inventory.inventory.part_issue import PartIssue
            from app.data.inventory.inventory.inventory_movement import InventoryMovement
            from app.data.inventory.inventory.inventory_summary import InventorySummary
            
            inventory_manager = InventoryManager()
            issues_created = []
            
            # Process each item in the queue
            for item in queue_data:
                inventory_id = int(item['inventory_id'])
                quantity = float(item['quantity'])
                part_id = int(item['part_id'])
                storeroom_id = int(item['storeroom_id'])
                major_location_id = int(item['major_location_id'])
                location_id = int(item['location_id']) if item.get('location_id') else None
                bin_id = int(item['bin_id']) if item.get('bin_id') else None
                
                # Get active inventory record
                active_inv = ActiveInventory.query.get_or_404(inventory_id)
                
                # Check available quantity
                available = active_inv.quantity_on_hand - active_inv.quantity_allocated
                if available < quantity:
                    flash(f'Insufficient quantity for {item["part_number"]}. Available: {available}, Requested: {quantity}', 'error')
                    db.session.rollback()
                    return redirect(url_for('inventory.issue_parts'))
                
                # Update active inventory
                active_inv.quantity_on_hand -= quantity
                active_inv.last_movement_date = datetime.utcnow()
                
                # Delete if empty and flag is set
                from app.buisness.inventory.stock.inventory_manager import DELETE_EMPTY_ACTIVE_ROWS
                if DELETE_EMPTY_ACTIVE_ROWS and active_inv.quantity_on_hand <= 0:
                    db.session.delete(active_inv)
                
                # Update inventory summary
                summary = InventorySummary.query.filter_by(part_id=part_id).first()
                if summary:
                    summary.quantity_on_hand_total = (summary.quantity_on_hand_total or 0.0) - quantity
                    summary.last_updated_at = datetime.utcnow()
                
                # Get unit cost
                unit_cost_at_issue = summary.unit_cost_avg if summary else None
                total_cost = (unit_cost_at_issue * quantity) if unit_cost_at_issue else None
                
                # Create InventoryMovement
                movement = InventoryMovement(
                    part_id=part_id,
                    major_location_id=major_location_id,
                    storeroom_id=storeroom_id,
                    movement_type="Issue",
                    quantity_delta=-quantity,
                    from_major_location_id=major_location_id,
                    from_storeroom_id=storeroom_id,
                    from_location_id=location_id,
                    from_bin_id=bin_id,
                    unit_cost=unit_cost_at_issue,
                )
                db.session.add(movement)
                db.session.flush()  # Get movement.id
                
                # Get part_demand_id from queue item if linked
                part_demand_id = int(item.get('part_demand_id')) if item.get('part_demand_id') else None
                
                # Create PartIssue
                part_issue = PartIssue(
                    inventory_movement_id=movement.id,
                    part_id=part_id,
                    quantity_issued=quantity,
                    unit_cost_at_issue=unit_cost_at_issue,
                    total_cost=total_cost,
                    issued_to_user_id=issued_to_user_id,
                    part_demand_id=part_demand_id,
                    asset_id=asset_id,
                    issue_type='ForPartDemand' if part_demand_id else issue_type,
                    issue_date=issue_date,
                    issued_from_storeroom_id=storeroom_id,
                    issued_from_location_id=location_id,
                    issued_from_bin_id=bin_id,
                    issued_by_id=issued_by_id,
                    issue_reason=issue_reason,
                    issue_notes=issue_notes,
                )
                db.session.add(part_issue)
                db.session.flush()  # Get part_issue.id
                
                # Link movement to part_issue
                movement.part_issue_id = part_issue.id
                
                issues_created.append({
                    'part_number': item['part_number'],
                    'quantity': quantity,
                    'issue_id': part_issue.id
                })
            
            db.session.commit()
            
            flash(f'Successfully issued {len(issues_created)} part(s)', 'success')
            logger.info(f"Parts issued by {current_user.username}: {len(issues_created)} items")
            
            return redirect(url_for('inventory.issue_parts'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error submitting issue: {e}", exc_info=True)
            flash(f'Error submitting issue: {str(e)}', 'error')
            return redirect(url_for('inventory.issue_parts'))
    
    @inventory_bp.route('/issue-parts/api/events')
    @login_required
    def issue_parts_get_events():
        """API endpoint: Get maintenance events with unlinked demands for issue parts"""
        from app.buisness.inventory.purchase_orders.purchase_order_linkage_portal import PurchaseOrderLinkagePortal
        from datetime import datetime
        
        def _parse_int(value):
            if value is None:
                return None
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        def _parse_datetime(value: str | None) -> datetime | None:
            if not value:
                return None
            try:
                return datetime.fromisoformat(value)
            except (TypeError, ValueError):
                return None
        
        part_id = _parse_int(request.args.get('part_id', type=int))
        asset_id = _parse_int(request.args.get('asset_id', type=int))
        make = request.args.get('make', type=str)
        model = request.args.get('model', type=str)
        asset_type_id = _parse_int(request.args.get('asset_type_id', type=int))
        major_location_id = _parse_int(request.args.get('major_location_id', type=int))
        assigned_user_id = _parse_int(request.args.get('assigned_user_id', type=int))
        created_from = _parse_datetime(request.args.get('created_from', type=str))
        created_to = _parse_datetime(request.args.get('created_to', type=str))
        
        # Use a dummy PO ID (0) since we just need the method, not the PO
        # We'll modify the logic to get unlinked demands (not linked to issues)
        from app.data.maintenance.base.part_demands import PartDemand
        from app.data.maintenance.base.actions import Action
        from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
        from app.data.core.asset_info.asset import Asset
        from app.data.inventory.inventory.part_issue import PartIssue
        
        # Get all demand IDs that are already linked to issues
        linked_demand_ids = db.session.query(PartIssue.part_demand_id).filter(
            PartIssue.part_demand_id.isnot(None)
        ).distinct().all()
        linked_demand_ids = {row[0] for row in linked_demand_ids}
        
        # Query unlinked demands
        query = PartDemand.query.filter(
            ~PartDemand.id.in_(linked_demand_ids) if linked_demand_ids else True
        )
        
        if part_id:
            query = query.filter(PartDemand.part_id == part_id)
        
        unlinked_demands = query.options(
            db.joinedload(PartDemand.action).joinedload(Action.maintenance_action_set).joinedload(MaintenanceActionSet.asset),
            db.joinedload(PartDemand.part)
        ).all()
        
        # Group by maintenance action set (event)
        events_dict = {}
        for demand in unlinked_demands:
            if not demand.action or not demand.action.maintenance_action_set:
                continue
            
            mas = demand.action.maintenance_action_set
            asset = mas.asset
            
            # Apply filters
            if asset_id and asset and asset.id != asset_id:
                continue
            if make and asset and asset.make_model and asset.make_model.make != make:
                continue
            if model and asset and asset.make_model and asset.make_model.model != model:
                continue
            if asset_type_id and asset and asset.asset_type_id != asset_type_id:
                continue
            if major_location_id and asset and asset.major_location_id != major_location_id:
                continue
            if assigned_user_id and mas.assigned_user_id != assigned_user_id:
                continue
            if created_from and mas.created_at and mas.created_at < created_from:
                continue
            if created_to and mas.created_at and mas.created_at > created_to:
                continue
            
            event_id = mas.id
            if event_id not in events_dict:
                events_dict[event_id] = {
                    "event_id": event_id,
                    "maintenance_action_set": mas,
                    "demands": []
                }
            
            events_dict[event_id]["demands"].append(demand)
        
        # Serialize for JSON
        result = []
        for event_data in events_dict.values():
            mas = event_data["maintenance_action_set"]
            demands = event_data["demands"]
            
            result.append({
                "event_id": mas.id,
                "task_name": mas.task_name,
                "asset_name": mas.asset.name if mas.asset else None,
                "asset_id": mas.asset_id,
                "status": mas.status,
                "priority": mas.priority,
                "planned_start": mas.planned_start_datetime.isoformat() if mas.planned_start_datetime else None,
                "demands": [
                    {
                        "id": d.id,
                        "part_id": d.part_id,
                        "part_number": d.part.part_number if d.part else str(d.part_id),
                        "part_name": d.part.part_name if d.part else "",
                        "quantity_required": float(d.quantity_required),
                        "status": d.status,
                        "priority": d.priority,
                        "action_name": d.action.action_name if d.action else ""
                    }
                    for d in demands
                ]
            })
        
        return jsonify(result)






