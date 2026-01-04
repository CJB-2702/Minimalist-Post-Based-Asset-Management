
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
    
    # Reference to the dispatch request
    request_id = db.Column(db.Integer, db.ForeignKey('dispatch_requests.id'), nullable=False)
    
    # Relationship to request
    @declared_attr
    def request(cls):
        return db.relationship('DispatchRequest', foreign_keys=[cls.request_id])

