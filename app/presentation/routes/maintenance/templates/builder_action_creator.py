"""
Builder Action Creator Helper Routes
Helper routes for action creator portal that accept form data for template builders.
"""

from flask import Blueprint, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.logger import get_logger
from app.buisness.maintenance.builders.template_builder_context import TemplateBuilderContext
from app.services.maintenance.template_builder_service import TemplateBuilderService

logger = get_logger("asset_management.routes.maintenance.templates.builder_action_creator")

# This will be registered under the same blueprint as template_builder
# We'll import and use template_builder_bp from template_builder.py

# Note: These routes will be added to template_builder.py instead of a separate blueprint
# to keep all template builder routes together

