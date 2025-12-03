"""
Core routes package for core foundation models
Includes CRUD operations for User, MajorLocation, AssetType, MakeModel, Asset, Event
"""

from flask import Blueprint
from app.logger import get_logger

bp = Blueprint('core', __name__)
logger = get_logger("asset_management.routes.bp")

# Import all core route modules (events-related routes live in core.events.*)
from . import users, locations, asset_types, make_models, assets, dashboard, meter_history