"""
Purchase Order routes
"""
import json
import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, make_response, send_from_directory
from flask_login import login_required, current_user
from app import db
from app.logger import get_logger
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from app.buisness.inventory.purchasing.purchase_order_context import PurchaseOrderContext
from app.buisness.inventory.purchasing.purchase_order_factory import PurchaseOrderFactory
from app.data.inventory.purchasing import PurchaseOrderHeader, PurchaseOrderLine, PartDemandPurchaseOrderLink
from app.data.maintenance.base.part_demands import PartDemand
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.core.event_info.event import Event
from app.data.core.major_location import MajorLocation
from app.data.inventory.inventory.storeroom import Storeroom
from app.services.inventory.purchasing.purchase_order_line_service import PurchaseOrderLineService
from app.services.inventory.purchasing.po_search_service import POSearchService
from app.data.core.asset_info.asset import Asset
from datetime import datetime

logger = get_logger("asset_management.routes.inventory.purchasing")

# Import inventory_bp from main module
from app.presentation.routes.inventory.main import inventory_bp

# Import po_portal module to register its routes
from . import po_portal

# Purchase Orders Splash/Index (Golden Path-focused)
@inventory_bp.route('/purchase-order')
@login_required
def purchase_orders_index():
    """Landing page for purchase order operations (golden path entry points)."""
    logger.info(f"Purchase orders index accessed by {current_user.username}")
    recent_pos = PurchaseOrderHeader.query.order_by(PurchaseOrderHeader.created_at.desc()).limit(10).all()
    return render_template('inventory/purchase_orders/index.html', recent_pos=recent_pos)

# Purchase Orders List/View
@inventory_bp.route('/purchase-order/view')
@login_required
def purchase_orders_list():
    """List all purchase orders"""
    logger.info(f"Purchase orders list accessed by {current_user.username}")

    # Parse filters (supports query-string prefiltering on page load)
    filters_obj = POSearchService.parse_filters(request.args)
    filters = POSearchService.to_template_dict(filters_obj)

    # Search purchase orders using shared service
    purchase_orders = POSearchService.search_purchase_orders(filters_obj, limit=1000)

    # Compute linkage status (unlinked / partially_linked / fully_linked) for table display.
    # Note: we intentionally don't use "green" for fully linked in the UI (per UX request).
    po_linkage_status_by_id: dict[int, str] = {}
    po_ids = [po.id for po in purchase_orders] if purchase_orders else []
    if po_ids:
        rows = (
            db.session.query(
                PurchaseOrderLine.purchase_order_id.label("po_id"),
                func.coalesce(func.sum(PurchaseOrderLine.quantity_ordered), 0.0).label("qty_ordered"),
                func.coalesce(func.sum(func.coalesce(PartDemandPurchaseOrderLink.quantity_allocated, 0.0)), 0.0).label(
                    "qty_allocated"
                ),
            )
            .outerjoin(
                PartDemandPurchaseOrderLink,
                PartDemandPurchaseOrderLink.purchase_order_line_id == PurchaseOrderLine.id,
            )
            .filter(PurchaseOrderLine.purchase_order_id.in_(po_ids))
            .group_by(PurchaseOrderLine.purchase_order_id)
            .all()
        )

        totals_by_po_id = {int(r.po_id): (float(r.qty_ordered or 0.0), float(r.qty_allocated or 0.0)) for r in rows}
        eps = 1e-6
        for po_id in po_ids:
            qty_ordered, qty_allocated = totals_by_po_id.get(int(po_id), (0.0, 0.0))
            if qty_ordered <= eps or qty_allocated <= eps:
                po_linkage_status_by_id[int(po_id)] = "unlinked"
            elif qty_allocated + eps >= qty_ordered:
                po_linkage_status_by_id[int(po_id)] = "fully_linked"
            else:
                po_linkage_status_by_id[int(po_id)] = "partially_linked"

    shared_options = POSearchService.get_shared_filter_options()
    status_options = ["Draft", "Submitted", "Ordered", "Shipped", "Arrived", "Partial", "Complete", "Cancelled"]

    return render_template(
        "inventory/ordering/purchase_orders_list.html",
        purchase_orders=purchase_orders,
        po_linkage_status_by_id=po_linkage_status_by_id,
        status_options=status_options,
        users=shared_options["users"],
        major_locations=shared_options["major_locations"],
        assets=shared_options["assets"],
        filters=filters,
    )

