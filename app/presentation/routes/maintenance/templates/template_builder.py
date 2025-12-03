"""
Template Builder Routes
Routes for building and editing maintenance templates before submission.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from app import db
from app.logger import get_logger
from app.buisness.maintenance.builders.template_builder_context import TemplateBuilderContext
from app.data.maintenance.builders.template_builder_memory import TemplateBuilderMemory
from app.data.maintenance.builders.template_builder_attachment_reference import TemplateBuilderAttachmentReference
from app.data.maintenance.templates.template_action_sets import TemplateActionSet
from app.services.maintenance.template_builder_service import TemplateBuilderService

logger = get_logger("asset_management.routes.maintenance.manager.template_builder")

# Create template builder blueprint (will be registered under /maintenance/manager/template-builder)
template_builder_bp = Blueprint('template_builder', __name__, url_prefix='')


@template_builder_bp.route('/new')
@login_required
def new_builder():
    """
    Create a new template builder.
    Query params:
        - from_template: ID of template to copy from (optional)
        - is_revision: If true, create as revision (optional)
    """
    from_template_id = request.args.get('from_template', type=int)
    is_revision = request.args.get('is_revision', 'false').lower() == 'true'
    
    if from_template_id:
        # Copy from existing template
        try:
            template = TemplateActionSet.query.get_or_404(from_template_id)
            if is_revision:
                name = f"Revision of {template.task_name}"
            else:
                name = f"Copy of {template.task_name}"
            
            context = TemplateBuilderContext.copy_from_template(
                template_action_set_id=from_template_id,
                name=name,
                is_revision=is_revision,
                user_id=current_user.id
            )
            if is_revision:
                flash('Template builder created as new revision', 'success')
            else:
                flash('Template builder created from existing template', 'success')
            return redirect(url_for('template_builder.view_builder', builder_id=context.builder_id))
        except Exception as e:
            logger.error(f"Error creating builder from template: {e}")
            flash(f'Error creating builder: {str(e)}', 'error')
            return redirect(url_for('manager_portal.build_maintenance'))
    else:
        # Create blank builder
        try:
            context = TemplateBuilderContext.create_blank(
                name='New Template',
                build_type=None,
                user_id=current_user.id
            )
            flash('New template builder created', 'success')
            return redirect(url_for('template_builder.view_builder', builder_id=context.builder_id))
        except Exception as e:
            logger.error(f"Error creating blank builder: {e}")
            flash(f'Error creating builder: {str(e)}', 'error')
            return redirect(url_for('manager_portal.build_maintenance'))

# =========================
# Split Add Action Endpoints
# =========================

@template_builder_bp.route('/<int:builder_id>/add-blank-action', methods=['POST'])
@login_required
def add_blank_action(builder_id):
    """Add a blank action with default name and redirect to edit page."""
    try:
        context = TemplateBuilderContext(builder_id)
        
        # Create a minimal action dict with just a default name
        # User will fill in all details on the edit page
        action_dict = {
            'action_name': 'New Action'
        }
        
        # If form has actionName, use it; otherwise use default
        if request.form.get('actionName'):
            action_dict['action_name'] = request.form.get('actionName')
        
        context.add_action_from_dict(action_dict)
        
        # Get the index of the newly created action (it will be the last one)
        new_action_index = len(context.build_actions) - 1
        
        flash('Blank action created successfully', 'success')
    except Exception as e:
        logger.error(f"Error adding blank action to builder {builder_id}: {e}", exc_info=True)
        flash(f'Error adding action: {str(e)}', 'error')
        return redirect(url_for('template_builder.view_builder', builder_id=builder_id))
    
    # Support both HTMX and standard post
    is_htmx = request.headers.get('HX-Request', '').lower() == 'true'
    if is_htmx:
        builder_data = TemplateBuilderService.get_builder_data(builder_id)
        available_templates = TemplateBuilderService.get_available_templates()
        builder_json = TemplateBuilderService.get_builder_json(builder_id)
        return render_template(
            'maintenance/user_views/manager/template_builder.html',
            builder=builder_data,
            available_templates=available_templates,
            builder_json=builder_json
        )
    # Redirect to the edit page with the newly created action selected
    return redirect(url_for('template_builder.view_builder', builder_id=builder_id, action_index=new_action_index))

@template_builder_bp.route('/<int:builder_id>/add-action-from-proto/<int:proto_id>', methods=['POST'])
@login_required
def add_action_from_proto(builder_id, proto_id):
    """Add an action by copying from a ProtoActionItem."""
    try:
        context = TemplateBuilderContext(builder_id)
        context.add_action_from_proto(proto_id)
        flash('Action added from proto', 'success')
    except Exception as e:
        logger.error(f"Error adding action from proto to builder {builder_id}: {e}", exc_info=True)
        flash(f'Error adding action from proto: {str(e)}', 'error')
    return redirect(url_for('template_builder.view_builder', builder_id=builder_id))

@template_builder_bp.route('/<int:builder_id>/add-action-from-template-action/<int:template_action_id>', methods=['POST'])
@login_required
def add_action_from_template_action(builder_id, template_action_id):
    """Add an action by copying from a TemplateActionItem."""
    try:
        context = TemplateBuilderContext(builder_id)
        context.add_action_from_template_item(template_action_id)
        flash('Action added from template action', 'success')
    except Exception as e:
        logger.error(f"Error adding action from template action to builder {builder_id}: {e}", exc_info=True)
        flash(f'Error adding action from template: {str(e)}', 'error')
    return redirect(url_for('template_builder.view_builder', builder_id=builder_id))

@template_builder_bp.route('/<int:builder_id>/add-action-from-json', methods=['POST'])
@login_required
def add_action_from_json(builder_id):
    """Add an action from JSON payload."""
    try:
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            raise ValueError("Invalid JSON payload")
        # Accept either the dict directly or under 'action'
        action_dict = payload.get('action', payload)
        if not isinstance(action_dict, dict):
            raise ValueError("Invalid action payload")
        context = TemplateBuilderContext(builder_id)
        context.add_action_from_dict(action_dict)
        flash('Action added from JSON', 'success')
    except Exception as e:
        logger.error(f"Error adding action from JSON to builder {builder_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 400
    return jsonify({'status': 'ok'}), 200

@template_builder_bp.route('/<int:builder_id>/get-action-dict/<int:action_index>', methods=['GET'])
@login_required
def get_action_dict(builder_id, action_index):
    """Get action dictionary for a specific action index in the builder."""
    try:
        context = TemplateBuilderContext(builder_id)
        if 0 <= action_index < len(context.build_actions):
            action = context.build_actions[action_index]
            action_dict = action.to_dict()
            # Remove sequence_order so it gets assigned automatically
            if 'sequence_order' in action_dict:
                del action_dict['sequence_order']
            return jsonify({'action_dict': action_dict}), 200
        else:
            return jsonify({'error': f'Action index {action_index} out of range'}), 404
    except Exception as e:
        logger.error(f"Error getting action dict for builder {builder_id}, action {action_index}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 400


@template_builder_bp.route('/<int:builder_id>')
@login_required
def view_builder(builder_id):
    """View and edit template builder."""
    try:
        # Check if builder has already been submitted
        builder_memory = TemplateBuilderMemory.query.get_or_404(builder_id)
        if builder_memory.build_status == 'Submitted' and builder_memory.template_action_set_id:
            return redirect(url_for('template_builder.already_submitted', builder_id=builder_id))
        
        # Store in session for easy access
        session['active_template_builder_id'] = builder_id
        
        # Get builder data via service
        builder_data = TemplateBuilderService.get_builder_data(builder_id)
        available_templates = TemplateBuilderService.get_available_templates()
        builder_json = TemplateBuilderService.get_builder_json(builder_id)
        
        # Get selected action index from query parameter
        selected_action_index = request.args.get('action_index', type=int)
        selected_action = None
        if selected_action_index is not None and 0 <= selected_action_index < len(builder_data['actions']):
            selected_action = builder_data['actions'][selected_action_index]
        elif builder_data['actions']:
            # Default to first action if none selected
            selected_action = builder_data['actions'][0]
            selected_action_index = 0
        
        # Get parts and tools for dropdowns
        from app.data.core.supply.part import Part
        from app.data.core.supply.tool import Tool
        parts = Part.query.filter_by(status='Active').order_by(Part.part_name).all()
        tools = Tool.query.order_by(Tool.tool_name).all()
        
        return render_template(
            'maintenance/builder/edit_build_template.html',
            builder=builder_data,
            available_templates=available_templates,
            builder_json=builder_json,
            parts=parts,
            tools=tools,
            selected_action_index=selected_action_index,
            selected_action=selected_action
        )
    except Exception as e:
        logger.error(f"Error loading builder {builder_id}: {e}")
        flash(f'Error loading template builder: {str(e)}', 'error')
        return redirect(url_for('manager_portal.build_maintenance'))


@template_builder_bp.route('/<int:builder_id>/already-submitted')
@login_required
def already_submitted(builder_id):
    """Show message that builder has already been submitted."""
    try:
        builder_memory = TemplateBuilderMemory.query.get_or_404(builder_id)
        
        if not builder_memory.template_action_set_id:
            # If somehow status is Submitted but no template_id, redirect to builder
            flash('Builder status is submitted but no template found. Redirecting to builder.', 'warning')
            return redirect(url_for('template_builder.view_builder', builder_id=builder_id))
        
        template = TemplateActionSet.query.get(builder_memory.template_action_set_id)
        
        return render_template(
            'maintenance/user_views/manager/template_builder_already_submitted.html',
            builder=builder_memory,
            template=template
        )
    except Exception as e:
        logger.error(f"Error loading already submitted builder {builder_id}: {e}")
        flash(f'Error loading builder: {str(e)}', 'error')
        return redirect(url_for('manager_portal.build_maintenance'))


@template_builder_bp.route('/drafts')
@login_required
def view_drafts():
    """View incomplete template builder drafts."""
    try:
        # Get search parameters
        search_id = request.args.get('search_id', type=int)
        search_user_id = request.args.get('search_user_id', type=int)
        search_name = request.args.get('search_name', '').strip() or None
        search_content = request.args.get('search_content', '').strip() or None
        
        # Default to current user's ID if no search_user_id provided
        if search_user_id is None:
            search_user_id = current_user.id
        
        # Build query - only show incomplete drafts (not submitted)
        query = TemplateBuilderMemory.query.filter(
            TemplateBuilderMemory.build_status != 'Submitted'
        )
        
        # Apply filters
        if search_id:
            query = query.filter_by(id=search_id)
        if search_user_id:
            query = query.filter_by(created_by_id=search_user_id)
        if search_name:
            query = query.filter(TemplateBuilderMemory.name.ilike(f'%{search_name}%'))
        if search_content:
            # Search in build_state JSON content
            query = query.filter(TemplateBuilderMemory.build_state.ilike(f'%{search_content}%'))
        
        # Order by most recently updated
        drafts = query.order_by(TemplateBuilderMemory.updated_at.desc()).all()
        
        # Get user information for display
        from app.data.core.user_info.user import User
        user_map = {}
        user_ids = set(draft.created_by_id for draft in drafts if draft.created_by_id)
        if user_ids:
            users = User.query.filter(User.id.in_(user_ids)).all()
            user_map = {user.id: user.username for user in users}
        
        # Format drafts for template
        drafts_data = []
        for draft in drafts:
            build_state = draft.get_build_state_dict()
            metadata = build_state.get('metadata', {})
            actions = build_state.get('actions', [])
            
            drafts_data.append({
                'id': draft.id,
                'name': draft.name,
                'build_type': draft.build_type,
                'build_status': draft.build_status,
                'created_by_id': draft.created_by_id,
                'created_by_username': user_map.get(draft.created_by_id, 'Unknown'),
                'created_at': draft.created_at,
                'updated_at': draft.updated_at,
                'task_name': metadata.get('task_name', ''),
                'total_actions': len(actions),
            })
        
        return render_template(
            'maintenance/user_views/manager/view_drafts.html',
            drafts=drafts_data,
            search_id=search_id,
            search_user_id=search_user_id,
            search_name=search_name or '',
            search_content=search_content or ''
        )
    except Exception as e:
        logger.error(f"Error loading drafts: {e}")
        flash(f'Error loading drafts: {str(e)}', 'error')
        return redirect(url_for('manager_portal.build_maintenance'))


@template_builder_bp.route('/<int:builder_id>/actions-list', methods=['GET'])
@login_required
def get_actions_list(builder_id):
    """Get actions list fragment for HTMX."""
    try:
        builder_data = TemplateBuilderService.get_builder_data(builder_id)
        return render_template(
            'maintenance/user_views/manager/template_builder_actions_list.html',
            builder=builder_data
        )
    except Exception as e:
        logger.error(f"Error loading actions list for builder {builder_id}: {e}")
        return f'<div class="alert alert-danger">Error loading actions: {str(e)}</div>', 500


@template_builder_bp.route('/<int:builder_id>/action/add', methods=['POST', 'PUT'])
@login_required
def add_action(builder_id):
    """Add an action to the builder."""
    try:
        context = TemplateBuilderContext(builder_id)
        action_type = request.form.get('action_type')
        
        if action_type == 'custom':
            # Convert form data to action dict via service
            action_dict = TemplateBuilderService.convert_form_to_action_dict(request.form)
            context.add_action_from_dict(action_dict)
            flash('Action added successfully', 'success')
        elif action_type == 'from_template':
            template_action_id = request.form.get('template_action_id', type=int)
            if template_action_id:
                context.add_action_from_template_item(template_action_id)
                flash('Action added from template', 'success')
            else:
                flash('Template action ID required', 'error')
        elif action_type == 'from_proto':
            proto_action_id = request.form.get('proto_action_id', type=int)
            if proto_action_id:
                context.add_action_from_proto(proto_action_id)
                flash('Action added from proto', 'success')
            else:
                flash('Proto action ID required', 'error')
        else:
            flash('Invalid action type', 'error')
            
    except Exception as e:
        logger.error(f"Error adding action to builder {builder_id}: {e}")
        flash(f'Error adding action: {str(e)}', 'error')
    
    # Check if this is an HTMX request
    is_htmx = request.headers.get('HX-Request', '').lower() == 'true'
    
    if is_htmx:
        # Return full page HTML for HTMX to extract sections via OOB swaps
        builder_data = TemplateBuilderService.get_builder_data(builder_id)
        available_templates = TemplateBuilderService.get_available_templates()
        builder_json = TemplateBuilderService.get_builder_json(builder_id)
        return render_template(
            'maintenance/user_views/manager/template_builder.html',
            builder=builder_data,
            available_templates=available_templates,
            builder_json=builder_json
        )
    else:
        # Regular form submission - redirect
        return redirect(url_for('template_builder.view_builder', builder_id=builder_id))

@template_builder_bp.route('/<int:builder_id>/action/<int:action_index>/update', methods=['POST'])
@login_required
def update_template_action(builder_id, action_index):
    """Update a template build action's editable fields."""
    try:
        updates = TemplateBuilderService.convert_form_to_action_updates(request.form)
        context = TemplateBuilderContext(builder_id)
        context.update_action(action_index, updates)
        flash('Action updated successfully', 'success')
    except Exception as e:
        logger.error(f"Error updating action {action_index} in builder {builder_id}: {e}", exc_info=True)
        flash(f'Error updating action: {str(e)}', 'error')
    # HTMX support mirrors metadata/add routes
    is_htmx = request.headers.get('HX-Request', '').lower() == 'true'
    if is_htmx:
        builder_data = TemplateBuilderService.get_builder_data(builder_id)
        available_templates = TemplateBuilderService.get_available_templates()
        builder_json = TemplateBuilderService.get_builder_json(builder_id)
        
        # Get selected action index
        selected_action_index = request.args.get('action_index', type=int) or action_index
        selected_action = None
        if selected_action_index is not None and 0 <= selected_action_index < len(builder_data['actions']):
            selected_action = builder_data['actions'][selected_action_index]
        
        # Get parts and tools for dropdowns
        from app.data.core.supply.part import Part
        from app.data.core.supply.tool import Tool
        parts = Part.query.filter_by(status='Active').order_by(Part.part_name).all()
        tools = Tool.query.order_by(Tool.tool_name).all()
        
        return render_template(
            'maintenance/builder/edit_build_template.html',
            builder=builder_data,
            available_templates=available_templates,
            builder_json=builder_json,
            parts=parts,
            tools=tools,
            selected_action_index=selected_action_index,
            selected_action=selected_action
        )
    return redirect(url_for('template_builder.view_builder', builder_id=builder_id, action_index=action_index))


