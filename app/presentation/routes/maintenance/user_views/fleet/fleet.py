"""
Fleet/Admin Portal Main Routes
Dashboard and main navigation for fleet-wide maintenance oversight
"""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.logger import get_logger

logger = get_logger("asset_management.routes.maintenance.fleet")

# Create fleet portal blueprint
fleet_bp = Blueprint('fleet_portal', __name__, url_prefix='/maintenance/fleet')


@fleet_bp.route('/')
@fleet_bp.route('/dashboard')
@login_required
def dashboard():
    """Fleet dashboard with comprehensive maintenance overview"""
    logger.info(f"Fleet dashboard accessed by {current_user.username}")
    
    # Get basic stats
    stats = {
        'total_assets': 0,
        'assets_due': 0,
        'overdue_maintenance': 0,
        'active_maintenance': 0,
        'completion_rate': 0,
    }
    
    try:
        from app.data.core.asset_info.asset import Asset
        from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
        
        stats['total_assets'] = Asset.query.count()
        stats['active_maintenance'] = MaintenanceActionSet.query.filter(
            MaintenanceActionSet.status.in_(['Planned', 'In Progress', 'Delayed'])
        ).count()
    except ImportError as e:
        logger.warning(f"Could not load fleet stats: {e}")
    
    return render_template('maintenance/user_views/fleet/dashboard.html', stats=stats)

