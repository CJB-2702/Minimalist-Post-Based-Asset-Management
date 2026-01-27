"""
Manager Portal Routes
Routes for maintenance managers to plan, schedule, and manage maintenance work
"""

from app.presentation.routes.maintenance.user_views.manager.main import manager_bp
# Import create_assign routes to register them with manager_bp
from app.presentation.routes.maintenance.user_views.manager import create_assign
# Import part_demands routes to register them with manager_bp
from app.presentation.routes.maintenance.user_views.manager import part_demands

__all__ = ['manager_bp']

