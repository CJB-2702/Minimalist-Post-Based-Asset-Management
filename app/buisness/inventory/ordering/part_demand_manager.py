from __future__ import annotations

from app.buisness.inventory.purchase_orders.purchase_order_factory import PurchaseOrderFactory
from app.data.maintenance.base.part_demands import PartDemand


class PartDemandManager:
    """
    Compatibility manager used by existing inventory/supply blueprints.

    This manager focuses on demand-driven purchasing operations and delegates purchase order
    creation to `PurchaseOrderFactory`.
    """

    def __init__(self):
        self.purchase_order_factory = PurchaseOrderFactory()

    def get_open_demands_for_part(self, *, part_id: int) -> list[PartDemand]:
        """
        Return demand lines that are candidates for ordering.

        Lifecycle alignment: exclude demands already Ordered or later.
        """
        excluded = {"Ordered", "Shipped", "Arrived", "At Inventory", "Issued", "Installed"}
        return (
            PartDemand.query.filter_by(part_id=part_id)
            .filter(~PartDemand.status.in_(excluded))
            .order_by(PartDemand.created_at.asc())
            .all()
        )

    def create_purchase_order_from_demands(
        self,
        *,
        vendor_name: str,
        major_location_id: int,
        storeroom_id: int | None,
        part_demand_ids: list[int],
        unit_cost_by_part_demand_id: dict[int, float],
        created_by_id: int,
    ):
        return self.purchase_order_factory.create_from_part_demands(
            vendor_name=vendor_name,
            major_location_id=major_location_id,
            storeroom_id=storeroom_id,
            part_demand_ids=part_demand_ids,
            unit_cost_by_part_demand_id=unit_cost_by_part_demand_id,
            created_by_id=created_by_id,
        )


