"""
All Details Route
Displays all detail records (asset and model) for a specific asset.

This route belongs to the assets module since it deals with detail tables,
which are part of the assets feature module, not core.
"""

from flask import Blueprint, render_template
from flask_login import login_required
from app.buisness.assets.asset_details_context import AssetDetailsContext
from app.services.assets.asset_detail_service import AssetDetailService
from app.logger import get_logger

logger = get_logger("asset_management.routes.assets.all_details")
bp = Blueprint('all_details', __name__)


@bp.route('/all-details/<int:asset_id>')
@login_required
def all_details(asset_id):
    """View all detail records for an asset"""
    logger.debug(f"User accessing all details for asset ID: {asset_id}")
    
    asset_context = AssetDetailsContext(asset_id)
    
    # Get details grouped by type using service (presentation-specific)
    asset_details = AssetDetailService.get_asset_details_by_type(asset_id)
    model_details = AssetDetailService.get_model_details_by_type(asset_id)
    
    # Get configurations using service (presentation-specific)
    asset_type_configs = AssetDetailService.get_asset_type_configs(asset_context.asset_type_id) if asset_context.asset_type_id else []
    model_type_configs = AssetDetailService.get_model_type_configs(asset_context.asset.make_model_id) if asset_context.asset.make_model_id else []
    
    logger.info(f"All details accessed for asset: {asset_context.asset.name} (ID: {asset_id})")
    
    return render_template('assets/all_details.html',
                         asset=asset_context.asset,
                         asset_details=asset_details,
                         model_details=model_details,
                         asset_type_configs=asset_type_configs,
                         model_type_configs=model_type_configs)