@template_builder_bp.route('/<int:builder_id>/action/<int:action_index>/delete', methods=['POST'])
@login_required
def delete_action(builder_id, action_index):
    """Delete an action from the builder."""
    try:
        context = TemplateBuilderContext(builder_id)
        context.remove_action(action_index)
        flash('Action deleted successfully', 'success')
    except IndexError:
        flash('Action not found', 'error')
    except Exception as e:
        logger.error(f"Error deleting action from builder {builder_id}: {e}")
        flash(f'Error deleting action: {str(e)}', 'error')
    
    return redirect(url_for('template_builder.view_builder', builder_id=builder_id))





@template_builder_bp.route('/<int:builder_id>/action/<int:action_index>/move', methods=['POST'])
@login_required
def move_action(builder_id, action_index):
    """Move an action up or down in the sequence."""
    try:
        context = TemplateBuilderContext(builder_id)
        direction = request.form.get('direction')  # 'up' or 'down'
        
        if direction == 'up' and action_index > 0:
            # Swap with previous action
            actions = context.build_actions
            actions[action_index], actions[action_index - 1] = actions[action_index - 1], actions[action_index]
            context._renumber_sequence_orders()
            context._save()
        elif direction == 'down' and action_index < len(context.build_actions) - 1:
            # Swap with next action
            actions = context.build_actions
            actions[action_index], actions[action_index + 1] = actions[action_index + 1], actions[action_index]
            context._renumber_sequence_orders()
            context._save()
    except Exception as e:
        logger.error(f"Error moving action in builder {builder_id}: {e}")
        # Only flash on error for non-HTMX requests
        is_htmx = request.headers.get('HX-Request', '').lower() == 'true'
        if not is_htmx:
            flash(f'Error moving action: {str(e)}', 'error')
    
    # Check if this is an HTMX request
    is_htmx = request.headers.get('HX-Request', '').lower() == 'true'
    
    if is_htmx:
        # Return full page HTML for HTMX to extract sections
        builder_data = TemplateBuilderService.get_builder_data(builder_id)
        available_templates = TemplateBuilderService.get_available_templates()
        builder_json = TemplateBuilderService.get_builder_json(builder_id)
        
        # Get selected action index
        selected_action_index = request.args.get('action_index', type=int)
        selected_action = None
        if selected_action_index is not None and 0 <= selected_action_index < len(builder_data['actions']):
            selected_action = builder_data['actions'][selected_action_index]
        
        # Get parts and tools for dropdowns
        from app.data.core.supply.part import Part
        from app.data.core.supply.tool import Tool
        parts = Part.query.filter_by(status='Active').order_by(Part.part_name).all()
        tools = Tool.query.order_by(Tool.tool_name).all()
        
        return render_template(
            'maintenance/builder/edit_build_template.html',
            builder=builder_data,
            available_templates=available_templates,
            builder_json=builder_json,
            parts=parts,
            tools=tools,
            selected_action_index=selected_action_index,
            selected_action=selected_action
        )
    else:
        # Regular form submission - redirect
        return redirect(url_for('template_builder.view_builder', builder_id=builder_id))





