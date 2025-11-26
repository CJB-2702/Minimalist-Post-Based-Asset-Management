#!/usr/bin/env python3
"""
Model Detail Virtual Base Class
Base class for all model-specific detail tables
"""

from app.data.core.user_created_base import UserCreatedBase
from app import db
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import event
from app.data.core.sequences import ModelDetailIDManager


class ModelDetailVirtual(UserCreatedBase):
    """
    Base class for all model-specific detail tables
    Provides common functionality for model detail tables
    """
    __abstract__ = True
    
    # Common field for all model detail tables
    make_model_id = db.Column(db.Integer, db.ForeignKey('make_models.id'), nullable=False)
    all_model_detail_id = db.Column(db.Integer, nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=True)
    
    # Relationship to MakeModel
    @declared_attr
    def make_model(cls):
        # Use the class name to create a unique backref
        backref_name = f'{cls.__name__.lower()}_details'
        return db.relationship('MakeModel', backref=backref_name)
    
    # Relationship to Event
    @declared_attr
    def event(cls):
        return db.relationship('Event', backref=f'{cls.__name__.lower()}_details')
    
    def __repr__(self):
        """String representation of the model detail table"""
        return f'<{self.__class__.__name__} Model:{self.make_model_id} GlobalID:{self.all_model_detail_id}>'
    
    def __init__(self, *args, **kwargs):
        """Initialize the model detail record with global row ID assignment"""
        kwargs['all_model_detail_id'] = ModelDetailIDManager.get_next_model_detail_id()
        super().__init__(*args, **kwargs)


# Note: Event listeners for abstract classes don't work in SQLAlchemy
# The event listener will be registered on concrete classes in their __init__.py files
