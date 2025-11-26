"""
MakeModel Details Context
Extends MakeModelContext with detail table management functionality.

Focus: Managing model detail relationships
"""

from typing import List, Dict, Any, Optional, Union
from app.data.core.asset_info.make_model import MakeModel
from app.buisness.core.make_model_context import MakeModelContext
from app.buisness.assets.model_details.model_details_struct import ModelDetailsStruct


class MakeModelDetailsContext(MakeModelContext):
    """
    Extended context manager for make/model operations including detail tables.
    
    Extends MakeModelContext with:
    - Model detail table management (emissions_info, model_info, etc.)
    - Detail table configurations
    - Detail grouping and aggregation
    
    Primary goal: Manage model detail relationships
    """
    
    def __init__(self, model: Union[MakeModel, int]):
        """
        Initialize MakeModelDetailsContext with a MakeModel instance or model ID.
        
        Args:
            model: MakeModel instance or model ID
        """
        super().__init__(model)
        
        # Cache for lazy loading detail data
        self._model_details_struct = None
        self._model_details = None  # List format for backward compatibility
    
    @property
    def model_details_struct(self) -> ModelDetailsStruct:
        """
        Get the structured model details for this model.
        
        Returns:
            ModelDetailsStruct instance with all detail types as attributes
        """
        if self._model_details_struct is None:
            self._model_details_struct = ModelDetailsStruct(self._model_id)
        return self._model_details_struct
    
    @property
    def model_details(self) -> List[Dict[str, Any]]:
        """
        Get all model detail records for this model as a list of dictionaries.
        
        Uses ModelDetailsStruct internally for structured access.
        
        Returns:
            List of dictionaries containing model detail records with metadata
        """
        if self._model_details is None:
            # Use struct internally, convert to list format for backward compatibility
            struct = self.model_details_struct
            details_dict = struct.asdict()
            
            self._model_details = []
            for class_name, record in details_dict.items():
                if record is not None:
                    # Extract common fields
                    detail_data = {
                        'id': record.id,
                        'all_model_detail_id': record.all_model_detail_id,
                        'make_model_id': record.make_model_id,
                        'created_at': record.created_at,
                        'created_by_id': record.created_by_id,
                        'updated_at': record.updated_at,
                        'updated_by_id': record.updated_by_id,
                        'table_name': record.__tablename__,
                        'table_class': class_name,
                        'record': record
                    }
                    self._model_details.append(detail_data)
            
            # Sort by global ID for consistent ordering
            self._model_details = sorted(self._model_details, key=lambda x: x['all_model_detail_id'])
        
        return self._model_details
    
    def get_model_details_by_type(self) -> Dict[str, List]:
        """
        Get model detail records grouped by detail table type.
        
        Uses ModelDetailsStruct internally for structured access.
        
        Returns:
            Dictionary mapping table class names to lists of detail records
        """
        struct = self.model_details_struct
        details_dict = struct.asdict()
        
        details_by_type = {}
        for class_name, record in details_dict.items():
            if record is not None:
                # Use table name as key
                key = record.__tablename__
                if key not in details_by_type:
                    details_by_type[key] = []
                details_by_type[key].append(record)
        
        return details_by_type
    
    @property
    def detail_count(self) -> int:
        """
        Get total count of all model detail records.
        
        Returns:
            Total number of detail records
        """
        # Count non-None records from struct
        struct = self.model_details_struct
        return sum(1 for record in struct.asdict().values() if record is not None)
    
    def refresh(self):
        """Refresh cached data from database"""
        super().refresh()  # Refresh core context cache
        self._model_details_struct = None
        self._model_details = None
    
    def __repr__(self):
        return f'<MakeModelDetailsContext model_id={self._model_id} model_details={len(self.model_details)} asset_count={self.asset_count}>'
