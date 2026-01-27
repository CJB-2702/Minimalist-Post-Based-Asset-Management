## Maintenance route refactor summary

This pass reorganized maintenance routes so that:

- **Data creators (row creation)** live in the **business layer** (routes delegate to managers).
- **Data updators** may live in business or service layers depending on complexity; specifically, work-portal completion is a **service**.
- Machine-generated maintenance comments are consolidated via a `MaintenanceNarrator` (similar to `DispatchNarrator`).

### New/updated business-layer components

- **`app/buisness/maintenance/base/narrator.py`**
  - `MaintenanceNarrator`: centralized comment text composition for maintenance events (actions, completion, blockers, parts, tools).

- **`app/buisness/maintenance/base/maintenance_action_creation_manager.py`**
  - `MaintenanceActionCreationManager`: **creates `Action` rows** (blank/proto/template/duplicate), handles insertion sequencing/shifting, and adds machine comments.

- **`app/buisness/maintenance/base/maintenance_blocker_creation_manager.py`**
  - `MaintenanceBlockerCreationManager`: **creates `MaintenanceBlocker` rows**, syncs status, applies optional priority, and adds either human override comment or machine comment.

- **`app/buisness/maintenance/base/part_demand_manager.py`**
  - `PartDemandManager`: generic part-demand modifications (issue/cancel/undo/update) + **creator** `create_for_action(...)`.

- **`app/buisness/maintenance/base/action_tool_creation_manager.py`**
  - `ActionToolCreationManager`: **creates `ActionTool` rows** (tool requirements) and adds machine comment.

- **`app/buisness/maintenance/base/maintenance_context.py`**
  - Added:
    - `get_action_creation_manager()`
    - `get_blocker_creation_manager()`

### New/updated service-layer components

- **`app/services/maintenance/maintenance_work_portal_service.py`**
  - `MaintenanceWorkPortalService(event_id).complete_from_work_portal(user_id, username, completion_comment, start_date, end_date, billable_hours, meter1, meter2, meter3, meter4)`
  - Encapsulates the work-portal completion workflow while using business-layer `MaintenanceContext` under the hood.

- **`app/services/maintenance/maintenance_supply_workflow.py`**
  - `MaintenanceSupplyWorkflowService`: route-facing interface for supply operations.
  - Delegates to `PartDemandManager` and `ActionToolCreationManager`.

### Route changes (high level)

#### Data creators (moved out of routes)
- **`app/presentation/routes/maintenance/core/edit_portal.py`**
  - Action creation routes now delegate to `MaintenanceContext.get_action_creation_manager()` instead of creating rows + shifting sequencing in-route.

- **`app/presentation/routes/maintenance/core/work_portal.py`**
  - Blocker creation now delegates to `MaintenanceContext.get_blocker_creation_manager()` (also removes the previous undefined-variable bug in the automated blocker comment).

- **`app/presentation/routes/maintenance/core/action_managment.py`**
  - `create_part_demand` delegates to `MaintenanceSupplyWorkflowService.create_part_demand(...)` (creation is inside business manager).
  - `create_action_tool` delegates to `MaintenanceSupplyWorkflowService.create_action_tool(...)` (creation is inside business manager).

#### Data updators (delegated to business/service)
- **`app/presentation/routes/maintenance/core/work_portal.py`**
  - `complete_maintenance` delegates to `MaintenanceWorkPortalService(...).complete_from_work_portal(...)`.

- **`app/presentation/routes/maintenance/core/part_demand.py`**
  - issue/cancel/undo/update routes delegate to `MaintenanceSupplyWorkflowService` instead of mutating/committing/commenting directly.

