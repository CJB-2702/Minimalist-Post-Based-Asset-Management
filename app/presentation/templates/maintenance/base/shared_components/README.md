# Shared Maintenance Components

This directory contains reusable components that are shared across multiple maintenance templates (view, edit, work pages).

## Components

### 1. capability_status_card.html
**Purpose:** Display asset capability status with visual indicators

**Features:**
- Color-coded card: Red (Non-Mission Capable), Yellow (Partially Capable), Default (Fully Capable)
- Shows active limitations with count
- Provides buttons to end active limitations
- Includes embedded end limitation modals

**Usage:**
```jinja
{% include 'maintenance/base/shared_components/capability_status_card.html' %}
```

**Required Context Variables:**
- `asset` - The asset object with capability_status property
- `active_limitations` - List of active AssetLimitationRecord objects

### 2. end_blocked_status_modal.html
**Purpose:** Modal for ending a maintenance blocker

**Features:**
- Auto-populated current time for end date
- Validates required fields (start/end dates, billable hours)
- Allows updating blocker notes
- Adds comment to event log

**Usage:**
```jinja
{% for blocker in active_blockers %}
{% include 'maintenance/base/shared_components/end_blocked_status_modal.html' %}
{% endfor %}
```

**Required Context Variables:**
- `blocker` - MaintenanceBlocker object with properties:
  - id
  - mission_capability_status
  - reason
  - start_date
  - billable_hours
  - notes

**Form Fields:**
- `blocked_status_start_date` (required) - Blocker start time
- `blocked_status_end_date` (required) - Blocker end time
- `blocked_status_billable_hours` (required) - Hours lost (min: 0)
- `blocked_status_notes` (optional) - Update to blocker notes
- `comment` (optional) - Comment to add to event

### 3. end_limitation_modal.html
**Purpose:** Modal for ending an asset capability limitation

**Features:**
- Auto-populated current time for end date
- Shows limitation status and description
- Adds comment to event log
- Closes the limitation record

**Usage:**
```jinja
{% for limitation in active_limitations %}
{% include 'maintenance/base/shared_components/end_limitation_modal.html' %}
{% endfor %}
```

**Required Context Variables:**
- `limitation` - AssetLimitationRecord object with properties:
  - id
  - status
  - limitation_description
  - temporary_modifications
  - start_time
  - is_active

**Form Fields:**
- `end_time` (required) - When the limitation was resolved
- `comment` (optional) - Comment to add to event

## Integration Notes

### Auto-populating Current Time
Both modal components include JavaScript that automatically sets the current date/time when the modal opens. This provides a good default while still allowing users to adjust if needed.

### Color Coding Standards
**Capability Status:**
- **Red (Danger)**: Non-Mission Capable (NMC) statuses
- **Yellow (Warning)**: Partial/Compensation statuses (PMC)
- **Default (Secondary)**: Fully Mission Capable (FMC)

**Blockers:**
- **Red (Danger)**: Active blockers
- Badge colors match priority levels

## Dependencies

These components rely on:
- Bootstrap 5 modals
- Bootstrap Icons
- Flask url_for() function
- Standard form POST handling

## Routes Used

- `maintenance.end_blocked_status` - POST to end a blocker
- `maintenance.close_limitation` - POST to close a limitation

## Best Practices

1. **Always include required context** - Check that your route passes all required variables
2. **Use in loops** - These components are designed to be included within loops
3. **Modal IDs** - Each modal uses the record's ID to ensure uniqueness
4. **Form validation** - Required fields are marked with asterisks and proper HTML5 validation
5. **User feedback** - Both forms include helper text to guide users
