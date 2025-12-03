"""
Meter History management routes
CRUD operations for MeterHistory model
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.data.core.asset_info.meter_history import MeterHistory
from app.data.core.asset_info.asset import Asset
from app import db
from app.logger import get_logger
from datetime import datetime

bp = Blueprint('meter_history', __name__)
logger = get_logger("asset_management.routes.core.meter_history")

@bp.route('/meter-history')
@login_required
def list():
    """List meter history records with filtering"""
    logger.debug(f"User {current_user.username} accessing meter history list")
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Filter parameters
    asset_id = request.args.get('asset_id', type=int)
    datetime_start = request.args.get('datetime_insert_start')
    datetime_end = request.args.get('datetime_insert_end')
    
    # Build query
    query = MeterHistory.query
    
    # Apply filters
    if asset_id:
        query = query.filter(MeterHistory.asset_id == asset_id)
    
    if datetime_start:
        try:
            start_dt = datetime.fromisoformat(datetime_start.replace('Z', '+00:00'))
            query = query.filter(MeterHistory.recorded_at >= start_dt)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid datetime_start format: {datetime_start}")
    
    if datetime_end:
        try:
            end_dt = datetime.fromisoformat(datetime_end.replace('Z', '+00:00'))
            query = query.filter(MeterHistory.recorded_at <= end_dt)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid datetime_end format: {datetime_end}")
    
    # Order by recorded_at descending (newest first)
    query = query.order_by(MeterHistory.recorded_at.desc())
    
    # Paginate
    meter_history = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Get all assets for filter dropdown
    assets = Asset.query.filter_by(is_active=True).order_by(Asset.name).all()
    
    logger.info(f"Meter history list returned {meter_history.total} records (page {page})")
    
    return render_template('core/meter_history/list.html',
                         meter_history=meter_history,
                         assets=assets,
                         current_filters={
                             'asset_id': asset_id,
                             'datetime_start': datetime_start,
                             'datetime_end': datetime_end
                         })

@bp.route('/meter-history/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit meter history record"""
    logger.debug(f"User {current_user.username} editing meter history ID: {id}")
    
    meter_history = MeterHistory.query.get_or_404(id)
    
    if request.method == 'POST':
        # Validate form data
        meter1 = request.form.get('meter1')
        meter2 = request.form.get('meter2')
        meter3 = request.form.get('meter3')
        meter4 = request.form.get('meter4')
        recorded_at_str = request.form.get('recorded_at')
        
        # Convert meter values (allow empty strings to become None)
        meter1 = float(meter1) if meter1 and meter1.strip() else None
        meter2 = float(meter2) if meter2 and meter2.strip() else None
        meter3 = float(meter3) if meter3 and meter3.strip() else None
        meter4 = float(meter4) if meter4 and meter4.strip() else None
        
        # Parse recorded_at
        recorded_at = None
        if recorded_at_str:
            try:
                # Try parsing ISO format
                recorded_at = datetime.fromisoformat(recorded_at_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                try:
                    # Try parsing common formats
                    recorded_at = datetime.strptime(recorded_at_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    flash('Invalid date format for recorded_at', 'error')
                    return render_template('core/meter_history/edit.html', meter_history=meter_history)
        
        # Update meter history record
        meter_history.meter1 = meter1
        meter_history.meter2 = meter2
        meter_history.meter3 = meter3
        meter_history.meter4 = meter4
        if recorded_at:
            meter_history.recorded_at = recorded_at
        meter_history.updated_by_id = current_user.id
        
        db.session.commit()
        
        flash('Meter history record updated successfully', 'success')
        return redirect(url_for('meter_history.list', asset_id=meter_history.asset_id))
    
    return render_template('core/meter_history/edit.html', meter_history=meter_history)