# Purchase Order Detail View
@inventory_bp.route('/purchase-order/<int:po_id>/view')
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
                
                # Get the next line number (max existing line number + 1, or 1 if no lines)
                existing_lines = PurchaseOrderLine.query.filter_by(purchase_order_id=po_id).all()
                next_line_number = max([line.line_number for line in existing_lines], default=0) + 1
                
                # Create the purchase order line directly
                new_line = PurchaseOrderLine(
                    purchase_order_id=po_id,
                    part_id=part_id,
                    quantity_ordered=float(quantity),
                    unit_cost=float(unit_cost),
                    line_number=next_line_number,
                    status='Draft',
                    expected_delivery_date=expected_date_obj,
                    notes=line_notes if line_notes else None,
                    created_by_id=current_user.id,
                    updated_by_id=current_user.id
                )
                
                db.session.add(new_line)
                db.session.flush()
                
                # Recalculate the total
                po_context.calculate_total()
                po_context.header.updated_by_id = current_user.id
                db.session.commit()
                
                flash('Line added successfully', 'success')
                logger.info(f"User {current_user.username} added line to PO {po_id}")
                
        except Exception as e:
                flash(f'Error adding line: {str(e)}', 'error')
                logger.error(f"Error adding line to PO {po_id}: {e}")
                db.session.rollback()
    
    elif action == 'remove_line':
        try:
                from app.data.inventory.purchasing import PurchaseOrderLine
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
                from app.data.inventory.purchasing import PurchaseOrderLine
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
                other_amount = request.form.get('other_amount', type=float) or 0.0
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
                po_context.header.other_amount = other_amount
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

@inventory_bp.route('/purchase-order/<int:po_id>/add-part', methods=['POST'])
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
        from app.utils.logging_sanitizer import sanitize_form_data
        logger.info(f"Add part request for PO {po_id}: form data = {sanitize_form_data(request.form)}")
        
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
        
        # Get the purchase order to add the line to
        po_header = po_context.header
        
        # Get the next line number (max existing line number + 1, or 1 if no lines)
        existing_lines = PurchaseOrderLine.query.filter_by(purchase_order_id=po_id).all()
        next_line_number = max([line.line_number for line in existing_lines], default=0) + 1
        
        # Create the purchase order line directly
        new_line = PurchaseOrderLine(
                purchase_order_id=po_id,
                part_id=part_id,
                quantity_ordered=float(quantity),
                unit_cost=float(unit_cost),
                line_number=next_line_number,
                status='Draft',
                expected_delivery_date=expected_date_obj,
                notes=line_notes if line_notes else None,
                created_by_id=current_user.id,
                updated_by_id=current_user.id
        )
        
        db.session.add(new_line)
        db.session.flush()
        
        # Recalculate the total
        po_context.calculate_total()
        po_header.updated_by_id = current_user.id
        db.session.commit()
        
        logger.info(f"User {current_user.username} added part {part_id} to PO {po_id}")
        
        # If HTMX request, return updated line items table
        if request.headers.get('HX-Request'):
                # Refresh po_context to get updated lines
                po_context = PurchaseOrderContext(po_id)
                
                response = make_response(render_template(
                    'inventory/ordering/_line_items_table.html',
                    po_context=po_context
                ))
                
                # Trigger success toast
                response.headers['HX-Trigger'] = json.dumps({
                    'showToast': {
                        'message': f'Part {part.part_number} added successfully!',
                        'type': 'success',
                        'title': 'Part Added'
                    }
                })
                
                return response
        
        flash('Part added successfully', 'success')
        return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))
        
    except Exception as e:
        logger.error(f"Error adding part to PO {po_id}: {e}")
        db.session.rollback()
        
        if request.headers.get('HX-Request'):
                return f'<div class="alert alert-danger">Error adding part: {str(e)}</div>', 500
        
    flash(f'Error adding part: {str(e)}', 'error')
    return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))

