"""
Outcome Uniqueness Policy

Ensures only one non-cancelled outcome exists as active for a request.
"""

from typing import TYPE_CHECKING
from app.buisness.dispatching.errors import OutcomeUniquenessError

if TYPE_CHECKING:
    from app.data.dispatching.request import DispatchRequest


class OutcomeUniquenessPolicy:
    """
    Enforces outcome uniqueness constraint.
    
    At most one non-cancelled outcome should exist across all outcome types
    for a given request at any point in time.
    """
    
    @classmethod
    def check(cls, request: 'DispatchRequest') -> None:
        """
        Validate that only one non-cancelled outcome exists.
        
        Args:
            request: The dispatch request to validate
            
        Raises:
            OutcomeUniquenessError: If multiple non-cancelled outcomes exist
        """
        from app.data.dispatching.outcomes.standard_dispatch import StandardDispatch
        from app.data.dispatching.outcomes.contract import Contract
        from app.data.dispatching.outcomes.reimbursement import Reimbursement
        from app.data.dispatching.outcomes.reject import Reject
        
        # Count non-cancelled outcomes across all types
        active_outcomes = []
        
        dispatch = StandardDispatch.query.filter_by(
            request_id=request.id,
            cancelled=False
        ).first()
        if dispatch:
            active_outcomes.append(('dispatch', dispatch.id))
        
        contract = Contract.query.filter_by(
            request_id=request.id,
            cancelled=False
        ).first()
        if contract:
            active_outcomes.append(('contract', contract.id))
        
        reimbursement = Reimbursement.query.filter_by(
            request_id=request.id,
            cancelled=False
        ).first()
        if reimbursement:
            active_outcomes.append(('reimbursement', reimbursement.id))
        
        reject = Reject.query.filter_by(
            request_id=request.id,
            cancelled=False
        ).first()
        if reject:
            active_outcomes.append(('reject', reject.id))
        
        # Check uniqueness
        if len(active_outcomes) > 1:
            outcome_list = ', '.join([f"{t} (ID: {i})" for t, i in active_outcomes])
            raise OutcomeUniquenessError(
                f"Multiple non-cancelled outcomes exist for request {request.id}: {outcome_list}. "
                f"Only one active outcome is allowed at a time."
            )
    
    @classmethod
    def check_before_create(cls, request: 'DispatchRequest', outcome_type: str) -> None:
        """
        Validate that no active outcome exists before creating a new one.
        
        Args:
            request: The dispatch request
            outcome_type: The type of outcome being created
            
        Raises:
            OutcomeUniquenessError: If an active outcome already exists
        """
        from app.data.dispatching.outcomes.standard_dispatch import StandardDispatch
        from app.data.dispatching.outcomes.contract import Contract
        from app.data.dispatching.outcomes.reimbursement import Reimbursement
        from app.data.dispatching.outcomes.reject import Reject
        
        # Check if any non-cancelled outcome exists
        outcome_models = {
            'dispatch': StandardDispatch,
            'contract': Contract,
            'reimbursement': Reimbursement,
            'reject': Reject,
        }
        
        for existing_type, model_class in outcome_models.items():
            existing = model_class.query.filter_by(
                request_id=request.id,
                cancelled=False
            ).first()
            
            if existing:
                raise OutcomeUniquenessError(
                    f"Cannot create {outcome_type} outcome: "
                    f"request {request.id} already has active {existing_type} outcome (ID: {existing.id}). "
                    f"Cancel the existing outcome first."
                )
