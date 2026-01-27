"""
ActionToolCreationManager

Business-layer manager for creating ActionTool rows (tool requirements) for actions.
"""

from __future__ import annotations

from typing import Tuple

from app import db
from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
from app.buisness.maintenance.base.narrator import MaintenanceNarrator
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.action_tools import ActionTool
from app.data.core.supply.tool_definition import ToolDefinition


class ActionToolCreationManager:
    @staticmethod
    def _load(action_id: int) -> Tuple[Action, MaintenanceContext, int]:
        action = Action.query.get(action_id)
        if not action:
            raise ValueError("Action not found")

        maintenance_context = MaintenanceContext.from_maintenance_action_set(action.maintenance_action_set_id)
        event_id = maintenance_context.event_id
        if not event_id:
            raise ValueError("Maintenance event not found")

        return action, maintenance_context, event_id

    def create_for_action(self, *, action_id: int, tool_id: int, user_id: int, username: str) -> int:
        action, maintenance_context, event_id = self._load(action_id)

        tool = ToolDefinition.query.get(tool_id)
        if not tool:
            raise ValueError("Tool not found")

        action_tool = ActionTool(
            action_id=action_id,
            tool_id=tool_id,
            quantity_required=1,
            status="Planned",
            priority="Medium",
            sequence_order=1,
            created_by_id=user_id,
            updated_by_id=user_id,
        )
        db.session.add(action_tool)
        db.session.commit()

        maintenance_context.add_comment(
            user_id=user_id,
            content=MaintenanceNarrator.tool_requirement_created(tool.tool_name, action.action_name, username),
            is_human_made=False,
        )
        db.session.commit()

        maintenance_context.refresh()
        return event_id

