"""
Maintenance Planner
Main orchestrator class for maintenance planning operations.
Handles plan selection, behavior delegation, and result aggregation.
"""

from typing import List, Optional, Union
from datetime import datetime
from app import db
from app.buisness.maintenance.planning.maintenance_plan_context import MaintenancePlanContext
from app.buisness.maintenance.planning.planning_result import PlanningResult
from app.buisness.maintenance.planning.behaviors.time_based_planner import TimeBasedPlanner
from app.buisness.maintenance.planning.behaviors.meter_based_planner import MeterBasedPlanner
from app.buisness.maintenance.planning.base_planner_behavior import BasePlannerBehavior
from app.data.maintenance.planning.maintenance_plans import MaintenancePlan
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.logger import get_logger

logger = get_logger("asset_management.business.maintenance.planning")


class MaintenancePlanner:
    """
    Main orchestrator for maintenance planning operations.
    
    Responsibilities:
    - Plan selection and filtering
    - Behavior selection based on frequency type
    - Asset analysis and result aggregation
    - Optional maintenance event creation
    - Error handling and logging
    """
    
    def __init__(self, plan_context: Optional[MaintenancePlanContext] = None):
        """
        Initialize MaintenancePlanner.
        
        Args:
            plan_context: Optional MaintenancePlanContext to work with
        """
        self.plan_context = plan_context
    
    @classmethod
    def from_plan_id(cls, plan_id: int) -> 'MaintenancePlanner':
        """
        Create MaintenancePlanner from plan ID.
        
        Args:
            plan_id: Maintenance plan ID
            
        Returns:
            MaintenancePlanner instance with initialized plan_context
        """
        plan_context = MaintenancePlanContext(plan_id)
        return cls(plan_context=plan_context)
    
    def plan_maintenance(
        self, 
        plan_context: Optional[MaintenancePlanContext] = None
    ) -> List[PlanningResult]:
        """
        Plan maintenance for a single maintenance plan.
        
        Args:
            plan_context: MaintenancePlanContext to plan for (uses self.plan_context if not provided)
            
        Returns:
            List of PlanningResult objects
        """
        if plan_context is None:
            plan_context = self.plan_context
        
        if plan_context is None:
            raise ValueError("No plan_context provided and no plan_context set on instance")
        
        # Check if plan is active
        if not plan_context.is_active:
            logger.info(f"Plan {plan_context.id} is not active, skipping planning")
            return []
        
        # Select appropriate planner behavior
        planner_behavior = self._select_planner_behavior(plan_context)
        if not planner_behavior:
            logger.warning(f"No planner behavior found for frequency_type: {plan_context.maintenance_plan.frequency_type}")
            return []
        
        # Find assets needing maintenance
        results = planner_behavior.find_assets_needing_maintenance(plan_context)
        
        # Filter out duplicate events (check for existing Planned/In Progress events)
        filtered_results = []
        for result in results:
            if result.needs_maintenance:
                # Check for duplicate
                has_duplicate = self._check_duplicate_events(
                    result.asset_id,
                    result.maintenance_plan_id
                )
                if has_duplicate:
                    result.needs_maintenance = False
                    result.reason = f"Duplicate prevention: Existing Planned or In Progress maintenance event found"
                    logger.debug(f"Duplicate event prevented for asset {result.asset_id}, plan {result.maintenance_plan_id}")
            
            filtered_results.append(result)
        
        return filtered_results
    
    def plan_all_active_plans(self) -> List[PlanningResult]:
        """
        Plan maintenance for all active maintenance plans.
        
        Returns:
            List of PlanningResult objects from all active plans
        """
        all_results = []
        active_plans = MaintenancePlan.query.filter_by(status='Active').all()
        
        logger.info(f"Planning maintenance for {len(active_plans)} active plans")
        
        for plan in active_plans:
            try:
                plan_context = MaintenancePlanContext(plan)
                results = self.plan_maintenance(plan_context)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Error planning for plan {plan.id}: {e}")
                # Continue with other plans
        
        return all_results
    
    def plan_plans(
        self, 
        plan_contexts: List[MaintenancePlanContext]
    ) -> List[PlanningResult]:
        """
        Plan maintenance for multiple maintenance plans.
        
        Args:
            plan_contexts: List of MaintenancePlanContext objects to plan for
            
        Returns:
            List of PlanningResult objects from all plans
        """
        all_results = []
        
        for plan_context in plan_contexts:
            try:
                results = self.plan_maintenance(plan_context)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Error planning for plan {plan_context.id}: {e}")
                # Continue with other plans
        
        return all_results
    
    def create_events_from_results(
        self,
        results: List[PlanningResult],
        user_id: Optional[int] = None,
        auto_create: bool = False
    ) -> List[MaintenanceActionSet]:
        """
        Create maintenance events from planning results.
        
        Args:
            results: List of PlanningResult objects
            user_id: User ID creating the events
            auto_create: If True, create events even if not explicitly needed
            
        Returns:
            List of created MaintenanceActionSet objects
        """
        created_events = []
        
        # Filter to results that need maintenance
        if not auto_create:
            results = [r for r in results if r.needs_maintenance]
        
        for result in results:
            if not result.needs_maintenance and not auto_create:
                continue
            
            try:
                # Double-check for duplicates before creating
                if self._check_duplicate_events(result.asset_id, result.maintenance_plan_id):
                    logger.warning(f"Duplicate event prevented for asset {result.asset_id}, plan {result.maintenance_plan_id}")
                    continue
                
                # Create maintenance event
                plan_context = result.maintenance_plan
                maintenance_event = plan_context.create_maintenance_event(
                    asset_id=result.asset_id,
                    planned_start_datetime=result.recommended_start_date or datetime.utcnow(),
                    user_id=user_id
                )
                
                if maintenance_event:
                    created_events.append(maintenance_event)
                    logger.info(f"Created maintenance event {maintenance_event.id} for asset {result.asset_id}, plan {result.maintenance_plan_id}")
                
            except Exception as e:
                logger.error(f"Error creating maintenance event for asset {result.asset_id}: {e}")
                result.errors.append(f"Error creating event: {str(e)}")
                # Continue with other results
        
        return created_events
    
    def _select_planner_behavior(
        self, 
        plan_context: MaintenancePlanContext
    ) -> Optional[BasePlannerBehavior]:
        """
        Select appropriate planner behavior based on frequency type.
        
        Args:
            plan_context: MaintenancePlanContext to get frequency type from
            
        Returns:
            BasePlannerBehavior instance or None if no match
        """
        frequency_type = plan_context.maintenance_plan.frequency_type
        
        if frequency_type in ['hours', 'days']:
            return TimeBasedPlanner()
        elif frequency_type in ['meter1', 'meter2', 'meter3', 'meter4']:
            return MeterBasedPlanner()
        # Future: Add HybridPlanner for combined time+meter logic
        # elif frequency_type.startswith('time_and_'):
        #     return HybridPlanner()
        
        return None
    
    def _check_duplicate_events(
        self, 
        asset_id: int, 
        maintenance_plan_id: int
    ) -> bool:
        """
        Check for existing Planned or In Progress maintenance events for the same plan+asset.
        
        Args:
            asset_id: Asset ID
            maintenance_plan_id: Maintenance plan ID
            
        Returns:
            True if duplicate exists, False otherwise
        """
        existing = (
            MaintenanceActionSet.query
            .filter_by(
                asset_id=asset_id,
                maintenance_plan_id=maintenance_plan_id
            )
            .filter(MaintenanceActionSet.status.in_(['Planned', 'In Progress']))
            .first()
        )
        
        return existing is not None
    
    def get_assets_needing_maintenance(
        self,
        plan_context: Optional[MaintenancePlanContext] = None
    ) -> List[PlanningResult]:
        """
        Get only the assets that need maintenance (filtered results).
        
        Args:
            plan_context: MaintenancePlanContext to plan for (uses self.plan_context if not provided)
            
        Returns:
            List of PlanningResult objects where needs_maintenance=True
        """
        results = self.plan_maintenance(plan_context)
        return [r for r in results if r.needs_maintenance]

