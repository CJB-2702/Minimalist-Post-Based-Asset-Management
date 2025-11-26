"""
Asset Factory Base Interface
Abstract base class defining the interface for asset creation factories.

This interface allows different factory implementations (core vs details) to be
swapped at runtime while maintaining a consistent API.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from app.data.core.asset_info.asset import Asset


class AssetFactoryBase(ABC):
    """Abstract base class for asset creation factories"""
    
    @abstractmethod
    def create_asset(
        self, 
        created_by_id: Optional[int] = None, 
        commit: bool = True, 
        enable_detail_insertion: bool = True,
        **kwargs
    ) -> Asset:
        """
        Create a new Asset with proper initialization
        
        Args:
            created_by_id: ID of the user creating the asset
            commit: Whether to commit the transaction
            enable_detail_insertion: Whether to create detail rows (may be ignored by basic factory)
            **kwargs: Asset fields (name, serial_number, make_model_id, etc.)
            
        Returns:
            Asset: The created asset instance
        """
        pass
    
    @abstractmethod
    def create_asset_from_dict(
        self,
        asset_data: Dict[str, Any],
        created_by_id: Optional[int] = None,
        commit: bool = True,
        lookup_fields: Optional[list] = None
    ) -> tuple[Asset, bool]:
        """
        Create an asset from a dictionary, with optional find_or_create behavior
        
        Args:
            asset_data: Dictionary containing asset data
            created_by_id: ID of the user creating the asset
            commit: Whether to commit the transaction
            lookup_fields: Fields to use for lookup (e.g., ['serial_number'])
            
        Returns:
            tuple: (asset, created) where created is True if asset was created
        """
        pass
    
    def get_factory_type(self) -> str:
        """
        Get the factory type identifier
        
        Returns:
            str: Factory type identifier ("core", "detail factory", or "unknown")
        """
        # Default implementation - subclasses should override
        return "unknown"

