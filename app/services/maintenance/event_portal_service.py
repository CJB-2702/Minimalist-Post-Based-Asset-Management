"""
Event Portal Service
Service for building queries and retrieving enhanced data for maintenance event viewing.

Provides:
- Comprehensive filtering for maintenance events
- Enhanced data retrieval (assigned users, action completion, comments)
- Query optimization with eager loading and subqueries
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from flask import Request
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import func, select, case, or_, and_, exists, desc, asc
from sqlalchemy.orm import joinedload, selectinload, Query
from app import db
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.maintenance.base.actions import Action
from app.data.core.event_info.event import Event
from app.data.core.event_info.comment import Comment
from app.data.core.asset_info.asset import Asset
from app.data.core.asset_info.make_model import MakeModel
from app.data.core.major_location import MajorLocation
from app.data.core.user_info.user import User


class EventPortalService:
    """
    Service for event portal presentation operations.
    Handles query building, filtering, and enhanced data retrieval.
    """
    
    @staticmethod
    def build_events_query(
        # Filter parameters
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_user_id: Optional[int] = None,
        created_by_user_id: Optional[int] = None,
        asset_id: Optional[int] = None,
        make_model_id: Optional[int] = None,
        major_location_id: Optional[int] = None,
        action_title: Optional[str] = None,
        has_comments_by: Optional[int] = None,
        
        # Portal-specific filters
        portal_type: str = 'manager',
        current_user_id: Optional[int] = None,
        
        # Date filters
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        
        # Search
        search_term: Optional[str] = None,
        
        # Ordering
        order_by: str = 'created_at',
        order_direction: str = 'desc'
    ) -> Query:
        """
        Build a SQLAlchemy query for maintenance events with all filters applied.
        
        Returns:
            SQLAlchemy Query object ready for pagination
        """
        query = MaintenanceActionSet.query
        
        # Portal-specific default filter
        if portal_type == 'technician' and current_user_id:
            query = query.filter(MaintenanceActionSet.assigned_user_id == current_user_id)
        
        # ============================================================================
        # BASE FILTERS - Direct fields in MaintenanceActionSet
        # ============================================================================
        
        # Status filter
        if status:
            query = query.filter(MaintenanceActionSet.status == status)
        
        # Priority filter
        if priority:
            query = query.filter(MaintenanceActionSet.priority == priority)
        
        # Assigned user filter
        if assigned_user_id:
            query = query.filter(MaintenanceActionSet.assigned_user_id == assigned_user_id)
        
        # Created by user filter
        if created_by_user_id:
            query = query.filter(MaintenanceActionSet.created_by_id == created_by_user_id)
        
        # Asset filter
        if asset_id:
            query = query.filter(MaintenanceActionSet.asset_id == asset_id)
        
        # Date filters (on planned_start_datetime)
        if date_from:
            query = query.filter(MaintenanceActionSet.planned_start_datetime >= date_from)
        if date_to:
            query = query.filter(MaintenanceActionSet.planned_start_datetime <= date_to)
        
        # Search term (searches in task_name and description)
        if search_term:
            query = query.filter(
                or_(
                    MaintenanceActionSet.task_name.ilike(f'%{search_term}%'),
                    MaintenanceActionSet.description.ilike(f'%{search_term}%')
                )
            )
        
        # ============================================================================
        # JOINED FILTERS - Require joins to related tables
        # ============================================================================
        
        # Make/Model filter (via Asset)
        if make_model_id:
            query = query.join(Asset, MaintenanceActionSet.asset_id == Asset.id)
            query = query.filter(Asset.make_model_id == make_model_id)
        
        # Major location filter (via Event or Asset)
        if major_location_id:
            query = query.join(Event, MaintenanceActionSet.event_id == Event.id)
            query = query.join(Asset, MaintenanceActionSet.asset_id == Asset.id, isouter=True)
            query = query.filter(
                or_(
                    Event.major_location_id == major_location_id,
                    Asset.major_location_id == major_location_id
                )
            )
        
        # Action title filter (via Action) - one-to-many, use EXISTS
        if action_title:
            action_subq = (
                select(1)
                .where(
                    Action.maintenance_action_set_id == MaintenanceActionSet.id,
                    Action.action_name.ilike(f'%{action_title}%')
                )
            )
            query = query.filter(exists(action_subq))
        
        # Has comments by user filter (via Event → Comment) - one-to-many, use EXISTS
        if has_comments_by:
            comment_subq = (
                select(1)
                .select_from(Comment)
                .join(Event, Comment.event_id == Event.id)
                .where(
                    Event.id == MaintenanceActionSet.event_id,
                    Comment.created_by_id == has_comments_by,
                    Comment.user_viewable.is_(None)  # Only visible comments
                )
            )
            query = query.filter(exists(comment_subq))
        
        # ============================================================================
        # ORDERING
        # ============================================================================
        
        # Special handling for ordering by last_comment_date
        if order_by == 'last_comment_date':
            # Create subquery for last comment date per event
            # If has_comments_by is set, only consider comments by that user
            comment_filter = Comment.user_viewable.is_(None)  # Only visible comments
            if has_comments_by:
                comment_filter = and_(
                    Comment.user_viewable.is_(None),
                    Comment.created_by_id == has_comments_by
                )
            
            last_comment_subq = (
                select(
                    Comment.event_id,
                    func.max(Comment.created_at).label('last_comment_date')
                )
                .where(comment_filter)
                .group_by(Comment.event_id)
                .subquery()
            )
            
            # Join with the subquery and order by last comment date
            query = query.join(Event, MaintenanceActionSet.event_id == Event.id)
            query = query.outerjoin(
                last_comment_subq,
                Event.id == last_comment_subq.c.event_id
            )
            
            # Use CASE to handle NULLs (put them last)
            if order_direction == 'desc':
                query = query.order_by(
                    case(
                        (last_comment_subq.c.last_comment_date.is_(None), 1),
                        else_=0
                    ),
                    desc(last_comment_subq.c.last_comment_date),
                    desc(MaintenanceActionSet.created_at)  # Secondary sort
                )
            else:
                query = query.order_by(
                    case(
                        (last_comment_subq.c.last_comment_date.is_(None), 1),
                        else_=0
                    ),
                    asc(last_comment_subq.c.last_comment_date),
                    asc(MaintenanceActionSet.created_at)  # Secondary sort
                )
        else:
            # Standard ordering by MaintenanceActionSet columns
            order_column = getattr(MaintenanceActionSet, order_by, MaintenanceActionSet.created_at)
            if order_direction == 'desc':
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())
        
        return query
    
    @staticmethod
    def get_events_with_enhanced_data(
        query: Query,
        page: int = 1,
        per_page: int = 20
    ) -> Pagination:
        """
        Execute query with pagination and add enhanced data to each event.
        
        Enhanced data includes:
        - assigned_user (User object)
        - created_by_user (User object)
        - asset (Asset object with make_model)
        - major_location (MajorLocation object)
        - action_completion_fraction (float: completed/total)
        - total_actions (int)
        - completed_actions (int)
        - last_comment_date (datetime or None)
        - last_comment_by (User or None)
        
        Returns:
            Flask-SQLAlchemy Pagination object with enhanced items
        """
        # Add eager loading for relationships
        query = query.options(
            joinedload(MaintenanceActionSet.assigned_user),
            joinedload(MaintenanceActionSet.created_by),
            joinedload(MaintenanceActionSet.asset).joinedload(Asset.make_model),
            joinedload(MaintenanceActionSet.asset).joinedload(Asset.major_location),
            joinedload(MaintenanceActionSet.event).joinedload(Event.major_location),
            joinedload(MaintenanceActionSet.event)  # Load event itself
        )
        
        # Paginate
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Get event IDs for batch queries
        event_ids = [event.event_id for event in pagination.items if event.event_id]
        
        # Batch load last comments for all events
        last_comments = EventPortalService._get_last_comments_batch(event_ids)
        
        # Batch load action counts for all events
        action_counts = EventPortalService._get_action_counts_batch([event.id for event in pagination.items])
        
        # Add enhanced data to each event
        for event in pagination.items:
            enhanced_data = EventPortalService.get_event_enhanced_data(
                event,
                last_comments.get(event.event_id),
                action_counts.get(event.id)
            )
            # Attach enhanced data as attributes
            for key, value in enhanced_data.items():
                setattr(event, key, value)
        
        return pagination
    
    @staticmethod
    def get_event_enhanced_data(
        event: MaintenanceActionSet,
        last_comment: Optional[Comment] = None,
        action_counts: Optional[Dict] = None
    ) -> Dict:
        """
        Get enhanced data for a single maintenance event.
        
        Args:
            event: MaintenanceActionSet instance
            last_comment: Optional pre-loaded last comment
            action_counts: Optional pre-loaded action counts dict with 'total' and 'completed'
        
        Returns:
            Dictionary with enhanced fields
        """
        # Load action counts if not provided
        if action_counts is None:
            action_counts = EventPortalService._get_action_counts(event.id)
        
        total_actions = action_counts.get('total', 0)
        completed_actions = action_counts.get('completed', 0)
        
        # Calculate completion fraction
        if total_actions > 0:
            action_completion_fraction = completed_actions / total_actions
        else:
            action_completion_fraction = 0.0
        
        # Load last comment if not provided
        if last_comment is None and event.event_id:
            last_comment = EventPortalService._get_last_comment(event.event_id)
        
        # Get major location from event or asset
        major_location = None
        if event.event and event.event.major_location:
            major_location = event.event.major_location
        elif event.asset and event.asset.major_location:
            major_location = event.asset.major_location
        
        return {
            'assigned_user': event.assigned_user,
            'created_by_user': event.created_by,
            'asset': event.asset,
            'major_location': major_location,
            'make_model': event.asset.make_model if event.asset else None,
            'action_completion_fraction': action_completion_fraction,
            'total_actions': total_actions,
            'completed_actions': completed_actions,
            'last_comment_date': last_comment.created_at if last_comment else None,
            'last_comment_by': last_comment.created_by if last_comment else None,
        }
    
    @staticmethod
    def _get_last_comment(event_id: int) -> Optional[Comment]:
        """Get the most recent visible comment for an event."""
        return Comment.query.filter(
            Comment.event_id == event_id,
            Comment.user_viewable.is_(None)  # Only visible comments
        ).order_by(Comment.created_at.desc()).first()
    
    @staticmethod
    def _get_last_comments_batch(event_ids: List[int]) -> Dict[int, Optional[Comment]]:
        """Batch load last comments for multiple events."""
        if not event_ids:
            return {}
        
        # Get last comment per event using subquery
        subq = (
            select(
                Comment.event_id,
                func.max(Comment.id).label('last_comment_id')
            )
            .where(
                Comment.event_id.in_(event_ids),
                Comment.user_viewable.is_(None)  # Only visible comments
            )
            .group_by(Comment.event_id)
            .subquery()
        )
        
        # Load the actual comments
        comments = (
            db.session.query(Comment)
            .join(subq, Comment.id == subq.c.last_comment_id)
            .options(joinedload(Comment.created_by))
            .all()
        )
        
        # Map to event IDs
        return {comment.event_id: comment for comment in comments}
    
    @staticmethod
    def _get_action_counts(event_id: int) -> Dict[str, int]:
        """Get action counts for a single event."""
        total = Action.query.filter_by(maintenance_action_set_id=event_id).count()
        completed = Action.query.filter_by(
            maintenance_action_set_id=event_id,
            status='Complete'
        ).count()
        return {'total': total, 'completed': completed}
    
    @staticmethod
    def _get_action_counts_batch(event_ids: List[int]) -> Dict[int, Dict[str, int]]:
        """Batch load action counts for multiple events."""
        if not event_ids:
            return {}
        
        # Use aggregation to count actions per event
        counts = (
            db.session.query(
                Action.maintenance_action_set_id,
                func.count(Action.id).label('total'),
                func.sum(case((Action.status == 'Complete', 1), else_=0)).label('completed')
            )
            .filter(Action.maintenance_action_set_id.in_(event_ids))
            .group_by(Action.maintenance_action_set_id)
            .all()
        )
        
        # Map to event IDs
        return {
            event_id: {'total': total or 0, 'completed': int(completed or 0)}
            for event_id, total, completed in counts
        }
    
    @staticmethod
    def get_filter_options() -> Dict:
        """
        Get all available filter options for dropdowns.
        
        Returns:
            Dictionary with filter options
        """
        return {
            'statuses': ['Planned', 'In Progress', 'Blocked', 'Delayed', 'Complete'],
            'priorities': ['Low', 'Medium', 'High', 'Critical'],
            'users': User.query.filter_by(is_active=True).order_by(User.username).all(),
            'assets': Asset.query.filter_by(status='Active').order_by(Asset.name).all(),
            'make_models': MakeModel.query.filter_by(is_active=True).order_by(MakeModel.make, MakeModel.model).all(),
            'major_locations': MajorLocation.query.filter_by(is_active=True).order_by(MajorLocation.name).all(),
        }
    
    @staticmethod
    def extract_filters_from_request(request: Request) -> Dict:
        """
        Extract filter parameters from Flask request.
        
        Returns:
            Dictionary with filter values
        """
        from datetime import datetime as dt
        
        # Parse date filters
        date_from_str = request.args.get('date_from')
        date_to_str = request.args.get('date_to')
        date_from = None
        date_to = None
        
        if date_from_str:
            try:
                date_from = dt.strptime(date_from_str, '%Y-%m-%d')
            except ValueError:
                pass
        
        if date_to_str:
            try:
                date_to = dt.strptime(date_to_str, '%Y-%m-%d')
                # Add one day and subtract one second to include the full day
                from datetime import timedelta
                date_to = date_to + timedelta(days=1) - timedelta(seconds=1)
            except ValueError:
                pass
        
        # Get page number
        page = request.args.get('page', 1, type=int)
        if page < 1:
            page = 1
        
        return {
            'status': request.args.get('status') or None,
            'priority': request.args.get('priority') or None,
            'assigned_user_id': request.args.get('assigned_user_id', type=int) or None,
            'created_by_user_id': request.args.get('created_by_user_id', type=int) or None,
            'asset_id': request.args.get('asset_id', type=int) or None,
            'make_model_id': request.args.get('make_model_id', type=int) or None,
            'major_location_id': request.args.get('major_location_id', type=int) or None,
            'action_title': request.args.get('action_title') or None,
            'has_comments_by': request.args.get('has_comments_by', type=int) or None,
            'date_from': date_from,
            'date_to': date_to,
            'search_term': request.args.get('search') or None,
            'order_by': request.args.get('order_by', 'created_at'),
            'order_direction': request.args.get('order_direction', 'desc'),
            'page': page,
        }
    
    @staticmethod
    def get_active_filters(filters: Dict) -> Dict:
        """
        Get only the active (non-None) filters for display.
        
        Returns:
            Dictionary of active filter key-value pairs
        """
        active = {}
        for key, value in filters.items():
            if value is not None and key != 'page' and key != 'order_by' and key != 'order_direction':
                active[key] = value
        return active
