from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import os
from app.logger import setup_logging_from_config, get_logger

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    import os
    from pathlib import Path
    
    # Get the base directory (app's parent)
    base_dir = Path(__file__).parent.parent
    
    # Set template and static folders to new presentation folder structure
    template_folder = str(base_dir / 'app' / 'presentation' / 'templates')
    static_folder = str(base_dir / 'app' / 'presentation' / 'static')
    
    app = Flask(__name__, 
                template_folder=template_folder,
                static_folder=static_folder)
    
    # Get singleton logger
    logger = get_logger("asset_management")
    logger.info("Initializing Flask application")
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///asset_management.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    logger.debug(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    logger.debug("Extensions initialized")
    
    # Import and register blueprints
    from app.data import core, assets
    
    # Import models to ensure they're registered with SQLAlchemy
    from app.data.core.user_info.user import User
    from app.data.core.user_created_base import UserCreatedBase
    from app.data.core.major_location import MajorLocation
    from app.data.core.asset_info.asset_type import AssetType
    from app.data.core.asset_info.make_model import MakeModel
    from app.data.core.asset_info.asset import Asset
    from app.data.core.event_info.event import Event
    
    # Import new dispatching models (rebuilt minimal set)
    try:
        from app.data.dispatching.request import DispatchRequest
        from app.data.dispatching.outcomes.standard_dispatch import StandardDispatch
        from app.data.dispatching.outcomes.contract import Contract
        from app.data.dispatching.outcomes.reimbursement import Reimbursement
    except Exception:
        # Dispatching module may be unavailable during certain phases; skip registration
        pass
    
    # Import supply models to ensure they're registered (supply is now part of core)
    try:
        from app.data.core.supply.part_definition import PartDefinition
        from app.data.core.supply.tool_definition import ToolDefinition
    except ImportError as e:
        logger.warning(f"Could not import supply models: {e}")
        pass
    
    # Import maintenance models to ensure they're registered
    try:
        from app.data.maintenance.templates.template_action_sets import TemplateActionSet
        from app.data.maintenance.templates.template_actions import TemplateActionItem
        from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem
        from app.data.maintenance.planning.maintenance_plans import MaintenancePlan
        from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
        from app.data.maintenance.base.actions import Action
        from app.data.maintenance.base.part_demands import PartDemand
        from app.data.maintenance.base.action_tools import ActionTool
    except ImportError as e:
        # Maintenance module may be unavailable during certain phases; skip registration
        logger.warning(f"Could not import maintenance models: {e}")
        pass
    
    logger.debug("Models imported and registered")
    
    # Register blueprints
    from app.auth import auth
    from app.presentation.routes import main
    from app.presentation.routes import init_app as init_routes
    
    app.register_blueprint(auth)
    app.register_blueprint(main)
    
    # Initialize tiered routes system (without re-registering main)
    init_routes(app)
    
    # Add template global to check if endpoint exists
    @app.template_global()
    def endpoint_exists(endpoint):
        """Check if a route endpoint exists - raises exceptions instead of hiding them"""
        # Check if endpoint exists in the URL map
        from flask import has_request_context, current_app
        if has_request_context():
            app_to_check = current_app
        else:
            app_to_check = app
        
        return endpoint in [rule.endpoint for rule in app_to_check.url_map.iter_rules()]
    
    logger.info("Flask application initialization complete")
    
    return app 