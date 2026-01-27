"""
Outcome handler strategies for different outcome types

Implements the Strategy pattern for outcome-type-specific behavior.
"""

from app.buisness.dispatching.outcomes.base import OutcomeHandler, OutcomeHandlerFactory
from app.buisness.dispatching.outcomes.standard_dispatch_handler import StandardDispatchHandler
from app.buisness.dispatching.outcomes.contract_handler import ContractHandler
from app.buisness.dispatching.outcomes.reimbursement_handler import ReimbursementHandler
from app.buisness.dispatching.outcomes.reject_handler import RejectHandler

__all__ = [
    'OutcomeHandler',
    'OutcomeHandlerFactory',
    'StandardDispatchHandler',
    'ContractHandler',
    'ReimbursementHandler',
    'RejectHandler',
]
