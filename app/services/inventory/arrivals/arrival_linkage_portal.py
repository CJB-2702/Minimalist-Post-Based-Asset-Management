"""
Arrival Linkage Portal Service

UI/View layer service for the arrival linkage portal.
Business logic for linking/unlinking is handled by ArrivalLinkageManager.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import joinedload

from app import db
from app.buisness.inventory.arrivals.arrival_linkage_manager import ArrivalLinkageManager
from app.data.inventory.arrivals.arrival_header import ArrivalHeader
from app.data.inventory.arrivals.arrival_line import ArrivalLine
from app.data.inventory.arrivals.purchase_order_link import ArrivalPurchaseOrderLink
from app.data.inventory.purchasing.purchase_order_line import PurchaseOrderLine
from app.logger import get_logger

logger = get_logger("asset_management.services.inventory.arrivals.linkage_portal")


@dataclass
class ArrivalWithPOLines:
    """Part Arrival with its linked and linkable PO lines"""
    part_arrival: ArrivalLine
    linked_po_lines: list[PurchaseOrderLine]  # Multiple links supported
    linkable_po_lines: list[PurchaseOrderLine]
    quantity_available: float
    allocation_percentage: float
    links_info: list[dict]  # Detailed link information with quantities


class ArrivalLinkagePortal:
    """
    UI/View service for the Arrival Linkage Portal.
    
    Provides portal-specific methods for:
    - Getting part arrivals with their PO line linkages (for display)
    - Finding unlinked PO lines matching a part arrival's part (for search/filter)
    - Portal-specific queries and data formatting
    
    Note: Actual link/unlink operations are handled by ArrivalLinkageManager,
    which can be accessed via ArrivalContext or ArrivalLineContext.
    """
    
    def __init__(self, package_header_id: int):
        self.package_header_id = package_header_id
        self._package = None
        self._linkage_manager = None
        
    @property
    def package_header(self) -> ArrivalHeader:
        if self._package is None:
            self._package = ArrivalHeader.query.get_or_404(self.package_header_id)
        return self._package
    
    @property
    def linkage_manager(self) -> ArrivalLinkageManager:
        """Access to the linkage manager for business logic operations"""
        if self._linkage_manager is None:
            self._linkage_manager = ArrivalLinkageManager()
        return self._linkage_manager
    
    def get_arrivals_with_po_lines(self) -> list[ArrivalWithPOLines]:
        """
        Get all part arrivals for this package, with:
        - Already linked PO lines (multiple links supported)
        - Available unlinked PO lines (matching part_id)
        - Allocation calculations
        """
        result = []
        
        # Get all part arrivals for this package
        # Note: po_line_links is a dynamic relationship, so we can't use joinedload on it
        arrivals = ArrivalLine.query.filter_by(
            package_header_id=self.package_header_id
        ).options(
            joinedload(ArrivalLine.part),
            joinedload(ArrivalLine.major_location)
        ).all()
        
        # Load PO line links separately to avoid N+1 queries
        arrival_line_ids = [arrival.id for arrival in arrivals]
        links_by_arrival = {}
        if arrival_line_ids:
            links = ArrivalPurchaseOrderLink.query.filter(
                ArrivalPurchaseOrderLink.arrival_line_id.in_(arrival_line_ids)
            ).options(
                joinedload(ArrivalPurchaseOrderLink.purchase_order_line).joinedload(PurchaseOrderLine.purchase_order),
            ).all()
            
            # Group links by arrival_line_id
            for link in links:
                if link.arrival_line_id not in links_by_arrival:
                    links_by_arrival[link.arrival_line_id] = []
                links_by_arrival[link.arrival_line_id].append(link)
        
        for arrival in arrivals:
            # Get all linked PO lines via links (using pre-loaded links from session)
            links = links_by_arrival.get(arrival.id, [])
            linked_po_lines = [link.purchase_order_line for link in links]
            
            # Build detailed link information
            links_info = [
                {
                    "link_id": link.id,
                    "po_line_id": link.purchase_order_line_id,
                    "po_line": link.purchase_order_line,
                    "quantity_linked": link.quantity_linked,
                    "po_number": link.purchase_order_line.purchase_order.po_number if link.purchase_order_line and link.purchase_order_line.purchase_order else None,
                }
                for link in links
            ]
            
            # Calculate quantity linked vs available
            total_quantity_linked = arrival.total_quantity_linked
            quantity_available = arrival.quantity_available_for_linking
            
            # Calculate allocation percentage
            if arrival.quantity_received > 0:
                allocation_pct = (total_quantity_linked / arrival.quantity_received) * 100.0
            else:
                allocation_pct = 0.0
            
            # Find unlinked PO lines matching this part
            # Get all PO lines for the same part that aren't fully received
            # Exclude lines already linked to this arrival
            linkable_po_lines = []
            if arrival.part_id:
                from sqlalchemy import exists, select
                
                # Get PO lines that match part and have capacity
                po_lines = PurchaseOrderLine.query.filter(
                    PurchaseOrderLine.part_id == arrival.part_id,
                    PurchaseOrderLine.status.in_(['Pending', 'Ordered', 'Shipped'])
                ).options(
                    joinedload(PurchaseOrderLine.purchase_order)
                ).all()
                
                # Filter to lines that still need quantities and aren't already linked
                linked_po_line_ids = {link.purchase_order_line_id for link in links}
                for line in po_lines:
                    if line.id in linked_po_line_ids:
                        continue  # Skip already linked lines
                    
                    qty_needed = line.quantity_ordered - line.quantity_received_total
                    if qty_needed > 0:
                        linkable_po_lines.append(line)
            
            result.append(ArrivalWithPOLines(
                part_arrival=arrival,
                linked_po_lines=linked_po_lines,
                linkable_po_lines=linkable_po_lines,
                quantity_available=quantity_available,
                allocation_percentage=allocation_pct,
                links_info=links_info
            ))
        
        return result
    
    def get_purchase_orders_with_lines(
        self,
        part_id: int | None = None,
        po_number: str | None = None,
        vendor_name: str | None = None,
        status: str | None = None,
        major_location_id: int | None = None,
    ) -> list[dict]:
        """
        Get purchase orders that have unlinked PO lines.
        Optionally filter by part_id, PO number, vendor, etc.
        """
        # Query PO lines that match criteria
        query = PurchaseOrderLine.query
        
        if part_id:
            query = query.filter(PurchaseOrderLine.part_id == part_id)
        
        # Only get lines that still need quantities
        query = query.filter(
            PurchaseOrderLine.status.in_(['Pending', 'Ordered', 'Shipped'])
        )
        
        po_lines = query.options(
            joinedload(PurchaseOrderLine.purchase_order),
            joinedload(PurchaseOrderLine.part)
        ).all()
        
        # Filter PO lines that still need quantities
        filtered_lines = []
        for line in po_lines:
            qty_needed = line.quantity_ordered - line.quantity_received_total
            if qty_needed > 0:
                filtered_lines.append(line)
        
        # Group by purchase order
        pos_dict = {}
        for line in filtered_lines:
            po = line.purchase_order
            
            # Apply PO-level filters
            if po_number and po_number.lower() not in (po.po_number or "").lower():
                continue
            if vendor_name and vendor_name.lower() not in (po.vendor_name or "").lower():
                continue
            if status and po.status != status:
                continue
            if major_location_id and po.major_location_id != major_location_id:
                continue
            
            po_id = po.id
            
            if po_id not in pos_dict:
                pos_dict[po_id] = {
                    "purchase_order_id": po_id,
                    "purchase_order": po,
                    "po_lines": []
                }
            
            pos_dict[po_id]["po_lines"].append(line)
        
        return list(pos_dict.values())
    
    def link_arrival_to_po_line(
        self, 
        part_arrival_id: int, 
        po_line_id: int, 
        quantity_to_link: float,
        user_id: int
    ) -> tuple[bool, str]:
        """
        Link a part arrival to a PO line.
        
        Delegates to ArrivalLinkageManager after validating the arrival
        belongs to this package.
        
        Returns:
            (success: bool, message: str)
        """
        # Validate arrival belongs to this package
        arrival = ArrivalLine.query.get(part_arrival_id)
        if not arrival or arrival.package_header_id != self.package_header_id:
            return False, "Invalid part arrival"
        
        # Delegate to manager (using new create_link method)
        success, message, link = self.linkage_manager.create_link(
            arrival_line_id=part_arrival_id,
            po_line_id=po_line_id,
            quantity_to_link=quantity_to_link,
            user_id=user_id,
        )
        return success, message
    
    def unlink_arrival_from_po_line(
        self, 
        part_arrival_id: int, 
        user_id: int,
        link_id: int | None = None,
    ) -> tuple[bool, str]:
        """
        Unlink a part arrival from a PO line.
        
        If link_id is provided, unlinks that specific link.
        If link_id is None, unlinks all links for the arrival (legacy behavior).
        
        Delegates to ArrivalLinkageManager after validating the arrival
        belongs to this package.
        
        Returns:
            (success: bool, message: str)
        """
        # Validate arrival belongs to this package
        arrival = ArrivalLine.query.get(part_arrival_id)
        if not arrival or arrival.package_header_id != self.package_header_id:
            return False, "Arrival not found or does not belong to this package"
        
        # If link_id is provided, delete that specific link
        if link_id is not None:
            link = ArrivalPurchaseOrderLink.query.get(link_id)
            if not link or link.arrival_line_id != part_arrival_id:
                return False, "Link not found or does not belong to this arrival"
            return self.linkage_manager.delete_link(link_id, user_id)
        
        # Legacy behavior: delete all links for this arrival
        # This is less ideal but maintains backward compatibility
        links = arrival.po_line_links.all()
        if not links:
            return False, "No links found for this arrival"
        
        # Delete all links
        for link in links:
            success, message = self.linkage_manager.delete_link(link.id, user_id)
            if not success:
                return False, f"Failed to delete link {link.id}: {message}"
        
        return True, f"Successfully unlinked {len(links)} link(s)"
    
    @staticmethod
    def calculate_package_linkage_statuses(package_ids: list[int]) -> dict[int, str]:
        """
        Calculate linkage status for multiple packages.
        
        Status values:
        - "fully_linked": all arrival lines have at least one PO line link
        - "partially_linked": some arrival lines have links
        - "unlinked": no arrival lines have links (or no arrivals)
        
        Args:
            package_ids: List of package header IDs
            
        Returns:
            Dict mapping package_id to status string
        """
        from sqlalchemy import func, case, exists, select
        from app.data.inventory.arrivals.purchase_order_link import ArrivalPurchaseOrderLink
        
        if not package_ids:
            return {}
        
        # Query to count arrivals and linked arrivals per package
        # An arrival is considered "linked" if it has at least one ArrivalPurchaseOrderLink
        
        rows = (
            db.session.query(
                ArrivalLine.package_header_id.label("package_id"),
                func.count(ArrivalLine.id).label("total_arrivals"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                exists(
                                    select(1)
                                    .select_from(ArrivalPurchaseOrderLink)
                                    .where(ArrivalPurchaseOrderLink.arrival_line_id == ArrivalLine.id)
                                ),
                                1
                            ),
                            else_=0
                        )
                    ),
                    0
                ).label("linked_arrivals"),
            )
            .filter(ArrivalLine.package_header_id.in_(package_ids))
            .group_by(ArrivalLine.package_header_id)
            .all()
        )
        
        # Build result dict
        status_by_id = {}
        counts_by_package_id = {
            int(r.package_id): (int(r.total_arrivals or 0), int(r.linked_arrivals or 0))
            for r in rows
        }
        
        for package_id in package_ids:
            total_arrivals, linked_arrivals = counts_by_package_id.get(int(package_id), (0, 0))
            
            if total_arrivals <= 0 or linked_arrivals <= 0:
                status_by_id[int(package_id)] = "unlinked"
            elif linked_arrivals >= total_arrivals:
                status_by_id[int(package_id)] = "fully_linked"
            else:
                status_by_id[int(package_id)] = "partially_linked"
        
        return status_by_id

