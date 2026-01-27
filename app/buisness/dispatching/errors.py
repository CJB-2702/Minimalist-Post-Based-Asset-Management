"""
Domain exceptions for dispatching business logic

These exceptions represent business rule violations and domain-specific errors.
They should be raised by the business layer when invariants are violated.
"""


class DispatchDomainError(Exception):
    """Base exception for all dispatching domain errors"""
    pass


class DispatchTransitionError(DispatchDomainError):
    """Raised when a state transition is invalid or not allowed"""
    pass


class DispatchPolicyViolation(DispatchDomainError):
    """Raised when a business policy/rule is violated"""
    pass


class DispatchConsistencyError(DispatchDomainError):
    """Raised when data consistency invariants are violated"""
    pass


class DispatchConflictError(DispatchDomainError):
    """Raised when resource conflicts occur (e.g., double booking)"""
    pass


class RequestIntentLockError(DispatchPolicyViolation):
    """Raised when attempting to modify locked request intent fields"""
    pass


class ActiveOutcomePointerError(DispatchConsistencyError):
    """Raised when active outcome pointer invariants are violated"""
    pass


class OutcomeUniquenessError(DispatchPolicyViolation):
    """Raised when multiple non-cancelled outcomes exist for a request"""
    pass


class DoubleBookingError(DispatchConflictError):
    """Raised when an asset is double-booked for overlapping time periods"""
    pass


class AssetDispatchabilityError(DispatchPolicyViolation):
    """Raised when an asset cannot be dispatched due to work order conflicts"""
    pass
