"""
Inventory management routes - Active inventory and movement linking
"""
from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.logger import get_logger
from app.services.inventory.inventory.active_inventory_service import ActiveInventoryService
from app.services.inventory.inventory.inventory_movement_service import InventoryMovementService
from app.buisness.inventory.inventory.inventory_manager import InventoryManager
from app.buisness.inventory.locations.storeroom_context import StoreroomContext
from app.buisness.inventory.locations.location_context import LocationContext
from app.data.inventory.inventory.active_inventory import ActiveInventory
from app.data.inventory.inventory.storeroom import Storeroom
from app.data.inventory.locations.location import Location
from app.data.inventory.locations.bin import Bin
from sqlalchemy.orm import joinedload
from datetime import datetime

logger = get_logger("asset_management.routes.inventory.inventory")

# Import inventory_bp from main module
from app.presentation.routes.inventory.main import inventory_bp

# Import move inventory GUI module to register its routes
from . import move_inventory_gui  # noqa: F401

# Import stocking portals module to register its routes
from . import stocking_portals  # noqa: F401

# Part Issues List
@inventory_bp.route('/part-issues')
@login_required
def part_issues_list():
    """List all part issues with filters"""
    logger.info(f"Part issues list accessed by {current_user.username}")
    
    from app.data.inventory.inventory.part_issue import PartIssue
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
        # Get data from form POST
        active_inventory_id = request.form.get('active_inventory_id', type=int)
        if not active_inventory_id:
            flash('Active inventory ID is required', 'error')
            return redirect(url_for('inventory.active_inventory_view'))
        
        source_inv = ActiveInventory.query.get_or_404(active_inventory_id)
        
        # Get destination details from form
        quantity = request.form.get('quantity', type=float)
        if not quantity or quantity <= 0:
            flash('Quantity must be greater than 0', 'error')
            return redirect(url_for('inventory.active_inventory_view'))
        
        to_major_location_id = request.form.get('to_major_location_id', type=int)
        to_storeroom_id = request.form.get('to_storeroom_id', type=int)
        to_location_name = request.form.get('to_location', '').strip() if request.form.get('to_location') else None
        to_bin_tag = request.form.get('to_bin', '').strip() if request.form.get('to_bin') else None
        
        # Validate required fields
        if not to_major_location_id or not to_storeroom_id:
            flash('Major location and storeroom are required', 'error')
            return redirect(url_for('inventory.active_inventory_view'))
        
        # Validate bin requires location
        if to_bin_tag and not to_location_name:
            flash('Bin requires a location', 'error')
            return redirect(url_for('inventory.active_inventory_view'))
        
        # Check sufficient quantity
        available_quantity = (source_inv.quantity_on_hand or 0.0) - (source_inv.quantity_allocated or 0.0)
        if available_quantity < quantity:
            flash(f'Not enough quantity. Available: {available_quantity}', 'error')
            return redirect(url_for('inventory.active_inventory_view'))
        
        # Get source details
        from_storeroom = source_inv.storeroom
        if not from_storeroom:
            flash('Source storeroom not found', 'error')
            return redirect(url_for('inventory.active_inventory_view'))
        
        from_major_location_id = from_storeroom.major_location_id
        from_storeroom_id = source_inv.storeroom_id
        from_location_id = source_inv.location_id
        from_bin_id = source_inv.bin_id
        
        # Get destination storeroom
        to_storeroom = Storeroom.query.get(to_storeroom_id)
        if not to_storeroom:
            flash('Destination storeroom not found', 'error')
            return redirect(url_for('inventory.active_inventory_view'))
        
        if to_storeroom.major_location_id != to_major_location_id:
            flash('Storeroom does not belong to the specified major location', 'error')
            return redirect(url_for('inventory.active_inventory_view'))
        
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
                flash('Location is required when specifying a bin', 'error')
                return redirect(url_for('inventory.active_inventory_view'))
        
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
            flash('Cannot transfer inventory to the same location', 'error')
        return redirect(url_for('inventory.active_inventory_view'))
    
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
        
        flash(f'Successfully moved {quantity} units', 'success')
        return redirect(url_for('inventory.active_inventory_view'))
        
    except ValueError as e:
        db.session.rollback()
        logger.error(f"Error moving inventory: {e}")
        flash(str(e), 'error')
        return redirect(url_for('inventory.active_inventory_view'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error moving inventory: {e}", exc_info=True)
        flash('An unexpected error occurred', 'error')
        return redirect(url_for('inventory.active_inventory_view'))
    
    # Submit Issue Endpoint
@inventory_bp.route('/submit-issue', methods=['POST'])
@login_required
def submit_issue():
    """
    Process part issue submission.

    NOTE: This handler was mid-refactor and had syntax/indentation issues that prevented
    the inventory module from importing. It is temporarily disabled to allow the app to run.
    """
    logger.warning("submit_issue is temporarily disabled (refactor in progress)")
    flash("Issue submission is temporarily disabled while refactor is in progress.", "error")
    return redirect(url_for('inventory.issue_parts'))
    
@inventory_bp.route('/issue-parts/api/events')
@login_required
def issue_parts_get_events():
    """
    API endpoint: Get maintenance events with unlinked demands for issue parts portal
    Uses PartDemandSearchService to find matching demands
    """
    try:
        from app.services.inventory.purchasing.part_demand_search_service import PartDemandSearchService
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
        
        # Get filter parameters
        part_id = request.args.get('part_id', type=int)
        asset_id = request.args.get('asset_id', type=int)
        make = request.args.get('make', type=str)
        model = request.args.get('model', type=str)
        asset_type_id = request.args.get('asset_type_id', type=int)
        major_location_id = request.args.get('major_location_id', type=int)
        assigned_user_id = request.args.get('assigned_user_id', type=int)
        created_from = _parse_datetime(request.args.get('created_from', type=str))
        created_to = _parse_datetime(request.args.get('created_to', type=str))
        
        # Get unlinked demands (demands not already linked to inventory issues)
        # Note: For issue parts, we want demands that are orderable (not already issued)
        unlinked_demands = PartDemandSearchService.get_filtered_part_demands(
            part_id=part_id,
            asset_id=asset_id,
            asset_type_id=asset_type_id,
            make=make,
            model=model,
            assigned_to_id=assigned_user_id,
            major_location_id=major_location_id,
            maintenance_event_created_from=created_from,
            maintenance_event_created_to=created_to,
            default_to_orderable=True,
            limit=2000,
        )
        
        # Group by maintenance event
        events_dict = {}
        for demand in unlinked_demands:
            # Skip demands without proper relationships
            if not demand.action or not demand.action.maintenance_action_set:
                continue
                
            mas = demand.action.maintenance_action_set
            event_id = mas.event_id
            
            if event_id not in events_dict:
                events_dict[event_id] = {
                    "event_id": event_id,
                    "maintenance_action_set": mas,
                    "demands": []
                }
            
            events_dict[event_id]["demands"].append(demand)
        
        # Serialize events for JSON response
        result = []
        for event_data in events_dict.values():
            mas = event_data["maintenance_action_set"]
            demands = event_data["demands"]
            
            # Safely get asset name
            asset_name = None
            if mas.asset and hasattr(mas.asset, 'name'):
                asset_name = mas.asset.name
            
            # Safely get planned start datetime
            planned_start = None
            if hasattr(mas, 'planned_start_datetime') and mas.planned_start_datetime:
                planned_start = mas.planned_start_datetime.isoformat()
            
            # Serialize demands
            serialized_demands = []
            for d in demands:
                # Safely get part info
                part_number = str(d.part_id)
                part_name = ""
                if d.part:
                    if hasattr(d.part, 'part_number') and d.part.part_number:
                        part_number = d.part.part_number
                    if hasattr(d.part, 'part_name') and d.part.part_name:
                        part_name = d.part.part_name
                
                # Safely get action name
                action_name = ""
                if d.action and hasattr(d.action, 'action_name'):
                    action_name = d.action.action_name or ""
                
                serialized_demands.append({
                    "id": d.id,
                    "part_id": d.part_id,
                    "part_number": part_number,
                    "part_name": part_name,
                    "quantity_required": float(d.quantity_required) if d.quantity_required else 0.0,
                    "status": d.status if d.status else "",
                    "priority": d.priority if d.priority else "",
                    "action_name": action_name
                })
            
            result.append({
                "event_id": event_data["event_id"],
                "task_name": getattr(mas, 'task_name', '') or "",
                "asset_name": asset_name,
                "asset_id": getattr(mas, 'asset_id', None),
                "status": getattr(mas, 'status', '') or "",
                "priority": getattr(mas, 'priority', '') or "",
                "planned_start": planned_start,
                "demands": serialized_demands
            })
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error loading events: {str(e)}", exc_info=True)
        return jsonify({"error": f"Error loading events: {str(e)}"}), 500


@inventory_bp.route('/issue-parts/api/demands')
@login_required
def issue_parts_get_demands():
    """
    API endpoint: Get unlinked part demands by part ID for issue parts portal
    Uses PartDemandSearchService to find matching demands
    """
    try:
        from app.services.inventory.purchasing.part_demand_search_service import PartDemandSearchService
        
        part_id = request.args.get('part_id', type=int)
        
        if not part_id:
            return jsonify([])
        
        # Get unlinked demands for this part
        unlinked_demands = PartDemandSearchService.get_filtered_part_demands(
            part_id=part_id,
            default_to_orderable=True,
            limit=2000,
        )
        
        # Serialize demands for JSON response
        result = []
        for d in unlinked_demands:
            # Safely get part info
            part_number = str(d.part_id)
            part_name = ""
            if d.part:
                if hasattr(d.part, 'part_number') and d.part.part_number:
                    part_number = d.part.part_number
                if hasattr(d.part, 'part_name') and d.part.part_name:
                    part_name = d.part.part_name
            
            # Safely get action name
            action_name = ""
            if d.action and hasattr(d.action, 'action_name'):
                action_name = d.action.action_name or ""
            
            # Get event name from maintenance action set
            event_name = ""
            if d.action and d.action.maintenance_action_set:
                mas = d.action.maintenance_action_set
                event_name = getattr(mas, 'task_name', '') or ""
            
            result.append({
                "id": d.id,
                "part_id": d.part_id,
                "part_number": part_number,
                "part_name": part_name,
                "quantity_required": float(d.quantity_required) if d.quantity_required else 0.0,
                "status": d.status if d.status else "",
                "priority": d.priority if d.priority else "",
                "action_name": action_name,
                "event_name": event_name
            })
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error loading demands: {str(e)}", exc_info=True)
        return jsonify({"error": f"Error loading demands: {str(e)}"}), 500






