"""
OutcomeManager - Domain service for outcome assignment and resolution

Manages outcome lifecycle operations (assign/cancel/change/resolution-status).
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime
from app import db
from app.buisness.dispatching.state_machine import (
    StandardDispatchStateMachine,
    ContractStateMachine,
    ReimbursementStateMachine,
    RejectStateMachine,
)
from app.buisness.dispatching.policies.outcome_uniqueness import OutcomeUniquenessPolicy
from app.buisness.dispatching.policies.active_pointer import ActiveOutcomePointerPolicy
from app.buisness.dispatching.narrator import DispatchNarrator
from app.buisness.dispatching.outcomes import OutcomeHandlerFactory
from app.buisness.core.event_context import EventContext
from app.buisness.dispatching.errors import DispatchPolicyViolation, DispatchTransitionError

if TYPE_CHECKING:
    from app.buisness.dispatching.context import DispatchContext


class OutcomeManager:
    """
    Domain service for outcome lifecycle operations.
    
    Responsibilities:
    - Assign/cancel/change active outcomes
    - Maintain active outcome pointer invariants
    - Apply outcome-specific state machine transitions (resolution_status)
    - Delegate type-specific behavior to OutcomeHandler strategies
    - Emit machine-generated timeline comments via DispatchNarrator
    """
    
    # Map outcome types to state machines
    STATE_MACHINES = {
        'dispatch': StandardDispatchStateMachine,
        'contract': ContractStateMachine,
        'reimbursement': ReimbursementStateMachine,
        'reject': RejectStateMachine,
    }
    
    def __init__(self, ctx: 'DispatchContext'):
        """
        Initialize OutcomeManager with a DispatchContext.
        
        Args:
            ctx: The DispatchContext to manage
        """
        self.ctx = ctx
        self.request = ctx.request
        self.event = ctx.event
    
    def assign_outcome(
        self,
        actor_id: int,
        outcome_type: str,
        payload: Dict[str, Any]
    ) -> None:
        """
        Assign an outcome to the request.
        
        Args:
            actor_id: User assigning the outcome
            outcome_type: Type of outcome ('dispatch', 'contract', 'reimbursement', 'reject')
            payload: Data for creating the outcome
            
        Raises:
            DispatchPolicyViolation: If assignment violates business rules
        """
        # Validate no active outcome exists
        OutcomeUniquenessPolicy.check_before_create(self.request, outcome_type)
        
        # Get handler for outcome type
        handler = OutcomeHandlerFactory.get_handler(outcome_type)
        
        # Validate assignment
        handler.validate_assignment(self.ctx, payload)
        
        # Create outcome
        outcome = handler.create(self.ctx, actor_id, payload)
        
        # Set active outcome pointer
        self.request.active_outcome_type = outcome_type
        self.request.active_outcome_row_id = outcome.id
        self.request.resolution_type = outcome_type  # Legacy field
        self.request.updated_by_id = actor_id
        
        # Validate pointer consistency
        ActiveOutcomePointerPolicy.check(self.request)
        
        # Update request workflow status based on outcome type and status
        from app.buisness.dispatching.request_manager import RequestManager
        request_mgr = RequestManager(self.ctx)
        
        if outcome_type == 'reject':
            # Reject can immediately resolve the request
            request_mgr.set_workflow_status(actor_id, 'Resolved', skip_comment=True)
        elif outcome_type == 'dispatch':
            # For dispatch outcomes, check the dispatch status
            dispatch_status = getattr(outcome, 'status', 'Planned')
            if dispatch_status == 'Complete':
                request_mgr.set_workflow_status(actor_id, 'Resolved', skip_comment=True)
            else:
                request_mgr.set_workflow_status(actor_id, 'Planned', skip_comment=True)
        else:
            # For other outcomes (contract, reimbursement), set to Planned
            request_mgr.set_workflow_status(actor_id, 'Planned', skip_comment=True)
        
        # Add outcome assignment comment
        if self.event:
            extra_details = handler.describe_assigned(outcome)
            comment = DispatchNarrator.outcome_assigned(outcome_type, outcome.id, extra_details)
            event_ctx = EventContext(self.event)
            event_ctx.add_comment(actor_id, comment, is_human_made=False)
        
        # Flush to database
        db.session.flush()
        
        # Rebuild context to reflect changes
        self.ctx._build()
    
    def cancel_active_outcome(self, actor_id: int, reason: str) -> None:
        """
        Cancel the active outcome.
        
        Args:
            actor_id: User cancelling the outcome
            reason: Reason for cancellation
            
        Raises:
            DispatchPolicyViolation: If no active outcome exists
        """
        if not self.request.active_outcome_type:
            raise DispatchPolicyViolation("No active outcome to cancel")
        
        outcome_type = self.request.active_outcome_type
        outcome_id = self.request.active_outcome_row_id
        
        # Get handler and cancel outcome
        handler = OutcomeHandlerFactory.get_handler(outcome_type)
        handler.cancel(self.ctx, actor_id, reason)
        
        # Clear active outcome pointer
        self.request.active_outcome_type = None
        self.request.active_outcome_row_id = None
        self.request.resolution_type = None  # Legacy field
        self.request.updated_by_id = actor_id
        
        # Update request workflow status back to UnderReview
        from app.buisness.dispatching.request_manager import RequestManager
        request_mgr = RequestManager(self.ctx)
        request_mgr.set_workflow_status(actor_id, 'UnderReview', skip_comment=True)
        
        # Add outcome cancellation comment
        if self.event:
            comment = DispatchNarrator.outcome_cancelled(outcome_type, outcome_id, reason)
            event_ctx = EventContext(self.event)
            event_ctx.add_comment(actor_id, comment, is_human_made=False)
        
        # Flush to database
        db.session.flush()
        
        # Rebuild context to reflect changes
        self.ctx._build()
    
    def change_outcome(
        self,
        actor_id: int,
        new_outcome_type: str,
        payload: Dict[str, Any],
        reason: str
    ) -> None:
        """
        Change outcome type (composed operation: cancel + assign).
        
        Args:
            actor_id: User changing the outcome
            new_outcome_type: New outcome type
            payload: Data for creating the new outcome
            reason: Reason for the change
        """
        # Store old outcome info for comment
        old_type = self.request.active_outcome_type
        old_id = self.request.active_outcome_row_id
        
        if not old_type:
            raise DispatchPolicyViolation("No active outcome to change")
        
        # Cancel current outcome
        self.cancel_active_outcome(actor_id, reason)
        
        # Assign new outcome
        self.assign_outcome(actor_id, new_outcome_type, payload)
        
        # Add outcome change comment (replaces individual cancel/assign comments)
        if self.event:
            new_id = self.request.active_outcome_row_id
            comment = DispatchNarrator.outcome_changed(old_type, old_id, new_outcome_type, new_id, reason)
            event_ctx = EventContext(self.event)
            event_ctx.add_comment(actor_id, comment, is_human_made=False)
    
    def set_resolution_status(
        self,
        actor_id: int,
        new_status: str,
        reason: Optional[str] = None
    ) -> None:
        """
        Update the active outcome's resolution_status.
        
        Args:
            actor_id: User making the change
            new_status: Target resolution_status
            reason: Optional reason for the change
            
        Raises:
            DispatchPolicyViolation: If no active outcome exists
            DispatchTransitionError: If transition is invalid
        """
        if not self.request.active_outcome_type:
            raise DispatchPolicyViolation("No active outcome to update")
        
        outcome_type = self.request.active_outcome_type
        outcome = self.ctx.active_outcome
        
        if not outcome:
            raise DispatchPolicyViolation(f"Active outcome {outcome_type} not found in context")
        
        old_status = outcome.resolution_status
        
        # Get state machine for outcome type
        state_machine = self.STATE_MACHINES.get(outcome_type)
        if not state_machine:
            raise DispatchPolicyViolation(f"Unknown outcome type: {outcome_type}")
        
        # Validate transition
        state_machine.validate_transition(old_status, new_status, outcome)
        
        # Apply transition
        outcome.resolution_status = new_status
        outcome.updated_by_id = actor_id
        
        # Sync legacy status field if it exists
        if hasattr(outcome, 'status'):
            outcome.status = new_status
        
        # If outcome reaches Complete, resolve the request
        if new_status == 'Complete':
            from app.buisness.dispatching.request_manager import RequestManager
            request_mgr = RequestManager(self.ctx)
            request_mgr.resolve(actor_id)
        
        # Add resolution status change comment
        if self.event:
            comment = DispatchNarrator.resolution_status_changed(
                outcome_type,
                old_status,
                new_status,
                reason
            )
            event_ctx = EventContext(self.event)
            event_ctx.add_comment(actor_id, comment, is_human_made=False)
        
        # Flush to database
        db.session.flush()
        
        # Rebuild context to reflect changes
        self.ctx._build()
    
    def validate_outcome_uniqueness(self) -> None:
        """
        Validate that only one non-cancelled outcome exists.
        
        Raises:
            OutcomeUniquenessError: If multiple active outcomes exist
        """
        OutcomeUniquenessPolicy.check(self.request)
    
    def validate_active_pointer(self) -> None:
        """
        Validate active outcome pointer consistency.
        
        Raises:
            ActiveOutcomePointerError: If pointer invariants are violated
        """
        ActiveOutcomePointerPolicy.check(self.request)
