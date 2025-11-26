#!/usr/bin/env python3
"""
Main build orchestrator for the Asset Management System
Handles phased building of models and data insertion
"""

from app import create_app, db
from pathlib import Path
import json
from app.logger import get_logger

logger = get_logger("asset_management.build")

def check_system_initialization():
    """
    Check if the system has been properly initialized
    
    Returns:
        bool: True if system is properly initialized, False otherwise
    """
    from app.data.core.event_info.event import Event
    from app.data.core.user_info.user import User
    
    try:
        # Check if system initialization event exists
        system_event = Event.query.filter_by(
            event_type='System',
            description='System initialized with core data'
        ).first()
        
        # Check if system user exists
        system_user = User.query.filter_by(username='system').first()
        
        # Check if essential data exists
        from app.data.core.asset_info.asset_type import AssetType
        asset_types = AssetType.query.first()
        
        return system_event is not None and system_user is not None and asset_types is not None
        
    except Exception as e:
        logger.error(f"Error checking system initialization: {e}")
        return False


def verify_critical_data():
    """
    Verify that critical data is present in the database
    
    Returns:
        bool: True if all critical data is present, False otherwise
    """
    from app.data.core.user_info.user import User
    from app.data.core.event_info.event import Event
    from app.data.core.asset_info.asset_type import AssetType
    
    try:
        # Check for System user (id=0)
        system_user = User.query.filter_by(id=0, username='system').first()
        if not system_user:
            logger.warning("System user (id=0) not found")
            return False
        
        # Check for Admin user (id=1)
        admin_user = User.query.filter_by(id=1, username='admin').first()
        if not admin_user:
            logger.warning("Admin user (id=1) not found")
            return False
        
        # Check for System_Initialized event
        system_event = Event.query.filter_by(
            event_type='System',
            description='System initialized with core data'
        ).first()
        if not system_event:
            logger.warning("System_Initialized event not found")
            return False
        
        # Check for Vehicle asset type
        vehicle_type = AssetType.query.filter_by(name='Vehicle').first()
        if not vehicle_type:
            logger.warning("Vehicle asset type not found")
            return False
        
        logger.info("Critical data verification passed")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying critical data: {e}")
        return False


def insert_critical_data():
    """
    Insert critical data that must always be present
    
    Loads from app/data/core/build_data_critical.json and inserts using factories.
    This function is called ALWAYS, regardless of flags.
    
    Raises:
        FileNotFoundError: If critical data file not found
        Exception: If critical data insertion fails (stops application)
    """
    critical_file = Path(__file__).parent / 'data' / 'core' / 'build_data_critical.json'
    
    if not critical_file.exists():
        error_msg = f"Critical data file not found: {critical_file}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    logger.info("Loading critical data from build_data_critical.json...")
    with open(critical_file, 'r') as f:
        critical_data = json.load(f)
    
    # Verify critical data is present first
    if verify_critical_data():
        logger.info("Critical data already present, skipping insertion")
        return
    
    logger.warning("Critical data missing, attempting insertion...")
    
    # Get system user for audit fields (may not exist yet)
    from app.data.core.user_info.user import User
    system_user = User.query.filter_by(username='system').first()
    system_user_id = system_user.id if system_user else None
    
    try:
        # Insert Essential Users
        if 'Essential' in critical_data and 'Users' in critical_data['Essential']:
            logger.info("Inserting essential users...")
            for user_key, user_data in critical_data['Essential']['Users'].items():
                User.find_or_create_from_dict(
                    user_data,
                    user_id=system_user_id,
                    lookup_fields=['username']
                )
                logger.info(f"Inserted essential user: {user_data.get('username')}")
        
        # Insert Essential Events (System_Initialized)
        if 'Essential' in critical_data and 'Events' in critical_data['Essential']:
            logger.info("Inserting essential events...")
            from app.data.core.build import create_system_initialization_event
            # The create_system_initialization_event function handles the event creation
            create_system_initialization_event(system_user_id, force_create=True)
        
        # Insert Core Asset Types
        if 'Core' in critical_data and 'Asset_Types' in critical_data['Core']:
            logger.info("Inserting core asset types...")
            from app.data.core.asset_info.asset_type import AssetType
            for type_key, type_data in critical_data['Core']['Asset_Types'].items():
                AssetType.find_or_create_from_dict(
                    type_data,
                    user_id=system_user_id,
                    lookup_fields=['name']
                )
                logger.info(f"Inserted asset type: {type_data.get('name')}")
        
        db.session.commit()
        logger.info("Successfully inserted critical data")
        
        # Verify again after insertion
        if not verify_critical_data():
            error_msg = "Critical data insertion completed but verification failed"
            logger.error(error_msg)
            raise Exception(error_msg)
        
    except Exception as e:
        db.session.rollback()
        error_msg = f"Critical data insertion failed: {e}"
        logger.error(error_msg)
        raise Exception(error_msg)

