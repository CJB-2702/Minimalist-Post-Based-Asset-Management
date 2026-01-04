from __future__ import annotations

from app.buisness.inventory.stock.inventory_manager import InventoryManager


class StoreroomManager:
    """
    Storeroom-level convenience operations (bulk moves, transfers).
    """

    def __init__(self, storeroom_id: int, *, inventory_manager: InventoryManager | None = None):
        self.storeroom_id = storeroom_id
        self.inventory_manager = inventory_manager or InventoryManager()

    def assign_unassigned_to_bin(
        self,
        *,
        part_id: int,
        major_location_id: int,
        quantity_to_move: float,
        to_location_id: int | None = None,
        to_bin_id: int | None = None,
    ):
        return self.inventory_manager.assign_unassigned_to_bin(
            part_id=part_id,
            storeroom_id=self.storeroom_id,
            major_location_id=major_location_id,
            quantity_to_move=quantity_to_move,
            to_location_id=to_location_id,
            to_bin_id=to_bin_id,
        )


