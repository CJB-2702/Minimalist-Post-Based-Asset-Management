from app import db
from datetime import datetime
from app.data.core.event_info.event import Event, EventDetailVirtual


class DispatchRequest(EventDetailVirtual):
    __tablename__ = 'dispatch_requests'

    # Constants
    event_type = "Dispatch"

    # Domain fields
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    submitted_at = db.Column(db.DateTime, nullable=True)
    desired_start = db.Column(db.DateTime, nullable=False)
    desired_end = db.Column(db.DateTime, nullable=False)
    num_people = db.Column(db.Integer, nullable=True)
    names_freeform = db.Column(db.Text, nullable=True)
    asset_type_id = db.Column(db.Integer, db.ForeignKey('asset_types.id'), nullable=False)
    asset_subclass_text = db.Column(db.String(255), nullable=False)
    dispatch_scope = db.Column(db.String(50), nullable=False)
    estimated_meter_usage = db.Column(db.Float, nullable=True)
    major_location_id = db.Column(db.Integer, db.ForeignKey('major_locations.id'), nullable=False)
    activity_location = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='Draft')
    resolution_type = db.Column(db.String(50), nullable=True)


    # Relationships
    requester = db.relationship('User', foreign_keys=[requester_id])
    asset_type = db.relationship('AssetType')
    major_location = db.relationship('MajorLocation')
    
    # Note: Use DispatchContext to access outcomes and perform operations

    def create_event(self):
        # Ensure coherent description and status on Event creation
        description = f"Dispatch request created for asset type {self.asset_type_id}"
        status = 'RequestCreated' if self.status == 'Draft' else self.status

        self.event_id = Event.add_event(
            event_type=self.event_type,
            description=description,
            user_id=self.created_by_id,
            asset_id=self.asset_id,
            status=status,
        )




