"""
Assign Monitor Service
Service layer for Create & Assign Portal presentation operations.
Handles data retrieval and formatting for event creation and assignment workflows.
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from app.buisness.maintenance.factories.maintenance_factory import MaintenanceFactory
from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
from app.buisness.maintenance.templates.template_maintenance_context import TemplateMaintenanceContext
from app.data.maintenance.templates.template_action_sets import TemplateActionSet
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.core.asset_info.asset import Asset
from app.data.core.user_info.user import User
from app.data.core.asset_info.asset_type import AssetType
from app.data.core.asset_info.make_model import MakeModel
from app.data.core.major_location import MajorLocation
from app import db


class AssignMonitorService:
    """
    Service for Create & Assign Portal presentation operations.
    Handles data retrieval and formatting for event creation and assignment workflows.
    """
    
    @staticmethod
    def get_active_templates(
        asset_type_id: Optional[int] = None,
        make_model_id: Optional[int] = None,
        search: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get active templates for selection with optional filtering.
        
        Args:
            asset_type_id: Filter by asset type ID
            make_model_id: Filter by make/model ID
            search: Search term for task name (partial match)
            limit: Maximum number of results to return (None for all)
            
        Returns:
            Tuple of (list of template dictionaries, total count)
        """
        query = TemplateActionSet.query.filter_by(is_active=True)
        
        # Apply filters
        if asset_type_id:
            query = query.filter_by(asset_type_id=asset_type_id)
        if make_model_id:
            query = query.filter_by(make_model_id=make_model_id)
        if search:
            query = query.filter(TemplateActionSet.task_name.ilike(f'%{search}%'))
        
        # Get total count before limiting
        total_count = query.count()
        
        # Apply limit if specified
        if limit:
            templates = query.order_by(TemplateActionSet.task_name).limit(limit).all()
        else:
            templates = query.order_by(TemplateActionSet.task_name).all()
        
        result = []
        
        for template in templates:
            template_context = TemplateMaintenanceContext(template.id)
            summary = template_context.summary()
            
            result.append({
                'id': template.id,
                'task_name': template.task_name,
                'description': template.description,
                'revision': template.revision,
                'estimated_duration': template.estimated_duration,
                'total_actions': summary.get('total_action_items', 0),
                'estimated_cost': summary.get('total_estimated_cost', 0),
            })
        
        return result, total_count
    
    @staticmethod
    def get_template_summary(template_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed summary of a specific template for preview.
        
        Args:
            template_id: Template action set ID
            
        Returns:
            Dictionary with detailed template information or None if not found
        """
        template = TemplateActionSet.query.get(template_id)
        if not template or not template.is_active:
            return None
        
        template_context = TemplateMaintenanceContext(template.id)
        summary = template_context.summary()
        
        # Get actions with details
        from app.buisness.maintenance.templates.template_action_context import TemplateActionContext
        actions = TemplateActionContext.get_by_template_action_set(template_id)
        
        # Get parts summary
        parts_summary = []
        for action in actions:
            for part_demand in action.part_demands:
                if part_demand.part:
                    parts_summary.append({
                        'part_name': part_demand.part.part_name,
                        'quantity': part_demand.quantity_required,
                        'expected_cost': part_demand.expected_cost,
                    })
        
        # Get tools summary
        tools_summary = []
        for action in actions:
            for tool in action.action_tools:
                if tool.tool:
                    tools_summary.append({
                        'tool_name': tool.tool.tool_name,
                        'quantity': tool.quantity_required,
                    })
        
        return {
            'id': template.id,
            'task_name': template.task_name,
            'description': template.description,
            'revision': template.revision,
            'estimated_duration': template.estimated_duration,
            'total_actions': summary.get('total_action_items', 0),
            'estimated_cost': summary.get('total_estimated_cost', 0),
            'actions': [
                {
                    'sequence_order': action._struct.sequence_order,
                    'action_name': action._struct.action_name,
                    'description': action._struct.description,
                    'estimated_duration': action._struct.template_action_item.estimated_duration if action._struct.template_action_item else None,
                }
                for action in actions
            ],
            'parts_summary': parts_summary,
            'tools_summary': tools_summary,
        }
    
    @staticmethod
    def get_available_assets(
        asset_type_id: Optional[int] = None,
        make_model_id: Optional[int] = None,
        location_id: Optional[int] = None,
        search: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get assets available for assignment with optional filtering.
        
        Args:
            asset_type_id: Filter by asset type ID
            make_model_id: Filter by make/model ID
            location_id: Filter by location ID
            search: Search term for asset name or serial number (partial match)
            limit: Maximum number of results to return (None for all)
            
        Returns:
            Tuple of (list of asset dictionaries, total count)
        """
        query = Asset.query
        
        # Apply filters
        if asset_type_id:
            query = query.join(MakeModel).filter(MakeModel.asset_type_id == asset_type_id)
        if make_model_id:
            query = query.filter(Asset.make_model_id == make_model_id)
        if location_id:
            query = query.filter(Asset.major_location_id == location_id)
        if search:
            query = query.filter(
                (Asset.name.ilike(f'%{search}%')) |
                (Asset.serial_number.ilike(f'%{search}%'))
            )
        
        # Get total count before limiting
        total_count = query.count()
        
        # Apply limit if specified
        if limit:
            assets = query.order_by(Asset.name).limit(limit).all()
        else:
            assets = query.order_by(Asset.name).limit(200).all()
        
        result = []
        
        for asset in assets:
            # Get recent maintenance history (last 5 events)
            recent_maintenance = MaintenanceActionSet.query.filter_by(
                asset_id=asset.id
            ).order_by(MaintenanceActionSet.created_at.desc()).limit(5).all()
            
            result.append({
                'id': asset.id,
                'name': asset.name,
                'serial_number': asset.serial_number,
                'asset_type': asset.make_model.asset_type.name if asset.make_model and asset.make_model.asset_type else None,
                'make_model': f"{asset.make_model.make} {asset.make_model.model}" if asset.make_model else None,
                'location': asset.major_location.name if asset.major_location else None,
                'status': asset.status,
                'recent_maintenance': [
                    {
                        'id': m.id,
                        'task_name': m.task_name,
                        'status': m.status,
                        'created_at': m.created_at.isoformat() if m.created_at else None,
                    }
                    for m in recent_maintenance
                ],
            })
        
        return result, total_count
    
    @staticmethod
    def get_available_technicians(
        search: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get list of active technicians with current workload information.
        
        Args:
            search: Search term for username or email (partial match)
            limit: Maximum number of results to return (None for all)
        
        Returns:
            Tuple of (list of technician dictionaries with workload counts, total count)
        """
        # Get all active users (technicians)
        # Note: In a real system, you might filter by role/permissions
        query = User.query.filter_by(is_active=True)
        
        # Apply search filter
        if search:
            query = query.filter(
                (User.username.ilike(f'%{search}%')) |
                (User.email.ilike(f'%{search}%'))
            )
        
        # Get total count before limiting
        total_count = query.count()
        
        # Apply limit if specified
        if limit:
            technicians = query.order_by(User.username).limit(limit).all()
        else:
            technicians = query.order_by(User.username).all()
        
        result = []
        
        for tech in technicians:
            # Count currently assigned maintenance action sets
            workload_count = MaintenanceActionSet.query.filter(
                MaintenanceActionSet.assigned_user_id == tech.id,
                MaintenanceActionSet.status.in_(['Planned', 'In Progress', 'Delayed'])
            ).count()
            
            result.append({
                'id': tech.id,
                'username': tech.username,
                'email': tech.email,
                'workload_count': workload_count,
            })
        
        return result, total_count
    
    @staticmethod
    def create_event_from_template(
        template_action_set_id: int,
        asset_id: int,
        planned_start_datetime: Optional[datetime] = None,
        maintenance_plan_id: Optional[int] = None,
        user_id: Optional[int] = None,
        assigned_user_id: Optional[int] = None,
        assigned_by_id: Optional[int] = None,
        priority: str = 'Medium',
        notes: Optional[str] = None
    ) -> MaintenanceActionSet:
        """
        Create a maintenance event from a template.
        
        Args:
            template_action_set_id: Template action set ID
            asset_id: Asset ID for the maintenance event
            planned_start_datetime: Planned start datetime
            maintenance_plan_id: Optional maintenance plan ID
            user_id: User ID creating the maintenance event
            assigned_user_id: Optional user ID to assign the maintenance to
            assigned_by_id: Optional user ID of the manager assigning the maintenance
            priority: Priority level (Low, Medium, High, Critical)
            notes: Optional assignment notes
            
        Returns:
            Created MaintenanceActionSet instance
            
        Raises:
            ValueError: If template not found, asset not found, or invalid parameters
        """
        # Validate template exists and is active
        template = TemplateActionSet.query.get(template_action_set_id)
        if not template:
            raise ValueError(f"Template {template_action_set_id} not found")
        if not template.is_active:
            raise ValueError(f"Template {template_action_set_id} is not active")
        
        # Validate asset exists
        asset = Asset.query.get(asset_id)
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        
        # Validate technician if assigned
        if assigned_user_id:
            technician = User.query.get(assigned_user_id)
            if not technician or not technician.is_active:
                raise ValueError(f"Technician {assigned_user_id} not found or not active")
        
        # Create event using factory
        maintenance_action_set = MaintenanceFactory.create_from_template(
            template_action_set_id=template_action_set_id,
            asset_id=asset_id,
            planned_start_datetime=planned_start_datetime,
            maintenance_plan_id=maintenance_plan_id,
            user_id=user_id,
            assigned_user_id=assigned_user_id,
            assigned_by_id=assigned_by_id,
            priority=priority,
            notes=notes,
            commit=True
        )
        
        return maintenance_action_set
    
    @staticmethod
    def assign_event(
        event_id: int,
        assigned_user_id: int,
        assigned_by_id: int,
        planned_start_datetime: Optional[datetime] = None,
        priority: Optional[str] = None,
        notes: Optional[str] = None
    ) -> MaintenanceActionSet:
        """
        Assign or reassign a maintenance event to a technician.
        
        Args:
            event_id: Event ID (MaintenanceActionSet has ONE-TO-ONE with Event)
            assigned_user_id: User ID to assign the maintenance to
            assigned_by_id: User ID of the manager assigning the maintenance
            planned_start_datetime: Optional planned start datetime to update
            priority: Optional priority to update
            notes: Optional assignment notes
            
        Returns:
            Updated MaintenanceActionSet instance
            
        Raises:
            ValueError: If event not found, technician not found, or invalid parameters
        """
        # Validate technician
        technician = User.query.get(assigned_user_id)
        if not technician or not technician.is_active:
            raise ValueError(f"Technician {assigned_user_id} not found or not active")
        
        # Get maintenance context and assignment manager
        maintenance_context = MaintenanceContext.from_event(event_id)
        
        if not maintenance_context or not maintenance_context.struct:
            raise ValueError(f"Maintenance event {event_id} not found")
        
        # Assign event using assignment manager
        assignment_manager = maintenance_context.get_assignment_manager()
        comment_text = assignment_manager.assign(
            assigned_user_id=assigned_user_id,
            assigned_by_id=assigned_by_id,
            planned_start_datetime=planned_start_datetime,
            priority=priority,
            notes=notes
        )
        
        # Add comment to event
        maintenance_context.add_comment(
            user_id=assigned_by_id,
            content=comment_text,
            is_human_made=True
        )
        
        # Return the maintenance_action_set from the context
        return maintenance_context.struct.maintenance_action_set
    
    @staticmethod
    def get_unassigned_events(
        asset_id: Optional[int] = None,
        asset_type_id: Optional[int] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 20
    ):
        """
        Get unassigned maintenance events with optional filtering and pagination.
        
        Args:
            asset_id: Filter by asset ID
            asset_type_id: Filter by asset type ID
            status: Filter by status
            priority: Filter by priority
            date_from: Filter by planned start date (from)
            date_to: Filter by planned start date (to)
            page: Page number for pagination (default: 1)
            per_page: Items per page (default: 20)
            
        Returns:
            Pagination object with unassigned event dictionaries formatted for presentation
        """
        query = MaintenanceActionSet.query.filter(
            MaintenanceActionSet.assigned_user_id.is_(None)
        )
        
        # Default filter: exclude "Complete" status if no status filter provided
        if status:
            query = query.filter_by(status=status)
        else:
            # Exclude completed events by default
            query = query.filter(MaintenanceActionSet.status != 'Complete')
        
        # Apply other filters
        if asset_id:
            query = query.filter_by(asset_id=asset_id)
        if asset_type_id:
            query = query.join(Asset).join(Asset.make_model).filter(
                Asset.make_model.has(asset_type_id=asset_type_id)
            )
        if priority:
            query = query.filter_by(priority=priority)
        if date_from:
            query = query.filter(MaintenanceActionSet.planned_start_datetime >= date_from)
        if date_to:
            query = query.filter(MaintenanceActionSet.planned_start_datetime <= date_to)
        
        # Order by planned start datetime (most recent first), then by created_at
        # In most databases, NULLs sort last in DESC order, but we'll use a CASE to be explicit
        from sqlalchemy import case, desc
        query = query.order_by(
            case(
                (MaintenanceActionSet.planned_start_datetime.is_(None), 1),
                else_=0
            ),
            desc(MaintenanceActionSet.planned_start_datetime),
            desc(MaintenanceActionSet.created_at)
        )
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Format results
        result = []
        for event in pagination.items:
            result.append({
                'id': event.id,
                'event_id': event.event_id,
                'task_name': event.task_name,
                'asset_id': event.asset_id,
                'asset_name': event.asset.name if event.asset else None,
                'status': event.status,
                'priority': event.priority,
                'planned_start_datetime': event.planned_start_datetime.isoformat() if event.planned_start_datetime else None,
                'created_at': event.created_at.isoformat() if event.created_at else None,
            })
        
        # Create a pagination-like object with formatted items
        class PaginatedResults:
            def __init__(self, items, pagination_obj):
                self.items = items
                self.page = pagination_obj.page
                self.per_page = pagination_obj.per_page
                self.total = pagination_obj.total
                self.pages = pagination_obj.pages
                self.has_prev = pagination_obj.has_prev
                self.has_next = pagination_obj.has_next
                self.prev_num = pagination_obj.prev_num
                self.next_num = pagination_obj.next_num
                self.iter_pages = pagination_obj.iter_pages
        
        return PaginatedResults(result, pagination)
    
    @staticmethod
    def bulk_assign_events(
        event_ids: List[int],
        assigned_user_id: int,
        assigned_by_id: int,
        notes: Optional[str] = None
    ) -> Tuple[int, int, List[int]]:
        """
        Assign multiple events to the same technician in a single operation.
        
        Args:
            event_ids: List of event IDs to assign
            assigned_user_id: User ID to assign all events to
            assigned_by_id: User ID of the manager assigning the events
            notes: Optional notes to apply to all assignments
            
        Returns:
            Tuple of (success_count, failed_count, failed_event_ids)
        """
        # Validate technician
        technician = User.query.get(assigned_user_id)
        if not technician or not technician.is_active:
            raise ValueError(f"Technician {assigned_user_id} not found or not active")
        
        success_count = 0
        failed_count = 0
        failed_event_ids = []
        
        for event_id in event_ids:
            try:
                # Get maintenance action set by event_id
                maintenance_action_set = MaintenanceActionSet.query.filter_by(
                    event_id=event_id
                ).first()
                
                if not maintenance_action_set:
                    failed_count += 1
                    failed_event_ids.append(event_id)
                    continue
                
                # Skip if already assigned
                if maintenance_action_set.assigned_user_id:
                    failed_count += 1
                    failed_event_ids.append(event_id)
                    continue
                
                # Assign using service method
                AssignMonitorService.assign_event(
                    event_id=event_id,
                    assigned_user_id=assigned_user_id,
                    assigned_by_id=assigned_by_id,
                    notes=f"Bulk assigned. {notes}" if notes else "Bulk assigned"
                )
                
                success_count += 1
                
            except Exception as e:
                failed_count += 1
                failed_event_ids.append(event_id)
                db.session.rollback()
        
        return success_count, failed_count, failed_event_ids
    
    @staticmethod
    def get_event_summary(event_id: int) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive summary of a maintenance event.
        
        Args:
            event_id: Event ID (MaintenanceActionSet has ONE-TO-ONE with Event)
            
        Returns:
            Dictionary with comprehensive event information or None if not found
        """
        try:
            maintenance_context = MaintenanceContext.from_event(event_id)
        except ValueError:
            return None
        
        maintenance_action_set = maintenance_context.maintenance_action_set
        
        return {
            'id': maintenance_action_set.id,
            'event_id': maintenance_action_set.event_id,
            'task_name': maintenance_action_set.task_name,
            'description': maintenance_action_set.description,
            'status': maintenance_action_set.status,
            'priority': maintenance_action_set.priority,
            'asset_id': maintenance_action_set.asset_id,
            'asset_name': maintenance_action_set.asset.name if maintenance_action_set.asset else None,
            'assigned_user_id': maintenance_action_set.assigned_user_id,
            'assigned_user_name': maintenance_action_set.assigned_user.username if maintenance_action_set.assigned_user else None,
            'assigned_by_id': maintenance_action_set.assigned_by_id,
            'assigned_by_name': maintenance_action_set.assigned_by.username if maintenance_action_set.assigned_by else None,
            'planned_start_datetime': maintenance_action_set.planned_start_datetime.isoformat() if maintenance_action_set.planned_start_datetime else None,
            'total_actions': maintenance_context.total_actions,
            'completed_actions': maintenance_context.completed_actions,
            'completion_percentage': maintenance_context.completion_percentage,
        }

