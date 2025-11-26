from flask import render_template, request, redirect, url_for, flash
from datetime import datetime
from flask_login import current_user, login_required
from app.presentation.routes.dispatching import dispatching_bp
from app import db
from app.data.dispatching.request import DispatchRequest
from app.buisness.dispatching.dispatch_manager import DispatchManager
from app.buisness.dispatching.dispatch import DispatchContext
from app.data.core.asset_info.asset_type import AssetType
from app.data.core.major_location import MajorLocation
from app.data.core.asset_info.asset import Asset
from app.data.core.user_info.user import User


@dispatching_bp.route('/')
@login_required
def index():
    """Dispatch console with overview statistics and recent activity"""
    from app.data.dispatching.outcomes.standard_dispatch import StandardDispatch
    from app.data.dispatching.outcomes.contract import Contract
    from app.data.dispatching.outcomes.reimbursement import Reimbursement
    from datetime import datetime, timedelta
    
    # Get statistics
    total_requests = DispatchRequest.query.count()
    pending_requests = DispatchRequest.query.filter_by(status='Draft').count()
    active_requests = DispatchRequest.query.filter(DispatchRequest.status.in_(['Submitted', 'Active'])).count()
    
    total_dispatches = StandardDispatch.query.count()
    active_dispatches = StandardDispatch.query.filter(StandardDispatch.status.in_(['Planned', 'Active', 'Dispatched'])).count()
    upcoming_dispatches = StandardDispatch.query.filter(
        StandardDispatch.scheduled_start >= datetime.utcnow(),
        StandardDispatch.scheduled_start <= datetime.utcnow() + timedelta(days=7)
    ).count()
    
    total_contracts = Contract.query.count()
    total_reimbursements = Reimbursement.query.count()
    
    # Get recent requests
    recent_requests = DispatchRequest.query.order_by(DispatchRequest.created_at.desc()).limit(10).all()
    
    # Get upcoming dispatches
    upcoming = StandardDispatch.query.filter(
        StandardDispatch.scheduled_start >= datetime.utcnow()
    ).order_by(StandardDispatch.scheduled_start.asc()).limit(10).all()
    
    # Get pending requests for queue
    queue_items = DispatchRequest.query.filter_by(status='Draft').order_by(DispatchRequest.created_at.asc()).limit(20).all()
    
    stats = {
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'active_requests': active_requests,
        'total_dispatches': total_dispatches,
        'active_dispatches': active_dispatches,
        'upcoming_dispatches': upcoming_dispatches,
        'total_contracts': total_contracts,
        'total_reimbursements': total_reimbursements
    }
    
    return render_template('dispatching/index.html', 
                         stats=stats,
                         recent_requests=recent_requests,
                         upcoming=upcoming,
                         queue_items=queue_items)


# CRUD: DispatchRequest
@dispatching_bp.route('/requests')
def requests_list():
    requests = DispatchRequest.query.order_by(DispatchRequest.created_at.desc()).all()
    return render_template('dispatching/requests_list.html', requests=requests)


@dispatching_bp.route('/requests/new', methods=['GET', 'POST'])
def requests_new():
    if request.method == 'POST':
        form = request.form

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
        try:
            asset_type_id = int(asset_type_id_raw) if asset_type_id_raw else None
            major_location_id = int(major_location_id_raw) if major_location_id_raw else None
        except ValueError:
            flash('Invalid selection for asset type or location.', 'danger')
            return redirect(url_for('dispatching.requests_new'))

        # Use DispatchManager to create request
        try:
            item = DispatchManager.create_request(
                requester_id=None,
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
                status=form.get('status') or 'Draft',
            )
            db.session.commit()
            flash('Dispatch request created', 'success')
            return redirect(url_for('dispatching.requests_detail', item_id=item.id))
        except Exception as e:
            flash(f'Error creating request: {str(e)}', 'danger')
            return redirect(url_for('dispatching.requests_new'))

    asset_types = AssetType.query.all()
    locations = MajorLocation.query.all()
    return render_template('dispatching/requests_form.html', asset_types=asset_types, locations=locations)


@dispatching_bp.route('/requests/<int:item_id>')
def requests_detail(item_id):
    ctx = DispatchContext.from_request_id(item_id)
    # Get data for outcome forms if no outcome exists
    assets = None
    users = None
    if not ctx.has_outcome:
        # Get assets matching the request's asset type
        if ctx.request.asset_type_id:
            assets = Asset.query.filter(
                Asset.make_model.has(asset_type_id=ctx.request.asset_type_id)
            ).all()
        else:
            assets = Asset.query.limit(100).all()
        users = User.query.filter_by(is_active=True).all()
    return render_template('dispatching/requests_detail.html', 
                         ctx=ctx, 
                         item=ctx.request,
                         assets=assets,
                         users=users)


# CRUD: Dispatch - Access through request context
@dispatching_bp.route('/dispatches')
def dispatches_list():
    from app.data.dispatching.outcomes.standard_dispatch import StandardDispatch
    items = StandardDispatch.query.order_by(StandardDispatch.created_at.desc()).all()
    # Create contexts for each dispatch to access full request data
    contexts = [DispatchContext.from_request_id(d.request_id) for d in items]
    return render_template('dispatching/dispatches_list.html', items=items, contexts=contexts)


