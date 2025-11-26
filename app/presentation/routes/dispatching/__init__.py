from flask import Blueprint

dispatching_bp = Blueprint('dispatching', __name__)

from . import views, api  # noqa: E402,F401




