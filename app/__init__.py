from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from app.logger import setup_logging_from_config, get_logger

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"  # Use Redis in production for distributed systems
)

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
    # SECURITY: Require SECRET_KEY in environment - no fallback
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    if not app.config['SECRET_KEY']:
        logger.critical("SECRET_KEY not set in environment! Application cannot start.")
        raise RuntimeError("SECRET_KEY environment variable is required")

    # Prefer an explicit DATABASE_URL env var; if not provided, store the
    # SQLite database inside the project's `instance/` directory so it is
    # persisted via the docker-compose volume and path resolution is reliable.
    from pathlib import Path
    base_dir = Path(__file__).parent.parent
    instance_dir = base_dir / 'instance'
    instance_dir.mkdir(parents=True, exist_ok=True)
    """
    db_env = os.environ.get('DATABASE_URL')
    if db_env:
        app.config['SQLALCHEMY_DATABASE_URI'] = db_env
    else:
        # Use absolute path to avoid relative path issues inside the container
    """
    default_db_path = instance_dir / 'asset_management.db'
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{str(default_db_path.resolve())}"

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # HTTPS/TLS Configuration
    # Default to True (secure) for production - only disable for development
    app.config['ENABLE_HTTPS'] = os.environ.get('ENABLE_HTTPS', 'True').lower() in ('true', '1', 'yes', 'on')
    app.config['FORCE_HTTPS_REDIRECT'] = os.environ.get('FORCE_HTTPS_REDIRECT', 'True').lower() in ('true', '1', 'yes', 'on')
    
    # Session cookie security configuration
    # Default to True (secure) - only set to False for development (HTTP)
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'True').lower() in ('true', '1', 'yes', 'on')
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access to session cookie
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
    app.config['PERMANENT_SESSION_LIFETIME'] = int(os.environ.get('PERMANENT_SESSION_LIFETIME', '3600'))  # Default: 1 hour
    
    # Remember me cookie security
    app.config['REMEMBER_COOKIE_SECURE'] = os.environ.get('REMEMBER_COOKIE_SECURE', 'True').lower() in ('true', '1', 'yes', 'on')
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    app.config['REMEMBER_COOKIE_DURATION'] = int(os.environ.get('REMEMBER_COOKIE_DURATION', '86400'))  # Default: 24 hours
    
    # Password policy configuration
    app.config['PASSWORD_EXPIRATION_DAYS'] = int(os.environ.get('PASSWORD_EXPIRATION_DAYS', '90'))  # Default: 90 days
    app.config['PASSWORD_HISTORY_COUNT'] = int(os.environ.get('PASSWORD_HISTORY_COUNT', '5'))  # Default: remember last 5 passwords
    app.config['MAX_FAILED_LOGIN_ATTEMPTS'] = int(os.environ.get('MAX_FAILED_LOGIN_ATTEMPTS', '5'))  # Default: 5 attempts
    app.config['ACCOUNT_LOCKOUT_MINUTES'] = int(os.environ.get('ACCOUNT_LOCKOUT_MINUTES', '30'))  # Default: 30 minutes lockout
    
    # Log security configuration status
    if app.config['ENABLE_HTTPS']:
        logger.info("HTTPS enforcement enabled")
        if app.config['FORCE_HTTPS_REDIRECT']:
            logger.info("Automatic HTTP to HTTPS redirect enabled")
    else:
        logger.warning("⚠️  HTTPS enforcement DISABLED - Acceptable for development only!")

    logger.debug("Database configured: SQLite")
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    logger.debug("Extensions initialized")
    
    # Import and register blueprints
    from app.data import core, assets
    
    # Import models to ensure they're registered with SQLAlchemy
    from app.data.core.user_info.user import User
    from app.data.core.user_info.password_history import PasswordHistory
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
    
    # Add HTTPS redirect before request processing
    @app.before_request
    def enforce_https():
        """Redirect HTTP requests to HTTPS if HTTPS enforcement is enabled"""
        if app.config.get('ENABLE_HTTPS') and app.config.get('FORCE_HTTPS_REDIRECT'):
            from flask import request, redirect, url_for
            
            # Check if request is not secure (HTTP) and not already HTTPS
            if not request.is_secure and not request.headers.get('X-Forwarded-Proto') == 'https':
                # Get the full URL and replace http:// with https://
                url = request.url.replace('http://', 'https://', 1)
                return redirect(url, code=301)  # 301 Permanent Redirect
    
    # Check for password expiration on each request
    @app.before_request
    def check_password_expiration():
        """Check if authenticated user's password has expired"""
        from flask_login import current_user
        from flask import request, flash, url_for, redirect
        
        # Skip check for unauthenticated users
        if not current_user.is_authenticated:
            return None
        
        # Skip check for static files and auth endpoints
        if request.endpoint and (request.endpoint.startswith('static') or 
                                request.endpoint.startswith('auth.')):
            return None
        
        # Skip check for password change endpoint (when we implement it)
        if request.endpoint and 'password' in request.endpoint:
            return None
        
        # Check if password is expired
        if current_user.is_password_expired():
            flash('Your password has expired. Please change your password to continue.', 'error')
            # TODO: Redirect to password change page when implemented
            # For now, just log and show warning
            logger.warning(f"User {current_user.username} attempted access with expired password")
            # return redirect(url_for('auth.change_password'))
        
        return None
    
    # Add security headers to all responses
    @app.after_request
    def set_security_headers(response):
        """Add security headers to all responses"""
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        
        # Prevent MIME-sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Enable XSS filter (legacy browsers)
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Content Security Policy
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:;"
        )
        
        # HTTPS Strict Transport Security (HSTS)
        # Enable when HTTPS is configured to prevent protocol downgrade attacks
        if app.config.get('ENABLE_HTTPS'):
            # max-age=31536000 (1 year), includeSubDomains applies to all subdomains
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
    
    logger.info("Flask application initialization complete")
    
    return app 