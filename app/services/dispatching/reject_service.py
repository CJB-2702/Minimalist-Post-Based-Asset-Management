"""
Reject Service
Presentation service for rejection outcome data retrieval and filtering.
"""

from typing import Dict, Optional, Tuple
from flask import Request
from flask_sqlalchemy.pagination import Pagination
from app import db
from app.data.dispatching.outcomes.reject import Reject


class RejectService:
    """
    Service for rejection outcome presentation data.
    
    Provides methods for:
    - Building filtered rejection queries
    - Paginating rejection lists
    - Retrieving filter options
    """
    
    @staticmethod
    def build_filtered_query(
        rejection_category: Optional[str] = None,
        can_resubmit: Optional[bool] = None,
        search: Optional[str] = None
    ):
        """
        Build a filtered rejection query.
        
        Args:
            rejection_category: Filter by rejection category
            can_resubmit: Filter by can resubmit status
            search: Search in reason, notes, and alternative suggestion
            
        Returns:
            SQLAlchemy query object
        """
        query = Reject.query
        
        if rejection_category:
            query = query.filter(Reject.rejection_category == rejection_category)
        
        if can_resubmit is not None:
            query = query.filter(Reject.can_resubmit == can_resubmit)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    Reject.reason.ilike(search_term),
                    Reject.notes.ilike(search_term),
                    Reject.alternative_suggestion.ilike(search_term)
                )
            )
        
        # Order by created date (newest first)
        query = query.order_by(Reject.created_at.desc())
        
        return query
    
    @staticmethod
    def get_list_data(
        request: Request,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[Pagination, Dict]:
        """
        Get paginated rejection list with filters applied.
        
        Args:
            request: Flask request object
            page: Page number (default: 1)
            per_page: Items per page (default: 20)
            
        Returns:
            Tuple of (pagination object, filter options dict)
        """
        # Extract filter parameters
        rejection_category = request.args.get('rejection_category')
        can_resubmit_param = request.args.get('can_resubmit')
        can_resubmit = None if can_resubmit_param is None else (can_resubmit_param.lower() == 'true')
        search = request.args.get('search')
        
        # Build filtered query
        query = RejectService.build_filtered_query(
            rejection_category=rejection_category,
            can_resubmit=can_resubmit,
            search=search
        )
        
        # Paginate
        rejects_page = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Get filter options
        categories = db.session.query(Reject.rejection_category).distinct().all()
        categories = [c[0] for c in categories if c[0]]
        
        filter_options = {
            'categories': sorted(categories)
        }
        
        return rejects_page, filter_options
