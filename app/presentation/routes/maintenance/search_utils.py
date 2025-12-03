"""
Maintenance Search Utilities Routes
Reusable HTMX searchbar endpoints for maintenance-specific entities.
"""

from flask import Blueprint, render_template, request
from flask_login import login_required
from app.logger import get_logger
from app.data.maintenance.templates.template_action_sets import TemplateActionSet
from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem
from app.data.core.asset_info.asset_type import AssetType
from app.data.core.asset_info.make_model import MakeModel

logger = get_logger("asset_management.routes.maintenance.search_utils")

maintenance_searchutils_bp = Blueprint('maintenance_searchutils', __name__, url_prefix='/maintenance/searchutils')


@maintenance_searchutils_bp.route('/template-action-set')
@login_required
def searchbar_template_action_set():
    """HTMX endpoint to return template action set search results"""
    try:
        # Handle both parameter name variations
        name = request.args.get('name', '').strip() or request.args.get('search', '').strip()
        count = request.args.get('count', type=int, default=8)
        asset_type_id = request.args.get('asset_type_id', type=int)
        make_model_id = request.args.get('make_model_id', type=int)
        is_active = request.args.get('is_active', type=bool, default=True)
        
        # Build query
        query = TemplateActionSet.query
        
        # Apply filters
        if is_active:
            query = query.filter(TemplateActionSet.is_active == True)
        if asset_type_id:
            query = query.filter(TemplateActionSet.asset_type_id == asset_type_id)
        if make_model_id:
            query = query.filter(TemplateActionSet.make_model_id == make_model_id)
        if name:
            query = query.filter(TemplateActionSet.task_name.ilike(f'%{name}%'))
        
        # Get total count before limiting
        total_count = query.count()
        
        # Apply limit
        templates = query.order_by(TemplateActionSet.task_name).limit(count).all()
        
        # Format results for template
        items = []
        for template in templates:
            display_name = template.task_name
            if template.revision:
                display_name += f" (Rev. {template.revision})"
            items.append({
                'id': template.id,
                'display_name': display_name,
                'task_name': template.task_name,
                'revision': template.revision,
                'description': template.description
            })
        
        return render_template(
            'maintenance/searchbars/template_action_set_results.html',
            items=items,
            total_count=total_count,
            showing=len(items),
            search=name
        )
    except Exception as e:
        logger.error(f"Error in template action set search: {e}")
        return render_template(
            'maintenance/searchbars/template_action_set_results.html',
            items=[],
            total_count=0,
            showing=0,
            search=name or '',
            error=str(e)
        ), 500


@maintenance_searchutils_bp.route('/proto-action')
@login_required
def searchbar_proto_action():
    """HTMX endpoint to return proto action search results"""
    try:
        name = request.args.get('name', '').strip() or request.args.get('search', '').strip()
        count = request.args.get('count', type=int, default=8)
        category = request.args.get('category')
        is_active = request.args.get('is_active', type=bool, default=True)
        
        # Build query
        query = ProtoActionItem.query
        
        # Apply filters
        # Note: ProtoActionItem doesn't have is_active field based on the model
        # If needed, this can be added later
        if category:
            # ProtoActionItem may have a category field - adjust based on actual model
            # For now, we'll search in action_name and description
            pass
        if name:
            query = query.filter(
                (ProtoActionItem.action_name.ilike(f'%{name}%')) |
                (ProtoActionItem.description.ilike(f'%{name}%'))
            )
        
        # Get total count before limiting
        total_count = query.count()
        
        # Apply limit
        proto_actions = query.order_by(ProtoActionItem.action_name).limit(count).all()
        
        # Format results for template
        items = []
        for proto_action in proto_actions:
            items.append({
                'id': proto_action.id,
                'display_name': proto_action.action_name,
                'action_name': proto_action.action_name,
                'description': proto_action.description
            })
        
        return render_template(
            'maintenance/searchbars/proto_action_results.html',
            items=items,
            total_count=total_count,
            showing=len(items),
            search=name
        )
    except Exception as e:
        logger.error(f"Error in proto action search: {e}")
        return render_template(
            'maintenance/searchbars/proto_action_results.html',
            items=[],
            total_count=0,
            showing=0,
            search=name or '',
            error=str(e)
        ), 500

