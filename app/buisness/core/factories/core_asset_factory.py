"""
Core Asset Factory
Handles basic asset creation with event creation.

This factory provides the minimum functionality needed for asset creation:
- Validation
- Asset creation
- Event creation

Detail table creation is handled by AssetDetailsFactory in the assets module.
"""

from typing import Optional, Dict, Any
from app.buisness.core.factories.asset_factory_base import AssetFactoryBase
from app.data.core.asset_info.asset import Asset
from app.data.core.event_info.event import Event
from app import db
from app.logger import get_logger

logger = get_logger("asset_management.buisness.core")


class CoreAssetFactory(AssetFactoryBase):
    """Core asset factory - handles basic asset creation and event creation"""
    
    def create_asset(
        self, 
        created_by_id: Optional[int] = None, 
        commit: bool = True, 
        enable_detail_insertion: bool = True,  # Ignored in core factory
        **kwargs
    ) -> Asset:
        """
        Create asset with basic operations (validation, event creation)
        
        Note: enable_detail_insertion is accepted for API compatibility but
        is ignored in the core factory. Use AssetDetailsFactory for detail insertion.
        """
        # Validate required fields
        if 'name' not in kwargs:
            raise ValueError("Asset name is required")
        if 'serial_number' not in kwargs:
            raise ValueError("Asset serial number is required")
        
        # Check for duplicate serial number
        existing_asset = Asset.query.filter_by(serial_number=kwargs['serial_number']).first()
        if existing_asset:
            raise ValueError(f"Asset with serial number '{kwargs['serial_number']}' already exists")
        
        # Set audit fields
        if created_by_id:
            kwargs['created_by_id'] = created_by_id
            kwargs['updated_by_id'] = created_by_id
        
        # Create asset
        asset = Asset(**kwargs)
        db.session.add(asset)
        
        # Flush to get ID before creating event
        db.session.flush()
        
        # Create creation event (business logic)
        self._create_creation_event(asset, created_by_id)
        
        # Commit if requested
        if commit:
            db.session.commit()
            logger.info(f"Asset created: {asset.name} (ID: {asset.id})")
        else:
            logger.info(f"Asset staged: {asset.name} (ID: {asset.id}, not committed)")
        
        return asset
    
    def create_asset_from_dict(
        self,
        asset_data: Dict[str, Any],
        created_by_id: Optional[int] = None,
        commit: bool = True,
        lookup_fields: Optional[list] = None
    ) -> tuple[Asset, bool]:
        """Create asset from dictionary with optional find_or_create"""
        if lookup_fields:
            query_filters = {field: asset_data.get(field) for field in lookup_fields if field in asset_data}
            existing_asset = Asset.query.filter_by(**query_filters).first()
            if existing_asset:
                return existing_asset, False
        
        asset = self.create_asset(created_by_id=created_by_id, commit=commit, **asset_data)
        return asset, True
    
    def _create_creation_event(self, asset: Asset, user_id: Optional[int]):
        """Create asset creation event"""
        event = Event(
            event_type='Asset Created',
            description=f"Asset '{asset.name}' ({asset.serial_number}) was created",
            user_id=user_id,
            asset_id=asset.id,
            major_location_id=asset.major_location_id
        )
        db.session.add(event)
    
    def get_factory_type(self) -> str:
        """Return factory type identifier"""
        return "core"

