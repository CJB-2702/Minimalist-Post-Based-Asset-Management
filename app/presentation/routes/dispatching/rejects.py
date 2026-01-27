"""
Reject outcome CRUD routes for dispatching module
"""

from flask import render_template, request, redirect, url_for, flash
from datetime import datetime
from flask_login import current_user, login_required
from app.presentation.routes.dispatching import dispatching_bp
from app import db
from app.data.dispatching.outcomes.reject import Reject
from app.buisness.dispatching.context import DispatchContext
from app.services.dispatching.reject_service import RejectService


@dispatching_bp.route('/rejects')
def rejects_list():
    """List all rejected requests with filtering and pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Use service to get list data with filters
    rejects_page, filter_options = RejectService.get_list_data(
        request=request,
        page=page,
        per_page=per_page
    )
    
    contexts = [DispatchContext.load(r.request_id) for r in rejects_page.items]
    
    return render_template('dispatching/outcomes/rejects/list.html', 
                         items=rejects_page,
                         contexts=contexts,
                         filter_options=filter_options)


@dispatching_bp.route('/rejects/<int:item_id>')
@dispatching_bp.route('/rejects/<int:item_id>/view')
@login_required
def rejects_detail(item_id):
    """View rejection details"""
    reject = Reject.query.get_or_404(item_id)
    ctx = DispatchContext.load(reject.request_id)
    
    return render_template('dispatching/outcomes/rejects/detail.html',
                         ctx=ctx,
                         item=reject,
                         reject=reject)


@dispatching_bp.route('/rejects/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def rejects_edit(item_id):
    """Edit rejection"""
    reject = Reject.query.get_or_404(item_id)
    ctx = DispatchContext.load(reject.request_id)
    
    if request.method == 'POST':
        # Track changes for comment
        changes = []
        
        # Update fields and track changes
        reason = request.form.get('reason')
        rejection_category = request.form.get('rejection_category') or None
        notes = request.form.get('notes') or None
        alternative_suggestion = request.form.get('alternative_suggestion') or None
        can_resubmit = request.form.get('can_resubmit') == '1'
        
        # Parse resubmit_after datetime if provided
        resubmit_after_str = request.form.get('resubmit_after')
        resubmit_after = None
        if resubmit_after_str:
            try:
                resubmit_after = datetime.strptime(resubmit_after_str, '%Y-%m-%d')
            except ValueError:
                pass
        
        if reject.reason != reason:
            changes.append(f"reason updated")
            reject.reason = reason
        if reject.rejection_category != rejection_category:
            changes.append(f"rejection_category: '{reject.rejection_category}' → '{rejection_category}'")
            reject.rejection_category = rejection_category
        if reject.notes != notes:
            changes.append(f"notes updated")
            reject.notes = notes
        if reject.alternative_suggestion != alternative_suggestion:
            changes.append(f"alternative_suggestion updated")
            reject.alternative_suggestion = alternative_suggestion
        if reject.can_resubmit != can_resubmit:
            changes.append(f"can_resubmit: {reject.can_resubmit} → {can_resubmit}")
            reject.can_resubmit = can_resubmit
        if reject.resubmit_after != resubmit_after:
            changes.append(f"resubmit_after: {reject.resubmit_after} → {resubmit_after}")
            reject.resubmit_after = resubmit_after
        
        # Update audit fields
        reject.updated_by_id = current_user.id
        reject.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Add comment to event if there were changes
        if changes and ctx.event:
            comment_text = f"Rejection updated by {current_user.username}. Changes: " + ", ".join(changes)
            ctx.add_comment(current_user.id, comment_text)
        
        flash('Rejection updated successfully', 'success')
        return redirect(url_for('dispatching.rejects_detail', item_id=reject.id))
    
    return render_template('dispatching/outcomes/rejects/edit.html',
                         ctx=ctx,
                         item=reject,
                         reject=reject)


@dispatching_bp.route('/rejects/<int:item_id>/cancel', methods=['POST'])
@login_required
def rejects_cancel(item_id):
    """Cancel rejection outcome"""
    reject = Reject.query.get_or_404(item_id)
    ctx = DispatchContext.load(reject.request_id)
    
    # Get cancellation reason from form
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Cancellation reason is required', 'danger')
        return redirect(url_for('dispatching.rejects_edit', item_id=item_id))
    
    # Check if this reject is the active outcome
    if ctx.active_outcome_type != 'reject' or ctx.active_outcome_id != reject.id:
        flash('Cannot cancel: This rejection is not the active outcome for this request', 'danger')
        return redirect(url_for('dispatching.rejects_detail', item_id=item_id))
    
    try:
        # Use business layer to cancel the outcome
        ctx.cancel_active_outcome(current_user.id, reason)
        flash('Rejection outcome cancelled successfully. Request returned to "Under Review" status.', 'success')
        return redirect(url_for('dispatching.requests_detail', item_id=ctx.request_id))
    except Exception as e:
        flash(f'Error cancelling rejection: {str(e)}', 'danger')
        return redirect(url_for('dispatching.rejects_detail', item_id=item_id))
