"""Public routes blueprint for non-authenticated pages."""

from flask import Blueprint

public_bp = Blueprint('public', __name__, url_prefix='/public')

from . import views



