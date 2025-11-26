"""
Technician Portal Main Routes
Dashboard and main navigation for maintenance technicians
"""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.logger import get_logger

logger = get_logger("asset_management.routes.maintenance.technician")

# Create technician portal blueprint
technician_bp = Blueprint('technician_portal', __name__, url_prefix='/maintenance/technician')


@technician_bp.route('/')
@technician_bp.route('/dashboard')
@login_required
def dashboard():
    """Technician dashboard with assigned work"""
    logger.info(f"Technician dashboard accessed by {current_user.username}")
    
    # Get basic stats
    stats = {
        'assigned_work': 0,
        'in_progress': 0,
        'completed_today': 0,
    }
    
    try:
        from app.data.maintenance.base.actions import Action
        from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
        
        # Get work assigned to current user
        stats['assigned_work'] = Action.query.filter_by(
            assigned_user_id=current_user.id
        ).filter(Action.status.in_(['Not Started', 'In Progress'])).count()
        
        stats['in_progress'] = Action.query.filter_by(
            assigned_user_id=current_user.id,
            status='In Progress'
        ).count()
    except ImportError as e:
        logger.warning(f"Could not load technician stats: {e}")
    
    return render_template('maintenance/technician/dashboard.html', stats=stats)

