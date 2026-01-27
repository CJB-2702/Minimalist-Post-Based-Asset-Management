"""Arrival creation routes.

Canonical entry point:
- /inventory/arrivals/create-arrival  (Arrivals Creation Portal)
"""

from __future__ import annotations

from flask import flash, make_response, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from pathlib import Path

from app import db
from app.buisness.inventory.arrivals.arrival_context import ArrivalContext
from app.buisness.inventory.arrivals.arrival_factory import ArrivalFactory
from app.data.core.major_location import MajorLocation
from app.data.inventory.arrivals import ArrivalHeader, ArrivalLine
from app.data.inventory.inventory.storeroom import Storeroom
from app.logger import get_logger
from app.presentation.routes.inventory.main import inventory_bp
from app.services.inventory.arrivals.arrival_po_line_selection_service import ArrivalPOLineSelectionService
from app.services.inventory.purchasing.po_search_service import POSearchFilters, POSearchService

logger = get_logger("asset_management.routes.inventory.arrivals.create_arrival")


# -----------------------------------------------------------------------------
# Direct Issue: (kept here because it's part of the arrival creation workflow)
# -----------------------------------------------------------------------------


@inventory_bp.route("/arrivals/direct-issue-from-po")
@login_required
def direct_issue_from_po():
    package_id = request.args.get("package_id", type=int)
    if not package_id:
        flash("package_id is required", "error")
        return redirect(url_for("inventory.arrivals_index"))

    try:
        # Use ArrivalContext to manage arrivals, links, and direct issue logic
        arrival_context = ArrivalContext(package_id, eager_load=True)
        
        # Delegate direct issue logic to ArrivalContext
        issued_any, message = arrival_context.direct_issue_to_part_demands()
        
        db.session.commit()
        flash(message, "success" if issued_any else "info")
        return redirect(url_for("inventory.po_arrival_detail", id=package_id))
    except Exception as e:
        flash(f"Error during direct issue: {str(e)}", "error")
        logger.error(f"Error during direct issue: {e}", exc_info=True)
        db.session.rollback()
        return redirect(url_for("inventory.po_arrival_detail", id=package_id))


# -----------------------------------------------------------------------------
# Arrivals Creation Portal
# -----------------------------------------------------------------------------


SESSION_SELECTED_PO_LINE_IDS_KEY = "inventory_arrival_from_po_lines_selected_ids"
SESSION_UNLINKED_PARTS_KEY = "inventory_arrival_from_po_lines_unlinked_parts"


def _get_selected_po_line_ids() -> list[int]:
    raw = session.get(SESSION_SELECTED_PO_LINE_IDS_KEY, [])
    if not isinstance(raw, list):
        raw = []
    return ArrivalPOLineSelectionService.normalize_selected_ids([str(x) for x in raw])


def _set_selected_po_line_ids(ids: list[int]) -> None:
    session[SESSION_SELECTED_PO_LINE_IDS_KEY] = ids
    session.modified = True


def _filters_from_request_args() -> POSearchFilters:
    return POSearchService.parse_filters(request.args)


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


def _redirect_back_to_create_arrival(extra_params: dict | None = None):
    params = dict(request.args)
    if extra_params:
        params.update(extra_params)
    return redirect(url_for("inventory.create_arrival", **params))


