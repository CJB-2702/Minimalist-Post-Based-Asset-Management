"""
Supply routes - integrated into core section
"""

from flask import Blueprint, redirect, url_for, render_template
from flask_login import login_required, current_user
from app.logger import get_logger
from app.data.core.supply.part_definition import PartDefinition
from app.data.core.supply.tool_definition import ToolDefinition

logger = get_logger("asset_management.routes.core.supply.main")

# Create main supply blueprint - integrated into core
supply_bp = Blueprint('core_supply', __name__)

# ROUTE_TYPE: WORK_PORTAL (Complex GET)
# This route coordinates multiple domain operations for dashboard statistics.
# Rationale: Aggregates statistics from multiple sources for dashboard view.
@supply_bp.route('/supply')
@login_required
def index():
    """Supply management dashboard"""
    logger.debug(f"User {current_user.username} accessing supply dashboard")
    
    # Get basic statistics
    total_parts = PartDefinition.query.count()
    total_tools = ToolDefinition.query.count()
    
    # Get part demands count (if available)
    try:
        from app.data.maintenance.base.part_demands import PartDemand
        total_part_demands = PartDemand.query.count()
    except ImportError:
        total_part_demands = 0
    
    # Get recent parts
    recent_parts = PartDefinition.query.order_by(PartDefinition.created_at.desc()).limit(5).all()
    
    # Get recent tools
    recent_tools = ToolDefinition.query.order_by(ToolDefinition.created_at.desc()).limit(5).all()
    
    # Get parts by category
    from collections import defaultdict
    parts_by_category = defaultdict(int)
    for part in PartDefinition.query.all():
        category = part.category or 'Uncategorized'
        parts_by_category[category] += 1
    
    # Get tools by type (if available)
    tools_by_type = defaultdict(int)
    for tool in ToolDefinition.query.all():
        tool_type = tool.tool_type or 'Uncategorized'
        tools_by_type[tool_type] += 1
    
    # Stock alerts are managed through inventory system, so we'll leave them empty
    low_stock_parts = []
    out_of_stock_parts = []
    
    # Tools needing calibration (if available)
    tools_needing_calibration = []
    try:
        tools_needing_calibration = ToolDefinition.query.filter(
            ToolDefinition.next_calibration_date.isnot(None)
        ).limit(5).all()
    except:
        pass
    
    return render_template('supply/index.html',
                         total_parts=total_parts,
                         total_tools=total_tools,
                         total_part_demands=total_part_demands,
                         recent_parts=recent_parts,
                         recent_tools=recent_tools,
                         parts_by_category=dict(parts_by_category),
                         tools_by_status=dict(tools_by_type),  # Using tools_by_type since ToolDefinition doesn't have status
                         low_stock_parts=low_stock_parts,
                         out_of_stock_parts=out_of_stock_parts,
                         tools_needing_calibration=tools_needing_calibration)

# Note: Parts and tools blueprints are registered separately in routes/__init__.py
# to avoid nested endpoint names (core_supply.core_supply_parts.*)
# They are registered directly to the app with /core/supply/parts and /core/supply/tools prefixes

