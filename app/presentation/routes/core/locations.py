"""
Location management routes
CRUD operations for MajorLocation model
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from app.logger import get_logger
from flask_login import login_required, current_user
from app.data.core.major_location import MajorLocation
from app.data.core.asset_info.asset import Asset
from app.services.core.location_service import LocationService
from app import db

bp = Blueprint('locations', __name__)
logger = get_logger("asset_management.routes.bp")

@bp.route('/locations')
@login_required
def list():
    """List all locations"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Use service to get list data
    locations, count_dicts = LocationService.get_list_data(
        request=request,
        page=page,
        per_page=per_page
    )
    
    return render_template('core/locations/list.html', 
                         locations=locations, 
                         asset_counts=count_dicts['asset_counts'])

@bp.route('/locations/<int:location_id>')
@login_required
def detail(location_id):
    """View location details"""
    # Use service to get detail data
    detail_data = LocationService.get_detail_data(location_id)
    
    return render_template('core/locations/detail.html', 
                         location=detail_data['location'],
                         assets=detail_data['assets'],
                         events=detail_data['events'],
                         Asset=Asset)

# ROUTE_TYPE: DOMAIN_MANAGER (CREATE) - EXCEPTION
# EXCEPTION: Direct ORM usage allowed for location create operations.
# Rationale: Exception for simple entity creation without complex business logic.
@bp.route('/locations/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new location"""
    if request.method == 'POST':
        # Validate form data
        name = request.form.get('name')
        description = request.form.get('description')
        address = request.form.get('address')
        is_active = request.form.get('is_active') == 'on'
        
        # Check if name already exists
        if MajorLocation.query.filter_by(name=name).first():
            flash('Location name already exists', 'error')
            return render_template('core/locations/create.html')
        
        # Create new location
        location = MajorLocation(
            name=name,
            description=description,
            address=address,
            is_active=is_active,
            created_by_id=current_user.id,
            updated_by_id=current_user.id
        )
        
        db.session.add(location)
        db.session.commit()
        
        flash('Location created successfully', 'success')
        return redirect(url_for('locations.detail', location_id=location.id))
    
    return render_template('core/locations/create.html')

# ROUTE_TYPE: SIMPLE_CRUD (EDIT)
# EXCEPTION: Direct ORM usage allowed for simple EDIT operations on MajorLocation
# This route performs basic update operations with minimal business logic.
# Rationale: Simple location update doesn't require domain abstraction.
# NOTE: CREATE/DELETE operations should use domain managers - see create() and delete() routes
@bp.route('/locations/<int:location_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(location_id):
    """Edit location"""
    location = MajorLocation.query.get_or_404(location_id)
    
    if request.method == 'POST':
        # Validate form data
        name = request.form.get('name')
        description = request.form.get('description')
        address = request.form.get('address')
        is_active = request.form.get('is_active') == 'on'
        
        # Check if name already exists (excluding current location)
        existing_location = MajorLocation.query.filter_by(name=name).first()
        if existing_location and existing_location.id != location.id:
            flash('Location name already exists', 'error')
            return render_template('core/locations/edit.html', location=location, Asset=Asset)
        
        # Update location
        location.name = name
        location.description = description
        location.address = address
        location.is_active = is_active
        location.updated_by_id = current_user.id
        
        db.session.commit()
        
        flash('Location updated successfully', 'success')
        return redirect(url_for('locations.detail', location_id=location.id))
    
    return render_template('core/locations/edit.html', location=location, Asset=Asset)

# ROUTE_TYPE: DOMAIN_MANAGER (DELETE) - EXCEPTION
# EXCEPTION: Direct ORM usage allowed for location delete operations.
# Rationale: Exception for simple entity deletion with basic validation.
@bp.route('/locations/<int:location_id>/delete', methods=['POST'])
@login_required
def delete(location_id):
    """Delete location"""
    location = MajorLocation.query.get_or_404(location_id)
    
    # Check if location has assets
    if Asset.query.filter_by(major_location_id=location.id).count() > 0:
        flash('Cannot delete location with assets', 'error')
        return redirect(url_for('locations.detail', location_id=location.id))
    
    db.session.delete(location)
    db.session.commit()
    
    flash('Location deleted successfully', 'success')
    return redirect(url_for('locations.list')) 