@inventory_bp.route("/arrivals/create-arrival", methods=["GET"])
@login_required
def create_arrival():
    """Baseline create-arrival portal (select PO lines, then create package arrival)."""
    logger.info(f"Create arrival (baseline) accessed by {current_user.username}")

    filters = _filters_from_request_args()
    options = ArrivalPOLineSelectionService.get_filter_options()

    is_htmx = bool(request.headers.get("HX-Request"))

    # If a PO id is provided, allow the page to pre-load all unfulfilled lines for receipt.
    # This is used by the "Receive parts" button on the PO detail view.
    reset = (request.args.get("reset") or "").strip() in ("1", "true", "yes")
    if not is_htmx and reset:
        _set_selected_po_line_ids([])
        _set_unlinked_parts([])

    po_lines = ArrivalPOLineSelectionService.get_unfulfilled_po_lines(filters)

    if not is_htmx and filters.purchase_order_id:
        # Pre-select all visible (unfulfilled) lines for this PO.
        _set_selected_po_line_ids([l.id for l in po_lines])

    selected_ids = _get_selected_po_line_ids()
    selected_lines = ArrivalPOLineSelectionService.get_lines_by_ids(selected_ids)
    lines_summary = ArrivalPOLineSelectionService.build_lines_summary(selected_lines)

    # Get unlinked parts
    unlinked_parts = _get_unlinked_parts()

    locations = MajorLocation.query.filter_by(is_active=True).all()
    storerooms = Storeroom.query.order_by(Storeroom.room_name.asc()).all()

    template_vars = {
        "filters": POSearchService.to_template_dict(filters),
        "po_lines": po_lines,
        "selected_lines": selected_lines,
        "lines_summary": lines_summary,
        "unlinked_parts": unlinked_parts,
        "status_options": options["statuses"],
        "users": options["users"],
        "locations": locations,
        "storerooms": storerooms,
        "major_locations": options["locations"],
        "assets": options["assets"],
    }

    # If HTMX request, return only the search results partial
    if request.headers.get("HX-Request"):
        return render_template(
            "inventory/arrivals/components/search_results_table.html",
            **template_vars,
        )

    # Full page render
    return render_template(
        "inventory/arrivals/arrivals_creation_portal.html",
        **template_vars,
    )


@inventory_bp.route("/arrivals/create-arrival/add", methods=["POST"])
@login_required
def create_arrival_add():
    ids_to_add = ArrivalPOLineSelectionService.normalize_selected_ids(request.form.getlist("po_line_ids"))
    if not ids_to_add:
        flash("No PO lines selected to add", "warning")
        return _redirect_back_to_create_arrival()

    selected = _get_selected_po_line_ids()
    merged = selected + [i for i in ids_to_add if i not in selected]
    _set_selected_po_line_ids(merged)
    flash(f"Added {len(ids_to_add)} PO line(s) to selection", "success")
    return _redirect_back_to_create_arrival()


@inventory_bp.route("/arrivals/create-arrival/remove/<int:po_line_id>", methods=["POST"])
@login_required
def create_arrival_remove(po_line_id: int):
    selected = _get_selected_po_line_ids()
    if po_line_id in selected:
        selected = [i for i in selected if i != po_line_id]
    _set_selected_po_line_ids(selected)
    flash(f"Removed PO line {po_line_id}", "success")
    return _redirect_back_to_create_arrival()


@inventory_bp.route("/arrivals/create-arrival/clear", methods=["POST"])
@login_required
def create_arrival_clear():
    _set_selected_po_line_ids([])
    _set_unlinked_parts([])
    flash("Cleared selected PO lines and unlinked parts", "success")
    return _redirect_back_to_create_arrival()


@inventory_bp.route("/arrivals/create-arrival/add-part", methods=["POST"])
@login_required
def create_arrival_add_part():
    """Add a part to the arrival (not linked to a PO line)"""
    try:
        from app.data.core.supply.part_definition import PartDefinition
        
        part_id = request.form.get('part_id', type=int)
        
        if not part_id:
            flash("Part ID is required", "error")
            return _redirect_back_to_create_arrival()
        
        # Get part to retrieve default values
        part = PartDefinition.query.get(part_id)
        if not part:
            flash(f"Part {part_id} not found", "error")
            return _redirect_back_to_create_arrival()
        
        # Default quantity to 1.0 for arrivals
        quantity = 1.0
        
        unlinked = _get_unlinked_parts()
        # Check if part already exists, update it if so
        for item in unlinked:
            if item['part_id'] == part_id:
                # Update existing
                item['quantity'] = quantity
                _set_unlinked_parts(unlinked)
                flash("Part updated successfully", "success")
                return _redirect_back_to_create_arrival()
        
        # Add new unlinked part
        unlinked.append({
            'part_id': part_id,
            'part_number': part.part_number,
            'part_name': part.part_name,
            'quantity': quantity,
        })
        _set_unlinked_parts(unlinked)
        flash("Part added successfully", "success")
        return _redirect_back_to_create_arrival()
    except ValueError as e:
        flash(str(e), "error")
        return _redirect_back_to_create_arrival()
    except Exception as e:
        logger.error(f"Error adding unlinked part: {e}", exc_info=True)
        flash(f"Error adding unlinked part: {str(e)}", "error")
        return _redirect_back_to_create_arrival()


