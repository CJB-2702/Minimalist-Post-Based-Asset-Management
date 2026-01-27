"""
Request CRUD routes for dispatching module
"""

from flask import render_template, request, redirect, url_for, flash
from datetime import datetime
from flask_login import login_required, current_user
from app.presentation.routes.dispatching import dispatching_bp
from app import db
from app.data.dispatching.request import DispatchRequest
from app.buisness.dispatching.dispatch_manager import DispatchManager
from app.buisness.dispatching.context import DispatchContext
from app.data.core.asset_info.asset_type import AssetType
from app.data.core.major_location import MajorLocation
from app.data.core.asset_info.asset import Asset
from app.data.core.user_info.user import User
from app.services.dispatching.request_service import DispatchRequestService
from app.data.core.event_info.comment import Comment
from app.buisness.dispatching.request_manager import RequestManager
from app.buisness.dispatching.errors import RequestIntentLockError


@dispatching_bp.route('/requests')
def requests_list():
    """List all dispatch requests with filtering and pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Use service to get list data with filters
    requests_page, filter_options = DispatchRequestService.get_list_data(
        request=request,
        page=page,
        per_page=per_page
    )
    
    return render_template('dispatching/requests/list.html', 
                         requests=requests_page,
                         filter_options=filter_options)


@dispatching_bp.route('/requests/new', methods=['GET', 'POST'])
@login_required
def requests_new():
    """Create new dispatch request"""
    if request.method == 'POST':
        form = request.form

        # Validate required fields
        required_fields = ['requested_for_id', 'desired_start', 'desired_end', 'asset_type_id', 'major_location_id']
        missing_fields = [field for field in required_fields if not form.get(field)]
        if missing_fields:
            flash(f'Missing required fields: {", ".join(missing_fields)}', 'danger')
            return redirect(url_for('dispatching.requests_new'))

        # Parse and coerce request data
        try:
            desired_start_raw = form.get('desired_start')
            desired_end_raw = form.get('desired_end')
            desired_start_dt = datetime.fromisoformat(desired_start_raw) if desired_start_raw else None
            desired_end_dt = datetime.fromisoformat(desired_end_raw) if desired_end_raw else None
        except ValueError:
            flash('Invalid date/time format. Please use the provided picker.', 'danger')
            return redirect(url_for('dispatching.requests_new'))

        num_people_raw = form.get('num_people')
        num_people = int(num_people_raw) if num_people_raw else None

        estimated_meter_raw = form.get('estimated_meter_usage')
        try:
            estimated_meter_usage = float(estimated_meter_raw) if estimated_meter_raw else None
        except ValueError:
            flash('Estimated meter usage must be a number.', 'danger')
            return redirect(url_for('dispatching.requests_new'))

        asset_type_id_raw = form.get('asset_type_id')
        major_location_id_raw = form.get('major_location_id')
        requested_by_raw = form.get('requested_by')
        requested_for_raw = form.get('requested_for_id')
        
        try:
            asset_type_id = int(asset_type_id_raw) if asset_type_id_raw else None
            major_location_id = int(major_location_id_raw) if major_location_id_raw else None
            # Default requested_by to current user if not provided or invalid
            requested_by = int(requested_by_raw) if requested_by_raw else current_user.id
            requested_for = int(requested_for_raw) if requested_for_raw else None
        except ValueError:
            flash('Invalid selection for asset type, location, or user.', 'danger')
            return redirect(url_for('dispatching.requests_new'))

        # Validate requested_for is provided
        if not requested_for:
            flash('You must select a user for "Requested For" field.', 'danger')
            return redirect(url_for('dispatching.requests_new'))

        # Use DispatchManager to create request
        try:
            item = DispatchManager.create_request(
                requested_by=requested_by,
                requested_for=requested_for,
                submitted_at=datetime.utcnow(),
                desired_start=desired_start_dt,
                desired_end=desired_end_dt,
                num_people=num_people,
                names_freeform=form.get('names_freeform') or None,
                asset_type_id=asset_type_id,
                asset_subclass_text=form.get('asset_subclass_text') or '',
                dispatch_scope=form.get('dispatch_scope') or 'Local',
                estimated_meter_usage=estimated_meter_usage,
                major_location_id=major_location_id,
                activity_location=form.get('activity_location') or None,
                notes=form.get('notes') or None,
                workflow_status='Requested',  # Requests start as Requested (initial state)
                status='Requested',  # Legacy field
            )
            db.session.commit()
            flash('Dispatch request created', 'success')
            return redirect(url_for('dispatching.requests_detail', item_id=item.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating request: {str(e)}', 'danger')
            return redirect(url_for('dispatching.requests_new'))

    asset_types = AssetType.query.all()
    locations = MajorLocation.query.all()
    return render_template('dispatching/requests/form.html', asset_types=asset_types, locations=locations)


@dispatching_bp.route('/requests/<int:item_id>')
@dispatching_bp.route('/requests/<int:item_id>/view')
def requests_detail(item_id):
    """View dispatch request details"""
    ctx = DispatchContext.load(item_id)
    
    # Collect all outcomes for this request (using outcome_history)
    all_outcomes = []
    if ctx.dispatch:
        all_outcomes.append(('dispatch', ctx.dispatch))
    if ctx.contract:
        all_outcomes.append(('contract', ctx.contract))
    if ctx.reimbursement:
        all_outcomes.append(('reimbursement', ctx.reimbursement))
    if ctx.reject:
        all_outcomes.append(('reject', ctx.reject))
    
    # Get data for outcome forms if no active outcome exists
    assets = None
    users = None
    if not ctx.has_active_outcome:
        # Get assets matching the request's asset type
        if ctx.request.asset_type_id:
            assets = Asset.query.filter(
                Asset.make_model.has(asset_type_id=ctx.request.asset_type_id)
            ).all()
        else:
            assets = Asset.query.limit(100).all()
        users = User.query.filter_by(is_active=True).all()
    
    return render_template('dispatching/requests/detail.html', 
                         ctx=ctx, 
                         item=ctx.request,
                         all_outcomes=all_outcomes,
                         assets=assets,
                         users=users)


@dispatching_bp.route('/requests/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def requests_edit(item_id):
    """Edit existing dispatch request"""
    item = DispatchRequest.query.get_or_404(item_id)
    
    # Check if request has an active outcome (some fields are locked)
    has_active_outcome = item.active_outcome_type is not None
    
    if request.method == 'POST':
        form = request.form
        changes = []  # Track changes for comment
        updates = {}  # Track field updates for validation
        
        # Build updates dictionary from form data
        try:
            # Parse always-editable fields
            dispatch_scope = form.get('dispatch_scope') or 'Local'
            estimated_meter_raw = form.get('estimated_meter_usage')
            estimated_meter_usage = float(estimated_meter_raw) if estimated_meter_raw else None
            activity_location = form.get('activity_location') or None
            num_people_raw = form.get('num_people')
            num_people = int(num_people_raw) if num_people_raw else None
            names_freeform = form.get('names_freeform') or None
            notes = form.get('notes') or None
            
            # Add always-editable fields to updates
            if dispatch_scope != item.dispatch_scope:
                updates['dispatch_scope'] = dispatch_scope
            if estimated_meter_usage != item.estimated_meter_usage:
                updates['estimated_meter_usage'] = estimated_meter_usage
            if activity_location != item.activity_location:
                updates['activity_location'] = activity_location
            if num_people != item.num_people:
                updates['num_people'] = num_people
            if names_freeform != item.names_freeform:
                updates['names_freeform'] = names_freeform
            if notes != item.notes:
                updates['notes'] = notes
            
            # Parse potentially locked fields (only if form submitted them)
            if not has_active_outcome:
                # Parse datetime fields
                try:
                    desired_start_raw = form.get('desired_start')
                    desired_end_raw = form.get('desired_end')
                    desired_start_dt = datetime.fromisoformat(desired_start_raw) if desired_start_raw else None
                    desired_end_dt = datetime.fromisoformat(desired_end_raw) if desired_end_raw else None
                except ValueError:
                    flash('Invalid date/time format. Please use the provided picker.', 'danger')
                    return redirect(url_for('dispatching.requests_edit', item_id=item_id))
                
                # Add locked fields to updates if changed
                if desired_start_dt != item.desired_start:
                    updates['desired_start'] = desired_start_dt
                if desired_end_dt != item.desired_end:
                    updates['desired_end'] = desired_end_dt
                
                # Parse other locked fields
                asset_type_id = int(form.get('asset_type_id')) if form.get('asset_type_id') else None
                major_location_id = int(form.get('major_location_id')) if form.get('major_location_id') else None
                asset_subclass_text = form.get('asset_subclass_text') or ''
                
                if asset_type_id != item.asset_type_id:
                    updates['asset_type_id'] = asset_type_id
                if major_location_id != item.major_location_id:
                    updates['major_location_id'] = major_location_id
                if asset_subclass_text != item.asset_subclass_text:
                    updates['asset_subclass_text'] = asset_subclass_text
            
        except ValueError as e:
            flash(f'Invalid input: {str(e)}', 'danger')
            return redirect(url_for('dispatching.requests_edit', item_id=item_id))
        
        # Validate updates using business layer
        try:
            ctx = DispatchContext.load(item_id)
            request_manager = RequestManager(ctx)
            request_manager.validate_intent_update(updates)
            
            # Apply updates and track changes
            for field_name, new_value in updates.items():
                old_value = getattr(item, field_name)
                setattr(item, field_name, new_value)
                changes.append(f"{field_name.replace('_', ' ').title()}: '{old_value}' → '{new_value}'")
            
            # If changes were made, create a comment on the event
            if changes:
                change_summary = "\n".join(changes)
                comment = Comment(
                    event_id=item.event_id,
                    content=f"Request updated by {current_user.username}:\n{change_summary}",
                    is_human_made=False,
                    created_by_id=current_user.id
                )
                db.session.add(comment)
                flash('Dispatch request updated successfully', 'success')
            else:
                flash('No changes detected', 'info')
            
            db.session.commit()
            return redirect(url_for('dispatching.requests_detail', item_id=item.id))
            
        except RequestIntentLockError as e:
            flash(f'Cannot update: {str(e)}', 'warning')
            return redirect(url_for('dispatching.requests_edit', item_id=item_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating request: {str(e)}', 'danger')
            return redirect(url_for('dispatching.requests_edit', item_id=item_id))

    asset_types = AssetType.query.all()
    locations = MajorLocation.query.all()
    return render_template('dispatching/requests/form.html', 
                         item=item, 
                         asset_types=asset_types, 
                         locations=locations,
                         has_active_outcome=has_active_outcome)
