"""
Detail Table Context
Provides a clean interface for managing asset detail tables.
Handles CRUD operations and data access patterns for detail tables.
"""

from typing import List, Dict, Any, Optional, Union, Type
from app import db
from app.data.core.asset_info.asset import Asset
from app.data.assets.asset_details.purchase_info import PurchaseInfo
from app.data.assets.asset_details.vehicle_registration import VehicleRegistration
from app.data.assets.asset_details.toyota_warranty_receipt import ToyotaWarrantyReceipt
from app.services.assets.asset_detail_union_service import AssetDetailUnionService


# Detail table configuration mapping
DETAIL_TABLE_MODELS = {
    'purchase_info': PurchaseInfo,
    'vehicle_registration': VehicleRegistration,
    'toyota_warranty_receipt': ToyotaWarrantyReceipt,
}

DETAIL_TABLE_CONFIG = {
    'purchase_info': {
        'model': PurchaseInfo,
        'name': 'Purchase Information',
        'icon': 'bi-cart',
        'fields': ['purchase_date', 'purchase_price', 'purchase_vendor', 'purchase_order_number', 'warranty_start_date', 'warranty_end_date', 'purchase_notes', 'event_id']
    },
    'vehicle_registration': {
        'model': VehicleRegistration,
        'name': 'Vehicle Registration',
        'icon': 'bi-car-front',
        'fields': ['license_plate', 'registration_number', 'registration_expiry', 'vin_number', 'state_registered', 'registration_status', 'insurance_provider', 'insurance_policy_number', 'insurance_expiry']
    },
    'toyota_warranty_receipt': {
        'model': ToyotaWarrantyReceipt,
        'name': 'Toyota Warranty Receipt',
        'icon': 'bi-shield-check',
        'fields': ['warranty_receipt_number', 'warranty_type', 'warranty_mileage_limit', 'warranty_time_limit_months', 'dealer_name', 'dealer_contact', 'dealer_phone', 'dealer_email', 'service_history', 'warranty_claims']
    }
}


class DetailTableContext:
    """
    Context manager for asset detail table operations.
    
    Provides a clean interface for:
    - Accessing detail table configurations
    - Querying detail records by asset
    - CRUD operations on detail tables
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
        return DETAIL_TABLE_CONFIG.get(detail_type)
    
    @staticmethod
    def get_detail_table_model(detail_type: str) -> Optional[Type]:
        """
        Get the model class for a detail table type.
        
        Args:
            detail_type: The detail table type
            
        Returns:
            Model class or None if not found
        """
        return DETAIL_TABLE_MODELS.get(detail_type)
    
    @staticmethod
    def get_all_details_for_asset(asset_id: int) -> List[Dict[str, Any]]:
        """
        Get all detail records for a specific asset across all detail table types.
        
        Args:
            asset_id: The ID of the asset
            
        Returns:
            List of dictionaries containing detail records with metadata
        """
        return AssetDetailUnionService.get_all_details_for_asset(asset_id)
    
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
        model = DetailTableContext.get_detail_table_model(detail_type)
        if model:
            return model.query.filter_by(asset_id=asset_id).all()
        return []
    
    @staticmethod
    def create_detail_record(detail_type: str, asset_id: int, user_id: int, **data) -> Any:
        """
        Create a new detail record.
        
        Args:
            detail_type: The detail table type
            asset_id: The ID of the asset
            user_id: The ID of the user creating the record
            **data: Field values for the detail record
            
        Returns:
            Created detail record instance
            
        Raises:
            ValueError: If detail_type is invalid
        """
        model = DetailTableContext.get_detail_table_model(detail_type)
        if not model:
            raise ValueError(f"Invalid detail table type: {detail_type}")
        
        # Add required fields
        data['asset_id'] = asset_id
        data['created_by_id'] = user_id
        data['updated_by_id'] = user_id
        
        record = model(**data)
        db.session.add(record)
        return record
    
    @staticmethod
    def update_detail_record(record: Any, user_id: int, **data) -> Any:
        """
        Update an existing detail record.
        
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
        Delete a detail record.
        
        Args:
            record: The detail record to delete
        """
        db.session.delete(record)
    
    @staticmethod
    def get_detail_by_id(detail_type: str, record_id: int) -> Optional[Any]:
        """
        Get a detail record by ID.
        
        Args:
            detail_type: The detail table type
            record_id: The ID of the record
            
        Returns:
            Detail record instance or None if not found
        """
        model = DetailTableContext.get_detail_table_model(detail_type)
        if model:
            return model.query.get(record_id)
        return None
    
    @staticmethod
    def list_all_details(detail_type: str, asset_id: Optional[int] = None) -> List:
        """
        List all detail records of a specific type, optionally filtered by asset.
        
        Args:
            detail_type: The detail table type
            asset_id: Optional asset ID to filter by
            
        Returns:
            List of detail records
        """
        model = DetailTableContext.get_detail_table_model(detail_type)
        if not model:
            return []
        
        query = model.query
        if asset_id:
            query = query.filter_by(asset_id=asset_id)
        
        return query.all()

