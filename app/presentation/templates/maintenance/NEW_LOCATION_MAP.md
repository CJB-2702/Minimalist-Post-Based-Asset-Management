# Maintenance Templates Location Map

This document tracks the refactoring of the `app/presentation/templates/maintenance` directory from its initial flat structure to the current organized structure.

## Initial Directory State

Based on the initial `ls` output, the directory had a flat structure with:
- Multiple directories at root level
- Multiple HTML files at root level
- No clear organizational hierarchy

## New Directory Structure

The templates have been reorganized into logical groupings:

### Root Level (Portal & Navigation)
- `index.html` - Maintenance portal index (unchanged)
- `splash.html` - Maintenance splash page (unchanged)
- `stub.html` - Stub template (unchanged)

### `/base/` - Core Maintenance Functionality

Core maintenance operations and base templates moved here:

| Original Location | New Location | Status |
|------------------|--------------|--------|
| `action_creator_portal/` | `base/action_creator_portal/` | Moved |
| `action_creator_portal.html` | `base/action_creator_portal.html` | Moved |
| `actions/` | `base/actions/` | Moved |
| `create_maintenance_event.html` | `base/create_maintenance_event.html` | Moved |
| `blockers/` | `base/blockers/` | Moved |
| `do_maintenance.html` | `base/do_maintenance.html` | Moved |
| `edit_maintenance_event.html` | `base/edit_maintenance_event.html` | Moved |
| `event_portal/` | `base/event_portal/` | Moved |
| `maintenance_action_sets/` | `base/maintenance_action_sets/` | Moved |
| `maintenance_event/` | `base/maintenance_event/` | Moved |
| `maintenance_plans/` | `base/maintenance_plans/` | Moved |
| `part_demands/` | `base/part_demands/` | Moved |
| `view_maintenance_event.html` | `base/view_maintenance_event.html` | Moved |
| `work_maintenance_event.html` | `base/work_maintenance_event.html` | Moved |

### `/maintenance_templates/` - Template Management

Template-related views and management moved here:

| Original Location | New Location | Status |
|------------------|--------------|--------|
| `view_maintenance_template.html` | `maintenance_templates/view_maintenance_template.html` | Moved |
| `template_action_items/` | `maintenance_templates/template_action_items/` | Moved |
| `template_action_sets/` | `maintenance_templates/template_action_sets/` | Moved |
| `template_action_tools/` | `maintenance_templates/template_action_tools/` | Moved |
| `template_part_demands/` | `maintenance_templates/template_part_demands/` | Moved |
| `action_creator_portal.html` (template builder) | `maintenance_templates/action_creator_portal.html` | Moved |

### `/prototype/` - Prototype Actions

Prototype action views moved here:

| Original Location | New Location | Status |
|------------------|--------------|--------|
| `view_proto_action.html` | `prototype/view_proto_action.html` | Moved |

### `/user_views/` - User-Specific Views

User role-based views organized here:

| Original Location | New Location | Status |
|------------------|--------------|--------|
| `fleet/` | `user_views/fleet/` | Moved |
| `manager/` | `user_views/manager/` | Moved |
| `technician/` | `user_views/technician/` | Moved |

### `/searchbars/` - Search Components

Search bar result templates (unchanged location):

| Original Location | New Location | Status |
|------------------|--------------|--------|
| `searchbars/` | `searchbars/` | Unchanged |

## Route Template Path Updates

All route handlers that reference these templates need to be updated with the new paths:

### Base Templates (Updated to `maintenance/base/...`)
- `maintenance/view_maintenance_event.html` → `maintenance/base/view_maintenance_event.html`
- `maintenance/work_maintenance_event.html` → `maintenance/base/work_maintenance_event.html`
- `maintenance/edit_maintenance_event.html` → `maintenance/base/edit_maintenance_event.html`
- `maintenance/create_maintenance_event.html` → `maintenance/base/create_maintenance_event.html`
- `maintenance/do_maintenance.html` → `maintenance/base/do_maintenance.html`
- `maintenance/action_creator_portal.html` → `maintenance/base/action_creator_portal.html`
- `maintenance/event_portal/...` → `maintenance/base/event_portal/...`
- `maintenance/actions/...` → `maintenance/base/actions/...`
- `maintenance/blockers/...` → `maintenance/base/blockers/...`
- `maintenance/part_demands/...` → `maintenance/base/part_demands/...`
- `maintenance/maintenance_action_sets/...` → `maintenance/base/maintenance_action_sets/...`
- `maintenance/maintenance_event/...` → `maintenance/base/maintenance_event/...`
- `maintenance/maintenance_plans/...` → `maintenance/base/maintenance_plans/...`
- `maintenance/action_creator_portal/...` → `maintenance/base/action_creator_portal/...`

