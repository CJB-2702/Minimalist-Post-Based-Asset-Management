"""
Searchbar routes for portal navigation
Provides search functionality for portal names and routes
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
import json
from pathlib import Path
from app.logger import get_logger
from app.data.core.asset_info.asset import Asset
from app.data.core.asset_info.make_model import MakeModel
from app.data.core.major_location import MajorLocation
from app.data.core.user_info.user import User

logger = get_logger("asset_management.routes.searchbar")

# Create blueprint
searchbar_bp = Blueprint('searchbar', __name__)

def load_searchbar_routes():
    """Load searchbar routes from JSON file"""
    try:
        # Get the utils directory path
        utils_dir = Path(__file__).parent.parent.parent / 'utils'
        routes_file = utils_dir / 'searchbar_routes.json'
        
        if not routes_file.exists():
            logger.warning(f"Searchbar routes file not found at {routes_file}")
            return {}
        
        with open(routes_file, 'r', encoding='utf-8') as f:
            routes = json.load(f)
        
        return routes
    except Exception as e:
        logger.error(f"Error loading searchbar routes: {e}", exc_info=True)
        return {}

@searchbar_bp.route('/search')
@login_required
def search():
    """Global search across all entities and portal navigation"""
    query = request.args.get('q', '').strip()
    
    # Load searchbar routes for potential routes card
    searchbar_routes = load_searchbar_routes()
    
    # Filter searchbar routes based on query if provided
    filtered_routes = {}
    if searchbar_routes:
        if query:
            query_lower = query.lower()
            for category, routes in searchbar_routes.items():
                filtered_category = {}
                for route_name, route_info in routes.items():
                    searchable_text = f"{route_name} {route_info.get('name', '')} {route_info.get('description', '')} {category}".lower()
                    if query_lower in searchable_text:
                        filtered_category[route_name] = route_info
                if filtered_category:
                    filtered_routes[category] = filtered_category
        else:
            filtered_routes = searchbar_routes
    
    # If no query, show all routes card
    if not query:
        return render_template('search.html', 
                             results=None,
                             query='',
                             potential_routes=filtered_routes)
    
    # Search assets
    assets = Asset.query.filter(
        Asset.name.ilike(f'%{query}%') |
        Asset.serial_number.ilike(f'%{query}%')
    ).limit(10).all()
    
    # Search locations
    locations = MajorLocation.query.filter(
        MajorLocation.name.ilike(f'%{query}%') |
        MajorLocation.description.ilike(f'%{query}%')
    ).limit(10).all()
    
    # Search make/models
    make_models = MakeModel.query.filter(
        MakeModel.make.ilike(f'%{query}%') |
        MakeModel.model.ilike(f'%{query}%')
    ).limit(10).all()
    
    # Search users
    users = User.query.filter(
        User.username.ilike(f'%{query}%') |
        User.email.ilike(f'%{query}%')
    ).limit(10).all()
    
    results = {
        'assets': assets,
        'locations': locations,
        'make_models': make_models,
        'users': users
    }
    
    # Filter searchbar routes for matching routes
    if query and searchbar_routes:
        query_lower = query.lower()
        for category, routes in searchbar_routes.items():
            filtered_category = {}
            for route_name, route_info in routes.items():
                searchable_text = f"{route_name} {route_info.get('name', '')} {route_info.get('description', '')} {category}".lower()
                if query_lower in searchable_text:
                    filtered_category[route_name] = route_info
            if filtered_category:
                filtered_routes[category] = filtered_category
    
    return render_template('search.html', 
                         results=results, 
                         query=query,
                         potential_routes=filtered_routes)

@searchbar_bp.route('/api/searchbar/routes')
@login_required
def api_routes():
    """API endpoint to get all searchbar routes"""
    routes = load_searchbar_routes()
    return jsonify(routes)

@searchbar_bp.route('/searchbar/dropdown')
@login_required
def dropdown():
    """HTMX endpoint to return dropdown menu with routes"""
    # Get query from request args (HTMX sends it as 'q' parameter)
    query = request.args.get('q', '').strip().lower()
    routes = load_searchbar_routes()
    
    # Filter routes if query provided
    filtered_routes = {}
    if routes:
        if query:
            for category, category_routes in routes.items():
                filtered_category = {}
                for route_name, route_info in category_routes.items():
                    searchable_text = f"{route_name} {route_info.get('name', '')} {route_info.get('description', '')} {category}".lower()
                    if query in searchable_text:
                        filtered_category[route_name] = route_info
                if filtered_category:
                    filtered_routes[category] = filtered_category
        else:
            # Show all routes if no query
            filtered_routes = routes
    
    return render_template('searchbar/dropdown.html', routes=filtered_routes, query=query)
