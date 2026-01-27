"""
Routes for creating Purchase Orders from Part Demands portal
"""
import json
from typing import Optional
from flask import render_template, request, flash, redirect, url_for, session, make_response
from flask_login import login_required, current_user
from app import db
from app.logger import get_logger
from sqlalchemy import or_
from app.buisness.inventory.purchasing.purchase_order_factory import PurchaseOrderFactory
from app.data.core.major_location import MajorLocation
from app.data.inventory.inventory.storeroom import Storeroom
from app.services.inventory.purchasing.part_demand_search_service import PartDemandSearchService
from datetime import datetime

# Import inventory_bp from main module
from app.presentation.routes.inventory.main import inventory_bp

logger = get_logger("asset_management.routes.inventory.purchasing.po_from_part_demands")

# Session keys for storing selected part demand IDs and unlinked parts
SESSION_SELECTED_PART_DEMAND_IDS_KEY = "inventory_po_from_part_demands_selected_ids"
SESSION_UNLINKED_PARTS_KEY = "inventory_po_from_part_demands_unlinked_parts"


def _get_selected_part_demand_ids() -> list[int]:
    """Get selected part demand IDs from session"""
    raw = session.get(SESSION_SELECTED_PART_DEMAND_IDS_KEY, [])
    if not isinstance(raw, list):
        raw = []
    # normalize to ints and de-dupe
    return PartDemandSearchService.normalize_selected_ids([str(x) for x in raw])


def _set_selected_part_demand_ids(ids: list[int]) -> None:
    """Store selected part demand IDs in session"""
    session[SESSION_SELECTED_PART_DEMAND_IDS_KEY] = ids
    session.modified = True


def _parse_date_filter(date_str: str) -> Optional[datetime]:
    """Parse date filter string to datetime object."""
    if not date_str or not date_str.strip():
        return None
    date_str = date_str.strip()
    try:
        # Handle date-only format (YYYY-MM-DD) or datetime format
        if 'T' in date_str or '+' in date_str or 'Z' in date_str:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            # Date-only format
            return datetime.strptime(date_str, '%Y-%m-%d')
    except (ValueError, AttributeError):
        return None


def _get_unlinked_parts() -> list[dict]:
    """Get unlinked parts from session"""
    raw = session.get(SESSION_UNLINKED_PARTS_KEY, [])
    if not isinstance(raw, list):
        raw = []
    return raw


def _set_unlinked_parts(parts: list[dict]) -> None:
    """Store unlinked parts in session"""
    session[SESSION_UNLINKED_PARTS_KEY] = parts
    session.modified = True


def _add_unlinked_part(part_id: int, quantity: float, unit_cost: float) -> None:
    """Add an unlinked part to the session"""
    from app.data.core.supply.part_definition import PartDefinition
    part = PartDefinition.query.get(part_id)
    if not part:
        raise ValueError(f"Part {part_id} not found")
    
    unlinked = _get_unlinked_parts()
    # Check if part already exists, update it if so
    for item in unlinked:
        if item['part_id'] == part_id:
            item['quantity'] = quantity
        item['unit_cost'] = unit_cost
        _set_unlinked_parts(unlinked)
        return
    
    # Add new unlinked part
    unlinked.append({
    'part_id': part_id,
    'part_number': part.part_number,
    'part_name': part.part_name,
    'quantity': quantity,
    'unit_cost': unit_cost,
    })
    _set_unlinked_parts(unlinked)


def _redirect_back_to_part_demands_portal(extra_params: dict | None = None):
    """Redirect back to the part demands portal, preserving query parameters"""
    params = dict(request.args)
    if extra_params:
        params.update(extra_params)
    return redirect(url_for("inventory.create_po", **params))


@inventory_bp.route("/create-po/search-bars/parts", methods=["GET"])
@login_required
def search_bars_parts_po_from_demands():
    """HTMX endpoint to return part search results for adding unlinked parts"""
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
                'inventory/purchase_orders/components/unlinked_part_search_results.html',
                parts=parts,
                total_count=total_count,
                showing=len(parts),
                search=search,
                selected_part_id=selected_part_id
        )
    except Exception as e:
        logger.error(f"Error in parts search: {e}")
        return render_template(
                'inventory/purchase_orders/components/unlinked_part_search_results.html',
                parts=[],
                total_count=0,
                showing=0,
                search=search or '',
                error=str(e)
        ), 500
    
