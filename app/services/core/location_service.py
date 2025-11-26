"""
Location Service
Presentation service for location-related data retrieval and formatting.

Handles:
- Query building and filtering for location list views
- Count aggregation (asset counts)
- Detail view data aggregation (assets, events)
"""

from typing import Dict, Optional, Tuple
from flask import Request
from flask_sqlalchemy.pagination import Pagination
from app.data.core.major_location import MajorLocation
from app.data.core.asset_info.asset import Asset
from app.data.core.event_info.event import Event


class LocationService:
    """
    Service for location presentation data.
    
    Provides methods for:
    - Building filtered location queries
    - Aggregating counts (assets)
    - Retrieving detail view data (assets, events)
    - Paginating location lists
    """
    
    @staticmethod
    def build_filtered_query(active: Optional[bool] = None):
        """
        Build a filtered location query.
        
        Args:
            active: Filter by active status
            
        Returns:
            SQLAlchemy query object
        """
        query = MajorLocation.query
        
        if active is not None:
            query = query.filter(MajorLocation.is_active == active)
        
        # Order by name
        query = query.order_by(MajorLocation.name)
        
        return query
    
    @staticmethod
    def get_list_data(
        request: Request,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[Pagination, Dict]:
        """
        Get paginated location list with filters applied and count aggregations.
        
        Args:
            request: Flask request object
            page: Page number (default: 1)
            per_page: Items per page (default: 20)
            
        Returns:
            Tuple of (pagination object, count dict)
        """
        # Extract filter parameters
        active_param = request.args.get('active')
        active = None if active_param is None else (active_param.lower() == 'true')
        
        # Build filtered query
        query = LocationService.build_filtered_query(active=active)
        
        # Paginate
        locations = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Pre-calculate asset counts for each location to avoid N+1 queries
        asset_counts = {}
        for location in locations.items:
            asset_count = Asset.query.filter_by(major_location_id=location.id).count()
            asset_counts[location.id] = asset_count
        
        return locations, {'asset_counts': asset_counts}
    
    @staticmethod
    def get_detail_data(location_id: int) -> Dict:
        """
        Get location detail data with related assets and events.
        
        Args:
            location_id: Location ID
            
        Returns:
            Dictionary with location, assets, and events
        """
        location = MajorLocation.query.get_or_404(location_id)
        
        # Get assets at this location
        assets = Asset.query.filter_by(
            major_location_id=location.id
        ).order_by(Asset.created_at.desc()).all()
        
        # Get events at this location
        events = Event.query.filter_by(
            major_location_id=location_id
        ).order_by(Event.timestamp.desc()).limit(10).all()
        
        return {
            'location': location,
            'assets': assets,
            'events': events
        }

