"""
Base Planner Behavior
Abstract base class defining the interface for planner behaviors.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from app.data.core.asset_info.asset import Asset
from app.buisness.maintenance.planning.maintenance_plan_context import MaintenancePlanContext
from app.buisness.maintenance.planning.planning_result import PlanningResult
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.maintenance.templates.template_action_sets import TemplateActionSet


class BasePlannerBehavior(ABC):
    """Abstract base class for planner behaviors"""
    
    @abstractmethod
    def find_assets_needing_maintenance(
        self, 
        plan_context: MaintenancePlanContext
    ) -> List[PlanningResult]:
        """
        Find assets that need maintenance based on this planner's logic.
        
        Args:
            plan_context: MaintenancePlanContext for the plan to analyze
            
        Returns:
            List of PlanningResult objects indicating which assets need maintenance
        """
        pass
    
    @abstractmethod
    def calculate_due_date(
        self,
        asset: Asset,
        plan_context: MaintenancePlanContext,
        last_maintenance: Optional[MaintenanceActionSet] = None
    ) -> Optional[datetime]:
        """
        Calculate when maintenance is due for a specific asset.
        
        Args:
            asset: Asset to calculate due date for
            plan_context: MaintenancePlanContext for the plan
            last_maintenance: Last completed maintenance (if available)
            
        Returns:
            Due date or None if cannot be calculated
        """
        pass
    
    @abstractmethod
    def find_last_relevant_maintenance(
        self,
        asset: Asset,
        maintenance_template_action_set: TemplateActionSet
    ) -> Optional[MaintenanceActionSet]:
        """
        Helper function to find the last completed maintenance for an asset
        that matches the given template action set.
        
        Args:
            asset: Asset to find maintenance for
            maintenance_template_action_set: TemplateActionSet to match against
            
        Returns:
            MaintenanceActionSet or None if no maintenance found
        """
        pass
    
    @abstractmethod
    def should_create_maintenance(
        self,
        asset: Asset,
        plan_context: MaintenancePlanContext,
        last_maintenance: Optional[MaintenanceActionSet] = None
    ) -> bool:
        """
        Determine if maintenance should be created for this asset.
        
        Args:
            asset: Asset to check
            plan_context: MaintenancePlanContext for the plan
            last_maintenance: Last completed maintenance (if available)
            
        Returns:
            True if maintenance should be created
        """
        pass

