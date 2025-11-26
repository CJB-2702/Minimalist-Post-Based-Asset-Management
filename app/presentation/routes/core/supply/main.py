"""
Supply routes - integrated into core section
"""

from flask import Blueprint, redirect, url_for
from flask_login import login_required
from app.logger import get_logger

from .parts import bp as parts_bp
from .tools import bp as tools_bp

logger = get_logger("asset_management.routes.core.supply.main")

# Create main supply blueprint - integrated into core
supply_bp = Blueprint('core_supply', __name__)

# ROUTE_TYPE: WORK_PORTAL (Complex GET)
# This route coordinates multiple domain operations for dashboard statistics.
# Rationale: Aggregates statistics from multiple sources for dashboard view.
@supply_bp.route('/supply')
@login_required
def index():
    """Redirect supply dashboard to parts list"""
    logger.debug("Redirecting supply dashboard to parts list")
    return redirect(url_for('core_supply_parts.list'))

# Note: Parts and tools blueprints are registered separately in routes/__init__.py
# to avoid nested endpoint names (core_supply.core_supply_parts.*)
# They are registered directly to the app with /core/supply/parts and /core/supply/tools prefixes

