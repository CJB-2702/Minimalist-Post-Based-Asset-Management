"""
DispatchNarrator - Comment composer for dispatch lifecycle events

Ensures every transition produces a consistent machine-generated comment.
Separates audit narrative formatting from transition logic.
"""

from datetime import datetime
from typing import Optional


class DispatchNarrator:
    """
    Composes machine-generated comments for dispatch lifecycle events.
    
    All methods return comment text that should be added to the request Event
    with is_human_made=False.
    """
    
    @staticmethod
    def request_created(request) -> str:
        """Comment for request creation"""
        return f"Request created (ID: {request.id})"
    
    @staticmethod
    def request_submitted(request) -> str:
        """Comment for request submission"""
        return f"Request submitted at {request.submitted_at.strftime('%Y-%m-%d %H:%M') if request.submitted_at else 'N/A'}"
    
    @staticmethod
    def workflow_status_changed(from_status: str, to_status: str, reason: Optional[str] = None) -> str:
        """Comment for request workflow status changes"""
        comment = f"Workflow status changed: {from_status} → {to_status}"
        if reason:
            comment += f" | Reason: {reason}"
        return comment
    
    @staticmethod
    def request_cancelled(reason: str) -> str:
        """Comment for request cancellation"""
        return f"Request cancelled | Reason: {reason}"
    
    @staticmethod
    def fixes_requested(reason: str) -> str:
        """Comment when dispatcher requests fixes from requester"""
        return f"Fixes requested | Details: {reason}"
    
    @staticmethod
    def review_resumed() -> str:
        """Comment when review resumes after fixes"""
        return "Review resumed after fixes received"
    
    @staticmethod
    def outcome_assigned(outcome_type: str, outcome_id: int, extra: Optional[str] = None) -> str:
        """Comment for outcome assignment"""
        comment = f"Outcome assigned: {outcome_type.capitalize()} (ID: {outcome_id})"
        if extra:
            comment += f" | {extra}"
        return comment
    
    @staticmethod
    def outcome_cancelled(outcome_type: str, outcome_id: int, reason: str) -> str:
        """Comment for outcome cancellation"""
        return f"Outcome cancelled: {outcome_type.capitalize()} (ID: {outcome_id}) | Reason: {reason}"
    
    @staticmethod
    def outcome_changed(old_type: str, old_id: int, new_type: str, new_id: int, reason: str) -> str:
        """Comment for outcome type change (cancel + reassign)"""
        return (
            f"Outcome changed: {old_type.capitalize()} (ID: {old_id}) → "
            f"{new_type.capitalize()} (ID: {new_id}) | Reason: {reason}"
        )
    
    @staticmethod
    def resolution_status_changed(
        outcome_type: str,
        from_status: str,
        to_status: str,
        reason: Optional[str] = None
    ) -> str:
        """Comment for outcome resolution status changes"""
        comment = f"{outcome_type.capitalize()} resolution status: {from_status} → {to_status}"
        if reason:
            comment += f" | Reason: {reason}"
        return comment
    
    @staticmethod
    def followup_created(original_request_id: int, new_request_id: int) -> str:
        """Comment for follow-up request creation (on original request)"""
        return f"Follow-up request created (ID: {new_request_id}) to modify locked request intent"
    
    @staticmethod
    def followup_from(original_request_id: int) -> str:
        """Comment for follow-up request (on new request)"""
        return f"Follow-up to request ID: {original_request_id}"
    
    @staticmethod
    def dispatch_details(dispatch) -> str:
        """Generate detailed description for StandardDispatch outcome"""
        parts = []
        
        if dispatch.scheduled_start and dispatch.scheduled_end:
            parts.append(
                f"Scheduled: {dispatch.scheduled_start.strftime('%Y-%m-%d %H:%M')} to "
                f"{dispatch.scheduled_end.strftime('%Y-%m-%d %H:%M')}"
            )
        
        if dispatch.asset_dispatched_id:
            parts.append(f"Asset ID: {dispatch.asset_dispatched_id}")
        
        if dispatch.assigned_person_id:
            parts.append(f"Assigned to User ID: {dispatch.assigned_person_id}")
        
        return " | ".join(parts) if parts else "No additional details"
    
    @staticmethod
    def contract_details(contract) -> str:
        """Generate detailed description for Contract outcome"""
        parts = [
            f"Company: {contract.company_name}",
            f"Cost: {contract.cost_currency} {contract.cost_amount}"
        ]
        
        if contract.contract_reference:
            parts.append(f"Reference: {contract.contract_reference}")
        
        return " | ".join(parts)
    
    @staticmethod
    def reimbursement_details(reimbursement) -> str:
        """Generate detailed description for Reimbursement outcome"""
        parts = [
            f"Amount: {reimbursement.amount}",
            f"From: {reimbursement.from_account}",
            f"To: {reimbursement.to_account}"
        ]
        
        if reimbursement.policy_reference:
            parts.append(f"Policy: {reimbursement.policy_reference}")
        
        return " | ".join(parts)
    
    @staticmethod
    def reject_details(reject) -> str:
        """Generate detailed description for Reject outcome"""
        parts = [f"Reason: {reject.reason}"]
        
        if reject.rejection_category:
            parts.append(f"Category: {reject.rejection_category}")
        
        if reject.can_resubmit:
            resubmit_text = "Resubmission allowed"
            if reject.resubmit_after:
                resubmit_text += f" after {reject.resubmit_after.strftime('%Y-%m-%d')}"
            parts.append(resubmit_text)
        
        return " | ".join(parts)
