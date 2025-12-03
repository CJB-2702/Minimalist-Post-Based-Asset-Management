"""
Maintenance Action Set Factory
Factory for creating MaintenanceActionSet from TemplateActionSet.
Handles Event creation, metadata copying, and relationship setup.
"""

from typing import Optional
from datetime import datetime
from app import db
from app.logger import get_logger
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.maintenance.templates.template_action_sets import TemplateActionSet
from app.data.core.event_info.event import Event

logger = get_logger("asset_management.buisness.maintenance.factories")


class MaintenanceActionSetFactory:
    """
    Factory for creating MaintenanceActionSet from TemplateActionSet.
    
    Responsibilities:
    - Copy metadata from template
    - Create and link Event (ONE-TO-ONE relationship)
    - Set up relationships (asset, plan)
    - Initialize status and planned_start_datetime
    - Ensure only one MaintenanceActionSet per Event
    """
    
    @classmethod
    def create_from_template(
        cls,
        template_action_set_id: int,
        asset_id: int,
        planned_start_datetime: Optional[datetime] = None,
        maintenance_plan_id: Optional[int] = None,
        user_id: Optional[int] = None,
        assigned_user_id: Optional[int] = None,
        assigned_by_id: Optional[int] = None,
        priority: str = 'Medium',
        commit: bool = True
    ) -> MaintenanceActionSet:
        """
        Create MaintenanceActionSet from TemplateActionSet.
        
        Args:
            template_action_set_id: Template action set ID to copy from
            asset_id: Asset ID for the maintenance event
            planned_start_datetime: Planned start datetime (defaults to now)
            maintenance_plan_id: Optional maintenance plan ID
            user_id: User ID creating the maintenance event
            assigned_user_id: Optional user ID to assign the maintenance to
            assigned_by_id: Optional user ID of the manager assigning the maintenance
            priority: Priority level (Low, Medium, High, Critical) - defaults to 'Medium'
            commit: Whether to commit the transaction (default: True)
            
        Returns:
            Created MaintenanceActionSet instance
            
        Raises:
            ValueError: If template not found or invalid parameters
        """
        # Get template action set
        template_action_set = TemplateActionSet.query.get_or_404(template_action_set_id)
        
        if not template_action_set.is_active:
            logger.warning(f"Creating maintenance from inactive template: {template_action_set_id}")
        
        # Set defaults
        if not planned_start_datetime:
            planned_start_datetime = datetime.utcnow()
        
        if not user_id:
            # Try to get from template or use system user
            user_id = template_action_set.created_by_id
        
        # Create Event first (ONE-TO-ONE relationship)
        event_id = Event.add_event(
            event_type='maintenance',
            description=f'Maintenance: {template_action_set.task_name}',
            user_id=user_id,
            asset_id=asset_id
        )
        
        # Check if MaintenanceActionSet already exists for this event
        existing = MaintenanceActionSet.query.filter_by(event_id=event_id).first()
        if existing:
            raise ValueError(f"MaintenanceActionSet already exists for event {event_id} (ONE-TO-ONE relationship)")
        
        # Create MaintenanceActionSet
        maintenance_action_set = MaintenanceActionSet(
            # Event coupling - REQUIRED, ONE-TO-ONE
            event_id=event_id,
            
            # Template reference
            template_action_set_id=template_action_set_id,
            
            # Asset
            asset_id=asset_id,
            
            # Plan
            maintenance_plan_id=maintenance_plan_id,
            
            # Copy metadata from VirtualActionSet
            # Note: description is a computed property (from task_name), don't set it
            task_name=template_action_set.task_name,
            estimated_duration=template_action_set.estimated_duration,
            safety_review_required=template_action_set.safety_review_required,
            staff_count=template_action_set.staff_count,
            parts_cost=template_action_set.parts_cost,
            labor_hours=template_action_set.labor_hours,
            
            # Planning
            planned_start_datetime=planned_start_datetime,
            
            # Execution tracking - initialize
            status='Planned',
            priority=priority,
            
            # Assignment
            assigned_user_id=assigned_user_id,
            assigned_by_id=assigned_by_id,
            
            # Audit fields
            created_by_id=user_id,
            updated_by_id=user_id
        )
        
        db.session.add(maintenance_action_set)
        
        if commit:
            db.session.commit()
            logger.info(f"Created MaintenanceActionSet {maintenance_action_set.id} from template {template_action_set_id}")
        else:
            db.session.flush()
            logger.info(f"Created MaintenanceActionSet {maintenance_action_set.id} from template {template_action_set_id} (not committed)")
        
        return maintenance_action_set

