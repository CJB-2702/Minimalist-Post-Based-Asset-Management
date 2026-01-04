"""
Model Detail Context
Provides a clean interface for managing model detail tables.
Handles CRUD operations and data access patterns for model detail tables.
"""

from typing import List, Dict, Any, Optional, Union, Type
from app import db
from app.data.core.asset_info.make_model import MakeModel
from app.data.assets.model_details.emissions_info import EmissionsInfo
from app.data.assets.model_details.model_info import ModelInfo
from app.services.assets.model_detail_union_service import ModelDetailUnionService


# Model detail table configuration mapping
MODEL_DETAIL_TABLE_MODELS = {
    'emissions_info': EmissionsInfo,
    'model_info': ModelInfo,
}

MODEL_DETAIL_TABLE_CONFIG = {
    'emissions_info': {
        'model': EmissionsInfo,
        'name': 'Emissions Information',
        'icon': 'bi-cloud',
        'fields': ['emissions_standard', 'emissions_rating', 'fuel_type', 'mpg_city', 'mpg_highway', 'mpg_combined', 'co2_emissions']
    },
    'model_info': {
        'model': ModelInfo,
        'name': 'Model Information',
        'icon': 'bi-info-circle',
        'fields': ['model_year', 'body_style', 'engine_type', 'transmission_type', 'drivetrain', 'seating_capacity', 'cargo_capacity', 'towing_capacity']
    }
}


class ModelDetailContext:
    """
    Context manager for model detail table operations.
    
    Provides a clean interface for:
    - Accessing model detail table configurations
    - Querying detail records by make_model
    - CRUD operations on model detail tables
    """
    
    @staticmethod
    def get_model_detail_table_config(detail_type: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a model detail table type.
        
        Args:
            detail_type: The detail table type (e.g., 'emissions_info')
            
        Returns:
            Configuration dictionary or None if not found
        """
        return MODEL_DETAIL_TABLE_CONFIG.get(detail_type)
    
    @staticmethod
    def get_model_detail_table_model(detail_type: str) -> Optional[Type]:
        """
        Get the model class for a model detail table type.
        
        Args:
            detail_type: The detail table type
            
        Returns:
            Model class or None if not found
        """
        return MODEL_DETAIL_TABLE_MODELS.get(detail_type)
    
    @staticmethod
    def get_all_details_for_model(make_model_id: int) -> List[Dict[str, Any]]:
        """
        Get all detail records for a specific make_model across all detail table types.
        
        Args:
            make_model_id: The ID of the make_model
            
        Returns:
            List of dictionaries containing detail records with metadata
        """
        return ModelDetailUnionService.get_all_details_for_model(make_model_id)
    
    @staticmethod
    def get_details_by_type_for_model(make_model_id: int, detail_type: str) -> List:
        """
        Get detail records of a specific type for a make_model.
        
        Args:
            make_model_id: The ID of the make_model
            detail_type: The detail table type
            
        Returns:
            List of detail records of the specified type
        """
        model = ModelDetailContext.get_model_detail_table_model(detail_type)
        if model:
            return model.query.filter_by(make_model_id=make_model_id).all()
        return []
    
    @staticmethod
    def create_detail_record(detail_type: str, make_model_id: int, user_id: int, **data) -> Any:
        """
        Create a new model detail record.
        
        Args:
            detail_type: The detail table type
            make_model_id: The ID of the make_model
            user_id: The ID of the user creating the record
            **data: Field values for the detail record
            
        Returns:
            Created detail record instance
            
        Raises:
            ValueError: If detail_type is invalid
        """
        model = ModelDetailContext.get_model_detail_table_model(detail_type)
        if not model:
            raise ValueError(f"Invalid model detail table type: {detail_type}")
        
        # Add required fields
        data['make_model_id'] = make_model_id
        data['created_by_id'] = user_id
        data['updated_by_id'] = user_id
        
        record = model(**data)
        db.session.add(record)
        return record
    
    @staticmethod
    def update_detail_record(record: Any, user_id: int, **data) -> Any:
        """
        Update an existing model detail record.
        
        Args:
            record: The detail record to update
            user_id: The ID of the user updating the record
            **data: Field values to update
            
        Returns:
            Updated detail record instance
        """
        for key, value in data.items():
            if hasattr(record, key):
                setattr(record, key, value)
        
        record.updated_by_id = user_id
        return record
    
    @staticmethod
    def delete_detail_record(record: Any):
        """
        Delete a model detail record.
        
        Args:
            record: The detail record to delete
        """
        db.session.delete(record)
    
    @staticmethod
    def get_detail_by_id(detail_type: str, record_id: int) -> Optional[Any]:
        """
        Get a model detail record by ID.
        
        Args:
            detail_type: The detail table type
            record_id: The ID of the record
            
        Returns:
            Detail record instance or None if not found
        """
        model = ModelDetailContext.get_model_detail_table_model(detail_type)
        if model:
            return model.query.get(record_id)
        return None
    
    @staticmethod
    def list_all_details(detail_type: str, make_model_id: Optional[int] = None) -> List:
        """
        List all model detail records of a specific type, optionally filtered by make_model.
        
        Args:
            detail_type: The detail table type
            make_model_id: Optional make_model ID to filter by
            
        Returns:
            List of detail records with make_model relationship eagerly loaded
        """
        from sqlalchemy.orm import joinedload
        
        model = ModelDetailContext.get_model_detail_table_model(detail_type)
        if not model:
            return []
        
        # Eagerly load the make_model relationship to avoid N+1 queries
        # Use class-bound attribute instead of string for SQLAlchemy 2.0+ compatibility
        query = model.query.options(joinedload(model.make_model))
        if make_model_id:
            query = query.filter_by(make_model_id=make_model_id)
        
        return query.all()

