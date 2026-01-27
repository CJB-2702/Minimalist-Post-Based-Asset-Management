"""
Maintenance Query Service
Service layer for maintenance-related query operations.
Handles all query methods for MaintenanceContext, MaintenancePlanContext, and ActionContext.
"""

from typing import List, Optional
from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
from app.buisness.maintenance.planning.maintenance_plan_context import MaintenancePlanContext
from app.buisness.maintenance.base.action_managment.action_context import ActionContext
from app.buisness.maintenance.base.structs.maintenance_action_set_struct import MaintenanceActionSetStruct
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.maintenance.planning.maintenance_plans import MaintenancePlan
from app.data.maintenance.base.actions import Action


class MaintenanceQueryService:
    """
    Service for maintenance-related query operations.
    
    Provides query methods for:
    - MaintenanceContext queries
    - MaintenancePlanContext queries
    - ActionContext queries
    """
    
    # MaintenanceContext query methods
    @staticmethod
    def get_all_maintenance_contexts() -> List[MaintenanceContext]:
        """
        Get all maintenance action sets.
        
        Returns:
            List of MaintenanceContext instances
        """
        action_sets = MaintenanceActionSet.query.all()
        return [MaintenanceContext.from_maintenance_action_set(mas) for mas in action_sets]
    
    @staticmethod
    def get_maintenance_contexts_by_status(status: str) -> List[MaintenanceContext]:
        """
        Get maintenance action sets by status.
        
        Args:
            status: Status to filter by
            
        Returns:
            List of MaintenanceContext instances
        """
        action_sets = MaintenanceActionSet.query.filter_by(status=status).all()
        return [MaintenanceContext.from_maintenance_action_set(mas) for mas in action_sets]
    
    @staticmethod
    def get_maintenance_contexts_by_asset(asset_id: int) -> List[MaintenanceContext]:
        """
        Get maintenance action sets by asset.
        
        Args:
            asset_id: Asset ID to filter by
            
        Returns:
            List of MaintenanceContext instances
        """
        action_sets = MaintenanceActionSet.query.filter_by(asset_id=asset_id).all()
        return [MaintenanceContext.from_maintenance_action_set(mas) for mas in action_sets]
    
    @staticmethod
    def get_maintenance_contexts_by_user(user_id: int, assigned: bool = True) -> List[MaintenanceContext]:
        """
        Get maintenance action sets by assigned user.
        
        Args:
            user_id: User ID to filter by
            assigned: If True, filter by assigned_user_id; if False, filter by completed_by_id
            
        Returns:
            List of MaintenanceContext instances
        """
        if assigned:
            action_sets = MaintenanceActionSet.query.filter_by(assigned_user_id=user_id).all()
        else:
            action_sets = MaintenanceActionSet.query.filter_by(completed_by_id=user_id).all()
        return [MaintenanceContext.from_maintenance_action_set(mas) for mas in action_sets]
    
    @staticmethod
    def get_maintenance_context_by_event_id(event_id: int) -> Optional[MaintenanceContext]:
        """
        Get maintenance action set by event ID.
        Since there's only one MaintenanceActionSet per Event (ONE-TO-ONE), returns single instance.
        
        Args:
            event_id: Event ID
            
        Returns:
            MaintenanceContext instance or None if not found
        """
        try:
            return MaintenanceContext.from_event(event_id)
        except ValueError:
            raise ValueError(f"No maintenance action set found for event_id {event_id}")
    
    # MaintenancePlanContext query methods
    @staticmethod
    def get_all_maintenance_plan_contexts() -> List[MaintenancePlanContext]:
        """
        Get all maintenance plans.
        
        Returns:
            List of MaintenancePlanContext instances
        """
        plans = MaintenancePlan.query.all()
        return [MaintenancePlanContext(plan) for plan in plans]
    
    @staticmethod
    def get_active_maintenance_plan_contexts() -> List[MaintenancePlanContext]:
        """
        Get all active maintenance plans.
        
        Returns:
            List of MaintenancePlanContext instances
        """
        plans = MaintenancePlan.query.filter_by(status='Active').all()
        return [MaintenancePlanContext(plan) for plan in plans]
    
    @staticmethod
    def get_maintenance_plan_contexts_by_asset_type(asset_type_id: int) -> List[MaintenancePlanContext]:
        """
        Get maintenance plans by asset type.
        
        Args:
            asset_type_id: Asset type ID
            
        Returns:
            List of MaintenancePlanContext instances
        """
        plans = MaintenancePlan.query.filter_by(asset_type_id=asset_type_id).all()
        return [MaintenancePlanContext(plan) for plan in plans]
    
    # ActionContext query methods
    @staticmethod
    def get_action_contexts_by_maintenance_action_set(maintenance_action_set_id: int) -> List[ActionContext]:
        """
        Get all actions for a maintenance action set.
        
        Args:
            maintenance_action_set_id: Maintenance action set ID
            
        Returns:
            List of ActionContext instances, ordered by sequence_order
        """
        actions = Action.query.filter_by(
            maintenance_action_set_id=maintenance_action_set_id
        ).order_by(Action.sequence_order).all()
        return [ActionContext(action) for action in actions]
    
    @staticmethod
    def get_action_contexts_by_user(user_id: int) -> List[ActionContext]:
        """
        Get all actions assigned to a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of ActionContext instances
        """
        actions = Action.query.filter_by(assigned_user_id=user_id).all()
        return [ActionContext(action) for action in actions]
    
    @staticmethod
    def get_action_contexts_by_status(status: str, maintenance_action_set_id: Optional[int] = None) -> List[ActionContext]:
        """
        Get actions by status.
        
        Args:
            status: Status to filter by
            maintenance_action_set_id: Optional maintenance action set ID to filter by
            
        Returns:
            List of ActionContext instances
        """
        query = Action.query.filter_by(status=status)
        if maintenance_action_set_id:
            query = query.filter_by(maintenance_action_set_id=maintenance_action_set_id)
        actions = query.all()
        return [ActionContext(action) for action in actions]

