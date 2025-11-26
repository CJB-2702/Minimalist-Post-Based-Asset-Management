"""
Asset Detail Service
Presentation service for asset detail table data retrieval and formatting.

Handles:
- Query building and filtering for detail table list views
- Configuration retrieval for display
- Form option retrieval
- Data aggregation and grouping for presentation
"""

from typing import Dict, List, Optional, Tuple, Any
from flask import Request
from app.buisness.assets.asset_details.asset_details_struct import AssetDetailsStruct
from app.buisness.assets.model_details.model_details_struct import ModelDetailsStruct
from app.data.assets.detail_table_templates.asset_details_from_asset_type import AssetDetailTemplateByAssetType
from app.data.assets.detail_table_templates.asset_details_from_model_type import AssetDetailTemplateByModelType
from app.data.core.asset_info.asset import Asset
from app.data.core.asset_info.make_model import MakeModel
from app.services.assets.asset_detail_union_service import AssetDetailUnionService as AssetDetailsUnionService


class AssetDetailService:
    """
    Service for asset detail table presentation data.
    
    Provides methods for:
    - Building filtered detail table queries
    - Retrieving configurations
    - Formatting data for presentation
    - Grouping details by type for display
    """
    
    @staticmethod
    def get_detail_table_config(detail_type: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a detail table type.
        
        Args:
            detail_type: The detail table type (e.g., 'purchase_info')
            
        Returns:
            Configuration dictionary or None if not found
        """
        # Import here to avoid circular import
        from app.buisness.assets.detail_table_context import DetailTableContext
        return DetailTableContext.get_detail_table_config(detail_type)
    
    @staticmethod
    def get_asset_type_configs(asset_type_id: int) -> List:
        """
        Get asset detail table configurations for a specific asset type.
        
        Args:
            asset_type_id: The asset type ID
            
        Returns:
            List of AssetDetailTemplateByAssetType instances, or empty list
        """
        if asset_type_id:
            return AssetDetailTemplateByAssetType.query.filter_by(asset_type_id=asset_type_id).all()
        return []
    
    @staticmethod
    def get_model_type_configs(make_model_id: int) -> List:
        """
        Get asset detail table configurations for a specific make/model.
        
        Args:
            make_model_id: The make/model ID
            
        Returns:
            List of AssetDetailTemplateByModelType instances, or empty list
        """
        if make_model_id:
            return AssetDetailTemplateByModelType.query.filter_by(make_model_id=make_model_id).all()
        return []
    
    @staticmethod
    def list_detail_records(
        detail_type: str,
        asset_id: Optional[int] = None,
        model_id: Optional[int] = None
    ) -> List:
        """
        List all detail records of a specific type, optionally filtered.
        
        Args:
            detail_type: The detail table type
            asset_id: Optional asset ID to filter by
            model_id: Optional model ID to filter by (filters through asset relationship)
            
        Returns:
            List of detail records
        """
        # Import here to avoid circular import
        from app.buisness.assets.detail_table_context import DetailTableContext
        records = DetailTableContext.list_all_details(detail_type, asset_id=asset_id)
        
        # Apply model filter if needed
        if model_id:
            records = [r for r in records if r.asset and r.asset.make_model_id == model_id]
        
        return records
    
    @staticmethod
    def get_detail_record(detail_type: str, record_id: int) -> Optional[Any]:
        """
        Get a detail record by ID.
        
        Args:
            detail_type: The detail table type
            record_id: The ID of the record
            
        Returns:
            Detail record instance or None if not found
        """
        # Import here to avoid circular import
        from app.buisness.assets.detail_table_context import DetailTableContext
        return DetailTableContext.get_detail_by_id(detail_type, record_id)
    
    @staticmethod
    def get_all_details_for_asset(asset_id: int) -> List[Dict[str, Any]]:
        """
        Get all detail records for a specific asset across all detail table types.
        
        Args:
            asset_id: The ID of the asset
            
        Returns:
            List of dictionaries containing detail records with metadata
        """
        return AssetDetailsUnionService.get_all_details_for_asset(asset_id)
    
    @staticmethod
    def get_details_by_type_for_asset(asset_id: int, detail_type: str) -> List:
        """
        Get detail records of a specific type for an asset.
        
        Args:
            asset_id: The ID of the asset
            detail_type: The detail table type
            
        Returns:
            List of detail records of the specified type
        """
        # Import here to avoid circular import
        from app.buisness.assets.detail_table_context import DetailTableContext
        return DetailTableContext.get_details_by_type_for_asset(asset_id, detail_type)
    
    @staticmethod
    def get_asset_details_by_type(asset_id: int) -> Dict[str, List]:
        """
        Get asset detail records grouped by detail table type.
        
        Presentation-specific method for grouping details for display.
        
        Args:
            asset_id: The ID of the asset
            
        Returns:
            Dictionary mapping table names to lists of detail records
        """
        struct = AssetDetailsStruct(asset_id)
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
    
    @staticmethod
    def get_model_details_by_type(asset_id: int) -> Dict[str, List]:
        """
        Get model detail records grouped by detail table type for an asset's make_model.
        
        Presentation-specific method for grouping details for display.
        
        Args:
            asset_id: The ID of the asset (uses asset's make_model_id)
            
        Returns:
            Dictionary mapping table names to lists of detail records, or empty dict if no make_model
        """
        # Get asset to access make_model_id
        asset = Asset.query.get_or_404(asset_id)
        
        if not asset.make_model_id:
            return {}
        
        struct = ModelDetailsStruct(asset.make_model_id)
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
    
    @staticmethod
    def get_list_data(detail_type: str, request: Request) -> Tuple[List, Dict]:
        """
        Get filtered detail records for list view with form options.
        
        Args:
            detail_type: The detail table type
            request: Flask request object
            
        Returns:
            Tuple of (records list, form options dict)
        """
        # Get filter parameters
        asset_id_filter = request.args.get('asset_id', type=int)
        model_id_filter = request.args.get('model_id', type=int)
        
        # Get records with filters
        records = AssetDetailService.list_detail_records(
            detail_type=detail_type,
            asset_id=asset_id_filter,
            model_id=model_id_filter
        )
        
        # Get form options
        form_options = AssetDetailService.get_form_options()
        
        return records, form_options
    
    @staticmethod
    def get_form_options() -> Dict:
        """
        Get form options for detail table forms.
        
        Returns:
            Dictionary with asset_options, model_options, assets, and make_models
        """
        assets = Asset.query.all()
        make_models = MakeModel.query.all()
        
        return {
            'asset_options': [(a.id, f"{a.name} ({a.serial_number})") for a in assets],
            'model_options': [(m.id, f"{m.make} {m.model} {m.year or ''}") for m in make_models],
            'assets': assets,  # Raw list for flexibility
            'make_models': make_models
        }

