"""
PurchaseOrderManager - Business logic for purchase orders

Responsibilities:
- Create purchase orders from part demands
- Link part demands to purchase order lines
- Update order status based on arrivals
- Calculate totals and costs
- Generate purchase order events
- Handle order cancellation and modifications
"""

from pathlib import Path
from datetime import datetime, date
from app import db
from app.data.inventory.base import (
    PurchaseOrderHeader,
    PurchaseOrderLine,
    PartDemandPurchaseOrderLine
)
from app.data.core.event_info.event import Event
from app.data.maintenance.base.part_demands import PartDemand
from app.buisness.core.event_context import EventContext


class PurchaseOrderManager:
    """Handles all purchase order business logic"""
    
    @staticmethod
    def create_from_part_demands(part_demands, vendor_info, user_id, location_id=None):
        """
        Create purchase order from maintenance part demands
        
        Args:
            part_demands: List of PartDemand objects or IDs
            vendor_info: Dict with 'name', 'contact', 'shipping_cost', 'tax_amount'
            user_id: User creating the PO
            location_id: Delivery location (optional)
            
        Returns:
            PurchaseOrderHeader object
        """
        # Convert IDs to objects if needed
        if part_demands and isinstance(part_demands[0], int):
            part_demands = [PartDemand.query.get(pd_id) for pd_id in part_demands]
        
        # Group demands by part
        grouped = PurchaseOrderManager.group_demands_by_part(part_demands)
        
        # Generate PO number
        po_number = PurchaseOrderManager._generate_po_number()
        
        # Create PO header
        po_header = PurchaseOrderHeader(
            po_number=po_number,
            vendor_name=vendor_info.get('name'),
            vendor_contact=vendor_info.get('contact'),
            order_date=date.today(),
            expected_delivery_date=vendor_info.get('expected_delivery_date'),
            shipping_cost=vendor_info.get('shipping_cost', 0.0),
            tax_amount=vendor_info.get('tax_amount', 0.0),
            notes=vendor_info.get('notes'),
            major_location_id=location_id,
            status='Draft',
            created_by_id=user_id
        )
        
        db.session.add(po_header)
        db.session.flush()  # Get PO ID
        
        # Create PO lines for each part
        line_number = 1
        for part_id, demands in grouped.items():
            total_quantity = sum(d.quantity_required for d in demands)
            part = demands[0].part
            
            po_line = PurchaseOrderLine(
                purchase_order_id=po_header.id,
                part_id=part_id,
                quantity_ordered=total_quantity,
                unit_cost=part.unit_cost or 0.0,
                line_number=line_number,
                expected_delivery_date=vendor_info.get('expected_delivery_date'),
                status='Pending',
                created_by_id=user_id
            )
            
            db.session.add(po_line)
            db.session.flush()
            
            # Link demands to this line
            for demand in demands:
                PurchaseOrderManager.link_part_demand(
                    po_line.id, demand.id, demand.quantity_required, user_id
                )
            
            line_number += 1
        
        # Calculate total
        po_header.calculate_total()
        
        # Create event for tracking
        event = Event(
            event_type='Purchase Order Created',
            event_date=datetime.utcnow(),
            description=f"Purchase Order {po_number} created for {vendor_info.get('name')}",
            major_location_id=location_id,
            created_by_id=user_id
        )
        db.session.add(event)
        db.session.flush()
        
        po_header.event_id = event.id
        db.session.commit()
        
        return po_header
    
    @staticmethod
    def add_line(po_id, part_id, quantity, unit_cost, user_id, expected_date=None, notes=None):
        """
        Add new line to existing purchase order
        
        Args:
            po_id: Purchase order ID
            part_id: Part ID
            quantity: Quantity to order
            unit_cost: Cost per unit
            user_id: User adding the line
            expected_date: Expected delivery date (optional)
            notes: Line notes (optional)
            
        Returns:
            PurchaseOrderLine object
        """
        po = PurchaseOrderHeader.query.get(po_id)
        if not po:
            raise ValueError(f"Purchase order {po_id} not found")
        
        if not po.is_draft:
            raise ValueError(f"Cannot add lines to non-draft purchase order")
        
        # Get next line number
        max_line = db.session.query(db.func.max(PurchaseOrderLine.line_number))\
            .filter(PurchaseOrderLine.purchase_order_id == po_id).scalar()
        line_number = (max_line or 0) + 1
        
        # Create line
        po_line = PurchaseOrderLine(
            purchase_order_id=po_id,
            part_id=part_id,
            quantity_ordered=quantity,
            unit_cost=unit_cost,
            line_number=line_number,
            expected_delivery_date=expected_date,
            notes=notes,
            status='Pending',
            created_by_id=user_id
        )
        
        db.session.add(po_line)
        
        # Recalculate PO total
        po.calculate_total()
        po.updated_by_id = user_id
        
        db.session.commit()
        
        return po_line
    
    @staticmethod
    def link_part_demand(po_line_id, part_demand_id, quantity, user_id):
        """
        Link part demand to purchase order line
        
        Args:
            po_line_id: Purchase order line ID
            part_demand_id: Part demand ID
            quantity: Quantity allocated from this line
            user_id: User creating the link
            
        Returns:
            PartDemandPurchaseOrderLine object
        """
        link = PartDemandPurchaseOrderLine(
            part_demand_id=part_demand_id,
            purchase_order_line_id=po_line_id,
            quantity_allocated=quantity,
            created_by_id=user_id
        )
        
        db.session.add(link)
        db.session.commit()
        
        return link
    
    @staticmethod
    def submit_order(po_id, user_id):
        """
        Submit purchase order for ordering
        
        Args:
            po_id: Purchase order ID
            user_id: User submitting the order
            
        Returns:
            PurchaseOrderHeader object
        """
        po = PurchaseOrderHeader.query.get(po_id)
        if not po:
            raise ValueError(f"Purchase order {po_id} not found")
        
        if not po.is_draft:
            raise ValueError(f"Purchase order is not in draft status")
        
        if po.lines_count == 0:
            raise ValueError(f"Cannot submit purchase order with no lines")
        
        # Update status
        po.status = 'Submitted'
        po.updated_by_id = user_id
        
        # Add comment to event
        if po.event:
            event_context = EventContext(po.event_id)
            event_context.add_comment(user_id, "Purchase order submitted for ordering")
        
        db.session.commit()
        
        return po
    
    @staticmethod
    def cancel_order(po_id, reason, user_id):
        """
        Cancel purchase order
        
        Args:
            po_id: Purchase order ID
            reason: Cancellation reason
            user_id: User cancelling the order
            
        Returns:
            PurchaseOrderHeader object
        """
        po = PurchaseOrderHeader.query.get(po_id)
        if not po:
            raise ValueError(f"Purchase order {po_id} not found")
        
        if po.is_complete:
            raise ValueError(f"Cannot cancel completed purchase order")
        
        # Update status
        po.status = 'Cancelled'
        po.notes = f"{po.notes or ''}\n\nCancelled: {reason}".strip()
        po.updated_by_id = user_id
        
        # Update all lines
        for line in po.purchase_order_lines:
            line.status = 'Cancelled'
            line.updated_by_id = user_id
        
        # Add comment to event
        if po.event:
            event_context = EventContext(po.event_id)
            event_context.add_comment(user_id, f"Purchase order cancelled: {reason}")
        
        db.session.commit()
        
        return po
    
    @staticmethod
    def update_line_received_quantity(po_line_id, quantity, user_id):
        """
        Update received quantity for a PO line
        
        Args:
            po_line_id: Purchase order line ID
            quantity: Quantity received
            user_id: User updating the quantity
            
        Returns:
            PurchaseOrderLine object
        """
        po_line = PurchaseOrderLine.query.get(po_line_id)
        if not po_line:
            raise ValueError(f"Purchase order line {po_line_id} not found")
        
        # Update quantity
        po_line.update_quantity_received(quantity)
        po_line.updated_by_id = user_id
        
        db.session.commit()
        
        # Check if PO is complete
        PurchaseOrderManager.check_completion_status(po_line.purchase_order_id, user_id)
        
        return po_line
    
    @staticmethod
    def check_completion_status(po_id, user_id):
        """
        Check if purchase order is complete and update status
        
        Args:
            po_id: Purchase order ID
            user_id: User checking status
            
        Returns:
            PurchaseOrderHeader object
        """
        po = PurchaseOrderHeader.query.get(po_id)
        if not po:
            raise ValueError(f"Purchase order {po_id} not found")
        
        if po.is_cancelled or po.is_draft:
            return po
        
        # Check all lines
        all_complete = True
        any_partial = False
        
        for line in po.purchase_order_lines:
            if line.status == 'Cancelled':
                continue
            if not line.is_complete:
                all_complete = False
            if line.is_partial:
                any_partial = True
        
        # Update PO status
        old_status = po.status
        if all_complete:
            po.status = 'Complete'
        elif any_partial:
            po.status = 'Partial'
        
        if old_status != po.status:
            po.updated_by_id = user_id
            
            # Add comment to event
            if po.event:
                event_context = EventContext(po.event_id)
                event_context.add_comment(user_id, f"Purchase order status changed to {po.status}")
        
        db.session.commit()
        
        return po
    
    @staticmethod
    def get_unfulfilled_lines(po_id):
        """
        Get all unfulfilled lines for a purchase order
        
        Args:
            po_id: Purchase order ID
            
        Returns:
            List of PurchaseOrderLine objects
        """
        return PurchaseOrderLine.query.filter(
            PurchaseOrderLine.purchase_order_id == po_id,
            PurchaseOrderLine.status.in_(['Pending', 'Partial'])
        ).all()
    
    @staticmethod
    def get_linked_part_demands(po_id):
        """
        Get all part demands linked to a purchase order
        
        Args:
            po_id: Purchase order ID
            
        Returns:
            List of PartDemand objects
        """
        po = PurchaseOrderHeader.query.get(po_id)
        if not po:
            return []
        
        demands = []
        for line in po.purchase_order_lines:
            demands.extend(line.part_demands)
        
        return demands
    
    @staticmethod
    def group_demands_by_part(part_demands):
        """
        Group part demands by part ID
        
        Args:
            part_demands: List of PartDemand objects
            
        Returns:
            Dict mapping part_id to list of demands
        """
        grouped = {}
        for demand in part_demands:
            if demand.part_id not in grouped:
                grouped[demand.part_id] = []
            grouped[demand.part_id].append(demand)
        
        return grouped
    
    @staticmethod
    def _generate_po_number():
        """
        Generate unique PO number
        
        Returns:
            String PO number
        """
        # Get current date
        today = date.today()
        prefix = f"PO-{today.year}{today.month:02d}"
        
        # Find highest number for this month
        last_po = PurchaseOrderHeader.query.filter(
            PurchaseOrderHeader.po_number.like(f"{prefix}%")
        ).order_by(PurchaseOrderHeader.po_number.desc()).first()
        
        if last_po:
            # Extract number and increment
            try:
                last_num = int(last_po.po_number.split('-')[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1
        
        return f"{prefix}-{next_num:04d}"

