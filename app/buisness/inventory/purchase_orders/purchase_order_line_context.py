from __future__ import annotations

from app.buisness.inventory.status.status_manager import InventoryStatusManager
from app.data.inventory.ordering.purchase_order_line import PurchaseOrderLine


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


