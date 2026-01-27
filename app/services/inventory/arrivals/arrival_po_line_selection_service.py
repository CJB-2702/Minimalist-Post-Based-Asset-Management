"""app.services.inventory.arrival_po_line_selection_service

Service for the "Create Arrival from Purchase Order Lines" portal.

This service handles:
- Searching for unfulfilled/partially fulfilled PO lines
- Building summaries of selected PO lines
- Validating that lines can be received
"""

from __future__ import annotations

from sqlalchemy.orm import joinedload

from app.data.inventory.purchasing.purchase_order_header import PurchaseOrderHeader
from app.data.inventory.purchasing.purchase_order_line import PurchaseOrderLine
from app.logger import get_logger
from app.services.inventory.purchasing.po_search_service import POSearchFilters, POSearchService

logger = get_logger("asset_management.services.inventory.arrival_po_line_selection")


class ArrivalPOLineSelectionService:
    """Service for selecting PO lines for arrival creation."""

    @staticmethod
    def get_filter_options() -> dict:
        """Return dropdown options used by the portal filter UI."""
        statuses = ["Pending", "Ordered", "Shipped", "Complete", "Cancelled"]
        shared = POSearchService.get_shared_filter_options()

        return {
            "statuses": statuses,
            "users": shared["users"],
            "locations": shared["major_locations"],
            "assets": shared["assets"],
        }

    @staticmethod
    def get_unfulfilled_po_lines(filters: POSearchFilters, *, limit: int = 1000) -> list[PurchaseOrderLine]:
        """
        Get PO lines that are unfulfilled or partially fulfilled.

        We want lines where:
        - quantity_received_total < quantity_ordered (i.e., remaining > 0)
        - Status is Ordered or Shipped (not Complete, Cancelled)
        """
        # Use shared PO search service (query building), then re-fetch by ids with eager loading
        lines = POSearchService.search_po_lines(filters, unfulfilled_only=True, limit=limit)
        return ArrivalPOLineSelectionService.get_lines_by_ids([l.id for l in lines])

    @staticmethod
    def get_lines_by_ids(po_line_ids: list[int]) -> list[PurchaseOrderLine]:
        """Get PO lines by IDs with relationships loaded."""
        if not po_line_ids:
            return []

        lines = (
            PurchaseOrderLine.query.filter(PurchaseOrderLine.id.in_(po_line_ids))
            .options(
                joinedload(PurchaseOrderLine.purchase_order).joinedload(PurchaseOrderHeader.major_location),
                joinedload(PurchaseOrderLine.part),
            )
            .all()
        )

        # Preserve input order
        by_id = {l.id: l for l in lines}
        return [by_id[i] for i in po_line_ids if i in by_id]

    @staticmethod
    def build_lines_summary(selected_lines: list[PurchaseOrderLine]) -> list[dict]:
        """
        Build summary of selected PO lines showing remaining quantities.
        
        Remaining = quantity_ordered - quantity_received_total.
        """
        summary: list[dict] = []
        for line in sorted(selected_lines, key=lambda x: x.id):
            remaining = max(
                0.0,
                float(line.quantity_ordered or 0.0) - float(line.quantity_received_total or 0.0),
            )
            if remaining <= 0:
                continue  # Skip fully fulfilled lines

            part = line.part
            summary.append(
                {
                    "po_line_id": line.id,
                    "po_id": line.purchase_order_id,
                    "po_number": line.purchase_order.po_number if line.purchase_order else f"PO-{line.purchase_order_id}",
                    "part_id": line.part_id,
                    "part_number": part.part_number if part else str(line.part_id),
                    "part_name": part.part_name if part else "",
                    "quantity_ordered": float(line.quantity_ordered or 0.0),
                    "quantity_received_total": float(line.quantity_received_total or 0.0),
                    "remaining_qty": remaining,
                    "unit_cost": float(line.unit_cost or 0.0),
                    "status": line.status,
                }
            )

        return summary

    @staticmethod
    def normalize_selected_ids(raw_ids: list[str]) -> list[int]:
        """Normalize and de-duplicate selected PO line IDs."""
        ids: list[int] = []
        for x in raw_ids:
            try:
                ids.append(int(x))
            except Exception:
                continue
        # de-dupe, stable
        seen: set[int] = set()
        out: list[int] = []
        for i in ids:
            if i not in seen:
                seen.add(i)
                out.append(i)
        return out

    @staticmethod
    def validate_lines_for_receipt(po_line_ids: list[int]) -> tuple[bool, list[str]]:
        """
        Validate that selected lines can be received.

        Returns:
            (is_valid, list_of_error_messages)
        """
        if not po_line_ids:
            return False, ["No PO lines selected"]

        lines = ArrivalPOLineSelectionService.get_lines_by_ids(po_line_ids)
        if len(lines) != len(po_line_ids):
            return False, [f"One or more PO lines not found (requested {len(po_line_ids)}, found {len(lines)})"]

        errors: list[str] = []
        for line in lines:
            remaining = max(
                0.0,
                float(line.quantity_ordered or 0.0) - float(line.quantity_received_total or 0.0),
            )
            if remaining <= 0:
                errors.append(f"PO Line {line.id} is already fully fulfilled")
            if line.status in ("Complete", "Cancelled"):
                errors.append(f"PO Line {line.id} has status '{line.status}' and cannot be received")

        return len(errors) == 0, errors





