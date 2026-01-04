"""
Compatibility package.

Existing code may import `app.buisness.inventory.inventory.*`. During the rebuild, the new
implementation lives under `stock/` (and `arrivals/`, `purchase_orders/`, etc).
"""

from app.buisness.inventory.stock.inventory_manager import InventoryManager
from app.buisness.inventory.stock.storeroom_manager import StoreroomManager

__all__ = [
    "InventoryManager",
    "StoreroomManager",
]


