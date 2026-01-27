"""
Reimbursement Service
Presentation service for reimbursement outcome data retrieval and filtering.
"""

from typing import Dict, Optional, Tuple
from flask import Request
from flask_sqlalchemy.pagination import Pagination
from app import db
from app.data.dispatching.outcomes.reimbursement import Reimbursement


class ReimbursementService:
    """
    Service for reimbursement outcome presentation data.
    
    Provides methods for:
    - Building filtered reimbursement queries
    - Paginating reimbursement lists
    - Retrieving filter options
    """
    
    @staticmethod
    def build_filtered_query(
        from_account: Optional[str] = None,
        to_account: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        search: Optional[str] = None
    ):
        """
        Build a filtered reimbursement query.
        
        Args:
            from_account: Filter by from account
            to_account: Filter by to account
            min_amount: Filter by minimum amount
            max_amount: Filter by maximum amount
            search: Search in reason and policy reference
            
        Returns:
            SQLAlchemy query object
        """
        query = Reimbursement.query
        
        if from_account:
            query = query.filter(Reimbursement.from_account.ilike(f"%{from_account}%"))
        
        if to_account:
            query = query.filter(Reimbursement.to_account.ilike(f"%{to_account}%"))
        
        if min_amount is not None:
            query = query.filter(Reimbursement.amount >= min_amount)
        
        if max_amount is not None:
            query = query.filter(Reimbursement.amount <= max_amount)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    Reimbursement.reason.ilike(search_term),
                    Reimbursement.policy_reference.ilike(search_term),
                    Reimbursement.from_account.ilike(search_term),
                    Reimbursement.to_account.ilike(search_term)
                )
            )
        
        # Order by created date (newest first)
        query = query.order_by(Reimbursement.created_at.desc())
        
        return query
    
    @staticmethod
    def get_list_data(
        request: Request,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[Pagination, Dict]:
        """
        Get paginated reimbursement list with filters applied.
        
        Args:
            request: Flask request object
            page: Page number (default: 1)
            per_page: Items per page (default: 20)
            
        Returns:
            Tuple of (pagination object, filter options dict)
        """
        # Extract filter parameters
        from_account = request.args.get('from_account')
        to_account = request.args.get('to_account')
        min_amount = request.args.get('min_amount', type=float)
        max_amount = request.args.get('max_amount', type=float)
        search = request.args.get('search')
        
        # Build filtered query
        query = ReimbursementService.build_filtered_query(
            from_account=from_account,
            to_account=to_account,
            min_amount=min_amount,
            max_amount=max_amount,
            search=search
        )
        
        # Paginate
        reimbursements_page = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Get filter options
        from_accounts = db.session.query(Reimbursement.from_account).distinct().all()
        from_accounts = [a[0] for a in from_accounts if a[0]]
        
        to_accounts = db.session.query(Reimbursement.to_account).distinct().all()
        to_accounts = [a[0] for a in to_accounts if a[0]]
        
        filter_options = {
            'from_accounts': sorted(from_accounts),
            'to_accounts': sorted(to_accounts)
        }
        
        return reimbursements_page, filter_options
