"""
MaintenanceNarrator - Comment composer for maintenance lifecycle events

Ensures consistent machine-generated comment text across maintenance workflows.
Separates narrative formatting from transition logic.
"""

from __future__ import annotations

from typing import Optional


class MaintenanceNarrator:
    """
    Composes machine-generated comments for maintenance lifecycle events.

    All methods return comment text suitable for adding to the maintenance Event
    with is_human_made=False (unless otherwise noted by caller).
    """

    # === Actions ===
    @staticmethod
    def action_created(action_name: str, username: str) -> str:
        return f"Action created: '{action_name}' by {username}"

    @staticmethod
    def action_created_from_proto(action_name: str, username: str) -> str:
        return f"Action created from proto: '{action_name}' by {username}"

    @staticmethod
    def action_created_from_template(action_name: str, username: str) -> str:
        return f"Action created from template: '{action_name}' by {username}"

    @staticmethod
    def action_duplicated(action_name: str, username: str) -> str:
        return f"Action duplicated: '{action_name}' by {username}"

    @staticmethod
    def action_deleted(action_name: str, username: str) -> str:
        return f"Action deleted: '{action_name}' by {username}"

    # === Maintenance completion ===
    @staticmethod
    def maintenance_completed(username: str, comment: str) -> str:
        return f"Maintenance completed by {username}. {comment}".strip()

    # === Blockers ===
    @staticmethod
    def blocker_created(username: str, reason: str, billable_hours_lost: Optional[float] = None) -> str:
        base = f"Blocked status created by {username}. Reason: {reason}"
        if billable_hours_lost is not None:
            base += f" | Billable hours lost: {billable_hours_lost}"
        return base

    @staticmethod
    def blocker_ended(username: str, comment: Optional[str] = None) -> str:
        if comment:
            return f"Blocked status ended by {username}. {comment}"
        return f"Blocked status ended by {username}. Maintenance work resumed."

    # === Part demands ===
    @staticmethod
    def part_issued(part_name: str, quantity: float, username: str) -> str:
        return f"Part issued: {part_name} x{quantity} by {username}"

    @staticmethod
    def part_cancelled(part_name: str, quantity: float, username: str, reason: str) -> str:
        return f"Part demand cancelled: {part_name} x{quantity} by {username}. Reason: {reason}"

    @staticmethod
    def part_reset_to_planned(part_name: str, quantity: float, username: str) -> str:
        return f"Part demand reset to planned: {part_name} x{quantity} by {username}"

    @staticmethod
    def part_updated(part_name: str, quantity: float, username: str, status: Optional[str] = None) -> str:
        msg = f"Part demand updated: {part_name} x{quantity} by {username}"
        if status:
            msg += f". Status: {status}"
        return msg

    @staticmethod
    def part_demand_created(part_name: str, quantity: float, username: str, notes: Optional[str] = None) -> str:
        msg = f"Part demand created: {part_name} x{quantity} by {username}"
        if notes:
            msg += f". Notes: {notes}"
        return msg

    # === Tools (optional helpers) ===
    @staticmethod
    def tool_requirement_created(tool_name: str, action_name: str, username: str) -> str:
        return f"Tool requirement created: {tool_name} for action '{action_name}' by {username}"

    @staticmethod
    def tool_requirement_updated(tool_name: str, action_name: str, username: str, status: Optional[str] = None) -> str:
        msg = f"Tool requirement updated: {tool_name} for action '{action_name}' by {username}"
        if status:
            msg += f". Status: {status}"
        return msg

    @staticmethod
    def tool_requirement_deleted(tool_name: str, action_name: str, username: str) -> str:
        return f"Tool requirement deleted: {tool_name} from action '{action_name}' by {username}"

