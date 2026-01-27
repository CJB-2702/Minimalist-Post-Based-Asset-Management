"""
State machines for request and outcome lifecycles

Encodes valid transitions and provides guard hooks.
Keeps "what is allowed" separate from "how persistence occurs".
"""

from typing import Optional, Set, Dict, TYPE_CHECKING
from app.buisness.dispatching.errors import DispatchTransitionError

if TYPE_CHECKING:
    from app.buisness.dispatching.context import DispatchContext


class RequestStateMachine:
    """
    State machine for DispatchRequest workflow_status transitions.
    
    Request workflow is reversible - status can move back and forth
    based on dispatcher actions (except terminal states).
    
    Note: Requests start as Requested (initial state).
    """
    
    # Valid workflow statuses
    REQUESTED = 'Requested'  # Initial state when request is first created
    SUBMITTED = 'Submitted'
    UNDER_REVIEW = 'UnderReview'
    FIXES_REQUESTED = 'FixesRequested'
    PLANNED = 'Planned'
    RESOLVED = 'Resolved'
    CANCELLED = 'Cancelled'
    
    # Terminal states (cannot transition from these)
    TERMINAL_STATES = {RESOLVED, CANCELLED}
    
    # Valid transitions: from_status -> set of allowed to_status values
    TRANSITIONS: Dict[str, Set[str]] = {
        REQUESTED: {SUBMITTED, UNDER_REVIEW, PLANNED, FIXES_REQUESTED, RESOLVED, CANCELLED},  # Can transition to any state including resolved
        SUBMITTED: {UNDER_REVIEW, PLANNED, CANCELLED},  # Can go directly to Planned when outcome assigned
        UNDER_REVIEW: {FIXES_REQUESTED, PLANNED, CANCELLED},
        FIXES_REQUESTED: {UNDER_REVIEW, CANCELLED},
        PLANNED: {UNDER_REVIEW, RESOLVED, CANCELLED},  # Can go back to review if outcome cancelled
        # RESOLVED and CANCELLED are terminal - no transitions out
    }
    
    @classmethod
    def can_transition(cls, from_status: str, to_status: str, ctx: Optional['DispatchContext'] = None) -> bool:
        """
        Check if transition is valid.
        
        Args:
            from_status: Current status
            to_status: Target status
            ctx: Optional DispatchContext for additional validation
            
        Returns:
            bool: True if transition is allowed
        """
        # Allow staying in same state (no-op)
        if from_status == to_status:
            return True
        
        # Check if from_status is terminal
        if from_status in cls.TERMINAL_STATES:
            return False
        
        # Check if transition exists in transition table
        allowed_transitions = cls.TRANSITIONS.get(from_status, set())
        return to_status in allowed_transitions
    
    @classmethod
    def validate_transition(cls, from_status: str, to_status: str, ctx: Optional['DispatchContext'] = None) -> None:
        """
        Validate transition and raise exception if invalid.
        
        Args:
            from_status: Current status
            to_status: Target status
            ctx: Optional DispatchContext for additional validation
            
        Raises:
            DispatchTransitionError: If transition is not allowed
        """
        if not cls.can_transition(from_status, to_status, ctx):
            raise DispatchTransitionError(
                f"Invalid workflow status transition: {from_status} → {to_status}"
            )
    
    @classmethod
    def get_allowed_transitions(cls, from_status: str) -> Set[str]:
        """Get set of allowed target statuses from current status"""
        if from_status in cls.TERMINAL_STATES:
            return set()
        return cls.TRANSITIONS.get(from_status, set())


class OutcomeStateMachine:
    """
    Base state machine for outcome resolution_status transitions.
    
    Outcome status generally moves in one direction (not reversible like request status).
    """
    
    # Common statuses across all outcomes
    PLANNED = 'Planned'
    COMPLETE = 'Complete'
    CANCELLED = 'Cancelled'
    
    # Terminal states
    TERMINAL_STATES = {COMPLETE, CANCELLED}
    
    # Base transitions (can be overridden by subclasses)
    TRANSITIONS: Dict[str, Set[str]] = {
        PLANNED: {COMPLETE, CANCELLED},
        # COMPLETE and CANCELLED are terminal
    }
    
    @classmethod
    def can_transition(cls, from_status: str, to_status: str, outcome=None) -> bool:
        """
        Check if transition is valid.
        
        Args:
            from_status: Current status
            to_status: Target status
            outcome: Optional outcome object for additional validation
            
        Returns:
            bool: True if transition is allowed
        """
        # Allow staying in same state (no-op)
        if from_status == to_status:
            return True
        
        # Check if from_status is terminal
        if from_status in cls.TERMINAL_STATES:
            return False
        
        # Check if transition exists in transition table
        allowed_transitions = cls.TRANSITIONS.get(from_status, set())
        return to_status in allowed_transitions
    
    @classmethod
    def validate_transition(cls, from_status: str, to_status: str, outcome=None) -> None:
        """
        Validate transition and raise exception if invalid.
        
        Args:
            from_status: Current status
            to_status: Target status
            outcome: Optional outcome object for additional validation
            
        Raises:
            DispatchTransitionError: If transition is not allowed
        """
        if not cls.can_transition(from_status, to_status, outcome):
            raise DispatchTransitionError(
                f"Invalid resolution status transition: {from_status} → {to_status}"
            )
    
    @classmethod
    def get_allowed_transitions(cls, from_status: str) -> Set[str]:
        """Get set of allowed target statuses from current status"""
        if from_status in cls.TERMINAL_STATES:
            return set()
        return cls.TRANSITIONS.get(from_status, set())


class StandardDispatchStateMachine(OutcomeStateMachine):
    """
    State machine for StandardDispatch resolution_status.
    
    StandardDispatch has a richer lifecycle: Planned → In Progress → Complete
    """
    
    IN_PROGRESS = 'In Progress'
    
    # Override transitions for StandardDispatch
    TRANSITIONS: Dict[str, Set[str]] = {
        OutcomeStateMachine.PLANNED: {IN_PROGRESS, OutcomeStateMachine.COMPLETE, OutcomeStateMachine.CANCELLED},
        IN_PROGRESS: {OutcomeStateMachine.COMPLETE, OutcomeStateMachine.CANCELLED},
        # COMPLETE and CANCELLED are terminal
    }


class ContractStateMachine(OutcomeStateMachine):
    """
    State machine for Contract resolution_status.
    
    Simple lifecycle: Planned → Complete
    """
    # Uses base OutcomeStateMachine transitions


class ReimbursementStateMachine(OutcomeStateMachine):
    """
    State machine for Reimbursement resolution_status.
    
    Simple lifecycle: Planned → Complete
    """
    # Uses base OutcomeStateMachine transitions


class RejectStateMachine(OutcomeStateMachine):
    """
    State machine for Reject resolution_status.
    
    Reject is immediately complete when created.
    """
    
    # Override transitions - reject starts as Complete
    TRANSITIONS: Dict[str, Set[str]] = {
        OutcomeStateMachine.COMPLETE: {OutcomeStateMachine.CANCELLED},
        # CANCELLED is terminal
    }
