"""
Main routes for the Asset Management System
Dashboard and main navigation routes
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from app.logger import get_logger
from flask_login import login_required, current_user
from app.data.core.asset_info.asset import Asset
from app.data.core.asset_info.asset_type import AssetType
from app.data.core.asset_info.make_model import MakeModel
from app.data.core.major_location import MajorLocation
from app.data.core.user_info.user import User
from app.data.core.event_info.event import Event
from app import db

main = Blueprint('main', __name__)
logger = get_logger("asset_management.routes.main")

@main.route('/')
@login_required
def index():
    """Home page with navigation and basic stats"""
    # Get basic statistics
    total_assets = Asset.query.count()
    total_asset_types = AssetType.query.count()
    total_make_models = MakeModel.query.count()
    total_locations = MajorLocation.query.count()
    total_users = User.query.count()
    total_events = Event.query.count()
    
    # Get recent assets
    recent_assets = Asset.query.order_by(Asset.created_at.desc()).limit(5).all()
    
    # Get recent events
    recent_events = Event.query.order_by(Event.timestamp.desc()).limit(5).all()
    
    # Get assets by location
    locations_with_assets = []
    for location in MajorLocation.query.all():
        asset_count = Asset.query.filter_by(major_location_id=location.id).count()
        if asset_count > 0:
            locations_with_assets.append({
                'location': location,
                'asset_count': asset_count
            })
    
    # Get assets by type (through make/models)
    asset_types_with_counts = []
    for asset_type in AssetType.query.all():
        make_models = MakeModel.query.filter_by(asset_type_id=asset_type.id).all()
        asset_count = sum(Asset.query.filter_by(make_model_id=make_model.id).count() for make_model in make_models)
        if asset_count > 0:
            asset_types_with_counts.append({
                'asset_type': asset_type,
                'asset_count': asset_count
            })
    
    return render_template('index.html', 
                         total_assets=total_assets,
                         total_asset_types=total_asset_types,
                         total_make_models=total_make_models,
                         total_locations=total_locations,
                         total_users=total_users,
                         total_events=total_events,
                         recent_assets=recent_assets,
                         recent_events=recent_events,
                         locations_with_assets=locations_with_assets,
                         asset_types_with_counts=asset_types_with_counts)

@main.route('/dashboard')
@login_required
def dashboard():
    """Enhanced dashboard with more detailed statistics"""
    # Get comprehensive statistics
    stats = {
        'total_assets': Asset.query.count(),
        'active_assets': Asset.query.filter_by(status='Active').count(),
        'total_locations': MajorLocation.query.count(),
        'total_users': User.query.count(),
        'total_events': Event.query.count(),
        'total_asset_types': AssetType.query.count(),
        'total_make_models': MakeModel.query.count()
    }
    
    # Get recent activity
    recent_assets = Asset.query.order_by(Asset.created_at.desc()).limit(10).all()
    recent_events = Event.query.order_by(Event.timestamp.desc()).limit(10).all()
    
    # Get top locations by asset count
    locations = MajorLocation.query.all()
    location_stats = []
    for location in locations:
        asset_count = Asset.query.filter_by(major_location_id=location.id).count()
        location_stats.append({
            'location': location,
            'asset_count': asset_count
        })
    location_stats.sort(key=lambda x: x['asset_count'], reverse=True)
    
    # Get top asset types by count
    asset_type_stats = []
    for asset_type in AssetType.query.all():
        make_models = MakeModel.query.filter_by(asset_type_id=asset_type.id).all()
        asset_count = sum(Asset.query.filter_by(make_model_id=make_model.id).count() for make_model in make_models)
        asset_type_stats.append({
            'asset_type': asset_type,
            'asset_count': asset_count
        })
    asset_type_stats.sort(key=lambda x: x['asset_count'], reverse=True)
    
    return render_template('dashboard.html',
                         stats=stats,
                         recent_assets=recent_assets,
                         recent_events=recent_events,
                         location_stats=location_stats,
                         asset_type_stats=asset_type_stats)

@main.route('/search')
@login_required
def search():
    """Global search across all entities"""
    query = request.args.get('q', '')
    if not query:
        return render_template('search.html', results=None)
    
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
    
    return render_template('search.html', results=results, query=query)

@main.route('/help')
@login_required
def help():
    """Help and documentation page"""
    return render_template('help.html')

@main.route('/about')
@login_required
def about():
    """About page with system information"""
    return render_template('about.html') 





@main.route('/.well-known/appspecific/com.chrome.devtools.json')
def chrome_devtools():
    """Chrome DevTools configuration"""
    return  '{"name": "Asset Management System", "version": "1.0.0"}'