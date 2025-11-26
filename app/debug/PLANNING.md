# Debug Data Management System - Implementation Plan

## Overview
This document provides a detailed implementation plan for refactoring the data insertion system to separate critical production data from debugging/test data, and modernize data insertion to use factories and contexts.

## Prerequisites
- Review `UNDERSTANDING.md` for goals and requirements
- Understand current build system in `app/build.py`
- Familiarity with business layer factories and contexts
- Knowledge of phased build structure (6 phases)

## Implementation Phases

### Phase 1: Update Command-Line Interface
**Goal**: Update `app.py` to support new debug data flags and `--build-only` mode

#### Tasks
1. **Update `parse_arguments()` in `app.py`**
   - Add `--enable-debug-data` flag (default: True if not present)
   - Add `--no-debug-data` flag (explicitly disable)
   - Update `--build-only` behavior: Only create tables, no data insertion
   - Keep existing phase flags (`--phase1`, `--phase2`, etc.)
   - Document: Critical data is ALWAYS checked and inserted regardless of flags

2. **Update build logic in `app.py`**
   - Pass debug data flag to `build_database()`
   - Handle `--build-only` mode (skip data insertion, but still verify critical data)
   - Ensure critical data verification happens even in `--build-only` mode

#### Code Changes
```python
# app.py - parse_arguments()
parser.add_argument('--enable-debug-data', action='store_true', default=True,
                   help='Enable debug data insertion (default: enabled)')
parser.add_argument('--no-debug-data', action='store_false', dest='enable_debug_data',
                   help='Disable debug data insertion')
parser.add_argument('--build-only', action='store_true',
                   help='Build database tables only, do not insert data (except critical)')
```

#### Testing
- Test `--build-only` with no data insertion
- Test `--enable-debug-data` (default behavior)
- Test `--no-debug-data` to disable debug data
- Verify critical data is always inserted regardless of flags

---

### Phase 2: Create Debug Data Manager
**Goal**: Create central controller for debug data insertion

#### Tasks
1. **Create `app/debug/debug_data_manager.py`**
   - Main function: `insert_debug_data(enabled=True, phase='all')`
   - Load debug JSON files from `app/debug/data/`
   - Check if data already present (simple ID-based checks)
   - Follow build order: core → assets → dispatching → maintenance → inventory
   - Fail-fast error handling

2. **Implement data presence detection**
   - For each module, check if key records exist by ID
   - Use simple queries: `Model.query.filter_by(id=X).first()`
   - If any key record exists, skip that module's debug data
   - Log skipped modules

3. **Implement module insertion functions**
   - Call `add_core_debugging_data()` if core.json exists
   - Call `add_assets_debugging_data()` if assets.json exists
   - Call `add_dispatching_debugging_data()` if dispatching.json exists
   - Call `add_maintenance_debugging_data()` if maintenance.json exists
   - Call `add_inventory_debugging_data()` if inventory.json exists

#### API Design
```python
# app/debug/debug_data_manager.py

def insert_debug_data(enabled=True, phase='all'):
    """
    Insert debug data for specified phase(s)
    
    Args:
        enabled (bool): Whether to insert debug data (default: True)
        phase (str): Phase to insert ('phase1', 'phase2', ..., 'all')
    
    Returns:
        dict: Summary of inserted data
    
    Raises:
        Exception: If any debug data insertion fails (fail-fast)
    """
    pass

def _check_debug_data_present(module_name):
    """
    Check if debug data for a module is already present
    
    Args:
        module_name (str): Name of module ('core', 'assets', etc.)
    
    Returns:
        bool: True if data present, False otherwise
    """
    pass

def _load_debug_data_file(module_name):
    """
    Load debug data JSON file for a module
    
    Args:
        module_name (str): Name of module
    
    Returns:
        dict: Debug data or None if file doesn't exist
    """
    pass
```