@inventory_bp.route("/create-po/js", methods=["GET"])
def create_po_from_part_demands_js():
    """Serve the JavaScript file for create PO from part demands page"""
    from flask import current_app
    from pathlib import Path
    
    # Get the template directory from Flask app config
    template_folder = current_app.template_folder
    js_path = Path(template_folder) / 'inventory' / 'purchase_orders' / 'components' / 'create_from_part_demands.js'
    
    # Read and return the file
    with open(js_path, 'r', encoding='utf-8') as f:
        js_content = f.read()
    
    response = make_response(js_content)
    response.headers['Content-Type'] = 'application/javascript; charset=utf-8'
    return response

@inventory_bp.route("/create-po", methods=["GET"])
@login_required
def create_po():
    """Portal: select part demand lines, then create a purchase order with per-part pricing confirmation."""
    logger.info(f"Create PO from part demands accessed by {current_user.username}")

    # Get filter parameters
    part_id = request.args.get('part_id', type=int)
    part_description = request.args.get('part_description', '').strip() or None
    maintenance_event_id = request.args.get('maintenance_event_id', type=int)
    asset_id = request.args.get('asset_id', type=int)
    assigned_to_id = request.args.get('assigned_to_id', type=int)
    major_location_id = request.args.get('major_location_id', type=int)
    status = request.args.get('status', '').strip() or None
    sort_by = request.args.get('sort_by', '').strip() or None
    
    # Get date range parameters
    created_from = _parse_date_filter(request.args.get('created_from', '').strip())
    created_to = _parse_date_filter(request.args.get('created_to', '').strip())
    updated_from = _parse_date_filter(request.args.get('updated_from', '').strip())
    updated_to = _parse_date_filter(request.args.get('updated_to', '').strip())
    maintenance_event_created_from = _parse_date_filter(request.args.get('maintenance_event_created_from', '').strip())
    maintenance_event_created_to = _parse_date_filter(request.args.get('maintenance_event_created_to', '').strip())
    maintenance_event_updated_from = _parse_date_filter(request.args.get('maintenance_event_updated_from', '').strip())
    maintenance_event_updated_to = _parse_date_filter(request.args.get('maintenance_event_updated_to', '').strip())

    options = PartDemandSearchService.get_filter_options()

    # Search results - use default_to_orderable=True for inventory use case
    part_demands = PartDemandSearchService.get_filtered_part_demands(
    part_id=part_id,
        part_description=part_description,
        maintenance_event_id=maintenance_event_id,
        asset_id=asset_id,
        assigned_to_id=assigned_to_id,
        major_location_id=major_location_id,
        status=status,
        sort_by=sort_by,
        created_from=created_from,
        created_to=created_to,
        updated_from=updated_from,
        updated_to=updated_to,
        maintenance_event_created_from=maintenance_event_created_from,
        maintenance_event_created_to=maintenance_event_created_to,
        maintenance_event_updated_from=maintenance_event_updated_from,
        maintenance_event_updated_to=maintenance_event_updated_to,
        default_to_orderable=True
    )

    # Current selection (queue)
    selected_ids = _get_selected_part_demand_ids()
    selected_demands = PartDemandSearchService.get_demands_by_ids(selected_ids)
    parts_summary = PartDemandSearchService.build_parts_summary(selected_demands)
    
    # Get unlinked parts
    unlinked_parts = _get_unlinked_parts()
    
    # Add unlinked parts to summary
    for unlinked in unlinked_parts:
    # Check if part already exists in summary (from linked demands)
        existing = next((p for p in parts_summary if p['part_id'] == unlinked['part_id']), None)
        if existing:
                # Update quantity and unit cost if unlinked part has higher quantity
                if unlinked['quantity'] > existing['total_qty']:
                    existing['total_qty'] = unlinked['quantity']
                if unlinked['unit_cost'] > 0:
                    existing['default_unit_cost'] = unlinked['unit_cost']
        else:
                # Add new unlinked part to summary
                parts_summary.append({
                    'part_id': unlinked['part_id'],
                    'part_number': unlinked['part_number'],
                    'part_name': unlinked['part_name'],
                    'total_qty': unlinked['quantity'],
                    'default_unit_cost': unlinked['unit_cost'],
                })

    # Header dropdown options
    locations = MajorLocation.query.filter_by(is_active=True).all()
    storerooms = Storeroom.query.order_by(Storeroom.room_name.asc()).all()

    filters_dict = {
    "part_id": part_id or "",
        "part_description": part_description or "",
        "maintenance_event_id": maintenance_event_id or "",
        "asset_id": asset_id or "",
        "assigned_to_id": assigned_to_id or "",
        "major_location_id": major_location_id or "",
        "status": status or "",
        "sort_by": sort_by or "",
        "created_from": request.args.get('created_from', '').strip(),
        "created_to": request.args.get('created_to', '').strip(),
        "updated_from": request.args.get('updated_from', '').strip(),
        "updated_to": request.args.get('updated_to', '').strip(),
        "maintenance_event_created_from": request.args.get('maintenance_event_created_from', '').strip(),
        "maintenance_event_created_to": request.args.get('maintenance_event_created_to', '').strip(),
        "maintenance_event_updated_from": request.args.get('maintenance_event_updated_from', '').strip(),
        "maintenance_event_updated_to": request.args.get('maintenance_event_updated_to', '').strip(),
    }

    # If HTMX request, return only the search results partial
    if request.headers.get('HX-Request'):
        return render_template(
                "inventory/purchase_orders/components/search_results_table.html",
                filters=filters_dict,
                part_demands=part_demands,
                selected_demands=selected_demands,
                unlinked_parts=unlinked_parts,
        )

    # Full page render
    return render_template(
    "inventory/purchase_orders/create_from_part_demands.html",
        filters=filters_dict,
        part_demands=part_demands,
        selected_demands=selected_demands,
        parts_summary=parts_summary,
        unlinked_parts=unlinked_parts,
        status_options=options["status_options"],
        users=options["users"],
        locations=locations,
        storerooms=storerooms,
        major_locations=options["locations"],
    )

