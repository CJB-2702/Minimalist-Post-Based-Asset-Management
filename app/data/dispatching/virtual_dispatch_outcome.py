
from app import db
from app.data.core.user_created_base import UserCreatedBase
from sqlalchemy.ext.declarative import declared_attr


class VirtualDispatchOutcome(UserCreatedBase):
    """
    Base class for dispatch outcomes (StandardDispatch, Contract, Reimbursement)
    Decoupled from EventDetailVirtual - outcomes reference the request
    
    Note: Use DispatchContext for business logic operations (comments, status updates, etc.)
    """
    __abstract__ = True
    
    # Override created_by_id to make it required for outcomes
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Reference to the dispatch request
    request_id = db.Column(db.Integer, db.ForeignKey('dispatch_requests.id'), nullable=False)
    request_event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)


    outcome_type = db.Column(db.String(50), nullable=False)
    cancelled = db.Column(db.Boolean, default=False)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancelled_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    cancelled_reason = db.Column(db.Text, nullable=True)

    @declared_attr
    def request(cls):
        return db.relationship('DispatchRequest', foreign_keys=[cls.request_id])
    
    @declared_attr
    def request_event(cls):
        return db.relationship('Event', foreign_keys=[cls.request_event_id])