@inventory_bp.route("/arrivals/create-arrival/remove-part/<int:part_id>", methods=["POST"])
@login_required
def create_arrival_remove_part(part_id: int):
    """Remove a part from the arrival"""
    unlinked = _get_unlinked_parts()
    unlinked = [p for p in unlinked if p['part_id'] != part_id]
    _set_unlinked_parts(unlinked)
    flash(f"Removed part", "success")
    return _redirect_back_to_create_arrival()


@inventory_bp.route("/arrivals/create-arrival/search-bars/parts", methods=["GET"])
@login_required
def search_bars_parts_arrival():
    """HTMX endpoint to return part search results for adding parts"""
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
            'inventory/arrivals/components/unlinked_part_search_results.html',
            parts=parts,
            total_count=total_count,
            showing=len(parts),
            search=search,
            selected_part_id=selected_part_id
        )
    except Exception as e:
        logger.error(f"Error in parts search: {e}")
        return render_template(
            'inventory/arrivals/components/unlinked_part_search_results.html',
            parts=[],
            total_count=0,
            showing=0,
            search=search or '',
            error=str(e)
        ), 500


@inventory_bp.route("/arrivals/create-arrival/js", methods=["GET"])
def create_arrival_js():
    """Serve the JavaScript file for the Arrivals Creation Portal"""
    from flask import current_app
    
    # Get the template directory from Flask app config
    template_folder = current_app.template_folder
    js_path = Path(template_folder) / 'inventory' / 'arrivals' / 'components' / 'arrivals_creation_portal.js'
    
    # Read and return the file
    with open(js_path, 'r', encoding='utf-8') as f:
        js_content = f.read()
    
    response = make_response(js_content)
    response.headers['Content-Type'] = 'application/javascript; charset=utf-8'
    return response


