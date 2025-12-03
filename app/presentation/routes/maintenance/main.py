"""
Maintenance main routes - Portal splash page
"""
from flask import Blueprint, render_template, abort, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from app.logger import get_logger
from app import db

logger = get_logger("asset_management.routes.maintenance")

# Create maintenance blueprint
maintenance_bp = Blueprint('maintenance', __name__, url_prefix='/maintenance')

@maintenance_bp.route('/')
@maintenance_bp.route('/index')
@login_required
def index():
    """Maintenance portal splash page - Choose between technician, manager, and fleet portals"""
    logger.info("Maintenance splash page accessed")
    
    # Get basic maintenance stats if models are available
    stats = {}
    try:
        from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
        from app.data.maintenance.base.actions import Action
        
        stats = {
            'total_maintenance_events': MaintenanceActionSet.query.count(),
            'in_progress_events': MaintenanceActionSet.query.filter_by(status='In Progress').count(),
            'planned_events': MaintenanceActionSet.query.filter_by(status='Planned').count(),
            'completed_events': MaintenanceActionSet.query.filter_by(status='Complete').count(),
        }
    except ImportError:
        logger.warning("Maintenance models not available")
        stats = {
            'total_maintenance_events': 0,
            'in_progress_events': 0,
            'planned_events': 0,
            'completed_events': 0,
        }
    
    return render_template('maintenance/splash.html', stats=stats)


@maintenance_bp.route('/view-events')
@login_required
def view_events():
    """View maintenance events with comprehensive filtering"""
    logger.info(f"View events accessed by {current_user.username}")
    
    try:
        from app.presentation.routes.maintenance.event_portal import render_view_events_module
        return render_view_events_module(
            request=request,
            current_user=current_user,
            portal_type='manager',
            per_page=20
        )
    except Exception as e:
        logger.error(f"Error rendering view events: {e}")
        import traceback
        traceback.print_exc()
        flash("Error loading events. Please try again.", "error")
        return redirect(url_for('maintenance.index'))


@maintenance_bp.route('/maintenance-template/<int:template_set_id>')
@maintenance_bp.route('/maintenance-template/<int:template_set_id>/view')
@login_required
def view_maintenance_template(template_set_id):
    """View detailed information about a maintenance template"""
    logger.info(f"Viewing maintenance template for template_set_id={template_set_id}")
    
    try:
        from app.buisness.maintenance.templates.template_action_set_struct import TemplateActionSetStruct
        from app.buisness.maintenance.templates.template_maintenance_context import TemplateMaintenanceContext
        from app.buisness.maintenance.templates.template_action_item_struct import TemplateActionItemStruct
        
        # Get the template action set
        template_struct = TemplateActionSetStruct(template_set_id)
        
        if not template_struct:
            logger.warning(f"No template action set found for template_set_id={template_set_id}")
            abort(404)
        
        # Get template action items with their structs for convenient access
        action_item_structs = [TemplateActionItemStruct(item) for item in template_struct.template_action_items]
        
        # Get context for business logic if needed
        template_context = TemplateMaintenanceContext(template_struct)
        
        # Collect unique proto actions referenced by template action items
        from app.buisness.maintenance.proto_templates.proto_action_item_struct import ProtoActionItemStruct
        proto_actions_dict = {}  # {proto_id: {'struct': ProtoActionItemStruct, 'referenced_by': [TemplateActionItem]}}
        
        for action_item in template_struct.template_action_items:
            if action_item.proto_action_item:
                proto_id = action_item.proto_action_item.id
                if proto_id not in proto_actions_dict:
                    proto_actions_dict[proto_id] = {
                        'struct': ProtoActionItemStruct(action_item.proto_action_item),
                        'referenced_by': []
                    }
                proto_actions_dict[proto_id]['referenced_by'].append(action_item)
        
        # Convert to list for template
        proto_actions = list(proto_actions_dict.values())
        
        return render_template(
            'maintenance/maintenance_templates/view_maintenance_template.html',
            template=template_struct,
            template_context=template_context,
            action_items=action_item_structs,
            proto_actions=proto_actions,
        )
        
    except ImportError as e:
        logger.error(f"Could not import maintenance template modules: {e}")
        abort(500)
    except Exception as e:
        logger.error(f"Error viewing maintenance template {template_set_id}: {e}")
        import traceback
        traceback.print_exc()
        abort(500)


@maintenance_bp.route('/proto-actions/<int:proto_action_id>')
@maintenance_bp.route('/proto-actions/<int:proto_action_id>/view')
@login_required
def view_proto_action(proto_action_id):
    """View detailed information about a proto action"""
    logger.info(f"Viewing proto action for proto_action_id={proto_action_id}")
    
    try:
        from app.buisness.maintenance.proto_templates.proto_action_item_struct import ProtoActionItemStruct
        from app.buisness.maintenance.proto_templates.proto_action_context import ProtoActionContext
        from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem
        
        # Get the proto action item
        proto_struct = ProtoActionItemStruct(proto_action_id)
        
        if not proto_struct:
            logger.warning(f"No proto action item found for proto_action_id={proto_action_id}")
            abort(404)
        
        # Get context for business logic
        proto_context = ProtoActionContext(proto_struct)
        
        # Get template action items that reference this proto action
        template_action_items = proto_struct.proto_action_item.template_action_items.all()
        
        return render_template(
            'maintenance/prototype/view_proto_action.html',
            proto=proto_struct,
            proto_context=proto_context,
            template_action_items=template_action_items,
        )
        
    except ImportError as e:
        logger.error(f"Could not import proto action modules: {e}")
        abort(500)
    except Exception as e:
        logger.error(f"Error viewing proto action {proto_action_id}: {e}")
        import traceback
        traceback.print_exc()
        abort(500)


