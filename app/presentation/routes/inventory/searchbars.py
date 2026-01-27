"""
Search bars for purchase order creator and initial stocking
"""
from flask import render_template, request
from flask_login import login_required
from app import db
from app.logger import get_logger
from sqlalchemy.orm import joinedload
from sqlalchemy import or_

# Import inventory_bp from main module
from app.presentation.routes.inventory.main import inventory_bp

logger = get_logger("asset_management.routes.inventory.searchbars")


# Part search for purchase order creator
@inventory_bp.route('/purchase-order/search-bars/parts')
@login_required
def search_bars_parts():
    """HTMX endpoint to return part search results"""
    try:
        from app.data.core.supply.part_definition import PartDefinition
        
        search = request.args.get('search', '').strip()
        limit = request.args.get('limit', type=int, default=10)
        selected_part_id = request.args.get('selected_part_id', type=int)
        
        query = PartDefinition.query.filter(PartDefinition.status == 'Active')
        
        if search:
                query = query.filter(
                    db.or_(
                        PartDefinition.part_number.ilike(f'%{search}%'),
                        PartDefinition.part_name.ilike(f'%{search}%'),
                        PartDefinition.description.ilike(f'%{search}%')
                    )
                )
        
        parts = query.order_by(PartDefinition.part_name).limit(limit).all()
        total_count = query.count()
        
        return render_template(
                'inventory/ordering/search_bars/parts_results.html',
                parts=parts,
                total_count=total_count,
                showing=len(parts),
                search=search,
                selected_part_id=selected_part_id
        )
    except Exception as e:
        logger.error(f"Error in parts search: {e}")
        return render_template(
                'inventory/ordering/search_bars/parts_results.html',
                parts=[],
                total_count=0,
                showing=0,
                search=search or '',
                error=str(e)
        ), 500


# Initial Stocking - Storeroom dropdown filtered by major location
@inventory_bp.route('/initial-stocking/search-bars/storerooms')
@login_required
def initial_stocking_storerooms():
    """HTMX endpoint to return storeroom dropdown filtered by major location"""
    try:
        from app.data.inventory.inventory.storeroom import Storeroom
        
        major_location_id = request.args.get('major_location_id', type=int) or request.args.get('classic_major_location_id', type=int)
        # Get selected storeroom from the form if available, otherwise from URL
        selected_storeroom_id = request.args.get('storeroom_id', type=int) or request.args.get('classic_storeroom_id', type=int) or request.args.get('selected_storeroom_id', type=int)
        
        # Get storerooms filtered by major location
        storerooms_query = Storeroom.query.options(
            joinedload(Storeroom.major_location)
        ).order_by(Storeroom.room_name.asc())
        
        if major_location_id:
            storerooms_query = storerooms_query.filter_by(major_location_id=major_location_id)
        
        storerooms = storerooms_query.all()
        
        # Determine which template to use based on request source
        use_classic = request.args.get('use_classic', type=bool, default=False)
        template_name = 'initial_stocking_partials/classic_storeroom_dropdown.html' if use_classic else 'initial_stocking_partials/storeroom_dropdown.html'
        
        return render_template(
            f'inventory/inventory/{template_name}',
            storerooms=storerooms,
            selected_storeroom_id=selected_storeroom_id
        )
    except Exception as e:
        logger.error(f"Error in initial stocking storerooms search: {e}")
        use_classic = request.args.get('use_classic', type=bool, default=False)
        template_name = 'initial_stocking_partials/classic_storeroom_dropdown.html' if use_classic else 'initial_stocking_partials/storeroom_dropdown.html'
        return render_template(
            f'inventory/inventory/{template_name}',
            storerooms=[],
            selected_storeroom_id=None,
            error=str(e)
        ), 500


# Initial Stocking - Inventory list filtered by storeroom and part search
@inventory_bp.route('/initial-stocking/search-bars/inventory')
@login_required
def initial_stocking_inventory():
    """HTMX endpoint to return inventory list filtered by storeroom and part search"""
    try:
        from app.data.inventory.inventory.active_inventory import ActiveInventory
        from app.data.core.supply.part_definition import PartDefinition
        
        storeroom_id = request.args.get('storeroom_id', type=int)
        part_search = request.args.get('part_search', '').strip() or None
        
        if not storeroom_id:
            return render_template(
                'inventory/inventory/initial_stocking_partials/inventory_list.html',
                unassigned_inventory=[],
                selected_storeroom_id=None
            )
        
        # Get unassigned inventory for selected storeroom
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
        
        from app.data.inventory.inventory.storeroom import Storeroom
        
        unassigned_inventory = query.options(
            joinedload(ActiveInventory.part),
            joinedload(ActiveInventory.storeroom).joinedload(Storeroom.major_location)
        ).order_by(
            ActiveInventory.part_id.asc()
        ).all()
        
        return render_template(
            'inventory/inventory/initial_stocking_partials/inventory_list.html',
            unassigned_inventory=unassigned_inventory,
            selected_storeroom_id=storeroom_id,
            part_search=part_search
        )
    except Exception as e:
        logger.error(f"Error in initial stocking inventory search: {e}")
        return render_template(
            'inventory/inventory/initial_stocking_partials/inventory_list.html',
            unassigned_inventory=[],
            selected_storeroom_id=None,
            error=str(e)
        ), 500


