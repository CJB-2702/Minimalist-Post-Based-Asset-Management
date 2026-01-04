"""
Asset Details Context
Extends AssetContext with detail table management functionality.

Focus: Managing detail relationships (asset_details and model_details)
"""

from typing import List, Dict, Any, Optional, Union
from app.data.core.asset_info.asset import Asset
from app.buisness.core.asset_context import AssetContext
from app.buisness.assets.asset_type_details.asset_details_struct import AssetDetailsStruct
from app.buisness.assets.model_details.model_details_struct import ModelDetailsStruct
from app.data.assets.detail_table_templates.asset_details_from_asset_type import AssetDetailTemplateByAssetType
from app.data.assets.detail_table_templates.asset_details_from_model_type import AssetDetailTemplateByModelType


class AssetDetailsContext(AssetContext):
    """
    Extended context manager for asset operations including detail tables.
    
    Extends AssetContext with:
    - Asset detail table management (purchase_info, vehicle_registration, etc.)
    - Model detail table access (for asset's make_model)
    - Detail table configurations
    - Detail grouping and aggregation
    
    Primary goal: Manage detail relationships
    """
    
    def __init__(self, asset: Union[Asset, int]):
        """
        Initialize AssetDetailsContext with an Asset instance or asset ID.
        
        Args:
            asset: Asset instance or asset ID
        """
        super().__init__(asset)
        
        # Cache for lazy loading detail data
        self._asset_details_struct = None
        self._asset_details = None  # List format for backward compatibility
        self._model_details_struct = None
        self._model_details = None  # List format for backward compatibility
    
    @property
    def asset_details_struct(self) -> AssetDetailsStruct:
        """
        Get the structured asset details for this asset.
        
        Returns:
            AssetDetailsStruct instance with all detail types as attributes
        """
        if self._asset_details_struct is None:
            self._asset_details_struct = AssetDetailsStruct(self._asset_id)
        return self._asset_details_struct
    
    @property
    def asset_details(self) -> List[Dict[str, Any]]:
        """
        Get all asset detail records for this asset as a list of dictionaries.
        
        Uses AssetDetailsStruct internally for structured access.
        
        Returns:
            List of dictionaries containing asset detail records with metadata
        """
        if self._asset_details is None:
            # Use struct internally, convert to list format for backward compatibility
            struct = self.asset_details_struct
            details_dict = struct.asdict()
            
            self._asset_details = []
            for class_name, records in details_dict.items():
                # records is now a list (even if empty)
                if records:
                    for record in records:
                        # Extract common fields
                        detail_data = {
                            'id': record.id,
                            'all_asset_detail_id': record.all_asset_detail_id,
                            'asset_id': record.asset_id,
                            'created_at': record.created_at,
                            'created_by_id': record.created_by_id,
                            'updated_at': record.updated_at,
                            'updated_by_id': record.updated_by_id,
                            'table_name': record.__tablename__,
                            'table_class': class_name,
                            'record': record
                        }
                        self._asset_details.append(detail_data)
            
            # Sort by global ID for consistent ordering
            self._asset_details = sorted(self._asset_details, key=lambda x: x['all_asset_detail_id'])
        
        return self._asset_details
    
    @property
    def model_details(self) -> List[Dict[str, Any]]:
        """
        Get all model detail records for this asset's make_model (if exists) as a list of dictionaries.
        
        Uses ModelDetailsStruct internally for structured access.
        
        Returns:
            List of dictionaries containing model detail records with metadata, or empty list if no make_model
        """
        if self._model_details is None:
            if self._asset.make_model_id:
                # Use struct internally, convert to list format for backward compatibility
                struct = ModelDetailsStruct(self._asset.make_model_id)
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
            else:
                self._model_details = []
        return self._model_details
    
    @property
    def all_details(self) -> List[Dict[str, Any]]:
        """
        Get all detail records (both asset and model details) for this asset.
        
        Returns:
            Combined list of all detail records
        """
        return self.asset_details + self.model_details
    
    @property
    def asset_type_configs(self) -> List:
        """
        Get asset detail table configurations for this asset's asset type.
        
        Returns:
            List of AssetDetailTemplateByAssetType instances, or empty list
        """
        if self._asset.asset_type_id:
            return AssetDetailTemplateByAssetType.query.filter_by(asset_type_id=self._asset.asset_type_id).all()
        return []
    
    @property
    def model_type_configs(self) -> List:
        """
        Get asset detail table configurations for this asset's make_model.
        
        Returns:
            List of AssetDetailTemplateByModelType instances, or empty list
        """
        if self._asset.make_model_id:
            return AssetDetailTemplateByModelType.query.filter_by(make_model_id=self._asset.make_model_id).all()
        return []
    
    def get_asset_details_by_type(self) -> Dict[str, List]:
        """
        Get asset detail records grouped by detail table type (e.g., 'purchase_info', 'vehicle_registration').
        
        Uses AssetDetailsStruct internally for structured access.
        
        Returns:
            Dictionary mapping table class names (lowercase) to lists of detail records
        """
        struct = self.asset_details_struct
        details_dict = struct.asdict()
        
        details_by_type = {}
        for class_name, records in details_dict.items():
            # records is now a list
            if records:
                # Get table name from first record
                key = records[0].__tablename__
                # Add all records for this type
                details_by_type[key] = records
        
        return details_by_type
    
    def get_model_details_by_type(self) -> Dict[str, List]:
        """
        Get model detail records grouped by detail table type.
        
        Uses ModelDetailsStruct internally for structured access.
        
        Returns:
            Dictionary mapping table class names (lowercase) to lists of detail records
        """
        if not self._asset.make_model_id:
            return {}
        
        struct = ModelDetailsStruct(self._asset.make_model_id)
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
        Get total count of all detail records (both asset and model details).
        
        Returns:
            Total number of detail records
        """
        # Count all records from structs (now returns lists)
        asset_struct = self.asset_details_struct
        asset_detail_count = sum(len(records) for records in asset_struct.asdict().values() if records)
        
        model_detail_count = 0
        if self._asset.make_model_id:
            model_struct = ModelDetailsStruct(self._asset.make_model_id)
            # Model details are single objects (not lists), so count non-None values
            model_detail_count = sum(1 for record in model_struct.asdict().values() if record is not None)
        
        return asset_detail_count + model_detail_count
    
    def refresh(self):
        """Refresh cached data from database"""
        super().refresh()  # Refresh core context cache
        self._asset_details_struct = None
        self._asset_details = None
        self._model_details_struct = None
        self._model_details = None
    
    def __repr__(self):
        return f'<AssetDetailsContext asset_id={self._asset_id} asset_details={len(self.asset_details)} model_details={len(self.model_details)}>'

