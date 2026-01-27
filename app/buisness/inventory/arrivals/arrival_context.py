from __future__ import annotations

from sqlalchemy.orm import joinedload

from app.buisness.inventory.arrivals.arrival_linkage_manager import ArrivalLinkageManager
from app.buisness.inventory.arrivals.arrival_line_context import ArrivalLineContext
from app.buisness.inventory.inventory.inventory_manager import InventoryManager
from app.buisness.inventory.shared.status_manager import InventoryStatusManager
from app.data.inventory.arrivals.arrival_header import ArrivalHeader
from app.data.inventory.arrivals.arrival_line import ArrivalLine
from app.data.inventory.purchasing.purchase_order_line import PurchaseOrderLine


class ArrivalContext:
    """
    Package arrival operations.

    Supports lifecycle decisions:
    - package is directly linkable to one purchase order -> auto-create part arrivals line-by-line
    - otherwise: create package header and allow manual creation/linking of part arrivals
    """

    def __init__(
        self,
        arrival_header_id: int,
        *,
        inventory_manager: InventoryManager | None = None,
        status_manager: InventoryStatusManager | None = None,
        eager_load: bool = True,
    ):
        """
        Initialize ArrivalContext with arrival header and lines.
        
        Args:
            arrival_header_id: ID of the arrival header
            inventory_manager: Optional InventoryManager instance
            status_manager: Optional InventoryStatusManager instance
            eager_load: If True, load arrival lines with eager loading on init
        """
        self._arrival_header_id = arrival_header_id
        self.inventory_manager = inventory_manager or InventoryManager()
        self.status_manager = status_manager or InventoryStatusManager()
        
        # Load arrival header with eager loading of common relationships
        self._arrival_header = ArrivalHeader.query.options(
            joinedload(ArrivalHeader.major_location),
            joinedload(ArrivalHeader.storeroom),
            joinedload(ArrivalHeader.received_by),
        ).get_or_404(self._arrival_header_id)
        
        # Load arrival lines on init if requested
        self._arrival_lines: list[ArrivalLine] | None = None
        if eager_load:
            self._load_arrival_lines()

    def _load_arrival_lines(self, with_relationships: bool = True) -> None:
        """Load arrival lines, optionally with eager loading of relationships."""
        query = ArrivalLine.query.filter_by(package_header_id=self._arrival_header_id)
        
        if with_relationships:
            from app.data.inventory.arrivals.purchase_order_link import ArrivalPurchaseOrderLink
            # Note: po_line_links is a dynamic relationship, so we can't use joinedload on it
            # We'll load the links separately after getting the arrival lines
            query = query.options(
                joinedload(ArrivalLine.part),
                joinedload(ArrivalLine.major_location),
                joinedload(ArrivalLine.storeroom),
            )
        
        self._arrival_lines = query.order_by(ArrivalLine.id.asc()).all()
        
        # If we need relationships, load PO line links separately to avoid N+1 queries
        if with_relationships and self._arrival_lines:
            from app.data.inventory.arrivals.purchase_order_link import ArrivalPurchaseOrderLink
            arrival_line_ids = [line.id for line in self._arrival_lines]
            # Load all links for these arrival lines with their relationships
            links = ArrivalPurchaseOrderLink.query.filter(
                ArrivalPurchaseOrderLink.arrival_line_id.in_(arrival_line_ids)
            ).options(
                joinedload(ArrivalPurchaseOrderLink.purchase_order_line).joinedload(PurchaseOrderLine.purchase_order),
            ).all()
            
            # Group links by arrival_line_id for quick access
            # Note: This pre-loads the links into the session, so when we access
            # arrival.po_line_links.all() later, SQLAlchemy will use the cached data
            links_by_arrival = {}
            for link in links:
                if link.arrival_line_id not in links_by_arrival:
                    links_by_arrival[link.arrival_line_id] = []
                links_by_arrival[link.arrival_line_id].append(link)

    @property
    def arrival_header(self) -> ArrivalHeader:
        """Get the arrival header."""
        return self._arrival_header
    
    @property
    def arrival_lines(self) -> list[ArrivalLine]:
        """Get all arrival lines for this package, loading if not already loaded."""
        if self._arrival_lines is None:
            self._load_arrival_lines()
        return self._arrival_lines or []
    
    @property
    def arrival_line_contexts(self) -> list[ArrivalLineContext]:
        """Get ArrivalLineContext instances for all arrival lines."""
        return [
            ArrivalLineContext(
                arrival_line.id,
                inventory_manager=self.inventory_manager,
                status_manager=self.status_manager,
            )
            for arrival_line in self.arrival_lines
        ]
    
    @property
    def linkage_manager(self) -> ArrivalLinkageManager:
        """
        Convenience accessor for the arrival linkage manager.
        
        The manager is stateless and can be used for linking/unlinking
        part arrivals to PO lines.
        """
        return ArrivalLinkageManager()
    
    def get_package_with_relationships(self) -> ArrivalHeader:
        """
        Get the arrival header with all common relationships eager loaded.
        This is a convenience method for routes.
        """
        return self.arrival_header
    
    def get_part_arrivals_with_relationships(self) -> list[ArrivalLine]:
        """
        Get all part arrivals with relationships eager loaded.
        This is a convenience method for routes.
        """
        return self.arrival_lines
    
    def get_received_arrivals_with_links(self) -> list[tuple[ArrivalLine, list]]:
        """
        Get all received arrival lines with their linked PO line information.
        
        Returns:
            List of tuples: (arrival_line, list of po_line_links)
            Each po_line_link is an ArrivalPurchaseOrderLink instance
        """
        received_arrivals = []
        for arrival in self.arrival_lines:
            if arrival.status == "Received":
                # Get all PO line links for this arrival
                po_line_links = arrival.po_line_links.all()
                if po_line_links:
                    received_arrivals.append((arrival, list(po_line_links)))
        return received_arrivals
    
    def get_part_demand_links_for_po_line(self, po_line_id: int) -> list:
        """
        Get all part demand links for a specific PO line.
        
        Args:
            po_line_id: ID of the purchase order line
            
        Returns:
            List of PartDemandPurchaseOrderLink objects, ordered by ID
        """
        from app.data.inventory.purchasing.part_demand_link import PartDemandPurchaseOrderLink
        return (
            PartDemandPurchaseOrderLink.query.filter_by(purchase_order_line_id=po_line_id)
            .order_by(PartDemandPurchaseOrderLink.id.asc())
            .all()
        )
    
    def direct_issue_to_part_demands(self) -> tuple[bool, str]:
        """
        Issue received arrival quantities directly to linked part demands.
        
        For each received arrival:
        - Gets all linked PO lines (via ArrivalPurchaseOrderLink)
        - For each PO line, gets linked part demands
        - Issues quantities respecting the linked quantity from the arrival
        
        Returns:
            (issued_any: bool, message: str)
        """
        from app.data.inventory.arrivals.purchase_order_link import ArrivalPurchaseOrderLink
        
        received_arrivals = self.get_received_arrivals_with_links()
        if not received_arrivals:
            return False, "Nothing to direct issue (no received arrivals found)."
        
        issued_any = False
        
        for arrival, po_line_links in received_arrivals:
            remaining_to_issue = float(arrival.quantity_received or 0.0)
            if remaining_to_issue <= 0:
                continue
            
            # Process each linked PO line
            for po_link in po_line_links:
                if remaining_to_issue <= 0:
                    break
                
                po_line = po_link.purchase_order_line
                if po_line is None:
                    continue
                
                # Get part demand links for this PO line
                demand_links = self.get_part_demand_links_for_po_line(po_line.id)
                
                # Issue quantities to part demands, respecting the linked quantity
                linked_qty_available = float(po_link.quantity_linked or 0.0)
                
                for demand_link in demand_links:
                    if remaining_to_issue <= 0 or linked_qty_available <= 0:
                        break
                    
                    qty = min(
                        float(demand_link.quantity_allocated or 0.0),
                        remaining_to_issue,
                        linked_qty_available
                    )
                    if qty <= 0:
                        continue
                    
                    self.inventory_manager.issue_to_part_demand(
                        part_demand_id=demand_link.part_demand_id,
                        storeroom_id=arrival.storeroom_id,
                        major_location_id=arrival.major_location_id,
                        quantity_to_issue=qty,
                        from_location_id=None,
                        from_bin_id=None,
                    )
                    self.status_manager.propagate_demand_status_update(demand_link.part_demand_id, "Issued")
                    issued_any = True
                    remaining_to_issue -= qty
                    linked_qty_available -= qty
        
        if issued_any:
            return True, "Direct issue completed: received quantities issued to linked part demands."
        else:
            return False, "Nothing to direct issue (no quantities could be issued)."


