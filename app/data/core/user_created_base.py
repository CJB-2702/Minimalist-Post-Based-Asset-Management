from app import db
from datetime import datetime
from sqlalchemy.ext.declarative import declared_attr
from app.buisness.core.data_insertion_mixin import DataInsertionMixin

class UserCreatedBase(db.Model, DataInsertionMixin):
    """Abstract base class for all user-created entities with audit trail"""
    
    __abstract__ = True
    
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower() + 's'
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    @declared_attr
    def created_by(cls):
        return db.relationship('User', foreign_keys=[cls.created_by_id], overlaps="created_assets,created_locations,created_asset_types,created_make_models,events,created_comments,created_attachments")
    
    @declared_attr
    def updated_by(cls):
        return db.relationship('User', foreign_keys=[cls.updated_by_id], overlaps="updated_assets,updated_locations,updated_asset_types,updated_make_models,events,updated_comments,updated_attachments") 
    
    def get_columns(self):
        return {
            'id', 'created_at', 'created_by_id', 'updated_at', 'updated_by_id'
        }