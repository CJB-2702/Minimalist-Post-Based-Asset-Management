# Debug Data Management System - Understanding Document

## Overview
This document captures the goals and understanding for refactoring the data insertion system to separate essential production data from debugging/test data.

## Current State Analysis

### Phased Build Structure
The application uses a phased build system with 6 phases:

1. **Phase 1 (Core Foundation)**: Users, Locations, Asset Types, Make/Models, Assets, Events
2. **Phase 2 (Asset Details)**: Asset detail tables, model detail tables, detail table templates
3. **Phase 3 (Dispatching)**: Dispatch configurations and example dispatches
4. **Phase 4 (Supply)**: Parts, Tools, Part Demands
5. **Phase 5 (Maintenance)**: Maintenance templates, plans, and action sets
6. **Phase 6 (Inventory & Purchasing)**: Purchase orders, inventory movements, part arrivals

### Current Data Sources

#### Critical Data (MUST ALWAYS BE PRESENT)
- **Location**: `app/data/core/build_data_critical.json`
- **Purpose**: Contains essential data required for the application to function
- **Contents**:
  - Essential Users (System, Admin)
  - Essential Events (System_Initialized)
  - Core Asset Types (Vehicle)
- **Usage**: This data is loaded and inserted during every build/rebuild
- **Critical Rule**: This data MUST always be present and cannot be disabled

#### Build Data (Production + Test Data)
- **Location**: `app/utils/build_data.json`
- **Purpose**: Contains both production configuration data and test/debugging data
- **Contents**:
  - Core data (users, locations, asset types, make/models, assets)
  - Asset detail configurations and sample data
  - Dispatching configurations and examples
  - Supply items (parts, tools, part demands)
  - Maintenance templates, plans, and events
- **Problem**: Mixes essential production data with test/debugging data

### Current Build Process

#### Build Files Structure
Each phase has a `build.py` file in `app/data/{module}/build.py`:
- `app/data/core/build.py` - Phase 1
- `app/data/assets/build.py` - Phase 2
- `app/data/dispatching/build.py` - Phase 3
- `app/data/core/supply/build.py` - Phase 4
- `app/data/maintenance/build.py` - Phase 5
- `app/data/inventory/build.py` - Phase 6

#### Main Build Orchestrator
- **Location**: `app/build.py`
- **Function**: `build_database(build_phase, data_phase)`
- **Responsibilities**:
  - Orchestrates model building across phases
  - Calls phase-specific `init_data()` functions
  - Loads data from `app/utils/build_data.json`
  - Handles system initialization checks

### Current Data Insertion Methods

#### Direct Table Inserts (Current Approach)
The current build files use direct SQLAlchemy ORM inserts:
- Direct model instantiation: `Model(**data)`
- Direct `db.session.add()` calls
- Manual relationship resolution (e.g., looking up foreign keys by name)
- Direct `find_or_create_from_dict()` calls on models

**Example from current code**:
```python
# Direct insert approach
asset = Asset(**asset_data)
db.session.add(asset)
```

#### Business Layer Factories (Target Approach)
The application has factories in `app/buisness/` that should be used:
- **AssetFactory**: `app/buisness/assets/factories/asset_factory.py`
  - `create_asset()` - Creates assets with validation
  - `create_asset_from_dict()` - Creates from dict with find_or_create
- **MakeModelFactory**: `app/buisness/assets/factories/make_model_factory.py`
  - `create_make_model_from_dict()` - Creates make/models with validation
- **DetailFactory**: `app/buisness/assets/factories/detail_factory.py`
  - Abstract base for detail table creation
- **Maintenance Factories**: `app/buisness/maintenance/factories/`
  - `MaintenanceActionSetFactory`
  - `ActionFactory`
  - `MaintenanceFactory`

#### Business Layer Contexts
Context managers provide structured access to entities:
- **AssetContext**: `app/buisness/core/asset_context.py`
- **AssetDetailsContext**: `app/buisness/assets/asset_details_context.py`
- **PartContext**: `app/buisness/inventory/part_context.py`
- **ToolContext**: `app/buisness/inventory/tool_context.py`
- **MaintenanceContext**: `app/buisness/maintenance/base/maintenance_context.py`

## Goals

### Primary Goal: Separation of Concerns
**Separate essential production data from debugging/test data**

1. **Critical Data**: Must always be present (in `build_data_critical.json`)
2. **Debug Data**: Optional test/debugging data (in `app/debug/data/*.json`)
3. **Build Routes**: Should only handle essential production data
4. **Debug Routes**: Should handle all test/debugging data insertion

