"""
Issuable Tool management routes - integrated into core section
CRUD operations for IssuableTool model (tool instances)
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.data.core.supply.tool import Tool
from app.data.core.supply.issuable_tool import IssuableTool
from app.data.core.user_info.user import User
from app import db
from app.logger import get_logger
from datetime import datetime

logger = get_logger("asset_management.routes.core.supply.issuable_tools")
bp = Blueprint('core_supply_issuable_tools', __name__)

@bp.route('')
@login_required
def list():
    """List all issuable tool instances with basic filtering"""
    logger.debug(f"User {current_user.username} accessing issuable tools list")
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Basic filtering
    tool_id = request.args.get('tool_id', type=int)
    status = request.args.get('status')
    assigned_to_id = request.args.get('assigned_to_id', type=int)
    serial_number = request.args.get('serial_number')
    
    logger.debug(f"Issuable tools list filters - Tool ID: {tool_id}, Status: {status}, Assigned: {assigned_to_id}")
    
    # Query IssuableTool instances
    query = db.session.query(IssuableTool).join(Tool)
    
    # Apply filters
    if tool_id:
        query = query.filter(IssuableTool.tool_id == tool_id)
    
    if status:
        query = query.filter(IssuableTool.status == status)
    
    if assigned_to_id:
        query = query.filter(IssuableTool.assigned_to_id == assigned_to_id)
    
    if serial_number:
        query = query.filter(IssuableTool.serial_number.ilike(f'%{serial_number}%'))
    
    # Order by tool name
    query = query.order_by(Tool.tool_name, IssuableTool.serial_number)
    
    # Pagination
    issuable_tools = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Get filter options
    tools = Tool.query.order_by(Tool.tool_name).all()
    users = User.query.all()
    statuses = ['Available', 'In Use', 'Out for Repair', 'Retired']
    
    logger.info(f"Issuable tools list returned {issuable_tools.total} tools (page {page})")
    
    return render_template('supply/issuable_tools/list.html', 
                         issuable_tools=issuable_tools,
                         tools=tools,
                         users=users,
                         statuses=statuses,
                         current_filters={
                             'tool_id': tool_id,
                             'status': status,
                             'assigned_to_id': assigned_to_id,
                             'serial_number': serial_number
                         })

@bp.route('/<int:issuable_tool_id>')
@login_required
def detail(issuable_tool_id):
    """View individual issuable tool details"""
    logger.debug(f"User {current_user.username} accessing issuable tool detail for ID: {issuable_tool_id}")
    
    issuable_tool = IssuableTool.query.get_or_404(issuable_tool_id)
    users = User.query.all()
    
    logger.info(f"Issuable tool detail accessed - Tool: {issuable_tool.tool.tool_name if issuable_tool.tool else 'Unknown'} (ID: {issuable_tool_id})")
    
    return render_template('supply/issuable_tools/detail.html', 
                         issuable_tool=issuable_tool,
                         users=users)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new issuable tool instance"""
    # Get pre-selected tool_id from query params
    preselected_tool_id = request.args.get('tool_id', type=int)
    
    if request.method == 'POST':
        # Validate form data
        tool_id = request.form.get('tool_id', type=int)
        serial_number = request.form.get('serial_number')
        location = request.form.get('location')
        status = request.form.get('status', 'Available')
        last_calibration_date = request.form.get('last_calibration_date')
        next_calibration_date = request.form.get('next_calibration_date')
        assigned_to_id = request.form.get('assigned_to_id', type=int) or None
        
        if not tool_id:
            flash('Tool definition is required', 'error')
            tools = Tool.query.order_by(Tool.tool_name).all()
            users = User.query.all()
            return render_template('supply/issuable_tools/create.html', tools=tools, users=users, preselected_tool_id=tool_id)
        
        # Parse dates
        last_cal = None
        next_cal = None
        if last_calibration_date:
            try:
                last_cal = datetime.strptime(last_calibration_date, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid last calibration date format', 'error')
                tools = Tool.query.order_by(Tool.tool_name).all()
                users = User.query.all()
                return render_template('supply/issuable_tools/create.html', tools=tools, users=users, preselected_tool_id=tool_id)
        
        if next_calibration_date:
            try:
                next_cal = datetime.strptime(next_calibration_date, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid next calibration date format', 'error')
                tools = Tool.query.order_by(Tool.tool_name).all()
                users = User.query.all()
                return render_template('supply/issuable_tools/create.html', tools=tools, users=users, preselected_tool_id=tool_id)
        
        # Create new issuable tool
        issuable_tool = IssuableTool(
            tool_id=tool_id,
            serial_number=serial_number,
            location=location,
            status=status,
            last_calibration_date=last_cal,
            next_calibration_date=next_cal,
            assigned_to_id=assigned_to_id,
            created_by_id=current_user.id,
            updated_by_id=current_user.id
        )
        
        db.session.add(issuable_tool)
        db.session.commit()
        
        flash('Issuable tool created successfully', 'success')
        return redirect(url_for('core_supply_issuable_tools.detail', issuable_tool_id=issuable_tool.id))
    
    # Get form options
    tools = Tool.query.order_by(Tool.tool_name).all()
    users = User.query.all()
    
    return render_template('supply/issuable_tools/create.html', tools=tools, users=users, preselected_tool_id=preselected_tool_id)

@bp.route('/<int:issuable_tool_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(issuable_tool_id):
    """Edit issuable tool instance"""
    issuable_tool = IssuableTool.query.get_or_404(issuable_tool_id)
    
    if request.method == 'POST':
        # Validate form data
        tool_id = request.form.get('tool_id', type=int)
        serial_number = request.form.get('serial_number')
        location = request.form.get('location')
        status = request.form.get('status')
        last_calibration_date = request.form.get('last_calibration_date')
        next_calibration_date = request.form.get('next_calibration_date')
        assigned_to_id = request.form.get('assigned_to_id', type=int) or None
        
        if not tool_id:
            flash('Tool definition is required', 'error')
            tools = Tool.query.order_by(Tool.tool_name).all()
            users = User.query.all()
            return render_template('supply/issuable_tools/edit.html', issuable_tool=issuable_tool, tools=tools, users=users)
        
        # Parse dates
        last_cal = None
        next_cal = None
        if last_calibration_date:
            try:
                last_cal = datetime.strptime(last_calibration_date, '%Y-%m-%d').date()
            except ValueError:
                pass
        if next_calibration_date:
            try:
                next_cal = datetime.strptime(next_calibration_date, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Update issuable tool
        issuable_tool.tool_id = tool_id
        issuable_tool.serial_number = serial_number
        issuable_tool.location = location
        issuable_tool.status = status
        issuable_tool.last_calibration_date = last_cal
        issuable_tool.next_calibration_date = next_cal
        issuable_tool.assigned_to_id = assigned_to_id
        issuable_tool.updated_by_id = current_user.id
        
        db.session.commit()
        
        flash('Issuable tool updated successfully', 'success')
        return redirect(url_for('core_supply_issuable_tools.detail', issuable_tool_id=issuable_tool.id))
    
    # Get form options
    tools = Tool.query.order_by(Tool.tool_name).all()
    users = User.query.all()
    
    return render_template('supply/issuable_tools/edit.html', issuable_tool=issuable_tool, tools=tools, users=users)

@bp.route('/<int:issuable_tool_id>/delete', methods=['POST'])
@login_required
def delete(issuable_tool_id):
    """Delete issuable tool instance"""
    issuable_tool = IssuableTool.query.get_or_404(issuable_tool_id)
    
    db.session.delete(issuable_tool)
    db.session.commit()
    
    flash('Issuable tool deleted successfully', 'success')
    return redirect(url_for('core_supply_issuable_tools.list'))

@bp.route('/<int:issuable_tool_id>/assign', methods=['POST'])
@login_required
def assign(issuable_tool_id):
    """Assign issuable tool to a user"""
    issuable_tool = IssuableTool.query.get_or_404(issuable_tool_id)
    user_id = request.form.get('user_id', type=int)
    
    if not user_id:
        flash('Please select a user', 'error')
        return redirect(url_for('core_supply_issuable_tools.detail', issuable_tool_id=issuable_tool_id))
    
    issuable_tool.assign_to_user(user_id)
    issuable_tool.updated_by_id = current_user.id
    db.session.commit()
    
    flash('Tool assigned successfully', 'success')
    return redirect(url_for('core_supply_issuable_tools.detail', issuable_tool_id=issuable_tool_id))

@bp.route('/<int:issuable_tool_id>/unassign', methods=['POST'])
@login_required
def unassign(issuable_tool_id):
    """Unassign issuable tool from user"""
    issuable_tool = IssuableTool.query.get_or_404(issuable_tool_id)
    
    issuable_tool.unassign()
    issuable_tool.updated_by_id = current_user.id
    db.session.commit()
    
    flash('Tool unassigned successfully', 'success')
    return redirect(url_for('core_supply_issuable_tools.detail', issuable_tool_id=issuable_tool_id))

@bp.route('/<int:issuable_tool_id>/mark-repair', methods=['POST'])
@login_required
def mark_for_repair(issuable_tool_id):
    """Mark issuable tool as out for repair"""
    issuable_tool = IssuableTool.query.get_or_404(issuable_tool_id)
    
    issuable_tool.mark_for_repair()
    issuable_tool.updated_by_id = current_user.id
    db.session.commit()
    
    flash('Tool marked for repair', 'success')
    return redirect(url_for('core_supply_issuable_tools.detail', issuable_tool_id=issuable_tool_id))

@bp.route('/<int:issuable_tool_id>/retire', methods=['POST'])
@login_required
def retire(issuable_tool_id):
    """Retire issuable tool"""
    issuable_tool = IssuableTool.query.get_or_404(issuable_tool_id)
    
    issuable_tool.retire()
    issuable_tool.updated_by_id = current_user.id
    db.session.commit()
    
    flash('Tool retired successfully', 'success')
    return redirect(url_for('core_supply_issuable_tools.detail', issuable_tool_id=issuable_tool_id))

@bp.route('/<int:issuable_tool_id>/update-calibration', methods=['POST'])
@login_required
def update_calibration(issuable_tool_id):
    """Update calibration dates for issuable tool"""
    issuable_tool = IssuableTool.query.get_or_404(issuable_tool_id)
    
    calibration_date = request.form.get('calibration_date')
    next_calibration_date = request.form.get('next_calibration_date')
    
    if not calibration_date:
        flash('Calibration date is required', 'error')
        return redirect(url_for('core_supply_issuable_tools.detail', issuable_tool_id=issuable_tool_id))
    
    try:
        cal_date = datetime.strptime(calibration_date, '%Y-%m-%d').date()
        next_cal_date = None
        if next_calibration_date:
            next_cal_date = datetime.strptime(next_calibration_date, '%Y-%m-%d').date()
        issuable_tool.update_calibration(cal_date, next_cal_date)
    except ValueError:
        flash('Invalid date format', 'error')
        return redirect(url_for('core_supply_issuable_tools.detail', issuable_tool_id=issuable_tool_id))
    
    issuable_tool.updated_by_id = current_user.id
    db.session.commit()
    
    flash('Calibration updated successfully', 'success')
    return redirect(url_for('core_supply_issuable_tools.detail', issuable_tool_id=issuable_tool_id))

