"""
Generic data insertion mixin for SQLAlchemy models
Provides from_dict and to_dict methods for automatic data insertion

LAYER PLACEMENT REVIEW (APPROVED):
This mixin belongs in the business layer (app/buisness/core/) because:
- It provides utility methods for data model serialization/deserialization
- It's used by data models via inheritance (mixed into model classes)
- It handles business logic for data transformation (from_dict, to_dict)
- It manages audit fields (created_by_id, updated_by_id) which are business concerns
- It's not presentation-specific (used by both presentation and business layers)
- It's not data layer infrastructure (it adds behavior to models, not just structure)

This mixin is correctly placed in the business layer and should remain here.
"""

from app import db
from datetime import datetime
from sqlalchemy import inspect
from app.logger import get_logger

logger = get_logger("asset_management.domain.core.data_insertion")

class DataInsertionMixin:
    """
    Mixin that provides generic data insertion capabilities for SQLAlchemy models
    
    This mixin adds:
    - from_dict(): Create model instance from dictionary
    - to_dict(): Convert model instance to dictionary
    - create_from_dict(): Create and save model instance from dictionary
    - bulk_create_from_dicts(): Create multiple instances from list of dictionaries
    """
    
    @classmethod
    def from_dict(cls, data_dict, user_id=None, skip_fields=None):
        """
        Create a model instance from a dictionary
        
        Args:
            data_dict (dict): Dictionary containing model data
            user_id (int, optional): User ID for audit fields
            skip_fields (list, optional): Fields to skip during creation
            
        Returns:
            Model instance (not saved to database)
        """
        if skip_fields is None:
            skip_fields = []
        
        # Get model columns
        mapper = inspect(cls)
        columns = {c.key: c for c in mapper.columns}
        
        # Filter data to only include valid columns
        filtered_data = {}
        for key, value in data_dict.items():
            if key in columns and key not in skip_fields:
                # Handle special cases
                if key == 'password' and hasattr(cls, 'set_password'):
                    # Skip password field - will be handled by set_password
                    continue
                elif key in ['created_at', 'updated_at'] and value is None:
                    # Skip timestamp fields if None
                    continue
                else:
                    filtered_data[key] = value
        
        # Create instance
        instance = cls(**filtered_data)
        
        # Handle password if present
        if 'password' in data_dict and hasattr(instance, 'set_password'):
            instance.set_password(data_dict['password'])
        
        # Set audit fields if user_id provided
        if user_id is not None:
            if hasattr(instance, 'created_by_id') and not instance.created_by_id:
                instance.created_by_id = user_id
            if hasattr(instance, 'updated_by_id'):
                instance.updated_by_id = user_id
        
        return instance
    
    def to_dict(self, include_relationships=False, include_audit_fields=True):
        """
        Convert model instance to dictionary
        
        Args:
            include_relationships (bool): Whether to include relationship data
            include_audit_fields (bool): Whether to include audit fields
            
        Returns:
            dict: Dictionary representation of the model
        """
        result = {}
        
        # Get model columns
        mapper = inspect(self.__class__)
        
        for column in mapper.columns:
            value = getattr(self, column.key)
            
            # Skip audit fields if requested
            if not include_audit_fields and column.key in ['created_at', 'updated_at', 'created_by_id', 'updated_by_id']:
                continue
            
            # Handle datetime serialization
            if isinstance(value, datetime):
                result[column.key] = value.isoformat()
            else:
                result[column.key] = value
        
        # Include relationships if requested
        if include_relationships:
            for relationship in mapper.relationships:
                if relationship.key not in result:
                    related_obj = getattr(self, relationship.key)
                    if related_obj is None:
                        result[relationship.key] = None
                    elif hasattr(relationship.mapper.class_, 'to_dict'):
                        result[relationship.key] = related_obj.to_dict()
                    else:
                        result[relationship.key] = str(related_obj)
        
        return result
    
    @classmethod
    def create_from_dict(cls, data_dict, user_id=None, skip_fields=None, commit=True):
        """
        Create and save a model instance from dictionary
        
        Args:
            data_dict (dict): Dictionary containing model data
            user_id (int, optional): User ID for audit fields
            skip_fields (list, optional): Fields to skip during creation
            commit (bool): Whether to commit the transaction
            
        Returns:
            Model instance (saved to database)
        """
        instance = cls.from_dict(data_dict, user_id, skip_fields)
        
        try:
            db.session.add(instance)
            if commit:
                db.session.commit()
                logger.info(f"Created {cls.__name__}: {instance}")
            return instance
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating {cls.__name__}: {e}")
            raise
    
    @classmethod
    def bulk_create_from_dicts(cls, data_list, user_id=None, skip_fields=None, commit=True):
        """
        Create multiple model instances from list of dictionaries
        
        Args:
            data_list (list): List of dictionaries containing model data
            user_id (int, optional): User ID for audit fields
            skip_fields (list, optional): Fields to skip during creation
            commit (bool): Whether to commit the transaction
            
        Returns:
            list: List of created model instances
        """
        instances = []
        
        for data_dict in data_list:
            instance = cls.from_dict(data_dict, user_id, skip_fields)
            instances.append(instance)
            db.session.add(instance)
        
        try:
            if commit:
                db.session.commit()
                logger.info(f"Created {len(instances)} {cls.__name__} instances")
            return instances
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error bulk creating {cls.__name__}: {e}")
            raise
    
    @classmethod
    def find_or_create_from_dict(cls, data_dict, user_id=None, skip_fields=None, 
                                lookup_fields=None, commit=True):
        """
        Find existing instance or create new one from dictionary
        
        Args:
            data_dict (dict): Dictionary containing model data
            user_id (int, optional): User ID for audit fields
            skip_fields (list, optional): Fields to skip during creation
            lookup_fields (list, optional): Fields to use for lookup (default: unique fields)
            commit (bool): Whether to commit the transaction
            
        Returns:
            tuple: (instance, created) where created is boolean
        """
        if lookup_fields is None:
            # Try to find unique fields for lookup
            mapper = inspect(cls)
            lookup_fields = [c.key for c in mapper.columns if c.unique and c.key in data_dict]
        
        if not lookup_fields:
            # No unique fields found, create new instance
            return cls.create_from_dict(data_dict, user_id, skip_fields, commit), True
        
        # Build lookup query
        lookup_data = {field: data_dict[field] for field in lookup_fields if field in data_dict}
        if not lookup_data:
            # No lookup data available, create new instance
            return cls.create_from_dict(data_dict, user_id, skip_fields, commit), True
        
        # Try to find existing instance
        existing = cls.query.filter_by(**lookup_data).first()
        if existing:
            logger.info(f"Found existing {cls.__name__}: {existing}")
            return existing, False
        
        # Create new instance
        return cls.create_from_dict(data_dict, user_id, skip_fields, commit), True

