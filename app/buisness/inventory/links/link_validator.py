from __future__ import annotations

from app.data.inventory.ordering.part_demand_purchase_order_line import PartDemandPurchaseOrderLink


class InventoryLinkValidator:
    """
    Link validation helpers for inventory relationships.

    For rebuild phase: keep it simple and explicit.
    """

    @staticmethod
    def validate_purchase_order_line_demand_link(purchase_order_line_id: int, part_demand_id: int) -> bool:
        link = PartDemandPurchaseOrderLink.query.filter_by(
            purchase_order_line_id=purchase_order_line_id,
            part_demand_id=part_demand_id,
        ).first()
        return link is not None


