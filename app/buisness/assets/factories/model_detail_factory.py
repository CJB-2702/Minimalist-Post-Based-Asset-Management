#!/usr/bin/env python3
"""
Model Detail Factory
Factory class for creating model detail table rows
"""

from .detail_factory import DetailFactory
from app.logger import get_logger
from app import db

logger = get_logger("asset_management.domain.assets.factories")

class ModelDetailFactory(DetailFactory):
    """
    Factory class for creating model detail table rows
    """
    
    @classmethod
    def create_detail_table_rows(cls, model_id, asset_type_id):
        """
        Create detail table rows for a model based on model configurations
        
        Args:
            model_id (int): The model ID
            asset_type_id (int): The asset type ID
        """
        try:
            from app.data.assets.detail_table_templates.model_detail_table_template import ModelDetailTableTemplate
            from app.data.core.event_info.event import Event
            from app.data.core.asset_info.make_model import MakeModel
            
            # Get the model to find its creation event
            model = MakeModel.query.get(model_id)
            if model:
                # Find the model creation event by description pattern
                description_pattern = f"Model '{model.make} {model.model}'"
                if model.year:
                    description_pattern += f" ({model.year})"
                
                creation_event = Event.query.filter(
                    Event.event_type == 'Model Created',
                    Event.description.like(f"{description_pattern}%")
                ).order_by(Event.timestamp.asc()).first()
                
                event_id = creation_event.id if creation_event else None
                if event_id:
                    logger.debug(f"Found model creation event {event_id} for model {model_id}")
                else:
                    logger.warning(f"No creation event found for model {model_id}")
            else:
                event_id = None
                logger.warning(f"Model {model_id} not found")
            
            # Get all detail table configurations for this model
            detail_configs = ModelDetailTableTemplate.get_detail_table_types_for_model(asset_type_id)
            
            for config in detail_configs:
                cls._create_single_detail_row(
                    config=config,
                    detail_table_type=config.detail_table_type,
                    target_id=model_id,
                    event_id=event_id
                )
                
        except Exception as e:
            logger.debug(f"Error creating model detail table rows for model {model_id}: {e}")

