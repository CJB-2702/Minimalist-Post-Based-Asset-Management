"""
Dispatch Request Service
Presentation service for dispatch request-related data retrieval and filtering.
"""

from typing import Dict, Optional, Tuple
from datetime import datetime
from flask import Request
from flask_sqlalchemy.pagination import Pagination
from app import db
from app.data.dispatching.request import DispatchRequest
from app.data.core.asset_info.asset_type import AssetType
from app.data.core.asset_info.asset import Asset
from app.data.core.major_location import MajorLocation
from app.data.core.user_info.user import User


class DispatchRequestService:
    """
    Service for dispatch request presentation data.
    
    Provides methods for:
    - Building filtered dispatch request queries
    - Paginating dispatch request lists
    - Retrieving filter options
    """
    
    @staticmethod
    def build_filtered_query(
        status: Optional[str] = None,
        workflow_status: Optional[str] = None,
        asset_type_id: Optional[int] = None,
        asset_id: Optional[int] = None,
        asset_name: Optional[str] = None,
        major_location_id: Optional[int] = None,
        dispatch_scope: Optional[str] = None,
        active_outcome_type: Optional[str] = None,
        requested_by: Optional[int] = None,
        requested_for: Optional[int] = None,
        desired_start_from: Optional[datetime] = None,
        desired_start_to: Optional[datetime] = None,
        search: Optional[str] = None
    ):
        """
        Build a filtered dispatch request query.
        
        Args:
            status: Filter by legacy status
            workflow_status: Filter by workflow_status
            asset_type_id: Filter by asset type
            asset_id: Filter by specific asset (checks asset_id and requested_asset_id)
            asset_name: Filter by asset name (partial match)
            major_location_id: Filter by location
            dispatch_scope: Filter by dispatch scope
            active_outcome_type: Filter by active outcome type (dispatch/contract/reimbursement/reject/none)
            requested_by: Filter by user who created the request
            requested_for: Filter by user the request is for
            desired_start_from: Filter by desired_start >= this date
            desired_start_to: Filter by desired_start <= this date
            search: Search in notes, activity_location, names_freeform, and asset_subclass_text
            
        Returns:
            SQLAlchemy query object
        """
        query = DispatchRequest.query
        
        if status:
            query = query.filter(DispatchRequest.status == status)
        
        if workflow_status:
            query = query.filter(DispatchRequest.workflow_status == workflow_status)
        
        if asset_type_id:
            query = query.filter(DispatchRequest.asset_type_id == asset_type_id)
        
        if asset_id:
            # Filter by asset ID in request fields
            # - DispatchRequest.asset_id (inherited from EventDetailVirtual)
            # - DispatchRequest.requested_asset_id (specific asset requested)
            query = query.filter(
                db.or_(
                    DispatchRequest.asset_id == asset_id,
                    DispatchRequest.requested_asset_id == asset_id
                )
            )
        
        if asset_name:
            # Filter by asset name (partial match)
            # Join with Asset to search by name across asset_id and requested_asset_id
            query = query.outerjoin(
                Asset, 
                db.or_(
                    DispatchRequest.asset_id == Asset.id,
                    DispatchRequest.requested_asset_id == Asset.id
                )
            )
            asset_name_term = f"%{asset_name}%"
            query = query.filter(Asset.name.ilike(asset_name_term))
        
        if major_location_id:
            query = query.filter(DispatchRequest.major_location_id == major_location_id)
        
        if dispatch_scope:
            query = query.filter(DispatchRequest.dispatch_scope == dispatch_scope)
        
        if active_outcome_type is not None:
            if active_outcome_type == 'none':
                query = query.filter(DispatchRequest.active_outcome_type.is_(None))
            else:
                query = query.filter(DispatchRequest.active_outcome_type == active_outcome_type)
        
        if requested_by:
            query = query.filter(DispatchRequest.requested_by == requested_by)
        
        if requested_for:
            query = query.filter(DispatchRequest.requested_for == requested_for)
        
        if desired_start_from:
            query = query.filter(DispatchRequest.desired_start >= desired_start_from)
        
        if desired_start_to:
            query = query.filter(DispatchRequest.desired_start <= desired_start_to)
        
        if search:
            search_term = f"%{search}%"
            # Join with Asset if not already joined (for asset name/serial search)
            if asset_name is None:  # Only join if we haven't already joined for asset_name filter
                query = query.outerjoin(
                    Asset, 
                    db.or_(
                        DispatchRequest.asset_id == Asset.id,
                        DispatchRequest.requested_asset_id == Asset.id
                    )
                )
            query = query.filter(
                db.or_(
                    DispatchRequest.notes.ilike(search_term),
                    DispatchRequest.activity_location.ilike(search_term),
                    DispatchRequest.names_freeform.ilike(search_term),
                    DispatchRequest.asset_subclass_text.ilike(search_term),
                    Asset.serial_number.ilike(search_term),
                    Asset.name.ilike(search_term)
                )
            )
        
        # Order by created date (newest first)
        query = query.order_by(DispatchRequest.created_at.desc())
        
        return query
    
    @staticmethod
    def get_list_data(
        request: Request,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[Pagination, Dict]:
        """
        Get paginated dispatch request list with filters applied.
        
        Args:
            request: Flask request object
            page: Page number (default: 1)
            per_page: Items per page (default: 20)
            
        Returns:
            Tuple of (pagination object, filter options dict)
        """
        # Extract filter parameters
        status = request.args.get('status')
        workflow_status = request.args.get('workflow_status')
        asset_type_id = request.args.get('asset_type_id', type=int)
        asset_id = request.args.get('asset_id', type=int)
        asset_name = request.args.get('asset_name')
        major_location_id = request.args.get('major_location_id', type=int)
        dispatch_scope = request.args.get('dispatch_scope')
        active_outcome_type = request.args.get('active_outcome_type')
        requested_by = request.args.get('requested_by', type=int)
        requested_for = request.args.get('requested_for', type=int)
        search = request.args.get('search')
        
        # Parse date range parameters
        desired_start_from = None
        desired_start_to = None
        desired_start_from_str = request.args.get('desired_start_from')
        desired_start_to_str = request.args.get('desired_start_to')
        
        if desired_start_from_str:
            try:
                desired_start_from = datetime.fromisoformat(desired_start_from_str)
            except ValueError:
                pass  # Ignore invalid dates
        
        if desired_start_to_str:
            try:
                desired_start_to = datetime.fromisoformat(desired_start_to_str)
            except ValueError:
                pass  # Ignore invalid dates
        
        # Build filtered query
        query = DispatchRequestService.build_filtered_query(
            status=status,
            workflow_status=workflow_status,
            asset_type_id=asset_type_id,
            asset_id=asset_id,
            asset_name=asset_name,
            major_location_id=major_location_id,
            dispatch_scope=dispatch_scope,
            active_outcome_type=active_outcome_type,
            requested_by=requested_by,
            requested_for=requested_for,
            desired_start_from=desired_start_from,
            desired_start_to=desired_start_to,
            search=search
        )
        
        # Paginate
        requests_page = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Get filter options
        statuses = db.session.query(DispatchRequest.status).distinct().all()
        statuses = [s[0] for s in statuses if s[0]]
        
        workflow_statuses = db.session.query(DispatchRequest.workflow_status).distinct().all()
        workflow_statuses = [s[0] for s in workflow_statuses if s[0]]
        
        scopes = db.session.query(DispatchRequest.dispatch_scope).distinct().all()
        scopes = [s[0] for s in scopes if s[0]]
        
        # Get distinct active outcome types (including None as 'none')
        outcome_types_raw = db.session.query(DispatchRequest.active_outcome_type).distinct().all()
        outcome_types = []
        has_none = False
        for ot in outcome_types_raw:
            if ot[0] is None:
                has_none = True
            elif ot[0]:
                outcome_types.append(ot[0])
        if has_none:
            outcome_types.insert(0, 'none')  # Add 'none' for null values
        
        asset_types = AssetType.query.filter_by(is_active=True).order_by(AssetType.name).all()
        locations = MajorLocation.query.order_by(MajorLocation.name).all()
        
        # Get active users for requested_by and requested_for filters
        users = User.query.filter_by(is_active=True).order_by(User.username).all()
        
        filter_options = {
            'statuses': statuses,
            'workflow_statuses': workflow_statuses,
            'scopes': scopes,
            'outcome_types': outcome_types,
            'asset_types': asset_types,
            'locations': locations,
            'users': users
        }
        
        return requests_page, filter_options
