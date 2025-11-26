"""
Template Part Demand Struct
Data wrapper around TemplatePartDemand for convenient access.
Provides cached access and convenience methods - NO business logic.
"""

from typing import Optional, Union
from app.data.maintenance.templates.template_part_demands import TemplatePartDemand


class TemplatePartDemandStruct:
    """
    Data wrapper around TemplatePartDemand for convenient access.
    Provides cached access and convenience methods - NO business logic.
    """
    
    def __init__(self, template_part_demand: Union[TemplatePartDemand, int]):
        """
        Initialize TemplatePartDemandStruct with TemplatePartDemand instance or ID.
        
        Args:
            template_part_demand: TemplatePartDemand instance or ID
        """
        if isinstance(template_part_demand, int):
            self._template_part_demand = TemplatePartDemand.query.get_or_404(template_part_demand)
            self._template_part_demand_id = template_part_demand
        else:
            self._template_part_demand = template_part_demand
            self._template_part_demand_id = template_part_demand.id
    
    @property
    def template_part_demand(self) -> TemplatePartDemand:
        """Get the TemplatePartDemand instance"""
        return self._template_part_demand
    
    @property
    def template_part_demand_id(self) -> int:
        """Get the template part demand ID"""
        return self._template_part_demand_id
    
    @property
    def id(self) -> int:
        """Get the template part demand ID (alias)"""
        return self._template_part_demand_id
    
    # Convenience properties for common fields
    @property
    def part_id(self) -> int:
        """Get the part ID"""
        return self._template_part_demand.part_id
    
    @property
    def part(self):
        """Get the associated Part"""
        return self._template_part_demand.part
    
    @property
    def quantity_required(self) -> float:
        """Get the quantity required"""
        return self._template_part_demand.quantity_required
    
    @property
    def is_optional(self) -> bool:
        """Get whether part is optional"""
        return self._template_part_demand.is_optional
    
    @property
    def is_required(self) -> bool:
        """Get whether part is required"""
        return self._template_part_demand.is_required
    
    @property
    def template_action_item_id(self) -> int:
        """Get the template action item ID"""
        return self._template_part_demand.template_action_item_id
    
    @property
    def template_action_item(self):
        """Get the associated TemplateActionItem"""
        return self._template_part_demand.template_action_item
    
    @classmethod
    def from_id(cls, template_part_demand_id: int) -> 'TemplatePartDemandStruct':
        """
        Create TemplatePartDemandStruct from ID.
        
        Args:
            template_part_demand_id: Template part demand ID
            
        Returns:
            TemplatePartDemandStruct instance
        """
        return cls(template_part_demand_id)
    
    def refresh(self):
        """Refresh cached data from database"""
        from app import db
        db.session.refresh(self._template_part_demand)
    
    def __repr__(self):
        return f'<TemplatePartDemandStruct id={self._template_part_demand_id} part_id={self.part_id} quantity={self.quantity_required}>'

