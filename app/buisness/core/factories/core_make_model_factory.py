"""
Core MakeModel Factory
Handles basic make/model creation with event creation.

This factory provides the minimum functionality needed for make/model creation:
- Validation
- MakeModel creation
- Event creation

Detail table creation is handled by MakeModelFactory in the assets module.
"""

from typing import Optional, Dict, Any
from app.buisness.core.factories.make_model_factory_base import MakeModelFactoryBase
from app.data.core.asset_info.make_model import MakeModel
from app.data.core.event_info.event import Event
from app import db
from app.logger import get_logger

logger = get_logger("asset_management.buisness.core")


class CoreMakeModelFactory(MakeModelFactoryBase):
    """Core make/model factory - handles basic make/model creation and event creation"""
    
    def create_make_model(
        self, 
        created_by_id: Optional[int] = None, 
        commit: bool = True, 
        **kwargs
    ) -> MakeModel:
        """
        Create make/model with basic operations (validation, event creation)
        
        Note: Detail table creation is handled by MakeModelFactory in the assets module.
        """
        # Validate required fields
        if 'make' not in kwargs:
            raise ValueError("Make is required")
        if 'model' not in kwargs:
            raise ValueError("Model is required")
        
        # Check for duplicate make/model/year combination
        existing_model = MakeModel.query.filter_by(
            make=kwargs['make'],
            model=kwargs['model'],
            year=kwargs.get('year')
        ).first()
        
        if existing_model:
            raise ValueError(
                f"Make/Model/Year combination already exists: "
                f"{kwargs['make']} {kwargs['model']} {kwargs.get('year', 'N/A')}"
            )
        
        # Set audit fields
        if created_by_id:
            kwargs['created_by_id'] = created_by_id
            kwargs['updated_by_id'] = created_by_id
        
        # Create make/model
        make_model = MakeModel(**kwargs)
        db.session.add(make_model)
        
        # Flush to get ID before creating event
        db.session.flush()
        
        # Create creation event (business logic)
        self._create_creation_event(make_model, created_by_id)
        
        # Commit if requested
        if commit:
            db.session.commit()
            logger.info(f"Make/Model created: {make_model.make} {make_model.model} (ID: {make_model.id})")
        else:
            logger.info(f"Make/Model staged: {make_model.make} {make_model.model} (ID: {make_model.id}, not committed)")
        
        return make_model
    
    def create_make_model_from_dict(
        self,
        make_model_data: Dict[str, Any],
        created_by_id: Optional[int] = None,
        commit: bool = True,
        lookup_fields: Optional[list] = None
    ) -> tuple[MakeModel, bool]:
        """Create make/model from dictionary with optional find_or_create"""
        if lookup_fields:
            query_filters = {field: make_model_data.get(field) for field in lookup_fields if field in make_model_data}
            existing_make_model = MakeModel.query.filter_by(**query_filters).first()
            if existing_make_model:
                return existing_make_model, False
        
        make_model = self.create_make_model(created_by_id=created_by_id, commit=commit, **make_model_data)
        return make_model, True
    
    def _create_creation_event(self, make_model: MakeModel, user_id: Optional[int]):
        """Create make/model creation event"""
        description = f"Model '{make_model.make} {make_model.model}'"
        if make_model.year:
            description += f" ({make_model.year})"
        description += " was created"
        
        event = Event(
            event_type='Model Created',
            description=description,
            user_id=user_id
        )
        db.session.add(event)
    
    def get_factory_type(self) -> str:
        """Return factory type identifier"""
        return "core"

