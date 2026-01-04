"""
Stock/location data models (inventory).

This package provides clearer import paths for stock entities while reusing the canonical
model definitions in `app.data.inventory.inventory.*`.
"""

from app.data.inventory.inventory.bin_prototype import BinPrototype
from app.data.inventory.inventory.active_inventory import ActiveInventory
from app.data.inventory.inventory.inventory_summary import InventorySummary
from app.data.inventory.inventory.storeroom import Storeroom

__all__ = [
    "BinPrototype",
    "ActiveInventory",
    "InventorySummary",
    "Storeroom",
]