@template_builder_bp.route('/<int:builder_id>/action/<int:action_index>/part/add', methods=['POST'])
@login_required
def add_part_demand(builder_id, action_index):
    """Add a part demand to an action."""
    print(f"\n\n=== ADD PART DEMAND ROUTE CALLED ===")
    print(f"builder_id: {builder_id}, action_index: {action_index}")
    print(f"request.form: {request.form}")
    print(f"request.method: {request.method}")
    print(f"request.headers.get('HX-Request'): {request.headers.get('HX-Request')}")
    try:
        context = TemplateBuilderContext(builder_id)
        part_dict = TemplateBuilderService.convert_form_to_part_dict(request.form)
        context.add_part_demand_to_action(action_index, part_dict)
        print(f"context: {context.to_dict()}")
        flash('Part demand added successfully', 'success')
    except Exception as e:
        logger.error(f"Error adding part demand to builder {builder_id}: {e}")
        flash(f'Error adding part demand: {str(e)}', 'error')
    
    return redirect(url_for('template_builder.view_builder', builder_id=builder_id))





@template_builder_bp.route('/<int:builder_id>/action/<int:action_index>/part/<int:part_index>/delete', methods=['POST'])
@login_required
def delete_part_demand(builder_id, action_index, part_index):
    """Delete a part demand from an action."""
    try:
        context = TemplateBuilderContext(builder_id)
        context.remove_part_demand_from_action(action_index, part_index)
        flash('Part demand deleted successfully', 'success')
    except IndexError:
        flash('Part demand not found', 'error')
    except Exception as e:
        logger.error(f"Error deleting part demand from builder {builder_id}: {e}")
        flash(f'Error deleting part demand: {str(e)}', 'error')
    
    return redirect(url_for('template_builder.view_builder', builder_id=builder_id))

