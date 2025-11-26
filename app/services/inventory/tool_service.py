"""
Tool Service
Presentation service for tool-related queries.
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from flask_sqlalchemy.pagination import Pagination
from app.data.core.supply.tool import Tool
from app.data.core.supply.issuable_tool import IssuableTool
from app.data.core.user_info.user import User


class ToolService:
    """
    Service for tool-related presentation data.
    
    Provides methods for:
    - Building filtered tool queries
    - Getting assignment information
    - Finding tools needing calibration
    """
    
    @staticmethod
    def get_list_data(
        page: int = 1,
        per_page: int = 20,
        tool_name: Optional[str] = None,
        is_issuable: Optional[bool] = None,
        assigned_to_user_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> Tuple[Pagination, Dict[str, Any]]:
        """
        Get paginated tools with filters.
        
        Args:
            page: Page number
            per_page: Items per page
            tool_name: Filter by tool name (partial match)
            is_issuable: Filter by issuable status
            assigned_to_user_id: Filter by assigned user (for issuable tools)
            status: Filter by status (for issuable tools)
            
        Returns:
            Tuple of (pagination_object, form_options_dict)
        """
        # For issuance-related filtering, we need to use IssuableTool
        if status or assigned_to_user_id:
            from app import db
            # Query IssuableTool instances with their associated Tool information
            query = db.session.query(IssuableTool).join(Tool)
            
            if status:
                query = query.filter(IssuableTool.status == status)
            
            if assigned_to_user_id:
                query = query.filter(IssuableTool.assigned_to_id == assigned_to_user_id)
            
            # Apply tool definition filters to the joined Tool
            if tool_name:
                query = query.filter(Tool.tool_name.ilike(f'%{tool_name}%'))
            
            # Order by tool name
            query = query.order_by(Tool.tool_name)
            
            # Pagination for issuable tools
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        else:
            # For tool definition filtering only, use Tool directly
            query = Tool.query
            
            if tool_name:
                query = query.filter(Tool.tool_name.ilike(f'%{tool_name}%'))
            
            if is_issuable is not None:
                # Filter for tools that have corresponding IssuableTool entries
                if is_issuable:
                    query = query.join(IssuableTool, Tool.id == IssuableTool.id)
                else:
                    query = query.outerjoin(IssuableTool, Tool.id == IssuableTool.id).filter(
                        IssuableTool.id.is_(None)
                    )
            
            # Order by tool name
            query = query.order_by(Tool.tool_name)
            
            # Pagination for tool definitions
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Get form options
        from app import db
        tool_types = [tt[0] for tt in db.session.query(Tool.tool_type).distinct().all() if tt[0]]
        manufacturers = [man[0] for man in db.session.query(Tool.manufacturer).distinct().all() if man[0]]
        
        form_options = {
            'tool_types': tool_types,
            'manufacturers': manufacturers,
            'users': User.query.all()
        }
        
        return pagination, form_options
    
    @staticmethod
    def get_issuable_tools(assigned_to_user_id: Optional[int] = None) -> List[Tool]:
        """
        Get issuable tools, optionally filtered by assignment.
        
        Args:
            assigned_to_user_id: Optional user ID to filter by assignment
            
        Returns:
            List of Tool objects (that are issuable)
        """
        query = Tool.query.join(IssuableTool, Tool.id == IssuableTool.id)
        
        if assigned_to_user_id:
            query = query.filter(IssuableTool.assigned_to_id == assigned_to_user_id)
        
        return query.all()
    
    @staticmethod
    def get_tool_assignment_info(tool_id: int) -> Dict[str, Any]:
        """
        Get assignment information for a tool.
        
        Args:
            tool_id: Tool ID
            
        Returns:
            Dictionary with assignment information
        """
        tool = Tool.query.get(tool_id)
        if not tool:
            return {'error': 'Tool not found'}
        
        issuable_tool = IssuableTool.query.get(tool_id)
        
        return {
            'tool_id': tool_id,
            'is_issuable': issuable_tool is not None,
            'assigned_to': issuable_tool.assigned_to if issuable_tool else None,
            'assigned_to_id': issuable_tool.assigned_to_id if issuable_tool else None,
            'status': issuable_tool.status if issuable_tool else None,
            'location': issuable_tool.location if issuable_tool else None,
            'serial_number': issuable_tool.serial_number if issuable_tool else None,
            'next_calibration_date': issuable_tool.next_calibration_date if issuable_tool else None,
            'last_calibration_date': issuable_tool.last_calibration_date if issuable_tool else None
        }
    
    @staticmethod
    def get_tools_needing_calibration(days_ahead: int = 30) -> List[Tool]:
        """
        Get tools that need calibration within specified days.
        
        Args:
            days_ahead: Number of days to look ahead (default: 30)
            
        Returns:
            List of Tool objects needing calibration
        """
        from app import db
        today = datetime.now().date()
        cutoff_date = today + timedelta(days=days_ahead)
        
        query = Tool.query.join(IssuableTool, Tool.id == IssuableTool.id).filter(
            IssuableTool.next_calibration_date.isnot(None),
            IssuableTool.next_calibration_date <= cutoff_date
        )
        
        return query.all()



