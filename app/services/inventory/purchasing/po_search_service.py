"""app.services.inventory.purchasing.po_search_service

Shared search/filter service for Purchase Orders (headers) and Purchase Order Lines.

Goal:
- One canonical place to parse query-string args into a filter object
- One canonical place to build queries for:
  - PurchaseOrderHeader (PO list / viewer)
  - PurchaseOrderLine (PO line selection portals)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Query

from app import db
from app.data.core.asset_info.asset import Asset
from app.data.core.major_location import MajorLocation
from app.data.core.supply.part_definition import PartDefinition
from app.data.core.user_info.user import User
from app.data.inventory.purchasing.part_demand_link import PartDemandPurchaseOrderLink
from app.data.inventory.purchasing.purchase_order_header import PurchaseOrderHeader
from app.data.inventory.purchasing.purchase_order_line import PurchaseOrderLine
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.maintenance.base.part_demands import PartDemand
from app.services.inventory.purchasing.purchase_order_line_service import PurchaseOrderLineService


@dataclass(frozen=True)
class POSearchFilters:
    # Applies to PO headers AND PO lines (context-specific interpretation where needed)
    status: Optional[str] = None
    location_id: Optional[int] = None  # PO header location filter
    purchase_order_id: Optional[int] = None  # PO line filter (exact PO)

    part_number: Optional[str] = None
    part_name: Optional[str] = None
    vendor: Optional[str] = None

    # PO header order_date range (also used for PO-line search via header join)
    date_from: Optional[str] = None  # YYYY-MM-DD
    date_to: Optional[str] = None  # YYYY-MM-DD

    created_by_id: Optional[int] = None

    # Linked part demand / maintenance event filters (via PO line links)
    part_demand_assigned_to_id: Optional[int] = None
    event_assigned_to_id: Optional[int] = None
    asset_id: Optional[int] = None

    # General search term (po number / vendor / part fields)
    search_term: Optional[str] = None


class POSearchService:
    """Search utilities for PO headers and PO lines."""

    @staticmethod
    def parse_filters(args: Any) -> POSearchFilters:
        """
        Parse common filter args from a Flask `request.args`-like mapping.

        Back-compat:
        - Accepts `search_term` or `search` for the general search box.
        """
        def _get_int(key: str) -> Optional[int]:
            try:
                # Flask MultiDict supports `type=`
                return args.get(key, type=int)
            except TypeError:
                # Plain dict-like
                raw = args.get(key)
                if raw in (None, ""):
                    return None
                try:
                    return int(raw)
                except Exception:
                    return None

        search = (args.get("search_term") or args.get("search") or "").strip() or None
        return POSearchFilters(
            status=args.get("status") or None,
            location_id=_get_int("location_id"),
            # Back-compat: allow `po_id` as shorthand
            purchase_order_id=_get_int("purchase_order_id") or _get_int("po_id"),
            part_number=(args.get("part_number") or "").strip() or None,
            part_name=(args.get("part_name") or "").strip() or None,
            vendor=(args.get("vendor") or "").strip() or None,
            date_from=args.get("date_from") or None,
            date_to=args.get("date_to") or None,
            created_by_id=_get_int("created_by_id"),
            part_demand_assigned_to_id=_get_int("part_demand_assigned_to_id"),
            event_assigned_to_id=_get_int("event_assigned_to_id"),
            asset_id=_get_int("asset_id"),
            search_term=search,
        )

    @staticmethod
    def to_template_dict(filters: POSearchFilters) -> dict[str, Any]:
        """Normalize filters into simple strings/ints for templates + url_for(**filters)."""
        return {
            "status": filters.status or "",
            "location_id": filters.location_id or "",
            "purchase_order_id": filters.purchase_order_id or "",
            "part_number": filters.part_number or "",
            "part_name": filters.part_name or "",
            "vendor": filters.vendor or "",
            "date_from": filters.date_from or "",
            "date_to": filters.date_to or "",
            "created_by_id": filters.created_by_id or "",
            "part_demand_assigned_to_id": filters.part_demand_assigned_to_id or "",
            "event_assigned_to_id": filters.event_assigned_to_id or "",
            "asset_id": filters.asset_id or "",
            "search_term": filters.search_term or "",
        }

    @staticmethod
    def get_shared_filter_options() -> dict[str, Any]:
        """Dropdown data used by the shared PO search form."""
        return {
            "users": User.query.filter_by(is_active=True).order_by(User.username).all(),
            "major_locations": MajorLocation.query.filter_by(is_active=True).order_by(MajorLocation.name).all(),
            "assets": Asset.query.filter_by(status="Active").order_by(Asset.name).all(),
        }

    # --------------------------------------------------------------------------------------
    # PO HEADER SEARCH (purchase order viewer/list page)
    # --------------------------------------------------------------------------------------

    @staticmethod
    def build_po_headers_query(filters: POSearchFilters) -> Query:
        """
        Build a PurchaseOrderHeader query applying shared filters.

        Some filters (part fields, demand/event/asset) are applied via EXISTS on related PO lines.
        """
        query = PurchaseOrderHeader.query

        if filters.status:
            query = query.filter(PurchaseOrderHeader.status == filters.status)
        if filters.location_id:
            query = query.filter(PurchaseOrderHeader.major_location_id == filters.location_id)
        if filters.vendor:
            query = query.filter(PurchaseOrderHeader.vendor_name.ilike(f"%{filters.vendor}%"))
        if filters.created_by_id:
            query = query.filter(PurchaseOrderHeader.created_by_id == filters.created_by_id)

        # Date range (order_date)
        date_from_dt: Optional[datetime] = None
        date_to_dt: Optional[datetime] = None
        if filters.date_from:
            try:
                date_from_dt = datetime.strptime(filters.date_from, "%Y-%m-%d")
            except ValueError:
                date_from_dt = None
        if filters.date_to:
            try:
                date_to_dt = datetime.strptime(filters.date_to, "%Y-%m-%d")
            except ValueError:
                date_to_dt = None
        if date_from_dt:
            query = query.filter(PurchaseOrderHeader.order_date >= date_from_dt)
        if date_to_dt:
            query = query.filter(PurchaseOrderHeader.order_date <= date_to_dt)

        # Part filters (via PO lines -> part definition)
        if filters.part_number or filters.part_name:
            part_subq = (
                select(1)
                .select_from(PurchaseOrderLine)
                .join(PartDefinition, PurchaseOrderLine.part_id == PartDefinition.id)
                .where(PurchaseOrderLine.purchase_order_id == PurchaseOrderHeader.id)
            )
            if filters.part_number:
                part_subq = part_subq.where(PartDefinition.part_number.ilike(f"%{filters.part_number}%"))
            if filters.part_name:
                part_subq = part_subq.where(PartDefinition.part_name.ilike(f"%{filters.part_name}%"))
            query = query.filter(exists(part_subq))

        # Linked part demand / event / asset filters (via PO line links)
        if filters.part_demand_assigned_to_id or filters.event_assigned_to_id or filters.asset_id:
            link_subq = (
                select(1)
                .select_from(PurchaseOrderLine)
                .join(PartDemandPurchaseOrderLink, PartDemandPurchaseOrderLink.purchase_order_line_id == PurchaseOrderLine.id)
                .join(PartDemand, PartDemandPurchaseOrderLink.part_demand_id == PartDemand.id)
                .join(Action, PartDemand.action_id == Action.id)
                .join(MaintenanceActionSet, Action.maintenance_action_set_id == MaintenanceActionSet.id)
                .where(PurchaseOrderLine.purchase_order_id == PurchaseOrderHeader.id)
            )
            if filters.part_demand_assigned_to_id:
                link_subq = link_subq.where(Action.assigned_user_id == filters.part_demand_assigned_to_id)
            if filters.event_assigned_to_id:
                link_subq = link_subq.where(MaintenanceActionSet.assigned_user_id == filters.event_assigned_to_id)
            if filters.asset_id:
                link_subq = link_subq.where(MaintenanceActionSet.asset_id == filters.asset_id)
            query = query.filter(exists(link_subq))

        # General search: vendor, PO number, or part fields
        if filters.search_term:
            term = filters.search_term
            part_search_subq = (
                select(1)
                .select_from(PurchaseOrderLine)
                .join(PartDefinition, PurchaseOrderLine.part_id == PartDefinition.id)
                .where(
                    PurchaseOrderLine.purchase_order_id == PurchaseOrderHeader.id,
                    or_(
                        PartDefinition.part_number.ilike(f"%{term}%"),
                        PartDefinition.part_name.ilike(f"%{term}%"),
                    ),
                )
            )
            query = query.filter(
                or_(
                    PurchaseOrderHeader.po_number.ilike(f"%{term}%"),
                    PurchaseOrderHeader.vendor_name.ilike(f"%{term}%"),
                    exists(part_search_subq),
                )
            )

        return query

    @staticmethod
    def search_purchase_orders(filters: POSearchFilters, *, limit: int = 500) -> list[PurchaseOrderHeader]:
        return (
            POSearchService.build_po_headers_query(filters)
            .order_by(PurchaseOrderHeader.created_at.desc())
            .limit(limit)
            .all()
        )

    # --------------------------------------------------------------------------------------
    # PO LINE SEARCH (arrivals portal, line viewer portals, etc.)
    # --------------------------------------------------------------------------------------

    @staticmethod
    def search_po_lines(
        filters: POSearchFilters,
        *,
        unfulfilled_only: bool = False,
        limit: int = 1000,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> list[PurchaseOrderLine]:
        """Search PO lines using the existing PurchaseOrderLineService query builder."""
        date_from_dt: Optional[datetime] = None
        date_to_dt: Optional[datetime] = None
        if filters.date_from:
            try:
                date_from_dt = datetime.strptime(filters.date_from, "%Y-%m-%d")
            except ValueError:
                date_from_dt = None
        if filters.date_to:
            try:
                date_to_dt = datetime.strptime(filters.date_to, "%Y-%m-%d")
            except ValueError:
                date_to_dt = None

        query = PurchaseOrderLineService.build_po_lines_query(
            status=filters.status,
            purchase_order_id=filters.purchase_order_id,
            part_number=filters.part_number,
            part_name=filters.part_name,
            vendor=filters.vendor,
            date_from=date_from_dt,
            date_to=date_to_dt,
            created_by_id=filters.created_by_id,
            part_demand_assigned_to_id=filters.part_demand_assigned_to_id,
            event_assigned_to_id=filters.event_assigned_to_id,
            asset_id=filters.asset_id,
            search_term=filters.search_term,
            order_by=order_by,
            order_direction=order_direction,
        )

        if unfulfilled_only:
            # remaining = quantity_ordered - quantity_received_total > 0
            # Since quantity_received_total is a property using total_quantity_linked_from_arrivals,
            # we need to use a subquery to calculate it
            from sqlalchemy import func
            from app.data.inventory.arrivals.purchase_order_link import ArrivalPurchaseOrderLink

            # Subquery to calculate total linked quantity per PO line
            linked_subquery = (
                db.session.query(
                    ArrivalPurchaseOrderLink.purchase_order_line_id,
                    func.sum(ArrivalPurchaseOrderLink.quantity_linked).label('total_linked')
                )
                .group_by(ArrivalPurchaseOrderLink.purchase_order_line_id)
                .subquery()
            )

            query = query.outerjoin(
                linked_subquery,
                PurchaseOrderLine.id == linked_subquery.c.purchase_order_line_id
            ).filter(
                PurchaseOrderLine.quantity_ordered > func.coalesce(linked_subquery.c.total_linked, 0.0)
            )

            # Default line-status filter for this portal: Ordered or Shipped
            if not filters.status:
                query = query.filter(PurchaseOrderLine.status.in_(["Ordered", "Shipped"]))

        return query.limit(limit).all()

