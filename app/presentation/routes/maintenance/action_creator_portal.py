"""
Action Creator Portal Routes
Standalone portal for creating actions from various sources
"""
import traceback
from flask import Blueprint, render_template, request, abort
from flask_login import login_required, current_user

from app.logger import get_logger
from app.buisness.maintenance.base.structs.action_struct import ActionStruct
from app.buisness.maintenance.base.structs.maintenance_action_set_struct import MaintenanceActionSetStruct
from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
from app.data.maintenance.base.actions import Action
from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem
from app.data.maintenance.templates.template_action_sets import TemplateActionSet
from app.data.maintenance.templates.template_actions import TemplateActionItem

logger = get_logger("asset_management.routes.maintenance.action_creator_portal")

# Create blueprint for action creator portal
action_creator_portal_bp = Blueprint('action_creator_portal', __name__, url_prefix='/maintenance/action-creator-portal')


@action_creator_portal_bp.route('/<int:maintenance_action_set_id>')
@login_required
def action_creator_portal(maintenance_action_set_id):
    """Render the Action Creator Portal page"""
    logger.info(f"Rendering action creator portal for maintenance_action_set_id={maintenance_action_set_id}")
    
    try:
        # Get maintenance struct
        maintenance_struct = MaintenanceActionSetStruct.from_maintenance_action_set_id(maintenance_action_set_id)
        
        if not maintenance_struct:
            logger.warning(f"No maintenance action set found for maintenance_action_set_id={maintenance_action_set_id}")
            abort(404)
        
        # Get maintenance context
        maintenance_context = MaintenanceContext.from_maintenance_action_set(maintenance_action_set_id)
        
        # Get current actions for "From Current Action Set" tab
        current_actions = [ActionStruct(action) for action in sorted(maintenance_struct.actions, key=lambda a: a.sequence_order)]
        
        # Get template action sets for "From Template" tab
        template_action_sets = TemplateActionSet.query.filter_by(is_active=True).order_by(TemplateActionSet.task_name).all()
        
        # Get template action items for "From Template Action" tab
        template_action_items = TemplateActionItem.query.join(
            TemplateActionSet
        ).filter(
            TemplateActionSet.is_active == True
        ).order_by(
            TemplateActionSet.task_name,
            TemplateActionItem.sequence_order
        ).all()
        
        # Get proto actions for "From Proto Action" tab
        proto_actions = ProtoActionItem.query.order_by(ProtoActionItem.action_name).all()
        
        # Search filter from query params
        search_term = request.args.get('search', '').strip().lower()
        
        # Filter template action sets by search
        filtered_template_sets = []
        if search_term:
            for tas in template_action_sets:
                if (search_term in tas.task_name.lower() or 
                    (tas.description and search_term in tas.description.lower())):
                    filtered_template_sets.append(tas)
        else:
            filtered_template_sets = template_action_sets
        
        # Filter template action items by search
        filtered_template_items = []
        if search_term:
            for tai in template_action_items:
                if (search_term in tai.action_name.lower() or 
                    (tai.description and search_term in tai.description.lower())):
                    filtered_template_items.append(tai)
        else:
            filtered_template_items = template_action_items
        
        # Filter proto actions by search
        filtered_proto_actions = []
        if search_term:
            for pa in proto_actions:
                if (search_term in pa.action_name.lower() or 
                    (pa.description and search_term in pa.description.lower())):
                    filtered_proto_actions.append(pa)
        else:
            filtered_proto_actions = proto_actions
        
        # Filter current actions by search
        filtered_current_actions = []
        if search_term:
            for action_struct in current_actions:
                if (search_term in action_struct.action.action_name.lower() or 
                    (action_struct.action.description and search_term in action_struct.action.description.lower())):
                    filtered_current_actions.append(action_struct)
        else:
            filtered_current_actions = current_actions
        
        # Get event_id if available
        event_id = maintenance_struct.event_id
        
        return render_template(
            'maintenance/base/action_creator_portal.html',
            maintenance_struct=maintenance_struct,
            maintenance_context=maintenance_context,
            maintenance_action_set_id=maintenance_action_set_id,
            event_id=event_id,
            template_action_sets=filtered_template_sets,
            template_action_items=filtered_template_items,
            proto_actions=filtered_proto_actions,
            current_actions=filtered_current_actions,
            search_term=search_term,
        )
        
    except ImportError as e:
        logger.error(f"Could not import maintenance modules: {e}")
        abort(500)
    except Exception as e:
        logger.error(f"Error rendering action creator portal for maintenance_action_set_id={maintenance_action_set_id}: {e}")
        traceback.print_exc()
        abort(500)


