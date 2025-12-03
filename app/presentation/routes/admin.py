"""
Admin routes
Secret admin panel with links to various admin tools
"""

from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from app.data.core.user_info.user import User
from app.logger import get_logger

bp = Blueprint('admin', __name__)
logger = get_logger("asset_management.routes.admin")


def admin_required(f):
    """Decorator to require admin access"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            logger.warning(f"Non-admin user {current_user.username if current_user.is_authenticated else 'anonymous'} attempted to access admin page")
            abort(403)
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


@bp.route('/')
@login_required
@admin_required
def index():
    """Admin dashboard index page"""
    logger.info(f"Admin user {current_user.username} accessing admin panel")
    
    # Get all users for portal data viewer links
    users = User.query.order_by(User.username).all()
    
    return render_template('admin/index.html', users=users)

