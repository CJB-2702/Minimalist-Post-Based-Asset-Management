"""
Planning Result Data Structure
Represents the result of planning analysis for a single asset.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime
from app.data.core.asset_info.asset import Asset
from app.buisness.maintenance.planning.maintenance_plan_context import MaintenancePlanContext
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet


@dataclass
class PlanningResult:
    """Result of planning analysis for a single asset"""
    asset_id: int
    asset: Asset
    maintenance_plan_id: int
    maintenance_plan: MaintenancePlanContext
    needs_maintenance: bool
    reason: str  # Why maintenance is needed (or why not)
    due_date: Optional[datetime] = None
    last_maintenance_date: Optional[datetime] = None
    last_maintenance: Optional[MaintenanceActionSet] = None
    current_meter_readings: Dict[str, Optional[float]] = field(default_factory=lambda: {
        'meter1': None,
        'meter2': None,
        'meter3': None,
        'meter4': None
    })
    meter_readings_at_last_maintenance: Dict[str, Optional[float]] = field(default_factory=lambda: {
        'meter1': None,
        'meter2': None,
        'meter3': None,
        'meter4': None
    })
    days_since_last_maintenance: Optional[float] = None
    meter_delta: Dict[str, Optional[float]] = field(default_factory=lambda: {
        'meter1': None,
        'meter2': None,
        'meter3': None,
        'meter4': None
    })
    recommended_start_date: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert PlanningResult to dictionary for serialization"""
        return {
            'asset_id': self.asset_id,
            'maintenance_plan_id': self.maintenance_plan_id,
            'needs_maintenance': self.needs_maintenance,
            'reason': self.reason,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'last_maintenance_date': self.last_maintenance_date.isoformat() if self.last_maintenance_date else None,
            'days_since_last_maintenance': self.days_since_last_maintenance,
            'current_meter_readings': self.current_meter_readings,
            'meter_readings_at_last_maintenance': self.meter_readings_at_last_maintenance,
            'meter_delta': self.meter_delta,
            'recommended_start_date': self.recommended_start_date.isoformat() if self.recommended_start_date else None,
            'errors': self.errors
        }

