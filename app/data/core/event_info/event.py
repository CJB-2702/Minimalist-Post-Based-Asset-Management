from app import db
from datetime import datetime
from abc import abstractmethod
from app.buisness.core.data_insertion_mixin import DataInsertionMixin
from app.data.core.user_created_base import UserCreatedBase
from app.data.core.virtual_sequence_generator import VirtualSequenceGenerator
from sqlalchemy.ext.declarative import declared_attr

class Event(UserCreatedBase, DataInsertionMixin):
    __tablename__ = 'events'
    
    event_type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=True)
    major_location_id = db.Column(db.Integer, db.ForeignKey('major_locations.id'), nullable=True)
    status = db.Column(db.String(20),nullable=True)
    
    # Relationships (no backrefs)
    user = db.relationship('User', foreign_keys=[user_id], overlaps="events")
    asset = db.relationship('Asset', overlaps="asset_ref,events")
    major_location = db.relationship('MajorLocation')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Auto-set major_location_id from asset if not provided
        if self.asset_id and not self.major_location_id:
            from app.data.core.asset_info.asset import Asset
            asset = Asset.query.get(self.asset_id)
            if asset and asset.major_location_id:
                self.major_location_id = asset.major_location_id
    
    def __repr__(self):
        return f'<Event {self.event_type}: {self.description}>'
    
    @classmethod
    def add_event(cls, event_type, description, user_id=None, asset_id=None, major_location_id=None, status=None):
        """
        Create and save a new event
        
        Args:
            event_type (str): Type of event
            description (str): Event description
            user_id (int, optional): User ID who triggered the event
            asset_id (int, optional): Related asset ID
            major_location_id (int, optional): Related location ID
            status (str, optional): Event status
            
        Returns:
            int: The ID of the created event
        """
        from app import db
        
        event = cls(
            event_type=event_type,
            description=description,
            user_id=user_id,
            asset_id=asset_id,
            major_location_id=major_location_id,
            status=status
        )
        
        db.session.add(event)
        db.session.flush()  # Get the ID without committing
        return event.id 
    

# EventDetailIDManager moved to app.models.core.sequences


class EventDetailVirtual(UserCreatedBase):
    """
    Base class for all event-specific detail tables
    Provides common functionality for event detail tables
    Uses shared global row ID sequence across all detail tables
    """
    __abstract__ = True
    
    # Common field for all event detail tables
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    all_details_id = db.Column(db.Integer, nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=True)
    
    # Relationship to Event
    @declared_attr
    def event(cls):
        # Use the class name to create a unique backref
        backref_name = f'{cls.__name__.lower()}_details'
        return db.relationship('Event', backref=backref_name)
    
    def __repr__(self):
        """String representation of the event detail table"""
        return f'<{self.__class__.__name__} Event:{self.event_id} GlobalID:{self.all_details_id}>'
    
    def __init__(self, *args, **kwargs):
        """Initialize the event detail record with global row ID assignment"""
        if 'all_details_id' not in kwargs:
            from app.data.core.sequences import EventDetailIDManager
            self.all_details_id = EventDetailIDManager.get_next_event_detail_id()

        if 'event_id' not in kwargs:
            self.create_event()

        super().__init__(*args, **kwargs)

    @abstractmethod
    def create_event(self):
        # Assign global row ID before calling parent constructor
        if self.asset_id:
            self.event_id = Event.add_event(event_type=self.event_type, description=self.description, user_id=self.user_id, asset_id=self.asset_id)
        else:
            self.event_id = Event.add_event(event_type=self.event_type, description=self.description, user_id=self.user_id)
