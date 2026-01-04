from __future__ import annotations

from dataclasses import dataclass

from app.data.inventory.ordering.part_demand_purchase_order_line import PartDemandPurchaseOrderLink
from app.data.inventory.ordering.purchase_order_line import PurchaseOrderLine
from app.data.maintenance.base.part_demands import PartDemand


@dataclass(frozen=True)
class BrokenPurchaseOrderLink:
    link_id: int
    purchase_order_line_id: int | None
    part_demand_id: int | None
    reason: str


class PurchaseOrderLinkManager:
    """
    Link integrity tools for PO line <-> PartDemand links.
    """

    def detect_broken_links(self) -> list[BrokenPurchaseOrderLink]:
        broken: list[BrokenPurchaseOrderLink] = []
        for link in PartDemandPurchaseOrderLink.query.all():
            po_line = PurchaseOrderLine.query.get(link.purchase_order_line_id)
            demand = PartDemand.query.get(link.part_demand_id)
            if po_line is None:
                broken.append(
                    BrokenPurchaseOrderLink(
                        link_id=link.id,
                        purchase_order_line_id=link.purchase_order_line_id,
                        part_demand_id=link.part_demand_id,
                        reason="purchase_order_line_missing",
                    )
                )
            if demand is None:
                broken.append(
                    BrokenPurchaseOrderLink(
                        link_id=link.id,
                        purchase_order_line_id=link.purchase_order_line_id,
                        part_demand_id=link.part_demand_id,
                        reason="part_demand_missing",
                    )
                )
        return broken


