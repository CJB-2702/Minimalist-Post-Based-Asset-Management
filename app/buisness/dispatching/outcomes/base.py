"""
Base outcome handler protocol and factory

Defines the interface for outcome-type-specific behavior.
"""

from typing import Protocol, Dict, Any, TYPE_CHECKING
from app.buisness.dispatching.errors import DispatchDomainError

if TYPE_CHECKING:
    from app.buisness.dispatching.context import DispatchContext


class OutcomeHandler(Protocol):
    """
    Protocol for outcome-type-specific handlers.
    
    Each outcome type (dispatch, contract, reimbursement, reject) implements
    this protocol to provide type-specific validation, creation, and comment logic.
    """
    
    outcome_type: str
    
    def validate_assignment(self, ctx: 'DispatchContext', payload: Dict[str, Any]) -> None:
        """
        Validate that an outcome can be assigned with the given payload.
        
        Args:
            ctx: DispatchContext for the request
            payload: Data for creating the outcome
            
        Raises:
            DispatchDomainError: If validation fails
        """
        ...
    
    def create(self, ctx: 'DispatchContext', actor_id: int, payload: Dict[str, Any]):
        """
        Create the outcome instance.
        
        Args:
            ctx: DispatchContext for the request
            actor_id: User creating the outcome
            payload: Data for creating the outcome
            
        Returns:
            The created outcome object
        """
        ...
    
    def cancel(self, ctx: 'DispatchContext', actor_id: int, reason: str) -> None:
        """
        Cancel the outcome.
        
        Args:
            ctx: DispatchContext for the request
            actor_id: User cancelling the outcome
            reason: Reason for cancellation
        """
        ...
    
    def describe_assigned(self, outcome) -> str:
        """
        Generate description text for outcome assignment comment.
        
        Args:
            outcome: The outcome object
            
        Returns:
            str: Description text
        """
        ...
    
    def describe_cancelled(self, outcome, reason: str) -> str:
        """
        Generate description text for outcome cancellation comment.
        
        Args:
            outcome: The outcome object
            reason: Cancellation reason
            
        Returns:
            str: Description text
        """
        ...


class OutcomeHandlerFactory:
    """
    Factory for creating outcome handlers.
    
    Maps outcome type strings to handler instances.
    """
    
    _handlers: Dict[str, OutcomeHandler] = {}
    
    @classmethod
    def register(cls, outcome_type: str, handler: OutcomeHandler) -> None:
        """Register a handler for an outcome type"""
        cls._handlers[outcome_type] = handler
    
    @classmethod
    def get_handler(cls, outcome_type: str) -> OutcomeHandler:
        """
        Get handler for an outcome type.
        
        Args:
            outcome_type: The outcome type ('dispatch', 'contract', 'reimbursement', 'reject')
            
        Returns:
            OutcomeHandler: The handler instance
            
        Raises:
            DispatchDomainError: If outcome type is unknown
        """
        handler = cls._handlers.get(outcome_type)
        if not handler:
            raise DispatchDomainError(f"Unknown outcome type: {outcome_type}")
        return handler
    
    @classmethod
    def get_all_types(cls) -> list:
        """Get list of all registered outcome types"""
        return list(cls._handlers.keys())
