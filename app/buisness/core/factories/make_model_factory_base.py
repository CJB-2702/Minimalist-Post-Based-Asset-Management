"""
Asset Factory Base Interface
Abstract base class defining the interface for asset creation factories.

This interface allows different factory implementations (core vs details) to be
swapped at runtime while maintaining a consistent API.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from app.data.core.asset_info.asset import Asset
from app.data.core.asset_info.make_model import MakeModel


class MakeModelFactoryBase(ABC):
    """Abstract base class for make/model creation factories"""
    
    @abstractmethod
    def create_make_model(
        self, 
        created_by_id: Optional[int] = None, 
        commit: bool = True, 
        **kwargs
    ) -> MakeModel:
        """
        Create a new MakeModel with proper initialization
        
        Args:
            created_by_id: ID of the user creating the make/model
            commit: Whether to commit the transaction
            **kwargs: MakeModel fields (make, model, year, asset_type_id, etc.)
            
        Returns:
            MakeModel: The created make/model instance
        """
        pass
    
    @abstractmethod
    def create_make_model_from_dict(
        self,
        make_model_data: Dict[str, Any],
        created_by_id: Optional[int] = None,
        commit: bool = True,
        lookup_fields: Optional[list] = None
    ) -> tuple[MakeModel, bool]:
        """
        Create a make/model from a dictionary, with optional find_or_create behavior
        
        Args:
            make_model_data: Dictionary containing make/model data
            created_by_id: ID of the user creating the make/model
            commit: Whether to commit the transaction
            lookup_fields: Fields to use for lookup (e.g., ['make', 'model', 'year'])
            
        Returns:
            tuple: (make_model, created) where created is True if make/model was created
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

