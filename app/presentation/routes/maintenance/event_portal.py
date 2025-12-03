"""
Event Portal Routes
Reusable event viewing module for maintenance portals
"""

from flask import Request, render_template, Response
from flask_login import current_user
from typing import Optional, Dict
from app.logger import get_logger
from app.services.maintenance.event_portal_service import EventPortalService
from app.data.core.user_info.user import User

logger = get_logger("asset_management.routes.maintenance.event_portal")


def render_view_events_module(
    request: Request,
    current_user: User,
    portal_type: str = 'manager',
    default_filters: Optional[Dict] = None,
    per_page: int = 20,
    template_name: str = 'maintenance/base/event_portal/view_events.html'
) -> Response:
    """
    Render the events view module with filtering and pagination.
    
    Args:
        request: Flask request object
        current_user: Current logged-in user
        portal_type: Type of portal ('manager' or 'technician')
        default_filters: Optional default filter values
        per_page: Number of items per page
        template_name: Template to render
        
    Returns:
        Rendered HTML string
    """
    logger.info(f"Rendering events view module for {portal_type} portal, user: {current_user.username}")
    
    # Extract filters from request
    filters = EventPortalService.extract_filters_from_request(request)
    
    # Apply default filters if provided
    if default_filters:
        for key, value in default_filters.items():
            if filters.get(key) is None:
                filters[key] = value
    
    # Build query
    query = EventPortalService.build_events_query(
        status=filters.get('status'),
        priority=filters.get('priority'),
        assigned_user_id=filters.get('assigned_user_id'),
        created_by_user_id=filters.get('created_by_user_id'),
        asset_id=filters.get('asset_id'),
        make_model_id=filters.get('make_model_id'),
        major_location_id=filters.get('major_location_id'),
        action_title=filters.get('action_title'),
        has_comments_by=filters.get('has_comments_by'),
        portal_type=portal_type,
        current_user_id=current_user.id if portal_type == 'technician' else None,
        date_from=filters.get('date_from'),
        date_to=filters.get('date_to'),
        search_term=filters.get('search_term'),
        order_by=filters.get('order_by', 'created_at'),
        order_direction=filters.get('order_direction', 'desc')
    )
    
    # Get paginated events with enhanced data
    events = EventPortalService.get_events_with_enhanced_data(
        query,
        page=filters.get('page', 1),
        per_page=per_page
    )
    
    # Get filter options for dropdowns
    filter_options = EventPortalService.get_filter_options()
    
    # Get active filters for display
    active_filters = EventPortalService.get_active_filters(filters)
    
    # Prepare template context
    context = {
        'events': events,
        'filter_options': filter_options,
        'active_filters': active_filters,
        'portal_type': portal_type,
        'current_user': current_user,
        'filters': filters,  # Include all filters for form persistence
    }
    
    return render_template(template_name, **context)
