"""
Arrival Linkage Manager

Stateless business logic for linking/unlinking part arrivals to PO lines.
Uses many-to-many relationship through ArrivalPurchaseOrderLink.
"""
from __future__ import annotations

from app import db
from app.data.inventory.arrivals.arrival_line import ArrivalLine
from app.data.inventory.arrivals.purchase_order_link import ArrivalPurchaseOrderLink
from app.data.inventory.purchasing.purchase_order_line import PurchaseOrderLine
from app.logger import get_logger

logger = get_logger("asset_management.buisness.inventory.arrivals.linkage_manager")


class ArrivalLinkageManager:
    """
    Stateless manager for arrival linkage operations.
    
    Provides generic link/unlink operations that work from any context.
    All methods are stateless and can be used independently.
    """
    
    def create_link(
        self,
        arrival_line_id: int,
        po_line_id: int,
        quantity_to_link: float,
        user_id: int,
        notes: str | None = None,
    ) -> tuple[bool, str, ArrivalPurchaseOrderLink | None]:
        """
        Create a new link between an arrival line and a PO line.
        
        Args:
            arrival_line_id: ID of the arrival line to link
            po_line_id: ID of the purchase order line to link to
            quantity_to_link: Quantity to link (must be > 0)
            user_id: User performing the action
            notes: Optional notes for the link
            
        Returns:
            (success: bool, message: str, link: ArrivalPurchaseOrderLink | None)
        """
        arrival = ArrivalLine.query.get(arrival_line_id)
        if not arrival:
            return False, "Arrival line not found", None

        po_line = PurchaseOrderLine.query.get(po_line_id)
        if not po_line:
            return False, "Purchase order line not found", None

        success, message, link = self.apply_link(
            arrival=arrival,
            po_line=po_line,
            quantity_to_link=quantity_to_link,
            user_id=user_id,
            notes=notes,
        )
        if not success:
            return False, message, None

        try:
            db.session.commit()
            logger.info(f"Created link between arrival {arrival_line_id} and PO line {po_line_id} (qty: {quantity_to_link}) by user {user_id}")
            return True, f"Successfully linked {quantity_to_link} units to PO line", link
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create link between arrival {arrival_line_id} and PO line {po_line_id}: {e}")
            return False, f"Database error: {str(e)}", None

    def apply_link(
        self,
        *,
        arrival: ArrivalLine,
        po_line: PurchaseOrderLine,
        quantity_to_link: float,
        user_id: int,
        notes: str | None = None,
    ) -> tuple[bool, str, ArrivalPurchaseOrderLink | None]:
        """
        Apply link creation in-session without committing.
        
        This is the primitive used by UI routes (commit/rollback) and also by factories,
        so business validation stays centralized.
        
        Args:
            arrival: ArrivalLine instance
            po_line: PurchaseOrderLine instance
            quantity_to_link: Quantity to link
            user_id: User performing the action
            notes: Optional notes for the link
            
        Returns:
            (success: bool, message: str, link: ArrivalPurchaseOrderLink | None)
        """
        # Validate quantity
        try:
            qty = float(quantity_to_link)
        except (TypeError, ValueError):
            return False, "Invalid quantity", None
        if qty <= 0:
            return False, "quantity_to_link must be > 0", None

        # Validate part IDs match
        if arrival.part_id != po_line.part_id:
            return False, "Part ID mismatch: Arrival and PO line must have the same part", None

        # Check if link already exists
        existing_link = ArrivalPurchaseOrderLink.query.filter_by(
            arrival_line_id=arrival.id,
            purchase_order_line_id=po_line.id
        ).first()
        if existing_link:
            return False, "Link already exists between this arrival and PO line", None

        # Check availability on arrival side
        quantity_available = arrival.quantity_available_for_linking
        if qty > quantity_available:
            return (
                False,
                f"Insufficient quantity available on arrival. Need {qty}, only {quantity_available} available",
                None
            )

        # Check availability on PO line side
        qty_remaining = float(po_line.quantity_ordered or 0.0) - float(po_line.quantity_received_total or 0.0)
        if qty > qty_remaining:
            return False, f"PO line only needs {qty_remaining} more units", None

        # Create link
        link = ArrivalPurchaseOrderLink(
            arrival_line_id=arrival.id,
            purchase_order_line_id=po_line.id,
            quantity_linked=qty,
            notes=notes,
            created_by_id=user_id,
            updated_by_id=user_id,
        )
        db.session.add(link)
        
        po_line.updated_by_id = user_id

        return True, f"Successfully linked {qty} units to PO line", link

    def update_link_quantity(
        self,
        link_id: int,
        new_quantity: float,
        user_id: int,
    ) -> tuple[bool, str]:
        """
        Update the quantity on an existing link.
        
        Args:
            link_id: ID of the link to update
            new_quantity: New quantity to set (must be > 0)
            user_id: User performing the action
            
        Returns:
            (success: bool, message: str)
        """
        link = ArrivalPurchaseOrderLink.query.get(link_id)
        if not link:
            return False, "Link not found"

        # Validate new quantity
        try:
            new_qty = float(new_quantity)
        except (TypeError, ValueError):
            return False, "Invalid quantity"
        if new_qty <= 0:
            return False, "quantity must be > 0"

        arrival = link.arrival_line
        po_line = link.purchase_order_line
        old_qty = float(link.quantity_linked)
        qty_difference = new_qty - old_qty

        # Check if we're increasing the quantity
        if qty_difference > 0:
            # Check availability on arrival side (add back the old quantity)
            quantity_available = arrival.quantity_available_for_linking + old_qty
            if new_qty > quantity_available:
                return (
                    False,
                    f"Insufficient quantity available on arrival. Need {new_qty}, only {quantity_available} available"
                )

            # Check availability on PO line side (add back the old quantity)
            qty_remaining = float(po_line.quantity_ordered or 0.0) - float(po_line.quantity_received_total or 0.0) + old_qty
            if new_qty > qty_remaining:
                return False, f"PO line only needs {qty_remaining} more units"

        # Update link quantity
        link.quantity_linked = new_qty
        link.updated_by_id = user_id
        
        po_line.updated_by_id = user_id

        try:
            db.session.commit()
            logger.info(f"Updated link {link_id} quantity from {old_qty} to {new_qty} by user {user_id}")
            return True, f"Successfully updated link quantity to {new_qty}"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update link {link_id} quantity: {e}")
            return False, f"Database error: {str(e)}"

    def delete_link(
        self,
        link_id: int,
        user_id: int,
    ) -> tuple[bool, str]:
        """
        Delete a link between an arrival line and a PO line.
        
        Args:
            link_id: ID of the link to delete
            user_id: User performing the action
            
        Returns:
            (success: bool, message: str)
        """
        link = ArrivalPurchaseOrderLink.query.get(link_id)
        if not link:
            return False, "Link not found"

        success, message = self.apply_unlink(
            link=link,
            user_id=user_id,
        )
        if not success:
            return False, message

        try:
            db.session.commit()
            logger.info(f"Deleted link {link_id} by user {user_id}")
            return True, "Successfully deleted link"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to delete link {link_id}: {e}")
            return False, f"Database error: {str(e)}"

    def apply_unlink(
        self,
        *,
        link: ArrivalPurchaseOrderLink,
        user_id: int,
    ) -> tuple[bool, str]:
        """
        Apply link deletion in-session without committing.
        
        Args:
            link: ArrivalPurchaseOrderLink instance to delete
            user_id: User performing the action
            
        Returns:
            (success: bool, message: str)
        """
        po_line = link.purchase_order_line
        quantity_linked = float(link.quantity_linked or 0.0)
        
        po_line.updated_by_id = user_id

        # Delete the link
        db.session.delete(link)

        return True, "Successfully unlinked arrival from PO line"

    def get_linkage_info(self, arrival_line_id: int) -> dict | None:
        """
        Get comprehensive linkage information for an arrival line.
        
        Args:
            arrival_line_id: ID of the arrival line
            
        Returns:
            dict with linkage info or None if arrival not found
        """
        arrival = ArrivalLine.query.get(arrival_line_id)
        if not arrival:
            return None
        
        links = arrival.po_line_links.all()
        
        return {
            "arrival_line_id": arrival.id,
            "total_quantity_linked": arrival.total_quantity_linked,
            "quantity_available": arrival.quantity_available_for_linking,
            "links": [
                {
                    "link_id": link.id,
                    "po_line_id": link.purchase_order_line_id,
                    "quantity_linked": link.quantity_linked,
                    "po_number": link.purchase_order_line.purchase_order.po_number if link.purchase_order_line and link.purchase_order_line.purchase_order else None,
                    "notes": link.notes,
                }
                for link in links
            ]
        }

    def validate_linkage(
        self,
        arrival_line_id: int,
        po_line_id: int,
        quantity: float,
    ) -> tuple[bool, str]:
        """
        Validate if a linkage operation would succeed without performing it.
        
        Args:
            arrival_line_id: ID of the arrival line
            po_line_id: ID of the purchase order line
            quantity: Quantity to link
            
        Returns:
            (is_valid: bool, error_message: str)
        """
        arrival = ArrivalLine.query.get(arrival_line_id)
        if not arrival:
            return False, "Arrival line not found"
        
        po_line = PurchaseOrderLine.query.get(po_line_id)
        if not po_line:
            return False, "Purchase order line not found"
        
        # Validate quantity
        try:
            qty = float(quantity)
        except (TypeError, ValueError):
            return False, "Invalid quantity"
        if qty <= 0:
            return False, "quantity must be > 0"
        
        # Validate part IDs match
        if arrival.part_id != po_line.part_id:
            return False, "Part ID mismatch"
        
        # Check if link already exists
        existing_link = ArrivalPurchaseOrderLink.query.filter_by(
            arrival_line_id=arrival_line_id,
            purchase_order_line_id=po_line_id
        ).first()
        if existing_link:
            return False, "Link already exists between this arrival and PO line"
        
        # Check availability on arrival side
        quantity_available = arrival.quantity_available_for_linking
        if qty > quantity_available:
            return False, f"Insufficient quantity available. Need {qty}, only {quantity_available} available"
        
        # Check availability on PO line side
        qty_remaining = po_line.quantity_ordered - po_line.quantity_received_total
        if qty > qty_remaining:
            return False, f"PO line only needs {qty_remaining} more units"
        
        return True, ""

    def get_all_links_for_arrival(self, arrival_line_id: int) -> list[ArrivalPurchaseOrderLink]:
        """
        Get all links for an arrival line.
        
        Args:
            arrival_line_id: ID of the arrival line
            
        Returns:
            List of ArrivalPurchaseOrderLink instances
        """
        return ArrivalPurchaseOrderLink.query.filter_by(
            arrival_line_id=arrival_line_id
        ).all()

    def get_all_links_for_po_line(self, po_line_id: int) -> list[ArrivalPurchaseOrderLink]:
        """
        Get all links for a PO line.
        
        Args:
            po_line_id: ID of the purchase order line
            
        Returns:
            List of ArrivalPurchaseOrderLink instances
        """
        return ArrivalPurchaseOrderLink.query.filter_by(
            purchase_order_line_id=po_line_id
        ).all()
