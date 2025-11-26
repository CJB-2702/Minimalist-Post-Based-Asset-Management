"""
Asset Details Card Route
HTMX endpoint for displaying asset details card with detail count.

This route belongs to the assets module since it uses AssetDetailsContext
and displays detail-related information.
"""

from flask import Blueprint, render_template
from flask_login import login_required
from app.buisness.assets.asset_details_context import AssetDetailsContext
from app.services.core.asset_service import AssetService
from app.logger import get_logger

logger = get_logger("asset_management.routes.assets.asset_details_card")
bp = Blueprint('asset_details_card', __name__)


@bp.route('/details-card')
@bp.route('/details-card/<int:asset_id>')
@login_required
def asset_details_card(asset_id=None):
    """HTMX endpoint for asset details card"""
    if asset_id is None:
        # Return empty state
        return render_template('core/assets/asset_details_card.html', asset=None)
    
    asset_context = AssetDetailsContext(asset_id)
    
    # Get recent events from service (presentation-specific query)
    events = AssetService.get_recent_events(asset_id, limit=5)
    
    logger.debug(f"Asset details card accessed for asset ID: {asset_id}")
    
    return render_template('core/assets/asset_details_card.html',
                         asset=asset_context.asset,
                         asset_type=asset_context.asset_type,
                         make_model=asset_context.make_model,
                         location=asset_context.major_location,
                         events=events,
                         detail_count=asset_context.detail_count)

