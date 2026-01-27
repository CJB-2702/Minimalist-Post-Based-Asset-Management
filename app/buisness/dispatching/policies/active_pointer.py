"""
Active Outcome Pointer Policy

Validates active outcome pointer consistency invariants.
"""

from typing import TYPE_CHECKING
from app.buisness.dispatching.errors import ActiveOutcomePointerError

if TYPE_CHECKING:
    from app.data.dispatching.request import DispatchRequest


class ActiveOutcomePointerPolicy:
    """
    Enforces active outcome pointer invariants.
    
    Invariants:
    1. If active_outcome_type is not null, active_outcome_row_id must be not null (and vice versa)
    2. The referenced outcome row must exist
    3. The referenced outcome row must have cancelled=False
    """
    
    @classmethod
    def check(cls, request: 'DispatchRequest') -> None:
        """
        Validate active outcome pointer consistency.
        
        Args:
            request: The dispatch request to validate
            
        Raises:
            ActiveOutcomePointerError: If pointer invariants are violated
        """
        # Check pointer consistency (both null or both not null)
        if (request.active_outcome_type is None) != (request.active_outcome_row_id is None):
            raise ActiveOutcomePointerError(
                f"Active outcome pointer inconsistency: "
                f"active_outcome_type={request.active_outcome_type}, "
                f"active_outcome_row_id={request.active_outcome_row_id}. "
                f"Both must be null or both must be not null."
            )
        
        # If no active outcome, validation passes
        if request.active_outcome_type is None:
            return
        
        # Validate that referenced outcome exists and is not cancelled
        cls._validate_outcome_exists_and_active(request)
    
    @classmethod
    def _validate_outcome_exists_and_active(cls, request: 'DispatchRequest') -> None:
        """
        Validate that the active outcome row exists and is not cancelled.
        
        Args:
            request: The dispatch request
            
        Raises:
            ActiveOutcomePointerError: If outcome doesn't exist or is cancelled
        """
        from app.data.dispatching.outcomes.standard_dispatch import StandardDispatch
        from app.data.dispatching.outcomes.contract import Contract
        from app.data.dispatching.outcomes.reimbursement import Reimbursement
        from app.data.dispatching.outcomes.reject import Reject
        
        outcome_type = request.active_outcome_type
        outcome_id = request.active_outcome_row_id
        
        # Map outcome type to model class
        outcome_models = {
            'dispatch': StandardDispatch,
            'contract': Contract,
            'reimbursement': Reimbursement,
            'reject': Reject,
        }
        
        if outcome_type not in outcome_models:
            raise ActiveOutcomePointerError(
                f"Invalid active_outcome_type: {outcome_type}. "
                f"Must be one of: {', '.join(outcome_models.keys())}"
            )
        
        # Query the outcome
        model_class = outcome_models[outcome_type]
        outcome = model_class.query.get(outcome_id)
        
        if not outcome:
            raise ActiveOutcomePointerError(
                f"Active outcome pointer references non-existent {outcome_type} with ID {outcome_id}"
            )
        
        if outcome.cancelled:
            raise ActiveOutcomePointerError(
                f"Active outcome pointer references cancelled {outcome_type} with ID {outcome_id}"
            )
    
    @classmethod
    def validate_pointer_set(cls, outcome_type: str, outcome_id: int) -> None:
        """
        Validate that a pointer can be set (both values must be provided).
        
        Args:
            outcome_type: The outcome type to set
            outcome_id: The outcome ID to set
            
        Raises:
            ActiveOutcomePointerError: If pointer values are inconsistent
        """
        if (outcome_type is None) != (outcome_id is None):
            raise ActiveOutcomePointerError(
                f"Cannot set active outcome pointer with inconsistent values: "
                f"outcome_type={outcome_type}, outcome_id={outcome_id}. "
                f"Both must be provided or both must be null."
            )
