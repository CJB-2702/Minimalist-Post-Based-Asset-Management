"""
Outcome creation and card rendering routes for dispatching module
"""

from flask import render_template, request, redirect, url_for, flash
from datetime import datetime
from flask_login import current_user, login_required
from app.presentation.routes.dispatching import dispatching_bp
from app.buisness.dispatching.context import DispatchContext
from app.buisness.dispatching.policies.dispatch_status_validation import DispatchStatusValidationPolicy
from app.buisness.dispatching.errors import DispatchPolicyViolation
from app.data.core.asset_info.asset_type import AssetType
from app.data.core.major_location import MajorLocation
from app.data.core.asset_info.asset import Asset
from app.data.core.user_info.user import User


def _get_outcome_plural(outcome_type):
    """Get the proper plural form for outcome type (for template paths)"""
    plurals = {
        'dispatch': 'dispatches',
        'contract': 'contracts',
        'reimbursement': 'reimbursements',
        'reject': 'rejects'
    }
    return plurals.get(outcome_type, f'{outcome_type}s')


# Outcome Creation
@dispatching_bp.route('/requests/<int:request_id>/outcome/<outcome_type>', methods=['GET', 'POST'])
def outcome_create(request_id, outcome_type):
    """Create an outcome for a dispatch request"""
    ctx = DispatchContext.load(request_id)
    
    # Validate outcome type
    if outcome_type not in ['dispatch', 'contract', 'reimbursement', 'reject']:
        flash('Invalid outcome type', 'danger')
        return redirect(url_for('dispatching.requests_detail', item_id=request_id))
    
    # Check if active outcome already exists
    if ctx.has_active_outcome:
        flash('An active outcome already exists for this request. Cancel it first before creating a new one.', 'danger')
        return redirect(url_for('dispatching.requests_detail', item_id=request_id))
    
    if request.method == 'POST':
        try:
            form = request.form
            # Get created_by_id from form (allows override) or default to current user
            created_by_id = form.get('created_by_id')
            if created_by_id:
                created_by_id = int(created_by_id)
            else:
                created_by_id = current_user.id if current_user.is_authenticated else None
            
            if outcome_type == 'dispatch':
                # Parse datetime fields (datetime-local format: YYYY-MM-DDTHH:MM)
                def parse_datetime_local(dt_str):
                    if not dt_str:
                        return None
                    try:
                        # datetime-local format: YYYY-MM-DDTHH:MM
                        return datetime.strptime(dt_str, '%Y-%m-%dT%H:%M')
                    except ValueError:
                        # Try ISO format as fallback
                        try:
                            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                        except ValueError:
                            return None
                
                scheduled_start = parse_datetime_local(form.get('scheduled_start'))
                scheduled_end = parse_datetime_local(form.get('scheduled_end'))
                actual_start = parse_datetime_local(form.get('actual_start'))
                actual_end = parse_datetime_local(form.get('actual_end'))
                
                # Parse numeric fields
                meter_start = float(form.get('meter_start')) if form.get('meter_start') else None
                meter_end = float(form.get('meter_end')) if form.get('meter_end') else None
                
                # Parse assigned_by_id
                assigned_by_id = int(form.get('assigned_by_id')) if form.get('assigned_by_id') else None
                
                # Parse assigned_person_id
                assigned_person_id = int(form.get('assigned_person_id')) if form.get('assigned_person_id') else None
                
                # Parse asset_dispatched_id
                asset_dispatched_id = int(form.get('asset_dispatched_id')) if form.get('asset_dispatched_id') else None
                
                # Parse conflicts_resolved
                conflicts_resolved = form.get('conflicts_resolved') == '1'
                
                # Get status
                status = form.get('status', 'Planned')
                
                # Validate status against actual dates
                try:
                    DispatchStatusValidationPolicy.validate(status, actual_start, actual_end)
                except DispatchPolicyViolation as e:
                    flash(str(e), 'danger')
                    return redirect(url_for('dispatching.outcome_create', 
                                          request_id=request_id, 
                                          outcome_type='dispatch'))
                
                # Build payload for assign_outcome
                # Note: created_by_id is handled by the handler via actor_id parameter
                payload = {
                    'assigned_by_id': assigned_by_id,
                    'assigned_person_id': assigned_person_id,
                    'asset_dispatched_id': asset_dispatched_id,
                    'scheduled_start': scheduled_start,
                    'scheduled_end': scheduled_end,
                    'actual_start': actual_start,
                    'actual_end': actual_end,
                    'meter_start': meter_start,
                    'meter_end': meter_end,
                    'location_from_id': form.get('location_from_id') or None,
                    'location_to_id': form.get('location_to_id') or None,
                    'status': status,
                    'conflicts_resolved': conflicts_resolved
                }
                
                ctx.assign_outcome(created_by_id, 'dispatch', payload)
                # Refresh context to get the newly created dispatch
                ctx._build()
                flash('Dispatch outcome created successfully', 'success')
                return redirect(url_for('dispatching.dispatches_detail', item_id=ctx.dispatch.id))
                
            elif outcome_type == 'contract':
                cost_amount = float(form.get('cost_amount')) if form.get('cost_amount') else None
                # Note: created_by_id is handled by the handler via actor_id parameter
                payload = {
                    'company_name': form.get('company_name'),
                    'cost_currency': form.get('cost_currency'),
                    'cost_amount': cost_amount,
                    'contract_reference': form.get('contract_reference') or None,
                    'notes': form.get('notes') or None
                }
                ctx.assign_outcome(created_by_id, 'contract', payload)
                flash('Contract outcome created successfully', 'success')
                return redirect(url_for('dispatching.requests_detail', item_id=request_id))
                
            elif outcome_type == 'reimbursement':
                amount = float(form.get('amount')) if form.get('amount') else None
                # Note: created_by_id is handled by the handler via actor_id parameter
                payload = {
                    'from_account': form.get('from_account'),
                    'to_account': form.get('to_account'),
                    'amount': amount,
                    'reason': form.get('reason'),
                    'policy_reference': form.get('policy_reference') or None
                }
                ctx.assign_outcome(created_by_id, 'reimbursement', payload)
                flash('Reimbursement outcome created successfully', 'success')
                return redirect(url_for('dispatching.requests_detail', item_id=request_id))
                
            elif outcome_type == 'reject':
                # Parse resubmit_after datetime if provided
                resubmit_after_str = form.get('resubmit_after')
                resubmit_after = None
                if resubmit_after_str:
                    try:
                        resubmit_after = datetime.strptime(resubmit_after_str, '%Y-%m-%d')
                    except ValueError:
                        pass
                
                can_resubmit = form.get('can_resubmit') == '1'
                
                # Note: created_by_id is handled by the handler via actor_id parameter
                payload = {
                    'reason': form.get('reason'),
                    'rejection_category': form.get('rejection_category') or None,
                    'notes': form.get('notes') or None,
                    'alternative_suggestion': form.get('alternative_suggestion') or None,
                    'can_resubmit': can_resubmit,
                    'resubmit_after': resubmit_after
                }
                ctx.assign_outcome(created_by_id, 'reject', payload)
                flash('Request rejected successfully', 'success')
                return redirect(url_for('dispatching.requests_detail', item_id=request_id))
                
        except Exception as e:
            flash(f'Error creating outcome: {str(e)}', 'danger')
            return redirect(url_for('dispatching.requests_detail', item_id=request_id))
    
    # GET request - show form
    # Get data for forms
    assets = None
    users = None
    default_scheduled_start = None
    default_scheduled_end = None
    default_assigned_by_id = None
    default_assigned_person_id = None
    
    if outcome_type == 'dispatch':
        # Get assets matching the request's asset type
        if ctx.request.asset_type_id:
            assets = Asset.query.filter(
                Asset.make_model.has(asset_type_id=ctx.request.asset_type_id)
            ).all()
        else:
            assets = Asset.query.limit(100).all()
        users = User.query.filter_by(is_active=True).all()
        
        # Pre-fill from request data
        if ctx.request.desired_start:
            # Format datetime for datetime-local input (YYYY-MM-DDTHH:MM)
            default_scheduled_start = ctx.request.desired_start.strftime('%Y-%m-%dT%H:%M')
        if ctx.request.desired_end:
            default_scheduled_end = ctx.request.desired_end.strftime('%Y-%m-%dT%H:%M')
        
        # Default assigned_by to current user
        if current_user.is_authenticated:
            default_assigned_by_id = current_user.id
        
        # Default assigned person to the person the request is for
        if ctx.request.requested_for:
            default_assigned_person_id = ctx.request.requested_for
    
    outcome_plural = _get_outcome_plural(outcome_type)
    return render_template(f'dispatching/outcomes/{outcome_plural}/form.html',
                         request_id=request_id,
                         request=ctx.request,
                         assets=assets or [],
                         users=users or [],
                         default_scheduled_start=default_scheduled_start,
                         default_scheduled_end=default_scheduled_end,
                         default_assigned_by_id=default_assigned_by_id,
                         default_assigned_person_id=default_assigned_person_id)