@inventory_bp.route("/create-po/add", methods=["POST"])
@login_required
def create_po_from_part_demands_add():
    """Add selected part demands to the selection queue"""
    ids_to_add = PartDemandSearchService.normalize_selected_ids(request.form.getlist("part_demand_ids"))
    if not ids_to_add:
        flash("No part demands selected to add", "warning")
        return _redirect_back_to_part_demands_portal()

    selected = _get_selected_part_demand_ids()
    merged = selected + [i for i in ids_to_add if i not in selected]
    _set_selected_part_demand_ids(merged)
    flash(f"Added {len(ids_to_add)} part demand(s) to selection", "success")
    return _redirect_back_to_part_demands_portal()

@inventory_bp.route("/create-po/remove/<int:part_demand_id>", methods=["POST"])
@login_required
def create_po_from_part_demands_remove(part_demand_id: int):
    """Remove a part demand from the selection queue"""
    selected = _get_selected_part_demand_ids()
    if part_demand_id in selected:
        selected = [i for i in selected if i != part_demand_id]
        _set_selected_part_demand_ids(selected)
    flash(f"Removed part demand {part_demand_id}", "success")
    return _redirect_back_to_part_demands_portal()

@inventory_bp.route("/create-po/remove-part/<int:part_id>", methods=["POST"])
@login_required
def create_po_from_part_demands_remove_part(part_id: int):
    """Remove all part demands for a specific part from the selection queue"""
    from app.data.maintenance.base.part_demands import PartDemand
    
    selected = _get_selected_part_demand_ids()
    if not selected:
        flash("No part demands selected", "error")
        return _redirect_back_to_part_demands_portal()
    
    # Get all part demands for this part
    part_demands = PartDemand.query.filter(
    PartDemand.id.in_(selected),
        PartDemand.part_id == part_id
    ).all()
    
    if not part_demands:
        flash(f"No part demands found for part {part_id}", "error")
        return _redirect_back_to_part_demands_portal()
    
    # Remove all part demand IDs for this part
    part_demand_ids_to_remove = {d.id for d in part_demands}
    selected = [i for i in selected if i not in part_demand_ids_to_remove]
    _set_selected_part_demand_ids(selected)
    
    flash(f"Removed {len(part_demand_ids_to_remove)} part demand(s) for part {part_id}", "success")
    return _redirect_back_to_part_demands_portal()