#### Testing
- Test with empty debug files (should skip gracefully)
- Test with missing debug files (should skip gracefully)
- Test with existing data (should skip insertion)
- Test with new data (should insert)
- Test fail-fast behavior (stop on first error)

---

### Phase 3: Create Module-Specific Debug Insertion Functions
**Goal**: Create insertion functions for each module using factories/contexts

#### Tasks
1. **Create `app/debug/add_core_debugging_data.py`**
   - Function: `insert_core_debug_data(debug_data, system_user_id)`
   - Use `User.find_or_create_from_dict()` for users
   - Use `MajorLocation.find_or_create_from_dict()` for locations
   - Use `AssetType.find_or_create_from_dict()` for asset types
   - Use `MakeModelFactory.create_make_model_from_dict()` for make/models
   - Use `AssetFactory.create_asset_from_dict()` for assets
   - Check for existing data by ID before inserting

2. **Create `app/debug/add_assets_debugging_data.py`**
   - Function: `insert_assets_debug_data(debug_data, system_user_id)`
   - Use `AssetDetailFactory` for asset details
   - Use `ModelDetailFactory` for model details
   - Use detail table contexts for complex operations
   - Check for existing data by ID before inserting

3. **Create `app/debug/add_dispatching_debugging_data.py`**
   - Function: `insert_dispatching_debug_data(debug_data, system_user_id)`
   - Use appropriate factories/contexts for dispatch data
   - Check for existing data by ID before inserting

4. **Create `app/debug/add_maintenance_debugging_data.py`**
   - Function: `insert_maintenance_debug_data(debug_data, system_user_id)`
   - Use `MaintenanceActionSetFactory` for action sets
   - Use `ActionFactory` for actions
   - Use `MaintenanceFactory` for complete maintenance workflows
   - Check for existing data by ID before inserting

5. **Create `app/debug/add_inventory_debugging_data.py`**
   - Function: `insert_inventory_debug_data(debug_data, system_user_id)`
   - Use appropriate factories/contexts for inventory data
   - Check for existing data by ID before inserting

#### Code Pattern
Each module function should follow this pattern:
```python
def insert_<module>_debug_data(debug_data, system_user_id):
    """
    Insert debug data for <module> module
    
    Args:
        debug_data (dict): Debug data from JSON file
        system_user_id (int): System user ID for audit fields
    
    Raises:
        Exception: If insertion fails (fail-fast)
    """
    if not debug_data:
        logger.info(f"No {module} debug data to insert")
        return
    
    # Check if data already present
    if _check_<module>_data_present(debug_data):
        logger.info(f"{module} debug data already present, skipping")
        return
    
    # Insert data using factories/contexts
    try:
        # Insert data here using factories
        db.session.commit()
        logger.info(f"Successfully inserted {module} debug data")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to insert {module} debug data: {e}")
        raise
```

#### Testing
- Test each module function independently
- Test with empty data (should skip)
- Test with existing data (should skip)
- Test with new data (should insert)
- Test error handling (should rollback and raise)

---

### Phase 4: Update Critical Data Handling
**Goal**: Ensure critical data is always verified and inserted

#### Tasks
1. **Update `app/build.py` - `insert_data()` function**
   - Always load and verify `build_data_critical.json` first
   - Attempt to insert critical data
   - If insertion fails, stop application immediately
   - Log critical data verification

2. **Create critical data verification function**
   - Function: `verify_critical_data()`
   - Check for System user (id=0)
   - Check for Admin user (id=1)
   - Check for System_Initialized event
   - Check for Vehicle asset type
   - Return True if all present, False otherwise

3. **Update critical data insertion**
   - Function: `insert_critical_data()`
   - Load from `app/data/core/build_data_critical.json`
   - Use factories/contexts for insertion
   - Fail-fast: Stop if any critical data fails to insert

