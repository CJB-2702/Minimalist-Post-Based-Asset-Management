"""
Part management routes - integrated into core section
CRUD operations for Part model
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.data.core.supply.part_definition import PartDefinition
from app.buisness.inventory.part_context import PartContext
from app import db
from app.logger import get_logger

logger = get_logger("asset_management.routes.core.supply.parts")
bp = Blueprint('core_supply_parts', __name__)

# ROUTE_TYPE: SIMPLE_CRUD (GET)
# EXCEPTION: Direct ORM usage allowed for simple GET operations on Part
# This route performs basic list operations with minimal filtering and business logic.
# Rationale: Simple pagination and filtering on single entity type doesn't require domain abstraction.
# NOTE: CREATE/DELETE operations should use domain managers - see create() and delete() routes
@bp.route('')
@login_required
def list():
    """List all parts with basic filtering"""
    logger.debug(f"User {current_user.username} accessing parts list")
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Basic filtering
    category = request.args.get('category')
    status = request.args.get('status')
    manufacturer = request.args.get('manufacturer')
    part_name = request.args.get('part_name')
    
    logger.debug(f"Parts list filters - Category: {category}, Status: {status}")
    
    query = PartDefinition.query
    
    if category:
        query = query.filter(PartDefinition.category == category)
    
    if status:
        query = query.filter(PartDefinition.status == status)
    
    if manufacturer:
        query = query.filter(PartDefinition.manufacturer.ilike(f'%{manufacturer}%'))
    
    if part_name:
        query = query.filter(PartDefinition.part_name.ilike(f'%{part_name}%'))
    
    # Order by part name
    query = query.order_by(PartDefinition.part_name)
    
    # Pagination
    parts = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Get filter options
    categories = db.session.query(PartDefinition.category).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]
    
    manufacturers = db.session.query(PartDefinition.manufacturer).distinct().all()
    manufacturers = [man[0] for man in manufacturers if man[0]]
    
    logger.info(f"Parts list returned {parts.total} parts (page {page})")
    
    return render_template('supply/parts/list.html', 
                         parts=parts,
                         categories=categories,
                         manufacturers=manufacturers,
                         current_filters={
                             'category': category,
                             'status': status,
                             'manufacturer': manufacturer,
                             'part_name': part_name
                         })

@bp.route('/<int:part_id>')
@login_required
def detail(part_id):
    """View individual part details"""
    logger.debug(f"User {current_user.username} accessing part detail for part ID: {part_id}")
    
    # Use PartContext for data aggregation
    context = PartContext(part_id)
    
    logger.info(f"Part detail accessed - Part: {context.part.part_name} (ID: {part_id})")
    
    return render_template('supply/parts/detail.html', 
                         part=context.part,
                         part_demands=context.get_recent_demands(limit=10))

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new part"""
    if request.method == 'POST':
        # Validate form data
        part_number = request.form.get('part_number')
        part_name = request.form.get('part_name')
        description = request.form.get('description')
        category = request.form.get('category')
        manufacturer = request.form.get('manufacturer')
        supplier = request.form.get('supplier')
        revision = request.form.get('revision')
        last_unit_cost = request.form.get('last_unit_cost', type=float)
        unit_of_measure = request.form.get('unit_of_measure')
        location = request.form.get('location')
        status = request.form.get('status', 'Active')
        
        # Check if part number already exists
        if PartDefinition.query.filter_by(part_number=part_number).first():
            flash('Part number already exists', 'error')
            return render_template('supply/parts/create.html')
        
        # Create new part
        part = PartDefinition(
            part_number=part_number,
            part_name=part_name,
            description=description,
            category=category,
            manufacturer=manufacturer,
            supplier=supplier,
            revision=revision,
            last_unit_cost=last_unit_cost,
            unit_of_measure=unit_of_measure,
            location=location,
            status=status,
            created_by_id=current_user.id,
            updated_by_id=current_user.id
        )
        
        db.session.add(part)
        db.session.commit()
        
        flash('Part created successfully', 'success')
        return redirect(url_for('core_supply_parts.detail', part_id=part.id))
    
    return render_template('supply/parts/create.html')

# ROUTE_TYPE: SIMPLE_CRUD (EDIT)
# EXCEPTION: Direct ORM usage allowed for simple EDIT operations on Part
# This route performs basic update operations with minimal business logic.
# Rationale: Simple part update doesn't require domain abstraction.
# NOTE: CREATE/DELETE operations should use domain managers - see create() and delete() routes
@bp.route('/<int:part_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(part_id):
    """Edit part"""
    part = PartDefinition.query.get_or_404(part_id)
    
    if request.method == 'POST':
        # Validate form data
        part_number = request.form.get('part_number')
        part_name = request.form.get('part_name')
        description = request.form.get('description')
        category = request.form.get('category')
        manufacturer = request.form.get('manufacturer')
        supplier = request.form.get('supplier')
        revision = request.form.get('revision')
        last_unit_cost = request.form.get('last_unit_cost', type=float)
        unit_of_measure = request.form.get('unit_of_measure')
        location = request.form.get('location')
        status = request.form.get('status')
        
        # Check if part number already exists (excluding current part)
        existing_part = PartDefinition.query.filter_by(part_number=part_number).first()
        if existing_part and existing_part.id != part.id:
            flash('Part number already exists', 'error')
            return render_template('supply/parts/edit.html', part=part)
        
        # Update part
        part.part_number = part_number
        part.part_name = part_name
        part.description = description
        part.category = category
        part.manufacturer = manufacturer
        part.supplier = supplier
        part.revision = revision
        part.last_unit_cost = last_unit_cost
        part.unit_of_measure = unit_of_measure
        part.location = location
        part.status = status
        part.updated_by_id = current_user.id
        
        db.session.commit()
        
        flash('Part updated successfully', 'success')
        return redirect(url_for('core_supply_parts.detail', part_id=part.id))
    
    return render_template('supply/parts/edit.html', part=part)

@bp.route('/<int:part_id>/delete', methods=['POST'])
@login_required
def delete(part_id):
    """Delete part"""
    part = PartDefinition.query.get_or_404(part_id)
    
    # Check if part has part demands
    if part.part_demands.count() > 0:
        flash('Cannot delete part with part demands', 'error')
        return redirect(url_for('core_supply_parts.detail', part_id=part.id))
    
    db.session.delete(part)
    db.session.commit()
    
    flash('Part deleted successfully', 'success')
    return redirect(url_for('core_supply_parts.list'))



