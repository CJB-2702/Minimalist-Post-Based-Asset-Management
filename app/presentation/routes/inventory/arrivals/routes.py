"""
PO Arrival routes
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_required, current_user
from app import db
from app.logger import get_logger
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from app.buisness.inventory.arrivals.part_arrival_context import PartArrivalContext
from app.buisness.inventory.arrivals.package_arrival_context import PackageArrivalContext
from app.buisness.inventory.stock.inventory_manager import InventoryManager
from app.buisness.inventory.status.status_manager import InventoryStatusManager
from app.data.inventory.arrivals import PackageHeader, PartArrival
from app.data.inventory.ordering import PurchaseOrderLine, PurchaseOrderHeader, PartDemandPurchaseOrderLink
from app.data.core.major_location import MajorLocation
from app.data.inventory.inventory.storeroom import Storeroom
from app.services.inventory.arrivals.arrival_po_line_selection_service import (
    ArrivalPOLineSelectionService,
    POLineFilters,
)

logger = get_logger("asset_management.routes.inventory.arrivals")


def register_arrival_routes(inventory_bp):
    """Register all arrival routes to the inventory blueprint"""
    
    # Arrivals Index/Splash Page
    @inventory_bp.route('/arrivals')
    @login_required
    def arrivals_index():
        logger.info(f"Arrivals index accessed by {current_user.username}")
        recent_packages = PackageHeader.query.order_by(PackageHeader.received_date.desc()).limit(10).all()
        return render_template("inventory/arrivals/index.html", recent_packages=recent_packages)

    # Package Arrival Detail View (new scheme + backward-compatible alias)
    @inventory_bp.route('/package-arrival/<int:id>/view')
    @inventory_bp.route('/po-arrival/<int:id>')
    @login_required
    def po_arrival_detail(id):
        """View details of a single package arrival"""
        logger.info(f"PO arrival detail accessed by {current_user.username} for package {id}")
        
        # Get package with eager loading of related data (excluding dynamic relationship)
        package = PackageHeader.query.options(
            joinedload(PackageHeader.major_location),
            joinedload(PackageHeader.storeroom),
            joinedload(PackageHeader.received_by)
        ).get_or_404(id)
        
        # Get all part arrivals for this package with eager loading
        # Since part_arrivals is a dynamic relationship, query PartArrival directly
        part_arrivals = PartArrival.query.filter_by(package_header_id=id).options(
            joinedload(PartArrival.purchase_order_line).joinedload(PurchaseOrderLine.purchase_order),
            joinedload(PartArrival.part),
            joinedload(PartArrival.major_location),
            joinedload(PartArrival.storeroom)
        ).all()
        
        return render_template('inventory/arrivals/view_detail.html',
                             package=package,
                             part_arrivals=part_arrivals)

    # Arrivals List/View (new scheme + backward-compatible alias)
    @inventory_bp.route('/arrivals/view')
    @inventory_bp.route('/po-arrivals')
    @login_required
    def po_arrivals():
        """View and filter past package arrivals"""
        logger.info(f"PO arrivals list accessed by {current_user.username}")
        
        # Get filter parameters
        location_id = request.args.get('location_id', type=int)
        status = request.args.get('status', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        search = request.args.get('search', '').strip()
        
        # Build query
        query = PackageHeader.query
        
        # Apply filters
        if location_id:
            query = query.filter(PackageHeader.major_location_id == location_id)
        if status:
            query = query.filter(PackageHeader.status == status)
        if date_from:
            from datetime import datetime
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                query = query.filter(PackageHeader.received_date >= date_from_obj)
            except ValueError:
                pass
        if date_to:
            from datetime import datetime
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                query = query.filter(PackageHeader.received_date <= date_to_obj)
            except ValueError:
                pass
        if search:
            query = query.filter(
                db.or_(
                    PackageHeader.package_number.ilike(f'%{search}%'),
                    PackageHeader.tracking_number.ilike(f'%{search}%'),
                    PackageHeader.carrier.ilike(f'%{search}%')
                )
            )
        
        # Order by received date (newest first)
        packages = query.order_by(PackageHeader.received_date.desc()).limit(100).all()
        
        # Get locations for filter dropdown
        locations = MajorLocation.query.filter_by(is_active=True).all()
        
        return render_template('inventory/arrivals/view_list.html',
                             packages=packages,
                             locations=locations,
                             selected_location_id=location_id,
                             selected_status=status,
                             date_from=date_from,
                             date_to=date_to,
                             search=search)

    # Package Arrival Edit (inspection/accept/reject + optional direct issue)
    @inventory_bp.route('/package-arrival/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    def package_arrival_edit(id):
        """Edit/inspect a package arrival (accept/reject quantities)."""
        try:
            package = PackageHeader.query.options(
                joinedload(PackageHeader.major_location),
                joinedload(PackageHeader.storeroom),
                joinedload(PackageHeader.received_by),
            ).get_or_404(id)

            part_arrivals = (
                PartArrival.query.filter_by(package_header_id=id)
                .options(
                    joinedload(PartArrival.purchase_order_line).joinedload(PurchaseOrderLine.purchase_order),
                    joinedload(PartArrival.part),
                )
                .order_by(PartArrival.id.asc())
                .all()
            )

            if request.method == "GET":
                return render_template(
                    "inventory/arrivals/edit.html",
                    package=package,
                    part_arrivals=part_arrivals,
                )

            # POST: record inspection for each arrival row
            direct_issue = bool(request.form.get("direct_issue"))
            for arrival in part_arrivals:
                accepted = request.form.get(f"accepted_{arrival.id}", type=float) or 0.0
                rejected = request.form.get(f"rejected_{arrival.id}", type=float) or 0.0
                if accepted == 0.0 and rejected == 0.0:
                    continue
                PartArrivalContext(arrival.id).record_inspection(
                    quantity_accepted=accepted,
                    quantity_rejected=rejected,
                    processed_by_user_id=current_user.id,
                    create_receipt_movement=True,
                )

            db.session.commit()
            flash("Arrival inspection saved successfully", "success")

            if direct_issue:
                return redirect(url_for("inventory.direct_issue_from_po", package_id=id))
            return redirect(url_for("inventory.po_arrival_detail", id=id))

        except Exception as e:
            flash(f"Error saving arrival inspection: {str(e)}", "error")
            logger.error(f"Error saving arrival inspection: {e}", exc_info=True)
            db.session.rollback()
            return redirect(url_for("inventory.po_arrival_detail", id=id))

    # Golden Path: Create Arrival from Purchase Order
    @inventory_bp.route('/arrivals/create-from-po', methods=['GET', 'POST'])
    @login_required
    def arrivals_create_from_po():
        logger.info(f"Arrivals create-from-po accessed by {current_user.username}")

        locations = MajorLocation.query.filter_by(is_active=True).all()
        storerooms = Storeroom.query.order_by(Storeroom.room_name.asc()).all()
        purchase_orders = (
            PurchaseOrderHeader.query.filter(PurchaseOrderHeader.status.in_(["Ordered", "Shipped"]))
            .order_by(PurchaseOrderHeader.created_at.desc())
            .limit(200)
            .all()
        )

        if request.method == "GET":
            return render_template(
                "inventory/arrivals/create_from_po.html",
                purchase_orders=purchase_orders,
                locations=locations,
                storerooms=storerooms,
            )

        try:
            purchase_order_id = request.form.get("purchase_order_id", type=int)
            package_number = (request.form.get("package_number") or "").strip()
            major_location_id = request.form.get("major_location_id", type=int)
            storeroom_id = request.form.get("storeroom_id", type=int)

            if not purchase_order_id:
                flash("Purchase order is required", "error")
                return redirect(url_for("inventory.arrivals_create_from_po"))
            if not package_number:
                flash("Package number is required", "error")
                return redirect(url_for("inventory.arrivals_create_from_po"))
            
            # Check if package number already exists
            existing_package = PackageHeader.query.filter_by(package_number=package_number).first()
            if existing_package:
                flash(f"Package number '{package_number}' already exists. Please use a unique package number.", "error")
                return redirect(url_for("inventory.arrivals_create_from_po"))
            
            if not major_location_id:
                flash("Location is required", "error")
                return redirect(url_for("inventory.arrivals_create_from_po"))
            if not storeroom_id:
                flash("Storeroom is required", "error")
                return redirect(url_for("inventory.arrivals_create_from_po"))

            ctx = PackageArrivalContext.create_for_purchase_order(
                purchase_order_id=purchase_order_id,
                package_number=package_number,
                major_location_id=major_location_id,
                storeroom_id=storeroom_id,
                received_by_id=current_user.id,
                created_by_id=current_user.id,
            )
            # Optional metadata
            pkg = ctx.package
            pkg.tracking_number = (request.form.get("tracking_number") or "").strip() or None
            pkg.carrier = (request.form.get("carrier") or "").strip() or None
            pkg.notes = (request.form.get("notes") or "").strip() or None
            db.session.commit()

            flash(f"Package {pkg.package_number} created. Please record accept/reject quantities.", "success")
            return redirect(url_for("inventory.package_arrival_edit", id=pkg.id))
        except IntegrityError as e:
            logger.error(f"Integrity error creating arrival: {e}", exc_info=True)
            db.session.rollback()
            if "package_number" in str(e.orig).lower():
                flash(f"Package number '{package_number}' already exists. Please use a unique package number.", "error")
            else:
                flash(f"Database error: {str(e)}", "error")
            return redirect(url_for("inventory.arrivals_create_from_po"))
        except Exception as e:
            flash(f"Error creating arrival: {str(e)}", "error")
            logger.error(f"Error creating arrival: {e}", exc_info=True)
            db.session.rollback()
            return redirect(url_for("inventory.arrivals_create_from_po"))

    # Golden Path: Direct Issue accepted parts to Work Order (via linked part demands)
    @inventory_bp.route('/arrivals/direct-issue-from-po')
    @login_required
    def direct_issue_from_po():
        package_id = request.args.get("package_id", type=int)
        if not package_id:
            flash("package_id is required", "error")
            return redirect(url_for("inventory.arrivals_index"))

        try:
            package = PackageHeader.query.get_or_404(package_id)
            arrivals = PartArrival.query.filter_by(package_header_id=package_id).options(
                joinedload(PartArrival.purchase_order_line)
            ).all()

            inv = InventoryManager()
            status_mgr = InventoryStatusManager()

            issued_any = False
            for arrival in arrivals:
                if arrival.status != "Accepted":
                    continue
                po_line = arrival.purchase_order_line
                if po_line is None:
                    continue

                # Issue from unassigned bin at this storeroom/location.
                remaining_to_issue = float(arrival.quantity_received or 0.0)
                if remaining_to_issue <= 0:
                    continue

                links = (
                    PartDemandPurchaseOrderLink.query.filter_by(purchase_order_line_id=po_line.id)
                    .order_by(PartDemandPurchaseOrderLink.id.asc())
                    .all()
                )

                for link in links:
                    if remaining_to_issue <= 0:
                        break
                    qty = min(float(link.quantity_allocated or 0.0), remaining_to_issue)
                    if qty <= 0:
                        continue
                    movement, part_issue = inv.issue_to_part_demand(
                        part_demand_id=link.part_demand_id,
                        storeroom_id=arrival.storeroom_id,
                        major_location_id=arrival.major_location_id,
                        quantity_to_issue=qty,
                        from_location_id=None,
                        from_bin_id=None,
                    )
                    status_mgr.propagate_demand_status_update(link.part_demand_id, "Issued")
                    issued_any = True
                    remaining_to_issue -= qty

            db.session.commit()
            if issued_any:
                flash("Direct issue completed: accepted quantities issued to linked part demands.", "success")
            else:
                flash("Nothing to direct issue (no Accepted arrivals found).", "info")
            return redirect(url_for("inventory.po_arrival_detail", id=package_id))
        except Exception as e:
            flash(f"Error during direct issue: {str(e)}", "error")
            logger.error(f"Error during direct issue: {e}", exc_info=True)
            db.session.rollback()
            return redirect(url_for("inventory.po_arrival_detail", id=package_id))

    # Factory Pattern 2: Create Arrival from Purchase Order Lines
    SESSION_SELECTED_PO_LINE_IDS_KEY = "inventory_arrival_from_po_lines_selected_ids"

    def _get_selected_po_line_ids() -> list[int]:
        raw = session.get(SESSION_SELECTED_PO_LINE_IDS_KEY, [])
        if not isinstance(raw, list):
            raw = []
        return ArrivalPOLineSelectionService.normalize_selected_ids([str(x) for x in raw])

    def _set_selected_po_line_ids(ids: list[int]) -> None:
        session[SESSION_SELECTED_PO_LINE_IDS_KEY] = ids
        session.modified = True

    def _filters_from_request_args() -> POLineFilters:
        return POLineFilters(
            status=request.args.get("status") or None,
            part_number=(request.args.get("part_number") or "").strip() or None,
            part_name=(request.args.get("part_name") or "").strip() or None,
            vendor=(request.args.get("vendor") or "").strip() or None,
            date_from=request.args.get("date_from") or None,
            date_to=request.args.get("date_to") or None,
            created_by_id=request.args.get("created_by_id", type=int),
            part_demand_assigned_to_id=request.args.get("part_demand_assigned_to_id", type=int),
            event_assigned_to_id=request.args.get("event_assigned_to_id", type=int),
            asset_id=request.args.get("asset_id", type=int),
            search_term=(request.args.get("search") or "").strip() or None,
        )

    def _redirect_back_to_po_lines_portal(extra_params: dict | None = None):
        params = dict(request.args)
        if extra_params:
            params.update(extra_params)
        return redirect(url_for("inventory.create_arrival_from_po_lines", **params))

    @inventory_bp.route("/arrivals/create-from-po-lines", methods=["GET"])
    @login_required
    def create_arrival_from_po_lines():
        """Portal: select PO lines, then create a package arrival with full acceptance (no rejections)."""
        logger.info(f"Create arrival from PO lines accessed by {current_user.username}")

        filters = _filters_from_request_args()
        options = ArrivalPOLineSelectionService.get_filter_options()

        # Search results (unfulfilled/partially fulfilled lines)
        po_lines = ArrivalPOLineSelectionService.get_unfulfilled_po_lines(filters)

        # Current selection (queue)
        selected_ids = _get_selected_po_line_ids()
        selected_lines = ArrivalPOLineSelectionService.get_lines_by_ids(selected_ids)
        lines_summary = ArrivalPOLineSelectionService.build_lines_summary(selected_lines)

        # Header dropdown options
        locations = MajorLocation.query.filter_by(is_active=True).all()
        storerooms = Storeroom.query.order_by(Storeroom.room_name.asc()).all()

        return render_template(
            "inventory/arrivals/create_from_po_lines.html",
            filters={
                "status": filters.status or "",
                "part_number": filters.part_number or "",
                "part_name": filters.part_name or "",
                "vendor": filters.vendor or "",
                "date_from": filters.date_from or "",
                "date_to": filters.date_to or "",
                "created_by_id": filters.created_by_id or "",
                "part_demand_assigned_to_id": filters.part_demand_assigned_to_id or "",
                "event_assigned_to_id": filters.event_assigned_to_id or "",
                "asset_id": filters.asset_id or "",
                "search_term": filters.search_term or "",
            },
            po_lines=po_lines,
            selected_lines=selected_lines,
            lines_summary=lines_summary,
            status_options=options["statuses"],
            users=options["users"],
            locations=locations,
            storerooms=storerooms,
            major_locations=options["locations"],
            assets=options["assets"],
        )

    @inventory_bp.route("/arrivals/create-from-po-lines/add", methods=["POST"])
    @login_required
    def create_arrival_from_po_lines_add():
        ids_to_add = ArrivalPOLineSelectionService.normalize_selected_ids(request.form.getlist("po_line_ids"))
        if not ids_to_add:
            flash("No PO lines selected to add", "warning")
            return _redirect_back_to_po_lines_portal()

        selected = _get_selected_po_line_ids()
        merged = selected + [i for i in ids_to_add if i not in selected]
        _set_selected_po_line_ids(merged)
        flash(f"Added {len(ids_to_add)} PO line(s) to selection", "success")
        return _redirect_back_to_po_lines_portal()

    @inventory_bp.route("/arrivals/create-from-po-lines/remove/<int:po_line_id>", methods=["POST"])
    @login_required
    def create_arrival_from_po_lines_remove(po_line_id: int):
        selected = _get_selected_po_line_ids()
        if po_line_id in selected:
            selected = [i for i in selected if i != po_line_id]
            _set_selected_po_line_ids(selected)
            flash(f"Removed PO line {po_line_id}", "success")
        return _redirect_back_to_po_lines_portal()

    @inventory_bp.route("/arrivals/create-from-po-lines/clear", methods=["POST"])
    @login_required
    def create_arrival_from_po_lines_clear():
        _set_selected_po_line_ids([])
        flash("Cleared selected PO lines", "success")
        return _redirect_back_to_po_lines_portal()

    @inventory_bp.route("/arrivals/create-from-po-lines/submit", methods=["POST"])
    @login_required
    def create_arrival_from_po_lines_submit():
        selected_ids = _get_selected_po_line_ids()
        if not selected_ids:
            flash("No PO lines selected", "error")
            return _redirect_back_to_po_lines_portal()

        # Validate lines can be fully accepted
        is_valid, errors = ArrivalPOLineSelectionService.validate_lines_for_full_acceptance(selected_ids)
        if not is_valid:
            for msg in errors[:5]:
                flash(msg, "error")
            if len(errors) > 5:
                flash(f"...and {len(errors) - 5} more validation errors", "error")
            return _redirect_back_to_po_lines_portal()

        package_number = (request.form.get("package_number") or "").strip()
        if not package_number:
            flash("Package number is required", "error")
            return _redirect_back_to_po_lines_portal()

        # Check if package number already exists
        existing_package = PackageHeader.query.filter_by(package_number=package_number).first()
        if existing_package:
            flash(f"Package number '{package_number}' already exists. Please use a unique package number.", "error")
            return _redirect_back_to_po_lines_portal()

        major_location_id = request.form.get("major_location_id", type=int)
        if not major_location_id:
            flash("Location is required", "error")
            return _redirect_back_to_po_lines_portal()

        storeroom_id = request.form.get("storeroom_id", type=int)
        if not storeroom_id:
            flash("Storeroom is required", "error")
            return _redirect_back_to_po_lines_portal()

        try:
            ctx = PackageArrivalContext.create_from_purchase_order_lines(
                po_line_ids=selected_ids,
                package_number=package_number,
                major_location_id=major_location_id,
                storeroom_id=storeroom_id,
                received_by_id=current_user.id,
                created_by_id=current_user.id,
            )

            # Optional metadata
            pkg = ctx.package
            pkg.tracking_number = (request.form.get("tracking_number") or "").strip() or None
            pkg.carrier = (request.form.get("carrier") or "").strip() or None
            pkg.notes = (request.form.get("notes") or "").strip() or None

            db.session.commit()
            _set_selected_po_line_ids([])
            flash(f"Package {pkg.package_number} created successfully. All parts fully accepted.", "success")
            return redirect(url_for("inventory.po_arrival_detail", id=pkg.id))
        except IntegrityError as e:
            logger.error(f"Integrity error creating arrival from PO lines: {e}", exc_info=True)
            db.session.rollback()
            if "package_number" in str(e.orig).lower():
                flash(f"Package number '{package_number}' already exists. Please use a unique package number.", "error")
            else:
                flash(f"Database error: {str(e)}", "error")
            return _redirect_back_to_po_lines_portal()
        except Exception as e:
            logger.error(f"Error creating arrival from PO lines: {e}", exc_info=True)
            db.session.rollback()
            flash(f"Error creating package arrival: {str(e)}", "error")
            return _redirect_back_to_po_lines_portal()

    # Factory Pattern 3: Create Unlinked Arrival
    @inventory_bp.route("/create-unlinked-arrival", methods=["GET", "POST"])
    @login_required
    def create_unlinked_arrival():
        """Portal: create an unlinked package arrival from self-defined part arrivals."""
        logger.info(f"Create unlinked arrival accessed by {current_user.username}")

        # Shared form data
        locations = MajorLocation.query.filter_by(is_active=True).all()
        storerooms = Storeroom.query.order_by(Storeroom.room_name.asc()).all()

        if request.method == "GET":
            return render_template(
                "inventory/arrivals/create_unlinked.html",
                locations=locations,
                storerooms=storerooms,
            )

        # POST: create unlinked arrival
        try:
            package_number = (request.form.get("package_number") or "").strip()
            if not package_number:
                flash("Package number is required", "error")
                return redirect(url_for("inventory.create_unlinked_arrival"))

            # Check if package number already exists
            existing_package = PackageHeader.query.filter_by(package_number=package_number).first()
            if existing_package:
                flash(f"Package number '{package_number}' already exists. Please use a unique package number.", "error")
                return redirect(url_for("inventory.create_unlinked_arrival"))

            major_location_id = request.form.get("major_location_id", type=int)
            if not major_location_id:
                flash("Location is required", "error")
                return redirect(url_for("inventory.create_unlinked_arrival"))

            storeroom_id = request.form.get("storeroom_id", type=int)
            if not storeroom_id:
                flash("Storeroom is required", "error")
                return redirect(url_for("inventory.create_unlinked_arrival"))

            # Extract part arrivals from form
            # Part arrivals are submitted as arrays: part_id[], quantity_received[], arrival_notes[]
            part_ids = request.form.getlist("part_id[]")
            quantities = request.form.getlist("quantity_received[]")
            notes_list = request.form.getlist("arrival_notes[]")

            if not part_ids:
                flash("At least one part arrival is required", "error")
                return redirect(url_for("inventory.create_unlinked_arrival"))

            # Build part_arrivals list
            part_arrivals = []
            for i, part_id_str in enumerate(part_ids):
                try:
                    part_id = int(part_id_str)
                except (ValueError, TypeError):
                    flash(f"Invalid part ID at line {i + 1}", "error")
                    return redirect(url_for("inventory.create_unlinked_arrival"))

                try:
                    quantity = float(quantities[i]) if i < len(quantities) else 0.0
                except (ValueError, TypeError):
                    flash(f"Invalid quantity at line {i + 1}", "error")
                    return redirect(url_for("inventory.create_unlinked_arrival"))

                if quantity <= 0:
                    flash(f"Quantity must be greater than 0 at line {i + 1}", "error")
                    return redirect(url_for("inventory.create_unlinked_arrival"))

                arrival_data = {
                    "part_id": part_id,
                    "quantity_received": quantity,
                    "inspection_notes": (notes_list[i] if i < len(notes_list) else "").strip() or None,
                }

                part_arrivals.append(arrival_data)

            # Create unlinked arrival
            logger.info(f"Creating unlinked arrival with {len(part_arrivals)} part arrivals")
            ctx = PackageArrivalContext.create_unlinked(
                package_number=package_number,
                major_location_id=major_location_id,
                storeroom_id=storeroom_id,
                received_by_id=current_user.id,
                part_arrivals=part_arrivals,
                created_by_id=current_user.id,
                carrier=(request.form.get("carrier") or "").strip() or None,
                tracking_number=(request.form.get("tracking_number") or "").strip() or None,
                notes=(request.form.get("notes") or "").strip() or None,
            )

            db.session.commit()
            logger.info(f"Unlinked arrival {ctx.package_header_id} created successfully")

            flash(
                f"Package {ctx.package.package_number} created successfully. All parts accepted and added to inventory.",
                "success",
            )

            return redirect(url_for("inventory.po_arrival_detail", id=ctx.package_header_id))

        except ValueError as e:
            logger.error(f"Validation error creating unlinked arrival: {e}")
            db.session.rollback()
            flash(f"Error creating arrival: {str(e)}", "error")
            return redirect(url_for("inventory.create_unlinked_arrival"))
        except IntegrityError as e:
            logger.error(f"Integrity error creating unlinked arrival: {e}", exc_info=True)
            db.session.rollback()
            if "package_number" in str(e.orig).lower():
                flash(f"Package number '{package_number}' already exists. Please use a unique package number.", "error")
            else:
                flash(f"Database error: {str(e)}", "error")
            return redirect(url_for("inventory.create_unlinked_arrival"))
        except Exception as e:
            logger.error(f"Error creating unlinked arrival: {e}", exc_info=True)
            db.session.rollback()
            flash(f"Error creating arrival: {str(e)}", "error")
            return redirect(url_for("inventory.create_unlinked_arrival"))

