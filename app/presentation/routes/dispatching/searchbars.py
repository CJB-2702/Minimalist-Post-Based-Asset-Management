"""
Search bars for dispatching module
"""
from flask import render_template, request
from flask_login import login_required
from app import db
from app.logger import get_logger
from sqlalchemy import or_

# Import dispatching_bp from main module
from app.presentation.routes.dispatching import dispatching_bp

logger = get_logger("asset_management.routes.dispatching.searchbars")


# User search for request form
@dispatching_bp.route('/search-bars/users')
@login_required
def search_bars_users():
    """HTMX endpoint to return user search results"""
    try:
        from app.data.core.user_info.user import User
        
        search = request.args.get('search', '').strip()
        limit = request.args.get('limit', type=int, default=10)
        selected_user_id = request.args.get('selected_user_id', type=int)
        
        # Query active users only
        query = User.query.filter(User.is_active == True)
        
        if search:
            query = query.filter(
                db.or_(
                    User.username.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%'),
                    User.first_name.ilike(f'%{search}%'),
                    User.last_name.ilike(f'%{search}%')
                )
            )
        
        users = query.order_by(User.username).limit(limit).all()
        total_count = query.count()
        
        return render_template(
            'dispatching/search_bars/users_results.html',
            users=users,
            total_count=total_count,
            showing=len(users),
            search=search,
            selected_user_id=selected_user_id
        )
    except Exception as e:
        logger.error(f"Error in users search: {e}")
        return render_template(
            'dispatching/search_bars/users_results.html',
            users=[],
            total_count=0,
            showing=0,
            search=search or '',
            error=str(e)
        ), 500
