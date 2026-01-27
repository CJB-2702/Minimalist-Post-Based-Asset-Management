from __future__ import annotations

from datetime import datetime

from app import db
from app.buisness.inventory.arrivals.arrival_linkage_manager import ArrivalLinkageManager
from app.buisness.inventory.shared.status_manager import InventoryStatusManager
from app.buisness.inventory.inventory.inventory_manager import InventoryManager
from app.data.inventory.arrivals.arrival_line import ArrivalLine
from app.data.inventory.purchasing.purchase_order_line import PurchaseOrderLine


class ArrivalLineContext:
    """
    Handles operations for a single ArrivalLine.

    Provides convenient access to arrival line data and related operations.
    """

    def __init__(
        self,
        part_arrival_id: int,
        *,
        inventory_manager: InventoryManager | None = None,
        status_manager: InventoryStatusManager | None = None,
    ):
        self.part_arrival_id = part_arrival_id
        self.inventory_manager = inventory_manager or InventoryManager()
        self.status_manager = status_manager or InventoryStatusManager()

    @property
    def arrival(self) -> ArrivalLine:
        return ArrivalLine.query.get_or_404(self.part_arrival_id)
    
    @property
    def linkage_manager(self) -> ArrivalLinkageManager:
        """
        Convenience accessor for the arrival linkage manager.
        
        The manager is stateless and can be used for linking/unlinking
        this part arrival to PO lines.
        """
        return ArrivalLinkageManager()


