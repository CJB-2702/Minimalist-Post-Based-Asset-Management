"""
Part Demand Struct
Data wrapper around PartDemand for convenient access.
Provides cached access and convenience methods - NO business logic.
"""

from typing import Optional, Union
from app.data.maintenance.base.part_demands import PartDemand


class PartDemandStruct:
    """
    Data wrapper around PartDemand for convenient access.
    Provides cached access and convenience methods - NO business logic.
    """
    
    def __init__(self, part_demand: Union[PartDemand, int]):
        """
        Initialize PartDemandStruct with PartDemand instance or ID.
        
        Args:
            part_demand: PartDemand instance or ID
        """
        if isinstance(part_demand, int):
            self._part_demand = PartDemand.query.get_or_404(part_demand)
            self._part_demand_id = part_demand
        else:
            self._part_demand = part_demand
            self._part_demand_id = part_demand.id
    
    @property
    def part_demand(self) -> PartDemand:
        """Get the PartDemand instance"""
        return self._part_demand
    
    @property
    def part_demand_id(self) -> int:
        """Get the part demand ID"""
        return self._part_demand_id
    
    @property
    def id(self) -> int:
        """Get the part demand ID (alias)"""
        return self._part_demand_id
    
    # Convenience properties for common fields
    @property
    def part_id(self) -> int:
        """Get the part ID"""
        return self._part_demand.part_id
    
    @property
    def part(self):
        """Get the associated Part"""
        return self._part_demand.part
    
    @property
    def quantity_required(self) -> float:
        """Get the quantity required"""
        return self._part_demand.quantity_required
    
    @property
    def status(self) -> str:
        """Get the status"""
        return self._part_demand.status
    
    @property
    def priority(self) -> str:
        """Get the priority"""
        return self._part_demand.priority
    
    @property
    def action_id(self) -> int:
        """Get the action ID"""
        return self._part_demand.action_id
    
    @property
    def action(self):
        """Get the associated Action"""
        return self._part_demand.action
    
    @property
    def requested_by_id(self) -> Optional[int]:
        """Get the requested by user ID"""
        return self._part_demand.requested_by_id
    
    @property
    def requested_by(self):
        """Get the user who requested the part"""
        return self._part_demand.requested_by
    
    @property
    def maintenance_approval_by_id(self) -> Optional[int]:
        """Get the maintenance approval by user ID"""
        return self._part_demand.maintenance_approval_by_id
    
    @property
    def maintenance_approval_by(self):
        """Get the user who approved from maintenance"""
        return self._part_demand.maintenance_approval_by
    
    @property
    def maintenance_approval_date(self):
        """Get the maintenance approval date"""
        return self._part_demand.maintenance_approval_date
    
    @property
    def supply_approval_by_id(self) -> Optional[int]:
        """Get the supply approval by user ID"""
        return self._part_demand.supply_approval_by_id
    
    @property
    def supply_approval_by(self):
        """Get the user who approved from supply"""
        return self._part_demand.supply_approval_by
    
    @property
    def supply_approval_date(self):
        """Get the supply approval date"""
        return self._part_demand.supply_approval_date
    
    @classmethod
    def from_id(cls, part_demand_id: int) -> 'PartDemandStruct':
        """
        Create PartDemandStruct from ID.
        
        Args:
            part_demand_id: Part demand ID
            
        Returns:
            PartDemandStruct instance
        """
        return cls(part_demand_id)
    
    def refresh(self):
        """Refresh cached data from database"""
        from app import db
        db.session.refresh(self._part_demand)
    
    def __repr__(self):
        return f'<PartDemandStruct id={self._part_demand_id} part_id={self.part_id} quantity={self.quantity_required} status={self.status}>'