#### Code Changes
```python
# app/build.py

def insert_critical_data():
    """
    Insert critical data that must always be present
    
    Raises:
        Exception: If critical data insertion fails (stops application)
    """
    critical_file = Path(__file__).parent.parent / 'data' / 'core' / 'build_data_critical.json'
    
    if not critical_file.exists():
        raise FileNotFoundError(f"Critical data file not found: {critical_file}")
    
    with open(critical_file, 'r') as f:
        critical_data = json.load(f)
    
    # Verify critical data is present
    if not verify_critical_data():
        logger.warning("Critical data missing, attempting insertion...")
        # Insert critical data using factories
        # If insertion fails, raise exception to stop application
```

#### Testing
- Test with missing critical data file (should fail)
- Test with invalid critical data (should fail)
- Test with existing critical data (should verify and continue)
- Test with missing critical records (should insert)

---

### Phase 5: Integrate Debug Data Manager into Build Process
**Goal**: Integrate debug data manager into `app/build.py`

#### Tasks
1. **Update `app/build.py` - `build_database()` function**
   - After tables are initialized
   - After critical data is inserted
   - Call `debug_data_manager.insert_debug_data()` if enabled
   - Pass phase information to debug data manager

2. **Update `app/build.py` - `insert_data()` function**
   - Remove test data insertion from phase-specific functions
   - Keep only critical data insertion in build files
   - Call debug data manager after critical data

#### Code Changes
```python
# app/build.py

def build_database(build_phase='all', data_phase='all', enable_debug_data=True):
    """
    Main build orchestrator
    
    Args:
        build_phase (str): Phase to build
        data_phase (str): Phase for data insertion
        enable_debug_data (bool): Whether to insert debug data (default: True)
    """
    app = create_app()
    
    with app.app_context():
        # Build models
        if build_phase != 'none':
            build_models(build_phase)
        
        # Always insert critical data (regardless of flags)
        insert_critical_data()
        
        # Insert phase-specific data (if not --build-only)
        if data_phase != 'none':
            insert_data(data_phase)
        
        # Insert debug data (if enabled and not --build-only)
        if enable_debug_data and data_phase != 'none':
            from app.debug.debug_data_manager import insert_debug_data
            try:
                insert_debug_data(enabled=True, phase=data_phase)
            except Exception as e:
                logger.error(f"Debug data insertion failed: {e}")
                raise
```

#### Testing
- Test with `--build-only` (should skip debug data)
- Test with `--no-debug-data` (should skip debug data)
- Test with `--enable-debug-data` (should insert debug data)
- Test phase-specific debug data insertion
- Test fail-fast behavior

---

### Phase 6: Migrate Test Data from Build Files
**Goal**: Move test data from `app/utils/build_data.json` to debug files

#### Tasks
1. **Identify test data in `app/utils/build_data.json`**
   - Review all sections: Core, Asset_Details, Dispatching, Supply, Maintenance
   - Identify what's test data vs. critical data
   - Document mapping: source → destination

2. **Create debug JSON files**
   - `app/debug/data/core.json` - Core test data
   - `app/debug/data/assets.json` - Asset test data
   - `app/debug/data/dispatching.json` - Dispatching test data
   - `app/debug/data/maintenance.json` - Maintenance test data
   - `app/debug/data/inventory.json` - Inventory test data

3. **Move test data to debug files**
   - Extract test data from `build_data.json`
   - Ensure all debug data specifies IDs for presence detection
   - Maintain JSON structure compatibility
   - Update insertion functions to use new data structure

4. **Update build files to remove test data**
   - Remove test data insertion from `app/data/core/build.py`
   - Remove test data insertion from `app/data/assets/build.py`
   - Remove test data insertion from `app/data/maintenance/build.py`
   - Keep only critical data insertion in build files

#### Data Migration Checklist
- [ ] Core: Users (Generic_User), Locations, Make/Models, Assets
- [ ] Assets: Detail table configurations, sample detail data
- [ ] Dispatching: Users, dispatch configurations, example dispatches
- [ ] Supply: Parts, Tools, Part Demands
- [ ] Maintenance: Templates, plans, action sets, events
- [ ] Inventory: Sample inventory data (if any)