@inventory_bp.route("/create-po/clear", methods=["POST"])
@login_required
def create_po_from_part_demands_clear():
    """Clear all selected part demands from the queue"""
    _set_selected_part_demand_ids([])
    flash("Cleared selected part demands", "success")
    return _redirect_back_to_part_demands_portal()

@inventory_bp.route("/create-po/submit-v2", methods=["POST"])
@login_required
def create_po_from_part_demands_submit_v2():
    """Submit purchase order creation from part demands using JSON schema"""
    from flask import jsonify
    
    # Get JSON data from request
    if request.is_json:
        data = request.get_json()
    else:
    # Try to parse as form data and convert to schema
        data = {
                "header": {
                    "vendor_name": request.form.get("vendor_name", "").strip(),
                    "vendor_contact": request.form.get("vendor_contact", "").strip() or None,
                    "location_id": request.form.get("location_id", type=int),
                    "storeroom_id": request.form.get("storeroom_id", type=int),
                    "shipping_cost": request.form.get("shipping_cost", type=float) or 0.0,
                    "tax_amount": request.form.get("tax_amount", type=float) or 0.0,
                    "other_amount": request.form.get("other_amount", type=float) or 0.0,
                    "notes": request.form.get("notes", "").strip() or None,
                },
                "line_items": json.loads(request.form.get("line_items", "[]"))
        }
    
    logger.info(f"PO SUBMISSION V2 - Received from user: {current_user.username} (ID: {current_user.id})")
    logger.debug(f"Submission data: {json.dumps(data, indent=2)}")
    
    try:
    # Use the from_dict factory method
        po_context = PurchaseOrderFactory.from_dict(
                po_data=data,
                created_by_id=current_user.id,
        )
        
        db.session.commit()
        
        # Clear selected part demand IDs and unlinked parts from session
        _set_selected_part_demand_ids([])
        _set_unlinked_parts([])
        
        logger.info(f"Successfully created PO {po_context.purchase_order_id} ({po_context.header.po_number})")
        
        # Return success response with redirect URL
        return jsonify({
                "success": True,
                "message": f"Purchase order {po_context.header.po_number} created successfully",
                "po_id": po_context.purchase_order_id,
                "po_number": po_context.header.po_number,
                "redirect_url": url_for("inventory.purchase_order_view", po_id=po_context.purchase_order_id)
        }), 200
        
    except ValueError as e:
        logger.error(f"Validation error creating PO from part demands: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
                "success": False,
                "message": f"Validation error: {str(e)}"
        }), 400
        
    except Exception as e:
        logger.error(f"Error creating PO from part demands: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
                "success": False,
                "message": f"Error creating purchase order: {str(e)}"
        }), 500

