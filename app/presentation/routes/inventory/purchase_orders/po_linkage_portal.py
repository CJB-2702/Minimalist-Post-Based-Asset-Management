"""
Purchase Order Linkage Portal Routes

Routes for linking part demands to PO lines.
"""
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from app.buisness.inventory.purchase_orders.purchase_order_linkage_portal import PurchaseOrderLinkagePortal
from app.logger import get_logger

logger = get_logger("asset_management.routes.inventory.purchase_orders.linkage_portal")

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


def register_po_linkage_routes(inventory_bp):
    """Register PO linkage portal routes"""
    
    @inventory_bp.route('/purchase-orders/<int:po_id>/link')
    @login_required
    def po_linkage_portal(po_id):
        """Purchase order linkage portal main page"""
        logger.info(f"PO linkage portal accessed for PO {po_id} by {current_user.username}")
        
        portal = PurchaseOrderLinkagePortal(po_id)
        po = portal.purchase_order
        lines_with_demands = portal.get_po_lines_with_demands()
        
        return render_template(
            'inventory/purchase_orders/linkage_portal.html',
            purchase_order=po,
            lines_with_demands=lines_with_demands,
            portal=portal
        )
    
    @inventory_bp.route('/purchase-orders/<int:po_id>/link/api/events')
    @login_required
    def po_linkage_get_events(po_id):
        """API endpoint: Get maintenance events with unlinked demands"""
        part_id = request.args.get('part_id', type=int)
        asset_id = request.args.get('asset_id', type=int)
        make = request.args.get('make', type=str)
        model = request.args.get('model', type=str)
        asset_type_id = request.args.get('asset_type_id', type=int)
        major_location_id = request.args.get('major_location_id', type=int)
        assigned_user_id = request.args.get('assigned_user_id', type=int)
        created_from = _parse_datetime(request.args.get('created_from', type=str))
        created_to = _parse_datetime(request.args.get('created_to', type=str))
        
        portal = PurchaseOrderLinkagePortal(po_id)
        events = portal.get_maintenance_events_with_demands(
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
        
        # Serialize for JSON
        result = []
        for event_data in events:
            mas = event_data["maintenance_action_set"]
            demands = event_data["demands"]
            
            result.append({
                "event_id": event_data["event_id"],
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
    
    @inventory_bp.route('/purchase-orders/<int:po_id>/link/api/link', methods=['POST'])
    @login_required
    def po_linkage_link_demand(po_id):
        """API endpoint: Link a demand to a PO line"""
        data = request.get_json() or {}
        po_line_id = _parse_int(data.get("po_line_id"))
        part_demand_id = _parse_int(data.get("part_demand_id"))
        
        if not po_line_id or not part_demand_id:
            return jsonify({"success": False, "message": "Missing po_line_id or part_demand_id"}), 400
        
        portal = PurchaseOrderLinkagePortal(po_id)
        success, message = portal.link_demand(po_line_id, part_demand_id, current_user.id)
        
        return jsonify({"success": success, "message": message})
    
    @inventory_bp.route('/purchase-orders/<int:po_id>/link/api/unlink', methods=['POST'])
    @login_required
    def po_linkage_unlink_demand(po_id):
        """API endpoint: Unlink a demand from a PO line"""
        data = request.get_json() or {}
        part_demand_id = _parse_int(data.get("part_demand_id"))
        
        if not part_demand_id:
            return jsonify({"success": False, "message": "Missing part_demand_id"}), 400
        
        portal = PurchaseOrderLinkagePortal(po_id)
        success, message = portal.unlink_demand(part_demand_id)
        
        return jsonify({"success": success, "message": message})

