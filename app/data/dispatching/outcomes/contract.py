from app import db
from app.data.dispatching.virtual_dispatch_outcome import VirtualDispatchOutcome


class Contract(VirtualDispatchOutcome):
    __tablename__ = 'dispatch_contract_details'
    outcome_type = db.Column(db.String(50), nullable=False, default='contract')
    
    # Resolution lifecycle status: Planned, Complete, Cancelled
    resolution_status = db.Column(db.String(50), nullable=False, default='Planned')

    company_name = db.Column(db.String(255), nullable=False)
    cost_currency = db.Column(db.String(10), nullable=False)
    cost_amount = db.Column(db.Float, nullable=False)
    contract_reference = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)