### Secondary Goal: Modernize Data Insertion
**Move from direct table inserts to factory/context pattern**

1. **Replace Direct Inserts**: Use factories instead of direct model instantiation
2. **Use Contexts**: Use context managers for complex operations
3. **Leverage Business Logic**: Utilize validation and business rules in factories
4. **Maintain Consistency**: Ensure all data creation follows same patterns

### Tertiary Goal: Centralized Debug Management
**Create a unified debug data management system**

1. **Debug Data Manager**: Central controller for debug data configuration
2. **Modular Debug Files**: Separate debug files per module (core, assets, maintenance, etc.)
3. **Configuration Control**: Enable/disable debug data insertion via command-line flag (default: enabled)
4. **Rebuild Integration**: Load debug data only on rebuild, skip if data already present

## Proposed Structure

### Debug Folder Structure
```
app/debug/
├── debug_data_manager.py          # Central controller for debug data
├── add_core_debugging_data.py      # Core module debug data insertion
├── add_assets_debugging_data.py    # Assets module debug data insertion
├── add_inventory_debugging_data.py # Inventory module debug data insertion
├── add_maintenance_debugging_data.py # Maintenance module debug data insertion
├── add_dispatching_debugging_data.py # Dispatching module debug data insertion
└── data/
    ├── core.json                   # Core debug data
    ├── assets.json                 # Assets debug data
    ├── inventory.json              # Inventory debug data
    ├── maintenance.json            # Maintenance debug data
    └── dispatching.json            # Dispatching debug data
```

### Data Flow

#### Production Build Flow
```
app/build.py
  └─> Load build_data_critical.json (ALWAYS)
  └─> Phase-specific build.py files
      └─> init_data() functions
          └─> Use factories/contexts for data creation
```

#### Debug Data Flow
```
app/build.py (on rebuild)
  └─> Verify build_data_critical.json is present (ALWAYS)
  └─> Insert critical data (ALWAYS)
  └─> Check --enable-debug-data flag (default: true)
      └─> If enabled:
          └─> app/debug/debug_data_manager.py
              └─> Check if data already present (skip if yes)
              └─> Load app/debug/data/*.json files
              └─> Follow build order: core → assets → dispatching → maintenance → inventory
              └─> Call module-specific add_*_debugging_data.py functions
                  └─> Use factories/contexts for data creation
                  └─> Fail-fast: throw error and stop if any insertion fails
```

## Key Requirements

### 1. Critical Data Protection
- `build_data_critical.json` must always be loaded and verified present
- Critical data insertion cannot be disabled
- Critical data must be inserted before any other data
- Critical data must be verified present on every build/rebuild

### 2. Factory/Context Usage
- All new data insertion must use factories
- Complex operations should use contexts
- Direct table inserts should be phased out
- Maintain backward compatibility during transition

### 3. Debug Data Manager
- Central configuration for debug data modules
- Command-line flag to enable/disable (default: enabled if flag not present)
- Load debug data only on rebuild, skip if data already present
- Follow build order: core → assets → dispatching → maintenance → inventory
- Fail-fast: If any debug data insertion fails, throw error and stop application
- Logging and error handling

### 4. Modular Debug Files
- Each module has its own debug data file
- Each module has its own insertion function
- Debug files can be empty (structure only)
- Debug files should mirror production data structure

### 5. Data Conflict Resolution
- **No conflicts expected**: Only `build_data_critical.json` is production data
- All other data in `app/utils/build_data.json` is debugging data
- Debug data should not conflict with critical data
- If conflicts occur, it indicates a design issue that needs fixing

## Migration Strategy

### Phase 1: Identify Test Data
- Review all `build.py` files
- Identify test/debugging data vs. production data
- Document what goes where

### Phase 2: Create Debug Structure
- Create debug JSON files (can be empty initially)
- Create debug insertion functions (stubs)
- Create debug_data_manager skeleton

### Phase 3: Move Test Data
- Extract test data from `build_data.json`
- Move to appropriate `app/debug/data/*.json` files
- Update insertion functions to use factories

### Phase 4: Refactor Build Files
- Remove test data insertion from build files
- Keep only essential production data
- Update to use factories/contexts

### Phase 5: Integration
- Integrate debug_data_manager into build process
- Add configuration options
- Test both production and debug data flows

## Benefits

1. **Clear Separation**: Production vs. debug data is explicit
2. **Maintainability**: Debug data doesn't clutter production build
3. **Flexibility**: Debug data can be enabled/disabled per module
4. **Consistency**: All data creation uses same factory/context pattern
5. **Testability**: Debug data can be easily modified without affecting production
6. **Scalability**: Easy to add new debug data modules

