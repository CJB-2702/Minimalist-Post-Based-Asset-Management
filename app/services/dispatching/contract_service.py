"""
Contract Service
Presentation service for contract outcome data retrieval and filtering.
"""

from typing import Dict, Optional, Tuple
from flask import Request
from flask_sqlalchemy.pagination import Pagination
from app import db
from app.data.dispatching.outcomes.contract import Contract


class ContractService:
    """
    Service for contract outcome presentation data.
    
    Provides methods for:
    - Building filtered contract queries
    - Paginating contract lists
    - Retrieving filter options
    """
    
    @staticmethod
    def build_filtered_query(
        company_name: Optional[str] = None,
        cost_currency: Optional[str] = None,
        min_cost: Optional[float] = None,
        max_cost: Optional[float] = None,
        search: Optional[str] = None
    ):
        """
        Build a filtered contract query.
        
        Args:
            company_name: Filter by company name (partial match)
            cost_currency: Filter by currency
            min_cost: Filter by minimum cost
            max_cost: Filter by maximum cost
            search: Search in company name, contract reference, and notes
            
        Returns:
            SQLAlchemy query object
        """
        query = Contract.query
        
        if company_name:
            query = query.filter(Contract.company_name.ilike(f"%{company_name}%"))
        
        if cost_currency:
            query = query.filter(Contract.cost_currency == cost_currency)
        
        if min_cost is not None:
            query = query.filter(Contract.cost_amount >= min_cost)
        
        if max_cost is not None:
            query = query.filter(Contract.cost_amount <= max_cost)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    Contract.company_name.ilike(search_term),
                    Contract.contract_reference.ilike(search_term),
                    Contract.notes.ilike(search_term)
                )
            )
        
        # Order by created date (newest first)
        query = query.order_by(Contract.created_at.desc())
        
        return query
    
    @staticmethod
    def get_list_data(
        request: Request,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[Pagination, Dict]:
        """
        Get paginated contract list with filters applied.
        
        Args:
            request: Flask request object
            page: Page number (default: 1)
            per_page: Items per page (default: 20)
            
        Returns:
            Tuple of (pagination object, filter options dict)
        """
        # Extract filter parameters
        company_name = request.args.get('company_name')
        cost_currency = request.args.get('cost_currency')
        min_cost = request.args.get('min_cost', type=float)
        max_cost = request.args.get('max_cost', type=float)
        search = request.args.get('search')
        
        # Build filtered query
        query = ContractService.build_filtered_query(
            company_name=company_name,
            cost_currency=cost_currency,
            min_cost=min_cost,
            max_cost=max_cost,
            search=search
        )
        
        # Paginate
        contracts_page = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Get filter options
        currencies = db.session.query(Contract.cost_currency).distinct().all()
        currencies = [c[0] for c in currencies if c[0]]
        
        companies = db.session.query(Contract.company_name).distinct().all()
        companies = [c[0] for c in companies if c[0]]
        
        filter_options = {
            'currencies': sorted(currencies),
            'companies': sorted(companies)
        }
        
        return contracts_page, filter_options
