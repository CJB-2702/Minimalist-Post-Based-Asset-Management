"""
Core Search Utilities Routes
Reusable HTMX searchbar endpoints for core entities used across the application.
"""

from flask import Blueprint, render_template, request
from flask_login import login_required
from app.logger import get_logger
from app.data.core.asset_info.asset import Asset
from app.data.core.asset_info.make_model import MakeModel
from app.data.core.asset_info.asset_type import AssetType
from app.data.core.event_info.event import Event
from app.data.core.user_info.user import User
from app.data.core.major_location import MajorLocation

logger = get_logger("asset_management.routes.core.searchutils")

searchutils_bp = Blueprint('searchutils', __name__, url_prefix='/core/searchutils')


@searchutils_bp.route('/assets')
@login_required
def searchbar_assets():
    """HTMX endpoint to return asset search results"""
    try:
        # Handle both parameter name variations
        name = request.args.get('name', '').strip() or request.args.get('search', '').strip()
        count = request.args.get('count', type=int, default=8)
        asset_type_id = request.args.get('asset_type_id', type=int)
        make_model_id = request.args.get('make_model_id', type=int)
        location_id = request.args.get('location_id', type=int)
        is_active = request.args.get('is_active', 'True')
        
        # Build query
        query = Asset.query
        
        # Apply filters
        if asset_type_id:
            query = query.join(MakeModel).filter(MakeModel.asset_type_id == asset_type_id)
        if make_model_id:
            query = query.filter(Asset.make_model_id == make_model_id)
        if location_id:
            query = query.filter(Asset.major_location_id == location_id)
        if is_active.lower() == 'true':
            query = query.filter(Asset.is_active == True)
        elif is_active.lower() == 'false':
            query = query.filter(Asset.is_active == False)
        if name:
            query = query.filter(
                (Asset.name.ilike(f'%{name}%')) |
                (Asset.serial_number.ilike(f'%{name}%'))
            )
        
        # Get total count before limiting
        total_count = query.count()
        
        # Apply limit
        assets = query.order_by(Asset.name).limit(count).all()
        
        # Format results for template
        items = []
        for asset in assets:
            items.append({
                'id': asset.id,
                'display_name': f"{asset.name}{' (' + asset.serial_number + ')' if asset.serial_number else ''}"
            })
        
        return render_template(
            'core/searchbars/simple_results.html',
            items=items,
            total_count=total_count,
            showing=len(items),
            search=name
        )
    except Exception as e:
        logger.error(f"Error in assets search: {e}")
        return render_template(
            'core/searchbars/simple_results.html',
            items=[],
            total_count=0,
            showing=0,
            search=name or '',
            error=str(e)
        ), 500


@searchutils_bp.route('/make-models')
@login_required
def searchbar_make_models():
    """HTMX endpoint to return make/model search results"""
    try:
        search = request.args.get('search', '').strip()
        count = request.args.get('count', type=int, default=8)
        asset_type_id = request.args.get('asset_type_id', type=int)
        is_active = request.args.get('is_active', type=bool, default=True)
        
        # Build query
        query = MakeModel.query
        
        # Apply filters
        if asset_type_id:
            query = query.filter(MakeModel.asset_type_id == asset_type_id)
        if is_active:
            query = query.filter(MakeModel.is_active == True)
        if search:
            query = query.filter(
                (MakeModel.make.ilike(f'%{search}%')) |
                (MakeModel.model.ilike(f'%{search}%'))
            )
        
        # Get total count before limiting
        total_count = query.count()
        
        # Apply limit
        make_models = query.order_by(MakeModel.make, MakeModel.model).limit(count).all()
        
        # Format results for template
        items = []
        for mm in make_models:
            display_name = f"{mm.make} {mm.model}"
            if mm.year:
                display_name += f" ({mm.year})"
            items.append({
                'id': mm.id,
                'display_name': display_name
            })
        
        return render_template(
            'core/searchbars/simple_results.html',
            items=items,
            total_count=total_count,
            showing=len(items),
            search=search
        )
    except Exception as e:
        logger.error(f"Error in make/models search: {e}")
        return render_template(
            'core/searchbars/simple_results.html',
            items=[],
            total_count=0,
            showing=0,
            search=search or '',
            error=str(e)
        ), 500


@searchutils_bp.route('/events')
@login_required
def searchbar_events():
    """HTMX endpoint to return event search results"""
    try:
        title = request.args.get('title', '').strip() or request.args.get('search', '').strip()
        count = request.args.get('count', type=int, default=8)
        event_type = request.args.get('event_type')
        asset_id = request.args.get('asset_id', type=int)
        status = request.args.get('status')
        
        # Build query
        query = Event.query
        
        # Apply filters
        if event_type:
            query = query.filter(Event.event_type == event_type)
        if asset_id:
            query = query.filter(Event.asset_id == asset_id)
        if status:
            query = query.filter(Event.status == status)
        if title:
            # Search in description (events don't have a title field, description is used)
            query = query.filter(Event.description.ilike(f'%{title}%'))
        
        # Get total count before limiting
        total_count = query.count()
        
        # Apply limit
        events = query.order_by(Event.timestamp.desc()).limit(count).all()
        
        # Format results for template
        items = []
        for event in events:
            # Truncate description for display
            display_name = event.description[:100] + "..." if len(event.description) > 100 else event.description
            display_name = f"{event.event_type}: {display_name}"
            items.append({
                'id': event.id,
                'display_name': display_name
            })
        
        return render_template(
            'core/searchbars/simple_results.html',
            items=items,
            total_count=total_count,
            showing=len(items),
            search=title
        )
    except Exception as e:
        logger.error(f"Error in events search: {e}")
        return render_template(
            'core/searchbars/simple_results.html',
            items=[],
            total_count=0,
            showing=0,
            search=title or '',
            error=str(e)
        ), 500


@searchutils_bp.route('/users')
@login_required
def searchbar_users():
    """HTMX endpoint to return user search results"""
    try:
        username = request.args.get('username', '').strip() or request.args.get('search', '').strip()
        count = request.args.get('count', type=int, default=8)
        is_active = request.args.get('is_active', type=bool, default=True)
        role = request.args.get('role')  # e.g., 'technician', 'admin'
        
        # Build query
        query = User.query
        
        # Apply filters
        if is_active:
            query = query.filter(User.is_active == True)
        if role:
            if role == 'admin':
                query = query.filter(User.is_admin == True)
            # Add other role filters as needed
        if username:
            query = query.filter(
                (User.username.ilike(f'%{username}%')) |
                (User.email.ilike(f'%{username}%'))
            )
        
        # Get total count before limiting
        total_count = query.count()
        
        # Apply limit
        users = query.order_by(User.username).limit(count).all()
        
        # Format results for template
        items = []
        for user in users:
            items.append({
                'id': user.id,
                'display_name': user.username
            })
        
        return render_template(
            'core/searchbars/simple_results.html',
            items=items,
            total_count=total_count,
            showing=len(items),
            search=username
        )
    except Exception as e:
        logger.error(f"Error in users search: {e}")
        return render_template(
            'core/searchbars/simple_results.html',
            items=[],
            total_count=0,
            showing=0,
            search=username or '',
            error=str(e)
        ), 500