## Resolved Questions

### 1. Debug Data Loading
**Q**: Should debug data be loaded on every startup or only on rebuild?  
**A**: Only on rebuild. If data is already present, skip insertion.

### 2. Command-Line Flag
**Q**: Should there be a command-line flag to enable/disable debug data?  
**A**: Yes, with a command-line flag. Default to `true` (enabled) if the flag is not present.

### 3. Dependency Handling
**Q**: How should debug data handle dependencies (e.g., assets need locations)?  
**A**: Follow the established build order: core → assets → dispatching → maintenance → inventory. Each phase depends on previous phases.

### 4. Transactional Behavior
**Q**: Should debug data insertion be transactional (all or nothing)?  
**A**: Yes, fail-fast approach. If any debug data fails to insert, throw an error and stop the application.

### 5. Data Conflicts
**Q**: How to handle conflicts between production and debug data?  
**A**: There should be no conflicts. The only production data is `build_data_critical.json`, which must always be present. All other data in `app/utils/build_data.json` is debugging data and should not conflict with critical data.

## Additional Questions

### 6. Data Presence Detection
**Q**: How should the system detect if debug data is already present?  
**A**: *To be determined* - Should we check for:
for now review the current methods all debug data should specify the id
do simple checks

### 7. Critical Data Verification
**Q**: What should happen if critical data verification fails?  
**A**: Attempt to insert and if insertion fails stop the application

### 8. Debug Data File Requirements
**Q**: Should debug data JSON files be required to exist, or optional?  
**A**: optional. if the json file does not exist skip



### 10. Debug Data Clearing
**Q**: Should there be a way to clear existing debug data before inserting?  
**A**: if debug data exists skip


### Command-Line Interface
Proposed flag structure:
```bash
# Enable debug data (default if flag not present)
python app.py --rebuild --enable-debug-data

# Disable debug data
python app.py --rebuild --no-debug-data



### 11. Module-Level Control
**Q**: Should there be separate flags for each module, or one global flag?  
**A**: 
review the following flags update to use proposed flag structure with the phase arguments
def parse_arguments():
    """Parse command line arguments for build phases"""
    parser = argparse.ArgumentParser(description='Asset Management System')
    parser.add_argument('--phase1', action='store_true', 
                       help='Build only Phase 1 (Core Foundation Tables and System Initialization)')
    parser.add_argument('--phase2', action='store_true', 
                       help='Build Phase 1 and Phase 2 (Core + Asset Detail Tables)')
    parser.add_argument('--phase3', action='store_true', 
                       help='Build Phase 1, Phase 2, and Phase 3 (Core + Asset Detail Tables + Automatic Detail Creation)')
    parser.add_argument('--phase4', action='store_true', 
                       help='Build Phase 1, Phase 2, Phase 3, and Phase 4 (Core + Asset Detail Tables + Automatic Detail Creation + User Interface)')
    parser.add_argument('--build-only', action='store_true',
                       help='Build database only, do not start the web server')
if --build only is present it means only create the tables don't insert data
BUILD DATA CRITICAL IS ALWAYS CHECKED AND INSERTED REGARDLESS OF FLAGS




### 12. Integration Point
**Q**: How should `debug_data_manager` be integrated into `app/build.py`?  
**A**: call it automatically after all the tables are initialized and critical data insertion


## Implementation Notes

### Build Order
Debug data insertion must follow this order to respect dependencies:
1. **Core** - Users, Locations, Asset Types, Make/Models, Assets
2. **Assets** - Asset details, model details (depends on Core)
3. **Dispatching** - Dispatch configurations (depends on Assets)
4. **Maintenance** - Maintenance templates, plans, events (depends on Assets, Supply)
5. **Inventory** - Inventory movements, purchase orders (depends on Supply, Maintenance)

### Error Handling
- Critical data verification failure: **Stop build immediately**
- Debug data insertion failure: **Throw error and stop application**
- Missing debug file: **To be determined** (see Additional Questions)
- Empty debug file: **To be determined** (see Additional Questions)


```

## Next Steps

1. **Answer Additional Questions**: Resolve remaining questions about data presence detection, file requirements, etc.
2. **Create Planning Document**: Detailed implementation steps with API design
3. **Review Build Files**: Identify all test data in current build files
4. **Design debug_data_manager API**: Function signatures, configuration structure
5. **Create Migration Plan**: Step-by-step plan for each module
6. **Implement Incrementally**: Start with one module, test, then expand

