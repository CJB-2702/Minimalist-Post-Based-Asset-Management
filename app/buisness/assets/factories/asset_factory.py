"""
Asset Details Factory
Extended factory that adds detail table creation to asset creation.

This factory extends CoreAssetFactory to provide detail table creation
functionality. It delegates to AssetDetailFactory for the actual detail creation.
"""

from typing import Optional, Dict, Any
from app.buisness.core.factories.core_asset_factory import CoreAssetFactory
from app.data.core.asset_info.asset import Asset
from app.logger import get_logger

logger = get_logger("asset_management.buisness.assets")


class AssetDetailsFactory(CoreAssetFactory):
    """Extended factory that adds detail table creation"""
    
    def create_asset(
        self, 
        created_by_id: Optional[int] = None, 
        commit: bool = True, 
        enable_detail_insertion: bool = True,
        **kwargs
    ) -> Asset:
        """
        Create asset with detail table creation if enabled
        
        This method:
        1. Uses parent factory to create asset and event
        2. Conditionally creates detail table rows if enabled
        3. Commits the transaction
        """
        # Use parent to create asset and event
        asset = super().create_asset(
            created_by_id=created_by_id,
            commit=False,  # Don't commit yet, we may add details
            enable_detail_insertion=enable_detail_insertion,
            **kwargs
        )
        
        # Create detail rows if enabled
        if enable_detail_insertion:
            self._create_detail_rows(asset)
        
        # Now commit if requested
        if commit:
            from app import db
            db.session.commit()
            logger.info(f"Asset with details created: {asset.name} (ID: {asset.id})")
        
        return asset
    

    def create_asset_from_dict(
        self,
        asset_data: Dict[str, Any],
        created_by_id: Optional[int] = None,
        commit: bool = True,
        lookup_fields: Optional[list] = None
    ) -> tuple[Asset, bool]:
        """Create an asset from a dictionary, with optional find_or_create behavior"""
        asset, created = super().create_asset_from_dict(
            asset_data, 
            created_by_id=created_by_id, 
            commit=False,  # Don't commit yet, we may add details
            lookup_fields=lookup_fields
        )
        
        # Only create detail rows if this is a new asset
        if created:
            self._create_detail_rows(asset)
        
        # Now commit if requested
        if commit:
            from app import db
            db.session.commit()
        
        return asset, created
    
    def _create_detail_rows(self, asset: Asset):
        """
        Create detail table rows for asset
        
        Delegates to AssetDetailFactory for the actual detail creation logic.
        Errors in detail creation are logged but don't fail asset creation.
        """
        try:
            from app.buisness.assets.factories.asset_detail_factory import AssetDetailFactory
            AssetDetailFactory.create_detail_table_rows(asset)
        except Exception as e:
            logger.warning(f"Could not create detail rows for asset {asset.id}: {e}")
            # Don't fail asset creation if detail creation fails
    
    def get_factory_type(self) -> str:
        """Return factory type identifier"""
        return "detail factory"


# Backward compatibility alias
AssetFactory = AssetDetailsFactory

