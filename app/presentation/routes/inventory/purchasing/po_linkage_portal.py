"""
Purchase Order Linkage Portal Routes

Routes for linking part demands to PO lines.
"""
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from app.buisness.inventory.purchasing.purchase_order_context import PurchaseOrderContext
from app.buisness.inventory.purchasing.purchase_order_link_manager import PurchaseOrderLinkManager
from app.services.inventory.purchasing.po_linkage_lookup_service import POLinkageLookupService
from app.logger import get_logger

# Import inventory_bp from main module
from app.presentation.routes.inventory.main import inventory_bp

logger = get_logger("asset_management.routes.inventory.purchasing.linkage_portal")

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
        # Accept ISO strings like "2024-01-15" or full ISO datetime
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


@inventory_bp.route('/purchase-order/<int:po_id>/link')
@login_required
def po_linkage_portal(po_id):
    """Purchase order linkage portal main page"""
    logger.info(f"PO linkage portal accessed for PO {po_id} by {current_user.username}")
    
    context = PurchaseOrderContext(po_id)
    po = context.purchase_order
    lines_with_demands = context.get_po_lines_with_demands()
    
    return render_template(
        'inventory/purchase_orders/linkage_portal.html',
        purchase_order=po,
        lines_with_demands=lines_with_demands
    )

@inventory_bp.route('/purchase-order/api/events')
@login_required
def po_linkage_get_events():
    """API endpoint: Get maintenance events with unlinked demands"""
    try:
        po_id = request.args.get('po_id', type=int)
        part_id = request.args.get('part_id', type=int)
        asset_id = request.args.get('asset_id', type=int)
        make = request.args.get('make', type=str)
        model = request.args.get('model', type=str)
        asset_type_id = request.args.get('asset_type_id', type=int)
        major_location_id = request.args.get('major_location_id', type=int)
        assigned_user_id = request.args.get('assigned_user_id', type=int)
        created_from = _parse_datetime(request.args.get('created_from', type=str))
        created_to = _parse_datetime(request.args.get('created_to', type=str))
        
        # Use the service to get events with demands
        events = POLinkageLookupService.get_maintenance_events_with_demands(
            po_id=po_id,
            part_id=part_id,
            asset_id=asset_id,
            make=make,
            model=model,
            asset_type_id=asset_type_id,
            major_location_id=major_location_id,
            created_from=created_from,
            created_to=created_to,
            assigned_user_id=assigned_user_id,
        )
        
        # Serialize for JSON using the service method
        result = [POLinkageLookupService.serialize_event_data(event_data) for event_data in events]
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error loading events: {str(e)}", exc_info=True)
        return jsonify({"error": f"Error loading events: {str(e)}"}), 500
    
@inventory_bp.route('/purchase-order/<int:po_id>/link/api/link', methods=['POST'])
@inventory_bp.route('/purchase-orders/<int:po_id>/link/api/link', methods=['POST'])
@login_required
def po_linkage_link_demand(po_id):
    """API endpoint: Link a demand to a PO line"""
    data = request.get_json() or {}
    po_line_id = _parse_int(data.get("po_line_id"))
    part_demand_id = _parse_int(data.get("part_demand_id"))
    
    if not po_line_id or not part_demand_id:
        return jsonify({"success": False, "message": "Missing po_line_id or part_demand_id"}), 400
    
    link_manager = PurchaseOrderLinkManager()
    success, message = link_manager.link_demand(po_id, po_line_id, part_demand_id, current_user.id)
    
    return jsonify({"success": success, "message": message})

@inventory_bp.route('/purchase-order/<int:po_id>/link/api/unlink', methods=['POST'])
@login_required
def po_linkage_unlink_demand(po_id):
    """API endpoint: Unlink a demand from a PO line"""
    data = request.get_json() or {}
    part_demand_id = _parse_int(data.get("part_demand_id"))
    
    if not part_demand_id:
        return jsonify({"success": False, "message": "Missing part_demand_id"}), 400
    
    link_manager = PurchaseOrderLinkManager()
    success, message = link_manager.unlink_demand(po_id, part_demand_id)
    
    return jsonify({"success": success, "message": message})

