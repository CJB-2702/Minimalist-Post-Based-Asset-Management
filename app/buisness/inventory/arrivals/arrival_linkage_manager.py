"""
Arrival Linkage Manager

Stateless business logic for linking/unlinking part arrivals to PO lines.
"""
from __future__ import annotations

from app import db
from app.data.inventory.arrivals.part_arrival import PartArrival
from app.data.inventory.ordering.purchase_order_line import PurchaseOrderLine
from app.logger import get_logger

logger = get_logger("asset_management.buisness.inventory.arrivals.linkage_manager")


class ArrivalLinkageManager:
    """
    Stateless manager for arrival linkage operations.
    
    Provides generic link/unlink operations that work from any context.
    All methods are stateless and can be used independently.
    """
    
    def link_arrival_to_po_line(
        self,
        part_arrival_id: int,
        po_line_id: int,
        quantity_to_link: float,
        user_id: int,
    ) -> tuple[bool, str]:
        """
        Link a part arrival to a PO line.
        
        Args:
            part_arrival_id: ID of the part arrival to link
            po_line_id: ID of the purchase order line to link to
            quantity_to_link: Quantity to link (must be > 0)
            user_id: User performing the action
            
        Returns:
            (success: bool, message: str)
        """
        # Get arrival
        arrival = PartArrival.query.get(part_arrival_id)
        if not arrival:
            return False, "Part arrival not found"
        
        # Get PO line
        po_line = PurchaseOrderLine.query.get(po_line_id)
        if not po_line:
            return False, "Purchase order line not found"
        
        # Validate part IDs match
        if arrival.part_id != po_line.part_id:
            return False, "Part ID mismatch: Arrival and PO line must have the same part"
        
        # Check if arrival already linked to a different PO line
        if arrival.purchase_order_line_id and arrival.purchase_order_line_id != po_line_id:
            return False, "Arrival is already linked to a different PO line"
        
        # Check availability on arrival side
        quantity_linked = arrival.quantity_linked_to_purchase_order_line or 0.0
        quantity_available = arrival.quantity_received - quantity_linked
        
        if quantity_to_link > quantity_available:
            return False, f"Insufficient quantity available on arrival. Need {quantity_to_link}, only {quantity_available} available"
        
        # Check availability on PO line side
        qty_needed = po_line.quantity_ordered - po_line.quantity_received_total
        if quantity_to_link > qty_needed:
            return False, f"PO line only needs {qty_needed} more units"
        
        # Update arrival
        arrival.purchase_order_line_id = po_line_id
        arrival.quantity_linked_to_purchase_order_line = (arrival.quantity_linked_to_purchase_order_line or 0.0) + quantity_to_link
        arrival.updated_by_id = user_id
        
        # Update PO line accepted quantity
        po_line.quantity_accepted = (po_line.quantity_accepted or 0.0) + quantity_to_link
        po_line.updated_by_id = user_id
        
        try:
            db.session.commit()
            logger.info(f"Linked arrival {part_arrival_id} to PO line {po_line_id} (qty: {quantity_to_link}) by user {user_id}")
            return True, f"Successfully linked {quantity_to_link} units to PO line"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to link arrival {part_arrival_id} to PO line {po_line_id}: {e}")
            return False, f"Database error: {str(e)}"
    
    def unlink_arrival_from_po_line(
        self,
        part_arrival_id: int,
        user_id: int,
    ) -> tuple[bool, str]:
        """
        Unlink a part arrival from its PO line.
        
        Args:
            part_arrival_id: ID of the part arrival to unlink
            user_id: User performing the action
            
        Returns:
            (success: bool, message: str)
        """
        # Find the arrival
        arrival = PartArrival.query.get(part_arrival_id)
        
        if not arrival:
            return False, "Arrival not found"
        
        if not arrival.purchase_order_line_id:
            return False, "Arrival is not linked to any PO line"
        
        # Get the quantity that was linked (to subtract from accepted)
        quantity_linked = arrival.quantity_linked_to_purchase_order_line or 0.0
        po_line_id = arrival.purchase_order_line_id
        
        # Get the PO line to update its accepted quantity
        po_line = PurchaseOrderLine.query.get(po_line_id)
        if po_line:
            # Decrease accepted quantity by the amount that was linked
            po_line.quantity_accepted = max(0.0, (po_line.quantity_accepted or 0.0) - quantity_linked)
            po_line.updated_by_id = user_id
        
        # Unlink
        arrival.purchase_order_line_id = None
        arrival.quantity_linked_to_purchase_order_line = 0.0
        arrival.updated_by_id = user_id
        
        try:
            db.session.commit()
            logger.info(f"Unlinked arrival {part_arrival_id} from PO line {po_line_id} (qty: {quantity_linked}) by user {user_id}")
            return True, "Successfully unlinked arrival from PO line"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to unlink arrival {part_arrival_id}: {e}")
            return False, f"Database error: {str(e)}"
    
    def get_linkage_info(self, part_arrival_id: int) -> dict | None:
        """
        Get current linkage information for a part arrival.
        
        Args:
            part_arrival_id: ID of the part arrival
            
        Returns:
            dict with linkage info or None if arrival not found
        """
        arrival = PartArrival.query.get(part_arrival_id)
        if not arrival:
            return None
        
        return {
            "part_arrival_id": arrival.id,
            "po_line_id": arrival.purchase_order_line_id,
            "quantity_linked": arrival.quantity_linked_to_purchase_order_line or 0.0,
            "quantity_available": arrival.quantity_received - (arrival.quantity_linked_to_purchase_order_line or 0.0),
            "is_linked": arrival.purchase_order_line_id is not None,
        }
    
    def validate_linkage(
        self,
        part_arrival_id: int,
        po_line_id: int,
        quantity: float,
    ) -> tuple[bool, str]:
        """
        Validate if a linkage operation would succeed without performing it.
        
        Args:
            part_arrival_id: ID of the part arrival
            po_line_id: ID of the purchase order line
            quantity: Quantity to link
            
        Returns:
            (is_valid: bool, error_message: str)
        """
        arrival = PartArrival.query.get(part_arrival_id)
        if not arrival:
            return False, "Part arrival not found"
        
        po_line = PurchaseOrderLine.query.get(po_line_id)
        if not po_line:
            return False, "Purchase order line not found"
        
        if arrival.part_id != po_line.part_id:
            return False, "Part ID mismatch"
        
        if arrival.purchase_order_line_id and arrival.purchase_order_line_id != po_line_id:
            return False, "Arrival is already linked to a different PO line"
        
        quantity_linked = arrival.quantity_linked_to_purchase_order_line or 0.0
        quantity_available = arrival.quantity_received - quantity_linked
        
        if quantity > quantity_available:
            return False, f"Insufficient quantity available. Need {quantity}, only {quantity_available} available"
        
        qty_needed = po_line.quantity_ordered - po_line.quantity_received_total
        if quantity > qty_needed:
            return False, f"PO line only needs {qty_needed} more units"
        
        return True, ""

