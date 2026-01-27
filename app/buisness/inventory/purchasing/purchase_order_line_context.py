from __future__ import annotations

from sqlalchemy.orm import joinedload

from app.buisness.inventory.shared.status_manager import InventoryStatusManager
from app.data.inventory.purchasing.part_demand_link import PartDemandPurchaseOrderLink
from app.data.inventory.purchasing.purchase_order_line import PurchaseOrderLine
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.part_demands import PartDemand


class PurchaseOrderLineContext:
    """
    Business wrapper around a purchase order line.
    """

    def __init__(self, purchase_order_line_id: int, *, status_manager: InventoryStatusManager | None = None):
        self.purchase_order_line_id = purchase_order_line_id
        self.status_manager = status_manager or InventoryStatusManager()

    @property
    def line(self) -> PurchaseOrderLine:
        return PurchaseOrderLine.query.get_or_404(self.purchase_order_line_id)

    def recalculate_completion(self) -> None:
        self.status_manager.propagate_purchase_order_line_update(self.purchase_order_line_id)

    def get_linked_demand_links(self) -> list[PartDemandPurchaseOrderLink]:
        """
        Get all linked demand links for this PO line with eager loading.
        
        Returns:
            List of PartDemandPurchaseOrderLink objects with eager-loaded relationships
        """
        return PartDemandPurchaseOrderLink.query.filter_by(
            purchase_order_line_id=self.purchase_order_line_id
        ).options(
            joinedload(PartDemandPurchaseOrderLink.part_demand)
            .joinedload(PartDemand.action)
            .joinedload(Action.maintenance_action_set)
        ).all()

    def get_linked_demands(self) -> list[PartDemand]:
        """
        Get all linked part demands for this PO line.
        
        Returns:
            List of PartDemand objects that are linked to this PO line
        """
        links = self.get_linked_demand_links()
        return [link.part_demand for link in links if link.part_demand]

    def get_quantity_allocated(self) -> float:
        """
        Calculate total quantity allocated to part demands on this PO line.
        
        Returns:
            Sum of all quantity_allocated from links to part demands
        """
        links = self.get_linked_demand_links()
        return sum(link.quantity_allocated for link in links)

    def get_quantity_available(self) -> float:
        """
        Calculate available quantity on this PO line (ordered - allocated).
        
        Returns:
            Quantity available for linking to new demands
        """
        line = self.line
        quantity_allocated = self.get_quantity_allocated()
        return line.quantity_ordered - quantity_allocated

    def get_allocation_percentage(self) -> float:
        """
        Calculate the percentage of ordered quantity that is allocated.
        
        Returns:
            Allocation percentage (0.0 to 100.0), or 0.0 if quantity_ordered is 0
        """
        line = self.line
        if line.quantity_ordered > 0:
            quantity_allocated = self.get_quantity_allocated()
            return (quantity_allocated / line.quantity_ordered) * 100.0
        return 0.0

    def get_linkable_demands(self, exclude_demand_ids: set[int]) -> list[PartDemand]:
        """
        Find unlinked part demands that match this PO line's part.
        
        Args:
            exclude_demand_ids: Set of demand IDs to exclude (already linked elsewhere)
        
        Returns:
            List of PartDemand objects that can be linked to this line,
            ordered by priority (desc) and id
        """
        line = self.line
        query = PartDemand.query.filter(
            PartDemand.part_id == line.part_id
        )
        
        if exclude_demand_ids:
            query = query.filter(PartDemand.id.not_in(exclude_demand_ids))
        
        return query.options(
            joinedload(PartDemand.action).joinedload(Action.maintenance_action_set)
        ).order_by(PartDemand.priority.desc(), PartDemand.id).all()


