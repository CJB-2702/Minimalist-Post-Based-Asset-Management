"""
Maintenance Work Portal Service

Service layer for work-portal operations that benefit from a service boundary.
Per project convention: `complete_from_work_portal(...)` lives in service layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app import db
from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
from app.buisness.maintenance.base.narrator import MaintenanceNarrator


class MaintenanceWorkPortalService:
    """
    Service wrapper for work-portal actions for a specific maintenance event (event_id).
    """

    def __init__(self, event_id: int):
        self._event_id = event_id

    def complete_from_work_portal(
        self,
        user_id: int,
        username: str,
        completion_comment: str,
        start_date: datetime,
        end_date: datetime,
        billable_hours: float,
        meter1: Optional[float],
        meter2: Optional[float],
        meter3: Optional[float],
        meter4: Optional[float],
    ) -> None:
        """
        Complete a maintenance event using values from the work portal UI.

        This orchestrates:
        - blocked-action protection
        - billable hours assignment
        - meter verification + completion
        - preserving the user-provided end_date (business layer defaults to utcnow())
        - adding a consistent machine-generated completion comment
        """

        maintenance_context = MaintenanceContext.from_event(self._event_id)
        struct = maintenance_context.struct

        if not struct:
            raise ValueError("Maintenance event not found")

        # Blocked actions prevent completion
        blocked_actions = [a for a in struct.actions if a.status == "Blocked"]
        if blocked_actions:
            raise ValueError("Cannot complete maintenance. Please resolve all blocked actions first.")

        # Persist start date + billable hours before completion
        struct.maintenance_action_set.start_date = start_date

        billable_hours_manager = maintenance_context.get_billable_hours_manager()
        billable_hours_manager.set_actual_hours(billable_hours, user_id=user_id)

        # Complete (this syncs event status and handles meter verification)
        maintenance_context.complete(
            user_id=user_id,
            notes=completion_comment,
            meter1=meter1,
            meter2=meter2,
            meter3=meter3,
            meter4=meter4,
        )

        # Preserve user-entered end_date (complete() sets it to utcnow())
        struct.maintenance_action_set.end_date = end_date
        db.session.commit()

        # Add machine completion comment
        if struct.event_id:
            maintenance_context.add_comment(
                user_id=user_id,
                content=MaintenanceNarrator.maintenance_completed(username, completion_comment),
                is_human_made=False,
            )
            db.session.commit()

        maintenance_context.refresh()

