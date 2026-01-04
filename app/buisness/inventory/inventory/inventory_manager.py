"""
Compatibility module for legacy imports.

Re-exports `InventoryManager` from the new `stock` package.
"""

from app.buisness.inventory.stock.inventory_manager import InventoryManager

__all__ = ["InventoryManager"]


