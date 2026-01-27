"""
Inventory management routes - Portal landing page
"""
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.logger import get_logger

logger = get_logger("asset_management.routes.inventory")

# Create inventory blueprint
inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')


@inventory_bp.route('/')
@inventory_bp.route('/index')
@login_required
def index():
    """Inventory management portal landing page"""
    logger.info(f"Inventory portal accessed by {current_user.username}")
    
    return render_template('inventory/index.html')


# Import route modules to register their routes
# Routes are registered automatically when modules are imported
from app.presentation.routes.inventory import purchasing
from app.presentation.routes.inventory.purchasing import routes as po_routes
from app.presentation.routes.inventory.purchasing import po_linkage_portal
from app.presentation.routes.inventory.purchasing import part_picker
from app.presentation.routes.inventory.purchasing import po_portal
from app.presentation.routes.inventory import arrivals
from app.presentation.routes.inventory.arrivals import routes as arrival_routes
from app.presentation.routes.inventory.arrivals import arrival_linkage_portal
from app.presentation.routes.inventory import inventory
from app.presentation.routes.inventory.inventory import routes as inventory_routes
from app.presentation.routes.inventory.inventory import move_inventory_gui
from app.presentation.routes.inventory import searchbars
from app.presentation.routes.inventory import storeroom
from app.presentation.routes.inventory.storeroom import routes as storeroom_routes
