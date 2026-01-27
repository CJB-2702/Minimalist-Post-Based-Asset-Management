"""
Dispatching business layer.

Main entry point: DispatchContext (domain facade)

New architecture (state + outcome transition model):
- DispatchContext: Domain facade / aggregate controller
- RequestManager: Request workflow operations
- OutcomeManager: Outcome lifecycle operations
- State machines: Request and outcome state transitions
- Policies: Business rule validation
- Outcome handlers: Type-specific behavior strategies
- DispatchNarrator: Comment generation

Legacy (deprecated):
- DispatchManager: Old factory-style manager (use DispatchContext instead)
"""

from app.buisness.dispatching.context import DispatchContext
from app.buisness.dispatching.request_manager import RequestManager
from app.buisness.dispatching.outcome_manager import OutcomeManager
from app.buisness.dispatching.errors import (
    DispatchDomainError,
    DispatchTransitionError,
    DispatchPolicyViolation,
    DispatchConsistencyError,
    DispatchConflictError,
)

# Legacy imports (deprecated)
from app.buisness.dispatching.dispatch_manager import DispatchManager

__all__ = [
    'DispatchContext',
    'RequestManager',
    'OutcomeManager',
    'DispatchDomainError',
    'DispatchTransitionError',
    'DispatchPolicyViolation',
    'DispatchConsistencyError',
    'DispatchConflictError',
    # Legacy (deprecated)
    'DispatchManager',
]

