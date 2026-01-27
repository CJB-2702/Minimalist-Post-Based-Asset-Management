"""
Routes package for the Asset Management System
Organized in a tiered structure mirroring the model organization
"""

from flask import Blueprint
from app.logger import get_logger

logger = get_logger("asset_management.routes")

# Create main blueprint
main = Blueprint('main', __name__)

# Import route modules
from . import core, assets, main_routes


def init_app(app):
    """Initialize all route blueprints with the Flask app"""
    logger.debug("Initializing route blueprints")

    # Register public routes (non-authenticated pages)
    from .public import public_bp
    app.register_blueprint(public_bp)
    logger.info("Registered public routes blueprint")

    # Don't register main again - it's already registered in app/__init__.py
    app.register_blueprint(core.bp, url_prefix='/core')
    app.register_blueprint(assets.bp, url_prefix='/assets')

    # Register individual core route blueprints
    from .core import assets as core_assets, locations, asset_types, make_models, users, dashboard, meter_history
    from .core.events import events as core_events
    from .core.events import comments as core_comments
    from .core.events import attachments as core_attachments
    from .core.admin import settings_cache_viewer

    # Register core dashboard
    app.register_blueprint(dashboard.bp, url_prefix='/core')
    
    app.register_blueprint(core_events.bp, url_prefix='/core')
    app.register_blueprint(core_assets.bp, url_prefix='/core', name='core_assets')
    app.register_blueprint(locations.bp, url_prefix='/core')
    app.register_blueprint(asset_types.bp, url_prefix='/core')
    app.register_blueprint(make_models.bp, url_prefix='/core')
    app.register_blueprint(users.bp, url_prefix='/core')
    app.register_blueprint(meter_history.bp, url_prefix='/core')
    
    # Register core search utilities blueprint
    from .core import searchutils
    app.register_blueprint(searchutils.searchutils_bp)
    
    # Register core admin blueprints
    app.register_blueprint(settings_cache_viewer.bp, url_prefix='/core/users')
    
    # Register main admin blueprint
    from . import admin
    app.register_blueprint(admin.bp, url_prefix='/admin')

    # Register comments and attachments blueprints
    app.register_blueprint(core_comments.bp, url_prefix='')
    app.register_blueprint(core_attachments.bp, url_prefix='')
    
    # Register dispatching blueprint (new minimal rebuild)
    from .dispatching import dispatching_bp
    app.register_blueprint(dispatching_bp, url_prefix='/dispatching')
    
    # Register maintenance blueprints - optional during rebuild
    try:
        from .maintenance.main import maintenance_bp
        
        # IMPORTANT: Import core route modules BEFORE registering the blueprint
        # These modules add routes to maintenance_bp, so they must be imported first
        try:
            from .maintenance.core import action_managment, part_demand, blockers, limitations, tool
            # These modules import maintenance_bp and add routes to it
            logger.info("Loaded maintenance core route modules (action_managment, part_demand, blockers, limitations, tool)")
        except ImportError as e:
            logger.debug(f"Maintenance core route modules not available: {e}")
        
        # Now register the blueprint after all routes have been added to it
        app.register_blueprint(maintenance_bp)
        logger.info("Registered maintenance main blueprint")
        
        # Register maintenance event blueprint (now in core subdirectory)
        try:
            # Register maintenance event portal blueprints (decomposed from maintenance_event.py)
            from .maintenance.core.view_portal import maintenance_event_bp as view_bp
            from .maintenance.core.work_portal import maintenance_event_bp as work_bp
            from .maintenance.core.edit_portal import maintenance_event_bp as edit_bp
            from .maintenance.core.assign_portal import maintenance_event_bp as assign_bp
            from .maintenance.core.maintenance_management import maintenance_event_bp as mgmt_bp
            
            app.register_blueprint(view_bp)
            app.register_blueprint(work_bp)
            app.register_blueprint(edit_bp)
            app.register_blueprint(assign_bp)
            app.register_blueprint(mgmt_bp)
            logger.info("Registered maintenance event blueprint")
        except ImportError as e:
            logger.debug(f"Maintenance event blueprint not available: {e}")
        
        # Register action creator portal blueprint
        try:
            from .maintenance.action_creator_portal import action_creator_portal_bp
            app.register_blueprint(action_creator_portal_bp)
            logger.info("Registered action creator portal blueprint")
        except ImportError as e:
            logger.debug(f"Action creator portal blueprint not available: {e}")
        
        # Register maintenance search utilities blueprint
        try:
            from .maintenance import search_utils
            app.register_blueprint(search_utils.maintenance_searchutils_bp)
            logger.info("Registered maintenance search utilities blueprint")
        except ImportError as e:
            logger.debug(f"Maintenance search utilities blueprint not available: {e}")
        
        # Register maintenance plan planning routes
        try:
            from .maintenance.planning.maintenance_plan_routes import bp as maintenance_plan_bp
            app.register_blueprint(maintenance_plan_bp, url_prefix='/maintenance')
            logger.info("Registered maintenance plan planning blueprint")
        except ImportError as e:
            logger.debug(f"Maintenance plan planning blueprint not available: {e}")
        
        # Try to register sub-blueprints if they exist
        try:
            from .maintenance import (
                maintenance_plans, 
                maintenance_action_sets,
                actions, 
                part_demands, 
                blockers,
                template_actions,
                proto_action_items,
                template_part_demands,
                template_action_tools
            )
            
            app.register_blueprint(maintenance_plans.bp, url_prefix='/maintenance', name='maintenance_plans')
            app.register_blueprint(maintenance_action_sets.bp, url_prefix='/maintenance', name='maintenance_action_sets')
            app.register_blueprint(actions.bp, url_prefix='/maintenance', name='actions')
            app.register_blueprint(part_demands.bp, url_prefix='/maintenance', name='part_demands')
            app.register_blueprint(blockers.bp, url_prefix='/maintenance', name='blockers')
            app.register_blueprint(template_actions.bp, url_prefix='/maintenance', name='template_actions')
            app.register_blueprint(proto_action_items.bp, url_prefix='/maintenance', name='proto_action_items')
            app.register_blueprint(template_part_demands.bp, url_prefix='/maintenance', name='template_part_demands')
            app.register_blueprint(template_action_tools.bp, url_prefix='/maintenance', name='template_action_tools')
            logger.info("Registered maintenance sub-blueprints")
        except ImportError as e:
            logger.debug(f"Maintenance sub-blueprints not available: {e}")
        
        # Try to register maintenance portal blueprints
        portal_blueprints_registered = 0
        
        # Register technician portal
        try:
            from .maintenance.user_views.technician import technician_bp
            app.register_blueprint(technician_bp)
            portal_blueprints_registered += 1
            logger.debug("Registered technician portal blueprint")
        except ImportError as e:
            logger.debug(f"Technician portal blueprint not available: {e}")
        
        # Register manager portal
        try:
            from .maintenance.user_views.manager import manager_bp
            from .maintenance.templates.template_builder import template_builder_bp
            app.register_blueprint(manager_bp)
            # Template builder blueprint: register with full path since blueprint prefix is empty
            app.register_blueprint(template_builder_bp, url_prefix='/maintenance/manager/template-builder')
            portal_blueprints_registered += 1
            logger.debug("Registered manager portal blueprint and template builder blueprint")
        except ImportError as e:
            logger.debug(f"Manager portal blueprint not available: {e}")
        
        # Register fleet portal
        try:
            from .maintenance.user_views.fleet import fleet_bp
            app.register_blueprint(fleet_bp)
            portal_blueprints_registered += 1
            logger.debug("Registered fleet portal blueprint")
        except ImportError as e:
            logger.debug(f"Fleet portal blueprint not available: {e}")
        
        if portal_blueprints_registered > 0:
            logger.info(f"Registered {portal_blueprints_registered} maintenance portal blueprint(s)")
            
    except ImportError as e:
        logger.warning(f"Maintenance main blueprint not available during rebuild: {e}")
        pass
    
    # Register supply blueprints (integrated into core section)
    try:
        from .core.supply.main import supply_bp
        from .core.supply import parts as core_supply_parts, tools as core_supply_tools
        
        # Register main supply blueprint with /core prefix
        app.register_blueprint(supply_bp, url_prefix='/core')
        
        # Register parts and tools blueprints separately to avoid nested endpoint names
        app.register_blueprint(core_supply_parts.bp, url_prefix='/core/supply/part-definitions')
        app.register_blueprint(core_supply_tools.bp, url_prefix='/core/supply/tools')
        
        logger.info("Registered core supply blueprints")
    except ImportError as e:
        logger.warning(f"Core supply blueprints not available: {e}")
    
    # Register inventory blueprint
    try:
        from .inventory import inventory_bp
        app.register_blueprint(inventory_bp)
        logger.info("Registered inventory blueprint")
    except Exception as e:
        logger.error(f"Failed to register inventory blueprint: {e}", exc_info=True)
        raise  # Re-raise to make errors visible
    
    # Register searchbar blueprint
    try:
        from .searchbar import searchbar_bp
        app.register_blueprint(searchbar_bp)
        logger.info("Registered searchbar blueprint")
    except Exception as e:
        logger.error(f"Failed to register searchbar blueprint: {e}", exc_info=True)
        raise  # Re-raise to make errors visible
    
    logger.info("All route blueprints registered successfully") 