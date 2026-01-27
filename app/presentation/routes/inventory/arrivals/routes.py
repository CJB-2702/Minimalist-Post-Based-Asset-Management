"""
PO Arrival routes
"""
from collections import defaultdict
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.logger import get_logger
from sqlalchemy import func, case
from app.buisness.inventory.arrivals.arrival_context import ArrivalContext
from app.data.inventory.arrivals import ArrivalHeader, ArrivalLine
from app.data.core.major_location import MajorLocation
from app.services.inventory.arrivals.arrival_linkage_portal import ArrivalLinkagePortal

logger = get_logger("asset_management.routes.inventory.arrivals")

# Import inventory_bp from main module
from app.presentation.routes.inventory.main import inventory_bp

# Import create-arrival routes to register them
from . import create_arrival  # noqa: F401

# Arrivals Index/Splash Page
@inventory_bp.route('/arrivals')
@login_required
def arrivals_index():
    logger.info(f"Arrivals index accessed by {current_user.username}")
    recent_packages = ArrivalHeader.query.order_by(ArrivalHeader.received_date.desc()).limit(10).all()
    return render_template("inventory/arrivals/index.html", recent_packages=recent_packages)

    # Package Arrival Detail View (new scheme + backward-compatible alias)
@inventory_bp.route('/package-arrival/<int:id>/view')
@inventory_bp.route('/po-arrival/<int:id>')
@login_required
def po_arrival_detail(id):
    """View details of a single package arrival"""
    logger.info(f"PO arrival detail accessed by {current_user.username} for package {id}")
    
    # Use ArrivalContext to get package and part arrivals with eager loading
    arrival_context = ArrivalContext(id, eager_load=True)
    package = arrival_context.get_package_with_relationships()
    part_arrivals = arrival_context.get_part_arrivals_with_relationships()
    
    # Build arrival lines summary grouped by part_id (similar to lines_summary in create-arrival)
    arrival_summary = []
    part_groups = defaultdict(list)
    
    # Group arrival lines by part_id
    for arrival in part_arrivals:
        part_groups[arrival.part_id].append(arrival)
    
    # Collect all unique PO headers and lines for extended display
    po_headers_dict = {}  # po_id -> full PO header data
    po_lines_dict = {}  # po_line_id -> full PO line data
    
    # Build summary for each part group
    for part_id, arrivals in part_groups.items():
        head_arrival = arrivals[0]
        part = head_arrival.part
        
        # Calculate totals
        total_received = sum(a.quantity_received for a in arrivals)
        total_linked = sum(a.total_quantity_linked for a in arrivals)
        total_unlinked = total_received - total_linked
        
        # Collect all PO line links for this part group
        # Handle cases where arrival lines might not be linked to POs
        po_line_details = []
        for arrival in arrivals:
            # Safely get PO line links - handle case where relationship might not exist
            try:
                links = arrival.po_line_links.all() if hasattr(arrival, 'po_line_links') else []
            except Exception:
                links = []
            
            for link in links:
                # Safely check if link has required relationships
                if not link:
                    continue
                    
                try:
                    po_line = link.purchase_order_line if hasattr(link, 'purchase_order_line') else None
                except Exception:
                    po_line = None
                    
                if not po_line:
                    continue
                    
                try:
                    po = po_line.purchase_order if hasattr(po_line, 'purchase_order') else None
                except Exception:
                    po = None
                    
                if not po:
                    continue
                
                # Store full PO header data
                if po.id not in po_headers_dict:
                    try:
                        # Get event info - Event has event_type and description, not name
                        event_info = None
                        if po.event:
                            if hasattr(po.event, 'event_type'):
                                event_info = f"{po.event.event_type}"
                                if hasattr(po.event, 'description') and po.event.description:
                                    event_info += f": {po.event.description[:50]}"
                            elif hasattr(po.event, 'description'):
                                event_info = po.event.description[:50] if po.event.description else None
                        
                        po_headers_dict[po.id] = {
                            'id': po.id,
                            'po_number': getattr(po, 'po_number', 'N/A'),
                            'vendor_name': getattr(po, 'vendor_name', 'N/A'),
                            'vendor_contact': getattr(po, 'vendor_contact', None),
                            'order_date': getattr(po, 'order_date', None),
                            'expected_delivery_date': getattr(po, 'expected_delivery_date', None),
                            'status': getattr(po, 'status', 'Unknown'),
                            'shipping_cost': float(getattr(po, 'shipping_cost', 0) or 0.0),
                            'tax_amount': float(getattr(po, 'tax_amount', 0) or 0.0),
                            'other_amount': float(getattr(po, 'other_amount', 0) or 0.0),
                            'total_cost': float(getattr(po, 'total_cost', 0) or 0.0),
                            'notes': getattr(po, 'notes', None),
                            'major_location': po.major_location.name if (hasattr(po, 'major_location') and po.major_location) else None,
                            'storeroom': po.storeroom.room_name if (hasattr(po, 'storeroom') and po.storeroom) else None,
                            'event': event_info,
                            'created_by': po.created_by.username if (hasattr(po, 'created_by') and po.created_by) else None,
                            'created_date': getattr(po, 'created_date', None),
                            'updated_by': po.updated_by.username if (hasattr(po, 'updated_by') and po.updated_by) else None,
                            'updated_date': getattr(po, 'updated_date', None),
                        }
                    except Exception as e:
                        logger.warning(f"Error extracting PO header data for PO {po.id}: {e}")
                        continue
                
                # Store full PO line data
                if po_line.id not in po_lines_dict:
                    try:
                        po_lines_dict[po_line.id] = {
                            'id': po_line.id,
                            'po_id': po.id,
                            'line_number': getattr(po_line, 'line_number', 0),
                            'part_id': getattr(po_line, 'part_id', None),
                            'part_number': po_line.part.part_number if (hasattr(po_line, 'part') and po_line.part) else None,
                            'part_name': po_line.part.part_name if (hasattr(po_line, 'part') and po_line.part) else None,
                            'quantity_ordered': float(getattr(po_line, 'quantity_ordered', 0) or 0.0),
                            'unit_cost': float(getattr(po_line, 'unit_cost', 0) or 0.0),
                            'line_total': float(getattr(po_line, 'line_total', 0) or 0.0),
                            'expected_delivery_date': getattr(po_line, 'expected_delivery_date', None),
                            'notes': getattr(po_line, 'notes', None),
                            'status': getattr(po_line, 'status', 'Unknown'),
                            'quantity_received_total': float(getattr(po_line, 'quantity_received_total', 0) or 0.0),
                            'total_quantity_linked_from_arrivals': float(getattr(po_line, 'total_quantity_linked_from_arrivals', 0) or 0.0),
                            'is_fake_for_inventory_adjustments': getattr(po_line, 'is_fake_for_inventory_adjustments', False),
                            'created_by': po_line.created_by.username if (hasattr(po_line, 'created_by') and po_line.created_by) else None,
                            'created_date': getattr(po_line, 'created_date', None),
                            'updated_by': po_line.updated_by.username if (hasattr(po_line, 'updated_by') and po_line.updated_by) else None,
                            'updated_date': getattr(po_line, 'updated_date', None),
                        }
                    except Exception as e:
                        logger.warning(f"Error extracting PO line data for line {po_line.id}: {e}")
                        continue
                
                try:
                    po_line_details.append({
                        'arrival_line_id': arrival.id,
                        'link_id': link.id if hasattr(link, 'id') else None,
                        'po_line_id': po_line.id,
                        'po_id': po.id,
                        'po_number': getattr(po, 'po_number', 'N/A'),
                        'line_number': getattr(po_line, 'line_number', 0),
                        'quantity_linked': float(getattr(link, 'quantity_linked', 0) or 0.0),
                        'quantity_ordered': float(getattr(po_line, 'quantity_ordered', 0) or 0.0),
                        'unit_cost': float(getattr(po_line, 'unit_cost', 0) or 0.0),
                        'status': getattr(po_line, 'status', 'Unknown'),
                        'vendor_name': getattr(po, 'vendor_name', 'N/A'),
                        'link_notes': getattr(link, 'notes', None),
                    })
                except Exception as e:
                    logger.warning(f"Error creating PO line detail entry: {e}")
                    continue
        
        arrival_summary.append({
            'part_id': part_id,
            'part_number': part.part_number if part else str(part_id),
            'part_name': part.part_name if part else '',
            'total_received': total_received,
            'total_linked': total_linked,
            'total_unlinked': total_unlinked,
            'arrival_lines': arrivals,
            'po_line_details': po_line_details,
            'status': head_arrival.status,
            'condition': head_arrival.condition,
            'received_date': head_arrival.received_date,
            'location': head_arrival.major_location.name if head_arrival.major_location else 'N/A',
            'storeroom': head_arrival.storeroom.room_name if head_arrival.storeroom else 'N/A',
        })
    
    # Count linked PO lines for template logic
    po_link_count = sum(len(item['po_line_details']) for item in arrival_summary)
    
    # Convert dicts to lists for template, sorted for better display
    po_headers_list = sorted(po_headers_dict.values(), key=lambda x: (x['po_number'], x['id']))
    po_lines_list = sorted(po_lines_dict.values(), key=lambda x: (x['po_id'], x['line_number']))
    
    return render_template('inventory/arrivals/view_detail.html',
                         package=package,
                         part_arrivals=part_arrivals,
                         arrival_summary=arrival_summary,
                         po_link_count=po_link_count,
                         po_headers=po_headers_list,
                         po_lines=po_lines_list)

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
    query = ArrivalHeader.query
    
    # Apply filters
    if location_id:
        query = query.filter(ArrivalHeader.major_location_id == location_id)
    if status:
        query = query.filter(ArrivalHeader.status == status)
    if date_from:
        from datetime import datetime
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(ArrivalHeader.received_date >= date_from_obj)
        except ValueError:
            pass
    if date_to:
        from datetime import datetime
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(ArrivalHeader.received_date <= date_to_obj)
        except ValueError:
            pass
    if search:
        query = query.filter(
        db.or_(
                ArrivalHeader.package_number.ilike(f'%{search}%'),
                ArrivalHeader.tracking_number.ilike(f'%{search}%'),
                ArrivalHeader.carrier.ilike(f'%{search}%')
        )
    )
    
    # Order by received date (newest first)
    packages = query.order_by(ArrivalHeader.received_date.desc()).limit(100).all()

    # Linkage status per package: use service layer to calculate using new many-to-many relationship
    package_ids = [p.id for p in packages] if packages else []
    package_linkage_status_by_id = ArrivalLinkagePortal.calculate_package_linkage_statuses(package_ids)
    
    # Get locations for filter dropdown
    locations = MajorLocation.query.filter_by(is_active=True).all()
    
    return render_template('inventory/arrivals/view_list.html',
                         packages=packages,
                         package_linkage_status_by_id=package_linkage_status_by_id,
                         locations=locations,
                         selected_location_id=location_id,
                         selected_status=status,
                         date_from=date_from,
                         date_to=date_to,
                         search=search)

@inventory_bp.route('/package-arrival/<int:id>/edit', methods=['GET'])
@login_required
def package_arrival_edit(id):
    """Edit page - to be implemented later."""
    return render_template("inventory/arrivals/edit.html")

    # Arrival creation routes moved to `arrivals/create_arrival.py`

