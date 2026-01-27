"""
Contract outcome CRUD routes for dispatching module
"""

from flask import render_template, request, redirect, url_for, flash
from datetime import datetime
from flask_login import current_user, login_required
from app.presentation.routes.dispatching import dispatching_bp
from app import db
from app.data.dispatching.outcomes.contract import Contract
from app.buisness.dispatching.context import DispatchContext
from app.services.dispatching.contract_service import ContractService


@dispatching_bp.route('/contracts')
def contracts_list():
    """List all contracts with filtering and pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Use service to get list data with filters
    contracts_page, filter_options = ContractService.get_list_data(
        request=request,
        page=page,
        per_page=per_page
    )
    
    contexts = [DispatchContext.load(c.request_id) for c in contracts_page.items]
    
    return render_template('dispatching/outcomes/contracts/list.html', 
                         items=contracts_page,
                         contexts=contexts,
                         filter_options=filter_options)


@dispatching_bp.route('/contracts/<int:item_id>')
@dispatching_bp.route('/contracts/<int:item_id>/view')
@login_required
def contracts_detail(item_id):
    """View contract details"""
    contract = Contract.query.get_or_404(item_id)
    ctx = DispatchContext.load(contract.request_id)
    
    return render_template('dispatching/outcomes/contracts/detail.html',
                         ctx=ctx,
                         item=contract,
                         contract=contract)


@dispatching_bp.route('/contracts/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def contracts_edit(item_id):
    """Edit contract"""
    contract = Contract.query.get_or_404(item_id)
    ctx = DispatchContext.load(contract.request_id)
    
    if request.method == 'POST':
        # Track changes for comment
        changes = []
        
        # Update fields and track changes
        company_name = request.form.get('company_name')
        cost_currency = request.form.get('cost_currency')
        cost_amount = float(request.form.get('cost_amount')) if request.form.get('cost_amount') else None
        contract_reference = request.form.get('contract_reference') or None
        notes = request.form.get('notes') or None
        
        if contract.company_name != company_name:
            changes.append(f"company_name: '{contract.company_name}' → '{company_name}'")
            contract.company_name = company_name
        if contract.cost_currency != cost_currency:
            changes.append(f"cost_currency: '{contract.cost_currency}' → '{cost_currency}'")
            contract.cost_currency = cost_currency
        if contract.cost_amount != cost_amount:
            changes.append(f"cost_amount: {contract.cost_amount} → {cost_amount}")
            contract.cost_amount = cost_amount
        if contract.contract_reference != contract_reference:
            changes.append(f"contract_reference: '{contract.contract_reference}' → '{contract_reference}'")
            contract.contract_reference = contract_reference
        if contract.notes != notes:
            changes.append("notes updated")
            contract.notes = notes
        
        # Update audit fields
        contract.updated_by_id = current_user.id
        contract.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Add comment to event if there were changes
        if changes and ctx.event:
            comment_text = f"Contract updated by {current_user.username}. Changes: " + ", ".join(changes)
            ctx.add_comment(current_user.id, comment_text)
        
        flash('Contract updated successfully', 'success')
        return redirect(url_for('dispatching.contracts_detail', item_id=contract.id))
    
    return render_template('dispatching/outcomes/contracts/edit.html',
                         ctx=ctx,
                         item=contract,
                         contract=contract)


@dispatching_bp.route('/contracts/<int:item_id>/cancel', methods=['POST'])
@login_required
def contracts_cancel(item_id):
    """Cancel contract outcome"""
    contract = Contract.query.get_or_404(item_id)
    ctx = DispatchContext.load(contract.request_id)
    
    # Get cancellation reason from form
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Cancellation reason is required', 'danger')
        return redirect(url_for('dispatching.contracts_edit', item_id=item_id))
    
    # Check if this contract is the active outcome
    if ctx.active_outcome_type != 'contract' or ctx.active_outcome_id != contract.id:
        flash('Cannot cancel: This contract is not the active outcome for this request', 'danger')
        return redirect(url_for('dispatching.contracts_detail', item_id=item_id))
    
    try:
        # Use business layer to cancel the outcome
        ctx.cancel_active_outcome(current_user.id, reason)
        flash('Contract outcome cancelled successfully. Request returned to "Under Review" status.', 'success')
        return redirect(url_for('dispatching.requests_detail', item_id=ctx.request_id))
    except Exception as e:
        flash(f'Error cancelling contract: {str(e)}', 'danger')
        return redirect(url_for('dispatching.contracts_detail', item_id=item_id))