# Initial Stocking - Locations dropdown filtered by storeroom
@inventory_bp.route('/initial-stocking/search-bars/locations')
@login_required
def initial_stocking_locations():
    """HTMX endpoint to return location dropdown filtered by storeroom"""
    try:
        from app.data.inventory.locations.location import Location
        
        storeroom_id = request.args.get('storeroom_id', type=int) or request.args.get('classic_storeroom_id', type=int)
        selected_location_id = request.args.get('location_id', type=int) or request.args.get('classic_location_id', type=int)
        
        logger.debug(f"Initial stocking locations - storeroom_id: {storeroom_id}, all args: {dict(request.args)}")
        
        if not storeroom_id:
            logger.warning("No storeroom_id provided for locations query")
            return render_template(
                'inventory/inventory/initial_stocking_partials/location_dropdown.html',
                locations=[],
                selected_location_id=None
            )
        
        # Get locations for this storeroom
        locations = Location.query.filter_by(
            storeroom_id=storeroom_id
        ).order_by(Location.location.asc()).all()
        
        logger.debug(f"Found {len(locations)} locations for storeroom_id {storeroom_id}")
        
        return render_template(
            'inventory/inventory/initial_stocking_partials/location_dropdown.html',
            locations=locations,
            selected_location_id=selected_location_id
        )
    except Exception as e:
        logger.error(f"Error in initial stocking locations search: {e}")
        return render_template(
            'inventory/inventory/initial_stocking_partials/location_dropdown.html',
            locations=[],
            selected_location_id=None,
            error=str(e)
        ), 500


# Initial Stocking - Bins dropdown filtered by location
@inventory_bp.route('/initial-stocking/search-bars/bins')
@login_required
def initial_stocking_bins():
    """HTMX endpoint to return bin dropdown filtered by location"""
    try:
        from app.data.inventory.locations.bin import Bin
        
        location_id = request.args.get('location_id', type=int) or request.args.get('classic_location_id', type=int)
        selected_bin_id = request.args.get('bin_id', type=int) or request.args.get('classic_bin_id', type=int)
        
        if not location_id:
            return render_template(
                'inventory/inventory/initial_stocking_partials/bin_dropdown.html',
                bins=[],
                selected_bin_id=None
            )
        
        # Get bins for this location
        bins = Bin.query.filter_by(
            location_id=location_id
        ).order_by(Bin.bin_tag.asc()).all()
        
        return render_template(
            'inventory/inventory/initial_stocking_partials/bin_dropdown.html',
            bins=bins,
            selected_bin_id=selected_bin_id
        )
    except Exception as e:
        logger.error(f"Error in initial stocking bins search: {e}")
        return render_template(
            'inventory/inventory/initial_stocking_partials/bin_dropdown.html',
            bins=[],
            selected_bin_id=None,
            error=str(e)
        ), 500


# Initial Stocking - Search results with Add to Queue buttons
@inventory_bp.route('/initial-stocking/search-bars/unassigned-search')
@login_required
def initial_stocking_unassigned_search():
    """HTMX endpoint to return searchable unassigned inventory results"""
    try:
        from app.data.inventory.inventory.active_inventory import ActiveInventory
        from app.data.core.supply.part_definition import PartDefinition
        
        storeroom_id = request.args.get('storeroom_id', type=int)
        part_search = request.args.get('part_search', '').strip() or None
        
        if not storeroom_id:
            return render_template(
                'inventory/inventory/initial_stocking_partials/search_results.html',
                search_results=[],
                storeroom_id=None,
                part_search=part_search
            )
        
        # Get unassigned inventory for selected storeroom
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
        
        from app.data.inventory.inventory.storeroom import Storeroom
        
        search_results = query.options(
            joinedload(ActiveInventory.part),
            joinedload(ActiveInventory.storeroom).joinedload(Storeroom.major_location)
        ).order_by(
            ActiveInventory.part_id.asc()
        ).limit(50).all()  # Limit to 50 results for performance
        
        return render_template(
            'inventory/inventory/initial_stocking_partials/search_results.html',
            search_results=search_results,
            storeroom_id=storeroom_id,
            part_search=part_search
        )
    except Exception as e:
        logger.error(f"Error in initial stocking unassigned search: {e}")
        return render_template(
            'inventory/inventory/initial_stocking_partials/search_results.html',
            search_results=[],
            storeroom_id=None,
            part_search=part_search or '',
            error=str(e)
        ), 500