# Card rendering routes for sub-rendering
@dispatching_bp.route('/requests/<int:request_id>/card/request')
def request_card(request_id):
    """Render request card"""
    ctx = DispatchContext.load(request_id)
    return render_template('dispatching/outcomes/request_card.html', request=ctx.request)


@dispatching_bp.route('/outcomes/dispatch/<int:dispatch_id>/card')
def dispatch_card(dispatch_id):
    """Render dispatch outcome card"""
    from app.data.dispatching.outcomes.standard_dispatch import StandardDispatch
    dispatch = StandardDispatch.query.get_or_404(dispatch_id)
    return render_template('dispatching/outcomes/dispatch_card.html', dispatch=dispatch)


@dispatching_bp.route('/outcomes/contract/<int:contract_id>/card')
def contract_card(contract_id):
    """Render contract outcome card"""
    from app.data.dispatching.outcomes.contract import Contract
    contract = Contract.query.get_or_404(contract_id)
    return render_template('dispatching/outcomes/contract_card.html', contract=contract)


@dispatching_bp.route('/outcomes/reimbursement/<int:reimbursement_id>/card')
def reimbursement_card(reimbursement_id):
    """Render reimbursement outcome card"""
    from app.data.dispatching.outcomes.reimbursement import Reimbursement
    reimbursement = Reimbursement.query.get_or_404(reimbursement_id)
    return render_template('dispatching/outcomes/reimbursement_card.html', reimbursement=reimbursement)


