#!/usr/bin/env python3
"""
MakeModel Factory
Factory class for creating MakeModel instances with proper detail table initialization
"""

from app.logger import get_logger
from app import db
from app.buisness.core.factories.core_make_model_factory import CoreMakeModelFactory
from app.buisness.assets.factories.model_detail_factory import ModelDetailFactory

logger = get_logger("asset_management.domain.assets.factories")

class MakeModelFactory(CoreMakeModelFactory):
    """
    Factory class for creating MakeModel instances
    Ensures proper creation with detail table initialization
    """
    
  
    def create_make_model(self, created_by_id=None, commit=True, **kwargs):
        """
        Create a new MakeModel with proper initialization
        
        Args:
            created_by_id (int): ID of the user creating the make/model
            commit (bool): Whether to commit the transaction (default: True)
            **kwargs: MakeModel fields (make, model, year, asset_type_id, etc.)
            
        Returns:
            MakeModel: The created make/model instance
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Use parent to create model and event
        make_model = super().create_make_model(
            created_by_id=created_by_id,
            commit=False,  # Don't commit yet, we may add details
            **kwargs
        )
        
        # Create detail rows
        self._create_detail_rows(make_model)
        
        # Now commit if requested
        if commit:
            from app import db
            db.session.commit()
            logger.info(f"Make/Model with details created: {make_model.make} {make_model.model} (ID: {make_model.id})")
        
        return make_model
    
    def create_make_model_from_dict(self, make_model_data, created_by_id=None, commit=True, lookup_fields=None):
        """
        Create a make/model from a dictionary, with optional find_or_create behavior
        
        Args:
            make_model_data (dict): Make/Model data dictionary
            created_by_id (int): ID of the user creating the make/model
            commit (bool): Whether to commit the transaction
            lookup_fields (list): Fields to use for find_or_create (e.g., ['make', 'model', 'year'])
            
        Returns:
            tuple: (make_model, created) where created is True if make/model was created
        """
        make_model, created = super().create_make_model_from_dict(
            make_model_data, 
            created_by_id=created_by_id, 
            commit=False,  # Don't commit yet, we may add details
            lookup_fields=lookup_fields
        )
        
        # Only create detail rows if this is a new model
        if created:
            self._create_detail_rows(make_model)
        
        # Now commit if requested
        if commit:
            from app import db
            db.session.commit()
        
        return make_model, created

    def _create_detail_rows(self, make_model):
        """Create detail table rows for make/model"""
        try:
            ModelDetailFactory.create_detail_table_rows(make_model.id, make_model.asset_type_id)
        except Exception as e:
            logger.warning(f"Could not create detail rows for make model {make_model.id}: {e}")
            # Don't fail model creation if detail creation fails

    def get_factory_type(self) -> str:
        return "detail factory"