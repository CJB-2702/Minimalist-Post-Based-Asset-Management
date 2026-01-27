"""app.services.inventory.arrivals.arrival_po_line_finder_service

Service for finding purchase order lines that can be linked to arrivals.
"""

from __future__ import annotations

from app.data.inventory.purchasing.purchase_order_header import PurchaseOrderHeader
from app.data.inventory.purchasing.purchase_order_line import PurchaseOrderLine
from app.logger import get_logger

logger = get_logger("asset_management.services.inventory.arrivals.po_line_finder")


class ArrivalPOLineFinderService:
    """Service for finding PO lines that can be linked to arrivals."""

    @staticmethod
    def qty_needed_on_po_line(po_line: PurchaseOrderLine) -> float:
        """Calculate the quantity still needed on a PO line."""
        return float(po_line.quantity_ordered or 0.0) - float(po_line.quantity_received_total or 0.0)

    @staticmethod
    def find_fully_linkable_po_line(
        *,
        part_id: int,
        quantity_to_receive: float,
        major_location_id: int | None = None,
    ) -> PurchaseOrderLine | None:
        """
        Find a PO line that can absorb the full incoming quantity.

        We intentionally only auto-link when the PO line can take the entire quantity,
        to avoid creating mixed linked/unlinked quantities on the same arrival record.
        """
        if quantity_to_receive <= 0:
            return None

        query = PurchaseOrderLine.query.filter(
            PurchaseOrderLine.part_id == part_id,
            PurchaseOrderLine.status.in_(["Pending", "Ordered", "Shipped"]),
        )
        if major_location_id:
            # Filter by PO header location for better matching
            query = query.join(PurchaseOrderHeader).filter(
                PurchaseOrderHeader.major_location_id == major_location_id
            )

        # Prefer older lines first for determinism
        candidate_lines = query.order_by(PurchaseOrderLine.id.asc()).all()
        for line in candidate_lines:
            if ArrivalPOLineFinderService._qty_needed_on_po_line(line) >= quantity_to_receive:
                return line
        return None

    @staticmethod
    def find_linkable_po_lines(
        *,
        part_id: int,
        quantity_to_receive: float,
        major_location_id: int | None = None,
    ) -> list[PurchaseOrderLine]:
        """
        Find PO lines that can absorb quantities from the incoming arrival.

        Returns a list of PO lines that can be linked, ordered by preference.
        """
        if quantity_to_receive <= 0:
            return []

        query = PurchaseOrderLine.query.filter(
            PurchaseOrderLine.part_id == part_id,
            PurchaseOrderLine.status.in_(["Pending", "Ordered", "Shipped"]),
        )
        if major_location_id:
            # Filter by PO header location for better matching
            query = query.join(PurchaseOrderHeader).filter(
                PurchaseOrderHeader.major_location_id == major_location_id
            )

        # Prefer older lines first for determinism
        candidate_lines = query.order_by(PurchaseOrderLine.id.asc()).all()
        
        # Return lines that have remaining capacity
        linkable_lines = []
        for line in candidate_lines:
            if ArrivalPOLineFinderService.qty_needed_on_po_line(line) > 0:
                linkable_lines.append(line)
        
        return linkable_lines