#### Testing
- Test that all test data is moved to debug files
- Test that build files no longer insert test data
- Test that debug files can be loaded and inserted
- Test that existing functionality still works

---

### Phase 7: Refactor Build Files to Use Factories
**Goal**: Update build files to use factories/contexts instead of direct inserts

#### Tasks
1. **Update `app/data/core/build.py`**
   - Replace direct `User(**data)` with `User.find_or_create_from_dict()`
   - Replace direct `AssetType(**data)` with `AssetType.find_or_create_from_dict()`
   - Use `MakeModelFactory` for make/models
   - Use `AssetFactory` for assets

2. **Update `app/data/assets/build.py`**
   - Use `AssetDetailFactory` for asset details
   - Use `ModelDetailFactory` for model details
   - Use detail table contexts for complex operations

3. **Update `app/data/maintenance/build.py`**
   - Use `MaintenanceActionSetFactory` for action sets
   - Use `ActionFactory` for actions
   - Use `MaintenanceFactory` for complete workflows

4. **Update other build files**
   - Apply factory/context pattern consistently
   - Remove direct table inserts
   - Maintain backward compatibility during transition

#### Code Pattern
Replace:
```python
# Old: Direct insert
asset = Asset(**asset_data)
db.session.add(asset)
```

With:
```python
# New: Factory pattern
asset, created = AssetFactory.create_asset_from_dict(
    asset_data=asset_data,
    created_by_id=system_user_id,
    commit=False,
    lookup_fields=['serial_number']
)
```

#### Testing
- Test that factories are used correctly
- Test that validation works
- Test that business rules are enforced
- Test backward compatibility

---

### Phase 8: Testing and Validation
**Goal**: Comprehensive testing of the new system

#### Test Scenarios
1. **Critical Data Tests**
   - [ ] Critical data always inserted
   - [ ] Critical data verification works
   - [ ] Critical data insertion failure stops application

2. **Debug Data Tests**
   - [ ] Debug data inserted when enabled
   - [ ] Debug data skipped when disabled
   - [ ] Debug data skipped when already present
   - [ ] Debug data fail-fast behavior
   - [ ] Missing debug files handled gracefully
   - [ ] Empty debug files handled gracefully

3. **Build Flag Tests**
   - [ ] `--build-only` creates tables only
   - [ ] `--enable-debug-data` inserts debug data (default)
   - [ ] `--no-debug-data` skips debug data
   - [ ] Phase flags work correctly
   - [ ] Critical data always inserted regardless of flags

4. **Factory/Context Tests**
   - [ ] All data insertion uses factories
   - [ ] Validation works correctly
   - [ ] Business rules enforced
   - [ ] Error handling works

5. **Integration Tests**
   - [ ] Full build process works
   - [ ] Data dependencies respected
   - [ ] Build order followed correctly
   - [ ] No data conflicts

#### Test Commands
```bash
# Test critical data only
python app.py --build-only

# Test with debug data (default)
python app.py --rebuild

# Test without debug data
python app.py --rebuild --no-debug-data

# Test phase-specific builds
python app.py --phase1
python app.py --phase2 --enable-debug-data
```

---

## Implementation Checklist

### Phase 1: Command-Line Interface
- [ ] Update `app.py` argument parser
- [ ] Add `--enable-debug-data` flag (default: True)
- [ ] Add `--no-debug-data` flag
- [ ] Update `--build-only` behavior
- [ ] Test flag handling

### Phase 2: Debug Data Manager
- [ ] Create `debug_data_manager.py`
- [ ] Implement `insert_debug_data()` function
- [ ] Implement data presence detection
- [ ] Implement module loading
- [ ] Test manager functionality

### Phase 3: Module Insertion Functions
- [ ] Create `add_core_debugging_data.py`
- [ ] Create `add_assets_debugging_data.py`
- [ ] Create `add_dispatching_debugging_data.py`
- [ ] Create `add_maintenance_debugging_data.py`
- [ ] Create `add_inventory_debugging_data.py`
- [ ] Test each module function

