from flask import Blueprint

dispatching_bp = Blueprint('dispatching', __name__)

# Import all route modules
from . import (  # noqa: E402,F401
    navigation,
    requests,
    dispatches,
    contracts,
    reimbursements,
    rejects,
    outcomes,
    api,
    searchbars
)




