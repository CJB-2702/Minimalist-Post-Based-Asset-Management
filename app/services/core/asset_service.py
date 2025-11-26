"""
Asset Service
Presentation service for asset-related data retrieval and formatting.

Handles:
- Query building and filtering for asset list views
- Form option retrieval (locations, make_models, asset_types)
- Data aggregation for presentation
"""

from typing import Dict, List, Optional, Tuple
from flask import Request
from flask_sqlalchemy.pagination import Pagination
from app.data.core.asset_info.asset import Asset
from app.data.core.asset_info.asset_type import AssetType
from app.data.core.asset_info.make_model import MakeModel
from app.data.core.major_location import MajorLocation
from app.data.core.event_info.event import Event


class AssetService:
    """
    Service for asset presentation data.
    
    Provides methods for:
    - Building filtered asset queries
    - Retrieving form options
    - Paginating asset lists
    """
    
    @staticmethod
    def build_filtered_query(
        asset_type_id: Optional[int] = None,
        location_id: Optional[int] = None,
        make_model_id: Optional[int] = None,
        status: Optional[str] = None,
        serial_number: Optional[str] = None,
        name: Optional[str] = None
    ):
        """
        Build a filtered asset query.
        
        Args:
            asset_type_id: Filter by asset type
            location_id: Filter by location
            make_model_id: Filter by make/model
            status: Filter by status
            serial_number: Filter by serial number (partial match)
            name: Filter by name (partial match)
            
        Returns:
            SQLAlchemy query object
        """
        query = Asset.query
        
        if location_id:
            query = query.filter(Asset.major_location_id == location_id)
        
        if make_model_id:
            query = query.filter(Asset.make_model_id == make_model_id)
        
        if status:
            query = query.filter(Asset.status == status)
        
        if serial_number:
            query = query.filter(Asset.serial_number.ilike(f'%{serial_number}%'))
        
        if name:
            query = query.filter(Asset.name.ilike(f'%{name}%'))
        
        # Asset type filtering through make_model relationship
        if asset_type_id:
            query = query.join(Asset.make_model).filter(Asset.make_model.has(asset_type_id=asset_type_id))
        
        # Order by creation date (newest first)
        query = query.order_by(Asset.created_at.desc())
        
        return query
    
    @staticmethod
    def get_list_data(
        request: Request,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[Pagination, Dict, Dict]:
        """
        Get paginated asset list with filters applied.
        
        Args:
            request: Flask request object
            page: Page number (default: 1)
            per_page: Items per page (default: 20)
            
        Returns:
            Tuple of (pagination object, filter options dict, current filters dict)
        """
        # Extract filter parameters from request
        asset_type_id = request.args.get('asset_type_id', type=int)
        location_id = request.args.get('location_id', type=int)
        make_model_id = request.args.get('make_model_id', type=int)
        status = request.args.get('status')
        serial_number = request.args.get('serial_number')
        name = request.args.get('name')
        
        # Build filtered query
        query = AssetService.build_filtered_query(
            asset_type_id=asset_type_id,
            location_id=location_id,
            make_model_id=make_model_id,
            status=status,
            serial_number=serial_number,
            name=name
        )
        
        # Paginate
        assets = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Get filter options
        filter_options = {
            'asset_types': AssetType.query.all(),
            'locations': MajorLocation.query.all(),
            'make_models': MakeModel.query.all()
        }
        
        # Current filters for template
        current_filters = {
            'asset_type_id': asset_type_id,
            'location_id': location_id,
            'make_model_id': make_model_id,
            'status': status,
            'serial_number': serial_number,
            'name': name
        }
        
        return assets, filter_options, current_filters
    
    @staticmethod
    def get_form_options() -> Dict:
        """
        Get form options for asset creation/editing.
        
        Returns:
            Dictionary with 'locations' and 'make_models' keys
        """
        return {
            'locations': MajorLocation.query.all(),
            'make_models': MakeModel.query.all()
        }
    
    @staticmethod
    def get_recent_events(asset_id: int, limit: int = 10) -> List[Event]:
        """
        Get recent events for an asset, ordered by timestamp (newest first).
        
        This is a read-only presentation method for displaying events in asset views.
        
        Args:
            asset_id: Asset ID
            limit: Maximum number of events to return (default: 10)
            
        Returns:
            List of Event instances
        """
        return Event.query.filter_by(asset_id=asset_id)\
                         .order_by(Event.timestamp.desc())\
                         .limit(limit).all()

