"""
Reject outcome handler

Strategy implementation for Reject outcomes.
"""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime
from app import db
from app.data.dispatching.outcomes.reject import Reject
from app.buisness.dispatching.errors import DispatchPolicyViolation
from app.buisness.dispatching.narrator import DispatchNarrator

if TYPE_CHECKING:
    from app.buisness.dispatching.context import DispatchContext


class RejectHandler:
    """Handler for Reject outcomes"""
    
    outcome_type = 'reject'
    
    def validate_assignment(self, ctx: 'DispatchContext', payload: Dict[str, Any]) -> None:
        """
        Validate Reject assignment.
        
        Checks:
        - Required fields are present
        """
        required_fields = ['reason']
        missing = [f for f in required_fields if f not in payload]
        if missing:
            raise DispatchPolicyViolation(
                f"Missing required fields for Reject: {', '.join(missing)}"
            )
    
    def create(self, ctx: 'DispatchContext', actor_id: int, payload: Dict[str, Any]) -> Reject:
        """
        Create Reject outcome.
        
        Note: Reject starts with resolution_status='Complete' (immediately terminal)
        """
        reject = Reject(
            request_id=ctx.request.id,
            request_event_id=ctx.request.event_id,
            outcome_type='reject',
            resolution_status='Complete',  # Reject is immediately complete
            created_by_id=actor_id,
            **payload
        )
        
        db.session.add(reject)
        db.session.flush()
        
        return reject
    
    def cancel(self, ctx: 'DispatchContext', actor_id: int, reason: str) -> None:
        """Cancel Reject outcome (allows reversing a rejection)"""
        if not ctx.reject:
            raise DispatchPolicyViolation("No Reject outcome to cancel")
        
        ctx.reject.cancelled = True
        ctx.reject.cancelled_at = datetime.utcnow()
        ctx.reject.cancelled_by_id = actor_id
        ctx.reject.cancelled_reason = reason
        ctx.reject.updated_by_id = actor_id
        
        # Set resolution_status to Cancelled
        ctx.reject.resolution_status = 'Cancelled'
    
    def describe_assigned(self, outcome: Reject) -> str:
        """Generate description for assignment"""
        return DispatchNarrator.reject_details(outcome)
    
    def describe_cancelled(self, outcome: Reject, reason: str) -> str:
        """Generate description for cancellation"""
        return f"Rejection reversed | {reason}"
