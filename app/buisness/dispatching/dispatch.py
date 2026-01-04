"""
DispatchContext - Context class for dispatch operations

Holds references to event, request, and all possible outcomes.
Contains all business logic for dispatch operations.
Provides primary interface for route interactions.
"""

from app import db
from app.data.core.event_info.event import Event
from app.data.dispatching.request import DispatchRequest
from app.data.dispatching.outcomes.standard_dispatch import StandardDispatch
from app.data.dispatching.outcomes.contract import Contract
from app.data.dispatching.outcomes.reimbursement import Reimbursement
from app.data.dispatching.outcomes.reject import Reject
from app.buisness.core.event_context import EventContext

#pulled a sneaky on you
class DispatchContext:
    """
    Context class that holds references to event, request, and all outcomes.
    Can build itself from a request_id and provides logic to determine active outcome.
    Primary interface for route interactions.
    """
    
    def __init__(self, request_id=None, request=None):
        """
        Initialize context. Can build from request_id or provide request object.
        
        Args:
            request_id (int, optional): ID of the dispatch request
            request (DispatchRequest, optional): DispatchRequest object
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
    
    def _build(self):
        """Build all related objects (event and outcomes)"""
        # Load event
        if self.request.event_id:
            self.event = Event.query.get(self.request.event_id)
        else:
            self.event = None
        
        # Load all possible outcomes
        self.dispatch = StandardDispatch.query.filter_by(request_id=self.request_id).first()
        self.contract = Contract.query.filter_by(request_id=self.request_id).first()
        self.reimbursement = Reimbursement.query.filter_by(request_id=self.request_id).first()
        self.reject = Reject.query.filter_by(request_id=self.request_id).first()
        
        # Determine active outcome
        self._determine_outcome()
    
    def _determine_outcome(self):
        """
        Determine which outcome is active based on resolution_type and existence.
        Sets self.outcome and self.outcome_type.
        Priority: Reject > Contract/Reimbursement > Dispatch
        """
        self.outcome = None
        self.outcome_type = None
        
        # Reject takes highest priority as it's a terminal state
        if self.reject:
            self.outcome = self.reject
            self.outcome_type = 'reject'
        # Check resolution_type next
        elif self.request.resolution_type == 'Contracted' and self.contract:
            self.outcome = self.contract
            self.outcome_type = 'contract'
        elif self.request.resolution_type == 'Reimbursement' and self.reimbursement:
            self.outcome = self.reimbursement
            self.outcome_type = 'reimbursement'
        # Dispatch is the default outcome if it exists and no specific resolution
        elif self.dispatch:
            self.outcome = self.dispatch
            self.outcome_type = 'dispatch'
        # Fallback: check what exists
        elif self.contract:
            self.outcome = self.contract
            self.outcome_type = 'contract'
        elif self.reimbursement:
            self.outcome = self.reimbursement
            self.outcome_type = 'reimbursement'
    
    @classmethod
    def from_request_id(cls, request_id):
        """Factory method to create context from request_id"""
        return cls(request_id=request_id)
    
    @classmethod
    def from_request(cls, request):
        """Factory method to create context from request object"""
        return cls(request=request)
    
    # Convenience properties
    @property
    def has_event(self):
        """Check if event exists"""
        return self.event is not None
    
    @property
    def has_outcome(self):
        """Check if any outcome exists"""
        return self.outcome is not None
    
    @property
    def has_dispatch(self):
        """Check if dispatch outcome exists"""
        return self.dispatch is not None
    
    @property
    def has_contract(self):
        """Check if contract outcome exists"""
        return self.contract is not None
    
    @property
    def has_reimbursement(self):
        """Check if reimbursement outcome exists"""
        return self.reimbursement is not None
    
    @property
    def has_reject(self):
        """Check if reject outcome exists"""
        return self.reject is not None
    
    # Business logic methods - all logic contained in context
    def update_request_status(self, new_status, user_id=None, comment=None):
        """
        Update request status, sync event status, and add comment if provided
        
        Args:
            new_status (str): New status value
            user_id (int, optional): User making the change
            comment (str, optional): Comment to add to event
            
        Returns:
            DispatchContext: self for chaining
        """
        self.request.status = new_status
        
        # Sync event status if event exists
        if self.event:
            self.event.status = new_status
        
        # Add comment if provided
        if comment and self.event and user_id:
            comment_text = f"Status changed to {new_status}: {comment}"
            event_context = EventContext(self.event)
            event_context.add_comment(user_id, comment_text)
        
        db.session.commit()
        self._build()  # Rebuild to refresh state
        return self
    
    def add_comment(self, user_id, comment_content):
        """
        Add a comment to the request's event
        
        Args:
            user_id (int): User adding the comment
            comment_content (str): Comment content
            
        Returns:
            DispatchContext: self for chaining
        """
        if not self.event:
            raise ValueError("Request does not have an associated event")
        
        event_context = EventContext(self.event)
        event_context.add_comment(user_id, comment_content)
        db.session.commit()
        return self
    
    def create_dispatch_outcome(self, assigned_by_id=None, created_by_id=None, **dispatch_kwargs):
        """
        Create a StandardDispatch outcome linked to this request
        
        Args:
            assigned_by_id (int, optional): User assigning the dispatch
            created_by_id (int, optional): User creating the dispatch
            **dispatch_kwargs: Fields for StandardDispatch creation
            
        Returns:
            StandardDispatch: Created dispatch outcome
        """
        # Validate
        if self.dispatch:
            raise ValueError("Dispatch outcome already exists for this request")
        
        if not self.event:
            raise ValueError("Request does not have an associated event")
        
        # Create outcome
        dispatch = StandardDispatch(
            request_id=self.request_id,
            assigned_by_id=assigned_by_id,
            created_by_id=created_by_id,
            **dispatch_kwargs
        )
        
        db.session.add(dispatch)
        db.session.flush()
        
        # Set event asset_id to the dispatched asset if provided
        if dispatch.assett_dispatched_id and self.event:
            self.event.asset_id = dispatch.assett_dispatched_id
        
        # Build comprehensive comment with dispatch details
        comment_parts = [
            f"Dispatch outcome created (ID: {dispatch.id})",
            f"Status: {dispatch.status}",
            f"Scheduled: {dispatch.scheduled_start.strftime('%Y-%m-%d %H:%M') if dispatch.scheduled_start else 'N/A'} to {dispatch.scheduled_end.strftime('%Y-%m-%d %H:%M') if dispatch.scheduled_end else 'N/A'}"
        ]
        
        # Add asset information if available
        if dispatch.assett_dispatched_id:
            from app.data.core.asset_info.asset import Asset
            asset = Asset.query.get(dispatch.assett_dispatched_id)
            if asset:
                comment_parts.append(f"Asset: {asset.name} (ID: {asset.id})")
            else:
                comment_parts.append(f"Asset ID: {dispatch.assett_dispatched_id}")
        
        # Add assigned user information if available
        if dispatch.assigned_to_id:
            from app.data.core.user_info.user import User
            assigned_user = User.query.get(dispatch.assigned_to_id)
            if assigned_user:
                comment_parts.append(f"Assigned to: {assigned_user.username}")
        
        comment = " | ".join(comment_parts)
        event_context = EventContext(self.event)
        event_context.add_comment(created_by_id or dispatch.created_by_id, comment)
        
        db.session.commit()
        self._build()  # Rebuild to refresh state
        return dispatch
    
    def create_contract_outcome(self, created_by_id=None, **contract_kwargs):
        """
        Create a Contract outcome linked to this request
        
        Args:
            created_by_id (int, optional): User creating the contract
            **contract_kwargs: Fields for Contract creation
            
        Returns:
            Contract: Created contract outcome
        """
        # Validate
        if self.contract:
            raise ValueError("Contract outcome already exists for this request")
        
        if not self.event:
            raise ValueError("Request does not have an associated event")
        
        # Create outcome
        contract = Contract(
            request_id=self.request_id,
            created_by_id=created_by_id,
            **contract_kwargs
        )
        
        db.session.add(contract)
        db.session.flush()
        
        # Update request and event status
        self.request.resolution_type = 'Contracted'
        self.request.status = 'Contracted'
        self.event.status = 'Contracted'
        
        # Add comment to request event
        comment = f"Contracted with {contract.company_name} for {contract.cost_currency} {contract.cost_amount}"
        if contract.contract_reference:
            comment += f" (Ref: {contract.contract_reference})"
        event_context = EventContext(self.event)
        event_context.add_comment(created_by_id or contract.created_by_id, comment)
        
        db.session.commit()
        self._build()  # Rebuild to refresh state
        return contract
    
    def create_reimbursement_outcome(self, created_by_id=None, **reimbursement_kwargs):
        """
        Create a Reimbursement outcome linked to this request
        
        Args:
            created_by_id (int, optional): User creating the reimbursement
            **reimbursement_kwargs: Fields for Reimbursement creation
            
        Returns:
            Reimbursement: Created reimbursement outcome
        """
        # Validate
        if self.reimbursement:
            raise ValueError("Reimbursement outcome already exists for this request")
        
        if not self.event:
            raise ValueError("Request does not have an associated event")
        
        # Create outcome
        reimbursement = Reimbursement(
            request_id=self.request_id,
            created_by_id=created_by_id,
            **reimbursement_kwargs
        )
        
        db.session.add(reimbursement)
        db.session.flush()
        
        # Update request and event status
        self.request.resolution_type = 'Reimbursement'
        self.request.status = 'Reimbursed'
        self.event.status = 'Reimbursed'
        
        # Add comment to request event
        comment = f"Reimbursement recorded: {reimbursement.amount} from {reimbursement.from_account} to {reimbursement.to_account}"
        if reimbursement.policy_reference:
            comment += f" (Policy: {reimbursement.policy_reference})"
        event_context = EventContext(self.event)
        event_context.add_comment(created_by_id or reimbursement.created_by_id, comment)
        
        db.session.commit()
        self._build()  # Rebuild to refresh state
        return reimbursement
    
    def create_reject_outcome(self, created_by_id=None, **reject_kwargs):
        """
        Create a Reject outcome linked to this request
        
        Args:
            created_by_id (int, optional): User creating the rejection
            **reject_kwargs: Fields for Reject creation
            
        Returns:
            Reject: Created reject outcome
        """
        # Validate
        if self.reject:
            raise ValueError("Reject outcome already exists for this request")
        
        if not self.event:
            raise ValueError("Request does not have an associated event")
        
        # Create outcome
        reject = Reject(
            request_id=self.request_id,
            created_by_id=created_by_id,
            **reject_kwargs
        )
        
        db.session.add(reject)
        db.session.flush()
        
        # Update request and event status
        self.request.resolution_type = 'Rejected'
        self.request.status = 'Rejected'
        self.event.status = 'Rejected'
        
        # Add comment to request event
        comment = f"Request rejected: {reject.reason}"
        if reject.rejection_category:
            comment += f" (Category: {reject.rejection_category})"
        if reject.can_resubmit:
            comment += " - Resubmission allowed"
            if reject.resubmit_after:
                comment += f" after {reject.resubmit_after.strftime('%Y-%m-%d')}"
        event_context = EventContext(self.event)
        event_context.add_comment(created_by_id or reject.created_by_id, comment)
        
        db.session.commit()
        self._build()  # Rebuild to refresh state
        return reject
    
    def update_dispatch_status(self, new_status, user_id=None, comment=None):
        """
        Update dispatch status and add comment to request event
        
        Args:
            new_status (str): New status value
            user_id (int, optional): User making the change
            comment (str, optional): Comment to add
            
        Returns:
            DispatchContext: self for chaining
        """
        if not self.dispatch:
            raise ValueError("No dispatch outcome exists for this request")
        
        self.dispatch.status = new_status
        
        # Add comment to request event if provided
        if self.event and (comment or user_id):
            comment_text = f"Dispatch status changed to {new_status}"
            if comment:
                comment_text += f": {comment}"
            event_context = EventContext(self.event)
            event_context.add_comment(user_id or self.dispatch.updated_by_id, comment_text)
        
        db.session.commit()
        self._build()  # Rebuild to refresh state
        return self
    
    def validate_outcome_creation(self, outcome_type):
        """
        Validate that an outcome can be created for this request
        
        Args:
            outcome_type (str): Type of outcome ('dispatch', 'contract', 'reimbursement', 'reject')
            
        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        if not self.event:
            return False, "Request does not have an associated event"
        
        # Check if outcome already exists
        if outcome_type == 'dispatch' and self.dispatch:
            return False, "Dispatch outcome already exists for this request"
        elif outcome_type == 'contract' and self.contract:
            return False, "Contract outcome already exists for this request"
        elif outcome_type == 'reimbursement' and self.reimbursement:
            return False, "Reimbursement outcome already exists for this request"
        elif outcome_type == 'reject' and self.reject:
            return False, "Reject outcome already exists for this request"
        
        return True, None
    
    def get_outcome_summary(self):
        """
        Get a summary of all outcomes
        
        Returns:
            dict: Summary information about outcomes
        """
        return {
            'has_outcome': self.has_outcome,
            'outcome_type': self.outcome_type,
            'outcome': self.outcome,
            'dispatch': self.dispatch,
            'contract': self.contract,
            'reimbursement': self.reimbursement,
            'reject': self.reject,
            'resolution_type': self.request.resolution_type,
            'status': self.request.status
        }

