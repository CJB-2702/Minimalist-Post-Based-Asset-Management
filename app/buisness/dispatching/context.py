"""
DispatchContext - Domain Facade for dispatch request aggregate

Acts as the aggregate controller and provides an intention-revealing interface
for dispatch operations. Delegates mutation work to RequestManager and OutcomeManager.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from app import db
from app.data.core.event_info.event import Event
from app.data.dispatching.request import DispatchRequest
from app.data.dispatching.outcomes.standard_dispatch import StandardDispatch
from app.data.dispatching.outcomes.contract import Contract
from app.data.dispatching.outcomes.reimbursement import Reimbursement
from app.data.dispatching.outcomes.reject import Reject
from app.buisness.dispatching.request_manager import RequestManager
from app.buisness.dispatching.outcome_manager import OutcomeManager
from app.buisness.dispatching.narrator import DispatchNarrator
from app.buisness.dispatching.outcomes import (
    OutcomeHandlerFactory,
    StandardDispatchHandler,
    ContractHandler,
    ReimbursementHandler,
    RejectHandler,
)
from app.buisness.core.event_context import EventContext


class DispatchContext:
    """
    Domain Facade for dispatch request aggregate.
    
    Provides a thin façade that holds request, event, and active outcome instance.
    Exposes an intention-revealing interface and delegates mutation work to managers.
    
    Pattern: Domain Facade / Aggregate Controller
    """
    
    def __init__(self, request_id: Optional[int] = None, request: Optional[DispatchRequest] = None):
        """
        Initialize context from request_id or request object.
        
        Args:
            request_id: ID of the dispatch request
            request: DispatchRequest object
        """
        if request:
            self.request = request
            self.request_id = request.id
        elif request_id:
            self.request_id = request_id
            self.request = DispatchRequest.query.get_or_404(request_id)
        else:
            raise ValueError("Either request_id or request must be provided")
        
        # Build related objects
        self._build()
        
        # Initialize managers
        self.request_manager = RequestManager(self)
        self.outcome_manager = OutcomeManager(self)
    
    def _build(self) -> None:
        """
        Build all related objects (event and outcomes).
        
        Resolves active outcome using active_outcome_type/active_outcome_row_id.
        """
        # Load event
        if self.request.event_id:
            self.event = Event.query.get(self.request.event_id)
        else:
            self.event = None
        
        # Load all outcomes for history
        self.dispatch = StandardDispatch.query.filter_by(request_id=self.request_id).first()
        self.contract = Contract.query.filter_by(request_id=self.request_id).first()
        self.reimbursement = Reimbursement.query.filter_by(request_id=self.request_id).first()
        self.reject = Reject.query.filter_by(request_id=self.request_id).first()
        
        # Resolve active outcome from pointer
        self._resolve_active_outcome()
    
    def _resolve_active_outcome(self) -> None:
        """
        Resolve active outcome using active_outcome_type and active_outcome_row_id.
        
        Sets self.active_outcome_type, self.active_outcome_id, and self.active_outcome.
        """
        self.active_outcome_type = self.request.active_outcome_type
        self.active_outcome_id = self.request.active_outcome_row_id
        self.active_outcome = None
        
        if not self.active_outcome_type:
            return
        
        # Map outcome type to model and attribute
        outcome_map = {
            'dispatch': self.dispatch,
            'contract': self.contract,
            'reimbursement': self.reimbursement,
            'reject': self.reject,
        }
        
        self.active_outcome = outcome_map.get(self.active_outcome_type)
    
    @classmethod
    def load(cls, request_id: int) -> 'DispatchContext':
        """
        Factory method to load context from request_id.
        
        Args:
            request_id: ID of the dispatch request
            
        Returns:
            DispatchContext: Loaded context
        """
        return cls(request_id=request_id)
    
    @classmethod
    def from_request(cls, request: DispatchRequest) -> 'DispatchContext':
        """
        Factory method to create context from request object.
        
        Args:
            request: DispatchRequest object
            
        Returns:
            DispatchContext: Created context
        """
        return cls(request=request)
    
    # ========== Read Model Helpers ==========
    
    @property
    def outcome_history(self) -> List[Any]:
        """
        Get all outcomes for the request, sorted by creation time.
        
        Returns:
            list: All outcome objects sorted by created_at ascending
        """
        outcomes = []
        
        if self.dispatch:
            outcomes.append(self.dispatch)
        if self.contract:
            outcomes.append(self.contract)
        if self.reimbursement:
            outcomes.append(self.reimbursement)
        if self.reject:
            outcomes.append(self.reject)
        
        # Sort by created_at
        outcomes.sort(key=lambda o: o.created_at)
        
        return outcomes
    
    @property
    def has_event(self) -> bool:
        """Check if event exists"""
        return self.event is not None
    
    @property
    def has_active_outcome(self) -> bool:
        """Check if an active outcome exists"""
        return self.active_outcome is not None
    
    @property
    def has_any_outcome(self) -> bool:
        """Check if any outcome exists (active or cancelled)"""
        return any([self.dispatch, self.contract, self.reimbursement, self.reject])
    
    # ========== Request Lifecycle Operations ==========
    
    def submit(self, actor_id: int) -> 'DispatchContext':
        """
        Submit the request (legacy method - no-op since requests start as Submitted).
        
        Kept for backward compatibility.
        
        Args:
            actor_id: User submitting the request
            
        Returns:
            DispatchContext: self for chaining
        """
        self.request_manager.submit(actor_id)
        db.session.commit()
        self._build()
        return self
    
    def set_workflow_status(
        self,
        actor_id: int,
        new_status: str,
        reason: Optional[str] = None
    ) -> 'DispatchContext':
        """
        Set request workflow status.
        
        Args:
            actor_id: User making the change
            new_status: Target workflow_status
            reason: Optional reason for the transition
            
        Returns:
            DispatchContext: self for chaining
        """
        self.request_manager.set_workflow_status(actor_id, new_status, reason)
        db.session.commit()
        self._build()
        return self
    
    def begin_review(self, actor_id: int) -> 'DispatchContext':
        """Begin review (Submitted → UnderReview)"""
        self.request_manager.begin_review(actor_id)
        db.session.commit()
        self._build()
        return self
    
    def request_fixes(self, actor_id: int, reason: str) -> 'DispatchContext':
        """Request fixes from requester (UnderReview → FixesRequested)"""
        self.request_manager.request_fixes(actor_id, reason)
        db.session.commit()
        self._build()
        return self
    
    def resume_review(self, actor_id: int) -> 'DispatchContext':
        """Resume review after fixes (FixesRequested → UnderReview)"""
        self.request_manager.resume_review(actor_id)
        db.session.commit()
        self._build()
        return self
    
    def cancel_request(self, actor_id: int, reason: str) -> 'DispatchContext':
        """
        Cancel the request entirely.
        
        Cancels active outcome if present (composed operation).
        
        Args:
            actor_id: User cancelling the request
            reason: Reason for cancellation
            
        Returns:
            DispatchContext: self for chaining
        """
        # Cancel active outcome first if it exists
        if self.has_active_outcome:
            self.outcome_manager.cancel_active_outcome(actor_id, reason)
        
        # Cancel the request
        self.request_manager.cancel_request(actor_id, reason)
        db.session.commit()
        self._build()
        return self
    
    # ========== Outcome Lifecycle Operations ==========
    
    def assign_outcome(
        self,
        actor_id: int,
        outcome_type: str,
        payload: Dict[str, Any]
    ) -> 'DispatchContext':
        """
        Assign an outcome to the request.
        
        Args:
            actor_id: User assigning the outcome
            outcome_type: Type of outcome ('dispatch', 'contract', 'reimbursement', 'reject')
            payload: Data for creating the outcome
            
        Returns:
            DispatchContext: self for chaining
        """
        self.outcome_manager.assign_outcome(actor_id, outcome_type, payload)
        db.session.commit()
        self._build()
        return self
    
    def cancel_active_outcome(self, actor_id: int, reason: str) -> 'DispatchContext':
        """
        Cancel the active outcome.
        
        Args:
            actor_id: User cancelling the outcome
            reason: Reason for cancellation
            
        Returns:
            DispatchContext: self for chaining
        """
        self.outcome_manager.cancel_active_outcome(actor_id, reason)
        db.session.commit()
        self._build()
        return self
    
    def change_outcome(
        self,
        actor_id: int,
        new_outcome_type: str,
        payload: Dict[str, Any],
        reason: str
    ) -> 'DispatchContext':
        """
        Change outcome type (composed operation: cancel + assign).
        
        Args:
            actor_id: User changing the outcome
            new_outcome_type: New outcome type
            payload: Data for creating the new outcome
            reason: Reason for the change
            
        Returns:
            DispatchContext: self for chaining
        """
        self.outcome_manager.change_outcome(actor_id, new_outcome_type, payload, reason)
        db.session.commit()
        self._build()
        return self
    
    def set_resolution_status(
        self,
        actor_id: int,
        new_status: str,
        reason: Optional[str] = None
    ) -> 'DispatchContext':
        """
        Update the active outcome's resolution_status.
        
        Args:
            actor_id: User making the change
            new_status: Target resolution_status
            reason: Optional reason for the change
            
        Returns:
            DispatchContext: self for chaining
        """
        self.outcome_manager.set_resolution_status(actor_id, new_status, reason)
        db.session.commit()
        self._build()
        return self
    
    # ========== Comment Operations ==========
    
    def add_comment(self, user_id: int, comment_content: str, is_human_made: bool = True) -> 'DispatchContext':
        """
        Add a comment to the request's event.
        
        Args:
            user_id: User adding the comment
            comment_content: Comment content
            is_human_made: Whether comment is human-made (default True)
            
        Returns:
            DispatchContext: self for chaining
        """
        if not self.event:
            raise ValueError("Request does not have an associated event")
        
        event_context = EventContext(self.event)
        event_context.add_comment(user_id, comment_content, is_human_made=is_human_made)
        db.session.commit()
        return self
    
    # ========== Follow-up Request Operations ==========
    
    @classmethod
    def create_followup_request(
        cls,
        original_request_id: int,
        actor_id: int,
        new_payload: Dict[str, Any]
    ) -> 'DispatchContext':
        """
        Create a follow-up request when original request intent needs to change.
        
        Args:
            original_request_id: ID of the original request
            actor_id: User creating the follow-up
            new_payload: Data for the new request
            
        Returns:
            DispatchContext: Context for the new request
        """
        # Load original request
        original_ctx = cls.load(original_request_id)
        
        # Validate that original request is locked
        if not original_ctx.request_manager.is_intent_locked():
            raise ValueError(
                "Original request is not locked. "
                "Follow-up requests are only needed when intent is locked after outcome assignment."
            )
        
        # Create new request with previous_request_id link
        new_payload['previous_request_id'] = original_request_id
        new_payload['created_by_id'] = actor_id
        
        new_request = DispatchRequest(**new_payload)
        db.session.add(new_request)
        db.session.flush()
        
        # Ensure event is created
        if not new_request.event_id:
            new_request.create_event()
            db.session.flush()
        
        # Create contexts
        new_ctx = cls.from_request(new_request)
        
        # Add comments to both events
        if original_ctx.event:
            comment = DispatchNarrator.followup_created(original_request_id, new_request.id)
            original_ctx.add_comment(actor_id, comment, is_human_made=False)
        
        if new_ctx.event:
            comment = DispatchNarrator.followup_from(original_request_id)
            new_ctx.add_comment(actor_id, comment, is_human_made=False)
        
        db.session.commit()
        new_ctx._build()
        
        return new_ctx
    
    # ========== Validation Operations ==========
    
    def validate_outcome_uniqueness(self) -> None:
        """Validate that only one non-cancelled outcome exists"""
        self.outcome_manager.validate_outcome_uniqueness()
    
    def validate_active_pointer(self) -> None:
        """Validate active outcome pointer consistency"""
        self.outcome_manager.validate_active_pointer()
    
    def validate_intent_update(self, updates: Dict[str, Any]) -> None:
        """Validate that request intent fields can be updated"""
        self.request_manager.validate_intent_update(updates)
    
    # ========== Summary Operations ==========
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive summary of the dispatch context.
        
        Returns:
            dict: Summary information
        """
        return {
            'request_id': self.request.id,
            'workflow_status': self.request.workflow_status,
            'has_event': self.has_event,
            'active_outcome_type': self.active_outcome_type,
            'active_outcome_id': self.active_outcome_id,
            'has_active_outcome': self.has_active_outcome,
            'outcome_history_count': len(self.outcome_history),
            'is_intent_locked': self.request_manager.is_intent_locked(),
        }


# Register outcome handlers with factory
OutcomeHandlerFactory.register('dispatch', StandardDispatchHandler())
OutcomeHandlerFactory.register('contract', ContractHandler())
OutcomeHandlerFactory.register('reimbursement', ReimbursementHandler())
OutcomeHandlerFactory.register('reject', RejectHandler())
