from app import db
from app.data.dispatching.virtual_dispatch_outcome import VirtualDispatchOutcome


class Reject(VirtualDispatchOutcome):
    __tablename__ = 'dispatch_reject_details'

    # Rejection reason
    reason = db.Column(db.Text, nullable=False)
    rejection_category = db.Column(db.String(100), nullable=True)  # e.g., "Resource Unavailable", "Policy Violation", "Timing Conflict", "Other"
    notes = db.Column(db.Text, nullable=True)
    
    # Optional: Can specify alternative suggestions
    alternative_suggestion = db.Column(db.Text, nullable=True)
    can_resubmit = db.Column(db.Boolean, default=False)
    resubmit_after = db.Column(db.DateTime, nullable=True)
