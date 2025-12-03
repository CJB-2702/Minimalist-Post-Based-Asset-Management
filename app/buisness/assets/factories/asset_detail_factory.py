#!/usr/bin/env python3
"""
Asset Detail Factory
Factory class for creating asset detail table rows
"""

from .detail_factory import DetailFactory
from app.logger import get_logger
from app import db

logger = get_logger("asset_management.domain.assets.factories")

class AssetDetailFactory(DetailFactory):
    """
    Factory class for creating asset detail table rows
    """
    
    @classmethod
    def create_detail_table_rows(cls, asset):
        """
        Create detail table rows for an asset based on asset type and model type configurations
        
        Args:
            asset: The Asset object to create detail rows for
        """
        logger.debug(f"AssetDetailFactory.create_detail_table_rows called for asset {asset.id}")
        
        try:
            # Get the asset creation event
            from app.data.core.event_info.event import Event
            creation_event = Event.query.filter_by(
                asset_id=asset.id,
                event_type='Asset Created'
            ).order_by(Event.timestamp.asc()).first()
            
            event_id = creation_event.id if creation_event else None
            if event_id:
                logger.debug(f"Found asset creation event {event_id} for asset {asset.id}")
            else:
                logger.warning(f"No creation event found for asset {asset.id}")
            
            # Create asset detail rows based on asset type
            asset_type_id = asset.asset_type_id
            if asset_type_id:
                logger.debug(f"Creating asset type detail rows for asset type: {asset_type_id}")
                cls._create_asset_type_detail_rows(asset, asset_type_id, event_id=event_id)
            
            # Create asset detail rows based on model type
            if asset.make_model_id:
                logger.debug(f"Creating model type detail rows for make_model: {asset.make_model_id}")
                cls._create_model_type_detail_rows(asset, asset.make_model_id, event_id=event_id)
                
        except Exception as e:
            logger.debug(f"Error creating detail table rows for asset {asset.id}: {e}")
    
    @classmethod
    def _create_asset_type_detail_rows(cls, asset, asset_type_id, event_id=None):
        """
        Create detail table rows based on asset type configurations
        
        Args:
            asset: The Asset object
            asset_type_id (int): The asset type ID
            event_id (int, optional): The asset creation event ID
        """
        try:
            from app.data.assets.detail_table_templates.asset_details_from_asset_type import AssetDetailTemplateByAssetType
            
            # Get all detail table configurations for this asset type
            detail_configs = AssetDetailTemplateByAssetType.get_detail_table_types_for_asset_type(asset_type_id)
            logger.debug(f"Found {len(detail_configs)} asset type detail configurations")

            for config in detail_configs:
                many_to_one = getattr(config, 'many_to_one', False)
                logger.debug(f"Creating asset type detail row for {config.detail_table_type} (many_to_one={many_to_one})")
                cls._create_single_detail_row(
                    config=config,
                    detail_table_type=config.detail_table_type,
                    target_id=asset.id,
                    event_id=event_id
                )
                
        except Exception as e:
            logger.debug(f"Error creating asset type detail rows for asset {asset.id}: {e}")
    
    @classmethod
    def _create_model_type_detail_rows(cls, asset, make_model_id, event_id=None):
        """
        Create detail table rows based on model type configurations
        
        Args:
            asset: The Asset object
            make_model_id (int): The make model ID
            event_id (int, optional): The asset creation event ID
        """
        try:
            from app.data.assets.detail_table_templates.asset_details_from_model_type import AssetDetailTemplateByModelType
            
            # Get all detail table configurations for this model type
            detail_configs = AssetDetailTemplateByModelType.get_detail_table_types_for_model_type(make_model_id)
            logger.debug(f"Found {len(detail_configs)} model type detail configurations")

            for config in detail_configs:
                many_to_one = getattr(config, 'many_to_one', False)
                logger.debug(f"Creating model type detail row for {config.detail_table_type} (many_to_one={many_to_one})")
                cls._create_single_detail_row(
                    config=config,
                    detail_table_type=config.detail_table_type,
                    target_id=asset.id,
                    event_id=event_id
                )
                
        except Exception as e:
            logger.debug(f"Error creating model type detail rows for asset {asset.id}: {e}")

