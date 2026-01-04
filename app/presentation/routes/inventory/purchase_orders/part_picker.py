"""
Part picker portal for purchase orders
"""
from flask import render_template, request
from flask_login import login_required
from app import db
from app.logger import get_logger
from app.services.inventory.purchasing.part_picker_service import PartPickerService
from app.data.core.supply.part_definition import PartDefinition
from app.data.core.major_location import MajorLocation

logger = get_logger("asset_management.routes.inventory.purchase_orders.part_picker")


def register_part_picker_routes(inventory_bp):
    """Register part picker routes to the inventory blueprint"""
    
    # Part picker portal for purchase orders
    @inventory_bp.route('/purchase-orders/<int:po_id>/part-picker')
    @login_required
    def purchase_order_part_picker(po_id):
        """HTMX endpoint to return part picker portal"""
        mode = request.args.get('mode', 'description')  # description, inventory, maintenance
        search = request.args.get('search', '').strip()
        category = request.args.get('category')
        manufacturer = request.args.get('manufacturer')
        location_id = request.args.get('location_id', type=int)
        stock_level = request.args.get('stock_level')
        event_type = request.args.get('event_type')
        
        parts = []
        preview = {}
        
        if mode == 'description':
            parts = PartPickerService.search_by_description(
                search_term=search,
                category=category,
                manufacturer=manufacturer
            )
        elif mode == 'inventory':
            parts = PartPickerService.search_by_inventory(
                search_term=search,
                location_id=location_id,
                stock_level=stock_level
            )
        elif mode == 'maintenance':
            parts, preview = PartPickerService.search_by_maintenance_event(
                search_term=search,
                event_type=event_type
            )
        
        # Get unique categories and manufacturers for filters
        categories = db.session.query(PartDefinition.category).filter(
            PartDefinition.category.isnot(None),
            PartDefinition.status == 'Active'
        ).distinct().order_by(PartDefinition.category).all()
        categories = [c[0] for c in categories]
        
        manufacturers = db.session.query(PartDefinition.manufacturer).filter(
            PartDefinition.manufacturer.isnot(None),
            PartDefinition.status == 'Active'
        ).distinct().order_by(PartDefinition.manufacturer).all()
        manufacturers = [m[0] for m in manufacturers]
        
        # Get locations for inventory filter
        locations = MajorLocation.query.filter_by(is_active=True).all()
        
        return render_template(
            'inventory/ordering/part_picker.html',
            po_id=po_id,
            mode=mode,
            parts=parts,
            preview=preview,
            search=search,
            category=category,
            manufacturer=manufacturer,
            location_id=location_id,
            stock_level=stock_level,
            event_type=event_type,
            categories=categories,
            manufacturers=manufacturers,
            locations=locations
        )







