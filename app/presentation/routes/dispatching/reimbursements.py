"""
Reimbursement outcome CRUD routes for dispatching module
"""

from flask import render_template, request, redirect, url_for, flash
from datetime import datetime
from flask_login import current_user, login_required
from app.presentation.routes.dispatching import dispatching_bp
from app import db
from app.data.dispatching.outcomes.reimbursement import Reimbursement
from app.buisness.dispatching.context import DispatchContext
from app.services.dispatching.reimbursement_service import ReimbursementService


@dispatching_bp.route('/reimbursements')
def reimbursements_list():
    """List all reimbursements with filtering and pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Use service to get list data with filters
    reimbursements_page, filter_options = ReimbursementService.get_list_data(
        request=request,
        page=page,
        per_page=per_page
    )
    
    contexts = [DispatchContext.load(r.request_id) for r in reimbursements_page.items]
    
    return render_template('dispatching/outcomes/reimbursements/list.html', 
                         items=reimbursements_page,
                         contexts=contexts,
                         filter_options=filter_options)


@dispatching_bp.route('/reimbursements/<int:item_id>')
@dispatching_bp.route('/reimbursements/<int:item_id>/view')
@login_required
def reimbursements_detail(item_id):
    """View reimbursement details"""
    reimbursement = Reimbursement.query.get_or_404(item_id)
    ctx = DispatchContext.load(reimbursement.request_id)
    
    return render_template('dispatching/outcomes/reimbursements/detail.html',
                         ctx=ctx,
                         item=reimbursement,
                         reimbursement=reimbursement)


@dispatching_bp.route('/reimbursements/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def reimbursements_edit(item_id):
    """Edit reimbursement"""
    reimbursement = Reimbursement.query.get_or_404(item_id)
    ctx = DispatchContext.load(reimbursement.request_id)
    
    if request.method == 'POST':
        # Track changes for comment
        changes = []
        
        # Update fields and track changes
        from_account = request.form.get('from_account')
        to_account = request.form.get('to_account')
        amount = float(request.form.get('amount')) if request.form.get('amount') else None
        reason = request.form.get('reason')
        policy_reference = request.form.get('policy_reference') or None
        
        if reimbursement.from_account != from_account:
            changes.append(f"from_account: '{reimbursement.from_account}' → '{from_account}'")
            reimbursement.from_account = from_account
        if reimbursement.to_account != to_account:
            changes.append(f"to_account: '{reimbursement.to_account}' → '{to_account}'")
            reimbursement.to_account = to_account
        if reimbursement.amount != amount:
            changes.append(f"amount: {reimbursement.amount} → {amount}")
            reimbursement.amount = amount
        if reimbursement.reason != reason:
            changes.append("reason updated")
            reimbursement.reason = reason
        if reimbursement.policy_reference != policy_reference:
            changes.append(f"policy_reference: '{reimbursement.policy_reference}' → '{policy_reference}'")
            reimbursement.policy_reference = policy_reference
        
        # Update audit fields
        reimbursement.updated_by_id = current_user.id
        reimbursement.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Add comment to event if there were changes
        if changes and ctx.event:
            comment_text = f"Reimbursement updated by {current_user.username}. Changes: " + ", ".join(changes)
            ctx.add_comment(current_user.id, comment_text)
        
        flash('Reimbursement updated successfully', 'success')
        return redirect(url_for('dispatching.reimbursements_detail', item_id=reimbursement.id))
    
    return render_template('dispatching/outcomes/reimbursements/edit.html',
                         ctx=ctx,
                         item=reimbursement,
                         reimbursement=reimbursement)


@dispatching_bp.route('/reimbursements/<int:item_id>/cancel', methods=['POST'])
@login_required
def reimbursements_cancel(item_id):
    """Cancel reimbursement outcome"""
    reimbursement = Reimbursement.query.get_or_404(item_id)
    ctx = DispatchContext.load(reimbursement.request_id)
    
    # Get cancellation reason from form
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Cancellation reason is required', 'danger')
        return redirect(url_for('dispatching.reimbursements_edit', item_id=item_id))
    
    # Check if this reimbursement is the active outcome
    if ctx.active_outcome_type != 'reimbursement' or ctx.active_outcome_id != reimbursement.id:
        flash('Cannot cancel: This reimbursement is not the active outcome for this request', 'danger')
        return redirect(url_for('dispatching.reimbursements_detail', item_id=item_id))
    
    try:
        # Use business layer to cancel the outcome
        ctx.cancel_active_outcome(current_user.id, reason)
        flash('Reimbursement outcome cancelled successfully. Request returned to "Under Review" status.', 'success')
        return redirect(url_for('dispatching.requests_detail', item_id=ctx.request_id))
    except Exception as e:
        flash(f'Error cancelling reimbursement: {str(e)}', 'danger')
        return redirect(url_for('dispatching.reimbursements_detail', item_id=item_id))
