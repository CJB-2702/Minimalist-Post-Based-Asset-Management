"""
StandardDispatch outcome handler

Strategy implementation for StandardDispatch outcomes.
"""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime
from app import db
from app.data.dispatching.outcomes.standard_dispatch import StandardDispatch
from app.buisness.dispatching.errors import DispatchPolicyViolation
from app.buisness.dispatching.policies.double_booking import DoubleBookingSpecification
from app.buisness.dispatching.narrator import DispatchNarrator

if TYPE_CHECKING:
    from app.buisness.dispatching.context import DispatchContext


class StandardDispatchHandler:
    """Handler for StandardDispatch outcomes"""
    
    outcome_type = 'dispatch'
    
    def validate_assignment(self, ctx: 'DispatchContext', payload: Dict[str, Any]) -> None:
        """
        Validate StandardDispatch assignment.
        
        Checks:
        - Required fields are present
        - Double-booking conflicts
        """
        # Check required fields
        required_fields = ['scheduled_start', 'scheduled_end']
        missing = [f for f in required_fields if f not in payload]
        if missing:
            raise DispatchPolicyViolation(
                f"Missing required fields for StandardDispatch: {', '.join(missing)}"
            )
        
        # Validate double-booking if asset is specified
        asset_id = payload.get('asset_dispatched_id')
        if asset_id:
            scheduled_start = payload['scheduled_start']
            scheduled_end = payload['scheduled_end']
            
            # Convert string dates if needed
            if isinstance(scheduled_start, str):
                scheduled_start = datetime.fromisoformat(scheduled_start)
            if isinstance(scheduled_end, str):
                scheduled_end = datetime.fromisoformat(scheduled_end)
            
            DoubleBookingSpecification.check(
                asset_id=asset_id,
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_end
            )
    
    def create(self, ctx: 'DispatchContext', actor_id: int, payload: Dict[str, Any]) -> StandardDispatch:
        """
        Create StandardDispatch outcome.
        
        Special handling:
        - Copy requested_asset_id to asset_dispatched_id if not specified
        - Set outcome_type and request_event_id
        """
        # Copy requested_asset_id if not specified
        if 'asset_dispatched_id' not in payload and ctx.request.requested_asset_id:
            payload['asset_dispatched_id'] = ctx.request.requested_asset_id
        
        # Create the dispatch
        dispatch = StandardDispatch(
            request_id=ctx.request.id,
            request_event_id=ctx.request.event_id,
            outcome_type='dispatch',
            created_by_id=actor_id,
            **payload
        )
        
        db.session.add(dispatch)
        db.session.flush()
        
        # Update event asset_id if asset is dispatched
        if dispatch.asset_dispatched_id and ctx.event:
            ctx.event.asset_id = dispatch.asset_dispatched_id
        
        return dispatch
    
    def cancel(self, ctx: 'DispatchContext', actor_id: int, reason: str) -> None:
        """Cancel StandardDispatch outcome"""
        if not ctx.dispatch:
            raise DispatchPolicyViolation("No StandardDispatch outcome to cancel")
        
        ctx.dispatch.cancelled = True
        ctx.dispatch.cancelled_at = datetime.utcnow()
        ctx.dispatch.cancelled_by_id = actor_id
        ctx.dispatch.cancelled_reason = reason
        ctx.dispatch.updated_by_id = actor_id
        
        # Set status to Cancelled
        ctx.dispatch.status = 'Cancelled'
        ctx.dispatch.resolution_status = 'Cancelled'
    
    def describe_assigned(self, outcome: StandardDispatch) -> str:
        """Generate description for assignment"""
        return DispatchNarrator.dispatch_details(outcome)
    
    def describe_cancelled(self, outcome: StandardDispatch, reason: str) -> str:
        """Generate description for cancellation"""
        return f"StandardDispatch cancelled | {reason}"
