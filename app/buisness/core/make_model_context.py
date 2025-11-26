"""
MakeModel Context (Core)
Provides a clean interface for managing core make/model operations.
Only uses models from app.models.core.* to maintain layer separation.

Handles:
- Basic make/model information and relationships
- Event queries related to models
- Core make/model properties

Note: Detail table management is handled by MakeModelDetailsContext in domain.assets
"""

from typing import List, Optional, Union, Dict, Any
from app.data.core.asset_info.make_model import MakeModel
from app.data.core.asset_info.asset import Asset
from app.data.core.event_info.event import Event
from app.buisness.core.factories.make_model_factory_base import MakeModelFactoryBase

class MakeModelContext:
    """
    Core context manager for make/model operations.
    
    Provides a clean interface for:
    - Accessing make/model and related core models (AssetType)
    - Querying events related to the model
    - Accessing assets of this model type
    - Core make/model properties
    
    Uses only models from app.models.core.*
    """

    make_model_factory: MakeModelFactoryBase = None
    
    def __init__(self, model: Union[MakeModel, int]):
        """
        Initialize MakeModelContext with a MakeModel instance or model ID.
        
        Args:
            model: MakeModel instance or model ID
        """
        if isinstance(model, int):
            self._model = MakeModel.query.get_or_404(model)
            self._model_id = model
        else:
            self._model = model
            self._model_id = model.id
        
        self._creation_event = None
    
    
    @classmethod
    def _check_make_model_factory(cls):
        """Check if the make model factory is set"""
        if cls.make_model_factory is None:
            from app.buisness.core.factories.core_make_model_factory import CoreMakeModelFactory
            cls.make_model_factory = CoreMakeModelFactory()
        return cls.make_model_factory

    @classmethod
    def create(cls, created_by_id: Optional[int] = None, commit: bool = True, **kwargs) -> 'MakeModelContext':
        """Create a new make model using the configured factory"""
        cls._check_make_model_factory()
        make_model = cls.make_model_factory.create_make_model(created_by_id=created_by_id, commit=commit, **kwargs)
        return cls(make_model)
    
    @classmethod
    def create_from_dict(cls, make_model_data: Dict[str, Any], created_by_id: Optional[int] = None, commit: bool = True, lookup_fields: Optional[list] = None) -> 'MakeModelContext':
        """Create a make model from a dictionary with optional find_or_create behavior"""
        cls._check_make_model_factory()
        make_model, created = cls.make_model_factory.create_make_model_from_dict(make_model_data, created_by_id=created_by_id, commit=commit, lookup_fields=lookup_fields)
        return cls(make_model)
        
    @classmethod
    def get_factory_type(cls) -> str:
        """
        Get the type of the current factory (for debugging and introspection).
        
        This is useful for:
        - Debugging which factory is being used
        - Logging factory type in application logs
        - Verifying factory replacement worked correctly
        
        Returns:
            str: Factory type identifier:
                - "core" if CoreAssetFactory is in use
                - "detail factory" if AssetDetailsFactory is in use
                - "None (will use CoreAssetFactory on first create)" if factory not yet initialized
        """
        if cls.make_model_factory is None:
            return "None (will use CoreAssetFactory on first create)"
        return cls.make_model_factory.get_factory_type()
    

    @property
    def model(self) -> MakeModel:
        """Get the MakeModel instance"""
        return self._model
    
    @property
    def model_id(self) -> int:
        """Get the model ID"""
        return self._model_id
    
    @property
    def creation_event(self) -> Optional[Event]:
        """
        Get the creation event for this model.
        
        Returns:
            Event instance for model creation, or None if not found
        """
        if self._creation_event is None:
            # Find the "Model Created" event for this model
            # Since models don't have a direct model_id in events, we search by description pattern
            # The event description format is: "Model '{make} {model}' ({year}) was created"
            description_pattern = f"Model '{self._model.make} {self._model.model}'"
            if self._model.year:
                description_pattern += f" ({self._model.year})"
            
            self._creation_event = Event.query.filter(
                Event.event_type == 'Model Created',
                Event.description.like(f"{description_pattern}%")
            ).order_by(Event.timestamp.asc()).first()
        return self._creation_event
    
    def get_assets(self) -> List[Asset]:
        """
        Get all assets of this model type.
        
        Note: This does not store asset references in memory, just returns a list.
        Each call queries the database fresh.
        
        Returns:
            List of Asset instances for this model
        """
        return Asset.query.filter_by(make_model_id=self._model_id).order_by(Asset.created_at.desc()).all()
    
    @property
    def asset_count(self) -> int:
        """Get the count of assets using this model"""
        return Asset.query.filter_by(make_model_id=self._model_id).count()
    
    @property
    def asset_type(self):
        """Get the AssetType instance for this model"""
        return self._model.asset_type
    
    @property
    def asset_type_id(self) -> Optional[int]:
        """Get the asset type ID"""
        return self._model.asset_type_id
    
    def refresh(self):
        """Refresh cached data from database"""
        self._creation_event = None
    
    def __repr__(self):
        return f'<MakeModelContext model_id={self._model_id} asset_count={self.asset_count}>'


