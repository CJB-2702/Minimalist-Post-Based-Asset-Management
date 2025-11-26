"""
Phase 6: Inventory and Purchasing System

This module implements a comprehensive inventory and purchasing system with:
- Purchase order management
- Part receiving and inspection
- Inventory tracking with full traceability
- Integration with maintenance part demands

Architecture:
- base/ - Database models (CRUD only)
- managers/ - Business logic and workflows
- utils/ - Helper functions
"""

from app.data.inventory.base import (
    PurchaseOrderHeader,
    PurchaseOrderLine,
    PartDemandPurchaseOrderLine,
    PackageHeader,
    PartArrival,
    ActiveInventory,
    InventoryMovement
)

__all__ = [
    'PurchaseOrderHeader',
    'PurchaseOrderLine',
    'PartDemandPurchaseOrderLine',
    'PackageHeader',
    'PartArrival',
    'ActiveInventory',
    'InventoryMovement'
]