### Phase 4: Critical Data Handling
- [ ] Create `verify_critical_data()` function
- [ ] Create `insert_critical_data()` function
- [ ] Update `app/build.py` to always verify/insert critical data
- [ ] Test critical data handling

### Phase 5: Integration
- [ ] Update `build_database()` to call debug data manager
- [ ] Integrate after tables initialized and critical data inserted
- [ ] Test integration

### Phase 6: Data Migration
- [ ] Identify all test data in `build_data.json`
- [ ] Create debug JSON files
- [ ] Move test data to debug files
- [ ] Update build files to remove test data
- [ ] Test data migration

### Phase 7: Factory Refactoring
- [ ] Update `app/data/core/build.py` to use factories
- [ ] Update `app/data/assets/build.py` to use factories
- [ ] Update `app/data/maintenance/build.py` to use factories
- [ ] Update other build files
- [ ] Test factory usage

### Phase 8: Testing
- [ ] Critical data tests
- [ ] Debug data tests
- [ ] Build flag tests
- [ ] Factory/context tests
- [ ] Integration tests

---

## File Structure

### New Files to Create
```
app/debug/
├── debug_data_manager.py          # NEW
├── add_core_debugging_data.py     # NEW
├── add_assets_debugging_data.py   # NEW
├── add_inventory_debugging_data.py # NEW
├── add_maintenance_debugging_data.py # NEW
├── add_dispatching_debugging_data.py # NEW
└── data/
    ├── core.json                  # NEW (migrate from build_data.json)
    ├── assets.json                # NEW (migrate from build_data.json)
    ├── inventory.json             # NEW (migrate from build_data.json)
    ├── maintenance.json           # NEW (migrate from build_data.json)
    └── dispatching.json           # NEW (migrate from build_data.json)
```

### Files to Modify
```
app.py                             # Update argument parser
app/build.py                       # Integrate debug data manager, critical data handling
app/data/core/build.py            # Use factories, remove test data
app/data/assets/build.py          # Use factories, remove test data
app/data/maintenance/build.py     # Use factories, remove test data
app/data/dispatching/build.py     # Use factories, remove test data
app/data/inventory/build.py       # Use factories, remove test data
```

---

## Risk Mitigation

### Risks
1. **Breaking existing functionality**: Test thoroughly before removing old code
2. **Data loss during migration**: Backup database before migration
3. **Factory/context compatibility**: Test all factories work correctly
4. **Performance impact**: Monitor insertion performance

### Mitigation Strategies
1. **Incremental implementation**: One module at a time
2. **Backward compatibility**: Keep old code until new code is proven
3. **Comprehensive testing**: Test each phase before moving to next
4. **Rollback plan**: Keep backups and ability to revert

---

## Success Criteria

1. ✅ Critical data always verified and inserted
2. ✅ Debug data can be enabled/disabled via flags
3. ✅ Debug data skipped if already present
4. ✅ All data insertion uses factories/contexts
5. ✅ Build files no longer contain test data
6. ✅ Fail-fast error handling works
7. ✅ Build order respected
8. ✅ No data conflicts
9. ✅ All tests pass
10. ✅ Documentation updated

---

## Next Steps

1. Start with Phase 1 (Command-Line Interface) - simplest, lowest risk
2. Then Phase 2 (Debug Data Manager) - foundation for everything else
3. Then Phase 3 (Module Functions) - build incrementally
4. Continue through phases sequentially
5. Test after each phase before moving to next

---

## Notes

- All debug data should specify IDs for presence detection
- Use simple ID-based checks: `Model.query.filter_by(id=X).first()`
- Fail-fast: Stop application on any error
- Critical data is ALWAYS checked and inserted regardless of flags
- `--build-only` means only create tables, no data insertion (except critical)
- Debug data files are optional - skip if missing
- Empty debug files are skipped gracefully

