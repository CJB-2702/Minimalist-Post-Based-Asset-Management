"""
Contract outcome handler

Strategy implementation for Contract outcomes.
"""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime
from app import db
from app.data.dispatching.outcomes.contract import Contract
from app.buisness.dispatching.errors import DispatchPolicyViolation
from app.buisness.dispatching.narrator import DispatchNarrator

if TYPE_CHECKING:
    from app.buisness.dispatching.context import DispatchContext


class ContractHandler:
    """Handler for Contract outcomes"""
    
    outcome_type = 'contract'
    
    def validate_assignment(self, ctx: 'DispatchContext', payload: Dict[str, Any]) -> None:
        """
        Validate Contract assignment.
        
        Checks:
        - Required fields are present
        """
        required_fields = ['company_name', 'cost_currency', 'cost_amount']
        missing = [f for f in required_fields if f not in payload]
        if missing:
            raise DispatchPolicyViolation(
                f"Missing required fields for Contract: {', '.join(missing)}"
            )
    
    def create(self, ctx: 'DispatchContext', actor_id: int, payload: Dict[str, Any]) -> Contract:
        """Create Contract outcome"""
        contract = Contract(
            request_id=ctx.request.id,
            request_event_id=ctx.request.event_id,
            outcome_type='contract',
            created_by_id=actor_id,
            **payload
        )
        
        db.session.add(contract)
        db.session.flush()
        
        return contract
    
    def cancel(self, ctx: 'DispatchContext', actor_id: int, reason: str) -> None:
        """Cancel Contract outcome"""
        if not ctx.contract:
            raise DispatchPolicyViolation("No Contract outcome to cancel")
        
        ctx.contract.cancelled = True
        ctx.contract.cancelled_at = datetime.utcnow()
        ctx.contract.cancelled_by_id = actor_id
        ctx.contract.cancelled_reason = reason
        ctx.contract.updated_by_id = actor_id
        
        # Set resolution_status to Cancelled
        ctx.contract.resolution_status = 'Cancelled'
    
    def describe_assigned(self, outcome: Contract) -> str:
        """Generate description for assignment"""
        return DispatchNarrator.contract_details(outcome)
    
    def describe_cancelled(self, outcome: Contract, reason: str) -> str:
        """Generate description for cancellation"""
        return f"Contract cancelled | {reason}"
