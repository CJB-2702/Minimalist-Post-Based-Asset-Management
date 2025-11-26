"""
Core dashboard route
Provides central navigation to all core module areas
"""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.logger import get_logger

logger = get_logger("asset_management.routes.core.dashboard")
bp = Blueprint('core_dashboard', __name__)

@bp.route('')
@bp.route('/dashboard')
@login_required
def dashboard():
    """
    Core module dashboard
    Provides navigation to all core areas: asset_info, event_info, supply, user_info
    """
    logger.debug(f"User {current_user.username} accessing core dashboard")
    
    return render_template('core/dashboard.html')

