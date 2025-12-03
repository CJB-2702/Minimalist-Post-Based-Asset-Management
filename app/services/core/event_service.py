"""
Event Service
Presentation service for event-related data retrieval and formatting.

Handles:
- Query building and filtering for event list views
- Filter parameter extraction
"""

from typing import Dict, List, Optional, Tuple
from flask import Request
import json
from app.data.core.event_info.event import Event
from app.data.core.asset_info.asset import Asset
from app.data.core.event_info.comment import Comment
from app.buisness.core.event_context import EventContext
from app.data.core.event_info.attachment import Attachment


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
        Get only human-made comments for an event, ordered by creation date (oldest first).
        Filters out deleted comments and previous edits (hidden from users).
        
        This is a read-only presentation method for filtering comments in event views.
        
        Args:
            event_id: Event ID
            
        Returns:
            List of Comment objects that are human-made (excluding deleted and previous edits), ordered chronologically
        """
        from sqlalchemy import or_
        
        query = Comment.query.filter_by(
            event_id=event_id,
            is_human_made=True
        )
        
        # Filter out deleted comments and previous edits
        # Show only comments where user_viewable is None (visible)
        query = query.filter(
            or_(
                Comment.user_viewable.is_(None),
                ~Comment.user_viewable.in_(['deleted', 'edit'])
            )
        )
        
        # Order by creation date (oldest first) for chronological display
        return query.order_by(Comment.created_at.asc()).all()
    
    @staticmethod
    def _get_event_json_string(event_id: int, filter_human_only: bool = False) -> str:
        """
        #THIS IS A SECRET UTILITY METHOD. DO NOT USE IT.
        Get event and comment data as a JSON string.
        Always includes full metadata for all comments regardless of user.
        
        Args:
            event_id: Event ID
            filter_human_only: Whether to filter to human comments only (default: False)
            
        Returns:
            JSON string containing event data, comments, and metadata
        """
        event_context = EventContext(event_id)
        
        # Get comments (filtered or all)
        if filter_human_only:
            comments = EventService.get_human_comments(event_id)
        else:
            comments = event_context.comments
        
        # Prepare comment data with metadata always included
        comments_data = []
        for comment in comments:
            comment_data = {
                'comment': {
                    'id': comment.id,
                    'content': comment.content,
                    'event_id': comment.event_id,
                    'is_human_made': comment.is_human_made,
                    'user_viewable': comment.user_viewable,
                    'previous_comment_id': comment.previous_comment_id,
                    'replied_to_comment_id': comment.replied_to_comment_id,
                    'created_at': comment.created_at.isoformat() if comment.created_at else None,
                    'updated_at': comment.updated_at.isoformat() if comment.updated_at else None,
                    'created_by_id': comment.created_by_id,
                    'updated_by_id': comment.updated_by_id,
                    'created_by_username': comment.created_by.username if comment.created_by else None,
                    'updated_by_username': comment.updated_by.username if comment.updated_by else None,
                },
                'edit_history': [],
                'metadata': None
            }
            
            # Always get edit history (not just for comment owners)
            try:
                history_comments = EventContext.get_comment_edit_history(comment)
                comment_data['edit_history'] = [
                    {
                        'id': h.id,
                        'content': h.content,
                        'created_at': h.created_at.isoformat() if h.created_at else None,
                        'created_by_id': h.created_by_id,
                        'created_by_username': h.created_by.username if h.created_by else None,
                        'is_current': h.id == comment.id,
                    }
                    for h in history_comments
                ]
            except Exception:
                comment_data['edit_history'] = []
            
            # Always get metadata (not just for comment owners)
            try:
                comment_data['metadata'] = comment.print_safe_dict()
                
                attachment_links = comment.comment_attachments
                comment_data['metadata']['attachment_links'] = [
                    link.print_safe_dict() for link in attachment_links
                ]
                
                attachment_ids = [
                    link.attachment_id for link in attachment_links if link.attachment
                ]
                attachments = Attachment.query.filter(
                    Attachment.id.in_(attachment_ids)
                ).all()
                comment_data['metadata']['attachments'] = [
                    attachment.print_safe_dict() for attachment in attachments
                ]
            except Exception:
                comment_data['metadata'] = None
            
            comments_data.append(comment_data)
        
        # Prepare event data
        event = event_context.event
        event_data = {
            'id': event.id,
            'event_type': event.event_type,
            'description': event.description,
            'timestamp': event.timestamp.isoformat() if event.timestamp else None,
            'user_id': event.user_id,
            'asset_id': event.asset_id,
            'major_location_id': event.major_location_id,
            'status': event.status,
            'created_at': event.created_at.isoformat() if event.created_at else None,
            'updated_at': event.updated_at.isoformat() if event.updated_at else None,
            'created_by_id': event.created_by_id,
            'updated_by_id': event.updated_by_id,
            'created_by_username': event.created_by.username if event.created_by else None,
            'updated_by_username': event.updated_by.username if event.updated_by else None,
            'asset_name': event.asset.name if event.asset else None,
            'location_name': event.major_location.name if event.major_location else None,
        }
        
        # Build final data structure
        result = {
            'event': event_data,
            'comments': comments_data,
            'filter_human_only': filter_human_only,
            'comment_count': len(comments),
        }
        
        return json.dumps(result, default=str)

    @staticmethod
    def get_comment_json_string(comment_id: int) -> str:
        """
        Get comment data as a JSON string.
        
        Args:
            comment_id: Comment ID
            
        Returns:
            JSON string containing comment data
        """
        comment = Comment.query.get_or_404(comment_id)
        comment_data={}
        comment_data['metadata'] = comment.print_safe_dict()
                
        attachment_links = comment.comment_attachments
        comment_data['attachment_links'] = [
            link.print_safe_dict() for link in attachment_links
        ]
        
        attachment_ids = [
            link.attachment_id for link in attachment_links if link.attachment
        ]
        attachments = Attachment.query.filter(
            Attachment.id.in_(attachment_ids)
        ).all()
        comment_data['attachments'] = [
            attachment.print_safe_dict() for attachment in attachments
        ]
        return json.dumps(comment_data, default=str)