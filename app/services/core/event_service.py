"""
Event Service
Presentation service for event-related data retrieval and formatting.

Handles:
- Query building and filtering for event list views
- Filter parameter extraction
"""

from typing import Dict, List, Optional, Tuple
from flask import Request
from app.data.core.event_info.event import Event
from app.data.core.asset_info.asset import Asset
from app.data.core.event_info.comment import Comment


class EventService:
    """
    Service for event presentation data.
    
    Provides methods for:
    - Building filtered event queries
    - Extracting filter parameters from requests
    """
    
    @staticmethod
    def build_event_query(
        event_type: Optional[str] = None,
        user_id: Optional[int] = None,
        asset_id: Optional[str] = None,
        major_location_id: Optional[str] = None,
        make_model_id: Optional[int] = None,
        row_count: int = 50
    ) -> Tuple:
        """
        Build event query with filters.
        
        Args:
            event_type: Filter by event type
            user_id: Filter by user ID
            asset_id: Filter by asset ID (can be 'null' string or ID)
            major_location_id: Filter by location ID (can be 'null' string or ID)
            make_model_id: Filter by make/model ID (filters events related to assets of this make/model)
            row_count: Limit for results (default: 50)
            
        Returns:
            Tuple of (query object, filters dict)
        """
        query = Event.query
        
        if event_type:
            query = query.filter(Event.event_type == event_type)
        
        if user_id:
            query = query.filter(Event.user_id == user_id)
        
        # Handle asset filtering (including null)
        if asset_id is not None:
            if asset_id == 'null':
                query = query.filter(Event.asset_id.is_(None))
            elif asset_id != '':
                query = query.filter(Event.asset_id == int(asset_id))
        
        # Handle location filtering (including null)
        if major_location_id is not None:
            if major_location_id == 'null':
                query = query.filter(Event.major_location_id.is_(None))
            elif major_location_id != '':
                query = query.filter(Event.major_location_id == int(major_location_id))
        
        # Handle make/model filtering - filter events related to assets of this make/model
        if make_model_id:
            query = query.join(Asset, Event.asset_id == Asset.id).filter(
                Asset.make_model_id == make_model_id
            )
        
        # Order by timestamp (newest first)
        query = query.order_by(Event.timestamp.desc())
        
        filters = {
            'event_type': event_type,
            'user_id': user_id,
            'asset_id': asset_id,
            'major_location_id': major_location_id,
            'make_model_id': make_model_id,
            'row_count': row_count,
        }
        
        return query, filters
    
    @staticmethod
    def get_list_data(
        request: Request,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple:
        """
        Get paginated event list with filters applied.
        
        Args:
            request: Flask request object
            page: Page number (default: 1)
            per_page: Items per page (default: 20)
            
        Returns:
            Tuple of (pagination object, filters dict)
        """
        # Extract filter parameters from request
        event_type = request.args.get('event_type')
        user_id = request.args.get('user_id', type=int)
        asset_id = request.args.get('asset_id')
        major_location_id = request.args.get('major_location_id')
        make_model_id = request.args.get('make_model_id', type=int)
        
        # Build query using service method
        query, filters = EventService.build_event_query(
            event_type=event_type,
            user_id=user_id,
            asset_id=asset_id,
            major_location_id=major_location_id,
            make_model_id=make_model_id,
            row_count=per_page
        )
        
        # Paginate
        events = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return events, filters
    
    @staticmethod
    def get_card_data(
        request: Request,
        condensed_view: bool = False
    ) -> Tuple:
        """
        Get event card data (for HTMX endpoints).
        
        Args:
            request: Flask request object
            condensed_view: Whether to use condensed view (default: False)
            
        Returns:
            Tuple of (events list, filters dict)
        """
        row_count = request.args.get('row_count', 10 if condensed_view else 20, type=int)
        
        # Extract filter parameters from request
        event_type = request.args.get('event_type')
        user_id = request.args.get('user_id', type=int)
        asset_id = request.args.get('asset_id')
        major_location_id = request.args.get('major_location_id')
        make_model_id = request.args.get('make_model_id', type=int)
        
        # Build query using service method
        query, filters = EventService.build_event_query(
            event_type=event_type,
            user_id=user_id,
            asset_id=asset_id,
            major_location_id=major_location_id,
            make_model_id=make_model_id,
            row_count=row_count
        )
        
        # Limit results (no pagination for cards)
        events = query.limit(row_count).all()
        
        # Update filters with row_count
        filters['row_count'] = row_count
        
        return events, filters
    
    @staticmethod
    def get_filter_options() -> Dict:
        """
        Get filter options for event list views.
        
        Returns:
            Dictionary with users, assets, locations, and make_models
        """
        from app.data.core.user_info.user import User
        from app.data.core.major_location import MajorLocation
        from app.data.core.asset_info.make_model import MakeModel
        
        return {
            'users': User.query.all(),
            'assets': Asset.query.all(),
            'locations': MajorLocation.query.all(),
            'make_models': MakeModel.query.all()
        }
    
    @staticmethod
    def get_human_comments(event_id: int) -> List[Comment]:
        """
        Get only human-made comments for an event, ordered by creation date (newest first).
        
        This is a read-only presentation method for filtering comments in event views.
        
        Args:
            event_id: Event ID
            
        Returns:
            List of Comment objects that are human-made
        """
        return Comment.query.filter_by(
            event_id=event_id,
            is_human_made=True
        ).order_by(Comment.created_at.desc()).all()

