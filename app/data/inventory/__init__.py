"""
Phase 6: Inventory and Purchasing System

This module implements a comprehensive inventory and purchasing system with:
- Purchase order management (ordering/)
- Part receiving and inspection (arrivals/)
- Inventory tracking with full traceability (inventory/)
- Integration with maintenance part demands

Architecture:
- ordering/ - Purchase order data models
- arrivals/ - Part arrival data models
- inventory/ - Inventory tracking data models
"""

from app.data.inventory.ordering import (
    PurchaseOrderHeader,
    PurchaseOrderLine,
    PartDemandPurchaseOrderLink
)
from app.data.inventory.arrivals import (
    PackageHeader,
    PartArrival
)
from app.data.inventory.inventory import (
    Storeroom,
    BinPrototype,
    ActiveInventory,
    InventoryMovement,
    InventorySummary,
    PartIssue,
)
from app.data.inventory.locations import (
    Location,
    Bin
)

__all__ = [
    'PurchaseOrderHeader',
    'PurchaseOrderLine',
    'PartDemandPurchaseOrderLink',
    'PackageHeader',
    'PartArrival',
    'Storeroom',
    'BinPrototype',
    'ActiveInventory',
    'InventoryMovement',
    'InventorySummary',
    'PartIssue',
    'Location',
    'Bin',
]