@template_builder_bp.route('/<int:builder_id>/action/<int:action_index>/part/<int:part_index>/update', methods=['POST'])
@login_required
def update_part_demand(builder_id, action_index, part_index):
    """Update a part demand on a build action."""
    try:
        updates = TemplateBuilderService.convert_form_to_part_updates(request.form)
        context = TemplateBuilderContext(builder_id)
        context.update_part_demand(action_index, part_index, updates)
        flash('Part demand updated', 'success')
    except Exception as e:
        logger.error(f"Error updating part demand {part_index} on action {action_index} in builder {builder_id}: {e}", exc_info=True)
        flash(f'Error updating part demand: {str(e)}', 'error')
    return redirect(url_for('template_builder.view_builder', builder_id=builder_id))




@template_builder_bp.route('/<int:builder_id>/action/<int:action_index>/tool/add', methods=['POST'])
@login_required
def add_tool(builder_id, action_index):
    """Add a tool to an action."""
    # Debug: Print to console first to verify route is being called
    print(f"\n\n=== ADD TOOL ROUTE CALLED ===")
    print(f"builder_id: {builder_id}, action_index: {action_index}")
    print(f"request.form: {request.form}")
    print(f"request.method: {request.method}")
    print(f"request.headers.get('HX-Request'): {request.headers.get('HX-Request')}")
    
    try:
        context = TemplateBuilderContext(builder_id)
        logger.info(f"ADD TOOL - request.form: {request.form}")
        logger.debug(f"ADD TOOL - builder_id: {builder_id}, action_index: {action_index}")
        
        tool_dict = TemplateBuilderService.convert_form_to_tool_dict(request.form)
        logger.info(f"ADD TOOL - tool_dict: {tool_dict}")
        print(f"tool_dict: {tool_dict}")
        
        context.add_tool_to_action(action_index, tool_dict)
        logger.info(f"ADD TOOL - Successfully added tool to action {action_index}")
        print(f"Successfully added tool")
        flash('Tool added successfully', 'success')
    except Exception as e:
        logger.error(f"Error adding tool to builder {builder_id}: {e}", exc_info=True)
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Error adding tool: {str(e)}', 'error')
    
    return redirect(url_for('template_builder.view_builder', builder_id=builder_id))





