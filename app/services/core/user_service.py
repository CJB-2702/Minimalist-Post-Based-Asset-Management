"""
User Service
Presentation service for user-related data retrieval and formatting.

Handles:
- Query building and filtering for user list views
"""

from typing import Optional, Tuple
from flask import Request
from flask_sqlalchemy.pagination import Pagination
from app.data.core.user_info.user import User


class UserService:
    """
    Service for user presentation data.
    
    Provides methods for:
    - Building filtered user queries
    - Paginating user lists
    """
    
    @staticmethod
    def build_filtered_query(
        role: Optional[str] = None,
        active: Optional[bool] = None
    ):
        """
        Build a filtered user query.
        
        Args:
            role: Filter by role ('admin', 'system', 'regular')
            active: Filter by active status
            
        Returns:
            SQLAlchemy query object
        """
        query = User.query
        
        if role:
            if role == 'admin':
                query = query.filter(User.is_admin == True)
            elif role == 'system':
                query = query.filter(User.is_system == True)
            elif role == 'regular':
                query = query.filter(User.is_admin == False, User.is_system == False)
        
        if active is not None:
            query = query.filter(User.is_active == active)
        
        # Order by username
        query = query.order_by(User.username)
        
        return query
    
    @staticmethod
    def get_list_data(
        request: Request,
        page: int = 1,
        per_page: int = 20
    ) -> Pagination:
        """
        Get paginated user list with filters applied.
        
        Args:
            request: Flask request object
            page: Page number (default: 1)
            per_page: Items per page (default: 20)
            
        Returns:
            Pagination object
        """
        # Extract filter parameters
        role = request.args.get('role')
        active_param = request.args.get('active')
        active = None if active_param is None else (active_param.lower() == 'true')
        
        # Build filtered query
        query = UserService.build_filtered_query(role=role, active=active)
        
        # Paginate
        users = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return users

