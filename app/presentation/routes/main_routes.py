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
from app.data.dispatching.request import DispatchRequest
from app.data.dispatching.outcomes.standard_dispatch import StandardDispatch
from app.data.dispatching.outcomes.contract import Contract
from app.data.dispatching.outcomes.reimbursement import Reimbursement
from app import db

# Import the main blueprint from the package
from . import main

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

@main.route('/asset-management')
@login_required
def asset_management():
    """Asset management dashboard with detailed statistics and recent activity"""
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
        # Get make_models for this asset type
        make_models = MakeModel.query.filter_by(asset_type_id=asset_type.id).all()
        asset_count = sum(Asset.query.filter_by(make_model_id=make_model.id).count() for make_model in make_models)
        if asset_count > 0:
            asset_types_with_counts.append({
                'asset_type': asset_type,
                'asset_count': asset_count
            })
    
    return render_template('assets/index.html', 
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
    # Get comprehensive statistics - using variable names expected by template
    assets_count = Asset.query.count()
    asset_types_count = AssetType.query.count()
    make_models_count = MakeModel.query.count()
    events_count = Event.query.count()
    
    stats = {
        'total_assets': assets_count,
        'active_assets': Asset.query.filter_by(status='Active').count(),
        'total_locations': MajorLocation.query.count(),
        'total_users': User.query.count(),
        'total_events': events_count,
        'total_asset_types': asset_types_count,
        'total_make_models': make_models_count
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
        # Get make_models for this asset type
        make_models = MakeModel.query.filter_by(asset_type_id=asset_type.id).all()
        asset_count = sum(Asset.query.filter_by(make_model_id=make_model.id).count() for make_model in make_models)
        asset_type_stats.append({
            'asset_type': asset_type,
            'asset_count': asset_count
        })
    asset_type_stats.sort(key=lambda x: x['asset_count'], reverse=True)
    
    return render_template('dashboard.html',
                         stats=stats,
                         assets_count=assets_count,
                         asset_types_count=asset_types_count,
                         make_models_count=make_models_count,
                         events_count=events_count,
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

@main.route('/logs')
@login_required
def logs():
    """Log viewer page"""
    logger = get_logger()
    logger.debug(f"User {current_user.username} accessing log viewer")
    
    # Get query parameters for filtering and sorting
    sort_by = request.args.get('sort_by', 'line')  # level, module, function, line, message
    sort_order = request.args.get('sort_order', 'desc')  # asc, desc
    level_filter = request.args.get('level', '')  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    module_filter = request.args.get('module', '')  # module name
    function_filter = request.args.get('function', '')  # function name
    message_filter = request.args.get('message', '')  # message content
    limit = request.args.get('limit', 100, type=int)  # number of entries to show
    
    # Read log file and convert to valid JSON
    import json
    from pathlib import Path
    
    logs_dir = Path('logs')
    log_file = logs_dir / 'asset_management.log'
    
    logs_data = []
    if log_file.exists():
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
                
            # Convert to valid JSON array
            valid_logs = []
            for line_num, line in enumerate(lines):
                try:
                    log_entry = json.loads(line)
                    log_entry['index'] = line_num + 1
                    valid_logs.append(log_entry)
                except json.JSONDecodeError:
                    # Skip invalid JSON lines
                    continue
            
            # Apply filters
            filtered_logs = []
            for log in valid_logs:
                # Level filter
                if level_filter and log.get('level') != level_filter:
                    continue
                # Module filter
                if module_filter and module_filter.lower() not in log.get('module', '').lower():
                    continue
                # Function filter
                if function_filter and function_filter.lower() not in log.get('function', '').lower():
                    continue
                # Message filter
                if message_filter and message_filter.lower() not in log.get('message', '').lower():
                    continue
                filtered_logs.append(log)
            
            # Apply sorting
            reverse_sort = sort_order == 'index'
            if sort_by == 'index':
                filtered_logs.sort(key=lambda x: x.get('index', ''), reverse=reverse_sort)
            elif sort_by == 'level':
                filtered_logs.sort(key=lambda x: x.get('level', ''), reverse=reverse_sort)
            elif sort_by == 'module':
                filtered_logs.sort(key=lambda x: x.get('module', ''), reverse=reverse_sort)
            elif sort_by == 'function':
                filtered_logs.sort(key=lambda x: x.get('function', ''), reverse=reverse_sort)
            elif sort_by == 'line':
                filtered_logs.sort(key=lambda x: int(x.get('line', 0)), reverse=reverse_sort)
            elif sort_by == 'message':
                filtered_logs.sort(key=lambda x: x.get('message', ''), reverse=reverse_sort)
            else:
                # Default sort by line number
                filtered_logs.sort(key=lambda x: int(x.get('line', 0)), reverse=reverse_sort)
            
            # Apply limit
            logs_data = filtered_logs[:limit]
            
        except Exception as e:
            logger.error(f"Error reading log file: {e}")
    
    # Get unique values for filter dropdowns
    unique_levels = sorted(list(set(log.get('level') for log in logs_data)))
    unique_modules = sorted(list(set(log.get('module') for log in logs_data)))
    unique_functions = sorted(list(set(log.get('function') for log in logs_data)))
    
    return render_template('logs_table.html', 
                         logs=logs_data,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         level_filter=level_filter,
                         module_filter=module_filter,
                         function_filter=function_filter,
                         message_filter=message_filter,
                         limit=limit,
                         unique_levels=unique_levels,
                         unique_modules=unique_modules,
                         unique_functions=unique_functions)

@main.route('/api/logs')
@login_required
def api_logs():
    """API endpoint to get log data"""
    import json
    from pathlib import Path
    from datetime import datetime
    from flask import jsonify, request
    
    # Get query parameters for filtering
    log_type = request.args.get('type', 'asset_management')  # asset_management or errors
    limit = request.args.get('limit', 100, type=int)
    level = request.args.get('level', '')  # DEBUG, INFO, WARNING, ERROR
    logger_name = request.args.get('logger', '')  # specific logger name
    search = request.args.get('search', '')  # text search
    
    logger.debug(f"Log API request - Type: {log_type}, Limit: {limit}, Level: {level}, Logger: {logger_name}")
    
    # Find the most recent log file
    logs_dir = Path('logs')
    if not logs_dir.exists():
        return jsonify({'logs': [], 'error': 'Logs directory not found'})
    
    # Use fixed filenames for the simplified logger
    if log_type == 'errors':
        log_file = logs_dir / 'errors.log'
    else:
        log_file = logs_dir / 'asset_management.log'
    
    if not log_file.exists():
        return jsonify({'logs': [], 'error': f'Log file not found: {log_file.name}'})
    
    logs_data = []
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    try:
                        log_entry = json.loads(line.strip())
                        
                        # Apply filters
                        if level and log_entry.get('level') != level:
                            continue
                        if logger_name and logger_name not in log_entry.get('module', ''):
                            continue
                        if search and search.lower() not in log_entry.get('message', '').lower():
                            continue
                        
                        # Add line number for reference
                        log_entry['line_number'] = line_num
                        logs_data.append(log_entry)
                        
                        # Limit results
                        if len(logs_data) >= limit:
                            break
                            
                    except json.JSONDecodeError:
                        # Skip invalid JSON lines
                        continue
        
        # Reverse to show newest first
        logs_data.reverse()
        
        logger.info(f"Log API returned {len(logs_data)} log entries from {log_file.name}")
        return jsonify({
            'logs': logs_data,
            'log_file': log_file.name,
            'total_entries': len(logs_data),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        return jsonify({'logs': [], 'error': str(e)}) 