"""
PartDemandManager

Business-layer manager for generic PartDemand modifications (updators).
Routes should call a service interface, which delegates to this manager.
"""

from __future__ import annotations

from typing import Optional, Tuple

from app import db
from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
from app.buisness.maintenance.base.narrator import MaintenanceNarrator
from app.data.maintenance.base.part_demands import PartDemand
from app.data.maintenance.base.actions import Action
from app.data.core.supply.part_definition import PartDefinition


class PartDemandManager:
    """
    Handles PartDemand status transitions and edits with consistent narration.

    Returns the resolved `event_id` for redirecting.
    """

    @staticmethod
    def _load_context(part_demand_id: int) -> Tuple[PartDemand, Action, MaintenanceContext, int]:
        part_demand = PartDemand.query.get(part_demand_id)
        if not part_demand:
            raise ValueError("Part demand not found")

        action = Action.query.get(part_demand.action_id)
        if not action:
            raise ValueError("Action not found for part demand")

        maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
        event_id = maintenance_context.event_id
        if not event_id:
            raise ValueError("Maintenance event not found")

        return part_demand, action, maintenance_context, event_id

    @staticmethod
    def _part_name(part_id: int) -> str:
        part = PartDefinition.query.get(part_id)
        return part.part_name if part else f"Part #{part_id}"

    def issue(self, *, part_demand_id: int, user_id: int, username: str) -> int:
        part_demand, _action, maintenance_context, event_id = self._load_context(part_demand_id)

        part_demand.status = "Issued"
        db.session.commit()

        maintenance_context.add_comment(
            user_id=user_id,
            content=MaintenanceNarrator.part_issued(
                self._part_name(part_demand.part_id),
                part_demand.quantity_required,
                username,
            ),
            is_human_made=False,
        )
        db.session.commit()

        return event_id

    def cancel_by_technician(self, *, part_demand_id: int, user_id: int, username: str, reason: str) -> int:
        part_demand, _action, maintenance_context, event_id = self._load_context(part_demand_id)

        if part_demand.status == "Issued":
            raise ValueError("Cannot cancel an issued part demand")

        if not reason or not reason.strip():
            raise ValueError("Cancellation comment is required")

        part_demand.status = "Cancelled by Technician"
        db.session.commit()

        maintenance_context.add_comment(
            user_id=user_id,
            content=MaintenanceNarrator.part_cancelled(
                self._part_name(part_demand.part_id),
                part_demand.quantity_required,
                username,
                reason.strip(),
            ),
            is_human_made=False,
        )
        db.session.commit()

        return event_id

    def undo_to_planned(self, *, part_demand_id: int, user_id: int, username: str) -> int:
        part_demand, _action, maintenance_context, event_id = self._load_context(part_demand_id)

        if part_demand.status not in ["Cancelled by Technician", "Cancelled by Supply"]:
            raise ValueError("Can only undo cancelled part demands")

        part_demand.status = "Planned"
        db.session.commit()

        maintenance_context.add_comment(
            user_id=user_id,
            content=MaintenanceNarrator.part_reset_to_planned(
                self._part_name(part_demand.part_id),
                part_demand.quantity_required,
                username,
            ),
            is_human_made=False,
        )
        db.session.commit()

        return event_id

    def update(
        self,
        *,
        part_demand_id: int,
        user_id: int,
        username: str,
        quantity_required: Optional[float] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        part_demand, _action, maintenance_context, event_id = self._load_context(part_demand_id)

        valid_statuses = [
            "Planned",
            "Pending Manager Approval",
            "Pending Inventory Approval",
            "Ordered",
            "Issued",
            "Rejected",
            "Backordered",
            "Cancelled by Technician",
            "Cancelled by Supply",
        ]
        if status and status not in valid_statuses:
            raise ValueError("Invalid status")

        valid_priorities = ["Low", "Medium", "High", "Critical"]
        if priority and priority not in valid_priorities:
            priority = None

        if quantity_required is not None:
            if quantity_required <= 0:
                raise ValueError("Quantity must be greater than 0")
            part_demand.quantity_required = quantity_required

        if status is not None:
            part_demand.status = status
        if priority is not None:
            part_demand.priority = priority
        if notes is not None:
            part_demand.notes = notes

        part_demand.updated_by_id = user_id
        db.session.commit()

        maintenance_context.add_comment(
            user_id=user_id,
            content=MaintenanceNarrator.part_updated(
                self._part_name(part_demand.part_id),
                part_demand.quantity_required,
                username,
                status=status,
            ),
            is_human_made=True,
        )
        db.session.commit()

        return event_id

    # === Creators (must be business layer) ===
    def create_for_action(
        self,
        *,
        action_id: int,
        part_id: int,
        quantity_required: float,
        notes: Optional[str],
        user_id: int,
        username: str,
        initial_status: str = "Pending Manager Approval",
    ) -> int:
        """
        Create a new PartDemand row for an action and add a machine comment.

        Returns:
            event_id for redirecting
        """
        action = Action.query.get(action_id)
        if not action:
            raise ValueError("Action not found")

        maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
        event_id = maintenance_context.event_id
        if not event_id:
            raise ValueError("Maintenance event not found")

        if quantity_required <= 0:
            raise ValueError("Quantity must be greater than 0")

        part_demand = PartDemand(
            action_id=action_id,
            part_id=part_id,
            quantity_required=quantity_required,
            notes=notes,
            status=initial_status,
            requested_by_id=user_id,
            created_by_id=user_id,
            updated_by_id=user_id,
        )
        db.session.add(part_demand)
        db.session.commit()

        maintenance_context.add_comment(
            user_id=user_id,
            content=MaintenanceNarrator.part_demand_created(
                self._part_name(part_id),
                quantity_required,
                username,
                notes=notes,
            ),
            is_human_made=False,
        )
        db.session.commit()

        maintenance_context.refresh()
        return event_id

