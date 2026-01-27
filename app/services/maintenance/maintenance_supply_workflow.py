"""
Maintenance Supply Workflow (Service)

Service layer interface between maintenance routes and business managers.
Per project convention: routes should call services for presentation-facing workflows.
"""

from __future__ import annotations

from typing import Optional

from app.buisness.maintenance.base.action_managment.action_tool_creation_manager import ActionToolCreationManager
from app.buisness.maintenance.base.action_managment.part_demand_manager import PartDemandManager


class MaintenanceSupplyWorkflowService:
    """
    Presentation-facing service for supply-related maintenance workflows.

    Methods return `event_id` for redirecting back to the relevant maintenance portal.
    """

    _part_demands = PartDemandManager()
    _action_tools = ActionToolCreationManager()

    # === Creators (creation is in business managers) ===
    @staticmethod
    def create_part_demand(
        *,
        action_id: int,
        part_id: int,
        quantity_required: float,
        notes: Optional[str],
        user_id: int,
        username: str,
    ) -> int:
        return MaintenanceSupplyWorkflowService._part_demands.create_for_action(
            action_id=action_id,
            part_id=part_id,
            quantity_required=quantity_required,
            notes=notes,
            user_id=user_id,
            username=username,
        )

    @staticmethod
    def create_action_tool(*, action_id: int, tool_id: int, user_id: int, username: str) -> int:
        return MaintenanceSupplyWorkflowService._action_tools.create_for_action(
            action_id=action_id,
            tool_id=tool_id,
            user_id=user_id,
            username=username,
        )

    @staticmethod
    def issue_part_demand(*, part_demand_id: int, user_id: int, username: str) -> int:
        return MaintenanceSupplyWorkflowService._part_demands.issue(
            part_demand_id=part_demand_id,
            user_id=user_id,
            username=username,
        )

    @staticmethod
    def cancel_part_demand_by_technician(
        *, part_demand_id: int, user_id: int, username: str, reason: str
    ) -> int:
        return MaintenanceSupplyWorkflowService._part_demands.cancel_by_technician(
            part_demand_id=part_demand_id,
            user_id=user_id,
            username=username,
            reason=reason,
        )

    @staticmethod
    def undo_part_demand(*, part_demand_id: int, user_id: int, username: str) -> int:
        return MaintenanceSupplyWorkflowService._part_demands.undo_to_planned(
            part_demand_id=part_demand_id,
            user_id=user_id,
            username=username,
        )

    @staticmethod
    def update_part_demand(
        *,
        part_demand_id: int,
        user_id: int,
        username: str,
        quantity_required: Optional[float] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        return MaintenanceSupplyWorkflowService._part_demands.update(
            part_demand_id=part_demand_id,
            user_id=user_id,
            username=username,
            quantity_required=quantity_required,
            status=status,
            priority=priority,
            notes=notes,
        )

