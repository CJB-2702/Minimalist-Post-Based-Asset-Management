"""
Model Details Struct
Structured class that aggregates all model detail records for a given make/model.

Takes a make_model_id and retrieves the top one of each detail type
(expects only one of each type per model).
"""

from typing import Optional, Dict, Any
from app.data.assets.model_details import (
    ModelInfo,
    EmissionsInfo
)


class ModelDetailsStruct:
    """
    Structured representation of all model detail records for a make/model.
    
    Each detail type is available as a separate attribute.
    Assumes there is only one record of each detail type per make/model.
    """
    
    def __init__(self, make_model_id: int):
        """
        Initialize ModelDetailsStruct with a make_model_id.
        
        Loads one record of each detail type for the make/model.
        
        Args:
            make_model_id: The ID of the make/model to load details for
        """
        self.make_model_id = make_model_id
        
        # Load each detail type (expecting only one of each)
        self.model_info: Optional[ModelInfo] = ModelInfo.query.filter_by(
            make_model_id=make_model_id
        ).first()
        
        self.emissions_info: Optional[EmissionsInfo] = EmissionsInfo.query.filter_by(
            make_model_id=make_model_id
        ).first()
    
    def asdict(self) -> Dict[str, Any]:
        """
        Return a dictionary mapping class names to their instances.
        
        Returns:
            Dictionary with keys as class names and values as the detail record instances (or None)
            
        Example:
            {
                'ModelInfo': <ModelInfo instance or None>,
                'EmissionsInfo': <EmissionsInfo instance or None>
            }
        """
        return {
            'ModelInfo': self.model_info,
            'EmissionsInfo': self.emissions_info
        }
    
    def __repr__(self):
        """String representation of the model details struct"""
        details_present = [
            name for name, value in self.asdict().items() if value is not None
        ]
        return f'<ModelDetailsStruct make_model_id={self.make_model_id} details={details_present}>'

