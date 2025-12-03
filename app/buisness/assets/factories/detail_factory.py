#!/usr/bin/env python3
"""
Base Detail Factory
Abstract base class for creating detail table rows
"""

from abc import ABC, abstractmethod
from app.logger import get_logger
from app import db
from pathlib import Path

logger = get_logger("asset_management.domain.assets.factories")

class DetailFactory(ABC):
    """
    Abstract base class for detail table row creation
    """
    
    # Centralized detail table registry
    DETAIL_TABLE_REGISTRY = {
        # Asset detail tables
        'purchase_info': {
            'is_asset_detail': True,
            'module_path': 'app.data.assets.asset_type_details.purchase_info',
            'class_name': 'PurchaseInfo'
        },
        'vehicle_registration': {
            'is_asset_detail': True,
            'module_path': 'app.data.assets.asset_type_details.vehicle_registration',
            'class_name': 'VehicleRegistration'
        },
        'toyota_warranty_receipt': {
            'is_asset_detail': True,
            'module_path': 'app.data.assets.asset_type_details.toyota_warranty_receipt',
            'class_name': 'ToyotaWarrantyReceipt'
        },
        'smog_record': {
            'is_asset_detail': True,
            'module_path': 'app.data.assets.asset_type_details.smog_record',
            'class_name': 'SmogRecord'
        },
        # Model detail tables
        'emissions_info': {
            'is_asset_detail': False,
            'module_path': 'app.data.assets.model_details.emissions_info',
            'class_name': 'EmissionsInfo'
        },
        'model_info': {
            'is_asset_detail': False,
            'module_path': 'app.data.assets.model_details.model_info',
            'class_name': 'ModelInfo'
        }
    }
    
    @classmethod
    def get_detail_table_class(cls, table_type):
        """
        Get the detail table class for a given table type
        
        Args:
            table_type (str): The detail table type (e.g., 'purchase_info')
            
        Returns:
            class: The detail table class
            
        Raises:
            ValueError: If the table type is not found in the registry
        """
        if table_type not in cls.DETAIL_TABLE_REGISTRY:
            raise ValueError(f"Unknown detail table type: {table_type}")
        
        registry_entry = cls.DETAIL_TABLE_REGISTRY[table_type]
        module_path = registry_entry['module_path']
        class_name = registry_entry['class_name']
        
        # Import the module and get the class
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)
    
    @classmethod
    def is_asset_detail(cls, table_type):
        """
        Check if a detail table type is an asset detail
        
        Args:
            table_type (str): The detail table type
            
        Returns:
            bool: True if it's an asset detail, False if it's a model detail
            
        Raises:
            ValueError: If the table type is not found in the registry
        """
        if table_type not in cls.DETAIL_TABLE_REGISTRY:
            raise ValueError(f"Unknown detail table type: {table_type}")
        
        return cls.DETAIL_TABLE_REGISTRY[table_type]['is_asset_detail']
    
    @classmethod
    def _create_single_detail_row(cls, config, detail_table_type, target_id, **kwargs):
        """
        Create a single detail table row based on configuration
        
        Args:
            config: The template configuration object
            detail_table_type (str): The type of detail table to create
            target_id (int): The ID of the target (asset_id or make_model_id)
            **kwargs: Additional keyword arguments
            
        Returns:
            bool: True if row was created, False if it already existed or creation failed
        """
        logger.debug(f"Creating detail row for {detail_table_type}")
        
        try:
            detail_table_class_path = cls.DETAIL_TABLE_REGISTRY.get(detail_table_type)
            if not detail_table_class_path:
                logger.warning(f"No detail table registry entry found for '{detail_table_type}'")
                return False
            
            # Import the detail table class
            module_path, class_name = detail_table_class_path['module_path'], detail_table_class_path['class_name']
            module = __import__(module_path, fromlist=[class_name])
            detail_table_class = getattr(module, class_name)
            
            # Check if row already exists (only for non-many_to_one types)
            # If many_to_one is True, always create (allow multiple records)
            many_to_one = getattr(config, 'many_to_one', False)
            
            if detail_table_class_path['is_asset_detail']:
                # For many_to_one=False, check if record already exists
                if not many_to_one:
                    existing_row = detail_table_class.query.filter_by(asset_id=target_id).first()
                    if existing_row:
                        logger.debug(f"Asset detail row already exists for asset {target_id}, skipping")
                        return False
                detail_row = detail_table_class(asset_id=target_id, **kwargs)
            else:
                # For many_to_one=False, check if record already exists
                if not many_to_one:
                    existing_row = detail_table_class.query.filter_by(make_model_id=target_id).first()
                    if existing_row:
                        logger.debug(f"Model detail row already exists for model {target_id}, skipping")
                        return False
                detail_row = detail_table_class(make_model_id=target_id, **kwargs)
            
            # Add to session (don't commit - let the main transaction handle it)
            db.session.add(detail_row)
            logger.debug(f"Created detail row: {detail_row}")
            return True
            
        except Exception as e:
            logger.debug(f"Error creating detail row for {detail_table_type}: {e}")
            return False
    
    @abstractmethod
    def create_detail_table_rows(cls, target, **kwargs):
        """
        Create detail table rows for the target
        
        Args:
            target: The target object (Asset or MakeModel)
            **kwargs: Additional keyword arguments
        """
        pass

