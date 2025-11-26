"""
Asset detail table routes
Routes for managing asset-specific detail tables
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from app.logger import get_logger
from flask_login import login_required, current_user
from app.data.core.asset_info.asset import Asset
from app.data.assets.asset_details.purchase_info import PurchaseInfo
from app.data.assets.asset_details.vehicle_registration import VehicleRegistration
from app.data.assets.asset_details.toyota_warranty_receipt import ToyotaWarrantyReceipt
from app.buisness.assets.detail_table_context import DetailTableContext
from app.services.assets.asset_detail_service import AssetDetailService
from app import db
from pathlib import Path
from datetime import datetime

bp = Blueprint('detail_tables', __name__)
logger = get_logger("asset_management.routes.bp")

def get_detail_table_config(detail_type):
    """Get configuration for a detail table type"""
    return AssetDetailService.get_detail_table_config(detail_type)

def convert_form_data_to_model_types(model_class, form_data):
    """
    Convert form data strings to appropriate types based on model column types.
    Models take priority - form data is converted to match model types.
    
    Args:
        model_class: The SQLAlchemy model class
        form_data: Dictionary of form field names to string values
        
    Returns:
        Dictionary with converted values matching model field types
    """
    from sqlalchemy import Date, DateTime, Integer, Float, Boolean
    
    converted_data = {}
    
    for field_name, value in form_data.items():
        if value == '' or value is None:
            converted_data[field_name] = None
            continue
            
        # Get the column from the model
        if hasattr(model_class, field_name):
            column = getattr(model_class, field_name)
            if hasattr(column, 'property') and hasattr(column.property, 'columns'):
                column_type = column.property.columns[0].type
                
                # Convert based on column type
                if isinstance(column_type, Date):
                    try:
                        converted_data[field_name] = datetime.strptime(value, '%Y-%m-%d').date()
                    except ValueError:
                        converted_data[field_name] = None
                elif isinstance(column_type, DateTime):
                    try:
                        converted_data[field_name] = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        try:
                            converted_data[field_name] = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            converted_data[field_name] = None
                elif isinstance(column_type, Integer):
                    try:
                        converted_data[field_name] = int(value) if value else None
                    except ValueError:
                        converted_data[field_name] = None
                elif isinstance(column_type, Float):
                    try:
                        converted_data[field_name] = float(value) if value else None
                    except ValueError:
                        converted_data[field_name] = None
                elif isinstance(column_type, Boolean):
                    converted_data[field_name] = value.lower() in ('true', '1', 'yes', 'on')
                else:
                    # String or other types - keep as is but handle empty strings
                    converted_data[field_name] = value if value else None
            else:
                # Not a column, keep as is
                converted_data[field_name] = value if value else None
        else:
            # Field doesn't exist in model, keep as is
            converted_data[field_name] = value if value else None
    
    return converted_data

# Generic CRUD routes for all detail table types

@bp.route('/<detail_type>/')
@login_required
def list(detail_type):
    """List all records for a detail table type"""
    config = get_detail_table_config(detail_type)
    if not config:
        abort(404)
    
    # Use service to get list data with filters and form options
    records, form_options = AssetDetailService.get_list_data(detail_type, request)
    
    # Get filter parameters for template
    asset_id_filter = request.args.get('asset_id', type=int)
    model_id_filter = request.args.get('model_id', type=int)
    
    return render_template('assets/detail_tables/list.html',
                         detail_type=detail_type,
                         config=config,
                         records=records,
                         asset_options=form_options['asset_options'],
                         model_options=form_options['model_options'],
                         current_asset_filter=asset_id_filter,
                         current_model_filter=model_id_filter)

@bp.route('/<detail_type>/create', methods=['GET', 'POST'])
@login_required
def create(detail_type):
    """Create new record for a detail table type"""
    config = get_detail_table_config(detail_type)
    if not config:
        abort(404)
    
    # Get form options from service
    form_options = AssetDetailService.get_form_options()
    
    if request.method == 'POST':
        try:
            # Gather form data
            form_data = {}
            for field in config['fields']:
                if field in request.form:
                    form_data[field] = request.form.get(field)
            
            # Asset selection is required
            asset_id = request.form.get('asset_id', type=int)
            if not asset_id:
                flash('Asset selection is required', 'error')
                return render_template('assets/detail_tables/create.html',
                                     detail_type=detail_type,
                                     config=config,
                                     asset_options=form_options['asset_options'])
            
            # Convert form data to match model field types
            model_class = config['model']
            record_data = convert_form_data_to_model_types(model_class, form_data)
            
            # Create record using DetailTableContext
            record = DetailTableContext.create_detail_record(
                detail_type=detail_type,
                asset_id=asset_id,
                user_id=current_user.id,
                **record_data
            )
            db.session.commit()
            
            flash(f'{config["name"]} created successfully', 'success')
            return redirect(url_for('assets.detail_tables.list', detail_type=detail_type))
        except Exception as e:
            flash(f'Error creating {config["name"]}: {str(e)}', 'error')
            logger.error(f"Error creating detail record: {e}")
            db.session.rollback()
    
    return render_template('assets/detail_tables/create.html',
                         detail_type=detail_type,
                         config=config,
                         asset_options=form_options['asset_options'])

@bp.route('/<detail_type>/<int:id>/')
@login_required
def detail(detail_type, id):
    """View details of a specific record"""
    config = get_detail_table_config(detail_type)
    if not config:
        abort(404)
    
    # Use service to get detail record
    record = AssetDetailService.get_detail_record(detail_type, id)
    if not record:
        abort(404)
    
    return render_template('assets/detail_tables/detail.html',
                         detail_type=detail_type,
                         config=config,
                         record=record)

@bp.route('/<detail_type>/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(detail_type, id):
    """Edit a specific record"""
    config = get_detail_table_config(detail_type)
    if not config:
        abort(404)
    
    # Use service to get detail record
    record = AssetDetailService.get_detail_record(detail_type, id)
    if not record:
        abort(404)
    
    # Get form options from service
    form_options = AssetDetailService.get_form_options()
    
    if request.method == 'POST':
        try:
            # Gather form data
            form_data = {}
            for field in config['fields']:
                if field in request.form:
                    form_data[field] = request.form.get(field)
            
            # Convert form data to match model field types
            model_class = config['model']
            update_data = convert_form_data_to_model_types(model_class, form_data)
            
            # Update asset_id if present
            asset_id = request.form.get('asset_id', type=int)
            if asset_id:
                update_data['asset_id'] = asset_id
            
            # Update record using DetailTableContext
            DetailTableContext.update_detail_record(
                record=record,
                user_id=current_user.id,
                **update_data
            )
            db.session.commit()
            
            flash(f'{config["name"]} updated successfully', 'success')
            return redirect(url_for('assets.detail_tables.detail', detail_type=detail_type, id=id))
        except Exception as e:
            flash(f'Error updating {config["name"]}: {str(e)}', 'error')
            logger.error(f"Error updating detail record: {e}")
            db.session.rollback()
    
    return render_template('assets/detail_tables/edit.html',
                         detail_type=detail_type,
                         config=config,
                         record=record,
                         asset_options=form_options['asset_options'])

@bp.route('/<detail_type>/<int:id>/delete', methods=['POST'])
@login_required
def delete(detail_type, id):
    """Delete a specific record"""
    config = get_detail_table_config(detail_type)
    if not config:
        abort(404)
    
    # Use service to get detail record
    record = AssetDetailService.get_detail_record(detail_type, id)
    if not record:
        abort(404)
    
    try:
        DetailTableContext.delete_detail_record(record)
        db.session.commit()
        flash(f'{config["name"]} deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting {config["name"]}: {str(e)}', 'error')
        logger.error(f"Error deleting detail record: {e}")
        db.session.rollback()
    
    return redirect(url_for('assets.detail_tables.list', detail_type=detail_type))

# Asset-specific routes (for backward compatibility)

# ROUTE_TYPE: SIMPLE_CRUD (GET)
# EXCEPTION: Direct ORM usage allowed for backward-compatibility routes.
# This route duplicates functionality of generic routes above - legacy route.
# Rationale: Exception for backward-compatibility routes that duplicate generic route functionality.
# NOTE: CREATE/DELETE operations should use domain managers - see generic routes above
@bp.route('/assets/<int:asset_id>/purchase-info')
@login_required
def purchase_info(asset_id):
    """View purchase info for asset"""
    asset = Asset.query.get_or_404(asset_id)
    purchase_info = PurchaseInfo.query.filter_by(asset_id=asset_id).first()
    
    return render_template('assets/detail_tables/purchase_info.html', 
                         asset=asset,
                         purchase_info=purchase_info)

# ROUTE_TYPE: SIMPLE_CRUD (EDIT) - EXCEPTION for backward-compatibility
# EXCEPTION: Direct ORM usage allowed for backward-compatibility routes.
# This route duplicates functionality of generic routes above - legacy route.
# Rationale: Exception for backward-compatibility routes that duplicate generic route functionality.
# NOTE: CREATE/DELETE operations should use domain managers - see generic routes above
@bp.route('/assets/<int:asset_id>/purchase-info/edit', methods=['GET', 'POST'])
@login_required
def edit_purchase_info(asset_id):
    """Edit purchase info for asset"""
    asset = Asset.query.get_or_404(asset_id)
    purchase_info = PurchaseInfo.query.filter_by(asset_id=asset_id).first()
    
    if request.method == 'POST':
        # Convert form data to match data model field names and types
        purchase_date_str = request.form.get('purchase_date')
        purchase_date = None
        if purchase_date_str:
            try:
                purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid purchase date format', 'error')
                return render_template('assets/detail_tables/edit_purchase_info.html', 
                                     asset=asset,
                                     purchase_info=purchase_info)
        
        purchase_price = request.form.get('purchase_price', type=float)
        purchase_vendor = request.form.get('purchase_vendor') or None
        purchase_order_number = request.form.get('purchase_order_number') or None
        
        warranty_start_date_str = request.form.get('warranty_start_date')
        warranty_start_date = None
        if warranty_start_date_str:
            try:
                warranty_start_date = datetime.strptime(warranty_start_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid warranty start date format', 'error')
                return render_template('assets/detail_tables/edit_purchase_info.html', 
                                     asset=asset,
                                     purchase_info=purchase_info)
        
        warranty_end_date_str = request.form.get('warranty_end_date')
        warranty_end_date = None
        if warranty_end_date_str:
            try:
                warranty_end_date = datetime.strptime(warranty_end_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid warranty end date format', 'error')
                return render_template('assets/detail_tables/edit_purchase_info.html', 
                                     asset=asset,
                                     purchase_info=purchase_info)
        
        purchase_notes = request.form.get('purchase_notes') or None
        
        if purchase_info:
            # Update existing
            purchase_info.purchase_date = purchase_date
            purchase_info.purchase_price = purchase_price
            purchase_info.purchase_vendor = purchase_vendor
            purchase_info.purchase_order_number = purchase_order_number
            purchase_info.warranty_start_date = warranty_start_date
            purchase_info.warranty_end_date = warranty_end_date
            purchase_info.purchase_notes = purchase_notes
            purchase_info.updated_by_id = current_user.id
        else:
            # Create new
            purchase_info = PurchaseInfo(
                asset_id=asset_id,
                purchase_date=purchase_date,
                purchase_price=purchase_price,
                purchase_vendor=purchase_vendor,
                purchase_order_number=purchase_order_number,
                warranty_start_date=warranty_start_date,
                warranty_end_date=warranty_end_date,
                purchase_notes=purchase_notes,
                created_by_id=current_user.id,
                updated_by_id=current_user.id
            )
            db.session.add(purchase_info)
        
        db.session.commit()
        flash('Purchase info updated successfully', 'success')
        return redirect(url_for('assets.detail_tables.purchase_info', asset_id=asset_id))
    
    return render_template('assets/detail_tables/edit_purchase_info.html', 
                         asset=asset,
                         purchase_info=purchase_info)

# ROUTE_TYPE: SIMPLE_CRUD (GET)
# EXCEPTION: Direct ORM usage allowed for backward-compatibility routes.
# This route duplicates functionality of generic routes above - legacy route.
# Rationale: Exception for backward-compatibility routes that duplicate generic route functionality.
# NOTE: CREATE/DELETE operations should use domain managers - see generic routes above
@bp.route('/assets/<int:asset_id>/vehicle-registration')
@login_required
def vehicle_registration(asset_id):
    """View vehicle registration for asset"""
    asset = Asset.query.get_or_404(asset_id)
    registration = VehicleRegistration.query.filter_by(asset_id=asset_id).first()
    
    return render_template('assets/detail_tables/vehicle_registration.html', 
                         asset=asset,
                         registration=registration)

# ROUTE_TYPE: SIMPLE_CRUD (EDIT) - EXCEPTION for backward-compatibility
# EXCEPTION: Direct ORM usage allowed for backward-compatibility routes.
# This route duplicates functionality of generic routes above - legacy route.
# Rationale: Exception for backward-compatibility routes that duplicate generic route functionality.
# NOTE: CREATE/DELETE operations should use domain managers - see generic routes above
@bp.route('/assets/<int:asset_id>/vehicle-registration/edit', methods=['GET', 'POST'])
@login_required
def edit_vehicle_registration(asset_id):
    """Edit vehicle registration for asset"""
    asset = Asset.query.get_or_404(asset_id)
    registration = VehicleRegistration.query.filter_by(asset_id=asset_id).first()
    
    if request.method == 'POST':
        # Convert form data to match data model field names and types
        license_plate = request.form.get('license_plate') or None
        registration_number = request.form.get('registration_number') or None
        
        registration_expiry_str = request.form.get('registration_expiry')
        registration_expiry = None
        if registration_expiry_str:
            try:
                registration_expiry = datetime.strptime(registration_expiry_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid registration expiry date format', 'error')
                return render_template('assets/detail_tables/edit_vehicle_registration.html', 
                                     asset=asset,
                                     registration=registration)
        
        vin_number = request.form.get('vin_number') or None
        state_registered = request.form.get('state_registered') or None
        registration_status = request.form.get('registration_status') or 'Active'
        insurance_provider = request.form.get('insurance_provider') or None
        insurance_policy_number = request.form.get('insurance_policy_number') or None
        
        insurance_expiry_str = request.form.get('insurance_expiry')
        insurance_expiry = None
        if insurance_expiry_str:
            try:
                insurance_expiry = datetime.strptime(insurance_expiry_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid insurance expiry date format', 'error')
                return render_template('assets/detail_tables/edit_vehicle_registration.html', 
                                     asset=asset,
                                     registration=registration)
        
        if registration:
            # Update existing
            registration.license_plate = license_plate
            registration.registration_number = registration_number
            registration.registration_expiry = registration_expiry
            registration.vin_number = vin_number
            registration.state_registered = state_registered
            registration.registration_status = registration_status
            registration.insurance_provider = insurance_provider
            registration.insurance_policy_number = insurance_policy_number
            registration.insurance_expiry = insurance_expiry
            registration.updated_by_id = current_user.id
        else:
            # Create new
            registration = VehicleRegistration(
                asset_id=asset_id,
                license_plate=license_plate,
                registration_number=registration_number,
                registration_expiry=registration_expiry,
                vin_number=vin_number,
                state_registered=state_registered,
                registration_status=registration_status,
                insurance_provider=insurance_provider,
                insurance_policy_number=insurance_policy_number,
                insurance_expiry=insurance_expiry,
                created_by_id=current_user.id,
                updated_by_id=current_user.id
            )
            db.session.add(registration)
        
        db.session.commit()
        flash('Vehicle registration updated successfully', 'success')
        return redirect(url_for('assets.detail_tables.vehicle_registration', asset_id=asset_id))
    
    return render_template('assets/detail_tables/edit_vehicle_registration.html', 
                         asset=asset,
                         registration=registration)

# ROUTE_TYPE: SIMPLE_CRUD (GET)
# EXCEPTION: Direct ORM usage allowed for backward-compatibility routes.
# This route duplicates functionality of generic routes above - legacy route.
# Rationale: Exception for backward-compatibility routes that duplicate generic route functionality.
# NOTE: CREATE/DELETE operations should use domain managers - see generic routes above
@bp.route('/assets/<int:asset_id>/toyota-warranty')
@login_required
def toyota_warranty(asset_id):
    """View Toyota warranty info for asset"""
    asset = Asset.query.get_or_404(asset_id)
    warranty = ToyotaWarrantyReceipt.query.filter_by(asset_id=asset_id).first()
    
    return render_template('assets/detail_tables/toyota_warranty_receipt.html', 
                         asset=asset,
                         warranty=warranty)

# ROUTE_TYPE: SIMPLE_CRUD (EDIT) - EXCEPTION for backward-compatibility
# EXCEPTION: Direct ORM usage allowed for backward-compatibility routes.
# This route duplicates functionality of generic routes above - legacy route.
# Rationale: Exception for backward-compatibility routes that duplicate generic route functionality.
# NOTE: CREATE/DELETE operations should use domain managers - see generic routes above
@bp.route('/assets/<int:asset_id>/toyota-warranty/edit', methods=['GET', 'POST'])
@login_required
def edit_toyota_warranty(asset_id):
    """Edit Toyota warranty info for asset"""
    asset = Asset.query.get_or_404(asset_id)
    warranty = ToyotaWarrantyReceipt.query.filter_by(asset_id=asset_id).first()
    
    if request.method == 'POST':
        # Convert form data to match data model field names and types
        warranty_receipt_number = request.form.get('warranty_receipt_number') or None
        warranty_type = request.form.get('warranty_type') or None
        
        warranty_mileage_limit = request.form.get('warranty_mileage_limit', type=int)
        if warranty_mileage_limit == '':
            warranty_mileage_limit = None
        
        warranty_time_limit_months = request.form.get('warranty_time_limit_months', type=int)
        if warranty_time_limit_months == '':
            warranty_time_limit_months = None
        
        dealer_name = request.form.get('dealer_name') or None
        dealer_contact = request.form.get('dealer_contact') or None
        dealer_phone = request.form.get('dealer_phone') or None
        dealer_email = request.form.get('dealer_email') or None
        service_history = request.form.get('service_history') or None
        warranty_claims = request.form.get('warranty_claims') or None
        
        if warranty:
            # Update existing
            warranty.warranty_receipt_number = warranty_receipt_number
            warranty.warranty_type = warranty_type
            warranty.warranty_mileage_limit = warranty_mileage_limit
            warranty.warranty_time_limit_months = warranty_time_limit_months
            warranty.dealer_name = dealer_name
            warranty.dealer_contact = dealer_contact
            warranty.dealer_phone = dealer_phone
            warranty.dealer_email = dealer_email
            warranty.service_history = service_history
            warranty.warranty_claims = warranty_claims
            warranty.updated_by_id = current_user.id
        else:
            # Create new
            warranty = ToyotaWarrantyReceipt(
                asset_id=asset_id,
                warranty_receipt_number=warranty_receipt_number,
                warranty_type=warranty_type,
                warranty_mileage_limit=warranty_mileage_limit,
                warranty_time_limit_months=warranty_time_limit_months,
                dealer_name=dealer_name,
                dealer_contact=dealer_contact,
                dealer_phone=dealer_phone,
                dealer_email=dealer_email,
                service_history=service_history,
                warranty_claims=warranty_claims,
                created_by_id=current_user.id,
                updated_by_id=current_user.id
            )
            db.session.add(warranty)
        
        db.session.commit()
        flash('Toyota warranty info updated successfully', 'success')
        return redirect(url_for('assets.detail_tables.toyota_warranty', asset_id=asset_id))
    
    return render_template('assets/detail_tables/edit_toyota_warranty_receipt.html', 
                         asset=asset,
                         warranty=warranty) 