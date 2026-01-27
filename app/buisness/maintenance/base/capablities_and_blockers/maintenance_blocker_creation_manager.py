"""
MaintenanceBlockerCreationManager

Business-layer manager responsible for creating MaintenanceBlocker rows and
coordinating related status sync + comments.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app import db
from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
from app.buisness.maintenance.base.narrator import MaintenanceNarrator


class MaintenanceBlockerCreationManager:
    def __init__(self, maintenance_context: MaintenanceContext):
        self._ctx = maintenance_context

    def create_blocker(
        self,
        *,
        reason: str,
        notes: Optional[str],
        start_time: Optional[datetime],
        billable_hours_lost: Optional[float],
        user_id: int,
        username: str,
        event_priority: Optional[str] = None,
        comment_to_add_to_event: Optional[str] = None,
    ) -> None:
        struct = self._ctx.struct

        # Prevent multiple active blockers
        active_blockers = [b for b in struct.blockers if b.end_date is None]
        if active_blockers:
            raise ValueError(
                "An active blocked status already exists. Please end the current blocker before creating a new one."
            )

        blocker_manager = self._ctx.get_blocker_manager()
        blocker_manager.add_blocker(
            reason=reason,
            notes=notes,
            start_time=start_time,
            billable_hours_lost=billable_hours_lost,
            user_id=user_id,
        )

        # Sync event status
        self._ctx._sync_event_status()

        # Update priority if provided (reuse existing update method)
        if event_priority and event_priority in ["Low", "Medium", "High", "Critical"]:
            self._ctx.update_action_set_details(priority=event_priority)

        # Comment (human override allowed)
        if struct.event_id:
            if comment_to_add_to_event:
                self._ctx.add_comment(
                    user_id=user_id,
                    content=comment_to_add_to_event,
                    is_human_made=True,
                )
            else:
                self._ctx.add_comment(
                    user_id=user_id,
                    content=MaintenanceNarrator.blocker_created(username, reason, billable_hours_lost),
                    is_human_made=False,
                )

        db.session.commit()
        self._ctx.refresh()