@dispatching_bp.route('/dispatches/<int:item_id>')
def dispatches_detail(item_id):
    from app.data.dispatching.outcomes.standard_dispatch import StandardDispatch
    dispatch = StandardDispatch.query.get_or_404(item_id)
    ctx = DispatchContext.from_request_id(dispatch.request_id)
    return render_template('dispatching/dispatches_detail.html', ctx=ctx, item=dispatch, dispatch=dispatch)


# CRUD: Contract
@dispatching_bp.route('/contracts')
def contracts_list():
    from app.data.dispatching.outcomes.contract import Contract
    items = Contract.query.order_by(Contract.created_at.desc()).all()
    contexts = [DispatchContext.from_request_id(c.request_id) for c in items]
    return render_template('dispatching/contracts_list.html', items=items, contexts=contexts)


# CRUD: Reimbursement
@dispatching_bp.route('/reimbursements')
def reimbursements_list():
    from app.data.dispatching.outcomes.reimbursement import Reimbursement
    items = Reimbursement.query.order_by(Reimbursement.created_at.desc()).all()
    contexts = [DispatchContext.from_request_id(r.request_id) for r in items]
    return render_template('dispatching/reimbursements_list.html', items=items, contexts=contexts)


# CRUD: Reject
@dispatching_bp.route('/rejects')
def rejects_list():
    from app.data.dispatching.outcomes.reject import Reject
    items = Reject.query.order_by(Reject.created_at.desc()).all()
    contexts = [DispatchContext.from_request_id(r.request_id) for r in items]
    return render_template('dispatching/rejects_list.html', items=items, contexts=contexts)


# Outcome Management
@dispatching_bp.route('/requests/<int:request_id>/outcome/<outcome_type>', methods=['GET', 'POST'])
def outcome_create(request_id, outcome_type):
    """Create an outcome for a dispatch request"""
    ctx = DispatchContext.from_request_id(request_id)
    
    # Validate outcome type
    if outcome_type not in ['dispatch', 'contract', 'reimbursement', 'reject']:
        flash('Invalid outcome type', 'danger')
        return redirect(url_for('dispatching.requests_detail', item_id=request_id))
    
    # Check if outcome already exists
    is_valid, error_msg = ctx.validate_outcome_creation(outcome_type)
    if not is_valid:
        flash(error_msg, 'danger')
        return redirect(url_for('dispatching.requests_detail', item_id=request_id))
    
    if request.method == 'POST':
        try:
            form = request.form
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
                
                # Parse conflicts_resolved
                conflicts_resolved = form.get('conflicts_resolved') == '1'
                
                dispatch = ctx.create_dispatch_outcome(
                    assigned_by_id=assigned_by_id,
                    created_by_id=created_by_id,
                    scheduled_start=scheduled_start,
                    scheduled_end=scheduled_end,
                    actual_start=actual_start,
                    actual_end=actual_end,
                    meter_start=meter_start,
                    meter_end=meter_end,
                    location_from_id=form.get('location_from_id') or None,
                    location_to_id=form.get('location_to_id') or None,
                    status=form.get('status', 'Planned'),
                    conflicts_resolved=conflicts_resolved
                )
                flash('Dispatch outcome created successfully', 'success')
                return redirect(url_for('dispatching.dispatches_detail', item_id=dispatch.id))
                
            elif outcome_type == 'contract':
                cost_amount = float(form.get('cost_amount')) if form.get('cost_amount') else None
                contract = ctx.create_contract_outcome(
                    created_by_id=created_by_id,
                    company_name=form.get('company_name'),
                    cost_currency=form.get('cost_currency'),
                    cost_amount=cost_amount,
                    contract_reference=form.get('contract_reference') or None,
                    notes=form.get('notes') or None
                )
                flash('Contract outcome created successfully', 'success')
                return redirect(url_for('dispatching.requests_detail', item_id=request_id))
                
            elif outcome_type == 'reimbursement':
                amount = float(form.get('amount')) if form.get('amount') else None
                reimbursement = ctx.create_reimbursement_outcome(
                    created_by_id=created_by_id,
                    from_account=form.get('from_account'),
                    to_account=form.get('to_account'),
                    amount=amount,
                    reason=form.get('reason'),
                    policy_reference=form.get('policy_reference') or None
                )
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
                
                reject = ctx.create_reject_outcome(
                    created_by_id=created_by_id,
                    reason=form.get('reason'),
                    rejection_category=form.get('rejection_category') or None,
                    notes=form.get('notes') or None,
                    alternative_suggestion=form.get('alternative_suggestion') or None,
                    can_resubmit=can_resubmit,
                    resubmit_after=resubmit_after
                )
                flash('Request rejected successfully', 'success')
                return redirect(url_for('dispatching.requests_detail', item_id=request_id))
                
        except Exception as e:
            flash(f'Error creating outcome: {str(e)}', 'danger')
            return redirect(url_for('dispatching.requests_detail', item_id=request_id))
    
    # GET request - show form
    # Get data for forms
    assets = None
    users = None
    if outcome_type == 'dispatch':
        # Get assets matching the request's asset type
        if ctx.request.asset_type_id:
            assets = Asset.query.filter(
                Asset.make_model.has(asset_type_id=ctx.request.asset_type_id)
            ).all()
        else:
            assets = Asset.query.limit(100).all()
        users = User.query.filter_by(is_active=True).all()
    
    return render_template(f'dispatching/outcomes/{outcome_type}_form.html',
                         request_id=request_id,
                         request=ctx.request,
                         assets=assets or [],
                         users=users or [])



