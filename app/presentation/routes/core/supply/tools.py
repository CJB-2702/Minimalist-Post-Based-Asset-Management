"""
Tool management routes - integrated into core section
CRUD operations for Tool model
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.data.core.supply.tool import Tool
from app.data.core.supply.issuable_tool import IssuableTool
from app.data.core.user_info.user import User
from app import db
from app.logger import get_logger

logger = get_logger("asset_management.routes.core.supply.tools")
bp = Blueprint('core_supply_tools', __name__)

# ROUTE_TYPE: SIMPLE_CRUD (GET)
# EXCEPTION: Direct ORM usage allowed for simple GET operations on Tool/IssuableTool
# This route performs basic list operations with minimal filtering and business logic.
# Rationale: Simple pagination and filtering on single entity type doesn't require domain abstraction.
# NOTE: CREATE/DELETE operations should use domain managers - see create() and delete() routes
@bp.route('')
@login_required
def list():
    """List all tool definitions with basic filtering"""
    logger.debug(f"User {current_user.username} accessing tool definitions list")
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Basic filtering
    tool_type = request.args.get('tool_type')
    manufacturer = request.args.get('manufacturer')
    tool_name = request.args.get('tool_name')
    
    logger.debug(f"Tool definitions list filters - Type: {tool_type}, Manufacturer: {manufacturer}")
    
    # Query Tool definitions (not IssuableTool instances)
    query = Tool.query
    
    # Apply filters
    if tool_type:
        query = query.filter(Tool.tool_type == tool_type)
    
    if manufacturer:
        query = query.filter(Tool.manufacturer.ilike(f'%{manufacturer}%'))
    
    if tool_name:
        query = query.filter(Tool.tool_name.ilike(f'%{tool_name}%'))
    
    # Order by tool name
    query = query.order_by(Tool.tool_name)
    
    # Pagination
    tools = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Get filter options
    tool_types = db.session.query(Tool.tool_type).distinct().all()
    tool_types = [tt[0] for tt in tool_types if tt[0]]
    
    manufacturers = db.session.query(Tool.manufacturer).distinct().all()
    manufacturers = [man[0] for man in manufacturers if man[0]]
    
    logger.info(f"Tool definitions list returned {tools.total} tools (page {page})")
    
    return render_template('supply/tools/list.html', 
                         tools=tools,
                         tool_types=tool_types,
                         manufacturers=manufacturers,
                         current_filters={
                             'tool_type': tool_type,
                             'manufacturer': manufacturer,
                             'tool_name': tool_name
                         })

@bp.route('/<int:tool_id>')
@login_required
def detail(tool_id):
    """View individual tool definition details"""
    logger.debug(f"User {current_user.username} accessing tool definition detail for tool ID: {tool_id}")
    
    tool = Tool.query.get_or_404(tool_id)
    
    # Get issuable instances of this tool
    issuable_instances = IssuableTool.query.filter_by(tool_id=tool_id).all()
    
    logger.info(f"Tool definition detail accessed - Tool: {tool.tool_name} (ID: {tool_id})")
    
    return render_template('supply/tools/detail.html', 
                         tool=tool,
                         issuable_instances=issuable_instances)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new tool definition"""
    if request.method == 'POST':
        # Validate form data - only Tool definition fields
        tool_name = request.form.get('tool_name')
        description = request.form.get('description')
        tool_type = request.form.get('tool_type')
        manufacturer = request.form.get('manufacturer')
        model_number = request.form.get('model_number')
        
        if not tool_name:
            flash('Tool name is required', 'error')
            return render_template('supply/tools/create.html')
        
        # Create new tool definition
        tool = Tool(
            tool_name=tool_name,
            description=description,
            tool_type=tool_type,
            manufacturer=manufacturer,
            model_number=model_number,
            created_by_id=current_user.id,
            updated_by_id=current_user.id
        )
        
        db.session.add(tool)
        db.session.commit()
        
        flash('Tool definition created successfully', 'success')
        return redirect(url_for('core_supply_tools.detail', tool_id=tool.id))
    
    return render_template('supply/tools/create.html')

# ROUTE_TYPE: SIMPLE_CRUD (EDIT)
# EXCEPTION: Direct ORM usage allowed for simple EDIT operations on Tool/IssuableTool
# This route performs basic update operations with minimal business logic.
# Rationale: Simple tool update doesn't require domain abstraction. ToolContext is used for detail view.
# NOTE: CREATE/DELETE operations should use domain managers - see create() and delete() routes
@bp.route('/<int:tool_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(tool_id):
    """Edit tool definition"""
    tool = Tool.query.get_or_404(tool_id)
    
    if request.method == 'POST':
        # Validate form data - only Tool definition fields
        tool_name = request.form.get('tool_name')
        description = request.form.get('description')
        tool_type = request.form.get('tool_type')
        manufacturer = request.form.get('manufacturer')
        model_number = request.form.get('model_number')
        
        if not tool_name:
            flash('Tool name is required', 'error')
            return render_template('supply/tools/edit.html', tool=tool)
        
        # Update tool definition fields
        tool.tool_name = tool_name
        tool.description = description
        tool.tool_type = tool_type
        tool.manufacturer = manufacturer
        tool.model_number = model_number
        tool.updated_by_id = current_user.id
        
        db.session.commit()
        
        flash('Tool definition updated successfully', 'success')
        return redirect(url_for('core_supply_tools.detail', tool_id=tool.id))
    
    return render_template('supply/tools/edit.html', tool=tool)

@bp.route('/<int:tool_id>/delete', methods=['POST'])
@login_required
def delete(tool_id):
    """Delete tool definition"""
    tool = Tool.query.get_or_404(tool_id)
    
    # Check if there are issuable instances
    issuable_count = IssuableTool.query.filter_by(tool_id=tool_id).count()
    if issuable_count > 0:
        flash(f'Cannot delete tool definition with {issuable_count} issuable instance(s). Delete instances first.', 'error')
        return redirect(url_for('core_supply_tools.detail', tool_id=tool_id))
    
    db.session.delete(tool)
    db.session.commit()
    
    flash('Tool definition deleted successfully', 'success')
    return redirect(url_for('core_supply_tools.list'))

