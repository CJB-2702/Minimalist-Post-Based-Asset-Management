"""
MaintenanceActionCreationManager

Business-layer manager responsible for creating Action rows for a maintenance event.

All Action creation is centralized here to keep routes thin and to ensure
consistent sequencing + comments.
"""

from __future__ import annotations

from typing import Optional

from app import db
from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
from app.buisness.maintenance.base.narrator import MaintenanceNarrator
from app.buisness.maintenance.factories.action_factory import ActionFactory
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.action_tools import ActionTool
from app.data.maintenance.base.part_demands import PartDemand
from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem


class MaintenanceActionCreationManager:
    """
    Creates actions (blank / from proto / from template / duplicate) with:
    - correct sequence insertion
    - optional copying of part demands/tools
    - consistent event comments
    """

    def __init__(self, maintenance_context: MaintenanceContext):
        self._ctx = maintenance_context

    @property
    def event_id(self) -> Optional[int]:
        return self._ctx.struct.event_id

    def _shift_for_insertion(self, insert_position: str, after_action_id: Optional[int]) -> int:
        """
        Shift existing actions when inserting at beginning/after and return the new action sequence_order.
        """
        struct = self._ctx.struct

        if insert_position not in ("end", "beginning", "after"):
            raise ValueError(f"Invalid insert_position: {insert_position}")

        if not struct.actions:
            return 1

        if insert_position == "end":
            return self._ctx._calculate_sequence_order(insert_position="end", after_action_id=None)

        if insert_position == "beginning":
            # Shift all actions up by 1
            for a in struct.actions:
                a.sequence_order += 1
            return 1

        # insert_position == "after"
        if not after_action_id:
            raise ValueError("after_action_id required when insert_position is 'after'")

        target = next((a for a in struct.actions if a.id == after_action_id), None)
        if not target:
            raise ValueError(f"Action {after_action_id} not found in maintenance event")

        target_sequence = target.sequence_order
        for a in struct.actions:
            if a.sequence_order > target_sequence:
                a.sequence_order += 1
        return target_sequence + 1

    def create_blank_action(
        self,
        *,
        action_name: str,
        description: Optional[str],
        estimated_duration: Optional[float],
        expected_billable_hours: Optional[float],
        safety_notes: Optional[str],
        notes: Optional[str],
        insert_position: str = "end",
        after_action_id: Optional[int] = None,
        user_id: int,
        username: str,
    ) -> Action:
        seq = self._shift_for_insertion(insert_position, after_action_id)

        action = Action(
            maintenance_action_set_id=self._ctx.struct.maintenance_action_set_id,
            sequence_order=seq,
            action_name=action_name,
            description=description or None,
            estimated_duration=estimated_duration,
            expected_billable_hours=expected_billable_hours,
            safety_notes=safety_notes or None,
            notes=notes or None,
            status="Not Started",
            created_by_id=user_id,
            updated_by_id=user_id,
        )
        db.session.add(action)
        db.session.commit()

        # Machine comment
        if self.event_id:
            self._ctx.add_comment(
                user_id=user_id,
                content=MaintenanceNarrator.action_created(action.action_name, username),
                is_human_made=False,
            )
            db.session.commit()

        self._ctx.refresh()
        return action

    def create_from_proto_action_item(
        self,
        *,
        proto_action_item_id: int,
        action_name: str,
        description: Optional[str],
        estimated_duration: Optional[float],
        expected_billable_hours: Optional[float],
        safety_notes: Optional[str],
        notes: Optional[str],
        insert_position: str = "end",
        after_action_id: Optional[int] = None,
        copy_part_demands: bool = False,
        copy_tools: bool = False,
        user_id: int,
        username: str,
    ) -> Action:
        # Validate proto exists early (ActionFactory will also validate; this gives clearer errors)
        if not ProtoActionItem.query.get(proto_action_item_id):
            raise ValueError(f"Proto action item {proto_action_item_id} not found")

        seq = self._shift_for_insertion(insert_position, after_action_id)

        action = ActionFactory.create_from_proto_action_item(
            proto_action_item_id=proto_action_item_id,
            maintenance_action_set_id=self._ctx.struct.maintenance_action_set_id,
            sequence_order=seq,
            user_id=user_id,
            commit=False,
            copy_part_demands=copy_part_demands,
            copy_tools=copy_tools,
            action_name=action_name,
            description=description,
            estimated_duration=estimated_duration,
            expected_billable_hours=expected_billable_hours,
            safety_notes=safety_notes,
            notes=notes,
        )

        db.session.commit()

        if self.event_id:
            self._ctx.add_comment(
                user_id=user_id,
                content=MaintenanceNarrator.action_created_from_proto(action.action_name, username),
                is_human_made=False,
            )
            db.session.commit()

        self._ctx.refresh()
        return action

    def create_from_template_action_item(
        self,
        *,
        template_action_item_id: int,
        insert_position: str = "end",
        after_action_id: Optional[int] = None,
        copy_part_demands: bool = False,
        copy_tools: bool = False,
        user_id: int,
        username: str,
    ) -> Action:
        seq = self._shift_for_insertion(insert_position, after_action_id)

        action = ActionFactory.create_from_template_action_item(
            template_action_item_id=template_action_item_id,
            maintenance_action_set_id=self._ctx.struct.maintenance_action_set_id,
            user_id=user_id,
            commit=False,
            copy_part_demands=copy_part_demands,
            copy_tools=copy_tools,
        )
        action.sequence_order = seq

        db.session.commit()

        if self.event_id:
            self._ctx.add_comment(
                user_id=user_id,
                content=MaintenanceNarrator.action_created_from_template(action.action_name, username),
                is_human_made=False,
            )
            db.session.commit()

        self._ctx.refresh()
        return action

    def duplicate_from_current_action(
        self,
        *,
        source_action_id: int,
        action_name: Optional[str],
        description: Optional[str],
        estimated_duration: Optional[float],
        expected_billable_hours: Optional[float],
        safety_notes: Optional[str],
        notes: Optional[str],
        insert_position: str = "end",
        after_action_id: Optional[int] = None,
        copy_part_demands: bool = False,
        copy_tools: bool = False,
        user_id: int,
        username: str,
    ) -> Action:
        struct = self._ctx.struct
        source_action = Action.query.get(source_action_id)
        if not source_action:
            raise ValueError("Source action not found")
        if source_action.maintenance_action_set_id != struct.maintenance_action_set_id:
            raise ValueError("Source action does not belong to this maintenance event")

        seq = self._shift_for_insertion(insert_position, after_action_id)

        action = Action(
            maintenance_action_set_id=struct.maintenance_action_set_id,
            template_action_item_id=source_action.template_action_item_id,
            sequence_order=seq,
            action_name=(action_name or source_action.action_name),
            description=(description or source_action.description),
            estimated_duration=estimated_duration if estimated_duration is not None else source_action.estimated_duration,
            expected_billable_hours=expected_billable_hours if expected_billable_hours is not None else source_action.expected_billable_hours,
            safety_notes=(safety_notes or source_action.safety_notes),
            notes=(notes or source_action.notes),
            status="Not Started",
            created_by_id=user_id,
            updated_by_id=user_id,
        )
        db.session.add(action)
        db.session.flush()  # need action.id for copies

        if copy_part_demands:
            for src_pd in source_action.part_demands:
                db.session.add(
                    PartDemand(
                        action_id=action.id,
                        part_id=src_pd.part_id,
                        quantity_required=src_pd.quantity_required,
                        notes=src_pd.notes,
                        expected_cost=src_pd.expected_cost,
                        status="Planned",
                        priority=src_pd.priority,
                        sequence_order=src_pd.sequence_order,
                        created_by_id=user_id,
                        updated_by_id=user_id,
                    )
                )

        if copy_tools:
            for src_tool in source_action.action_tools:
                db.session.add(
                    ActionTool(
                        action_id=action.id,
                        tool_id=src_tool.tool_id,
                        quantity_required=src_tool.quantity_required,
                        notes=src_tool.notes,
                        status="Planned",
                        priority=src_tool.priority,
                        sequence_order=src_tool.sequence_order,
                        created_by_id=user_id,
                        updated_by_id=user_id,
                    )
                )

        db.session.commit()

        if self.event_id:
            self._ctx.add_comment(
                user_id=user_id,
                content=MaintenanceNarrator.action_duplicated(action.action_name, username),
                is_human_made=False,
            )
            db.session.commit()

        self._ctx.refresh()
        return action