@dispatching_bp.route('/outcomes/reject/<int:reject_id>/card')
def reject_card(reject_id):
    """Render reject outcome card"""
    from app.data.dispatching.outcomes.reject import Reject
    reject = Reject.query.get_or_404(reject_id)
    return render_template('dispatching/outcomes/reject_card.html', reject=reject)


@dispatching_bp.route('/requests/<int:request_id>/visual-dispatch-selector')
@login_required
def visual_dispatch_selector(request_id):
    """Visual dispatch selector - WIP/Stub page for timeline/calendar view"""
    ctx = DispatchContext.load(request_id)
    return render_template('dispatching/visual_dispatch_selector_stub.html',
                         request_id=request_id,
                         request=ctx.request)


@dispatching_bp.route('/requests/<int:request_id>/outcome/dispatch/asset-select-card')
@login_required
def asset_select_card(request_id):
    """HTMX endpoint to return asset selection card with filters and asset list"""
    from app.services.core.asset_service import AssetService
    
    ctx = DispatchContext.load(request_id)
    
    # Get filter parameters from request
    asset_type_id = request.args.get('asset_type_id', type=int)
    location_id = request.args.get('location_id', type=int)
    make_model_id = request.args.get('make_model_id', type=int)
    status = request.args.get('status', type=str)
    serial_number = request.args.get('serial_number', type=str)
    name = request.args.get('name', type=str)
    
    # Get availability filter parameters
    availability_mode = request.args.get('availability_mode', default='no_planned', type=str)
    
    # Parse availability time range (defaults to request's desired dates)
    availability_start = None
    availability_end = None
    availability_start_str = request.args.get('availability_start')
    availability_end_str = request.args.get('availability_end')
    
    if availability_start_str:
        try:
            availability_start = datetime.fromisoformat(availability_start_str)
        except (ValueError, TypeError):
            availability_start = ctx.request.desired_start
    else:
        availability_start = ctx.request.desired_start
    
    if availability_end_str:
        try:
            availability_end = datetime.fromisoformat(availability_end_str)
        except (ValueError, TypeError):
            availability_end = ctx.request.desired_end
    else:
        availability_end = ctx.request.desired_end
    
    # Build filtered query using AssetService
    # Only pass asset_type_id if explicitly provided, otherwise let it default from request
    filter_asset_type_id = asset_type_id if asset_type_id else (ctx.request.asset_type_id if ctx.request.asset_type_id else None)
    
    query = AssetService.build_filtered_query(
        asset_type_id=filter_asset_type_id,
        location_id=location_id,
        make_model_id=make_model_id,
        status=status,
        serial_number=serial_number,
        name=name,
        availability_mode=availability_mode,
        availability_start=availability_start,
        availability_end=availability_end
    )
    
    # Get assets (limit to 50 for the selection card)
    assets = query.limit(50).all()
    
    # Get filter options
    asset_types = AssetType.query.filter_by(is_active=True).all()
    locations = MajorLocation.query.all()
    make_models = []
    if asset_type_id or ctx.request.asset_type_id:
        from app.data.core.asset_info.make_model import MakeModel
        make_models = MakeModel.query.filter_by(
            asset_type_id=asset_type_id or ctx.request.asset_type_id
        ).all()
    
    return render_template('dispatching/outcomes/asset_select_card.html',
                         request_id=request_id,
                         request=ctx.request,
                         assets=assets,
                         asset_types=asset_types,
                         locations=locations,
                         make_models=make_models,
                         current_filters={
                             'asset_type_id': asset_type_id or ctx.request.asset_type_id,
                             'location_id': location_id,
                             'make_model_id': make_model_id,
                             'status': status,
                             'serial_number': serial_number,
                             'name': name,
                             'availability_mode': availability_mode,
                             'availability_start': availability_start,
                             'availability_end': availability_end
                         })
