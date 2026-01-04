"""
Compatibility module for legacy imports.

Re-exports `PurchaseOrderFactory` from the new `purchase_orders` package.
"""

from app.buisness.inventory.purchase_orders.purchase_order_factory import PurchaseOrderFactory

__all__ = ["PurchaseOrderFactory"]