@template_builder_bp.route('/<int:builder_id>/action/<int:action_index>/tool/<int:tool_index>/delete', methods=['POST'])
@login_required
def delete_tool(builder_id, action_index, tool_index):
    """Delete a tool from an action."""
    try:
        context = TemplateBuilderContext(builder_id)
        context.remove_tool_from_action(action_index, tool_index)
        flash('Tool deleted successfully', 'success')
    except IndexError:
        flash('Tool not found', 'error')
    except Exception as e:
        logger.error(f"Error deleting tool from builder {builder_id}: {e}")
        flash(f'Error deleting tool: {str(e)}', 'error')
    
    return redirect(url_for('template_builder.view_builder', builder_id=builder_id))

@template_builder_bp.route('/<int:builder_id>/action/<int:action_index>/tool/<int:tool_index>/update', methods=['POST'])
@login_required
def update_tool(builder_id, action_index, tool_index):
    """Update a tool on a build action."""
    try:
        updates = TemplateBuilderService.convert_form_to_tool_updates(request.form)
        context = TemplateBuilderContext(builder_id)
        context.update_tool(action_index, tool_index, updates)
        flash('Tool updated', 'success')
    except Exception as e:
        logger.error(f"Error updating tool {tool_index} on action {action_index} in builder {builder_id}: {e}", exc_info=True)
        flash(f'Error updating tool: {str(e)}', 'error')
    return redirect(url_for('template_builder.view_builder', builder_id=builder_id))




