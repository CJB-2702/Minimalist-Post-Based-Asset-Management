"""
Dispatch (StandardDispatch) CRUD routes for dispatching module
"""

from flask import render_template, request, redirect, url_for, flash
from datetime import datetime
from flask_login import current_user, login_required
from app.presentation.routes.dispatching import dispatching_bp
from app import db
from app.data.dispatching.outcomes.standard_dispatch import StandardDispatch
from app.buisness.dispatching.context import DispatchContext
from app.buisness.dispatching.policies.dispatch_status_validation import DispatchStatusValidationPolicy
from app.buisness.dispatching.errors import DispatchPolicyViolation
from app.data.core.asset_info.asset import Asset
from app.data.core.user_info.user import User
from app.services.dispatching.dispatch_service import DispatchService


@dispatching_bp.route('/dispatches')
def dispatches_list():
    """List all dispatches with filtering and pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Use service to get list data with filters
    dispatches_page, filter_options = DispatchService.get_list_data(
        request=request,
        page=page,
        per_page=per_page
    )
    
    # Create contexts for each dispatch to access full request data
    contexts = [DispatchContext.load(d.request_id) for d in dispatches_page.items]
    
    return render_template('dispatching/outcomes/dispatches/list.html', 
                         items=dispatches_page,
                         contexts=contexts,
                         filter_options=filter_options)


@dispatching_bp.route('/dispatches/<int:item_id>')
@dispatching_bp.route('/dispatches/<int:item_id>/view')
def dispatches_detail(item_id):
    """View dispatch details"""
    dispatch = StandardDispatch.query.get_or_404(item_id)
    ctx = DispatchContext.load(dispatch.request_id)
    
    # Get all outcomes for this request (excluding current dispatch to avoid duplication)
    all_outcomes = []
    other_outcomes = []
    if ctx.dispatch:
        all_outcomes.append(('dispatch', ctx.dispatch))
        # Only add to other_outcomes if it's a different dispatch
        if ctx.dispatch.id != dispatch.id:
            other_outcomes.append(('dispatch', ctx.dispatch))
    if ctx.contract:
        all_outcomes.append(('contract', ctx.contract))
        other_outcomes.append(('contract', ctx.contract))
    if ctx.reimbursement:
        all_outcomes.append(('reimbursement', ctx.reimbursement))
        other_outcomes.append(('reimbursement', ctx.reimbursement))
    if ctx.reject:
        all_outcomes.append(('reject', ctx.reject))
        other_outcomes.append(('reject', ctx.reject))
    
    # Determine if editing should be disabled
    # Disable if: dispatch is Cancelled AND active outcome is something else
    can_edit = True
    if dispatch.status == 'Cancelled' and ctx.active_outcome:
        # Check if active outcome is not this dispatch
        if ctx.active_outcome_type != 'dispatch' or ctx.active_outcome_id != dispatch.id:
            can_edit = False
    
    return render_template('dispatching/outcomes/dispatches/detail.html', 
                         ctx=ctx, 
                         item=dispatch, 
                         dispatch=dispatch,
                         all_outcomes=all_outcomes,
                         other_outcomes=other_outcomes,
                         can_edit=can_edit)


@dispatching_bp.route('/dispatches/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def dispatches_edit(item_id):
    """Edit dispatch"""
    dispatch = StandardDispatch.query.get_or_404(item_id)
    ctx = DispatchContext.load(dispatch.request_id)
    
    # Check if editing should be disabled
    # Disable if: dispatch is Cancelled AND active outcome is something else
    if dispatch.status == 'Cancelled' and ctx.active_outcome:
        # Check if active outcome is not this dispatch
        if ctx.active_outcome_type != 'dispatch' or ctx.active_outcome_id != dispatch.id:
            flash('Cannot edit this dispatch because it is cancelled and another outcome is active for this request.', 'danger')
            return redirect(url_for('dispatching.dispatches_detail', item_id=dispatch.id))
    
    if request.method == 'POST':
        # Track changes for comment
        changes = []
        
        # Parse datetime fields
        def parse_datetime_local(dt_str):
            if not dt_str:
                return None
            try:
                return datetime.strptime(dt_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                try:
                    return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                except ValueError:
                    return None
        
        # Update fields and track changes
        scheduled_start = parse_datetime_local(request.form.get('scheduled_start'))
        scheduled_end = parse_datetime_local(request.form.get('scheduled_end'))
        actual_start = parse_datetime_local(request.form.get('actual_start'))
        actual_end = parse_datetime_local(request.form.get('actual_end'))
        
        if dispatch.scheduled_start != scheduled_start:
            changes.append(f"scheduled_start: {dispatch.scheduled_start} → {scheduled_start}")
            dispatch.scheduled_start = scheduled_start
        if dispatch.scheduled_end != scheduled_end:
            changes.append(f"scheduled_end: {dispatch.scheduled_end} → {scheduled_end}")
            dispatch.scheduled_end = scheduled_end
        if dispatch.actual_start != actual_start:
            changes.append(f"actual_start: {dispatch.actual_start} → {actual_start}")
            dispatch.actual_start = actual_start
        if dispatch.actual_end != actual_end:
            changes.append(f"actual_end: {dispatch.actual_end} → {actual_end}")
            dispatch.actual_end = actual_end
        
        # Parse numeric fields
        meter_start = float(request.form.get('meter_start')) if request.form.get('meter_start') else None
        meter_end = float(request.form.get('meter_end')) if request.form.get('meter_end') else None
        
        if dispatch.meter_start != meter_start:
            changes.append(f"meter_start: {dispatch.meter_start} → {meter_start}")
            dispatch.meter_start = meter_start
        if dispatch.meter_end != meter_end:
            changes.append(f"meter_end: {dispatch.meter_end} → {meter_end}")
            dispatch.meter_end = meter_end
        
        # Parse IDs
        assigned_by_id = int(request.form.get('assigned_by_id')) if request.form.get('assigned_by_id') else None
        assigned_person_id = int(request.form.get('assigned_person_id')) if request.form.get('assigned_person_id') else None
        asset_dispatched_id = int(request.form.get('asset_dispatched_id')) if request.form.get('asset_dispatched_id') else None
        
        if dispatch.assigned_by_id != assigned_by_id:
            changes.append(f"assigned_by_id: {dispatch.assigned_by_id} → {assigned_by_id}")
            dispatch.assigned_by_id = assigned_by_id
        if dispatch.assigned_person_id != assigned_person_id:
            changes.append(f"assigned_person_id: {dispatch.assigned_person_id} → {assigned_person_id}")
            dispatch.assigned_person_id = assigned_person_id
        if dispatch.asset_dispatched_id != asset_dispatched_id:
            changes.append(f"asset_dispatched_id: {dispatch.asset_dispatched_id} → {asset_dispatched_id}")
            dispatch.asset_dispatched_id = asset_dispatched_id
        
        # String fields
        location_from_id = request.form.get('location_from_id') or None
        location_to_id = request.form.get('location_to_id') or None
        status = request.form.get('status', 'Planned')
        
        if dispatch.location_from_id != location_from_id:
            changes.append(f"location_from_id: {dispatch.location_from_id} → {location_from_id}")
            dispatch.location_from_id = location_from_id
        if dispatch.location_to_id != location_to_id:
            changes.append(f"location_to_id: {dispatch.location_to_id} → {location_to_id}")
            dispatch.location_to_id = location_to_id
        if dispatch.status != status:
            old_status = dispatch.status
            old_request_status = ctx.request.workflow_status
            changes.append(f"status: {old_status} → {status}")
            dispatch.status = status
            
            # Update request status based on dispatch status
            # If dispatch is Complete, set request to Resolved
            # Otherwise, set request to Planned
            if status == 'Complete':
                if old_request_status != 'Resolved':
                    ctx.request.workflow_status = 'Resolved'
                    ctx.request.updated_by_id = current_user.id
                    changes.append(f"request workflow_status: {old_request_status} → Resolved")
            elif old_status == 'Complete' and status != 'Complete':
                # If moving away from Complete, set request back to Planned
                if old_request_status == 'Resolved':
                    ctx.request.workflow_status = 'Planned'
                    ctx.request.updated_by_id = current_user.id
                    changes.append("request workflow_status: Resolved → Planned")
        
        # Boolean field
        conflicts_resolved = request.form.get('conflicts_resolved') == '1'
        if dispatch.conflicts_resolved != conflicts_resolved:
            changes.append(f"conflicts_resolved: {dispatch.conflicts_resolved} → {conflicts_resolved}")
            dispatch.conflicts_resolved = conflicts_resolved
        
        # Validate status against actual dates before committing
        try:
            DispatchStatusValidationPolicy.validate(
                dispatch.status,
                dispatch.actual_start,
                dispatch.actual_end
            )
        except DispatchPolicyViolation as e:
            flash(str(e), 'danger')
            # Rollback changes
            db.session.rollback()
            return redirect(url_for('dispatching.dispatches_edit', item_id=dispatch.id))
        
        # Update audit fields
        dispatch.updated_by_id = current_user.id
        dispatch.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Add comment to event if there were changes
        if changes and ctx.event:
            comment_text = f"Dispatch updated by {current_user.username}. Changes: " + ", ".join(changes)
            ctx.add_comment(current_user.id, comment_text)
        
        flash('Dispatch updated successfully', 'success')
        return redirect(url_for('dispatching.dispatches_detail', item_id=dispatch.id))
    
    # GET request - show form
    users = User.query.filter_by(is_active=True).all()
    assets = Asset.query.limit(100).all()
    
    return render_template('dispatching/outcomes/dispatches/edit.html',
                         ctx=ctx,
                         item=dispatch,
                         dispatch=dispatch,
                         users=users,
                         assets=assets)


@dispatching_bp.route('/dispatches/<int:item_id>/cancel', methods=['POST'])
@login_required
def dispatches_cancel(item_id):
    """Cancel dispatch outcome"""
    dispatch = StandardDispatch.query.get_or_404(item_id)
    ctx = DispatchContext.load(dispatch.request_id)
    
    # Get cancellation reason from form
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Cancellation reason is required', 'danger')
        return redirect(url_for('dispatching.dispatches_edit', item_id=item_id))
    
    # Check if this dispatch is the active outcome
    if ctx.active_outcome_type != 'dispatch' or ctx.active_outcome_id != dispatch.id:
        flash('Cannot cancel: This dispatch is not the active outcome for this request', 'danger')
        return redirect(url_for('dispatching.dispatches_detail', item_id=item_id))
    
    try:
        # Use business layer to cancel the outcome
        ctx.cancel_active_outcome(current_user.id, reason)
        flash('Dispatch outcome cancelled successfully. Request returned to "Under Review" status.', 'success')
        return redirect(url_for('dispatching.requests_detail', item_id=ctx.request_id))
    except Exception as e:
        flash(f'Error cancelling dispatch: {str(e)}', 'danger')
        return redirect(url_for('dispatching.dispatches_detail', item_id=item_id))