### Template Management (Updated to `maintenance/maintenance_templates/...`)
- `maintenance/view_maintenance_template.html` → `maintenance/maintenance_templates/view_maintenance_template.html`

### Prototype Actions (Updated to `maintenance/prototype/...`)
- `maintenance/view_proto_action.html` → `maintenance/prototype/view_proto_action.html`

### User Views (Updated to `maintenance/user_views/...`)
- `maintenance/manager/...` → `maintenance/user_views/manager/...`
- `maintenance/fleet/...` → `maintenance/user_views/fleet/...`
- `maintenance/technician/...` → `maintenance/user_views/technician/...`

### Unchanged
- `maintenance/splash.html` (root level)
- `maintenance/index.html` (root level)
- `maintenance/stub.html` (root level)
- `maintenance/searchbars/...` (unchanged location)

## Files Updated with Route Path Changes

The following route files have been updated with new template paths:

1. ✅ `app/presentation/routes/maintenance/core/maintenance_event.py`
   - Updated 4 template paths to use `base/` prefix
   - `view_maintenance_event.html`, `work_maintenance_event.html`, `edit_maintenance_event.html`, `maintenance_event/assign.html`

2. ✅ `app/presentation/routes/maintenance/action_creator_portal.py`
   - Updated 5 template paths to use `base/action_creator_portal/` prefix
   - Main portal template and all search/list templates

3. ✅ `app/presentation/routes/maintenance/main.py`
   - Updated 2 template paths
   - `view_maintenance_template.html` → `maintenance_templates/view_maintenance_template.html`
   - `view_proto_action.html` → `prototype/view_proto_action.html`

4. ✅ `app/presentation/routes/maintenance/event_portal.py`
   - Updated default template path to use `base/event_portal/` prefix

5. ✅ `app/presentation/routes/maintenance/user_views/manager/main.py`
   - Updated 6 template paths to use `user_views/manager/` prefix

6. ✅ `app/presentation/routes/maintenance/user_views/manager/create_assign.py`
   - Updated 7 template paths to use `user_views/manager/` prefix

7. ✅ `app/presentation/routes/maintenance/user_views/fleet/fleet.py`
   - Updated dashboard template path to use `user_views/fleet/` prefix

8. ✅ `app/presentation/routes/maintenance/user_views/technician/main.py`
   - Updated dashboard template path to use `user_views/technician/` prefix

9. ✅ `app/presentation/routes/maintenance/templates/template_builder.py`
   - Updated 12 template paths to use `user_views/manager/` prefix

10. ✅ `app/presentation/templates/maintenance/user_views/manager/template_action_creator_portal.html`
    - Updated template include path to use `user_views/manager/partials/` prefix

## Summary of Route Updates

### Total Files Updated: 10 files

**Route Files (9):**
- Core maintenance routes: 1 file
- Action creator portal routes: 1 file
- Main routes: 1 file
- Event portal routes: 1 file
- User view routes: 5 files (manager, fleet, technician)
- Template builder routes: 1 file

**Template Files (1):**
- HTML template includes: 1 file

### Template Path Changes Summary:
- **Base templates**: 13 paths updated to `maintenance/base/...`
- **Template management**: 1 path updated to `maintenance/maintenance_templates/...`
- **Prototype actions**: 1 path updated to `maintenance/prototype/...`
- **User views**: 18+ paths updated to `maintenance/user_views/...`
- **Template includes**: 1 path updated in HTML files

## Notes

- ✅ All template includes within HTML files have been updated to use the new paths
- ✅ Search bar result templates remain in `searchbars/` at the root level (unchanged)
- ✅ User-specific views are now clearly separated in `user_views/`
- ✅ Core maintenance functionality is organized under `base/`
- ✅ Template and prototype management are in their own dedicated directories
- ✅ All route handlers have been updated to reference the new template locations

---

**Document Created**: Tracking refactoring of maintenance templates directory structure.  
**Last Updated**: Route path updates completed - all routes now reference new template locations.

