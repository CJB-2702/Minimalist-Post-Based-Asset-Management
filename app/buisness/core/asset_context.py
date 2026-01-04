"""
Asset Context (Core)
Provides a clean interface for managing core asset operations.
Only uses models from app.models.core.* to maintain layer separation.

Handles:
- Basic asset information and relationships
- Event queries related to assets
- Core asset properties

Note: Detail table management is handled by AssetDetailsContext in domain.assets
"""

from typing import List, Optional, Union, Dict, Any, TYPE_CHECKING
from datetime import datetime
from app.data.core.asset_info.asset import Asset
from app.data.core.asset_info.meter_history import MeterHistory
from app.data.core.event_info.event import Event

if TYPE_CHECKING:
    from app.buisness.core.factories.asset_factory_base import AssetFactoryBase


class AssetContext:
    """
    Core context manager for asset operations.
    
    Provides a clean interface for:
    - Accessing asset and related core models (MakeModel, MajorLocation, AssetType)
    - Querying events related to the asset
    - Accessing basic asset properties
    - Creating new assets via factory pattern
    
    Uses only models from app.models.core.*
    
    Factory Replacement Strategy:
    =============================
    This class uses a factory replacement pattern to eliminate import dependencies
    from the core module to the assets module while maintaining important functionality.
    
    HOW IT WORKS:
    - AssetContext has a static class attribute 'asset_factory' that holds a factory instance
    - The core module provides CoreAssetFactory (basic asset creation + events)
    - The assets module can replace this factory with AssetDetailsFactory (adds detail creation)
    - When assets module is imported, it replaces AssetContext.asset_factory with AssetDetailsFactory
    - Almost all of the time, the factory will be AssetDetailsFactory in place
    
    WHY THIS APPROACH:
    - Core module has ZERO imports from assets module (maintains module independence)
    - Assets module imports core (reverse dependency - allowed direction)
    - Factory replacement happens at runtime when assets module is imported
    - If assets module is not imported, core factory is used (graceful degradation)
    - Business logic (event creation, detail creation) is in business layer, not data layer
    
    FACTORY LIFECYCLE:
    1. Initially, asset_factory is None
    2. On first AssetContext.create() call, if factory is None, CoreAssetFactory is created (lazy init)
    3. When assets module is imported, it checks factory type and replaces with AssetDetailsFactory
    4. Subsequent create() calls use AssetDetailsFactory (which includes detail creation)
    """
    
    # Static factory attribute - can be replaced by feature modules
    # Almost all of the time, this will be AssetDetailsFactory (set when assets module is imported)
    # If assets module is not imported, this will be CoreAssetFactory (created on first use)
    asset_factory: AssetFactoryBase = None
    
    def __init__(self, asset: Union[Asset, int]):
        """
        Initialize AssetContext with an Asset instance or asset ID.
        
        Args:
            asset: Asset instance or asset ID
        """
        if isinstance(asset, int):
            self._asset = Asset.query.get_or_404(asset)
            self._asset_id = asset
        else:
            self._asset = asset
            self._asset_id = asset.id

        self._creation_event = None
    
    @property
    def asset(self) -> Asset:
        """Get the Asset instance"""
        return self._asset
    
    @property
    def asset_id(self) -> int:
        """Get the asset ID"""
        return self._asset_id
    
    @property
    def make_model(self):
        """Get the MakeModel instance for this asset"""
        return self._asset.make_model
    
    @property
    def major_location(self):
        """Get the MajorLocation instance for this asset"""
        return self._asset.major_location
    
    @property
    def asset_type_id(self) -> Optional[int]:
        """Get the asset type ID through the make_model relationship"""
        return self._asset.asset_type_id
    
    @property
    def asset_type(self):
        """Get the AssetType instance for this asset"""
        if self._asset.asset_type_id and self._asset.make_model:
            return self._asset.make_model.asset_type
        return None
    
    @property
    def creation_event(self) -> Optional[Event]:
        """
        Get the creation event for this asset.
        
        Returns:
            Event instance for asset creation, or None if not found
        """
        if self._creation_event is None:
            # Find the "Asset Created" event for this asset
            self._creation_event = Event.query.filter_by(
                asset_id=self._asset_id,
                event_type='Asset Created'
            ).order_by(Event.timestamp.asc()).first()
        return self._creation_event
    
    def recent_events(self, limit: int = 10) -> List[Event]:
        """
        Get recent events for this asset, ordered by timestamp (newest first).
        
        Args:
            limit: Maximum number of events to return (default: 10)
            
        Returns:
            List of Event instances
        """
        return Event.query.filter_by(asset_id=self._asset_id).order_by(Event.timestamp.desc()).limit(limit).all()
    

    @classmethod
    def _check_asset_factory(cls):
        """Check if the asset factory is set"""
        if cls.asset_factory is None:
            from app.buisness.core.factories.core_asset_factory import CoreAssetFactory
            cls.asset_factory = CoreAssetFactory()
            # Disable detail creation when using core factory
            from app.data.core.asset_info.asset import Asset
            Asset.disable_detail_creation()
        return cls.asset_factory


    @classmethod
    def create(
        cls,
        created_by_id: Optional[int] = None,
        commit: bool = True,
        **kwargs
    ) -> 'AssetContext':
        """
        Create a new asset using the configured factory.
        
        This method uses the factory replacement pattern:
        - If assets module is imported, uses AssetDetailsFactory (creates asset + events + details)
        - If assets module not imported, uses CoreAssetFactory (creates asset + events only)
        - Factory is lazily initialized if not set
        
        Args:
            created_by_id: ID of the user creating the asset
            commit: Whether to commit the transaction
            enable_detail_insertion: Whether to create detail rows (only works with AssetDetailsFactory)
            **kwargs: Asset fields (name, serial_number, make_model_id, etc.)
            
        Returns:
            AssetContext instance for the newly created asset
            
        Raises:
            ValueError: If required fields are missing or serial number is duplicate
        """
        # Lazy initialization: if factory not set, use core factory
        # This ensures the system works even if assets module is never imported
        cls._check_asset_factory()
        # Use the configured factory to create the asset
        # In most cases, this will be AssetDetailsFactory (set by assets module)
        asset = cls.asset_factory.create_asset(
            created_by_id=created_by_id,
            commit=commit,
            **kwargs
        )
        
        return cls(asset)
    
    @classmethod
    def create_from_dict(cls, asset_data: Dict[str, Any], created_by_id: Optional[int] = None, commit: bool = True, lookup_fields: Optional[list] = None) -> 'AssetContext':
        """Create an asset from a dictionary with optional find_or_create behavior"""
        cls._check_asset_factory()
        asset, created = cls.asset_factory.create_asset_from_dict(asset_data, created_by_id=created_by_id, commit=commit, lookup_fields=lookup_fields)
        return cls(asset)
        
    
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
        if cls.asset_factory is None:
            return "None (will use CoreAssetFactory on first create)"
        return cls.asset_factory.get_factory_type()
    
    def update_meters(
        self,
        meter1: Optional[float] = None,
        meter2: Optional[float] = None,
        meter3: Optional[float] = None,
        meter4: Optional[float] = None,
        updated_by_id: Optional[int] = None,
        recorded_at: Optional[datetime] = None,
        validate: bool = True,
        commit: bool = True
    ) -> MeterHistory:
        """
        Update asset meters and create meter history record.
        
        Updates the asset's current meters and creates a MeterHistory record.
        Can optionally validate that at least one meter value is provided.
        
        Args:
            meter1-4: Meter values (can be None)
            updated_by_id: ID of the user making the change
            recorded_at: Optional timestamp (defaults to now)
            validate: If True, validates that at least one meter value is provided
            commit: If True, commit the transaction immediately. If False, 
                    add to session but don't commit (allows rollback on error)
        
        Raises:
            ValueError: If validate=True and all meters are None
            
        Returns:
            MeterHistory instance
        """
        from app import db
        
        # Validation: at least one meter must be provided (if validation enabled)
        
        if validate:

            all_meters_none = meter1 is None and meter2 is None and meter3 is None and meter4 is None
            if all_meters_none:
                raise ValueError("At least one meter value must be provided")
            #todo add validation for meter values
        
        if recorded_at is None:
            recorded_at = datetime.utcnow()
        
        # Create meter history record
        meter_history = MeterHistory(
            asset_id=self._asset_id,
            meter1=meter1,
            meter2=meter2,
            meter3=meter3,
            meter4=meter4,
            recorded_at=recorded_at,
            recorded_by_id=updated_by_id,
            created_by_id=updated_by_id,
            updated_by_id=updated_by_id
        )
        
        db.session.add(meter_history)
        
        # Flush to get the ID (needed even when commit=False so ID is available for foreign key)
        db.session.flush()
        
        # Update asset's current meters (only non-None values)
        if meter1 is not None:
            self._asset.meter1 = meter1
        if meter2 is not None:
            self._asset.meter2 = meter2
        if meter3 is not None:
            self._asset.meter3 = meter3
        if meter4 is not None:
            self._asset.meter4 = meter4
        
        # Update asset audit fields
        if updated_by_id:
            self._asset.updated_by_id = updated_by_id
        
        if commit:
            db.session.commit()
        
        return meter_history
    
    def edit(
        self,
        updated_by_id: Optional[int] = None,
        commit: bool = True,
        ignore_meter_validation: bool = False,
        **kwargs
    ) -> 'AssetContext':
        """
        Edit asset with automatic event creation for key field changes.
        
        Key fields that trigger events when changed:
        - name
        - serial_number
        - major_location_id
        - make_model_id
        
        Meter tracking:
        - If any meter values (meter1-4) are updated, a MeterHistory record is automatically created
        - Meter history is created with commit=False if commit=False, allowing transaction rollback
        
        Args:
            updated_by_id: ID of the user making the change
            commit: Whether to commit the transaction
            ignore_meter_validation: If True, skip meter validation (e.g., allow decreasing values, large jumps).
                                     This is ONLY available on asset edit route, NOT on maintenance completion.
            **kwargs: Fields to update (name, serial_number, major_location_id, make_model_id, status, meters, etc.)
            
        Returns:
            AssetContext instance (self)
        """
        from app import db
        from app.data.core.major_location import MajorLocation
        
        # Get current values for key fields
        key_fields = ['name', 'serial_number', 'major_location_id', 'make_model_id']
        current_values = {}
        new_values = {}
        changes = []
        
        for field in key_fields:
            current_value = getattr(self._asset, field, None)
            current_values[field] = current_value
            
            if field in kwargs:
                new_value = kwargs[field]
                new_values[field] = new_value
                
                # Check if value is actually changing
                if current_value != new_value:
                    changes.append((field, current_value, new_value))
        
        # Create event if any key fields are changing
        if changes:
            # Build description with old and new values
            description_parts = ["Asset Key Details Change:"]
            
            for field, old_val, new_val in changes:
                # Format values for display
                if field == 'major_location_id':
                    old_display = MajorLocation.query.get(old_val).name if old_val and MajorLocation.query.get(old_val) else str(old_val) if old_val else "None"
                    new_display = MajorLocation.query.get(new_val).name if new_val and MajorLocation.query.get(new_val) else str(new_val) if new_val else "None"
                elif field == 'make_model_id':
                    from app.data.core.asset_info.make_model import MakeModel
                    old_mm = MakeModel.query.get(old_val) if old_val else None
                    new_mm = MakeModel.query.get(new_val) if new_val else None
                    old_display = f"{old_mm.make} {old_mm.model}" if old_mm else str(old_val) if old_val else "None"
                    new_display = f"{new_mm.make} {new_mm.model}" if new_mm else str(new_val) if new_val else "None"
                else:
                    old_display = str(old_val) if old_val else "None"
                    new_display = str(new_val) if new_val else "None"
                
                description_parts.append(f"  {field}: {old_display} → {new_display}")
            
            description = "\n".join(description_parts)
            
            # Determine location for event (use new location if it's changing, otherwise current)
            event_location_id = new_values.get('major_location_id', self._asset.major_location_id)
            
            # Create the event
            event = Event(
                event_type='Asset Key Details Change',
                description=description,
                user_id=updated_by_id,
                asset_id=self._asset_id,
                major_location_id=event_location_id
            )
            db.session.add(event)
        
        # Check if meters are being updated
        meter_fields = ['meter1', 'meter2', 'meter3', 'meter4']
        meters_updated = any(field in kwargs for field in meter_fields)
        
        # Extract meter values from kwargs (use current values if not provided)
        meter_values = {}
        if meters_updated:
            for field in meter_fields:
                meter_values[field] = kwargs.get(field, getattr(self._asset, field, None))
        
        # Apply all changes (including non-key fields, but exclude meters - handled separately)
        for key, value in kwargs.items():
            if key not in meter_fields and value is not None:
                setattr(self._asset, key, value)
        
        # Set audit fields
        if updated_by_id:
            self._asset.updated_by_id = updated_by_id
        
        # Update meters and create history if meters were updated
        if meters_updated:
            self.update_meters(
                meter1=meter_values.get('meter1'),
                meter2=meter_values.get('meter2'),
                meter3=meter_values.get('meter3'),
                meter4=meter_values.get('meter4'),
                updated_by_id=updated_by_id,
                validate=not ignore_meter_validation,  # Validate unless explicitly bypassed
                commit=commit
            )
        
        # Commit if requested
        if commit:
            db.session.commit()
            from app.logger import get_logger
            logger = get_logger("asset_management.buisness.core")
            logger.info(f"Asset edited: {self._asset.name} (ID: {self._asset_id})")
        
        return self
    
    def refresh(self):
        """Refresh cached data from database"""
        self._creation_event = None
    
    def __repr__(self):
        return f'<AssetContext asset_id={self._asset_id}>'

