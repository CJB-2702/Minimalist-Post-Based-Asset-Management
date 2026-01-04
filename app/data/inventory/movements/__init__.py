"""
Movement/audit data models (inventory).

This package provides clearer import paths for movement entities while reusing the canonical
model definitions in `app.data.inventory.inventory.*`.
"""

from app.data.inventory.inventory.inventory_movement import InventoryMovement

__all__ = [
    "InventoryMovement",
]


