"""
Purchase Order routes
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_required, current_user
from app import db
from app.logger import get_logger
from sqlalchemy.orm import joinedload
from app.buisness.inventory.ordering.purchase_order_context import PurchaseOrderContext
from app.buisness.inventory.ordering.purchase_order_factory import PurchaseOrderFactory
from app.data.inventory.ordering import PurchaseOrderHeader, PurchaseOrderLine, PartDemandPurchaseOrderLink
from app.data.maintenance.base.part_demands import PartDemand
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.core.event_info.event import Event
from app.data.core.major_location import MajorLocation
from app.data.inventory.inventory.storeroom import Storeroom
from app.services.inventory.purchasing.purchase_order_line_service import PurchaseOrderLineService
from app.data.core.asset_info.asset import Asset
from datetime import datetime
from app.services.inventory.purchasing.po_part_demand_selection_service import (
    InventoryPartDemandSelectionService,
    PartDemandFilters,
)

logger = get_logger("asset_management.routes.inventory.purchase_orders")


def register_purchase_order_routes(inventory_bp):
    """Register all purchase order routes to the inventory blueprint"""
    
    # Purchase Orders Splash/Index (Golden Path-focused)
    @inventory_bp.route('/purchase-orders')
    @login_required
    def purchase_orders_index():
        """Landing page for purchase order operations (golden path entry points)."""
        logger.info(f"Purchase orders index accessed by {current_user.username}")
        recent_pos = PurchaseOrderHeader.query.order_by(PurchaseOrderHeader.created_at.desc()).limit(10).all()
        return render_template('inventory/purchase_orders/index.html', recent_pos=recent_pos)

    # Purchase Orders List/View
    @inventory_bp.route('/purchase-orders/view')
    @login_required
    def purchase_orders_list():
        """List all purchase orders"""
        logger.info(f"Purchase orders list accessed by {current_user.username}")
        
        # Get filters
        status = request.args.get('status')
        location_id = request.args.get('location_id', type=int)
        search = request.args.get('search', '').strip()
        
        # Build query
        query = PurchaseOrderHeader.query
        
        if status:
            query = query.filter(PurchaseOrderHeader.status == status)
        
        if location_id:
            query = query.filter(PurchaseOrderHeader.major_location_id == location_id)
        
        if search:
            query = query.filter(
                db.or_(
                    PurchaseOrderHeader.po_number.ilike(f'%{search}%'),
                    PurchaseOrderHeader.vendor_name.ilike(f'%{search}%')
                )
            )
        
        # Order by creation date (newest first)
        purchase_orders = query.order_by(
            PurchaseOrderHeader.created_at.desc()
        ).all()
        
        # Get locations for filter
        locations = MajorLocation.query.filter_by(is_active=True).all()
        
        return render_template('inventory/ordering/purchase_orders_list.html',
                             purchase_orders=purchase_orders,
                             locations=locations,
                             current_status=status,
                             current_location_id=location_id,
                             current_search=search)

    # Purchase Order Detail View (new route scheme + backward-compatible alias)
    @inventory_bp.route('/purchase-order/<int:po_id>/view')
    @inventory_bp.route('/purchase-orders/<int:po_id>')
    @login_required
    def purchase_order_view(po_id):
        """View purchase order details"""
        logger.info(f"Purchase order {po_id} viewed by {current_user.username}")
        
        po_context = PurchaseOrderContext(po_id)
        
        # Get part demand links for each line item with eager loading
        # Create a dictionary mapping line_id to list of demand links
        line_demand_links = {}
        for line in po_context.lines:
            links = PartDemandPurchaseOrderLink.query.filter_by(
                purchase_order_line_id=line.id
            ).options(
                joinedload(PartDemandPurchaseOrderLink.part_demand)
                .joinedload(PartDemand.action)
                .joinedload(Action.maintenance_action_set)
                .joinedload(MaintenanceActionSet.event)
            ).all()
            line_demand_links[line.id] = links
        
        return render_template('inventory/ordering/purchase_order_view.html',
                             po_context=po_context,
                             line_demand_links=line_demand_links)

    # Golden Path: Create PO from Single Maintenance Event
    @inventory_bp.route('/create-po-from-single-maintenance', methods=['GET', 'POST'])
    @login_required
    def create_po_from_single_maintenance():
        """Golden-path portal: create a PO from a single maintenance event."""
        logger.info(f"Create PO from single maintenance accessed by {current_user.username}")

        # Shared form data
        locations = MajorLocation.query.filter_by(is_active=True).all()
        storerooms = Storeroom.query.order_by(Storeroom.room_name.asc()).all()

        # Maintenance events with orderable demands
        maintenance_events = (
            db.session.query(MaintenanceActionSet, Event)
            .join(Event, MaintenanceActionSet.event_id == Event.id)
            .join(Action, Action.maintenance_action_set_id == MaintenanceActionSet.id)
            .join(PartDemand, PartDemand.action_id == Action.id)
            .filter(PartDemand.status.in_(["Planned", "Pending Manager Approval", "Pending Inventory Approval"]))
            .group_by(MaintenanceActionSet.id, Event.id)
            .order_by(Event.created_at.desc())
            .limit(100)
            .all()
        )

        selected_event_id = request.values.get("maintenance_event_id", type=int)
        demands = []
        if selected_event_id:
            demands = (
                PartDemand.query.join(Action)
                .join(MaintenanceActionSet)
                .filter(MaintenanceActionSet.event_id == selected_event_id)
                .filter(PartDemand.status.in_(["Planned", "Pending Manager Approval", "Pending Inventory Approval"]))
                .options(joinedload(PartDemand.part))
                .order_by(PartDemand.id.asc())
                .all()
            )

        if request.method == "GET":
            return render_template(
                "inventory/purchase_orders/create_from_single_maintenance.html",
                maintenance_events=maintenance_events,
                selected_event_id=selected_event_id,
                demands=demands,
                locations=locations,
                storerooms=storerooms,
            )

        # POST: create PO
        try:
            if not selected_event_id:
                flash("Please select a maintenance event", "error")
                return redirect(url_for("inventory.create_po_from_single_maintenance"))

            vendor_name = request.form.get("vendor_name", "").strip()
            if not vendor_name:
                flash("Vendor name is required", "error")
                return redirect(url_for("inventory.create_po_from_single_maintenance", maintenance_event_id=selected_event_id))

            location_id = request.form.get("location_id", type=int)
            if not location_id:
                flash("Location is required", "error")
                return redirect(url_for("inventory.create_po_from_single_maintenance", maintenance_event_id=selected_event_id))

            selected_demand_ids = [int(x) for x in request.form.getlist("part_demand_ids")]
            if not selected_demand_ids:
                flash("Please select at least one part demand", "error")
                return redirect(url_for("inventory.create_po_from_single_maintenance", maintenance_event_id=selected_event_id))

            unit_cost_by_demand_id: dict[int, float] = {}
            for demand_id in selected_demand_ids:
                cost_raw = request.form.get(f"unit_cost_{demand_id}", type=float)
                if cost_raw is None:
                    flash(f"Missing unit cost for demand {demand_id}", "error")
                    return redirect(url_for("inventory.create_po_from_single_maintenance", maintenance_event_id=selected_event_id))
                if cost_raw < 0:
                    flash(f"Unit cost cannot be negative (demand {demand_id})", "error")
                    return redirect(url_for("inventory.create_po_from_single_maintenance", maintenance_event_id=selected_event_id))
                unit_cost_by_demand_id[demand_id] = float(cost_raw)

            header_info = {
                "vendor_name": vendor_name,
                "vendor_contact": request.form.get("vendor_contact", "").strip() or None,
                "shipping_cost": request.form.get("shipping_cost", type=float) or 0.0,
                "tax_amount": request.form.get("tax_amount", type=float) or 0.0,
                "notes": request.form.get("notes", "").strip() or None,
                "location_id": location_id,
                "storeroom_id": request.form.get("storeroom_id", type=int),
            }

            logger.info(f"Creating PO from maintenance event {selected_event_id} with {len(selected_demand_ids)} selected demands")
            logger.debug(f"Header info: {header_info}")
            logger.debug(f"Selected demand IDs: {selected_demand_ids}")
            logger.debug(f"Unit costs by demand ID: {unit_cost_by_demand_id}")
            
            po_context = PurchaseOrderFactory.create_from_maintenance_event(
                maintenance_event_id=selected_event_id,
                header_info=header_info,
                created_by_id=current_user.id,
                part_demand_ids=selected_demand_ids,
                unit_cost_by_part_demand_id=unit_cost_by_demand_id,
            )

            # Log PO header details
            po_header = po_context.header
            logger.info(f"PO created successfully - ID: {po_context.purchase_order_id}, PO Number: {po_header.po_number}")
            logger.info(f"PO Header details - Vendor: {po_header.vendor_name}, Status: {po_header.status}, Location ID: {po_header.major_location_id}, Storeroom ID: {po_header.storeroom_id}")
            logger.info(f"PO Header - Shipping: {po_header.shipping_cost}, Tax: {po_header.tax_amount}, Total: {po_header.total_cost}")
            
            # Log PO lines
            po_lines = po_context.lines
            logger.info(f"PO has {len(po_lines)} lines:")
            for line in po_lines:
                logger.info(f"  Line {line.line_number} (ID: {line.id}): Part ID {line.part_id}, Qty: {line.quantity_ordered}, Unit Cost: {line.unit_cost}, Status: {line.status}")
            
            # Commit the transaction to ensure PO is persisted
            try:
                db.session.commit()
                logger.info(f"PO {po_context.purchase_order_id} committed to database")
            except Exception as commit_error:
                logger.error(f"Error committing PO {po_context.purchase_order_id} to database: {commit_error}", exc_info=True)
                db.session.rollback()
                raise

            # Generate redirect URL
            redirect_url = url_for("inventory.purchase_order_view", po_id=po_context.purchase_order_id)
            logger.info(f"Redirecting to: {redirect_url} (PO ID: {po_context.purchase_order_id})")
            
            flash(f"Purchase order {po_context.header.po_number} created successfully", "success")
            return redirect(redirect_url)
        except Exception as e:
            logger.error(f"Error creating PO from maintenance event: {e}", exc_info=True)
            db.session.rollback()
            flash(f"Error creating purchase order: {str(e)}", "error")
            return redirect(url_for("inventory.create_po_from_single_maintenance", maintenance_event_id=selected_event_id))

    def _extract_header_info_from_form():
        """Helper function to extract header info from form data"""
        vendor_name = request.form.get('vendor_name')
        vendor_contact = request.form.get('vendor_contact', '')
        shipping_cost = request.form.get('shipping_cost', type=float) or 0.0
        tax_amount = request.form.get('tax_amount', type=float) or 0.0
        location_id = request.form.get('location_id', type=int)
        expected_delivery_date = request.form.get('expected_delivery_date')
        notes = request.form.get('notes', '')
        
        # Parse expected delivery date
        expected_date = None
        if expected_delivery_date:
            try:
                from datetime import datetime
                expected_date = datetime.strptime(expected_delivery_date, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        return {
            'vendor_name': vendor_name,
            'vendor_contact': vendor_contact,
            'shipping_cost': shipping_cost,
            'tax_amount': tax_amount,
            'expected_delivery_date': expected_date,
            'notes': notes,
            'location_id': location_id
        }

    # Factory Pattern 2: Create PO from Part Demand Lines (cross-event selection)
    SESSION_SELECTED_PART_DEMAND_IDS_KEY = "inventory_po_from_part_demands_selected_ids"

    def _get_selected_part_demand_ids() -> list[int]:
        raw = session.get(SESSION_SELECTED_PART_DEMAND_IDS_KEY, [])
        if not isinstance(raw, list):
            raw = []
        # normalize to ints and de-dupe
        return InventoryPartDemandSelectionService.normalize_selected_ids([str(x) for x in raw])

    def _set_selected_part_demand_ids(ids: list[int]) -> None:
        session[SESSION_SELECTED_PART_DEMAND_IDS_KEY] = ids
        session.modified = True

    def _filters_from_request_args() -> PartDemandFilters:
        return PartDemandFilters(
            part_id=request.args.get("part_id", type=int),
            part_description=(request.args.get("part_description", "") or "").strip() or None,
            maintenance_event_id=request.args.get("maintenance_event_id", type=int),
            asset_id=request.args.get("asset_id", type=int),
            assigned_to_id=request.args.get("assigned_to_id", type=int),
            major_location_id=request.args.get("major_location_id", type=int),
            status=(request.args.get("status", "") or "").strip() or None,
        )

    def _redirect_back_to_part_demands_portal(extra_params: dict | None = None):
        params = dict(request.args)
        if extra_params:
            params.update(extra_params)
        return redirect(url_for("inventory.create_po_from_part_demands", **params))

    @inventory_bp.route("/create-po-from-part-demands", methods=["GET"])
    @login_required
    def create_po_from_part_demands():
        """Portal: select part demand lines, then create a purchase order with per-part pricing confirmation."""
        logger.info(f"Create PO from part demands accessed by {current_user.username}")

        filters = _filters_from_request_args()
        options = InventoryPartDemandSelectionService.get_filter_options()

        # Search results
        part_demands = InventoryPartDemandSelectionService.get_orderable_part_demands(filters)

        # Current selection (queue)
        selected_ids = _get_selected_part_demand_ids()
        selected_demands = InventoryPartDemandSelectionService.get_demands_by_ids(selected_ids)
        parts_summary = InventoryPartDemandSelectionService.build_parts_summary(selected_demands)

        # Header dropdown options
        locations = MajorLocation.query.filter_by(is_active=True).all()
        storerooms = Storeroom.query.order_by(Storeroom.room_name.asc()).all()

        return render_template(
            "inventory/purchase_orders/create_from_part_demands.html",
            filters={
                "part_id": filters.part_id or "",
                "part_description": filters.part_description or "",
                "maintenance_event_id": filters.maintenance_event_id or "",
                "asset_id": filters.asset_id or "",
                "assigned_to_id": filters.assigned_to_id or "",
                "major_location_id": filters.major_location_id or "",
                "status": filters.status or "",
            },
            part_demands=part_demands,
            selected_demands=selected_demands,
            parts_summary=parts_summary,
            status_options=options["status_options"],
            users=options["users"],
            locations=locations,
            storerooms=storerooms,
            major_locations=options["locations"],
        )

    @inventory_bp.route("/create-po-from-part-demands/add", methods=["POST"])
    @login_required
    def create_po_from_part_demands_add():
        ids_to_add = InventoryPartDemandSelectionService.normalize_selected_ids(request.form.getlist("part_demand_ids"))
        if not ids_to_add:
            flash("No part demands selected to add", "warning")
            return _redirect_back_to_part_demands_portal()

        selected = _get_selected_part_demand_ids()
        merged = selected + [i for i in ids_to_add if i not in selected]
        _set_selected_part_demand_ids(merged)
        flash(f"Added {len(ids_to_add)} part demand(s) to selection", "success")
        return _redirect_back_to_part_demands_portal()

    @inventory_bp.route("/create-po-from-part-demands/remove/<int:part_demand_id>", methods=["POST"])
    @login_required
    def create_po_from_part_demands_remove(part_demand_id: int):
        selected = _get_selected_part_demand_ids()
        if part_demand_id in selected:
            selected = [i for i in selected if i != part_demand_id]
            _set_selected_part_demand_ids(selected)
            flash(f"Removed part demand {part_demand_id}", "success")
        return _redirect_back_to_part_demands_portal()

    @inventory_bp.route("/create-po-from-part-demands/clear", methods=["POST"])
    @login_required
    def create_po_from_part_demands_clear():
        _set_selected_part_demand_ids([])
        flash("Cleared selected part demands", "success")
        return _redirect_back_to_part_demands_portal()

    @inventory_bp.route("/create-po-from-part-demands/submit", methods=["POST"])
    @login_required
    def create_po_from_part_demands_submit():
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

        selected_demands = InventoryPartDemandSelectionService.get_demands_by_ids(selected_ids)
        parts_summary = InventoryPartDemandSelectionService.build_parts_summary(selected_demands)

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

        header_info = {
            "vendor_name": vendor_name,
            "vendor_contact": (request.form.get("vendor_contact") or "").strip() or None,
            "shipping_cost": request.form.get("shipping_cost", type=float) or 0.0,
            "tax_amount": request.form.get("tax_amount", type=float) or 0.0,
            "notes": (request.form.get("notes") or "").strip() or None,
            "location_id": location_id,
            "storeroom_id": request.form.get("storeroom_id", type=int),
        }

        try:
            po_context = PurchaseOrderFactory.create_from_part_demand_lines(
                header_info=header_info,
                created_by_id=current_user.id,
                part_demand_ids=selected_ids,
                prices_by_part_id=prices_by_part_id,
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

    # Factory Pattern 3: Create Unlinked Purchase Order
    @inventory_bp.route("/create-unlinked-purchase-order", methods=["GET", "POST"])
    @login_required
    def create_unlinked_purchase_order():
        """Portal: create an unlinked purchase order from self-defined lines."""
        logger.info(f"Create unlinked purchase order accessed by {current_user.username}")

        # Shared form data
        locations = MajorLocation.query.filter_by(is_active=True).all()
        storerooms = Storeroom.query.order_by(Storeroom.room_name.asc()).all()

        if request.method == "GET":
            return render_template(
                "inventory/purchase_orders/create_unlinked.html",
                locations=locations,
                storerooms=storerooms,
            )

        # POST: create unlinked PO
        try:
            vendor_name = (request.form.get("vendor_name") or "").strip()
            if not vendor_name:
                flash("Vendor name is required", "error")
                return redirect(url_for("inventory.create_unlinked_purchase_order"))

            location_id = request.form.get("location_id", type=int)
            if not location_id:
                flash("Location is required", "error")
                return redirect(url_for("inventory.create_unlinked_purchase_order"))

            # Extract header info
            header_info = {
                "vendor_name": vendor_name,
                "vendor_contact": (request.form.get("vendor_contact") or "").strip() or None,
                "shipping_cost": request.form.get("shipping_cost", type=float) or 0.0,
                "tax_amount": request.form.get("tax_amount", type=float) or 0.0,
                "notes": (request.form.get("notes") or "").strip() or None,
                "location_id": location_id,
                "storeroom_id": request.form.get("storeroom_id", type=int),
            }

            # Parse expected delivery date
            expected_delivery_date = request.form.get("expected_delivery_date")
            if expected_delivery_date:
                try:
                    header_info["expected_delivery_date"] = datetime.strptime(
                        expected_delivery_date, "%Y-%m-%d"
                    ).date()
                except ValueError:
                    pass

            # Extract PO lines from form
            # Lines are submitted as arrays: part_id[], quantity[], unit_cost[], etc.
            part_ids = request.form.getlist("part_id[]")
            quantities = request.form.getlist("quantity[]")
            unit_costs = request.form.getlist("unit_cost[]")
            line_notes_list = request.form.getlist("line_notes[]")
            expected_dates_list = request.form.getlist("expected_delivery_date[]")

            if not part_ids:
                flash("At least one line item is required", "error")
                return redirect(url_for("inventory.create_unlinked_purchase_order"))

            # Build po_lines list
            po_lines = []
            for i, part_id_str in enumerate(part_ids):
                try:
                    part_id = int(part_id_str)
                except (ValueError, TypeError):
                    flash(f"Invalid part ID at line {i + 1}", "error")
                    return redirect(url_for("inventory.create_unlinked_purchase_order"))

                try:
                    quantity = float(quantities[i]) if i < len(quantities) else 0.0
                except (ValueError, TypeError):
                    flash(f"Invalid quantity at line {i + 1}", "error")
                    return redirect(url_for("inventory.create_unlinked_purchase_order"))

                try:
                    unit_cost = float(unit_costs[i]) if i < len(unit_costs) else 0.0
                except (ValueError, TypeError):
                    flash(f"Invalid unit cost at line {i + 1}", "error")
                    return redirect(url_for("inventory.create_unlinked_purchase_order"))

                if quantity <= 0:
                    flash(f"Quantity must be greater than 0 at line {i + 1}", "error")
                    return redirect(url_for("inventory.create_unlinked_purchase_order"))

                if unit_cost < 0:
                    flash(f"Unit cost cannot be negative at line {i + 1}", "error")
                    return redirect(url_for("inventory.create_unlinked_purchase_order"))

                line_data = {
                    "part_id": part_id,
                    "quantity_ordered": quantity,
                    "unit_cost": unit_cost,
                    "notes": (line_notes_list[i] if i < len(line_notes_list) else "").strip() or None,
                }

                # Parse expected delivery date for line
                if i < len(expected_dates_list) and expected_dates_list[i]:
                    try:
                        line_data["expected_delivery_date"] = datetime.strptime(
                            expected_dates_list[i], "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        pass

                po_lines.append(line_data)

            # Check submission option
            submission_option = request.form.get("submission_option")
            go_to_linkage_portal = submission_option == "linkage_portal"

            # Create unlinked PO
            logger.info(f"Creating unlinked PO with {len(po_lines)} lines")
            po_context = PurchaseOrderFactory.create_unlinked(
                header_info=header_info,
                po_lines=po_lines,
                created_by_id=current_user.id,
            )

            db.session.commit()
            logger.info(f"Unlinked PO {po_context.purchase_order_id} created successfully")

            flash(
                f"Purchase order {po_context.header.po_number} created successfully",
                "success",
            )

            # Redirect based on submission option
            if go_to_linkage_portal:
                # TODO: Redirect to linkage portal when it's implemented
                # For now, redirect to PO view
                logger.info("User selected linkage portal option (not yet implemented)")
                return redirect(
                    url_for("inventory.purchase_order_view", po_id=po_context.purchase_order_id)
                )
            else:
                # Create unlinked - redirect to PO view
                return redirect(
                    url_for("inventory.purchase_order_view", po_id=po_context.purchase_order_id)
                )

        except ValueError as e:
            logger.error(f"Validation error creating unlinked PO: {e}")
            db.session.rollback()
            flash(f"Error creating purchase order: {str(e)}", "error")
            return redirect(url_for("inventory.create_unlinked_purchase_order"))
        except Exception as e:
            logger.error(f"Error creating unlinked PO: {e}", exc_info=True)
            db.session.rollback()
            flash(f"Error creating purchase order: {str(e)}", "error")
            return redirect(url_for("inventory.create_unlinked_purchase_order"))

    # Purchase Order Edit (new route scheme + backward-compatible alias)
    @inventory_bp.route('/purchase-order/<int:po_id>/edit', methods=['GET', 'POST'])
    @inventory_bp.route('/purchase-orders/<int:po_id>/edit', methods=['GET', 'POST'])
    @login_required
    def purchase_order_edit(po_id):
        """Edit purchase order - add/remove lines"""
        try:
            po_context = PurchaseOrderContext(po_id)
        except Exception as e:
            logger.error(f"Error loading purchase order {po_id}: {e}")
            flash(f'Purchase order {po_id} not found', 'error')
            return redirect(url_for('inventory.purchase_orders_list'))
        
        if po_context.header.status != 'Draft':
            flash('Can only edit draft purchase orders', 'error')
            return redirect(url_for('inventory.purchase_order_view', po_id=po_id))
        
        if request.method == 'GET':
            logger.info(f"Purchase order {po_id} edit form accessed by {current_user.username}")
            
            # Get locations for form
            locations = MajorLocation.query.filter_by(is_active=True).all()
            
            return render_template('inventory/ordering/purchase_order_edit.html',
                                 po_context=po_context,
                                 locations=locations)
        
        # POST - Handle line operations
        action = request.form.get('action')
        
        if action == 'add_line':
            try:
                part_id = request.form.get('part_id', type=int)
                quantity = request.form.get('quantity', type=float)
                unit_cost = request.form.get('unit_cost', type=float)
                expected_date = request.form.get('expected_delivery_date')
                line_notes = request.form.get('line_notes', '')
                
                if not part_id or not quantity or not unit_cost:
                    flash('Part, quantity, and unit cost are required', 'error')
                    return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))
                
                # Parse expected delivery date
                expected_date_obj = None
                if expected_date:
                    try:
                        from datetime import datetime
                        expected_date_obj = datetime.strptime(expected_date, '%Y-%m-%d').date()
                    except ValueError:
                        pass
                
                po_context.add_line(
                    part_id=part_id,
                    quantity=quantity,
                    unit_cost=unit_cost,
                    user_id=current_user.id,
                    expected_date=expected_date_obj,
                    notes=line_notes if line_notes else None
                )
                
                flash('Line added successfully', 'success')
                logger.info(f"User {current_user.username} added line to PO {po_id}")
                
            except Exception as e:
                flash(f'Error adding line: {str(e)}', 'error')
                logger.error(f"Error adding line to PO {po_id}: {e}")
                db.session.rollback()
        
        elif action == 'remove_line':
            try:
                from app.data.inventory.ordering import PurchaseOrderLine
                line_id = request.form.get('line_id', type=int)
                line = PurchaseOrderLine.query.get(line_id)
                
                if not line or line.purchase_order_id != po_id:
                    flash('Line not found', 'error')
                    return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))
                
                db.session.delete(line)
                po_context.calculate_total()
                po_context.header.updated_by_id = current_user.id
                db.session.commit()
                
                flash('Line removed successfully', 'success')
                logger.info(f"User {current_user.username} removed line from PO {po_id}")
                
            except Exception as e:
                flash(f'Error removing line: {str(e)}', 'error')
                logger.error(f"Error removing line from PO {po_id}: {e}")
                db.session.rollback()
        
        elif action == 'update_line':
            try:
                from app.data.inventory.ordering import PurchaseOrderLine
                line_id = request.form.get('line_id', type=int)
                quantity = request.form.get('quantity', type=float)
                unit_cost = request.form.get('unit_cost', type=float)
                
                if not line_id or quantity is None or unit_cost is None:
                    flash('Line ID, quantity, and unit cost are required', 'error')
                    return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))
                
                if quantity <= 0 or unit_cost < 0:
                    flash('Quantity must be greater than 0 and unit cost must be non-negative', 'error')
                    return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))
                
                line = PurchaseOrderLine.query.get(line_id)
                
                if not line or line.purchase_order_id != po_id:
                    flash('Line not found', 'error')
                    return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))
                
                line.quantity_ordered = quantity
                line.unit_cost = unit_cost
                po_context.calculate_total()
                po_context.header.updated_by_id = current_user.id
                db.session.commit()
                
                flash('Line updated successfully', 'success')
                logger.info(f"User {current_user.username} updated line {line_id} in PO {po_id}")
                
            except Exception as e:
                flash(f'Error updating line: {str(e)}', 'error')
                logger.error(f"Error updating line in PO {po_id}: {e}")
                db.session.rollback()
        
        elif action == 'update_header':
            try:
                vendor_name = request.form.get('vendor_name')
                vendor_contact = request.form.get('vendor_contact', '')
                shipping_cost = request.form.get('shipping_cost', type=float) or 0.0
                tax_amount = request.form.get('tax_amount', type=float) or 0.0
                location_id = request.form.get('location_id', type=int)
                expected_delivery_date = request.form.get('expected_delivery_date')
                notes = request.form.get('notes', '')
                
                if not vendor_name:
                    flash('Vendor name is required', 'error')
                    return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))
                
                if not location_id:
                    flash('Location is required', 'error')
                    return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))
                
                po_context.header.vendor_name = vendor_name
                po_context.header.vendor_contact = vendor_contact
                po_context.header.shipping_cost = shipping_cost
                po_context.header.tax_amount = tax_amount
                po_context.header.major_location_id = location_id
                
                if expected_delivery_date:
                    try:
                        from datetime import datetime
                        po_context.header.expected_delivery_date = datetime.strptime(expected_delivery_date, '%Y-%m-%d').date()
                    except ValueError:
                        pass
                
                po_context.header.notes = notes
                po_context.calculate_total()
                po_context.header.updated_by_id = current_user.id
                db.session.commit()
                
                flash('Purchase order updated successfully', 'success')
                logger.info(f"User {current_user.username} updated PO {po_id}")
                
            except Exception as e:
                flash(f'Error updating purchase order: {str(e)}', 'error')
                logger.error(f"Error updating PO {po_id}: {e}")
                db.session.rollback()
        
        return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))

    @inventory_bp.route('/purchase-orders/<int:po_id>/add-part', methods=['POST'])
    @login_required
    def purchase_order_add_part(po_id):
        """Add a part to purchase order - HTMX endpoint"""
        po_context = PurchaseOrderContext(po_id)
        
        if po_context.header.status != 'Draft':
            if request.headers.get('HX-Request'):
                return '<div class="alert alert-danger">Can only add parts to draft purchase orders</div>', 400
            flash('Can only add parts to draft purchase orders', 'error')
            return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))
        
        try:
            # Log incoming request data for debugging
            logger.info(f"Add part request for PO {po_id}: form data = {dict(request.form)}")
            
            part_id = request.form.get('part_id', type=int)
            quantity = request.form.get('quantity', type=float)
            unit_cost = request.form.get('unit_cost', type=float)
            expected_date = request.form.get('expected_delivery_date')
            line_notes = request.form.get('line_notes', '')
            
            logger.info(f"Parsed values: part_id={part_id}, quantity={quantity}, unit_cost={unit_cost}")
            
            # Validate required fields
            if not part_id:
                if request.headers.get('HX-Request'):
                    return '<div class="alert alert-danger">Part ID is required</div>', 400
                flash('Part ID is required', 'error')
                return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))
            
            if not quantity or quantity <= 0:
                if request.headers.get('HX-Request'):
                    return '<div class="alert alert-danger">Valid quantity is required</div>', 400
                flash('Valid quantity is required', 'error')
                return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))
            
            # Always look up the part and use its last_unit_cost if unit_cost is not provided or is 0
            from app.data.core.supply.part_definition import PartDefinition
            part = PartDefinition.query.get(part_id)
            
            if not part:
                if request.headers.get('HX-Request'):
                    return f'<div class="alert alert-danger">Part with ID {part_id} not found</div>', 400
                flash(f'Part with ID {part_id} not found', 'error')
                return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))
            
            # Use part's last_unit_cost if unit_cost is not provided, is 0, or is None
            # This ensures we always try to use the part's stored cost
            if not unit_cost or unit_cost == 0:
                if part.last_unit_cost and part.last_unit_cost > 0:
                    unit_cost = part.last_unit_cost
                    logger.info(f"Using part's last_unit_cost: {unit_cost} for part {part_id} ({part.part_number})")
                else:
                    # If part doesn't have last_unit_cost, use 0.0 (user can update in PO)
                    unit_cost = 0.0
                    logger.info(f"Part {part_id} ({part.part_number}) has no last_unit_cost, using 0.0 (can be updated in PO)")
            
            # Allow 0.0 as a valid cost (user can update it in the purchase order)
            # Only reject if unit_cost is None (which shouldn't happen at this point)
            if unit_cost is None:
                if request.headers.get('HX-Request'):
                    return '<div class="alert alert-danger">Unit cost is required. Please set a cost for this part.</div>', 400
                flash('Unit cost is required. Please set a cost for this part.', 'error')
                return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))
            
            # Parse expected delivery date
            expected_date_obj = None
            if expected_date:
                try:
                    from datetime import datetime
                    expected_date_obj = datetime.strptime(expected_date, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            po_context.add_line(
                part_id=part_id,
                quantity=quantity,
                unit_cost=unit_cost,
                user_id=current_user.id,
                expected_date=expected_date_obj,
                notes=line_notes if line_notes else None
            )
            
            logger.info(f"User {current_user.username} added part {part_id} to PO {po_id}")
            
            # If HTMX request, return success message and trigger page reload
            if request.headers.get('HX-Request'):
                return '<div class="alert alert-success">Part added successfully</div><script>setTimeout(() => window.location.reload(), 500)</script>'
            
            flash('Part added successfully', 'success')
            return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))
            
        except Exception as e:
            logger.error(f"Error adding part to PO {po_id}: {e}")
            db.session.rollback()
            
            if request.headers.get('HX-Request'):
                return f'<div class="alert alert-danger">Error adding part: {str(e)}</div>', 500
            
            flash(f'Error adding part: {str(e)}', 'error')
            return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))

    @inventory_bp.route('/purchase-orders/<int:po_id>/lines/<int:line_id>/update', methods=['POST'])
    @login_required
    def purchase_order_update_line(po_id, line_id):
        """Update line item quantity and unit cost - HTMX endpoint"""
        try:
            po_context = PurchaseOrderContext(po_id)
            
            if po_context.header.status != 'Draft':
                return '<div class="alert alert-danger">Can only edit draft purchase orders</div>', 400
            
            from app.data.inventory.ordering import PurchaseOrderLine
            line = PurchaseOrderLine.query.get(line_id)
            
            if not line or line.purchase_order_id != po_id:
                return '<div class="alert alert-danger">Line not found</div>', 404
            
            quantity = request.form.get('quantity', type=float)
            unit_cost = request.form.get('unit_cost', type=float)
            
            if quantity is None or unit_cost is None:
                return '<div class="alert alert-danger">Quantity and unit cost are required</div>', 400
            
            if quantity <= 0 or unit_cost < 0:
                return '<div class="alert alert-danger">Quantity must be greater than 0 and unit cost must be non-negative</div>', 400
            
            line.quantity_ordered = quantity
            line.unit_cost = unit_cost
            po_context.calculate_total()
            po_context.header.updated_by_id = current_user.id
            db.session.commit()
            
            logger.info(f"User {current_user.username} updated line {line_id} in PO {po_id}")
            
            # Reload the page to update totals
            # Return the updated row HTML with a script to reload
            from flask import render_template
            row_html = render_template('inventory/ordering/_line_item_row.html', 
                                      line=line, 
                                      po_context=po_context)
            # Add script to reload page after a short delay to show the updated row
            return row_html + '<script>setTimeout(() => window.location.reload(), 500)</script>'
            
        except Exception as e:
            logger.error(f"Error updating line {line_id} in PO {po_id}: {e}")
            db.session.rollback()
            return f'<div class="alert alert-danger">Error updating line: {str(e)}</div>', 500

    @inventory_bp.route('/purchase-orders/<int:po_id>/lines/<int:line_id>/edit-form', methods=['GET'])
    @login_required
    def purchase_order_line_edit_form(po_id, line_id):
        """Get edit form for line item - HTMX endpoint"""
        try:
            po_context = PurchaseOrderContext(po_id)
            
            if po_context.header.status != 'Draft':
                return '<div class="alert alert-danger">Can only edit draft purchase orders</div>', 400
            
            from app.data.inventory.ordering import PurchaseOrderLine
            line = PurchaseOrderLine.query.get(line_id)
            
            if not line or line.purchase_order_id != po_id:
                return '<div class="alert alert-danger">Line not found</div>', 404
            
            # Return the edit form row HTML
            from flask import render_template
            return render_template('inventory/ordering/_line_item_edit_row.html', 
                                 line=line, 
                                 po_context=po_context)
            
        except Exception as e:
            logger.error(f"Error loading edit form for line {line_id} in PO {po_id}: {e}")
            return f'<div class="alert alert-danger">Error loading edit form: {str(e)}</div>', 500

    @inventory_bp.route('/purchase-orders/<int:po_id>/submit', methods=['POST'])
    @login_required
    def purchase_order_submit(po_id):
        """Submit purchase order for ordering"""
        try:
            po_context = PurchaseOrderContext(po_id)
            po_context.submit_order(current_user.id)
            
            flash(f'Purchase order {po_context.header.po_number} submitted successfully', 'success')
            logger.info(f"User {current_user.username} submitted PO {po_id}")
            return redirect(url_for('inventory.purchase_order_view', po_id=po_id))
            
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('inventory.purchase_order_view', po_id=po_id))
        except Exception as e:
            flash(f'Error submitting purchase order: {str(e)}', 'error')
            logger.error(f"Error submitting PO {po_id}: {e}")
            db.session.rollback()
            return redirect(url_for('inventory.purchase_order_view', po_id=po_id))

    @inventory_bp.route('/purchase-orders/<int:po_id>/cancel', methods=['POST'])
    @login_required
    def purchase_order_cancel(po_id):
        """Cancel purchase order"""
        try:
            reason = request.form.get('reason', 'No reason provided')
            po_context = PurchaseOrderContext(po_id)
            po_context.cancel_order(reason, current_user.id)
            
            flash(f'Purchase order {po_context.header.po_number} cancelled', 'success')
            logger.info(f"User {current_user.username} cancelled PO {po_id}")
            return redirect(url_for('inventory.purchase_order_view', po_id=po_id))
            
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('inventory.purchase_order_view', po_id=po_id))
        except Exception as e:
            flash(f'Error cancelling purchase order: {str(e)}', 'error')
            logger.error(f"Error cancelling PO {po_id}: {e}")
            db.session.rollback()
            return redirect(url_for('inventory.purchase_order_view', po_id=po_id))

    # Purchase Order Lines Viewer Portal
    @inventory_bp.route('/purchase-order-lines/view')
    @login_required
    def purchase_order_lines_view():
        """View all purchase order lines with filters"""
        logger.info(f"Purchase order lines view accessed by {current_user.username}")
        
        # Parse filters from request
        filters = {
            'status': request.args.get('status'),
            'part_number': request.args.get('part_number', '').strip() or None,
            'part_name': request.args.get('part_name', '').strip() or None,
            'vendor': request.args.get('vendor', '').strip() or None,
            'date_from': None,
            'date_to': None,
            'created_by_id': request.args.get('created_by_id', type=int),
            'part_demand_assigned_to_id': request.args.get('part_demand_assigned_to_id', type=int),
            'event_assigned_to_id': request.args.get('event_assigned_to_id', type=int),
            'asset_id': request.args.get('asset_id', type=int),
            'search_term': request.args.get('search', '').strip() or None,
            'order_by': request.args.get('order_by', 'created_at'),
            'order_direction': request.args.get('order_direction', 'desc'),
            'page': request.args.get('page', 1, type=int)
        }
        
        # Parse date filters
        if request.args.get('date_from'):
            try:
                filters['date_from'] = datetime.strptime(request.args.get('date_from'), '%Y-%m-%d')
            except ValueError:
                pass
        
        if request.args.get('date_to'):
            try:
                filters['date_to'] = datetime.strptime(request.args.get('date_to'), '%Y-%m-%d')
            except ValueError:
                pass
        
        # Build query
        query = PurchaseOrderLineService.build_po_lines_query(
            status=filters['status'],
            part_number=filters['part_number'],
            part_name=filters['part_name'],
            vendor=filters['vendor'],
            date_from=filters['date_from'],
            date_to=filters['date_to'],
            created_by_id=filters['created_by_id'],
            part_demand_assigned_to_id=filters['part_demand_assigned_to_id'],
            event_assigned_to_id=filters['event_assigned_to_id'],
            asset_id=filters['asset_id'],
            search_term=filters['search_term'],
            order_by=filters['order_by'],
            order_direction=filters['order_direction']
        )
        
        # Get paginated results
        po_lines = PurchaseOrderLineService.get_po_lines_with_enhanced_data(
            query,
            page=filters['page'],
            per_page=20
        )
        
        # Get filter options
        filter_options = PurchaseOrderLineService.get_filter_options()
        
        # Get active filters for display
        active_filters = PurchaseOrderLineService.get_active_filters(filters)
        
        # Get assets for asset filter
        assets = Asset.query.filter_by(status='Active').order_by(Asset.name).all()
        
        return render_template('inventory/purchase_orders/po_lines_list.html',
                             po_lines=po_lines,
                             filter_options=filter_options,
                             active_filters=active_filters,
                             assets=assets,
                             filters=filters)

    @inventory_bp.route('/purchase-order-line/<int:po_line_id>/view')
    @login_required
    def purchase_order_line_view(po_line_id):
        """View a single purchase order line detail"""
        logger.info(f"Purchase order line {po_line_id} viewed by {current_user.username}")
        
        po_line = PurchaseOrderLineService.get_po_line_by_id(po_line_id)
        
        if not po_line:
            flash('Purchase order line not found', 'error')
            return redirect(url_for('inventory.purchase_order_lines_view'))
        
        # Get linked part demands with full relationship chain
        # MaintenanceActionSet.asset is the source of truth, not through event
        demand_links = PartDemandPurchaseOrderLink.query.filter_by(
            purchase_order_line_id=po_line_id
        ).options(
            joinedload(PartDemandPurchaseOrderLink.part_demand)
            .joinedload(PartDemand.action)
            .joinedload(Action.maintenance_action_set)
            .joinedload(MaintenanceActionSet.asset),  # Direct relationship - source of truth
            joinedload(PartDemandPurchaseOrderLink.part_demand)
            .joinedload(PartDemand.action)
            .joinedload(Action.maintenance_action_set)
            .joinedload(MaintenanceActionSet.event)  # Load event separately if needed
        ).all()
        
        return render_template('inventory/purchase_orders/po_line_detail.html',
                             po_line=po_line,
                             demand_links=demand_links)

