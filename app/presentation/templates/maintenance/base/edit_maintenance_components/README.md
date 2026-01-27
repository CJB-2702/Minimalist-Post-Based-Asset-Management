# Edit Maintenance Event Components

This directory contains modular components for the edit maintenance event page, broken down from the original monolithic template.

## Component Structure

### Template Components

1. **event_header.html** - Event header with status badge and navigation buttons
2. **event_details_form.html** - Main event details form with all fields
3. **blockers_card.html** - Maintenance blockers list with inline editing
4. **limitations_card.html** - Asset capability limitations with inline editing
5. **blocker_modals.html** - Modal for creating new blockers
6. **limitation_modals.html** - Modal for creating new limitations

#### Action Editor Panel Components (action_editor_panel/)

7. **actions_list_sidebar.html** - Left sidebar showing condensed action list
8. **action_edit_form.html** - Middle panel with action editing form
9. **part_demands_section.html** - Part demands list with inline editing
10. **tools_section.html** - Tools requirements with inline editing

### JavaScript Module

**edit_maintenance.js** - Object-oriented JavaScript module that handles:
- Inline editing for blockers, limitations, part demands, and tools
- Modal management with auto-populated timestamps
- Action selection and deletion
- Action Creator Portal interactions
- Uses data attributes for configuration (no inline onclick in component templates)

## Key Features

### Data-Driven Design
All interactive elements use data attributes instead of inline JavaScript:
- `data-blocker-id` - Identifies blocker records
- `data-limitation-id` - Identifies limitation records
- `data-part-demand-id` - Identifies part demand records
- `data-tool-id` - Identifies tool records
- `data-edit-panel` - Links to edit panel elements
- `data-action` - Defines button actions

### Object-Oriented JavaScript
The JavaScript is organized into classes:
- `EditPanelManager` - Base class for managing inline edit panels
- `BlockerManager` - Extends EditPanelManager for blockers
- `LimitationManager` - Extends EditPanelManager for limitations
- `PartDemandManager` - Extends EditPanelManager for part demands
- `ToolManager` - Extends EditPanelManager for tools
- `ModalManager` - Handles modal behavior and auto-timestamps
- `ActionSelector` - Manages action selection
- `ActionDeleter` - Handles action deletion
- `ActionCreatorPortal` - Manages action creator portal interactions

### Route for JavaScript
A dedicated route serves the JavaScript file:
- URL: `/maintenance/maintenance-event/static/js/edit_maintenance.js`
- Route: `maintenance_event.serve_edit_maintenance_js`

## File Structure

```
edit_maintenance_components/
├── README.md
├── edit_maintenance.js
├── event_header.html
├── event_details_form.html
├── blockers_card.html
├── limitations_card.html
├── blocker_modals.html
├── limitation_modals.html
└── action_editor_panel/
    ├── actions_list_sidebar.html
    ├── action_edit_form.html
    ├── part_demands_section.html
    └── tools_section.html
```

## Usage

The main `edit_maintenance_event.html` file now includes these components using Jinja's `{% include %}` directive:

```jinja
{% include 'maintenance/base/edit_maintenance_components/event_header.html' %}
{% include 'maintenance/base/edit_maintenance_components/blockers_card.html' %}
{% include 'maintenance/base/edit_maintenance_components/action_editor_panel/actions_list_sidebar.html' %}
```

The JavaScript is loaded in the `extra_js` block:

```jinja
{% block extra_js %}
<script src="{{ url_for('maintenance_event_edit.serve_edit_maintenance_js') }}"></script>
{% endblock %}
```

## Benefits

1. **Maintainability** - Each component is self-contained and easier to update
2. **Reusability** - Components can be reused in other templates
3. **Readability** - Smaller files are easier to understand
4. **Testability** - Individual components can be tested in isolation
5. **Performance** - JavaScript is properly minified and cached
6. **Clean Code** - No inline JavaScript, all handled by the module

## File Size Reduction

- **Original**: 1,871 lines in one file
- **Refactored**: 
  - Main template: ~475 lines
  - 10 component templates: ~100-200 lines each
  - JavaScript module: ~400 lines
  - Total reduction: More modular and maintainable

## Development Notes

When adding new inline editing features:
1. Add data attributes to the HTML element
2. Create or extend a manager class in `edit_maintenance.js`
3. Use the `data-edit-panel` attribute to link edit panels
4. Follow the existing pattern for consistency
