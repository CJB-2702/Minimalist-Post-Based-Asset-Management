"""app.services.inventory.arrival_po_line_selection_service

Service for the "Create Arrival from Purchase Order Lines" portal.

This service handles:
- Searching for unfulfilled/partially fulfilled PO lines
- Building summaries of selected PO lines
- Validating that lines can be fully accepted (no partials/rejections for pattern 2)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.data.core.asset_info.asset import Asset
from app.data.core.major_location import MajorLocation
from app.data.core.supply.part_definition import PartDefinition
from app.data.core.user_info.user import User
from app.data.inventory.ordering.purchase_order_header import PurchaseOrderHeader
from app.data.inventory.ordering.purchase_order_line import PurchaseOrderLine
from app.logger import get_logger
from app.services.inventory.purchasing.purchase_order_line_service import PurchaseOrderLineService

logger = get_logger("asset_management.services.inventory.arrival_po_line_selection")


@dataclass(frozen=True)
class POLineFilters:
    status: Optional[str] = None
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    vendor: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    created_by_id: Optional[int] = None
    part_demand_assigned_to_id: Optional[int] = None
    event_assigned_to_id: Optional[int] = None
    asset_id: Optional[int] = None
    search_term: Optional[str] = None


class ArrivalPOLineSelectionService:
    """Service for selecting PO lines for arrival creation (pattern 2)."""

    @staticmethod
    def get_filter_options() -> dict:
        """Return dropdown options used by the portal filter UI."""
        statuses = ["Pending", "Ordered", "Shipped", "Complete", "Cancelled"]
        users = User.query.filter_by(is_active=True).order_by(User.username).all()
        locations = MajorLocation.query.filter_by(is_active=True).order_by(MajorLocation.name).all()
        assets = Asset.query.filter_by(status="Active").order_by(Asset.name).all()

        return {
            "statuses": statuses,
            "users": users,
            "locations": locations,
            "assets": assets,
        }

    @staticmethod
    def get_unfulfilled_po_lines(filters: POLineFilters, *, limit: int = 1000) -> list[PurchaseOrderLine]:
        """
        Get PO lines that are unfulfilled or partially fulfilled.

        For pattern 2, we want lines where:
        - quantity_received_total < quantity_ordered (i.e., remaining > 0)
        - Status is Ordered or Shipped (not Complete, Cancelled)
        """
        from datetime import datetime

        # Build base query using PurchaseOrderLineService
        date_from = None
        date_to = None
        if filters.date_from:
            try:
                date_from = datetime.strptime(filters.date_from, "%Y-%m-%d")
            except ValueError:
                pass
        if filters.date_to:
            try:
                date_to = datetime.strptime(filters.date_to, "%Y-%m-%d")
            except ValueError:
                pass

        query = PurchaseOrderLineService.build_po_lines_query(
            status=filters.status,
            part_number=filters.part_number,
            part_name=filters.part_name,
            vendor=filters.vendor,
            date_from=date_from,
            date_to=date_to,
            created_by_id=filters.created_by_id,
            part_demand_assigned_to_id=filters.part_demand_assigned_to_id,
            event_assigned_to_id=filters.event_assigned_to_id,
            asset_id=filters.asset_id,
            search_term=filters.search_term,
            order_by="created_at",
            order_direction="desc",
        )

        # Filter to only unfulfilled/partially fulfilled lines
        # remaining = quantity_ordered - (quantity_accepted + quantity_rejected) > 0
        query = query.filter(
            PurchaseOrderLine.quantity_ordered > (
                func.coalesce(PurchaseOrderLine.quantity_accepted, 0.0)
                + func.coalesce(PurchaseOrderLine.quantity_rejected, 0.0)
            )
        )

        # Default status filter: only Ordered or Shipped (exclude Complete, Cancelled)
        if not filters.status:
            query = query.filter(PurchaseOrderLine.status.in_(["Ordered", "Shipped"]))

        # Eager load relationships
        query = query.options(
            joinedload(PurchaseOrderLine.purchase_order).joinedload(PurchaseOrderHeader.major_location),
            joinedload(PurchaseOrderLine.part),
        )

        return query.limit(limit).all()

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

        For pattern 2: assumes full acceptance (no rejections), so remaining = quantity_ordered - quantity_received_total.
        """
        summary: list[dict] = []
        for line in sorted(selected_lines, key=lambda x: x.id):
            remaining = max(
                0.0,
                float(line.quantity_ordered or 0.0)
                - (float(line.quantity_accepted or 0.0) + float(line.quantity_rejected or 0.0)),
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
    def validate_lines_for_full_acceptance(po_line_ids: list[int]) -> tuple[bool, list[str]]:
        """
        Validate that selected lines can be fully accepted (pattern 2 constraint).

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
                float(line.quantity_ordered or 0.0)
                - (float(line.quantity_accepted or 0.0) + float(line.quantity_rejected or 0.0)),
            )
            if remaining <= 0:
                errors.append(f"PO Line {line.id} is already fully fulfilled")
            if line.status in ("Complete", "Cancelled"):
                errors.append(f"PO Line {line.id} has status '{line.status}' and cannot be received")

        return len(errors) == 0, errors





