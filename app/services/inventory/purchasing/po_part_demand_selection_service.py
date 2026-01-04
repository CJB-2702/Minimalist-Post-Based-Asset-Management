"""app.services.inventory.po_part_demand_selection_service

Inventory-side service for the "Create PO from Part Demand Lines" portal.

Key rule: maintenance services MUST NOT import inventory.
This module is allowed to import maintenance services and extend them.

This service is read-heavy (search + summarization) and keeps the route thin.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import joinedload

from app import db
from app.data.core.major_location import MajorLocation
from app.data.core.supply.part_definition import PartDefinition
from app.data.core.user_info.user import User
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.maintenance.base.part_demands import PartDemand
from app.logger import get_logger
from app.services.maintenance.part_demand_service import PartDemandService

logger = get_logger("asset_management.services.inventory.po_part_demand_selection")


ORDERABLE_PART_DEMAND_STATUSES: set[str] = {
    "Planned",
    "Pending Manager Approval",
    "Pending Inventory Approval",
}

BLOCKED_PART_DEMAND_STATUSES: set[str] = {
    "Issued",
    "Ordered",
    "Installed",
}


@dataclass(frozen=True)
class PartDemandFilters:
    part_id: Optional[int] = None
    part_description: Optional[str] = None
    maintenance_event_id: Optional[int] = None
    asset_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    major_location_id: Optional[int] = None
    status: Optional[str] = None


class InventoryPartDemandSelectionService(PartDemandService):
    """Inventory-side facade over maintenance PartDemandService."""

    @staticmethod
    def get_filter_options() -> dict:
        """Return dropdown options used by the portal filter UI."""
        # Status options: only show statuses relevant to ordering + any existing statuses.
        statuses = db.session.query(PartDemand.status).distinct().all()
        status_options = sorted({s[0] for s in statuses if s[0]})

        users = User.query.filter_by(is_active=True).order_by(User.username).all()
        locations = MajorLocation.query.filter_by(is_active=True).order_by(MajorLocation.name).all()

        return {
            "status_options": status_options,
            "users": users,
            "locations": locations,
        }

    @staticmethod
    def get_orderable_part_demands(filters: PartDemandFilters, *, limit: int = 1000) -> list[PartDemand]:
        """Search part demands using the maintenance filter semantics, but default to orderable demands."""
        demands = PartDemandService.get_filtered_part_demands(
            part_id=filters.part_id,
            part_description=filters.part_description,
            maintenance_event_id=filters.maintenance_event_id,
            asset_id=filters.asset_id,
            assigned_to_id=filters.assigned_to_id,
            major_location_id=filters.major_location_id,
            status=filters.status,
            limit=limit,
        )

        # If a status filter is explicitly provided, respect it.
        if filters.status:
            return demands

        # Otherwise, default to orderable statuses and exclude blocked statuses.
        filtered = [
            d for d in demands
            if (d.status in ORDERABLE_PART_DEMAND_STATUSES) and (d.status not in BLOCKED_PART_DEMAND_STATUSES)
        ]
        return filtered

    @staticmethod
    def get_demands_by_ids(part_demand_ids: list[int]) -> list[PartDemand]:
        if not part_demand_ids:
            return []

        demands = (
            PartDemand.query.filter(PartDemand.id.in_(part_demand_ids))
            .options(
                joinedload(PartDemand.part),
                joinedload(PartDemand.requested_by),
                joinedload(PartDemand.action).joinedload(Action.maintenance_action_set),
            )
            .all()
        )

        # Preserve input order
        by_id = {d.id: d for d in demands}
        return [by_id[i] for i in part_demand_ids if i in by_id]

    @staticmethod
    def build_parts_summary(selected_demands: list[PartDemand]) -> list[dict]:
        """Group selected demands by part_id and compute total required qty."""
        totals: dict[int, float] = {}
        for d in selected_demands:
            totals[d.part_id] = float(totals.get(d.part_id, 0.0) + (d.quantity_required or 0.0))

        part_ids = list(totals.keys())
        parts = PartDefinition.query.filter(PartDefinition.id.in_(part_ids)).all() if part_ids else []
        parts_by_id = {p.id: p for p in parts}

        summary: list[dict] = []
        for part_id, total_qty in sorted(totals.items(), key=lambda x: x[0]):
            part = parts_by_id.get(part_id)
            summary.append(
                {
                    "part_id": part_id,
                    "part_number": part.part_number if part else str(part_id),
                    "part_name": part.part_name if part else "",
                    "total_qty": total_qty,
                    "default_unit_cost": float(part.last_unit_cost) if (part and part.last_unit_cost) else 0.0,
                }
            )

        return summary

    @staticmethod
    def normalize_selected_ids(raw_ids: list[str]) -> list[int]:
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