@inventory_bp.route("/create-po/submit", methods=["POST"])
@login_required
def create_po_from_part_demands_submit():
    """Submit purchase order creation from selected part demands"""
    selected_ids = _get_selected_part_demand_ids()
    if not selected_ids:
        flash("No part demands selected", "error")
        return _redirect_back_to_part_demands_portal()

    vendor_name = (request.form.get("vendor_name") or "").strip()
    if not vendor_name:
        flash("Vendor name is required", "error")
        return _redirect_back_to_part_demands_portal()

    location_id = request.form.get("location_id", type=int)
    if not location_id:
        flash("Location is required", "error")
        return _redirect_back_to_part_demands_portal()

    selected_demands = PartDemandSearchService.get_demands_by_ids(selected_ids)
    parts_summary = PartDemandSearchService.build_parts_summary(selected_demands)

    # Parse per-part pricing and require explicit confirmation per part.
    prices_by_part_id: dict[int, float] = {}
    missing: list[str] = []
    for row in parts_summary:
        part_id = int(row["part_id"])
        unit_cost = request.form.get(f"unit_cost_part_{part_id}", type=float)
        confirmed = request.form.get(f"confirm_price_part_{part_id}") == "on"
        if unit_cost is None:
                missing.append(f"Missing unit cost for part {row['part_number']}")
                continue
        if unit_cost < 0:
                missing.append(f"Unit cost cannot be negative for part {row['part_number']}")
                continue
        if not confirmed:
                missing.append(f"Please confirm price for part {row['part_number']}")
                continue
        prices_by_part_id[part_id] = float(unit_cost)

    if missing:
        for msg in missing[:5]:
                flash(msg, "error")
        if len(missing) > 5:
                flash(f"...and {len(missing) - 5} more pricing errors", "error")
        return _redirect_back_to_part_demands_portal()

    # Build data structure for from_dict method
    # Group demands by part_id to create line_items
    from collections import defaultdict
    from app.data.maintenance.base.part_demands import PartDemand
    
    demands_by_part: dict[int, list[PartDemand]] = defaultdict(list)
    for demand in selected_demands:
        demands_by_part[demand.part_id].append(demand)
    
    # Build line_items with linked_demands
    line_items = []
    for part_id, part_demands_list in demands_by_part.items():
        # Calculate total quantity for this part
        total_quantity = sum(d.quantity_required for d in part_demands_list)
        unit_cost = prices_by_part_id[part_id]
        
        # Build linked_demands list
        linked_demands = [
            {
                "part_demand_id": d.id,
                "quantity_allocated": float(d.quantity_required)
            }
            for d in part_demands_list
        ]
        
        line_items.append({
            "part_id": part_id,
            "quantity": float(total_quantity),
            "unit_cost": float(unit_cost),
            "confirmed": True,  # Already validated above
            "linked_demands": linked_demands
        })
    
    # Build po_data dict for from_dict
    po_data = {
        "header": {
            "vendor_name": vendor_name,
            "vendor_contact": (request.form.get("vendor_contact") or "").strip() or None,
            "location_id": location_id,
            "storeroom_id": request.form.get("storeroom_id", type=int),
            "shipping_cost": request.form.get("shipping_cost", type=float) or 0.0,
            "tax_amount": request.form.get("tax_amount", type=float) or 0.0,
            "other_amount": request.form.get("other_amount", type=float) or 0.0,
            "notes": (request.form.get("notes") or "").strip() or None,
        },
        "line_items": line_items
    }

    try:
        po_context = PurchaseOrderFactory.from_dict(
                po_data=po_data,
                created_by_id=current_user.id,
        )
        db.session.commit()
        _set_selected_part_demand_ids([])
        flash(f"Purchase order {po_context.header.po_number} created successfully", "success")
        return redirect(url_for("inventory.purchase_order_view", po_id=po_context.purchase_order_id))
    except Exception as e:
        logger.error(f"Error creating PO from part demands: {e}", exc_info=True)
        db.session.rollback()
        flash(f"Error creating purchase order: {str(e)}", "error")
        return _redirect_back_to_part_demands_portal()
    
@inventory_bp.route("/create-po/add-unlinked-part", methods=["POST"])
@login_required
def create_po_from_part_demands_add_unlinked():
    """Add an unlinked part to the parts summary"""
    try:
        from app.data.core.supply.part_definition import PartDefinition
        
        part_id = request.form.get('part_id', type=int)
        
        if not part_id:
                flash("Part ID is required", "error")
                return _redirect_back_to_part_demands_portal()
        
        # Get part to retrieve default values
        part = PartDefinition.query.get(part_id)
        if not part:
                flash(f"Part {part_id} not found", "error")
                return _redirect_back_to_part_demands_portal()
        
        # Default quantity to 1.0 and unit_cost to part's last_unit_cost or 0
        quantity = 1.0
        unit_cost = float(part.last_unit_cost) if part.last_unit_cost else 0.0
        
        _add_unlinked_part(part_id, quantity, unit_cost)
        flash("Unlinked part added successfully", "success")
        return _redirect_back_to_part_demands_portal()
    except ValueError as e:
        flash(str(e), "error")
        return _redirect_back_to_part_demands_portal()
    except Exception as e:
        logger.error(f"Error adding unlinked part: {e}", exc_info=True)
    flash(f"Error adding unlinked part: {str(e)}", "error")
    return _redirect_back_to_part_demands_portal()

@inventory_bp.route("/create-po/remove-unlinked-part/<int:part_id>", methods=["POST"])
@login_required
def create_po_from_part_demands_remove_unlinked(part_id: int):
    """Remove an unlinked part from the parts summary"""
    unlinked = _get_unlinked_parts()
    unlinked = [p for p in unlinked if p['part_id'] != part_id]
    _set_unlinked_parts(unlinked)
    flash(f"Removed unlinked part", "success")
    return _redirect_back_to_part_demands_portal()