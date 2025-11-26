"""
Maintenance Plan Context
Business logic context manager for maintenance plans.
Provides plan scheduling, frequency management, and maintenance event creation.
"""

from typing import List, Optional, Union, Dict, Any
from datetime import datetime, timedelta
from app import db
from app.data.maintenance.base.maintenance_plans import MaintenancePlan
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.core.asset_info.asset import Asset
from app.data.core.event_info.event import Event


class MaintenancePlanContext:
    """
    Business logic context manager for maintenance plans.
    
    Wraps MaintenancePlan data table
    Provides plan scheduling, frequency management, template assignment, and maintenance event creation.
    """
    
    def __init__(self, maintenance_plan: Union[MaintenancePlan, int]):
        """
        Initialize MaintenancePlanContext with MaintenancePlan instance or ID.
        
        Args:
            maintenance_plan: MaintenancePlan instance or ID
        """
        if isinstance(maintenance_plan, int):
            self._maintenance_plan = MaintenancePlan.query.get_or_404(maintenance_plan)
            self._maintenance_plan_id = maintenance_plan
        else:
            self._maintenance_plan = maintenance_plan
            self._maintenance_plan_id = maintenance_plan.id
    
    @property
    def maintenance_plan(self) -> MaintenancePlan:
        """Get the MaintenancePlan instance"""
        return self._maintenance_plan
    
    @property
    def maintenance_plan_id(self) -> int:
        """Get the maintenance plan ID"""
        return self._maintenance_plan_id
    
    @property
    def id(self) -> int:
        """Get the maintenance plan ID (alias)"""
        return self._maintenance_plan_id
    
    # Convenience properties
    @property
    def name(self) -> str:
        """Get the plan name"""
        return self._maintenance_plan.name
    
    @property
    def status(self) -> str:
        """Get the plan status"""
        return self._maintenance_plan.status
    
    @property
    def is_active(self) -> bool:
        """Check if plan is active"""
        return self._maintenance_plan.status == 'Active'
    
    @property
    def template_action_set(self):
        """Get the associated TemplateActionSet"""
        return self._maintenance_plan.template_action_set
    
    @property
    def template_action_set_id(self) -> int:
        """Get the template action set ID"""
        return self._maintenance_plan.template_action_set_id
    
    def activate(self) -> 'MaintenancePlanContext':
        """
        Activate the maintenance plan.
        
        Returns:
            self for chaining
        """
        self._maintenance_plan.status = 'Active'
        db.session.commit()
        return self
    
    def deactivate(self) -> 'MaintenancePlanContext':
        """
        Deactivate the maintenance plan.
        
        Returns:
            self for chaining
        """
        self._maintenance_plan.status = 'Inactive'
        db.session.commit()
        return self
    
    def calculate_next_due_date(self, last_maintenance_date: Optional[datetime] = None) -> Optional[datetime]:
        """
        Calculate next due date based on plan frequency.
        
        Args:
            last_maintenance_date: Last maintenance date (defaults to now)
            
        Returns:
            Next due date or None if cannot be calculated
        """
        if not last_maintenance_date:
            last_maintenance_date = datetime.utcnow()
        
        frequency_type = self._maintenance_plan.frequency_type
        
        if frequency_type == 'hours' and self._maintenance_plan.delta_hours:
            return last_maintenance_date + timedelta(hours=self._maintenance_plan.delta_hours)
        elif frequency_type == 'meter1' and self._maintenance_plan.delta_m1:
            # Meter-based calculations would need current meter reading
            # This is a simplified version
            return None
        elif frequency_type == 'meter2' and self._maintenance_plan.delta_m2:
            return None
        elif frequency_type == 'meter3' and self._maintenance_plan.delta_m3:
            return None
        elif frequency_type == 'meter4' and self._maintenance_plan.delta_m4:
            return None
        elif frequency_type == 'days':
            # Default to 30 days if no specific delta
            delta_days = self._maintenance_plan.delta_hours / 24 if self._maintenance_plan.delta_hours else 30
            return last_maintenance_date + timedelta(days=delta_days)
        
        return None
    
    def get_matching_assets(self) -> List[Asset]:
        """
        Get assets that match this maintenance plan's criteria.
        
        Returns:
            List of Asset instances that match the plan's asset_type_id and model_id
        """
        query = Asset.query
        
        if self._maintenance_plan.asset_type_id:
            # Filter by asset type through make_model
            from app.data.core.asset_info.make_model import MakeModel
            query = query.join(MakeModel).filter(MakeModel.asset_type_id == self._maintenance_plan.asset_type_id)
        
        if self._maintenance_plan.model_id:
            query = query.filter(Asset.make_model_id == self._maintenance_plan.model_id)
        
        return query.all()
    
    def create_maintenance_event(
        self,
        asset_id: int,
        planned_start_datetime: Optional[datetime] = None,
        user_id: Optional[int] = None
    ) -> Optional[MaintenanceActionSet]:
        """
        Create a maintenance event from this plan for a specific asset.
        
        This is a high-level method that should delegate to MaintenanceFactory
        for the actual creation logic.
        
        Args:
            asset_id: Asset ID to create maintenance for
            planned_start_datetime: Planned start datetime (defaults to now)
            user_id: User ID creating the event
            
        Returns:
            Created MaintenanceActionSet or None if creation failed
        """
        # Import here to avoid circular imports
        from app.buisness.maintenance.factories.maintenance_factory import MaintenanceFactory
        
        if not planned_start_datetime:
            planned_start_datetime = datetime.utcnow()
        
        # Use factory to create maintenance event from template
        template_action_set = self._maintenance_plan.template_action_set
        if not template_action_set:
            return None
        
        maintenance_action_set = MaintenanceFactory.create_from_template(
            template_action_set_id=template_action_set.id,
            asset_id=asset_id,
            maintenance_plan_id=self._maintenance_plan_id,
            planned_start_datetime=planned_start_datetime,
            user_id=user_id
        )
        
        return maintenance_action_set
    
    @property
    def maintenance_action_sets(self) -> List[MaintenanceActionSet]:
        """
        Get all maintenance action sets created from this plan.
        
        Returns:
            List of MaintenanceActionSet instances
        """
        return list(self._maintenance_plan.maintenance_action_sets)
    
    # Query methods
    @staticmethod
    def get_all() -> List['MaintenancePlanContext']:
        """
        Get all maintenance plans.
        
        Returns:
            List of MaintenancePlanContext instances
        """
        plans = MaintenancePlan.query.all()
        return [MaintenancePlanContext(plan) for plan in plans]
    
    @staticmethod
    def get_active() -> List['MaintenancePlanContext']:
        """
        Get all active maintenance plans.
        
        Returns:
            List of MaintenancePlanContext instances
        """
        plans = MaintenancePlan.query.filter_by(status='Active').all()
        return [MaintenancePlanContext(plan) for plan in plans]
    
    @staticmethod
    def get_by_asset_type(asset_type_id: int) -> List['MaintenancePlanContext']:
        """
        Get maintenance plans by asset type.
        
        Args:
            asset_type_id: Asset type ID
            
        Returns:
            List of MaintenancePlanContext instances
        """
        plans = MaintenancePlan.query.filter_by(asset_type_id=asset_type_id).all()
        return [MaintenancePlanContext(plan) for plan in plans]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize maintenance plan to dictionary.
        
        Returns:
            Dictionary representation of maintenance plan
        """
        return {
            'id': self._maintenance_plan_id,
            'name': self._maintenance_plan.name,
            'description': self._maintenance_plan.description,
            'status': self._maintenance_plan.status,
            'asset_type_id': self._maintenance_plan.asset_type_id,
            'model_id': self._maintenance_plan.model_id,
            'template_action_set_id': self._maintenance_plan.template_action_set_id,
            'frequency_type': self._maintenance_plan.frequency_type,
            'delta_hours': self._maintenance_plan.delta_hours,
            'delta_m1': self._maintenance_plan.delta_m1,
            'delta_m2': self._maintenance_plan.delta_m2,
            'delta_m3': self._maintenance_plan.delta_m3,
            'delta_m4': self._maintenance_plan.delta_m4,
        }
    
    def refresh(self):
        """Refresh cached data from database"""
        from app import db
        db.session.refresh(self._maintenance_plan)
    
    def __repr__(self):
        return f'<MaintenancePlanContext id={self._maintenance_plan_id} name="{self.name}" status={self.status}>'

