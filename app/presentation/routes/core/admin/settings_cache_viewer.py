"""
Settings Cache Viewer Routes
Secret simple CRUD pages for viewing and editing portal_user_data
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from app.logger import get_logger
from flask_login import login_required, current_user
from app.data.core.user_info.user import User
from app.data.core.user_info.portal_user_data import PortalUserData
from app import db
import json

bp = Blueprint('settings_cache_viewer', __name__)
logger = get_logger("asset_management.routes.core.admin.settings_cache_viewer")


def check_admin_or_owner(user_id):
    """
    Check if user is admin or accessing their own data.
    Aborts with 403 if neither condition is met.
    """
    if not current_user.is_authenticated:
        abort(403)
    
    # Allow if user is admin or accessing their own data
    if current_user.is_admin or current_user.id == user_id:
        return
    
    # Otherwise deny access
    logger.warning(f"Non-admin user {current_user.username} (ID: {current_user.id}) attempted to access settings-cache for user {user_id}")
    abort(403)


@bp.route('/<int:user_id>/settings-cache/view', methods=['GET', 'POST'])
@login_required
def view(user_id):
    """
    View portal_user_data for a user
    Requires admin access unless user_id matches current_user.id
    """
    check_admin_or_owner(user_id)
    user = User.query.get_or_404(user_id)
    
    # Get or create portal_data
    portal_data = PortalUserData.query.filter_by(user_id=user.id).first()
    if not portal_data:
        # Create portal_data if it doesn't exist
        portal_data = PortalUserData(
            user_id=user.id,
            general_settings={},
            core_settings={},
            maintenance_settings={},
            general_cache={},
            core_cache={},
            maintenance_cache={}
        )
        db.session.add(portal_data)
        db.session.commit()
        flash('Created portal_user_data record for user', 'info')
    
    # Format JSON data for display
    settings_data = {
        'general_settings': json.dumps(portal_data.general_settings or {}, indent=2),
        'core_settings': json.dumps(portal_data.core_settings or {}, indent=2),
        'maintenance_settings': json.dumps(portal_data.maintenance_settings or {}, indent=2),
    }
    
    cache_data = {
        'general_cache': json.dumps(portal_data.general_cache or {}, indent=2),
        'core_cache': json.dumps(portal_data.core_cache or {}, indent=2),
        'maintenance_cache': json.dumps(portal_data.maintenance_cache or {}, indent=2),
    }
    
    return render_template('core/admin/settings_cache_viewer/view.html',
                         user=user,
                         portal_data=portal_data,
                         settings_data=settings_data,
                         cache_data=cache_data)


@bp.route('/<int:user_id>/settings-cache/edit', methods=['GET', 'POST'])
@login_required
def edit(user_id):
    """
    Edit portal_user_data for a user
    Requires admin access unless user_id matches current_user.id
    """
    check_admin_or_owner(user_id)
    user = User.query.get_or_404(user_id)
    
    # Get or create portal_data
    portal_data = PortalUserData.query.filter_by(user_id=user.id).first()
    if not portal_data:
        # Create portal_data if it doesn't exist
        portal_data = PortalUserData(
            user_id=user.id,
            general_settings={},
            core_settings={},
            maintenance_settings={},
            general_cache={},
            core_cache={},
            maintenance_cache={}
        )
        db.session.add(portal_data)
        db.session.commit()
        flash('Created portal_user_data record for user', 'info')
    
    if request.method == 'POST':
        try:
            # Parse JSON from form fields
            settings_fields = ['general_settings', 'core_settings', 'maintenance_settings']
            cache_fields = ['general_cache', 'core_cache', 'maintenance_cache']
            
            # Update settings
            for field in settings_fields:
                field_value = request.form.get(field, '{}')
                try:
                    parsed_value = json.loads(field_value) if field_value else {}
                    setattr(portal_data, field, parsed_value)
                except json.JSONDecodeError as e:
                    flash(f'Invalid JSON in {field}: {str(e)}', 'error')
                    return render_template('core/admin/settings_cache_viewer/edit.html',
                                         user=user,
                                         portal_data=portal_data)
            
            # Update cache
            for field in cache_fields:
                field_value = request.form.get(field, '{}')
                try:
                    parsed_value = json.loads(field_value) if field_value else {}
                    setattr(portal_data, field, parsed_value)
                except json.JSONDecodeError as e:
                    flash(f'Invalid JSON in {field}: {str(e)}', 'error')
                    return render_template('core/admin/settings_cache_viewer/edit.html',
                                         user=user,
                                         portal_data=portal_data)
            
            # Update audit fields
            portal_data.updated_by_id = current_user.id
            
            db.session.commit()
            flash('Portal user data updated successfully', 'success')
            return redirect(url_for('settings_cache_viewer.view', user_id=user_id))
        
        except Exception as e:
            flash(f'Error updating portal user data: {str(e)}', 'error')
            logger.error(f"Error updating portal user data: {e}")
            db.session.rollback()
    
    # Format JSON data for editing
    settings_data = {
        'general_settings': json.dumps(portal_data.general_settings or {}, indent=2),
        'core_settings': json.dumps(portal_data.core_settings or {}, indent=2),
        'maintenance_settings': json.dumps(portal_data.maintenance_settings or {}, indent=2),
    }
    
    cache_data = {
        'general_cache': json.dumps(portal_data.general_cache or {}, indent=2),
        'core_cache': json.dumps(portal_data.core_cache or {}, indent=2),
        'maintenance_cache': json.dumps(portal_data.maintenance_cache or {}, indent=2),
    }
    
    return render_template('core/admin/settings_cache_viewer/edit.html',
                         user=user,
                         portal_data=portal_data,
                         settings_data=settings_data,
                         cache_data=cache_data)


@bp.route('/<int:user_id>/settings-cache/reset', methods=['POST'])
@login_required
def reset(user_id):
    """
    Reset portal_user_data to default (empty dicts)
    Requires admin access unless user_id matches current_user.id
    """
    check_admin_or_owner(user_id)
    user = User.query.get_or_404(user_id)
    
    # Get portal_data
    portal_data = PortalUserData.query.filter_by(user_id=user.id).first()
    if not portal_data:
        flash('No portal_user_data found for this user', 'warning')
        return redirect(url_for('settings_cache_viewer.view', user_id=user_id))
    
    try:
        # Reset all fields to empty dicts
        portal_data.general_settings = {}
        portal_data.core_settings = {}
        portal_data.maintenance_settings = {}
        portal_data.general_cache = {}
        portal_data.core_cache = {}
        portal_data.maintenance_cache = {}
        
        # Update audit fields
        portal_data.updated_by_id = current_user.id
        
        db.session.commit()
        flash('Portal user data reset successfully', 'success')
        return redirect(url_for('settings_cache_viewer.view', user_id=user_id))
    
    except Exception as e:
        flash(f'Error resetting portal user data: {str(e)}', 'error')
        logger.error(f"Error resetting portal user data: {e}")
        db.session.rollback()
        return redirect(url_for('settings_cache_viewer.view', user_id=user_id))