@template_builder_bp.route('/<int:builder_id>/metadata', methods=['POST'])
@login_required
def update_metadata(builder_id):
    """Update template metadata."""
    try:
        context = TemplateBuilderContext(builder_id)
        builder_memory = TemplateBuilderMemory.query.get_or_404(builder_id)
        
        # Update common fields
        # Task name is only editable if not a revision
        if 'task_name' in request.form and not builder_memory.is_revision:
            context.task_name = request.form.get('task_name')
        if 'description' in request.form:
            context.description = request.form.get('description')
        if 'estimated_duration' in request.form:
            duration = request.form.get('estimated_duration')
            context.set_metadata('estimated_duration', float(duration) if duration else None)
        
        # Revision number is always disabled, so we don't update it here
        # It's set automatically based on is_revision status
        
        flash('Metadata updated', 'success')
    except Exception as e:
        logger.error(f"Error updating metadata for builder {builder_id}: {e}")
        flash(f'Error updating metadata: {str(e)}', 'error')
    
    # Check if this is an HTMX request
    is_htmx = request.headers.get('HX-Request', '').lower() == 'true'
    
    if is_htmx:
        # Return full page HTML for HTMX to extract sections
        builder_data = TemplateBuilderService.get_builder_data(builder_id)
        available_templates = TemplateBuilderService.get_available_templates()
        builder_json = TemplateBuilderService.get_builder_json(builder_id)
        return render_template(
            'maintenance/user_views/manager/template_builder.html',
            builder=builder_data,
            available_templates=available_templates,
            builder_json=builder_json
        )
    else:
        # Regular form submission - redirect
        return redirect(url_for('template_builder.view_builder', builder_id=builder_id))





@template_builder_bp.route('/<int:builder_id>/submit', methods=['POST'])
@login_required
def submit_template(builder_id):
    """Submit template builder and create actual TemplateActionSet."""
    try:
        context = TemplateBuilderContext(builder_id)
        template_context = context.submit_template(user_id=current_user.id)
        
        flash(f'Template created successfully! Template ID: {template_context.template_action_set_id}', 'success')
        return redirect(url_for('maintenance.view_maintenance_template', template_set_id=template_context.template_action_set_id))
    except ValueError as e:
        logger.error(f"Validation error submitting builder {builder_id}: {e}")
        flash(f'Validation error: {str(e)}', 'error')
    except Exception as e:
        logger.error(f"Error submitting builder {builder_id}: {e}")
        flash(f'Error submitting template: {str(e)}', 'error')
    
    return redirect(url_for('template_builder.view_builder', builder_id=builder_id))


