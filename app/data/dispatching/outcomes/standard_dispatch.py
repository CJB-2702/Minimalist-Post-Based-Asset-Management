from app import db
from app.data.dispatching.virtual_dispatch_outcome import VirtualDispatchOutcome


class StandardDispatch(VirtualDispatchOutcome):
    __tablename__ = 'dispatches'

    # Links
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

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

    # Status
    status = db.Column(db.String(50), nullable=False, default='Planned')
    conflicts_resolved = db.Column(db.Boolean, default=False)

    # Relationships
    assigned_by = db.relationship('User', foreign_keys=[assigned_by_id])




