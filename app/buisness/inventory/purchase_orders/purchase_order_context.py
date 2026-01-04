from __future__ import annotations

from app import db
from app.buisness.inventory.status.status_manager import InventoryStatusManager
from app.data.inventory.ordering.purchase_order_header import PurchaseOrderHeader
from app.data.inventory.ordering.purchase_order_line import PurchaseOrderLine


class PurchaseOrderContext:
    """
    Business wrapper around a purchase order.

    Kept intentionally small for the rebuild: routes/UI can compose richer flows later.
    """

    def __init__(self, purchase_order_id: int, *, status_manager: InventoryStatusManager | None = None):
        self.purchase_order_id = purchase_order_id
        self.status_manager = status_manager or InventoryStatusManager()

    @property
    def purchase_order(self) -> PurchaseOrderHeader:
        return PurchaseOrderHeader.query.get_or_404(self.purchase_order_id)

    @property
    def header(self) -> PurchaseOrderHeader:
        """Alias for purchase_order property for template compatibility"""
        return self.purchase_order

    def get_lines(self) -> list[PurchaseOrderLine]:
        return list(self.purchase_order.purchase_order_lines)

    @property
    def lines(self) -> list[PurchaseOrderLine]:
        """Property accessor for lines for template compatibility"""
        return self.get_lines()

    def set_status(self, new_status: str) -> None:
        self.status_manager.update_purchase_order_status(self.purchase_order_id, new_status)

    def mark_shipped(self) -> None:
        self.set_status("Shipped")

    def try_mark_arrived_if_complete(self) -> None:
        po = self.purchase_order
        all_complete = all(line.status == "Complete" for line in po.purchase_order_lines)
        if all_complete:
            self.status_manager.update_purchase_order_status(po.id, "Arrived")

    def calculate_total(self) -> None:
        """
        Calculate and update the total_cost field on the purchase order header.
        
        Total = sum of all line totals + shipping_cost + tax_amount
        
        Handles both committed and uncommitted lines in the session.
        """
        po = self.purchase_order
        
        # Get lines from relationship (for committed lines)
        # Also check session for uncommitted lines
        lines = list(po.purchase_order_lines.all())
        
        # If we have an ID, also check for uncommitted lines in the session
        if po.id:
            # Query the session for any pending lines with this purchase_order_id
            # This handles lines that are added but not yet flushed
            for obj in db.session.new:
                if isinstance(obj, PurchaseOrderLine) and obj.purchase_order_id == po.id:
                    if obj not in lines:
                        lines.append(obj)
        
        subtotal = sum(line.line_total for line in lines)
        
        # Add shipping and tax
        shipping = po.shipping_cost or 0.0
        tax = po.tax_amount or 0.0
        
        po.total_cost = subtotal + shipping + tax

    def submit_order(self, user_id: int) -> None:
        """
        Submit the purchase order for ordering.
        
        Changes status from Draft to Ordered, which will:
        - Validate the status transition
        - Create an event for tracking
        - Cascade status to lines and linked part demands
        
        Args:
            user_id: ID of the user submitting the order
            
        Raises:
            ValueError: If the PO is not in Draft status or has no lines
        """
        po = self.purchase_order
        
        # Validate current status
        if po.status != "Draft":
            raise ValueError(f"Cannot submit purchase order: current status is '{po.status}', must be 'Draft'")
        
        # Validate that the PO has at least one line
        lines = self.get_lines()
        if not lines:
            raise ValueError("Cannot submit purchase order: must have at least one line item")

            
        po.updated_by_id = user_id
        
        # Set status to Ordered (this will validate transition, create event, and cascade to lines/demands)
        self.set_status("Ordered")


