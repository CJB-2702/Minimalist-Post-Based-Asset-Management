from __future__ import annotations

from datetime import datetime

from app import db
from app.buisness.inventory.arrivals.arrival_linkage_manager import ArrivalLinkageManager
from app.buisness.inventory.status.status_manager import InventoryStatusManager
from app.buisness.inventory.stock.inventory_manager import InventoryManager
from app.data.inventory.arrivals.part_arrival import PartArrival
from app.data.inventory.ordering.purchase_order_line import PurchaseOrderLine


class PartArrivalContext:
    """
    Handles inspection outcomes for a single PartArrival.

    Key lifecycle behaviors:
    - Partial accepted/rejected is represented by splitting into two PartArrival rows
    - Only Accepted creates inventory movement and updates ActiveInventory/InventorySummary
    - PO line completion uses accepted+rejected totals
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
    def arrival(self) -> PartArrival:
        return PartArrival.query.get_or_404(self.part_arrival_id)
    
    @property
    def linkage_manager(self) -> ArrivalLinkageManager:
        """
        Convenience accessor for the arrival linkage manager.
        
        The manager is stateless and can be used for linking/unlinking
        this part arrival to PO lines.
        """
        return ArrivalLinkageManager()

    def record_inspection(
        self,
        *,
        quantity_accepted: float,
        quantity_rejected: float,
        processed_by_user_id: int,
        create_receipt_movement: bool = True,
    ) -> tuple[PartArrival, PartArrival | None]:
        if quantity_accepted < 0 or quantity_rejected < 0:
            raise ValueError("quantities must be non-negative")
        if (quantity_accepted + quantity_rejected) <= 0:
            raise ValueError("must accept or reject a positive quantity")

        arrival = self.arrival
        if (arrival.quantity_received or 0.0) < (quantity_accepted + quantity_rejected):
            raise ValueError("accepted+rejected cannot exceed quantity_received on the arrival")

        # Update the original arrival to be the accepted portion (if any), otherwise rejected.
        rejected_arrival: PartArrival | None = None
        if quantity_accepted > 0 and quantity_rejected > 0:
            arrival.quantity_received = quantity_accepted
            arrival.status = "Accepted"

            rejected_arrival = PartArrival(
                package_header_id=arrival.package_header_id,
                purchase_order_line_id=arrival.purchase_order_line_id,
                part_id=arrival.part_id,
                major_location_id=arrival.major_location_id,
                storeroom_id=arrival.storeroom_id,
                quantity_received=quantity_rejected,
                condition=arrival.condition,
                inspection_notes=arrival.inspection_notes,
                received_date=arrival.received_date,
                status="Rejected",
                created_by_id=processed_by_user_id,
                updated_by_id=processed_by_user_id,
            )
            db.session.add(rejected_arrival)
        else:
            arrival.quantity_received = quantity_accepted if quantity_accepted > 0 else quantity_rejected
            arrival.status = "Accepted" if quantity_accepted > 0 else "Rejected"

        arrival.updated_by_id = processed_by_user_id
        arrival.updated_at = datetime.utcnow()

        po_line: PurchaseOrderLine | None = None
        if arrival.purchase_order_line_id is not None:
            # Update PO line accepted/rejected totals (only for linked arrivals)
            po_line = PurchaseOrderLine.query.get_or_404(arrival.purchase_order_line_id)
            if quantity_accepted > 0:
                po_line.quantity_accepted = (po_line.quantity_accepted or 0.0) + quantity_accepted
            if quantity_rejected > 0:
                po_line.quantity_rejected = (po_line.quantity_rejected or 0.0) + quantity_rejected

        # Receipt movement + inventory updates ONLY for accepted
        if create_receipt_movement and quantity_accepted > 0:
            if arrival.storeroom_id is None:
                raise ValueError("storeroom_id is required to receive inventory into unassigned bin")
            self.inventory_manager.record_receipt_into_unassigned_bin(
                part_id=arrival.part_id,
                storeroom_id=arrival.storeroom_id,
                major_location_id=arrival.major_location_id,
                quantity_received_accepted=quantity_accepted,
                purchase_order_line_id=arrival.purchase_order_line_id,
                part_arrival_id=arrival.id,
            )

        # Propagate statuses (arrival, PO line completion -> demands, etc.)
        self.status_manager.propagate_part_arrival_status_update(arrival.id, arrival.status)
        if po_line is not None:
            self.status_manager.propagate_purchase_order_line_update(po_line.id)

        # Lifecycle convention: once receipt movement is created, linked part demands are "At Inventory"
        if create_receipt_movement and quantity_accepted > 0 and po_line is not None:
            for demand in po_line.part_demands:
                if getattr(demand, "status", None) not in ("Issued", "Installed"):
                    self.status_manager.propagate_demand_status_update(demand.id, "At Inventory")

        return arrival, rejected_arrival


