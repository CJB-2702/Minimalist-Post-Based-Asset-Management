"""
Model Detail Service
Presentation service for model detail table data retrieval and formatting.

Handles:
- Query building and filtering for model detail table list views
- Configuration retrieval for display
- Data retrieval for presentation
"""

from typing import Dict, List, Optional, Any
from app.data.assets.model_details.emissions_info import EmissionsInfo
from app.data.assets.model_details.model_info import ModelInfo
from app.data.core.asset_info.make_model import MakeModel


class ModelDetailService:
    """
    Service for model detail table presentation data.
    
    Provides methods for:
    - Building filtered model detail table queries
    - Retrieving configurations
    - Formatting data for presentation
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
        # Import here to avoid circular import
        from app.buisness.assets.model_detail_context import ModelDetailContext
        return ModelDetailContext.get_model_detail_table_config(detail_type)
    
    @staticmethod
    def list_detail_records(detail_type: str) -> List:
        """
        List all detail records of a specific type.
        
        Args:
            detail_type: The detail table type
            
        Returns:
            List of detail records
        """
        # Import here to avoid circular import
        from app.buisness.assets.model_detail_context import ModelDetailContext
        return ModelDetailContext.list_all_details(detail_type)
    
    @staticmethod
    def get_detail_record(detail_type: str, record_id: int) -> Optional[Any]:
        """
        Get a model detail record by ID.
        
        Args:
            detail_type: The detail table type
            record_id: The ID of the record
            
        Returns:
            Detail record instance or None if not found
        """
        # Import here to avoid circular import
        from app.buisness.assets.model_detail_context import ModelDetailContext
        return ModelDetailContext.get_detail_by_id(detail_type, record_id)
    
    @staticmethod
    def _get_detail_table_model(detail_type: str):
        """Helper to get model class for a detail type"""
        # Import here to avoid circular import
        from app.buisness.assets.model_detail_context import ModelDetailContext
        return ModelDetailContext.get_model_detail_table_model(detail_type)
    
    @staticmethod
    def get_detail_for_model(detail_type: str, make_model_id: int) -> Optional[Any]:
        """
        Get detail record for a specific model and detail type.
        
        Used by legacy routes that need a single detail record for a model.
        
        Args:
            detail_type: The detail table type ('emissions_info' or 'model_info')
            make_model_id: The make/model ID
            
        Returns:
            Detail record instance or None if not found
        """
        model = ModelDetailService._get_detail_table_model(detail_type)
        if model:
            return model.query.filter_by(make_model_id=make_model_id).first()
        return None
    
    @staticmethod
    def get_list_data(detail_type: str) -> List:
        """
        Get all detail records for list view.
        
        Args:
            detail_type: The detail table type
            
        Returns:
            List of detail records
        """
        return ModelDetailService.list_detail_records(detail_type)

