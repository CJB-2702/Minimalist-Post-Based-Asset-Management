"""
Compatibility package.

Some existing blueprints import `app.buisness.inventory.ordering`. During the inventory rebuild,
the new business structure lives under `purchase_orders/`.

This package re-exports the purchase order business objects to keep imports working without
touching the presentation layer.
"""

from app.buisness.inventory.purchase_orders.purchase_order_context import PurchaseOrderContext
from app.buisness.inventory.purchase_orders.purchase_order_factory import PurchaseOrderFactory
from app.buisness.inventory.purchase_orders.purchase_order_line_context import PurchaseOrderLineContext
from app.buisness.inventory.purchase_orders.purchase_order_link_manager import PurchaseOrderLinkManager
from app.buisness.inventory.ordering.part_demand_manager import PartDemandManager

__all__ = [
    "PurchaseOrderContext",
    "PurchaseOrderFactory",
    "PurchaseOrderLineContext",
    "PurchaseOrderLinkManager",
    "PartDemandManager",
]