def build_database(build_phase='all', data_phase='all', enable_debug_data=True):
    """
    Main build orchestrator for the Asset Management System
    
    Args:
        build_phase (str): 'phase1', 'phase2', 'phase3', 'all', or 'none'
        data_phase (str): 'phase1', 'phase2', 'phase3', 'all', or 'none'
        enable_debug_data (bool): Whether to insert debug data (default: True)
                                  Note: Critical data is ALWAYS checked and inserted regardless of flags
    """
    app = create_app()
    
    with app.app_context():
        logger.info(f"Starting database build - Build Phase: {build_phase}, Data Phase: {data_phase}")
        
        # Build models based on phase
        if build_phase != 'none':
            build_models(build_phase)
        
        # ALWAYS verify and insert critical data (regardless of flags)
        # Critical data must be present for the application to function
        logger.info("Verifying and inserting critical data (always required)...")
        try:
            insert_critical_data()
        except Exception as e:
            logger.error(f"Critical data insertion failed: {e}")
            logger.error("Application cannot continue without critical data. Stopping build.")
            raise
        
        # Check if system is properly initialized (after critical data is inserted)
        system_initialized = check_system_initialization()
        
        # Data insertion is now handled by:
        # 1. insert_critical_data() - Always runs (handled above)
        # 2. debug_data_manager - Handles all test/debug data (handled below)
        # The old insert_data() function has been removed as all test data
        # insertion has been moved to the debug data manager
        
        # Ensure system initialization event exists (part of critical data)
        if not system_initialized:
            logger.info("System not properly initialized, forcing system initialization event creation")
            from app.data.core.build import create_system_initialization_event
            from app.data.core.user_info.user import User
            
            system_user = User.query.filter_by(username='system').first()
            system_user_id = system_user.id if system_user else None
            
            create_system_initialization_event(system_user_id, force_create=True)
        
        # Insert debug data (if enabled and not --build-only)
        if enable_debug_data and data_phase != 'none':
            try:
                from app.debug.debug_data_manager import insert_debug_data
                logger.info("Inserting debug data...")
                insert_debug_data(enabled=True, phase=data_phase)
            except Exception as e:
                logger.error(f"Debug data insertion failed: {e}")
                raise
        
        logger.info("Database build completed successfully")

def build_models(phase):
    """
    Build database models based on the specified phase
    
    Args:
        phase (str): 'phase1', 'phase2', 'phase3', 'phase4', 'phase5', 'phase6', or 'all'
    """
    logger.info(f"Building models for phase: {phase}")
    
    if phase in ['phase1', 'phase2', 'phase3', 'phase4', 'phase5', 'phase6', 'all']:
        logger.info("Building Phase 1 models (Core Foundation)")
        from app.data.core.build import build_models as build_core_models
        build_core_models()
    
    if phase in ['phase2', 'phase3', 'phase4', 'phase5', 'phase6', 'all']:
        logger.info("Building Phase 2 models (Asset Details)")
        from app.data.assets.build import build_models as build_asset_models
        build_asset_models()
    
    if phase in ['phase3', 'phase4', 'phase5', 'phase6', 'all']:
        logger.info("Building Phase 3 models (Dispatching)")
        from app.data.dispatching.build import build_dispatch_models
        build_dispatch_models()
    
    if phase in ['phase4', 'phase5', 'phase6', 'all']:
        logger.info("Building Phase 4 models (Supply)")
        from app.data.core.supply.build import build_models as build_supply_models
        build_supply_models()
    
    if phase in ['phase5', 'phase6', 'all']:
        logger.info("Building Phase 5 models (Maintenance)")
        from app.data.maintenance.build import build_models as build_maintenance_models
        build_maintenance_models()
    
    if phase in ['phase6', 'all']:
        logger.info("Building Phase 6 models (Inventory & Purchasing)")
        from app.data.inventory.build import build_models as build_inventory_models
        build_inventory_models()
    
    # Create all tables
    db.create_all()
    logger.info("All database tables created")

# insert_data() function has been removed
# All data insertion is now handled by:
# 1. insert_critical_data() - Handles critical data (always runs)
# 2. debug_data_manager.insert_debug_data() - Handles all test/debug data
# Build files now only contain table creation logic (build_models functions)


# load_build_data() function removed
# Build data is now loaded by:
# 1. insert_critical_data() - Loads from app/data/core/build_data_critical.json
# 2. debug_data_manager - Loads from app/debug/data/*.json files

def build_models_only(phase):
    """
    Build only the models without inserting data
    
    Args:
        phase (str): 'phase1', 'phase2', 'phase3', 'phase4', 'phase5', or 'all'
    """
    build_database(build_phase=phase, data_phase='none')

# create_default_admin_user() function removed
# Admin user is now part of critical data and is inserted by insert_critical_data()
# See app/data/core/build_data_critical.json for admin user definition

def insert_data_only(phase):
    """
    Insert only data without building models
    
    Args:
        phase (str): 'phase1', 'phase2', 'phase3', 'phase4', 'phase5', or 'all'
    """
    build_database(build_phase='none', data_phase=phase)

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        build_phase = sys.argv[1]
        data_phase = sys.argv[2] if len(sys.argv) > 2 else build_phase
        build_database(build_phase=build_phase, data_phase=data_phase)
    else:
        build_database() 