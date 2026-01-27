from app import db
from app.data.dispatching.virtual_dispatch_outcome import VirtualDispatchOutcome


class StandardDispatch(VirtualDispatchOutcome):
    __tablename__ = 'dispatches'
    
    # Set default outcome_type for this outcome class
    outcome_type = db.Column(db.String(50), nullable=False, default='dispatch')

    # Links
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_person_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    asset_dispatched_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=True)


    # Schedule
    scheduled_start = db.Column(db.DateTime, nullable=False)
    scheduled_end = db.Column(db.DateTime, nullable=False)
    actual_start = db.Column(db.DateTime, nullable=True)
    actual_end = db.Column(db.DateTime, nullable=True)

    # Metering
    meter_start = db.Column(db.Float, nullable=True)
    meter_end = db.Column(db.Float, nullable=True)

    # Locations (freeform or codes)
    location_from_id = db.Column(db.String(100), nullable=True)
    location_to_id = db.Column(db.String(100), nullable=True)

    # Resolution lifecycle status: Planned, In Progress, Complete, Cancelled
    resolution_status = db.Column(db.String(50), nullable=False, default='Planned')
    # Legacy status field - kept for compatibility during transition
    status = db.Column(db.String(50), nullable=False, default='Planned')
    conflicts_resolved = db.Column(db.Boolean, default=False)

    # Relationships
    assigned_by = db.relationship('User', foreign_keys=[assigned_by_id])
    assigned_person = db.relationship('User', foreign_keys=[assigned_person_id])
    asset_dispatched = db.relationship('Asset', foreign_keys=[asset_dispatched_id])

    




