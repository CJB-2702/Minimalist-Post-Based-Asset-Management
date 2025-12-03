"""
Maintenance Factory
Main factory for creating complete maintenance workflows from templates.
Coordinates all factories, handles transaction management, and validates business rules.
"""

from typing import Optional
from datetime import datetime
from app import db
from app.logger import get_logger
from app.buisness.maintenance.factories.maintenance_action_set_factory import MaintenanceActionSetFactory
from app.buisness.maintenance.factories.action_factory import ActionFactory
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.maintenance.templates.template_action_sets import TemplateActionSet

logger = get_logger("asset_management.buisness.maintenance.factories")


class MaintenanceFactory:
    """
    Main factory for creating complete maintenance workflows from templates.
    
    Responsibilities:
    - Coordinate all factories
    - Create complete maintenance event with all actions, parts, tools
    - Handle transaction management
    - Validate business rules
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
        notes: Optional[str] = None,
        commit: bool = True
    ) -> MaintenanceActionSet:
        """
        Create complete maintenance event from template.
        
        This is the main entry point for creating maintenance events from templates.
        It coordinates the creation of:
        - MaintenanceActionSet (with Event)
        - All Actions (with PartDemands and ActionTools)
        
        Process: Template → Base (with Event creation)
        1. Create MaintenanceActionSet from TemplateActionSet
        2. Create Event (ONE-TO-ONE relationship)
        3. Create Action records from TemplateActionItems
        4. Create PartDemand records from TemplatePartDemands (standalone copies)
        5. Create ActionTool records from TemplateActionTools (standalone copies)
        
        Args:
            template_action_set_id: Template action set ID to copy from
            asset_id: Asset ID for the maintenance event
            planned_start_datetime: Planned start datetime (defaults to now)
            maintenance_plan_id: Optional maintenance plan ID
            user_id: User ID creating the maintenance event
            assigned_user_id: Optional user ID to assign the maintenance to
            assigned_by_id: Optional user ID of the manager assigning the maintenance
            priority: Priority level (Low, Medium, High, Critical) - defaults to 'Medium'
            notes: Optional assignment notes to add as event comment
            commit: Whether to commit the transaction (default: True)
            
        Returns:
            Created MaintenanceActionSet instance with all related records
            
        Raises:
            ValueError: If template not found, invalid parameters, or business rule violation
        """
        # Validate template exists
        template_action_set = TemplateActionSet.query.get_or_404(template_action_set_id)
        
        if not template_action_set.is_active:
            logger.warning(f"Creating maintenance from inactive template: {template_action_set_id}")
        
        # Set defaults
        if not planned_start_datetime:
            planned_start_datetime = datetime.utcnow()
        
        if not user_id:
            user_id = template_action_set.created_by_id
        
        try:
            # Step 1: Create MaintenanceActionSet (this also creates the Event)
            maintenance_action_set = MaintenanceActionSetFactory.create_from_template(
                template_action_set_id=template_action_set_id,
                asset_id=asset_id,
                planned_start_datetime=planned_start_datetime,
                maintenance_plan_id=maintenance_plan_id,
                user_id=user_id,
                assigned_user_id=assigned_user_id,
                assigned_by_id=assigned_by_id,
                priority=priority,
                commit=False  # Don't commit yet, wait for all actions
            )
            
            # Step 2: Create all Actions from TemplateActionItems
            # This also creates PartDemands and ActionTools
            actions = ActionFactory.create_from_template_action_set(
                template_action_set_id=template_action_set_id,
                maintenance_action_set_id=maintenance_action_set.id,
                user_id=user_id,
                commit=False  # Don't commit yet
            )
            
            # Validate business rules
            if not actions:
                logger.warning(f"No actions created from template {template_action_set_id}")
            
            # Add assignment comment if notes provided or if assigned
            if notes or assigned_user_id:
                from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
                maintenance_context = MaintenanceContext.from_maintenance_action_set(maintenance_action_set)
                
                # Build comment text
                comment_parts = []
                if assigned_user_id:
                    from app.data.core.user_info.user import User
                    technician = User.query.get(assigned_user_id)
                    technician_name = technician.username if technician else f"User {assigned_user_id}"
                    comment_parts.append(f"Assigned to {technician_name}")
                
                if notes:
                    comment_parts.append(f"Notes: {notes}")
                
                if comment_parts:
                    comment_text = " | ".join(comment_parts)
                    maintenance_context.add_comment(
                        user_id=user_id or assigned_by_id or maintenance_action_set.created_by_id,
                        content=comment_text,
                        is_human_made=True
                    )
            
            # Commit all changes
            if commit:
                db.session.commit()
                logger.info(
                    f"Created complete maintenance event {maintenance_action_set.id} "
                    f"from template {template_action_set_id} with {len(actions)} actions"
                )
            else:
                db.session.flush()
                logger.info(
                    f"Created complete maintenance event {maintenance_action_set.id} "
                    f"from template {template_action_set_id} with {len(actions)} actions (not committed)"
                )
            
            return maintenance_action_set
            
        except Exception as e:
            # Rollback on error
            db.session.rollback()
            logger.error(f"Failed to create maintenance from template {template_action_set_id}: {str(e)}")
            raise
    
    @classmethod
    def create_from_maintenance_plan(
        cls,
        maintenance_plan_id: int,
        asset_id: int,
        planned_start_datetime: Optional[datetime] = None,
        user_id: Optional[int] = None,
        commit: bool = True
    ) -> MaintenanceActionSet:
        """
        Create maintenance event from maintenance plan.
        
        Args:
            maintenance_plan_id: Maintenance plan ID
            asset_id: Asset ID for the maintenance event
            planned_start_datetime: Planned start datetime (defaults to now)
            user_id: User ID creating the maintenance event
            commit: Whether to commit the transaction (default: True)
            
        Returns:
            Created MaintenanceActionSet instance
            
        Raises:
            ValueError: If maintenance plan not found or invalid
        """
        from app.data.maintenance.planning.maintenance_plans import MaintenancePlan
        
        maintenance_plan = MaintenancePlan.query.get_or_404(maintenance_plan_id)
        
        if not maintenance_plan.template_action_set_id:
            raise ValueError(f"Maintenance plan {maintenance_plan_id} has no template action set")
        
        return cls.create_from_template(
            template_action_set_id=maintenance_plan.template_action_set_id,
            asset_id=asset_id,
            planned_start_datetime=planned_start_datetime,
            maintenance_plan_id=maintenance_plan_id,
            user_id=user_id,
            commit=commit
        )

