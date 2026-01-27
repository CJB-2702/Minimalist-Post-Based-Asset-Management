"""
RequestManager - Domain service for request workflow operations

Enforces request workflow rules and applies request state machine transitions.
"""

from typing import Optional, TYPE_CHECKING
from datetime import datetime
from app import db
from app.buisness.dispatching.state_machine import RequestStateMachine
from app.buisness.dispatching.policies.intent_lock import RequestIntentLockPolicy
from app.buisness.dispatching.narrator import DispatchNarrator
from app.buisness.core.event_context import EventContext
from app.buisness.dispatching.errors import DispatchTransitionError

if TYPE_CHECKING:
    from app.buisness.dispatching.context import DispatchContext


class RequestManager:
    """
    Domain service for request workflow operations.
    
    Responsibilities:
    - Transition request workflow_status via RequestStateMachine
    - Enforce request intent immutability rules
    - Emit machine-generated timeline comments via DispatchNarrator
    """
    
    def __init__(self, ctx: 'DispatchContext'):
        """
        Initialize RequestManager with a DispatchContext.
        
        Args:
            ctx: The DispatchContext to manage
        """
        self.ctx = ctx
        self.request = ctx.request
        self.event = ctx.event
    
    def set_workflow_status(
        self,
        actor_id: int,
        new_status: str,
        reason: Optional[str] = None,
        skip_comment: bool = False
    ) -> None:
        """
        Transition request workflow_status.
        
        Args:
            actor_id: User making the change
            new_status: Target workflow_status
            reason: Optional reason for the transition
            skip_comment: If True, don't add machine comment (for internal use)
            
        Raises:
            DispatchTransitionError: If transition is invalid
        """
        old_status = self.request.workflow_status
        
        # Validate transition
        RequestStateMachine.validate_transition(old_status, new_status, self.ctx)
        
        # Apply transition
        self.request.workflow_status = new_status
        self.request.updated_by_id = actor_id
        
        # Sync legacy status field
        self.request.status = new_status
        
        # Sync event status if event exists
        if self.event:
            self.event.status = new_status
        
        # Add machine comment
        if not skip_comment and self.event:
            comment = DispatchNarrator.workflow_status_changed(old_status, new_status, reason)
            event_ctx = EventContext(self.event)
            event_ctx.add_comment(actor_id, comment, is_human_made=False)
    
    def submit(self, actor_id: int) -> None:
        """
        Submit the request (legacy method - no-op since requests start as Submitted).
        
        Kept for backward compatibility.
        
        Args:
            actor_id: User submitting the request
        """
        # Requests now start as Submitted, so this is a no-op
        # Set submitted_at timestamp if not already set
        if not self.request.submitted_at:
            self.request.submitted_at = datetime.utcnow()
        
        # Ensure we're in Submitted state (should already be)
        if self.request.workflow_status != RequestStateMachine.SUBMITTED:
            self.set_workflow_status(actor_id, RequestStateMachine.SUBMITTED)
    
    def begin_review(self, actor_id: int) -> None:
        """
        Begin review (Submitted → UnderReview).
        
        Args:
            actor_id: User beginning review
        """
        self.set_workflow_status(
            actor_id,
            RequestStateMachine.UNDER_REVIEW,
            reason="Review started by dispatcher"
        )
    
    def request_fixes(self, actor_id: int, reason: str) -> None:
        """
        Request fixes from requester (UnderReview → FixesRequested).
        
        Args:
            actor_id: User requesting fixes
            reason: Details about what needs to be fixed
        """
        self.set_workflow_status(
            actor_id,
            RequestStateMachine.FIXES_REQUESTED,
            skip_comment=True
        )
        
        # Add specific fixes requested comment
        if self.event:
            comment = DispatchNarrator.fixes_requested(reason)
            event_ctx = EventContext(self.event)
            event_ctx.add_comment(actor_id, comment, is_human_made=False)
    
    def resume_review(self, actor_id: int) -> None:
        """
        Resume review after fixes (FixesRequested → UnderReview).
        
        Args:
            actor_id: User resuming review
        """
        self.set_workflow_status(
            actor_id,
            RequestStateMachine.UNDER_REVIEW,
            skip_comment=True
        )
        
        # Add specific review resumed comment
        if self.event:
            comment = DispatchNarrator.review_resumed()
            event_ctx = EventContext(self.event)
            event_ctx.add_comment(actor_id, comment, is_human_made=False)
    
    def plan(self, actor_id: int) -> None:
        """
        Mark request as planned (typically when outcome is assigned).
        
        Args:
            actor_id: User planning the request
        """
        self.set_workflow_status(
            actor_id,
            RequestStateMachine.PLANNED,
            reason="Outcome assigned"
        )
    
    def resolve(self, actor_id: int) -> None:
        """
        Mark request as resolved (typically when outcome is complete).
        
        Args:
            actor_id: User resolving the request
        """
        self.set_workflow_status(
            actor_id,
            RequestStateMachine.RESOLVED,
            reason="Outcome completed"
        )
    
    def cancel_request(self, actor_id: int, reason: str) -> None:
        """
        Cancel the request entirely.
        
        Args:
            actor_id: User cancelling the request
            reason: Reason for cancellation
        """
        self.set_workflow_status(
            actor_id,
            RequestStateMachine.CANCELLED,
            skip_comment=True
        )
        
        # Add specific cancellation comment
        if self.event:
            comment = DispatchNarrator.request_cancelled(reason)
            event_ctx = EventContext(self.event)
            event_ctx.add_comment(actor_id, comment, is_human_made=False)
    
    def validate_intent_update(self, updates: dict) -> None:
        """
        Validate that request intent fields can be updated.
        
        Args:
            updates: Dictionary of field names and new values
            
        Raises:
            RequestIntentLockError: If locked fields are being modified
        """
        RequestIntentLockPolicy.check(self.request, updates)
    
    def is_intent_locked(self) -> bool:
        """Check if request intent fields are locked"""
        return RequestIntentLockPolicy.is_locked(self.request)
