"""
Arrival Linkage Portal Routes

Routes for linking part arrivals to PO lines.
"""
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from app.services.inventory.arrivals.arrival_linkage_portal import ArrivalLinkagePortal
from app.buisness.inventory.arrivals.arrival_context import ArrivalContext
from app.logger import get_logger

logger = get_logger("asset_management.routes.inventory.arrivals.linkage_portal")

# Import inventory_bp from main module
from app.presentation.routes.inventory.main import inventory_bp

def _parse_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@inventory_bp.route('/arrivals/<int:package_id>/link')
@login_required
def arrival_linkage_portal(package_id):
    """Arrival linkage portal main page"""
    logger.info(f"Arrival linkage portal accessed for package {package_id} by {current_user.username}")
    
    portal = ArrivalLinkagePortal(package_id)
    package = portal.package_header
    arrivals_with_po_lines = portal.get_arrivals_with_po_lines()
    
    return render_template(
    'inventory/arrivals/linkage_portal.html',
    package=package,
    arrivals_with_po_lines=arrivals_with_po_lines,
    portal=portal
    )
    
@inventory_bp.route('/arrivals/<int:package_id>/link/api/purchase-orders')
@login_required
def arrival_linkage_get_pos(package_id):
    """API endpoint: Get purchase orders with unlinked PO lines"""
    part_id = request.args.get('part_id', type=int)
    po_number = request.args.get('po_number', type=str)
    vendor_name = request.args.get('vendor_name', type=str)
    status = request.args.get('status', type=str)
    major_location_id = request.args.get('major_location_id', type=int)
    
    portal = ArrivalLinkagePortal(package_id)
    pos = portal.get_purchase_orders_with_lines(
    part_id=part_id,
    po_number=po_number,
    vendor_name=vendor_name,
    status=status,
    major_location_id=major_location_id,
    )
    
    # Serialize for JSON
    result = []
    for po_data in pos:
        po = po_data["purchase_order"]
    po_lines = po_data["po_lines"]
    
    result.append({
        "purchase_order_id": po_data["purchase_order_id"],
        "po_number": po.po_number,
        "vendor_name": po.vendor_name,
        "status": po.status,
        "order_date": po.order_date.isoformat() if po.order_date else None,
        "po_lines": [
                {
                    "id": line.id,
                    "line_number": line.line_number,
                    "part_id": line.part_id,
                    "part_number": line.part.part_number if line.part else str(line.part_id),
                    "part_name": line.part.part_name if line.part else "",
                    "quantity_ordered": float(line.quantity_ordered),
                    "quantity_received": float(line.quantity_received_total),
                    "quantity_needed": float(line.quantity_ordered - line.quantity_received_total),
                    "status": line.status,
                    "unit_cost": float(line.unit_cost) if line.unit_cost else 0.0,
                }
                for line in po_lines
        ]
    })
    
    return jsonify(result)
    
@inventory_bp.route('/arrivals/<int:package_id>/link/api/link', methods=['POST'])
@login_required
def arrival_linkage_link_to_po_line(package_id):
    """API endpoint: Link an arrival to a PO line"""
    data = request.get_json() or {}
    part_arrival_id = _parse_int(data.get("part_arrival_id"))
    po_line_id = _parse_int(data.get("po_line_id"))
    quantity_to_link = _parse_float(data.get("quantity_to_link"))
    
    if not part_arrival_id or not po_line_id:
        return jsonify({"success": False, "message": "Missing part_arrival_id or po_line_id"}), 400
    
    if not quantity_to_link or quantity_to_link <= 0:
        return jsonify({"success": False, "message": "Invalid quantity"}), 400
    
    # Use ArrivalLinkagePortal service
    portal = ArrivalLinkagePortal(package_id)
    success, message = portal.link_arrival_to_po_line(
        part_arrival_id=part_arrival_id,
        po_line_id=po_line_id,
        quantity_to_link=quantity_to_link,
        user_id=current_user.id
    )
    
    return jsonify({"success": success, "message": message})
    
@inventory_bp.route('/arrivals/<int:package_id>/link/api/unlink', methods=['POST'])
@login_required
def arrival_linkage_unlink_from_po_line(package_id):
    """API endpoint: Unlink an arrival from a PO line"""
    data = request.get_json() or {}
    part_arrival_id = _parse_int(data.get("part_arrival_id"))
    link_id = _parse_int(data.get("link_id"))  # Support unlinking specific link
    
    if not part_arrival_id:
        return jsonify({"success": False, "message": "Missing part_arrival_id"}), 400
    
    # Use ArrivalLinkagePortal service
    portal = ArrivalLinkagePortal(package_id)
    success, message = portal.unlink_arrival_from_po_line(
        part_arrival_id=part_arrival_id,
        user_id=current_user.id,
        link_id=link_id
    )
    
    return jsonify({"success": success, "message": message})

