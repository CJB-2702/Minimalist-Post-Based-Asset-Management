from __future__ import annotations

from datetime import datetime

from app import db
from app.data.inventory.inventory.active_inventory import ActiveInventory
from app.data.inventory.inventory.inventory_movement import InventoryMovement
from app.data.inventory.inventory.inventory_summary import InventorySummary
from app.data.inventory.inventory.part_issue import PartIssue
from app.data.inventory.ordering.purchase_order_line import PurchaseOrderLine
from app.data.maintenance.base.part_demands import PartDemand
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet

# Configuration flag: if True, delete active inventory rows when quantity reaches zero
DELETE_EMPTY_ACTIVE_ROWS = True


class InventoryManager:
    """
    Core inventory operations.

    Responsibilities (per lifecycle docs):
    - Maintain ActiveInventory (bin-level) as the source of truth for locations
    - Maintain InventorySummary (part-level) for fast lookups
    - Create InventoryMovement rows for traceability
    """

    def _get_or_create_summary(self, part_id: int) -> InventorySummary:
        summary = InventorySummary.query.filter_by(part_id=part_id).first()
        if summary is None:
            summary = InventorySummary(part_id=part_id, quantity_on_hand_total=0.0)
            db.session.add(summary)
        return summary

    def _apply_summary_receipt(self, summary: InventorySummary, qty_delta: float, unit_cost: float | None) -> None:
        old_qty = summary.quantity_on_hand_total or 0.0
        new_qty = old_qty + qty_delta
        summary.quantity_on_hand_total = new_qty
        if unit_cost is not None and qty_delta > 0:
            # rolling average cost on receipt
            if summary.unit_cost_avg is None or old_qty <= 0:
                summary.unit_cost_avg = unit_cost
            else:
                summary.unit_cost_avg = ((summary.unit_cost_avg * old_qty) + (unit_cost * qty_delta)) / new_qty
        summary.last_updated_at = datetime.utcnow()

    def _apply_summary_issue(self, summary: InventorySummary, qty_delta: float) -> None:
        summary.quantity_on_hand_total = max(0.0, (summary.quantity_on_hand_total or 0.0) + qty_delta)
        summary.last_updated_at = datetime.utcnow()

    def _get_or_create_active_inventory(
        self,
        part_id: int,
        storeroom_id: int,
        *,
        location_id: int | None = None,
        bin_id: int | None = None,
    ) -> ActiveInventory:
        query = ActiveInventory.query.filter_by(
            part_id=part_id,
            storeroom_id=storeroom_id,
            location_id=location_id,
            bin_id=bin_id,
        )
        inv = query.first()
        if inv is None:
            inv = ActiveInventory(
                part_id=part_id,
                storeroom_id=storeroom_id,
                location_id=location_id,
                bin_id=bin_id,
                quantity_on_hand=0.0,
                quantity_allocated=0.0,
            )
            db.session.add(inv)
        return inv

    def record_receipt_into_unassigned_bin(
        self,
        *,
        part_id: int,
        storeroom_id: int,
        major_location_id: int,
        quantity_received_accepted: float,
        purchase_order_line_id: int | None,
        part_arrival_id: int | None,
    ) -> InventoryMovement:
        if quantity_received_accepted <= 0:
            raise ValueError("quantity_received_accepted must be > 0")

        po_line: PurchaseOrderLine | None = None
        unit_cost: float | None = None
        if purchase_order_line_id is not None:
            po_line = PurchaseOrderLine.query.get(purchase_order_line_id)
            unit_cost = po_line.unit_cost if po_line else None

        inv = self._get_or_create_active_inventory(
            part_id,
            storeroom_id,
            location_id=None,
            bin_id=None,
        )
        inv.quantity_on_hand = (inv.quantity_on_hand or 0.0) + quantity_received_accepted
        inv.last_movement_date = datetime.utcnow()

        # Note: We don't delete here even if DELETE_EMPTY_ACTIVE_ROWS is True
        # because this is a receipt operation that should always result in positive inventory

        summary = self._get_or_create_summary(part_id)
        self._apply_summary_receipt(summary, quantity_received_accepted, unit_cost)

        movement = InventoryMovement(
            part_id=part_id,
            major_location_id=major_location_id,
            storeroom_id=storeroom_id,
            movement_type="Receipt",
            quantity_delta=quantity_received_accepted,
            unit_cost=unit_cost,
            part_arrival_id=part_arrival_id,
            reference_type="purchase_order_line" if purchase_order_line_id else None,
            reference_id=purchase_order_line_id,
            to_major_location_id=major_location_id,
            to_storeroom_id=storeroom_id,
            to_location_id=None,
            to_bin_id=None,
        )
        db.session.add(movement)
        return movement

    def assign_unassigned_to_bin(
        self,
        *,
        part_id: int,
        storeroom_id: int,
        major_location_id: int,
        quantity_to_move: float,
        to_location_id: int | None = None,
        to_bin_id: int | None = None,
    ) -> tuple[InventoryMovement, InventoryMovement]:
        if quantity_to_move <= 0:
            raise ValueError("quantity_to_move must be > 0")

        src = self._get_or_create_active_inventory(
            part_id,
            storeroom_id,
            location_id=None,
            bin_id=None,
        )
        if (src.quantity_on_hand or 0.0) < quantity_to_move:
            raise ValueError("Not enough quantity in unassigned bin to move")

        dst = self._get_or_create_active_inventory(
            part_id,
            storeroom_id,
            location_id=to_location_id,
            bin_id=to_bin_id,
        )

        src.quantity_on_hand -= quantity_to_move
        dst.quantity_on_hand = (dst.quantity_on_hand or 0.0) + quantity_to_move
        now = datetime.utcnow()
        src.last_movement_date = now
        dst.last_movement_date = now

        # Delete empty active inventory row if flag is enabled
        if DELETE_EMPTY_ACTIVE_ROWS and (src.quantity_on_hand or 0.0) <= 0:
            db.session.delete(src)

        neg = InventoryMovement(
            part_id=part_id,
            major_location_id=major_location_id,
            storeroom_id=storeroom_id,
            movement_type="BinTransfer",
            quantity_delta=-quantity_to_move,
            from_major_location_id=major_location_id,
            from_storeroom_id=storeroom_id,
            from_location_id=None,
            from_bin_id=None,
            to_major_location_id=major_location_id,
            to_storeroom_id=storeroom_id,
            to_location_id=to_location_id,
            to_bin_id=to_bin_id,
        )
        db.session.add(neg)

        pos = InventoryMovement(
            part_id=part_id,
            major_location_id=major_location_id,
            storeroom_id=storeroom_id,
            movement_type="BinTransfer",
            quantity_delta=quantity_to_move,
            previous_movement_id=None,  # set after flush if desired
            from_major_location_id=major_location_id,
            from_storeroom_id=storeroom_id,
            from_location_id=None,
            from_bin_id=None,
            to_major_location_id=major_location_id,
            to_storeroom_id=storeroom_id,
            to_location_id=to_location_id,
            to_bin_id=to_bin_id,
        )
        db.session.add(pos)

        # no InventorySummary change (location-only)
        return neg, pos

    def transfer_between_bins(
        self,
        *,
        part_id: int,
        storeroom_id: int,
        major_location_id: int,
        quantity_to_move: float,
        from_location_id: int | None = None,
        from_bin_id: int | None = None,
        to_location_id: int | None = None,
        to_bin_id: int | None = None,
    ) -> tuple[InventoryMovement, InventoryMovement]:
        if quantity_to_move <= 0:
            raise ValueError("quantity_to_move must be > 0")

        src = self._get_or_create_active_inventory(
            part_id,
            storeroom_id,
            location_id=from_location_id,
            bin_id=from_bin_id,
        )
        if (src.quantity_on_hand or 0.0) < quantity_to_move:
            raise ValueError("Not enough quantity in source bin to transfer")

        dst = self._get_or_create_active_inventory(
            part_id,
            storeroom_id,
            location_id=to_location_id,
            bin_id=to_bin_id,
        )

        src.quantity_on_hand -= quantity_to_move
        dst.quantity_on_hand = (dst.quantity_on_hand or 0.0) + quantity_to_move
        now = datetime.utcnow()
        src.last_movement_date = now
        dst.last_movement_date = now

        # Delete empty active inventory row if flag is enabled
        if DELETE_EMPTY_ACTIVE_ROWS and (src.quantity_on_hand or 0.0) <= 0:
            db.session.delete(src)

        neg = InventoryMovement(
            part_id=part_id,
            major_location_id=major_location_id,
            storeroom_id=storeroom_id,
            movement_type="BinTransfer",
            quantity_delta=-quantity_to_move,
            from_major_location_id=major_location_id,
            from_storeroom_id=storeroom_id,
            from_location_id=from_location_id,
            from_bin_id=from_bin_id,
            to_major_location_id=major_location_id,
            to_storeroom_id=storeroom_id,
            to_location_id=to_location_id,
            to_bin_id=to_bin_id,
        )
        db.session.add(neg)

        pos = InventoryMovement(
            part_id=part_id,
            major_location_id=major_location_id,
            storeroom_id=storeroom_id,
            movement_type="BinTransfer",
            quantity_delta=quantity_to_move,
            previous_movement_id=neg.id if neg.id else None,
            from_major_location_id=major_location_id,
            from_storeroom_id=storeroom_id,
            from_location_id=from_location_id,
            from_bin_id=from_bin_id,
            to_major_location_id=major_location_id,
            to_storeroom_id=storeroom_id,
            to_location_id=to_location_id,
            to_bin_id=to_bin_id,
        )
        db.session.add(pos)

        # no InventorySummary change (location-only)
        return neg, pos

    def transfer_cross_storeroom(
        self,
        *,
        part_id: int,
        quantity_to_move: float,
        from_storeroom_id: int,
        from_major_location_id: int,
        from_location_id: int | None = None,
        from_bin_id: int | None = None,
        to_storeroom_id: int,
        to_major_location_id: int,
        to_location_id: int | None = None,
        to_bin_id: int | None = None,
    ) -> tuple[InventoryMovement, InventoryMovement]:
        """
        Transfer inventory between different storerooms (or same storeroom with different locations).
        
        Args:
            part_id: Part to transfer
            quantity_to_move: Quantity to move (must be > 0)
            from_storeroom_id: Source storeroom ID
            from_major_location_id: Source major location ID
            from_location_id: Source location ID (optional)
            from_bin_id: Source bin ID (optional)
            to_storeroom_id: Destination storeroom ID
            to_major_location_id: Destination major location ID
            to_location_id: Destination location ID (optional)
            to_bin_id: Destination bin ID (optional)
            
        Returns:
            Tuple of (negative movement, positive movement)
        """
        if quantity_to_move <= 0:
            raise ValueError("quantity_to_move must be > 0")

        # Get source inventory
        src = self._get_or_create_active_inventory(
            part_id,
            from_storeroom_id,
            location_id=from_location_id,
            bin_id=from_bin_id,
        )
        if (src.quantity_on_hand or 0.0) < quantity_to_move:
            raise ValueError("Not enough quantity in source to transfer")

        # Get or create destination inventory
        dst = self._get_or_create_active_inventory(
            part_id,
            to_storeroom_id,
            location_id=to_location_id,
            bin_id=to_bin_id,
        )

        # Update quantities
        src.quantity_on_hand -= quantity_to_move
        dst.quantity_on_hand = (dst.quantity_on_hand or 0.0) + quantity_to_move
        now = datetime.utcnow()
        src.last_movement_date = now
        dst.last_movement_date = now

        # Delete empty active inventory row if flag is enabled
        if DELETE_EMPTY_ACTIVE_ROWS and (src.quantity_on_hand or 0.0) <= 0:
            db.session.delete(src)

        # Create negative movement (from source)
        neg = InventoryMovement(
            part_id=part_id,
            major_location_id=from_major_location_id,
            storeroom_id=from_storeroom_id,
            movement_type="Relocation",
            quantity_delta=-quantity_to_move,
            from_major_location_id=from_major_location_id,
            from_storeroom_id=from_storeroom_id,
            from_location_id=from_location_id,
            from_bin_id=from_bin_id,
            to_major_location_id=to_major_location_id,
            to_storeroom_id=to_storeroom_id,
            to_location_id=to_location_id,
            to_bin_id=to_bin_id,
        )
        db.session.add(neg)

        # Create positive movement (to destination)
        pos = InventoryMovement(
            part_id=part_id,
            major_location_id=to_major_location_id,
            storeroom_id=to_storeroom_id,
            movement_type="Relocation",
            quantity_delta=quantity_to_move,
            previous_movement_id=neg.id if neg.id else None,
            from_major_location_id=from_major_location_id,
            from_storeroom_id=from_storeroom_id,
            from_location_id=from_location_id,
            from_bin_id=from_bin_id,
            to_major_location_id=to_major_location_id,
            to_storeroom_id=to_storeroom_id,
            to_location_id=to_location_id,
            to_bin_id=to_bin_id,
        )
        db.session.add(pos)

        # no InventorySummary change (location-only transfer)
        return neg, pos

    def issue_to_part_demand(
        self,
        *,
        part_demand_id: int,
        storeroom_id: int,
        major_location_id: int,
        quantity_to_issue: float,
        from_location_id: int | None = None,
        from_bin_id: int | None = None,
        issued_by_id: int | None = None,
    ) -> tuple[InventoryMovement, PartIssue]:
        if quantity_to_issue <= 0:
            raise ValueError("quantity_to_issue must be > 0")

        demand = PartDemand.query.get_or_404(part_demand_id)
        part_id = demand.part_id

        # Get Action and MaintenanceActionSet to get asset_id
        action = Action.query.get_or_404(demand.action_id)
        maintenance_action_set = MaintenanceActionSet.query.get_or_404(action.maintenance_action_set_id)
        asset_id = maintenance_action_set.asset_id  # Enforce asset_id from MaintenanceActionSet

        src = self._get_or_create_active_inventory(
            part_id,
            storeroom_id,
            location_id=from_location_id,
            bin_id=from_bin_id,
        )
        if (src.quantity_on_hand or 0.0) < quantity_to_issue:
            raise ValueError("Not enough quantity to issue")

        src.quantity_on_hand -= quantity_to_issue
        src.last_movement_date = datetime.utcnow()

        # Delete empty active inventory row if flag is enabled
        if DELETE_EMPTY_ACTIVE_ROWS and (src.quantity_on_hand or 0.0) <= 0:
            db.session.delete(src)

        summary = self._get_or_create_summary(part_id)
        self._apply_summary_issue(summary, -quantity_to_issue)

        # Get unit cost from summary
        unit_cost_at_issue = summary.unit_cost_avg if summary else None
        total_cost = (unit_cost_at_issue * quantity_to_issue) if unit_cost_at_issue else None

        # Create InventoryMovement first (without part_issue_id - will set after PartIssue is created)
        movement = InventoryMovement(
            part_id=part_id,
            major_location_id=major_location_id,
            storeroom_id=storeroom_id,
            movement_type="Issue",
            quantity_delta=-quantity_to_issue,
            from_major_location_id=major_location_id,
            from_storeroom_id=storeroom_id,
            from_location_id=from_location_id,
            from_bin_id=from_bin_id,
            unit_cost=unit_cost_at_issue,
        )
        db.session.add(movement)
        db.session.flush()  # Flush to get movement.id for PartIssue

        # Create PartIssue linked to the movement
        part_issue = PartIssue(
            inventory_movement_id=movement.id,
            part_id=part_id,
            quantity_issued=quantity_to_issue,
            unit_cost_at_issue=unit_cost_at_issue,
            total_cost=total_cost,
            part_demand_id=demand.id,
            asset_id=asset_id,  # From MaintenanceActionSet, enforced override
            issue_type='ForPartDemand',
            issue_date=datetime.utcnow(),
            issued_from_storeroom_id=storeroom_id,
            issued_from_location_id=from_location_id,
            issued_from_bin_id=from_bin_id,
            requested_by_id=demand.requested_by_id,
            issued_by_id=issued_by_id,
        )
        db.session.add(part_issue)
        db.session.flush()  # Flush to get part_issue.id
        
        # Link movement to part_issue
        movement.part_issue_id = part_issue.id

        return movement, part_issue

    def create_adjustment_movement(
        self,
        *,
        part_id: int,
        storeroom_id: int,
        major_location_id: int,
        quantity_delta: float,
        reason: str,
        location_id: int | None = None,
        bin_id: int | None = None,
    ) -> InventoryMovement:
        """
        Create an adjustment movement to correct inventory discrepancies.
        
        This method ensures that:
        - Only one ActiveInventory row exists per part+bin location combination
        - Zero inventory rows are deleted when DELETE_EMPTY_ACTIVE_ROWS is True
        - The unique constraint on part_id + bin location is maintained
        
        Args:
            part_id: Part to adjust
            storeroom_id: Storeroom where adjustment occurs
            major_location_id: Major location for the movement
            quantity_delta: Positive for increases, negative for decreases
            reason: Reason for the adjustment
            location_id: Optional location ID
            bin_id: Optional bin ID
            
        Returns:
            InventoryMovement: The created adjustment movement
        """
        if quantity_delta == 0:
            raise ValueError("quantity_delta cannot be zero for adjustments")
        
        # Get or create the active inventory record for this part+bin combination
        # The unique constraint ensures only one row exists per combination
        inv = self._get_or_create_active_inventory(
            part_id,
            storeroom_id,
            location_id=location_id,
            bin_id=bin_id,
        )
        
        # Update quantity
        old_qty = inv.quantity_on_hand or 0.0
        new_qty = old_qty + quantity_delta
        
        # Ensure quantity doesn't go negative (business rule)
        if new_qty < 0:
            raise ValueError(
                f"Adjustment would result in negative inventory. "
                f"Current: {old_qty}, Adjustment: {quantity_delta}, Result: {new_qty}"
            )
        
        inv.quantity_on_hand = new_qty
        inv.last_movement_date = datetime.utcnow()
        
        # Delete empty active inventory row if flag is enabled
        if DELETE_EMPTY_ACTIVE_ROWS and (inv.quantity_on_hand or 0.0) <= 0:
            db.session.delete(inv)
        
        # Update summary
        summary = self._get_or_create_summary(part_id)
        if quantity_delta > 0:
            # For positive adjustments, we don't update cost (no unit_cost provided)
            summary.quantity_on_hand_total = (summary.quantity_on_hand_total or 0.0) + quantity_delta
        else:
            # For negative adjustments, just reduce quantity
            summary.quantity_on_hand_total = max(0.0, (summary.quantity_on_hand_total or 0.0) + quantity_delta)
        summary.last_updated_at = datetime.utcnow()
        
        # Create adjustment movement
        movement = InventoryMovement(
            part_id=part_id,
            major_location_id=major_location_id,
            storeroom_id=storeroom_id,
            movement_type="Adjustment",
            quantity_delta=quantity_delta,
            reference_type="adjustment",
            reference_id=None,  # Could store adjustment reason ID if we had an adjustments table
            notes=reason,
            to_major_location_id=major_location_id,
            to_storeroom_id=storeroom_id,
            to_location_id=location_id,
            to_bin_id=bin_id,
        )
        db.session.add(movement)
        return movement

    def refresh_inventory_summary(self, *, part_ids: list[int] | None = None) -> None:
        """
        Rebuild InventorySummary totals from ActiveInventory.

        This is useful for integrity checks and rebuilds (no migrations).
        """
        query = db.session.query(ActiveInventory.part_id, db.func.sum(ActiveInventory.quantity_on_hand))
        if part_ids:
            query = query.filter(ActiveInventory.part_id.in_(part_ids))
        query = query.group_by(ActiveInventory.part_id)
        totals = {pid: float(total or 0.0) for pid, total in query.all()}

        target_part_ids = set(part_ids) if part_ids else set(totals.keys())
        for part_id in target_part_ids:
            summary = self._get_or_create_summary(part_id)
            summary.quantity_on_hand_total = totals.get(part_id, 0.0)
            summary.last_updated_at = datetime.utcnow()


