"""
Purchase Order Search Service for Arrivals

Service layer for searching and filtering purchase orders and purchase order lines
in the arrivals context. Analogous to po_search_service but focused on finding
PO lines that can be linked to arrival lines.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import exists, or_, select, func
from sqlalchemy.orm import Query, joinedload

from app.data.core.asset_info.asset import Asset
from app.data.core.major_location import MajorLocation
from app.data.core.supply.part_definition import PartDefinition
from app.data.core.user_info.user import User
from app.data.inventory.arrivals.purchase_order_link import ArrivalPurchaseOrderLink
from app.data.inventory.purchasing.purchase_order_header import PurchaseOrderHeader
from app.data.inventory.purchasing.purchase_order_line import PurchaseOrderLine
from app.logger import get_logger

logger = get_logger("asset_management.services.inventory.arrivals.purchase_order_search")


@dataclass(frozen=True)
class ArrivalPOSearchFilters:
    """Filter options for searching purchase orders in arrivals context."""
    # PO header filters
    status: Optional[str] = None
    location_id: Optional[int] = None  # PO header location filter
    purchase_order_id: Optional[int] = None  # PO line filter (exact PO)
    
    # Part filters
    part_id: Optional[int] = None
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    vendor: Optional[str] = None
    
    # Date filters
    date_from: Optional[str] = None  # YYYY-MM-DD
    date_to: Optional[str] = None  # YYYY-MM-DD
    
    created_by_id: Optional[int] = None
    
    # Linked arrival filters (via ArrivalPurchaseOrderLink)
    arrival_line_id: Optional[int] = None  # Filter by linked arrival
    package_header_id: Optional[int] = None  # Filter by arrivals in a package
    
    # General search term
    search_term: Optional[str] = None


class PurchaseOrderSearchService:
    """Search utilities for purchase orders in arrivals context."""
    
    @staticmethod
    def parse_filters(args: Any) -> ArrivalPOSearchFilters:
        """
        Parse filter args from a Flask `request.args`-like mapping.
        
        Args:
            args: Flask request.args or dict-like object
            
        Returns:
            ArrivalPOSearchFilters instance
        """
        def _get_int(key: str) -> Optional[int]:
            try:
                return args.get(key, type=int)
            except TypeError:
                raw = args.get(key)
                if raw in (None, ""):
                    return None
                try:
                    return int(raw)
                except Exception:
                    return None
        
        search = (args.get("search_term") or args.get("search") or "").strip() or None
        return ArrivalPOSearchFilters(
            status=args.get("status") or None,
            location_id=_get_int("location_id"),
            purchase_order_id=_get_int("purchase_order_id") or _get_int("po_id"),
            part_id=_get_int("part_id"),
            part_number=(args.get("part_number") or "").strip() or None,
            part_name=(args.get("part_name") or "").strip() or None,
            vendor=(args.get("vendor") or "").strip() or None,
            date_from=args.get("date_from") or None,
            date_to=args.get("date_to") or None,
            created_by_id=_get_int("created_by_id"),
            arrival_line_id=_get_int("arrival_line_id"),
            package_header_id=_get_int("package_header_id"),
            search_term=search,
        )
    
    @staticmethod
    def to_template_dict(filters: ArrivalPOSearchFilters) -> dict[str, Any]:
        """Normalize filters into simple strings/ints for templates + url_for(**filters)."""
        return {
            "status": filters.status or "",
            "location_id": filters.location_id or "",
            "purchase_order_id": filters.purchase_order_id or "",
            "part_id": filters.part_id or "",
            "part_number": filters.part_number or "",
            "part_name": filters.part_name or "",
            "vendor": filters.vendor or "",
            "date_from": filters.date_from or "",
            "date_to": filters.date_to or "",
            "created_by_id": filters.created_by_id or "",
            "arrival_line_id": filters.arrival_line_id or "",
            "package_header_id": filters.package_header_id or "",
            "search_term": filters.search_term or "",
        }
    
    @staticmethod
    def get_shared_filter_options() -> dict[str, Any]:
        """Dropdown data used by the PO search form in arrivals context."""
        return {
            "users": User.query.filter_by(is_active=True).order_by(User.username).all(),
            "major_locations": MajorLocation.query.filter_by(is_active=True).order_by(MajorLocation.name).all(),
        }
    
    # --------------------------------------------------------------------------------------
    # PO HEADER SEARCH
    # --------------------------------------------------------------------------------------
    
    @staticmethod
    def build_po_headers_query(filters: ArrivalPOSearchFilters) -> Query:
        """
        Build a PurchaseOrderHeader query applying filters.
        
        Some filters (part fields, linked arrivals) are applied via EXISTS on related PO lines.
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
        if filters.part_id or filters.part_number or filters.part_name:
            part_subq = (
                select(1)
                .select_from(PurchaseOrderLine)
                .join(PartDefinition, PurchaseOrderLine.part_id == PartDefinition.id)
                .where(PurchaseOrderLine.purchase_order_id == PurchaseOrderHeader.id)
            )
            if filters.part_id:
                part_subq = part_subq.where(PurchaseOrderLine.part_id == filters.part_id)
            if filters.part_number:
                part_subq = part_subq.where(PartDefinition.part_number.ilike(f"%{filters.part_number}%"))
            if filters.part_name:
                part_subq = part_subq.where(PartDefinition.part_name.ilike(f"%{filters.part_name}%"))
            query = query.filter(exists(part_subq))
        
        # Linked arrival filters (via ArrivalPurchaseOrderLink)
        if filters.arrival_line_id or filters.package_header_id:
            from app.data.inventory.arrivals.arrival_line import ArrivalLine
            
            link_subq = (
                select(1)
                .select_from(PurchaseOrderLine)
                .join(ArrivalPurchaseOrderLink, ArrivalPurchaseOrderLink.purchase_order_line_id == PurchaseOrderLine.id)
                .join(ArrivalLine, ArrivalPurchaseOrderLink.arrival_line_id == ArrivalLine.id)
                .where(PurchaseOrderLine.purchase_order_id == PurchaseOrderHeader.id)
            )
            if filters.arrival_line_id:
                link_subq = link_subq.where(ArrivalLine.id == filters.arrival_line_id)
            if filters.package_header_id:
                link_subq = link_subq.where(ArrivalLine.package_header_id == filters.package_header_id)
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
    def search_purchase_orders(filters: ArrivalPOSearchFilters, *, limit: int = 500) -> list[PurchaseOrderHeader]:
        """Search purchase orders using filters."""
        return (
            PurchaseOrderSearchService.build_po_headers_query(filters)
            .order_by(PurchaseOrderHeader.created_at.desc())
            .limit(limit)
            .all()
        )
    
    # --------------------------------------------------------------------------------------
    # PO LINE SEARCH (for linking to arrivals)
    # --------------------------------------------------------------------------------------
    
    @staticmethod
    def search_po_lines_for_arrivals(
        filters: ArrivalPOSearchFilters,
        *,
        unfulfilled_only: bool = True,
        exclude_arrival_line_id: Optional[int] = None,
        limit: int = 1000,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> list[PurchaseOrderLine]:
        """
        Search PO lines that can be linked to arrivals.
        
        Args:
            filters: Search filters
            unfulfilled_only: Only return lines with remaining capacity
            exclude_arrival_line_id: Exclude PO lines already linked to this arrival
            limit: Maximum results
            order_by: Field to sort by
            order_direction: 'asc' or 'desc'
            
        Returns:
            List of PurchaseOrderLine objects with relationships loaded
        """
        query = PurchaseOrderLine.query
        
        # Basic filters
        if filters.status:
            query = query.filter(PurchaseOrderLine.status == filters.status)
        elif unfulfilled_only:
            # Default to Ordered/Shipped for unfulfilled search
            query = query.filter(PurchaseOrderLine.status.in_(["Ordered", "Shipped"]))
        
        if filters.purchase_order_id:
            query = query.filter(PurchaseOrderLine.purchase_order_id == filters.purchase_order_id)
        
        if filters.part_id:
            query = query.filter(PurchaseOrderLine.part_id == filters.part_id)
        
        # Part name/number filters
        if filters.part_number or filters.part_name:
            query = query.join(PartDefinition, PurchaseOrderLine.part_id == PartDefinition.id)
            if filters.part_number:
                query = query.filter(PartDefinition.part_number.ilike(f"%{filters.part_number}%"))
            if filters.part_name:
                query = query.filter(PartDefinition.part_name.ilike(f"%{filters.part_name}%"))
        
        # Vendor filter (via PO header)
        if filters.vendor:
            query = query.join(PurchaseOrderHeader, PurchaseOrderLine.purchase_order_id == PurchaseOrderHeader.id)
            query = query.filter(PurchaseOrderHeader.vendor_name.ilike(f"%{filters.vendor}%"))
        
        # Location filter (via PO header)
        if filters.location_id:
            if not filters.vendor:  # Only join if not already joined
                query = query.join(PurchaseOrderHeader, PurchaseOrderLine.purchase_order_id == PurchaseOrderHeader.id)
            query = query.filter(PurchaseOrderHeader.major_location_id == filters.location_id)
        
        # Date filters (via PO header)
        if filters.date_from or filters.date_to:
            if not filters.vendor and not filters.location_id:
                query = query.join(PurchaseOrderHeader, PurchaseOrderLine.purchase_order_id == PurchaseOrderHeader.id)
            
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
        
        # Unfulfilled filter: remaining quantity > 0
        if unfulfilled_only:
            query = query.filter(
                PurchaseOrderLine.quantity_ordered
                > (
                    func.coalesce(PurchaseOrderLine.quantity_accepted, 0.0)
                    + func.coalesce(PurchaseOrderLine.quantity_rejected, 0.0)
                )
            )
        
        # Exclude PO lines already linked to a specific arrival
        if exclude_arrival_line_id:
            query = query.filter(
                ~exists(
                    select(1)
                    .select_from(ArrivalPurchaseOrderLink)
                    .where(
                        ArrivalPurchaseOrderLink.purchase_order_line_id == PurchaseOrderLine.id,
                        ArrivalPurchaseOrderLink.arrival_line_id == exclude_arrival_line_id
                    )
                )
            )
        
        # General search term
        if filters.search_term:
            term = filters.search_term
            if not filters.part_number and not filters.part_name:
                query = query.join(PartDefinition, PurchaseOrderLine.part_id == PartDefinition.id)
            if not filters.vendor and not filters.location_id and not filters.date_from and not filters.date_to:
                query = query.join(PurchaseOrderHeader, PurchaseOrderLine.purchase_order_id == PurchaseOrderHeader.id)
            
            query = query.filter(
                or_(
                    PurchaseOrderHeader.po_number.ilike(f"%{term}%"),
                    PurchaseOrderHeader.vendor_name.ilike(f"%{term}%"),
                    PartDefinition.part_number.ilike(f"%{term}%"),
                    PartDefinition.part_name.ilike(f"%{term}%"),
                )
            )
        
        # Apply sorting
        if order_by == "created_at":
            if order_direction == "asc":
                query = query.order_by(PurchaseOrderLine.created_at.asc())
            else:
                query = query.order_by(PurchaseOrderLine.created_at.desc())
        elif order_by == "po_number":
            if not filters.vendor and not filters.location_id and not filters.date_from and not filters.date_to:
                query = query.join(PurchaseOrderHeader, PurchaseOrderLine.purchase_order_id == PurchaseOrderHeader.id)
            if order_direction == "asc":
                query = query.order_by(PurchaseOrderHeader.po_number.asc())
            else:
                query = query.order_by(PurchaseOrderHeader.po_number.desc())
        
        # Use distinct to avoid duplicates from joins
        query = query.distinct()
        
        # Eager load relationships
        lines = query.options(
            joinedload(PurchaseOrderLine.purchase_order).joinedload(PurchaseOrderHeader.major_location),
            joinedload(PurchaseOrderLine.part),
        ).limit(limit).all()
        
        return lines
    
    @staticmethod
    def get_linkable_po_lines_for_arrival(
        arrival_line_id: int,
        filters: Optional[ArrivalPOSearchFilters] = None,
        *,
        limit: int = 1000,
    ) -> list[PurchaseOrderLine]:
        """
        Get PO lines that can be linked to a specific arrival line.
        
        Args:
            arrival_line_id: ID of the arrival line
            filters: Optional additional filters
            limit: Maximum results
            
        Returns:
            List of linkable PurchaseOrderLine objects
        """
        from app.data.inventory.arrivals.arrival_line import ArrivalLine
        
        arrival = ArrivalLine.query.get(arrival_line_id)
        if not arrival:
            return []
        
        # Build filters with part_id constraint
        if filters is None:
            filters = ArrivalPOSearchFilters()
        
        # Override part_id to match arrival
        filters = ArrivalPOSearchFilters(
            **{k: v for k, v in filters.__dict__.items()},
            part_id=arrival.part_id,
        )
        
        # Search with exclusion of this arrival
        return PurchaseOrderSearchService.search_po_lines_for_arrivals(
            filters,
            unfulfilled_only=True,
            exclude_arrival_line_id=arrival_line_id,
            limit=limit,
        )
    
    @staticmethod
    def get_filter_options() -> dict:
        """Return dropdown options used by the portal filter UI."""
        return {
            "statuses": ["Pending", "Ordered", "Shipped", "Complete", "Cancelled"],
            **PurchaseOrderSearchService.get_shared_filter_options(),
        }
