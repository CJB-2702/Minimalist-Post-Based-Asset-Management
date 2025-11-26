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

    # Don't register main again - it's already registered in app/__init__.py
    app.register_blueprint(core.bp, url_prefix='/core')
    app.register_blueprint(assets.bp, url_prefix='/assets')

    # Register individual core route blueprints
    from .core import assets as core_assets, locations, asset_types, make_models, users, dashboard
    from .core.events import events as core_events
    from .core.events import comments as core_comments
    from .core.events import attachments as core_attachments

    # Register core dashboard
    app.register_blueprint(dashboard.bp, url_prefix='/core')
    
    app.register_blueprint(core_events.bp, url_prefix='/core')
    app.register_blueprint(core_assets.bp, url_prefix='/core', name='core_assets')
    app.register_blueprint(locations.bp, url_prefix='/core')
    app.register_blueprint(asset_types.bp, url_prefix='/core')
    app.register_blueprint(make_models.bp, url_prefix='/core')
    app.register_blueprint(users.bp, url_prefix='/core')

    # Register comments and attachments blueprints
    app.register_blueprint(core_comments.bp, url_prefix='')
    app.register_blueprint(core_attachments.bp, url_prefix='')
    
    # Register dispatching blueprint (new minimal rebuild)
    from .dispatching import dispatching_bp
    app.register_blueprint(dispatching_bp, url_prefix='/dispatching')
    
    # Register maintenance blueprints - optional during rebuild
    try:
        from .maintenance.main import maintenance_bp
        app.register_blueprint(maintenance_bp)
        logger.info("Registered maintenance main blueprint")
        
        # Try to register sub-blueprints if they exist
        try:
            from .maintenance import (
                maintenance_plans, 
                maintenance_action_sets,
                actions, 
                part_demands, 
                delays,
                template_actions,
                proto_action_items,
                template_part_demands,
                template_action_tools
            )
            
            app.register_blueprint(maintenance_plans.bp, url_prefix='/maintenance', name='maintenance_plans')
            app.register_blueprint(maintenance_action_sets.bp, url_prefix='/maintenance', name='maintenance_action_sets')
            app.register_blueprint(actions.bp, url_prefix='/maintenance', name='actions')
            app.register_blueprint(part_demands.bp, url_prefix='/maintenance', name='part_demands')
            app.register_blueprint(delays.bp, url_prefix='/maintenance', name='delays')
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
            from .maintenance.technician import technician_bp
            app.register_blueprint(technician_bp)
            portal_blueprints_registered += 1
            logger.debug("Registered technician portal blueprint")
        except ImportError as e:
            logger.debug(f"Technician portal blueprint not available: {e}")
        
        # Register manager portal
        try:
            from .maintenance.manager import manager_bp, template_builder_bp
            app.register_blueprint(manager_bp)
            app.register_blueprint(template_builder_bp)
            portal_blueprints_registered += 1
            logger.debug("Registered manager portal blueprint and template builder blueprint")
        except ImportError as e:
            logger.debug(f"Manager portal blueprint not available: {e}")
        
        # Register fleet portal
        try:
            from .maintenance.fleet import fleet_bp
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
        from .core.supply import parts as core_supply_parts, tools as core_supply_tools, issuable_tools as core_supply_issuable_tools
        
        # Register main supply blueprint with /core prefix
        app.register_blueprint(supply_bp, url_prefix='/core')
        
        # Register parts, tools, and issuable_tools blueprints separately to avoid nested endpoint names
        app.register_blueprint(core_supply_parts.bp, url_prefix='/core/supply/parts')
        app.register_blueprint(core_supply_tools.bp, url_prefix='/core/supply/tools')
        app.register_blueprint(core_supply_issuable_tools.bp, url_prefix='/core/supply/issuable-tools')
        
        logger.info("Registered core supply blueprints")
    except ImportError as e:
        logger.warning(f"Core supply blueprints not available: {e}")
    
    logger.info("All route blueprints registered successfully") 