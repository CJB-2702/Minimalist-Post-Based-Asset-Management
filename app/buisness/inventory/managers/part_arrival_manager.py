"""
PartArrivalManager - Business logic for receiving and inspecting parts

Responsibilities:
- Create package headers and part arrivals
- Link arrivals to purchase order lines
- Handle inspection and quality control
- Update purchase order line quantities
- Trigger inventory movements upon acceptance
- Handle partial fulfillment tracking
"""

from pathlib import Path
from datetime import datetime, date
from app import db
from app.data.inventory.base import (
    PackageHeader,
    PartArrival,
    PurchaseOrderLine
)
from app.buisness.core.event_context import EventContext


class PartArrivalManager:
    """Handles receiving and inspection workflow"""
    
    @staticmethod
    def create_package(package_number, location_id, received_by_id, user_id, 
                      tracking_number=None, carrier=None, notes=None):
        """
        Create new package for receiving
        
        Args:
            package_number: Unique package identifier
            location_id: Location where package received
            received_by_id: User who received the package
            user_id: User creating the record
            tracking_number: Carrier tracking number (optional)
            carrier: Shipping carrier (optional)
            notes: Package notes (optional)
            
        Returns:
            PackageHeader object
        """
        # Check for duplicate package number
        existing = PackageHeader.query.filter_by(package_number=package_number).first()
        if existing:
            raise ValueError(f"Package {package_number} already exists")
        
        package = PackageHeader(
            package_number=package_number,
            tracking_number=tracking_number,
            carrier=carrier,
            received_date=date.today(),
            received_by_id=received_by_id,
            major_location_id=location_id,
            notes=notes,
            status='Received',
            created_by_id=user_id
        )
        
        db.session.add(package)
        db.session.commit()
        
        return package
    
    @staticmethod
    def receive_parts(package_id, po_line_id, quantity, condition, user_id, 
                     inspection_notes=None):
        """
        Receive parts into package against PO line
        
        Args:
            package_id: Package header ID
            po_line_id: Purchase order line ID
            quantity: Quantity received
            condition: Condition (Good/Damaged/Mixed)
            user_id: User receiving the parts
            inspection_notes: Initial inspection notes (optional)
            
        Returns:
            PartArrival object
        """
        package = PackageHeader.query.get(package_id)
        if not package:
            raise ValueError(f"Package {package_id} not found")
        
        po_line = PurchaseOrderLine.query.get(po_line_id)
        if not po_line:
            raise ValueError(f"Purchase order line {po_line_id} not found")
        
        # Validate quantity
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        # Create part arrival
        arrival = PartArrival(
            package_header_id=package_id,
            purchase_order_line_id=po_line_id,
            part_id=po_line.part_id,
            quantity_received=quantity,
            condition=condition,
            inspection_notes=inspection_notes,
            received_date=package.received_date,
            status='Pending',
            created_by_id=user_id
        )
        
        db.session.add(arrival)
        
        # Add comment to PO event if exists
        if po_line.purchase_order.event:
            event_context = EventContext(po_line.purchase_order.event_id)
            event_context.add_comment(user_id, f"Received {quantity} of {po_line.part.part_name} in package {package.package_number}")
        
        db.session.commit()
        
        return arrival
    
    @staticmethod
    def inspect_arrival(arrival_id, accepted_qty, rejected_qty, notes, user_id):
        """
        Record inspection results for arrival
        
        Args:
            arrival_id: Part arrival ID
            accepted_qty: Quantity accepted
            rejected_qty: Quantity rejected
            notes: Inspection notes
            user_id: User performing inspection
            
        Returns:
            PartArrival object
        """
        arrival = PartArrival.query.get(arrival_id)
        if not arrival:
            raise ValueError(f"Part arrival {arrival_id} not found")
        
        # Validate quantities
        total = accepted_qty + rejected_qty
        if total != arrival.quantity_received:
            raise ValueError(
                f"Accepted ({accepted_qty}) + Rejected ({rejected_qty}) "
                f"must equal received ({arrival.quantity_received})"
            )
        
        # Update arrival
        arrival.quantity_accepted = accepted_qty
        arrival.quantity_rejected = rejected_qty
        arrival.inspection_notes = notes
        arrival.status = 'Inspected'
        arrival.updated_by_id = user_id
        
        # Add comment to PO event
        po = arrival.purchase_order_line.purchase_order
        if po.event:
            event_context = EventContext(po.event_id)
            event_context.add_comment(user_id, f"Inspection complete: {accepted_qty} accepted, {rejected_qty} rejected")
        
        db.session.commit()
        
        return arrival
    
    @staticmethod
    def accept_arrival(arrival_id, user_id):
        """
        Accept parts into inventory
        
        This triggers:
        1. Update arrival status to Accepted
        2. Update PO line received quantity
        3. Check PO line completion
        4. Trigger InventoryManager.record_arrival()
        5. Create event
        
        Args:
            arrival_id: Part arrival ID
            user_id: User accepting the parts
            
        Returns:
            PartArrival object
        """
        arrival = PartArrival.query.get(arrival_id)
        if not arrival:
            raise ValueError(f"Part arrival {arrival_id} not found")
        
        if not arrival.is_inspected:
            raise ValueError("Parts must be inspected before acceptance")
        
        if arrival.quantity_accepted <= 0:
            raise ValueError("No quantity accepted to add to inventory")
        
        # Update arrival status
        arrival.status = 'Accepted'
        arrival.updated_by_id = user_id
        
        # Update PO line received quantity
        from app.buisness.inventory.managers.purchase_order_manager import PurchaseOrderManager
        PurchaseOrderManager.update_line_received_quantity(
            arrival.purchase_order_line_id,
            arrival.quantity_accepted,
            user_id
        )
        
        # Trigger inventory movement (imported here to avoid circular import)
        from app.buisness.inventory.managers.inventory_manager import InventoryManager
        InventoryManager.record_arrival(arrival_id, user_id)
        
        # Add comment to PO event
        po = arrival.purchase_order_line.purchase_order
        if po.event:
            event_context = EventContext(po.event_id)
            event_context.add_comment(user_id, f"Accepted {arrival.quantity_accepted} units into inventory")
        
        db.session.commit()
        
        return arrival
    
    @staticmethod
    def reject_arrival(arrival_id, reason, user_id):
        """
        Reject parts (no inventory movement)
        
        Args:
            arrival_id: Part arrival ID
            reason: Rejection reason
            user_id: User rejecting the parts
            
        Returns:
            PartArrival object
        """
        arrival = PartArrival.query.get(arrival_id)
        if not arrival:
            raise ValueError(f"Part arrival {arrival_id} not found")
        
        # Update arrival
        arrival.status = 'Rejected'
        arrival.quantity_rejected = arrival.quantity_received
        arrival.quantity_accepted = 0
        arrival.inspection_notes = f"{arrival.inspection_notes or ''}\n\nRejected: {reason}".strip()
        arrival.updated_by_id = user_id
        
        # Add comment to PO event
        po = arrival.purchase_order_line.purchase_order
        if po.event:
            event_context = EventContext(po.event_id)
            event_context.add_comment(user_id, f"Rejected {arrival.quantity_received} units: {reason}")
        
        db.session.commit()
        
        return arrival
    
    @staticmethod
    def process_package(package_id, user_id):
        """
        Mark package as fully processed
        
        Args:
            package_id: Package header ID
            user_id: User processing the package
            
        Returns:
            PackageHeader object
        """
        package = PackageHeader.query.get(package_id)
        if not package:
            raise ValueError(f"Package {package_id} not found")
        
        # Check all arrivals are processed
        pending = PartArrival.query.filter_by(
            package_header_id=package_id,
            status='Pending'
        ).count()
        
        if pending > 0:
            raise ValueError(f"Package has {pending} pending arrivals")
        
        package.status = 'Processed'
        package.updated_by_id = user_id
        
        db.session.commit()
        
        return package
    
    @staticmethod
    def get_pending_inspections(location_id=None):
        """
        Get arrivals needing inspection
        
        Args:
            location_id: Filter by location (optional)
            
        Returns:
            List of PartArrival objects
        """
        query = PartArrival.query.filter_by(status='Pending')
        
        if location_id:
            query = query.join(PackageHeader).filter(
                PackageHeader.major_location_id == location_id
            )
        
        return query.order_by(PartArrival.received_date).all()
    
    @staticmethod
    def get_package_summary(package_id):
        """
        Get summary of package and its arrivals
        
        Args:
            package_id: Package header ID
            
        Returns:
            Dict with package summary
        """
        package = PackageHeader.query.get(package_id)
        if not package:
            return None
        
        arrivals = PartArrival.query.filter_by(package_header_id=package_id).all()
        
        return {
            'package': package.to_dict(),
            'total_arrivals': len(arrivals),
            'pending': len([a for a in arrivals if a.status == 'Pending']),
            'inspected': len([a for a in arrivals if a.status == 'Inspected']),
            'accepted': len([a for a in arrivals if a.status == 'Accepted']),
            'rejected': len([a for a in arrivals if a.status == 'Rejected']),
            'arrivals': [a.to_dict() for a in arrivals]
        }

