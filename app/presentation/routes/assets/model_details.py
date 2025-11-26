"""
Model detail table routes
Routes for managing model-specific detail tables
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from app.logger import get_logger
from flask_login import login_required, current_user
from app.data.core.asset_info.make_model import MakeModel
from app.data.assets.model_details.emissions_info import EmissionsInfo
from app.data.assets.model_details.model_info import ModelInfo
from app.buisness.assets.model_detail_context import ModelDetailContext
from app.services.assets.model_detail_service import ModelDetailService
from app import db
from pathlib import Path

bp = Blueprint('model_details', __name__)
logger = get_logger("asset_management.routes.bp")

def get_model_detail_table_config(detail_type):
    """Get configuration for a model detail table type"""
    return ModelDetailService.get_model_detail_table_config(detail_type)

# Generic CRUD routes for all model detail table types

@bp.route('/<detail_type>/')
@login_required
def list(detail_type):
    """List all records for a model detail table type"""
    config = get_model_detail_table_config(detail_type)
    if not config:
        abort(404)
    
    # Use service to get list data
    records = ModelDetailService.get_list_data(detail_type)
    
    return render_template('assets/model_details/list.html',
                         detail_type=detail_type,
                         config=config,
                         records=records)

@bp.route('/<detail_type>/create', methods=['GET', 'POST'])
@login_required
def create(detail_type):
    """Create new record for a model detail table type"""
    config = get_model_detail_table_config(detail_type)
    if not config:
        abort(404)
    
    if request.method == 'POST':
        try:
            # Gather form data
            record_data = {}
            for field in config['fields']:
                value = request.form.get(field)
                if value:
                    record_data[field] = value
            
            # Make model selection is required
            make_model_id = request.form.get('make_model_id', type=int)
            if not make_model_id:
                flash('Make/Model selection is required', 'error')
                return render_template('assets/model_details/create.html',
                                     detail_type=detail_type,
                                     config=config)
            
            # Create record using ModelDetailContext
            record = ModelDetailContext.create_detail_record(
                detail_type=detail_type,
                make_model_id=make_model_id,
                user_id=current_user.id,
                **record_data
            )
            db.session.commit()
            
            flash(f'{config["name"]} created successfully', 'success')
            return redirect(url_for('assets.model_details.list', detail_type=detail_type))
        except Exception as e:
            flash(f'Error creating {config["name"]}: {str(e)}', 'error')
            logger.error(f"Error creating model detail record: {e}")
            db.session.rollback()
    
    return render_template('assets/model_details/create.html',
                         detail_type=detail_type,
                         config=config)

@bp.route('/<detail_type>/<int:id>/')
@login_required
def detail(detail_type, id):
    """View details of a specific model detail record"""
    config = get_model_detail_table_config(detail_type)
    if not config:
        abort(404)
    
    # Use service to get detail record
    record = ModelDetailService.get_detail_record(detail_type, id)
    if not record:
        abort(404)
    
    return render_template('assets/model_details/detail.html',
                         detail_type=detail_type,
                         config=config,
                         record=record)

@bp.route('/<detail_type>/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(detail_type, id):
    """Edit a specific model detail record"""
    config = get_model_detail_table_config(detail_type)
    if not config:
        abort(404)
    
    # Use service to get detail record
    record = ModelDetailService.get_detail_record(detail_type, id)
    if not record:
        abort(404)
    
    if request.method == 'POST':
        try:
            # Gather update data
            update_data = {}
            for field in config['fields']:
                # Skip event_id - it's set automatically and cannot be changed
                if field == 'event_id':
                    continue
                if field in request.form:
                    update_data[field] = request.form.get(field)
            
            # Update record using ModelDetailContext
            ModelDetailContext.update_detail_record(
                record=record,
                user_id=current_user.id,
                **update_data
            )
            db.session.commit()
            
            flash(f'{config["name"]} updated successfully', 'success')
            return redirect(url_for('assets.model_details.detail', detail_type=detail_type, id=id))
        except Exception as e:
            flash(f'Error updating {config["name"]}: {str(e)}', 'error')
            logger.error(f"Error updating model detail record: {e}")
            db.session.rollback()
    
    return render_template('assets/model_details/edit.html',
                         detail_type=detail_type,
                         config=config,
                         record=record)

@bp.route('/<detail_type>/<int:id>/delete', methods=['POST'])
@login_required
def delete(detail_type, id):
    """Delete a specific model detail record"""
    config = get_model_detail_table_config(detail_type)
    if not config:
        abort(404)
    
    # Use service to get detail record
    record = ModelDetailService.get_detail_record(detail_type, id)
    if not record:
        abort(404)
    
    try:
        ModelDetailContext.delete_detail_record(record)
        db.session.commit()
        flash(f'{config["name"]} deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting {config["name"]}: {str(e)}', 'error')
        logger.error(f"Error deleting model detail record: {e}")
        db.session.rollback()
    
    return redirect(url_for('assets.model_details.list', detail_type=detail_type))

# Make/Model-specific routes (for backward compatibility)

# ROUTE_TYPE: SIMPLE_CRUD (GET)
# EXCEPTION: Direct ORM usage allowed for backward-compatibility routes.
# This route duplicates functionality of generic routes above - legacy route.
# Rationale: Exception for backward-compatibility routes that duplicate generic route functionality.
# NOTE: CREATE/DELETE operations should use domain managers - see generic routes above
@bp.route('/make-models/<int:make_model_id>/emissions-info')
@login_required
def emissions_info(make_model_id):
    """View emissions info for make/model"""
    make_model = MakeModel.query.get_or_404(make_model_id)
    # Use service to get detail record
    emissions = ModelDetailService.get_detail_for_model('emissions_info', make_model_id)
    
    return render_template('assets/model_details/emissions_info.html', 
                         make_model=make_model,
                         emissions=emissions)

# ROUTE_TYPE: SIMPLE_CRUD (EDIT) - EXCEPTION for backward-compatibility
# EXCEPTION: Direct ORM usage allowed for backward-compatibility routes.
# This route duplicates functionality of generic routes above - legacy route.
# Rationale: Exception for backward-compatibility routes that duplicate generic route functionality.
# NOTE: CREATE/DELETE operations should use domain managers - see generic routes above
@bp.route('/make-models/<int:make_model_id>/emissions-info/edit', methods=['GET', 'POST'])
@login_required
def edit_emissions_info(make_model_id):
    """Edit emissions info for make/model"""
    make_model = MakeModel.query.get_or_404(make_model_id)
    # Use service to get detail record
    emissions = ModelDetailService.get_detail_for_model('emissions_info', make_model_id)
    
    if request.method == 'POST':
        # Validate form data
        fuel_economy_city = request.form.get('fuel_economy_city', type=float)
        fuel_economy_highway = request.form.get('fuel_economy_highway', type=float)
        fuel_economy_combined = request.form.get('fuel_economy_combined', type=float)
        emissions_standard = request.form.get('emissions_standard')
        co2_emissions = request.form.get('co2_emissions', type=float)
        certification_date = request.form.get('certification_date')
        notes = request.form.get('notes')
        
        if emissions:
            # Update existing
            emissions.fuel_economy_city = fuel_economy_city
            emissions.fuel_economy_highway = fuel_economy_highway
            emissions.fuel_economy_combined = fuel_economy_combined
            emissions.emissions_standard = emissions_standard
            emissions.co2_emissions = co2_emissions
            emissions.certification_date = certification_date
            emissions.notes = notes
            emissions.updated_by_id = current_user.id
        else:
            # Create new
            emissions = EmissionsInfo(
                make_model_id=make_model_id,
                fuel_economy_city = fuel_economy_city,
                fuel_economy_highway = fuel_economy_highway,
                fuel_economy_combined = fuel_economy_combined,
                emissions_standard = emissions_standard,
                co2_emissions = co2_emissions,
                certification_date = certification_date,
                notes = notes,
                created_by_id=current_user.id,
                updated_by_id=current_user.id
            )
            db.session.add(emissions)
        
        db.session.commit()
        flash('Emissions info updated successfully', 'success')
        return redirect(url_for('assets.model_details.emissions_info', make_model_id=make_model_id))
    
    return render_template('assets/model_details/edit_emissions_info.html', 
                         make_model=make_model,
                         emissions=emissions)

# ROUTE_TYPE: SIMPLE_CRUD (GET)
# EXCEPTION: Direct ORM usage allowed for backward-compatibility routes.
# This route duplicates functionality of generic routes above - legacy route.
# Rationale: Exception for backward-compatibility routes that duplicate generic route functionality.
# NOTE: CREATE/DELETE operations should use domain managers - see generic routes above
@bp.route('/make-models/<int:make_model_id>/model-info')
@login_required
def model_info(make_model_id):
    """View model info for make/model"""
    make_model = MakeModel.query.get_or_404(make_model_id)
    # Use service to get detail record
    model_info = ModelDetailService.get_detail_for_model('model_info', make_model_id)
    
    return render_template('assets/model_details/model_info.html', 
                         make_model=make_model,
                         model_info=model_info)

# ROUTE_TYPE: SIMPLE_CRUD (EDIT) - EXCEPTION for backward-compatibility
# EXCEPTION: Direct ORM usage allowed for backward-compatibility routes.
# This route duplicates functionality of generic routes above - legacy route.
# Rationale: Exception for backward-compatibility routes that duplicate generic route functionality.
# NOTE: CREATE/DELETE operations should use domain managers - see generic routes above
@bp.route('/make-models/<int:make_model_id>/model-info/edit', methods=['GET', 'POST'])
@login_required
def edit_model_info(make_model_id):
    """Edit model info for make/model"""
    make_model = MakeModel.query.get_or_404(make_model_id)
    # Use service to get detail record
    model_info = ModelDetailService.get_detail_for_model('model_info', make_model_id)
    
    if request.method == 'POST':
        # Validate form data
        body_style = request.form.get('body_style')
        engine_type = request.form.get('engine_type')
        transmission = request.form.get('transmission')
        drivetrain = request.form.get('drivetrain')
        seating_capacity = request.form.get('seating_capacity', type=int)
        cargo_capacity = request.form.get('cargo_capacity')
        towing_capacity = request.form.get('towing_capacity', type=float)
        fuel_type = request.form.get('fuel_type')
        fuel_capacity = request.form.get('fuel_capacity', type=float)
        notes = request.form.get('notes')
        
        if model_info:
            # Update existing
            model_info.body_style = body_style
            model_info.engine_type = engine_type
            model_info.transmission = transmission
            model_info.drivetrain = drivetrain
            model_info.seating_capacity = seating_capacity
            model_info.cargo_capacity = cargo_capacity
            model_info.towing_capacity = towing_capacity
            model_info.fuel_type = fuel_type
            model_info.fuel_capacity = fuel_capacity
            model_info.notes = notes
            model_info.updated_by_id = current_user.id
        else:
            # Create new
            model_info = ModelInfo(
                make_model_id=make_model_id,
                body_style = body_style,
                engine_type = engine_type,
                transmission = transmission,
                drivetrain = drivetrain,
                seating_capacity = seating_capacity,
                cargo_capacity = cargo_capacity,
                towing_capacity = towing_capacity,
                fuel_type = fuel_type,
                fuel_capacity = fuel_capacity,
                notes = notes,
                created_by_id=current_user.id,
                updated_by_id=current_user.id
            )
            db.session.add(model_info)
        
        db.session.commit()
        flash('Model info updated successfully', 'success')
        return redirect(url_for('assets.model_details.model_info', make_model_id=make_model_id))
    
    return render_template('assets/model_details/edit_model_info.html', 
                         make_model=make_model,
                         model_info=model_info) 