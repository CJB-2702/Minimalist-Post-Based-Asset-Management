"""
Compatibility module for legacy imports.

Re-exports `PurchaseOrderContext` from the new `purchase_orders` package.
"""

from app.buisness.inventory.purchase_orders.purchase_order_context import PurchaseOrderContext

__all__ = ["PurchaseOrderContext"]


