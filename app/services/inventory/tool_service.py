"""
Tool Service
Presentation service for tool-related queries.
"""

from typing import Dict, List, Optional, Tuple, Any
from flask_sqlalchemy.pagination import Pagination
from app.data.core.supply.tool_definition import ToolDefinition
from app.data.core.user_info.user import User


class ToolService:
    """
    Service for tool-related presentation data.
    
    Provides methods for:
    - Building filtered tool queries
    """
    
    @staticmethod
    def get_list_data(
        page: int = 1,
        per_page: int = 20,
        tool_name: Optional[str] = None
    ) -> Tuple[Pagination, Dict[str, Any]]:
        """
        Get paginated tools with filters.
        
        Args:
            page: Page number
            per_page: Items per page
            tool_name: Filter by tool name (partial match)
            
        Returns:
            Tuple of (pagination_object, form_options_dict)
        """
        # Query Tool definitions
        query = ToolDefinition.query
        
        if tool_name:
            query = query.filter(ToolDefinition.tool_name.ilike(f'%{tool_name}%'))
        
        # Order by tool name
        query = query.order_by(ToolDefinition.tool_name)
        
        # Pagination for tool definitions
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Get form options
        from app import db
        tool_types = [tt[0] for tt in db.session.query(ToolDefinition.tool_type).distinct().all() if tt[0]]
        manufacturers = [man[0] for man in db.session.query(ToolDefinition.manufacturer).distinct().all() if man[0]]
        
        form_options = {
            'tool_types': tool_types,
            'manufacturers': manufacturers,
            'users': User.query.all()
        }
        
        return pagination, form_options
    
    @staticmethod
    def get_tool_assignment_info(tool_id: int) -> Dict[str, Any]:
        """
        Get basic information for a tool.
        
        Args:
            tool_id: Tool ID
            
        Returns:
            Dictionary with tool information
        """
        tool = ToolDefinition.query.get(tool_id)
        if not tool:
            return {'error': 'Tool not found'}
        
        return {
            'tool_id': tool_id,
            'tool_name': tool.tool_name,
            'tool_type': tool.tool_type,
            'manufacturer': tool.manufacturer,
            'model_number': tool.model_number
        }