@inventory_bp.route('/purchase-order/<int:po_id>/lines/<int:line_id>/update', methods=['POST'])
@login_required
def purchase_order_update_line(po_id, line_id):
    """Update line item quantity and unit cost - HTMX endpoint"""
    try:
        po_context = PurchaseOrderContext(po_id)
        
        if po_context.header.status != 'Draft':
                return '<div class="alert alert-danger">Can only edit draft purchase orders</div>', 400
        
        from app.data.inventory.purchasing import PurchaseOrderLine
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
        
        # If HTMX request, return updated line row
        if request.headers.get('HX-Request'):
                # Refresh context to get updated totals
                po_context = PurchaseOrderContext(po_id)
                updated_line = [l for l in po_context.lines if l.id == line_id][0]
                
                response = make_response(render_template(
                    'inventory/ordering/_line_item_row.html',
                    line=updated_line,
                    po_context=po_context
                ))
                
                response.headers['HX-Trigger'] = json.dumps({
                    'showToast': {
                        'message': 'Line item updated successfully!',
                        'type': 'success'
                    },
                    'lineItemUpdated': {'line_id': line_id}
                })
                
                return response
        
        flash('Line item updated successfully', 'success')
        return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))
        
    except Exception as e:
        logger.error(f"Error updating line {line_id} in PO {po_id}: {e}")
        db.session.rollback()
        return f'<div class="alert alert-danger">Error updating line: {str(e)}</div>', 500

# Note: purchase_order_line_edit_form route removed - edit mode now toggles client-side
# in _line_item_row.html without requiring a server round-trip

@inventory_bp.route('/purchase-order/<int:po_id>/lines/<int:line_id>/delete', methods=['POST', 'DELETE'])
@login_required
def purchase_order_line_delete(po_id, line_id):
    """Delete a purchase order line - HTMX endpoint"""
    try:
        po_context = PurchaseOrderContext(po_id)
        
        if po_context.header.status != 'Draft':
                if request.headers.get('HX-Request'):
                    response = make_response('', 400)
                    response.headers['HX-Trigger'] = json.dumps({
                        'showToast': {
                            'message': 'Can only delete from draft purchase orders',
                            'type': 'error'
                        }
                    })
                    return response
                flash('Can only delete from draft purchase orders', 'error')
                return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))
        
        from app.data.inventory.purchasing import PurchaseOrderLine
        line = PurchaseOrderLine.query.get(line_id)
        
        if not line or line.purchase_order_id != po_id:
                if request.headers.get('HX-Request'):
                    response = make_response('', 404)
                    response.headers['HX-Trigger'] = json.dumps({
                        'showToast': {
                            'message': 'Line not found',
                            'type': 'error'
                        }
                    })
                    return response
                flash('Line not found', 'error')
                return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))
        
        db.session.delete(line)
        po_context.calculate_total()
        po_context.header.updated_by_id = current_user.id
        db.session.commit()
        
        logger.info(f"User {current_user.username} deleted line {line_id} from PO {po_id}")
        
        if request.headers.get('HX-Request'):
                # Return empty response with success toast
                response = make_response('', 200)
                response.headers['HX-Trigger'] = json.dumps({
                    'showToast': {
                        'message': 'Line item deleted successfully!',
                        'type': 'success'
                    }
                })
                return response
        
        flash('Line item deleted successfully', 'success')
        return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))
        
    except Exception as e:
        logger.error(f"Error deleting line {line_id} from PO {po_id}: {e}")
        db.session.rollback()
        if request.headers.get('HX-Request'):
                response = make_response('', 500)
                response.headers['HX-Trigger'] = json.dumps({
                    'showToast': {
                        'message': f'Error deleting line item: {str(e)}',
                        'type': 'error'
                    }
                })
                return response
    flash(f'Error deleting line item: {str(e)}', 'error')
    return redirect(url_for('inventory.purchase_order_edit', po_id=po_id))

@inventory_bp.route('/purchase-order/<int:po_id>/submit', methods=['POST'])
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

@inventory_bp.route('/purchase-order/<int:po_id>/cancel', methods=['POST'])
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

