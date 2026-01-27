"""
DispatchManager - Manager for creating dispatch requests and outcomes

DEPRECATED: This class is deprecated in favor of the new architecture.
Use DispatchContext instead, which provides a compositional, pattern-oriented
design for managing request lifecycle, outcome lifecycle, reversals, and validation.

Legacy functionality:
- Provides methods for creating requests and all outcome types
- Handles validation and coordination of outcome creation

Migration path:
- For request creation: Use DispatchRequest directly or DispatchContext
- For outcome assignment: Use DispatchContext.assign_outcome()
- For outcome changes: Use DispatchContext.change_outcome()

This class is kept for backward compatibility with existing presentation layer code.
"""

from app import db
from app.data.dispatching.request import DispatchRequest
from app.data.dispatching.outcomes.standard_dispatch import StandardDispatch
from app.data.dispatching.outcomes.contract import Contract
from app.data.dispatching.outcomes.reimbursement import Reimbursement
from app.data.dispatching.outcomes.reject import Reject
from app.data.core.event_info.event import Event
from app.buisness.core.event_context import EventContext


class DispatchManager:
    """
    Manager for creating dispatch requests and outcomes.
    Provides factory methods for all outcome types.
    """
    
    @staticmethod
    def create_request(**kwargs):
        """
        Create a dispatch request (event will be auto-created by EventDetailVirtual)
        
        Args:
            **kwargs: Fields for DispatchRequest creation
            
        Returns:
            DispatchRequest: The created request
        """
        request = DispatchRequest(**kwargs)
        db.session.add(request)
        db.session.flush()  # Get ID and trigger event creation
        
        # Ensure event is created (EventDetailVirtual should handle this)
        if not request.event_id:
            request.create_event()
            db.session.flush()
        
        return request
    
    @staticmethod
    def create_dispatch_outcome(request_id, asset_id, assigned_by_id=None, created_by_id=None, **dispatch_kwargs):
        """
        Create a StandardDispatch outcome linked to a request
        
        Args:
            request_id (int): The dispatch request ID
            asset_id (int): REQUIRED - The asset being dispatched
            assigned_by_id (int, optional): User assigning the dispatch
            created_by_id (int, optional): User creating the dispatch
            **dispatch_kwargs: Fields for StandardDispatch creation
            
        Returns:
            StandardDispatch: Created dispatch outcome
        """
        # Get request and validate
        request = DispatchRequest.query.get_or_404(request_id)
        
        # Validate asset_id is provided
        if not asset_id:
            raise ValueError("asset_id is required for dispatch creation")
        
        # Check if dispatch already exists
        existing_dispatch = StandardDispatch.query.filter_by(request_id=request_id).first()
        if existing_dispatch:
            raise ValueError("Dispatch outcome already exists for this request")
        
        # Check if event exists
        if not request.event_id:
            raise ValueError("Request does not have an associated event")
        
        event = Event.query.get(request.event_id)
        
        # Override asset_dispatched_id in dispatch_kwargs to ensure consistency
        dispatch_kwargs['asset_dispatched_id'] = asset_id
        
        # Create outcome
        dispatch = StandardDispatch(
            request_id=request_id,
            assigned_by_id=assigned_by_id,
            created_by_id=created_by_id,
            **dispatch_kwargs
        )
        
        db.session.add(dispatch)
        db.session.flush()
        
        # Synchronize asset_id across all three entities
        # 1. Update event.asset_id
        if event:
            event.asset_id = asset_id
        
        # 2. Update request.asset_id
        request.asset_id = asset_id
        
        # 3. dispatch.asset_dispatched_id is already set via dispatch_kwargs above
        
        # Build comprehensive comment with dispatch details
        comment_parts = [
            f"Dispatch outcome created (ID: {dispatch.id})",
            f"Status: {dispatch.status}",
            f"Scheduled: {dispatch.scheduled_start.strftime('%Y-%m-%d %H:%M') if dispatch.scheduled_start else 'N/A'} to {dispatch.scheduled_end.strftime('%Y-%m-%d %H:%M') if dispatch.scheduled_end else 'N/A'}"
        ]
        
        # Add asset information
        from app.data.core.asset_info.asset import Asset
        asset = Asset.query.get(asset_id)
        if asset:
            comment_parts.append(f"Asset: {asset.name} (ID: {asset.id})")
        else:
            comment_parts.append(f"Asset ID: {asset_id}")
        
        # Add assigned user information if available
        if dispatch.assigned_person_id:
            from app.data.core.user_info.user import User
            assigned_user = User.query.get(dispatch.assigned_person_id)
            if assigned_user:
                comment_parts.append(f"Assigned person: {assigned_user.username}")
        
        comment = " | ".join(comment_parts)
        event_context = EventContext(event)
        event_context.add_comment(created_by_id or dispatch.created_by_id, comment)
        
        db.session.commit()
        return dispatch
    
    @staticmethod
    def create_contract_outcome(request_id, created_by_id=None, **contract_kwargs):
        """
        Create a Contract outcome linked to a request
        
        Args:
            request_id (int): The dispatch request ID
            created_by_id (int, optional): User creating the contract
            **contract_kwargs: Fields for Contract creation
            
        Returns:
            Contract: Created contract outcome
        """
        # Get request and validate
        request = DispatchRequest.query.get_or_404(request_id)
        
        # Check if contract already exists
        existing_contract = Contract.query.filter_by(request_id=request_id).first()
        if existing_contract:
            raise ValueError("Contract outcome already exists for this request")
        
        # Check if event exists
        if not request.event_id:
            raise ValueError("Request does not have an associated event")
        
        event = Event.query.get(request.event_id)
        
        # Create outcome
        contract = Contract(
            request_id=request_id,
            created_by_id=created_by_id,
            **contract_kwargs
        )
        
        db.session.add(contract)
        db.session.flush()
        
        # Update request and event status
        request.resolution_type = 'Contracted'
        request.status = 'Contracted'
        event.status = 'Contracted'
        
        # Add comment to request event
        comment = f"Contracted with {contract.company_name} for {contract.cost_currency} {contract.cost_amount}"
        if contract.contract_reference:
            comment += f" (Ref: {contract.contract_reference})"
        event_context = EventContext(event)
        event_context.add_comment(created_by_id or contract.created_by_id, comment)
        
        db.session.commit()
        return contract
    
    @staticmethod
    def create_reimbursement_outcome(request_id, created_by_id=None, **reimbursement_kwargs):
        """
        Create a Reimbursement outcome linked to a request
        
        Args:
            request_id (int): The dispatch request ID
            created_by_id (int, optional): User creating the reimbursement
            **reimbursement_kwargs: Fields for Reimbursement creation
            
        Returns:
            Reimbursement: Created reimbursement outcome
        """
        # Get request and validate
        request = DispatchRequest.query.get_or_404(request_id)
        
        # Check if reimbursement already exists
        existing_reimbursement = Reimbursement.query.filter_by(request_id=request_id).first()
        if existing_reimbursement:
            raise ValueError("Reimbursement outcome already exists for this request")
        
        # Check if event exists
        if not request.event_id:
            raise ValueError("Request does not have an associated event")
        
        event = Event.query.get(request.event_id)
        
        # Create outcome
        reimbursement = Reimbursement(
            request_id=request_id,
            created_by_id=created_by_id,
            **reimbursement_kwargs
        )
        
        db.session.add(reimbursement)
        db.session.flush()
        
        # Update request and event status
        request.resolution_type = 'Reimbursement'
        request.status = 'Reimbursed'
        event.status = 'Reimbursed'
        
        # Add comment to request event
        comment = f"Reimbursement recorded: {reimbursement.amount} from {reimbursement.from_account} to {reimbursement.to_account}"
        if reimbursement.policy_reference:
            comment += f" (Policy: {reimbursement.policy_reference})"
        event_context = EventContext(event)
        event_context.add_comment(created_by_id or reimbursement.created_by_id, comment)
        
        db.session.commit()
        return reimbursement
    
    @staticmethod
    def create_reject_outcome(request_id, created_by_id=None, **reject_kwargs):
        """
        Create a Reject outcome linked to a request
        
        Args:
            request_id (int): The dispatch request ID
            created_by_id (int, optional): User creating the rejection
            **reject_kwargs: Fields for Reject creation
            
        Returns:
            Reject: Created reject outcome
        """
        # Get request and validate
        request = DispatchRequest.query.get_or_404(request_id)
        
        # Check if reject already exists
        existing_reject = Reject.query.filter_by(request_id=request_id).first()
        if existing_reject:
            raise ValueError("Reject outcome already exists for this request")
        
        # Check if event exists
        if not request.event_id:
            raise ValueError("Request does not have an associated event")
        
        event = Event.query.get(request.event_id)
        
        # Create outcome
        reject = Reject(
            request_id=request_id,
            created_by_id=created_by_id,
            **reject_kwargs
        )
        
        db.session.add(reject)
        db.session.flush()
        
        # Update request and event status
        request.resolution_type = 'Rejected'
        request.status = 'Rejected'
        event.status = 'Rejected'
        
        # Add comment to request event
        comment = f"Request rejected: {reject.reason}"
        if reject.rejection_category:
            comment += f" (Category: {reject.rejection_category})"
        if reject.can_resubmit:
            comment += " - Resubmission allowed"
            if reject.resubmit_after:
                comment += f" after {reject.resubmit_after.strftime('%Y-%m-%d')}"
        event_context = EventContext(event)
        event_context.add_comment(created_by_id or reject.created_by_id, comment)
        
        db.session.commit()
        return reject

