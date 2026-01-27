from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import joinedload

from app import db
from app.buisness.inventory.shared.status_manager import InventoryStatusManager
from app.buisness.inventory.purchasing.purchase_order_line_context import PurchaseOrderLineContext
from app.data.inventory.purchasing.part_demand_link import PartDemandPurchaseOrderLink
from app.data.inventory.purchasing.purchase_order_header import PurchaseOrderHeader
from app.data.inventory.purchasing.purchase_order_line import PurchaseOrderLine
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.maintenance.base.part_demands import PartDemand
from app.services.inventory.purchasing.part_demand_search_service import PartDemandSearchService


@dataclass
class POLineWithDemands:
    """PO Line with its linked and linkable demands"""
    po_line: PurchaseOrderLine
    linked_demands: list[PartDemand]
    linkable_demands: list[PartDemand]
    quantity_available: float
    allocation_percentage: float


class PurchaseOrderContext:
    """
    Business wrapper around a purchase order.

    Kept intentionally small for the rebuild: routes/UI can compose richer flows later.
    """

    def __init__(self, purchase_order_id: int, *, status_manager: InventoryStatusManager | None = None):
        self.purchase_order_id = purchase_order_id
        self.status_manager = status_manager or InventoryStatusManager()
        self._purchase_order = None
        self._purchase_order_lines = None

    @property
    def purchase_order(self) -> PurchaseOrderHeader:
        if not self._purchase_order:
            self._purchase_order = PurchaseOrderHeader.query.get_or_404(self.purchase_order_id)
        return self._purchase_order

    @property
    def header(self) -> PurchaseOrderHeader:
        """Alias for purchase_order property for template compatibility"""
        return self.purchase_order

    def get_lines(self) -> list[PurchaseOrderLine]:
        if not self._purchase_order_lines:
            self._purchase_order_lines = list(self.purchase_order.purchase_order_lines)
        return self._purchase_order_lines

    @property
    def lines(self) -> list[PurchaseOrderLine]:
        """Property accessor for lines for template compatibility"""
        return self.get_lines()

    @property
    def line_contexts(self) -> list[PurchaseOrderLineContext]:
        return [PurchaseOrderLineContext(line.id, status_manager=self.status_manager) for line in self.get_lines()]
    
    @property
    def subtotal(self) -> float:
        """
        Calculate the subtotal (sum of all line totals).
        
        Returns:
            float: Sum of all line item totals
        """
        return sum(line.line_total for line in self.get_lines())

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
        
        Total = sum of all line totals + shipping_cost + tax_amount + other_amount
        
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
        
        # Add shipping, tax, and other_amount
        shipping = po.shipping_cost or 0.0
        tax = po.tax_amount or 0.0
        other = po.other_amount or 0.0
        
        po.total_cost = subtotal + shipping + tax + other

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

    def cancel_order(self, reason: str, user_id: int) -> None:
        """
        Cancel the purchase order.
        
        Changes status to Cancelled, which will:
        - Validate the status transition
        - Cascade status to lines and linked part demands
        
        Args:
            reason: Reason for cancellation
            user_id: ID of the user cancelling the order
            
        Raises:
            ValueError: If the PO cannot be cancelled from its current status
        """
        po = self.purchase_order
        
        # Validate that the PO can be cancelled
        # Generally, only Draft or Ordered POs can be cancelled
        if po.status in ("Cancelled", "Complete"):
            raise ValueError(f"Cannot cancel purchase order: current status is '{po.status}'")
        
        po.updated_by_id = user_id
        
        # Add reason to notes if provided
        if reason and reason.strip() and reason != "No reason provided":
            current_notes = po.notes or ""
            cancellation_note = f"\n\n[Cancelled: {reason}]"
            po.notes = current_notes + cancellation_note
        
        # Set status to Cancelled (this will validate transition and cascade to lines/demands)
        self.set_status("Cancelled")

    def get_all_linked_demand_ids(self) -> set[int]:
        """
        Get all part demand IDs that are linked to any line in this purchase order.
        
        Returns:
            Set of part_demand_ids that are already linked to any PO line in this PO
        """
        all_linked_demand_ids = (
            db.session.query(PartDemandPurchaseOrderLink.part_demand_id)
            .join(PurchaseOrderLine, PartDemandPurchaseOrderLink.purchase_order_line_id == PurchaseOrderLine.id)
            .filter(PurchaseOrderLine.purchase_order_id == self.purchase_order_id)
            .distinct()
            .all()
        )
        return {row[0] for row in all_linked_demand_ids}

    def get_po_lines_with_demands(self) -> list[POLineWithDemands]:
        """
        Get all PO lines for this PO, with:
        - Already linked demands
        - Available unlinked demands (matching part_id)
        - Allocation calculations
        """
        result = []
        all_linked_demand_ids = self.get_all_linked_demand_ids()
        
        for line in self.purchase_order.purchase_order_lines:
            line_context = PurchaseOrderLineContext(line.id, status_manager=self.status_manager)
            
            linked_demands = line_context.get_linked_demands()
            linkable_demands = line_context.get_linkable_demands(all_linked_demand_ids)
            quantity_available = line_context.get_quantity_available()
            allocation_percentage = line_context.get_allocation_percentage()
            
            result.append(POLineWithDemands(
                po_line=line,
                linked_demands=linked_demands,
                linkable_demands=linkable_demands,
                quantity_available=quantity_available,
                allocation_percentage=allocation_percentage
            ))
        
        return result

    def get_maintenance_events_with_demands(
        self,
        part_id: int | None = None,
        asset_id: int | None = None,
        make: str | None = None,
        model: str | None = None,
        asset_type_id: int | None = None,
        major_location_id: int | None = None,
        created_from: object | None = None,
        created_to: object | None = None,
        assigned_user_id: int | None = None,
    ) -> list[dict]:
        """
        Get maintenance events that have unlinked part demands.
        Optionally filter by part_id.
        """
        # Get all linked demand IDs
        all_linked_demand_ids = (
            db.session.query(PartDemandPurchaseOrderLink.part_demand_id)
            .distinct()
            .all()
        )
        all_linked_demand_ids = {row[0] for row in all_linked_demand_ids}
        
        # Query unlinked demands via shared inventory search service, then group into events.
        # We keep this portal-specific grouping logic here, but the search/filtering logic lives in the service.
        unlinked_demands = PartDemandSearchService.get_filtered_part_demands(
            part_id=part_id,
            asset_id=asset_id,
            asset_type_id=asset_type_id,
            make=make,
            model=model,
            assigned_to_id=assigned_user_id,
            major_location_id=major_location_id,
            maintenance_event_created_from=created_from,
            maintenance_event_created_to=created_to,
            exclude_part_demand_ids=all_linked_demand_ids,
            default_to_orderable=True,
            limit=2000,
        )
        
        # Group by maintenance event
        events_dict = {}
        for demand in unlinked_demands:
            if not demand.action or not demand.action.maintenance_action_set:
                continue
                
            mas = demand.action.maintenance_action_set

            event_id = mas.event_id
            
            if event_id not in events_dict:
                events_dict[event_id] = {
                    "event_id": event_id,
                    "maintenance_action_set": mas,
                    "demands": []
                }
            
            events_dict[event_id]["demands"].append(demand)
        
        return list(events_dict.values())


