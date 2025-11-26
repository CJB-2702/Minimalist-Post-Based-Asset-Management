from app import db
from app.data.dispatching.virtual_dispatch_outcome import VirtualDispatchOutcome


class Reimbursement(VirtualDispatchOutcome):
    __tablename__ = 'dispatch_reimbursement_details'

    from_account = db.Column(db.String(100), nullable=False)
    to_account = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    policy_reference = db.Column(db.String(255), nullable=True)




