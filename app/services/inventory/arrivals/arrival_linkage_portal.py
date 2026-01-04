"""
Arrival Linkage Portal Service

UI/View layer service for the arrival linkage portal.
Business logic for linking/unlinking is handled by ArrivalLinkageManager.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import joinedload

from app.buisness.inventory.arrivals.arrival_linkage_manager import ArrivalLinkageManager
from app.data.inventory.arrivals.package_header import PackageHeader
from app.data.inventory.arrivals.part_arrival import PartArrival
from app.data.inventory.ordering.purchase_order_line import PurchaseOrderLine
from app.logger import get_logger

logger = get_logger("asset_management.services.inventory.arrivals.linkage_portal")


@dataclass
class ArrivalWithPOLines:
    """Part Arrival with its linked and linkable PO lines"""
    part_arrival: PartArrival
    linked_po_line: PurchaseOrderLine | None
    linkable_po_lines: list[PurchaseOrderLine]
    quantity_available: float
    allocation_percentage: float


class ArrivalLinkagePortal:
    """
    UI/View service for the Arrival Linkage Portal.
    
    Provides portal-specific methods for:
    - Getting part arrivals with their PO line linkages (for display)
    - Finding unlinked PO lines matching a part arrival's part (for search/filter)
    - Portal-specific queries and data formatting
    
    Note: Actual link/unlink operations are handled by ArrivalLinkageManager,
    which can be accessed via PackageArrivalContext or PartArrivalContext.
    """
    
    def __init__(self, package_header_id: int):
        self.package_header_id = package_header_id
        self._package = None
        self._linkage_manager = None
        
    @property
    def package_header(self) -> PackageHeader:
        if self._package is None:
            self._package = PackageHeader.query.get_or_404(self.package_header_id)
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
        - Already linked PO lines
        - Available unlinked PO lines (matching part_id)
        - Allocation calculations
        """
        result = []
        
        # Get all part arrivals for this package
        arrivals = PartArrival.query.filter_by(
            package_header_id=self.package_header_id
        ).options(
            joinedload(PartArrival.part),
            joinedload(PartArrival.purchase_order_line)
            .joinedload(PurchaseOrderLine.purchase_order),
            joinedload(PartArrival.major_location)
        ).all()
        
        for arrival in arrivals:
            # Get linked PO line (if any)
            linked_po_line = arrival.purchase_order_line
            
            # Calculate quantity linked vs available
            quantity_linked = arrival.quantity_linked_to_purchase_order_line or 0.0
            quantity_available = arrival.quantity_received - quantity_linked
            
            # Calculate allocation percentage
            if arrival.quantity_received > 0:
                allocation_pct = (quantity_linked / arrival.quantity_received) * 100.0
            else:
                allocation_pct = 0.0
            
            # Find unlinked PO lines matching this part
            # Get all PO lines for the same part that aren't fully received
            linkable_po_lines = []
            if arrival.part_id:
                po_lines = PurchaseOrderLine.query.filter(
                    PurchaseOrderLine.part_id == arrival.part_id,
                    PurchaseOrderLine.status.in_(['Pending', 'Ordered', 'Shipped'])
                ).options(
                    joinedload(PurchaseOrderLine.purchase_order)
                ).all()
                
                # Filter to lines that still need quantities
                for line in po_lines:
                    qty_needed = line.quantity_ordered - line.quantity_received_total
                    if qty_needed > 0:
                        linkable_po_lines.append(line)
            
            result.append(ArrivalWithPOLines(
                part_arrival=arrival,
                linked_po_line=linked_po_line,
                linkable_po_lines=linkable_po_lines,
                quantity_available=quantity_available,
                allocation_percentage=allocation_pct
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
        arrival = PartArrival.query.get(part_arrival_id)
        if not arrival or arrival.package_header_id != self.package_header_id:
            return False, "Invalid part arrival"
        
        # Delegate to manager
        return self.linkage_manager.link_arrival_to_po_line(
            part_arrival_id, po_line_id, quantity_to_link, user_id
        )
    
    def unlink_arrival_from_po_line(self, part_arrival_id: int, user_id: int) -> tuple[bool, str]:
        """
        Unlink a part arrival from its PO line.
        
        Delegates to ArrivalLinkageManager after validating the arrival
        belongs to this package.
        
        Returns:
            (success: bool, message: str)
        """
        # Validate arrival belongs to this package
        arrival = PartArrival.query.get(part_arrival_id)
        if not arrival or arrival.package_header_id != self.package_header_id:
            return False, "Arrival not found or does not belong to this package"
        
        # Delegate to manager
        return self.linkage_manager.unlink_arrival_from_po_line(part_arrival_id, user_id)

