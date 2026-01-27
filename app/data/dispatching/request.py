from app import db
from app.data.core.event_info.event import Event, EventDetailVirtual


class DispatchRequest(EventDetailVirtual):
    __tablename__ = 'dispatch_requests'

    # Constants
    event_type = "Dispatch"

    # Domain fields - Who requested and for whom
    # requested_by: The person who created this request (defaults to current_user, can be changed)
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    # requested_for: The person this request is for (required)
    requested_for = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Request intent fields (IMMUTABLE after first outcome assignment)
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
    
    # Optional: Request a specific asset (if user knows exactly which asset they want)
    # If a StandardDispatch is created, copy this to StandardDispatch.asset_dispatched_id
    requested_asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=True)
    
    # Workflow fields (MUTABLE)
    submitted_at = db.Column(db.DateTime, nullable=True)
    # workflow_status: Requested, Submitted, UnderReview, FixesRequested, Planned, Resolved, Cancelled
    workflow_status = db.Column(db.String(50), nullable=False, default='Requested')
    # Legacy status field - kept for compatibility during transition
    status = db.Column(db.String(50), nullable=False, default='Requested')
    
    # Current outcome tracking (MUTABLE)
    # active_outcome_type: 'dispatch'|'contract'|'reimbursement'|'reject'|null
    active_outcome_type = db.Column(db.String(50), nullable=True)
    active_outcome_row_id = db.Column(db.Integer, nullable=True)
    resolution_type = db.Column(db.String(50), nullable=True)  # Legacy field, may become redundant
    
    # Follow-up linkage: If request intent needs to change after outcome assignment,
    # create a new request and link it to the original via this field.
    # Renamed from previously_rejected_request_id to cover all replacement scenarios.
    previous_request_id = db.Column(
        db.Integer,
        db.ForeignKey('dispatch_requests.id'),
        nullable=True,
    )


    # Relationships
    requested_by_user = db.relationship('User', foreign_keys=[requested_by])
    requested_for_user = db.relationship('User', foreign_keys=[requested_for])
    asset_type = db.relationship('AssetType')
    major_location = db.relationship('MajorLocation')
    requested_asset = db.relationship('Asset', foreign_keys=[requested_asset_id])
    previous_request = db.relationship(
        'DispatchRequest',
        remote_side='DispatchRequest.id',
        foreign_keys=[previous_request_id],
        backref='follow_up_requests'
    )
    
    # Note: Use DispatchContext to access outcomes and perform operations

    def create_event(self):
        # Ensure coherent description and status on Event creation
        description = f"Dispatch request created for asset type {self.asset_type_id}"
        status = self.status or 'Submitted'

        self.event_id = Event.add_event(
            event_type=self.event_type,
            description=description,
            user_id=self.created_by_id,
            asset_id=self.asset_id,
            status=status,
        )