@action_creator_portal_bp.route('/search-template-action-sets')
@login_required
def search_template_action_sets():
    """HTMX endpoint to return template action set search results"""
    try:
        search = request.args.get('search', '').strip().lower()
        limit = request.args.get('limit', type=int, default=8)
        maintenance_action_set_id = request.args.get('maintenance_action_set_id', type=int)
        
        # Get all active template action sets
        template_sets = TemplateActionSet.query.filter_by(is_active=True).order_by(TemplateActionSet.task_name).all()
        
        # Filter by search term
        filtered_sets = []
        if search:
            for tas in template_sets:
                if (search in tas.task_name.lower() or 
                    (tas.description and search in tas.description.lower())):
                    filtered_sets.append(tas)
        else:
            filtered_sets = template_sets
        
        # Limit results
        total_count = len(filtered_sets)
        showing_sets = filtered_sets[:limit]
        
        return render_template(
            'maintenance/base/action_creator_portal/search_template_action_sets.html',
            template_action_sets=showing_sets,
            total_count=total_count,
            showing=len(showing_sets),
            search=search,
            maintenance_action_set_id=maintenance_action_set_id
        )
    except Exception as e:
        logger.error(f"Error in template action sets search: {e}")
        return render_template(
            'maintenance/base/action_creator_portal/search_template_action_sets.html',
            template_action_sets=[],
            total_count=0,
            showing=0,
            search=search or '',
            error=str(e)
        ), 500


@action_creator_portal_bp.route('/search-template-actions')
@login_required
def search_template_actions():
    """HTMX endpoint to return template action item search results"""
    try:
        search = request.args.get('search', '').strip().lower()
        limit = request.args.get('limit', type=int, default=8)
        maintenance_action_set_id = request.args.get('maintenance_action_set_id', type=int)
        
        # Get all template action items from active templates
        template_items = TemplateActionItem.query.join(
            TemplateActionSet
        ).filter(
            TemplateActionSet.is_active == True
        ).order_by(
            TemplateActionSet.task_name,
            TemplateActionItem.sequence_order
        ).all()
        
        # Filter by search term
        filtered_items = []
        if search:
            for tai in template_items:
                if (search in tai.action_name.lower() or 
                    (tai.description and search in tai.description.lower())):
                    filtered_items.append(tai)
        else:
            filtered_items = template_items
        
        # Limit results
        total_count = len(filtered_items)
        showing_items = filtered_items[:limit]
        
        return render_template(
            'maintenance/base/action_creator_portal/search_template_actions.html',
            template_action_items=showing_items,
            total_count=total_count,
            showing=len(showing_items),
            search=search,
            maintenance_action_set_id=maintenance_action_set_id
        )
    except Exception as e:
        logger.error(f"Error in template actions search: {e}")
        return render_template(
            'maintenance/base/action_creator_portal/search_template_actions.html',
            template_action_items=[],
            total_count=0,
            showing=0,
            search=search or '',
            error=str(e)
        ), 500


@action_creator_portal_bp.route('/search-proto-actions')
@login_required
def search_proto_actions():
    """HTMX endpoint to return proto action search results"""
    try:
        search = request.args.get('search', '').strip().lower()
        limit = request.args.get('limit', type=int, default=8)
        maintenance_action_set_id = request.args.get('maintenance_action_set_id', type=int)
        
        # Get all proto actions
        proto_actions = ProtoActionItem.query.order_by(ProtoActionItem.action_name).all()
        
        # Filter by search term
        filtered_actions = []
        if search:
            for pa in proto_actions:
                if (search in pa.action_name.lower() or 
                    (pa.description and search in pa.description.lower())):
                    filtered_actions.append(pa)
        else:
            filtered_actions = proto_actions
        
        # Limit results
        total_count = len(filtered_actions)
        showing_actions = filtered_actions[:limit]
        
        return render_template(
            'maintenance/base/action_creator_portal/search_proto_actions.html',
            proto_actions=showing_actions,
            total_count=total_count,
            showing=len(showing_actions),
            search=search,
            maintenance_action_set_id=maintenance_action_set_id
        )
    except Exception as e:
        logger.error(f"Error in proto actions search: {e}")
        return render_template(
            'maintenance/base/action_creator_portal/search_proto_actions.html',
            proto_actions=[],
            total_count=0,
            showing=0,
            search=search or '',
            error=str(e)
        ), 500


@action_creator_portal_bp.route('/list-template-action-items/<int:template_action_set_id>')
@login_required
def list_template_action_items(template_action_set_id):
    """HTMX endpoint to return template action items for a specific template action set"""
    try:
        maintenance_action_set_id = request.args.get('maintenance_action_set_id', type=int)
        
        # Get template action set
        template_set = TemplateActionSet.query.get_or_404(template_action_set_id)
        
        # Get template action items ordered by sequence_order
        template_items = sorted(
            template_set.template_action_items,
            key=lambda tai: tai.sequence_order
        )
        
        return render_template(
            'maintenance/base/action_creator_portal/list_template_action_items.html',
            template_action_items=template_items,
            template_action_set=template_set,
            maintenance_action_set_id=maintenance_action_set_id
        )
    except Exception as e:
        logger.error(f"Error listing template action items: {e}")
        return render_template(
            'maintenance/base/action_creator_portal/list_template_action_items.html',
            template_action_items=[],
            template_action_set=None,
            error=str(e)
        ), 500

