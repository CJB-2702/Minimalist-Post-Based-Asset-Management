"""
Navigation and portal routes for dispatching module
"""

from flask import render_template
from datetime import datetime, timedelta
from flask_login import login_required
from app.presentation.routes.dispatching import dispatching_bp
from app.data.dispatching.request import DispatchRequest


@dispatching_bp.route('/')
@login_required
def index():
    """Dispatching module landing page with links to dispatcher and user portals"""
    return render_template('dispatching/navigation/index.html')


@dispatching_bp.route('/user-portal')
@login_required
def user_portal():
    """User portal for viewing assigned vehicles and work assignments"""
    from flask import request
    from flask_login import current_user
    from app.data.core.asset_info.asset_type import AssetType
    from app.buisness.dispatching.context import DispatchContext
    from app import db
    
    # Extract filter parameters
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status = request.args.get('status')
    asset_type_id = request.args.get('asset_type_id', type=int)
    dispatch_scope = request.args.get('dispatch_scope')
    outcome_type = request.args.get('outcome_type')
    search = request.args.get('search')
    
    # Build query for requests assigned to current user
    query = DispatchRequest.query.filter_by(requested_for=current_user.id)
    
    # Apply filters
    if status:
        query = query.filter(DispatchRequest.status == status)
    
    if asset_type_id:
        query = query.filter(DispatchRequest.asset_type_id == asset_type_id)
    
    if dispatch_scope:
        query = query.filter(DispatchRequest.dispatch_scope == dispatch_scope)
    
    if outcome_type:
        if outcome_type == 'none':
            query = query.filter(DispatchRequest.active_outcome_type.is_(None))
        else:
            query = query.filter(DispatchRequest.active_outcome_type == outcome_type)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                DispatchRequest.notes.ilike(search_term),
                DispatchRequest.activity_location.ilike(search_term),
                DispatchRequest.names_freeform.ilike(search_term),
                DispatchRequest.asset_subclass_text.ilike(search_term)
            )
        )
    
    # Order by desired_start (newest first)
    query = query.order_by(DispatchRequest.desired_start.desc())
    
    # Paginate
    requests_page = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Load contexts with outcomes for each request
    contexts = []
    for req in requests_page.items:
        ctx = DispatchContext.from_request(req)
        contexts.append(ctx)
    
    # Get filter options
    statuses = db.session.query(DispatchRequest.status).filter_by(requested_for=current_user.id).distinct().all()
    statuses = [s[0] for s in statuses if s[0]]
    
    scopes = db.session.query(DispatchRequest.dispatch_scope).filter_by(requested_for=current_user.id).distinct().all()
    scopes = [s[0] for s in scopes if s[0]]
    
    outcome_types = db.session.query(DispatchRequest.active_outcome_type).filter_by(requested_for=current_user.id).distinct().all()
    outcome_types = [o[0] for o in outcome_types if o[0]]
    
    asset_types = AssetType.query.filter_by(is_active=True).order_by(AssetType.name).all()
    
    filter_options = {
        'statuses': statuses,
        'scopes': scopes,
        'outcome_types': outcome_types,
        'asset_types': asset_types,
    }
    
    return render_template('dispatching/navigation/user_portal.html',
                         contexts=contexts,
                         requests_page=requests_page,
                         filter_options=filter_options)


@dispatching_bp.route('/dispatcher-portal')
@login_required
def dispatcher_portal():
    """Dispatch console with overview statistics and recent activity"""
    from app.data.dispatching.outcomes.standard_dispatch import StandardDispatch
    from app.data.dispatching.outcomes.contract import Contract
    from app.data.dispatching.outcomes.reimbursement import Reimbursement
    
    # Get statistics
    total_requests = len(DispatchRequest.query.all())
    pending_requests = len(DispatchRequest.query.filter_by(workflow_status='Requested').all())
    active_requests = len(DispatchRequest.query.filter(DispatchRequest.workflow_status.in_(['Submitted', 'UnderReview', 'Planned'])).all())
    
    total_dispatches = len(StandardDispatch.query.all())
    active_dispatches = len(StandardDispatch.query.filter(StandardDispatch.status.in_(['Planned', 'Active', 'Dispatched'])).all())
    upcoming_dispatches = len(StandardDispatch.query.filter(
        StandardDispatch.scheduled_start >= datetime.utcnow(),
        StandardDispatch.scheduled_start <= datetime.utcnow() + timedelta(days=7)
    ).all())
    
    total_contracts = len(Contract.query.all())
    total_reimbursements = len(Reimbursement.query.all())
    
    # Get recent requests
    recent_requests = DispatchRequest.query.order_by(DispatchRequest.created_at.desc()).limit(10).all()
    
    # Get upcoming dispatches
    upcoming = StandardDispatch.query.filter(
        StandardDispatch.scheduled_start >= datetime.utcnow()
    ).order_by(StandardDispatch.scheduled_start.asc()).limit(10).all()
    
    # Get pending requests for queue (Requested = waiting for initial review)
    queue_items = DispatchRequest.query.filter_by(workflow_status='Requested').order_by(DispatchRequest.created_at.asc()).limit(20).all()
    
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
    
    return render_template('dispatching/navigation/dispatcher_portal.html', 
                         stats=stats,
                         recent_requests=recent_requests,
                         upcoming=upcoming,
                         queue_items=queue_items)
