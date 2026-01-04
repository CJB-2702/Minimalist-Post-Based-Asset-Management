"""
Inventory management routes - Portal landing page
"""
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.logger import get_logger

# Import route modules
from app.presentation.routes.inventory.purchase_orders.routes import register_purchase_order_routes
from app.presentation.routes.inventory.purchase_orders.po_linkage_portal import register_po_linkage_routes
from app.presentation.routes.inventory.arrivals.routes import register_arrival_routes
from app.presentation.routes.inventory.arrivals.arrival_linkage_portal import register_arrival_linkage_routes
from app.presentation.routes.inventory.inventory.routes import register_inventory_routes
from app.presentation.routes.inventory.purchase_orders.part_picker import register_part_picker_routes
from app.presentation.routes.inventory.searchbars import register_search_bars_routes
from app.presentation.routes.inventory.storeroom.routes import register_storeroom_routes

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


# Register all route modules
try:
    register_purchase_order_routes(inventory_bp)
    logger.debug("Registered purchase order routes")
except Exception as e:
    logger.error(f"Failed to register purchase order routes: {e}", exc_info=True)
    raise

try:
    register_po_linkage_routes(inventory_bp)
    logger.debug("Registered PO linkage routes")
except Exception as e:
    logger.error(f"Failed to register PO linkage routes: {e}", exc_info=True)
    raise

try:
    register_arrival_routes(inventory_bp)
    logger.debug("Registered arrival routes")
except Exception as e:
    logger.error(f"Failed to register arrival routes: {e}", exc_info=True)
    raise

try:
    register_arrival_linkage_routes(inventory_bp)
    logger.debug("Registered arrival linkage routes")
except Exception as e:
    logger.error(f"Failed to register arrival linkage routes: {e}", exc_info=True)
    raise

try:
    register_inventory_routes(inventory_bp)
    logger.debug("Registered inventory routes")
except Exception as e:
    logger.error(f"Failed to register inventory routes: {e}", exc_info=True)
    raise

try:
    register_part_picker_routes(inventory_bp)
    logger.debug("Registered part picker routes")
except Exception as e:
    logger.error(f"Failed to register part picker routes: {e}", exc_info=True)
    raise

try:
    register_search_bars_routes(inventory_bp)
    logger.debug("Registered search bars routes")
except Exception as e:
    logger.error(f"Failed to register search bars routes: {e}", exc_info=True)
    raise

try:
    register_storeroom_routes(inventory_bp)
    logger.debug("Registered storeroom routes")
except Exception as e:
    logger.error(f"Failed to register storeroom routes: {e}", exc_info=True)
    raise
