"""
Assets routes package for asset detail system
Includes routes for asset detail tables and model details
"""

from flask import Blueprint
from app.logger import get_logger

bp = Blueprint('assets', __name__)
logger = get_logger("asset_management.routes.bp")

# Import asset detail routes
from . import detail_tables, model_details, all_details, asset_details_card

# Register the blueprints
bp.register_blueprint(detail_tables.bp, url_prefix='/detail-tables')
bp.register_blueprint(model_details.bp, url_prefix='/model-details')
bp.register_blueprint(all_details.bp)
bp.register_blueprint(asset_details_card.bp) 