@inventory_bp.route("/arrivals/create-arrival/submit", methods=["POST"])
@login_required
def create_arrival_submit():
    """Submit arrival creation - handles both JSON and form data with HTMX support"""
    import json
    from flask import jsonify
    
    is_htmx = request.headers.get("HX-Request") == "true"
    
    # Get JSON data from request
    if request.is_json:
        data = request.get_json()
    else:
        # Try to parse as form data and convert to schema
        data = {
            "header": {
                "package_number": request.form.get("package_number", "").strip(),
                "major_location_id": request.form.get("major_location_id", type=int),
                "storeroom_id": request.form.get("storeroom_id", type=int),
                "tracking_number": request.form.get("tracking_number", "").strip() or None,
                "carrier": request.form.get("carrier", "").strip() or None,
                "notes": request.form.get("notes", "").strip() or None,
            }
        }
    
    logger.info(f"ARRIVAL SUBMISSION V2 - Received from user: {current_user.username} (ID: {current_user.id})")
    
    try:
        selected_ids = _get_selected_po_line_ids()
        unlinked_parts = _get_unlinked_parts()

        # Build unified parts list from selected PO lines and unlinked parts
        parts: list[dict] = []
        
        # Convert selected PO line IDs to parts format with purchase_order_line_id
        if selected_ids:
            from app.data.inventory.purchasing.purchase_order_line import PurchaseOrderLine
            
            # Validate PO lines for receipt
            is_valid, errors = ArrivalPOLineSelectionService.validate_lines_for_receipt(selected_ids)
            if not is_valid:
                error_msg = "Validation error: " + "; ".join(errors)
                if is_htmx:
                    return render_template("inventory/arrivals/components/error_message.html", message=error_msg), 400
                return jsonify({"success": False, "message": error_msg}), 400
            
            lines = PurchaseOrderLine.query.filter(PurchaseOrderLine.id.in_(selected_ids)).all()
            for line in lines:
                # Calculate remaining quantity for receipt
                remaining = max(
                    0.0,
                    float(line.quantity_ordered or 0.0) - float(line.quantity_received_total or 0.0),
                )
                if remaining > 0:
                    part_dict = {
                        "part_id": line.part_id,
                        "quantity_received": remaining,
                        "purchase_order_line_id": line.id,  # This will cause linking
                    }
                    # Extract quality fields from form if present (only for form submissions, not JSON)
                    if not request.is_json:
                        condition_key = f"condition_part_{line.part_id}"
                        notes_key = f"inspection_notes_part_{line.part_id}"
                        if condition_key in request.form:
                            condition = request.form.get(condition_key, "").strip()
                            if condition in ["Good", "Damaged", "Mixed"]:
                                part_dict["condition"] = condition
                        if notes_key in request.form:
                            notes = request.form.get(notes_key, "").strip()
                            if notes:
                                part_dict["inspection_notes"] = notes
                    parts.append(part_dict)
        
        # Convert unlinked parts to parts format (without purchase_order_line_id)
        for unlinked_part in unlinked_parts:
            part_id = unlinked_part.get("part_id")
            part_dict = {
                "part_id": part_id,
                "quantity_received": unlinked_part.get("quantity", unlinked_part.get("quantity_received", 1.0)),
            }
            # Extract quality fields from form if present (only for form submissions, not JSON)
            if not request.is_json:
                condition_key = f"condition_part_{part_id}"
                notes_key = f"inspection_notes_part_{part_id}"
                if condition_key in request.form:
                    condition = request.form.get(condition_key, "").strip()
                    if condition in ["Good", "Damaged", "Mixed"]:
                        part_dict["condition"] = condition
                if notes_key in request.form:
                    notes = request.form.get(notes_key, "").strip()
                    if notes:
                        part_dict["inspection_notes"] = notes
            # Include inspection_notes from unlinked_part dict if present (for backward compatibility)
            if "inspection_notes" not in part_dict and "inspection_notes" in unlinked_part:
                part_dict["inspection_notes"] = unlinked_part.get("inspection_notes")
            # No purchase_order_line_id means it will be unlinked (or auto-linked if available)
            parts.append(part_dict)
        
        # Add parts to the data dict using the new unified format
        if parts:
            data["parts"] = parts

        package_id = ArrivalFactory.from_dict(
            data,
            received_by_id=current_user.id,
            created_by_id=current_user.id,
        )

        pkg = ArrivalHeader.query.get_or_404(package_id)
        
        db.session.commit()
        _set_selected_po_line_ids([])
        _set_unlinked_parts([])
        
        logger.info(f"Successfully created package arrival {pkg.id} ({pkg.package_number})")
        
        # Handle HTMX requests with headers
        if is_htmx:
            redirect_url = url_for("inventory.po_arrival_detail", id=pkg.id)
            response = make_response("<div></div>")  # Empty div for hx-target
            response.headers["HX-Trigger"] = json.dumps({
                "showToast": {
                    "message": f"Package {pkg.package_number} created successfully. All parts received.",
                    "type": "success"
                }
            })
            response.headers["HX-Redirect"] = redirect_url
            return response
        
        # Return JSON for non-HTMX requests (API fallback)
        return jsonify({
            "success": True,
            "message": f"Package {pkg.package_number} created successfully. All parts received.",
            "package_id": pkg.id,
            "package_number": pkg.package_number,
            "redirect_url": url_for("inventory.po_arrival_detail", id=pkg.id)
        }), 200
        
    except IntegrityError as e:
        logger.error(f"Integrity error creating arrival from PO lines: {e}", exc_info=True)
        db.session.rollback()
        if "package_number" in str(e.orig).lower():
            error_msg = "Package number already exists. Please use a unique package number."
        else:
            error_msg = f"Database error: {str(e)}"
        if is_htmx:
            return render_template("inventory/arrivals/components/error_message.html", message=error_msg), 400
        return jsonify({"success": False, "message": error_msg}), 400 if "package_number" in str(e.orig).lower() else 500
        
    except ValueError as e:
        logger.error(f"Validation error creating arrival from PO lines: {e}", exc_info=True)
        db.session.rollback()
        error_msg = str(e)
        if is_htmx:
            return render_template("inventory/arrivals/components/error_message.html", message=error_msg), 400
        return jsonify({"success": False, "message": error_msg}), 400
        
    except Exception as e:
        logger.error(f"Error creating arrival from PO lines: {e}", exc_info=True)
        db.session.rollback()
        error_msg = f"Error creating package arrival: {str(e)}"
        if is_htmx:
            return render_template("inventory/arrivals/components/error_message.html", message=error_msg), 500
        return jsonify({"success": False, "message": error_msg}), 500


