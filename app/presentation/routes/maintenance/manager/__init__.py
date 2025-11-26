"""
Manager Portal Routes
Routes for maintenance managers to plan, schedule, and manage maintenance work
"""

from app.presentation.routes.maintenance.manager.main import manager_bp
from app.presentation.routes.maintenance.manager.template_builder import template_builder_bp

__all__ = ['manager_bp', 'template_builder_bp']

