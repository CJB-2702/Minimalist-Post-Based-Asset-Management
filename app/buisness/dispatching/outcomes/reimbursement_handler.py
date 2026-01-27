"""
Reimbursement outcome handler

Strategy implementation for Reimbursement outcomes.
"""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime
from app import db
from app.data.dispatching.outcomes.reimbursement import Reimbursement
from app.buisness.dispatching.errors import DispatchPolicyViolation
from app.buisness.dispatching.narrator import DispatchNarrator

if TYPE_CHECKING:
    from app.buisness.dispatching.context import DispatchContext


class ReimbursementHandler:
    """Handler for Reimbursement outcomes"""
    
    outcome_type = 'reimbursement'
    
    def validate_assignment(self, ctx: 'DispatchContext', payload: Dict[str, Any]) -> None:
        """
        Validate Reimbursement assignment.
        
        Checks:
        - Required fields are present
        """
        required_fields = ['from_account', 'to_account', 'amount', 'reason']
        missing = [f for f in required_fields if f not in payload]
        if missing:
            raise DispatchPolicyViolation(
                f"Missing required fields for Reimbursement: {', '.join(missing)}"
            )
    
    def create(self, ctx: 'DispatchContext', actor_id: int, payload: Dict[str, Any]) -> Reimbursement:
        """Create Reimbursement outcome"""
        reimbursement = Reimbursement(
            request_id=ctx.request.id,
            request_event_id=ctx.request.event_id,
            outcome_type='reimbursement',
            created_by_id=actor_id,
            **payload
        )
        
        db.session.add(reimbursement)
        db.session.flush()
        
        return reimbursement
    
    def cancel(self, ctx: 'DispatchContext', actor_id: int, reason: str) -> None:
        """Cancel Reimbursement outcome"""
        if not ctx.reimbursement:
            raise DispatchPolicyViolation("No Reimbursement outcome to cancel")
        
        ctx.reimbursement.cancelled = True
        ctx.reimbursement.cancelled_at = datetime.utcnow()
        ctx.reimbursement.cancelled_by_id = actor_id
        ctx.reimbursement.cancelled_reason = reason
        ctx.reimbursement.updated_by_id = actor_id
        
        # Set resolution_status to Cancelled
        ctx.reimbursement.resolution_status = 'Cancelled'
    
    def describe_assigned(self, outcome: Reimbursement) -> str:
        """Generate description for assignment"""
        return DispatchNarrator.reimbursement_details(outcome)
    
    def describe_cancelled(self, outcome: Reimbursement, reason: str) -> str:
        """Generate description for cancellation"""
        return f"Reimbursement cancelled | {reason}"
