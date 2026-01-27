from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app import db
from app.buisness.inventory.shared.status_validator import InventoryStatusValidator
from app.data.inventory.arrivals.arrival_line import ArrivalLine
from app.data.inventory.purchasing.purchase_order_header import PurchaseOrderHeader
from app.data.inventory.purchasing.purchase_order_line import PurchaseOrderLine
from app.data.maintenance.base.part_demands import PartDemand


@dataclass(frozen=True)
class StatusChange:
    entity_type: str
    entity_id: int
    from_status: str | None
    to_status: str


class InventoryStatusManager:
    """
    Inventory-centric status manager.

    This class is responsible for:
    - validating transitions
    - setting the status field on the target entity
    - propagating to linked entities where required by the lifecycle docs
    """

    def _set_status(self, entity_type: str, entity, new_status: str) -> StatusChange:
        old = getattr(entity, "status", None)
        if old == new_status:
            return StatusChange(entity_type, entity.id, old, new_status)
        if old is not None and not InventoryStatusValidator.can_transition(entity_type, old, new_status):
            raise ValueError(f"Invalid status transition for {entity_type} {entity.id}: {old} -> {new_status}")
        entity.status = new_status
        return StatusChange(entity_type, entity.id, old, new_status)

    def propagate_part_arrival_status_update(self, part_arrival_id: int, new_status: str) -> list[StatusChange]:
        arrival = ArrivalLine.query.get_or_404(part_arrival_id)
        changes: list[StatusChange] = [self._set_status("part_arrival", arrival, new_status)]

        # When an arrival is accepted/rejected, the PO line completion logic is updated elsewhere.
        # This propagation function exists mainly to standardize how we set arrival status.
        arrival.updated_at = datetime.utcnow()
        return changes

    def propagate_purchase_order_line_update(self, purchase_order_line_id: int) -> list[StatusChange]:
        """
        Recalculate and update PO line status and downstream demand statuses based on accepted+rejected.
        """
        po_line = PurchaseOrderLine.query.get_or_404(purchase_order_line_id)
        changes: list[StatusChange] = []

        if po_line.quantity_received_total >= po_line.quantity_ordered:
            if po_line.status != "Complete":
                changes.append(self._set_status("purchase_order_line", po_line, "Complete"))
                # Set linked demands to Arrived (lifecycle: line complete -> demand arrived)
                for demand in po_line.part_demands:
                    if getattr(demand, "status", None) not in ("Issued", "Installed"):
                        changes.append(self._set_status("part_demand", demand, "Arrived"))

        return changes

    def propagate_purchase_order_status(self, purchase_order_id: int, new_status: str) -> list[StatusChange]:
        po = PurchaseOrderHeader.query.get_or_404(purchase_order_id)
        changes: list[StatusChange] = [self._set_status("purchase_order", po, new_status)]

        # Create event when status changes to "Ordered" and event_id is not already set
        if new_status == "Ordered" and po.event_id is None:
            from app.data.core.event_info.event import Event
            event_description = f"Purchase Order {po.po_number} - {po.vendor_name}"
            if po.notes:
                event_description += f": {po.notes[:100]}"  # Limit description length
            
            po.event_id = Event.add_event(
                event_type="purchase_order",
                description=event_description,
                user_id=po.updated_by_id or po.created_by_id,
                major_location_id=po.major_location_id
            )

        # Cascade PO-level status to lines where it makes sense
        if new_status in ("Ordered", "Shipped"):
            for line in po.purchase_order_lines:
                if line.status not in ("Complete", "Cancelled"):
                    line.status = "Ordered" if new_status == "Ordered" else "Shipped"
                    changes.append(self._set_status("purchase_order_line", line, "Shipped" if new_status == "Shipped" else "Ordered"))
                    # Update demands as well
                    for demand in line.part_demands:
                        if getattr(demand, "status", None) not in ("Issued", "Installed"):
                            changes.append(self._set_status("part_demand", demand, new_status))

        if new_status == "Arrived":
            # PO arrived only when all lines complete; enforce on call sites
            for line in po.purchase_order_lines:
                if line.status != "Complete":
                    raise ValueError("Cannot mark purchase order Arrived until all lines are Complete")
        db.session.commit()
        return changes

    def propagate_demand_status_update(self, part_demand_id: int, new_status: str) -> list[StatusChange]:
        demand = PartDemand.query.get_or_404(part_demand_id)
        return [self._set_status("part_demand", demand, new_status)]

    def update_purchase_order_status(self, purchase_order_id: int, new_status: str) -> list[StatusChange]:
        return self.propagate_purchase_order_status(purchase_order_id, new_status)

    def update_purchase_order_line_status(self, purchase_order_line_id: int, new_status: str) -> list[StatusChange]:
        line = PurchaseOrderLine.query.get_or_404(purchase_order_line_id)
        return [self._set_status("purchase_order_line", line, new_status)]

    def update_part_demand_status(self, part_demand_id: int, new_status: str) -> list[StatusChange]:
        return self.propagate_demand_status_update(part_demand_id, new_status)