@template_builder_bp.route('/<int:builder_id>/delete', methods=['POST'])
@login_required
def delete_builder(builder_id):
    """Delete a template builder draft."""
    try:
        # Get the builder memory record
        builder_memory = TemplateBuilderMemory.query.get_or_404(builder_id)
        
        # Check if user has permission (only creator can delete, or admin)
        if builder_memory.created_by_id != current_user.id:
            flash('You do not have permission to delete this draft.', 'error')
            return redirect(url_for('template_builder.view_builder', builder_id=builder_id))
        
        # Check if already submitted
        if builder_memory.build_status == 'Submitted':
            flash('Cannot delete a submitted template.', 'error')
            return redirect(url_for('template_builder.view_builder', builder_id=builder_id))
        
        # Delete related attachment references
        attachment_refs = TemplateBuilderAttachmentReference.query.filter_by(
            template_builder_memory_id=builder_id
        ).all()
        for ref in attachment_refs:
            db.session.delete(ref)
        
        # Delete the builder memory record
        db.session.delete(builder_memory)
        db.session.commit()
        
        flash('Draft template deleted successfully.', 'success')
        return redirect(url_for('manager_portal.build_maintenance'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting builder {builder_id}: {e}")
        flash(f'Error deleting draft: {str(e)}', 'error')
        return redirect(url_for('template_builder.view_builder', builder_id=builder_id))




# =========================
# Template Action Creator Portal (Builder)
# =========================

@template_builder_bp.route('/<int:builder_id>/action-creator-portal')
@login_required
def template_action_creator_portal(builder_id):
    """Render a portal to browse and add actions (template sets, items, proto) to the builder."""
    from app.data.maintenance.templates.template_actions import TemplateActionItem
    from app.data.maintenance.templates.template_action_sets import TemplateActionSet
    from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem
    try:
        # Fetch lists
        template_action_sets = TemplateActionSet.query.filter_by(is_active=True).order_by(TemplateActionSet.task_name).all()
        template_action_items = TemplateActionItem.query.join(TemplateActionSet).filter(TemplateActionSet.is_active == True).order_by(TemplateActionSet.task_name, TemplateActionItem.sequence_order).all()
        proto_actions = ProtoActionItem.query.order_by(ProtoActionItem.action_name).all()
        search_term = request.args.get('search', '').strip().lower()
        # Basic filtering
        def match(text: str) -> bool:
            return search_term in (text or '').lower()
        if search_term:
            template_action_sets = [tas for tas in template_action_sets if match(tas.task_name) or match(tas.description)]
            template_action_items = [tai for tai in template_action_items if match(tai.action_name) or match(tai.description)]
            proto_actions = [pa for pa in proto_actions if match(pa.action_name) or match(pa.description)]
        
        # Get current build actions from the builder
        context = TemplateBuilderContext(builder_id)
        current_build_actions = []
        for idx, action in enumerate(context.build_actions):
            current_build_actions.append({
                'index': idx,
                'action_dict': action.to_dict(),
                'action_name': action.action_name or 'Unnamed Action',
                'description': action.description or '',
                'sequence_order': action.sequence_order,
                'estimated_duration': action.estimated_duration,
                'part_count': len(action.part_demands),
                'tool_count': len(action.tools),
                'attachment_count': len(action.attachments),
            })
        
        return render_template(
            'maintenance/builder/action_creator_portal.html',
            builder_id=builder_id,
            template_action_sets=template_action_sets,
            template_action_items=template_action_items,
            proto_actions=proto_actions,
            current_build_actions=current_build_actions,
            search_term=search_term
        )
    except Exception as e:
        logger.error(f"Error rendering template action creator portal for builder {builder_id}: {e}", exc_info=True)
        flash('Error loading action creator portal', 'error')
        return redirect(url_for('template_builder.view_builder', builder_id=builder_id))


@template_builder_bp.route('/search-template-action-sets')
@login_required
def tb_search_template_action_sets():
    """HTMX endpoint to return template action set search results for builder portal."""
    from app.data.maintenance.templates.template_action_sets import TemplateActionSet
    try:
        search = request.args.get('search', '').strip().lower()
        limit = request.args.get('limit', type=int, default=100)  # Increased default limit
        builder_id = request.args.get('builder_id', type=int)
        q = TemplateActionSet.query.filter_by(is_active=True).order_by(TemplateActionSet.task_name)
        sets = q.all()
        if search:
            sets = [tas for tas in sets if (search in (tas.task_name or '').lower()) or (tas.description and search in tas.description.lower())]
        total_count = len(sets)
        # If no search term, show all; if searching, apply limit
        if search:
            showing_sets = sets[:limit]
        else:
            showing_sets = sets
        return render_template(
            'maintenance/user_views/manager/partials/template_action_list.html',
            list_type='template_sets',
            items=showing_sets,
            total_count=total_count,
            showing=len(showing_sets),
            builder_id=builder_id
        )
    except Exception as e:
        logger.error(f"Error in builder template action sets search: {e}", exc_info=True)
        return render_template(
            'maintenance/user_views/manager/partials/template_action_list.html',
            list_type='template_sets',
            items=[],
            total_count=0,
            showing=0,
            builder_id=None,
            error=str(e)
        ), 500


@template_builder_bp.route('/search-template-actions')
@login_required
def tb_search_template_actions():
    """HTMX endpoint to return template action item search results for builder portal."""
    from app.data.maintenance.templates.template_actions import TemplateActionItem
    from app.data.maintenance.templates.template_action_sets import TemplateActionSet
    try:
        search = request.args.get('search', '').strip().lower()
        limit = request.args.get('limit', type=int, default=8)
        builder_id = request.args.get('builder_id', type=int)
        items = TemplateActionItem.query.join(TemplateActionSet).filter(TemplateActionSet.is_active == True).order_by(TemplateActionSet.task_name, TemplateActionItem.sequence_order).all()
        if search:
            items = [tai for tai in items if (search in (tai.action_name or '').lower()) or (tai.description and search in tai.description.lower())]
        total_count = len(items)
        showing_items = items[:limit]
        return render_template(
            'maintenance/user_views/manager/partials/template_action_list.html',
            list_type='template_actions',
            items=showing_items,
            total_count=total_count,
            showing=len(showing_items),
            builder_id=builder_id
        )
    except Exception as e:
        logger.error(f"Error in builder template actions search: {e}", exc_info=True)
        return render_template(
            'maintenance/user_views/manager/partials/template_action_list.html',
            list_type='template_actions',
            items=[],
            total_count=0,
            showing=0,
            builder_id=None,
            error=str(e)
        ), 500


@template_builder_bp.route('/search-proto-actions')
@login_required
def tb_search_proto_actions():
    """HTMX endpoint to return proto action search results for builder portal."""
    from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem
    try:
        search = request.args.get('search', '').strip().lower()
        limit = request.args.get('limit', type=int, default=8)
        builder_id = request.args.get('builder_id', type=int)
        proto_actions = ProtoActionItem.query.order_by(ProtoActionItem.action_name).all()
        if search:
            proto_actions = [pa for pa in proto_actions if (search in (pa.action_name or '').lower()) or (pa.description and search in pa.description.lower())]
        total_count = len(proto_actions)
        showing_actions = proto_actions[:limit]
        return render_template(
            'maintenance/user_views/manager/partials/template_action_list.html',
            list_type='proto_actions',
            items=showing_actions,
            total_count=total_count,
            showing=len(showing_actions),
            builder_id=builder_id
        )
    except Exception as e:
        logger.error(f"Error in builder proto actions search: {e}", exc_info=True)
        return render_template(
            'maintenance/user_views/manager/partials/template_action_list.html',
            list_type='proto_actions',
            items=[],
            total_count=0,
            showing=0,
            builder_id=None,
            error=str(e)
        ), 500


@template_builder_bp.route('/list-template-action-items/<int:template_action_set_id>')
@login_required
def tb_list_template_action_items(template_action_set_id):
    """HTMX endpoint to return template action items for a specific template action set (builder portal)."""
    from app.data.maintenance.templates.template_action_sets import TemplateActionSet
    try:
        builder_id = request.args.get('builder_id', type=int)
        template_set = TemplateActionSet.query.get_or_404(template_action_set_id)
        template_items = sorted(template_set.template_action_items, key=lambda tai: tai.sequence_order)
        return render_template(
            'maintenance/user_views/manager/partials/template_action_list.html',
            list_type='template_items_for_set',
            items=template_items,
            template_action_set=template_set,
            builder_id=builder_id
        )
    except Exception as e:
        logger.error(f"Error listing template action items for builder portal: {e}", exc_info=True)
        return render_template(
            'maintenance/user_views/manager/partials/template_action_list.html',
            list_type='template_items_for_set',
            items=[],
            builder_id=None,
            error=str(e)
        ), 500
