"""
User management routes
CRUD operations for User model
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from app.logger import get_logger
from flask_login import login_required, current_user
from app.data.core.user_info.user import User
from app.data.core.asset_info.asset import Asset
from app.data.core.event_info.event import Event
from app.data.core.major_location import MajorLocation
from app.data.core.asset_info.asset_type import AssetType
from app.buisness.core.user_context import UserContext
from app.services.core.user_service import UserService
from app.data.core.user_info.password_validator import PasswordValidator
from app import db

bp = Blueprint('users', __name__)
logger = get_logger("asset_management.routes.bp")

@bp.route('/users')
@login_required
def list():
    """List all users"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Use service to get list data
    users = UserService.get_list_data(
        request=request,
        page=page,
        per_page=per_page
    )
    
    return render_template('core/users/list.html', users=users)

# ROUTE_TYPE: SIMPLE_CRUD (GET)
# EXCEPTION: Direct ORM usage allowed for simple GET operations on User
# This route performs basic detail view operations with minimal business logic.
# Rationale: Simple detail view doesn't require domain abstraction.
# NOTE: CREATE/DELETE operations should use domain managers - see create() and delete() routes
@bp.route('/users/<int:user_id>')
@login_required
def detail(user_id):
    """View user details"""
    user = User.query.get_or_404(user_id)
    
    return render_template('core/users/detail.html', 
                         user=user,
                         Asset=Asset,
                         Event=Event,
                         MajorLocation=MajorLocation,
                         AssetType=AssetType)

@bp.route('/users/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new user using UserContext"""
    if request.method == 'POST':
        # Validate form data
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        is_admin = request.form.get('is_admin') == 'on'
        is_active = request.form.get('is_active') == 'on'
        
        # Validate password
        if not password:
            flash('Password is required', 'error')
            return render_template('core/users/create.html')
        
        # Use enhanced password validator
        is_valid, error_msg = PasswordValidator.validate(password)
        if not is_valid:
            flash(error_msg, 'error')
            return render_template('core/users/create.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('core/users/create.html')
        
        # Create user using UserContext (creates user + portal_user_data)
        try:
            user_context = UserContext.create(
                username=username,
                email=email,
                password=password,
                is_admin=is_admin,
                is_active=is_active,
                created_by_id=current_user.id,
                commit=True
            )
            
            flash('User created successfully', 'success')
            return redirect(url_for('users.detail', user_id=user_context.user_id))
        
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('core/users/create.html')
        except Exception as e:
            flash(f'Error creating user: {str(e)}', 'error')
            logger.error(f"Unexpected error creating user: {e}")
            db.session.rollback()
            return render_template('core/users/create.html')
    
    return render_template('core/users/create.html')

@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(user_id):
    """Edit user using UserContext"""
    user = User.query.get_or_404(user_id)
    user_context = UserContext(user)
    
    # Prevent editing system user
    if user.is_system:
        flash('System user cannot be edited', 'error')
        return redirect(url_for('users.detail', user_id=user.id))
    
    if request.method == 'POST':
        # Validate form data
        username = request.form.get('username')
        email = request.form.get('email')
        is_admin = request.form.get('is_admin') == 'on'
        is_active = request.form.get('is_active') == 'on'
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate password if provided
        if password:
            # Use enhanced password validator with history checking
            is_valid, error_msg = PasswordValidator.validate(password, user=user, check_history=True)
            if not is_valid:
                flash(error_msg, 'error')
                return render_template('core/users/edit.html', 
                                     user=user,
                                     Asset=Asset,
                                     Event=Event,
                                     MajorLocation=MajorLocation,
                                     AssetType=AssetType)
            
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return render_template('core/users/edit.html', 
                                     user=user,
                                     Asset=Asset,
                                     Event=Event,
                                     MajorLocation=MajorLocation,
                                     AssetType=AssetType)
        
        # Update user using UserContext
        try:
            update_data = {
                'username': username,
                'email': email,
                'is_admin': is_admin,
                'is_active': is_active
            }
            
            if password:
                update_data['password'] = password
            
            user_context.update(
                updated_by_id=current_user.id,
                commit=True,
                **update_data
            )
            
            flash('User updated successfully', 'success')
            return redirect(url_for('users.detail', user_id=user.id))
        
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('core/users/edit.html', 
                                 user=user,
                                 Asset=Asset,
                                 Event=Event,
                                 MajorLocation=MajorLocation,
                                 AssetType=AssetType)
        except Exception as e:
            flash(f'Error updating user: {str(e)}', 'error')
            logger.error(f"Unexpected error updating user: {e}")
            db.session.rollback()
            return render_template('core/users/edit.html', 
                                 user=user,
                                 Asset=Asset,
                                 Event=Event,
                                 MajorLocation=MajorLocation,
                                 AssetType=AssetType)
    
    return render_template('core/users/edit.html', 
                         user=user,
                         Asset=Asset,
                         Event=Event,
                         MajorLocation=MajorLocation,
                         AssetType=AssetType)

@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete(user_id):
    """Delete user using UserContext"""
    user = User.query.get_or_404(user_id)
    user_context = UserContext(user)
    
    # Prevent deleting system user or self
    if user.is_system:
        flash('System user cannot be deleted', 'error')
        return redirect(url_for('users.detail', user_id=user.id))
    
    if user.id == current_user.id:
        flash('Cannot delete your own account', 'error')
        return redirect(url_for('users.detail', user_id=user.id))
    
    # Delete user using UserContext
    try:
        user_context.delete(
            deleted_by_id=current_user.id,
            commit=True
        )
        flash('User deleted successfully', 'success')
        return redirect(url_for('users.list'))
    
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('users.detail', user_id=user.id))
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'error')
        logger.error(f"Unexpected error deleting user: {e}")
        db.session.rollback()
        return redirect(url_for('users.detail', user_id=user.id)) 