"""
Dispatch Service (StandardDispatch)
Presentation service for dispatch outcome data retrieval and filtering.
"""

from typing import Dict, Optional, Tuple
from flask import Request
from flask_sqlalchemy.pagination import Pagination
from datetime import datetime
from app import db
from app.data.dispatching.outcomes.standard_dispatch import StandardDispatch
from app.data.core.user_info.user import User
from app.data.core.asset_info.asset import Asset


class DispatchService:
    """
    Service for dispatch (StandardDispatch) presentation data.
    
    Provides methods for:
    - Building filtered dispatch queries
    - Paginating dispatch lists
    - Retrieving filter options
    """
    
    @staticmethod
    def build_filtered_query(
        status: Optional[str] = None,
        assigned_person_id: Optional[int] = None,
        asset_dispatched_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        conflicts_resolved: Optional[bool] = None
    ):
        """
        Build a filtered dispatch query.
        
        Args:
            status: Filter by status
            assigned_person_id: Filter by assigned person
            asset_dispatched_id: Filter by dispatched asset
            date_from: Filter by scheduled start date (from)
            date_to: Filter by scheduled start date (to)
            conflicts_resolved: Filter by conflicts resolved
            
        Returns:
            SQLAlchemy query object
        """
        query = StandardDispatch.query
        
        if status:
            query = query.filter(StandardDispatch.status == status)
        
        if assigned_person_id:
            query = query.filter(StandardDispatch.assigned_person_id == assigned_person_id)
        
        if asset_dispatched_id:
            query = query.filter(StandardDispatch.asset_dispatched_id == asset_dispatched_id)
        
        if date_from:
            query = query.filter(StandardDispatch.scheduled_start >= date_from)
        
        if date_to:
            query = query.filter(StandardDispatch.scheduled_start <= date_to)
        
        if conflicts_resolved is not None:
            query = query.filter(StandardDispatch.conflicts_resolved == conflicts_resolved)
        
        # Order by scheduled start (newest first)
        query = query.order_by(StandardDispatch.scheduled_start.desc())
        
        return query
    
    @staticmethod
    def get_list_data(
        request: Request,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[Pagination, Dict]:
        """
        Get paginated dispatch list with filters applied.
        
        Args:
            request: Flask request object
            page: Page number (default: 1)
            per_page: Items per page (default: 20)
            
        Returns:
            Tuple of (pagination object, filter options dict)
        """
        # Extract filter parameters
        status = request.args.get('status')
        assigned_person_id = request.args.get('assigned_person_id', type=int)
        asset_dispatched_id = request.args.get('asset_dispatched_id', type=int)
        conflicts_resolved_param = request.args.get('conflicts_resolved')
        conflicts_resolved = None if conflicts_resolved_param is None else (conflicts_resolved_param.lower() == 'true')
        
        # Parse date filters
        date_from = None
        date_to = None
        date_from_str = request.args.get('date_from')
        date_to_str = request.args.get('date_to')
        
        if date_from_str:
            try:
                date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
            except ValueError:
                pass
        
        if date_to_str:
            try:
                date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
            except ValueError:
                pass
        
        # Build filtered query
        query = DispatchService.build_filtered_query(
            status=status,
            assigned_person_id=assigned_person_id,
            asset_dispatched_id=asset_dispatched_id,
            date_from=date_from,
            date_to=date_to,
            conflicts_resolved=conflicts_resolved
        )
        
        # Paginate
        dispatches_page = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Get filter options
        statuses = db.session.query(StandardDispatch.status).distinct().all()
        statuses = [s[0] for s in statuses if s[0]]
        
        users = User.query.filter_by(is_active=True).order_by(User.username).all()
        assets = Asset.query.order_by(Asset.name).limit(100).all()
        
        filter_options = {
            'statuses': statuses,
            'users': users,
            'assets': assets
        }
        
        return dispatches_page, filter_options
