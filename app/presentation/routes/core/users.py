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
from app import db

bp = Blueprint('users', __name__)
logger = get_logger("asset_management.routes.bp")

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from app.logger import get_logger
from flask_login import login_required, current_user
from app.data.core.user_info.user import User
from app.data.core.asset_info.asset import Asset
from app.data.core.event_info.event import Event
from app.data.core.major_location import MajorLocation
from app.data.core.asset_info.asset_type import AssetType
from app.services.core.user_service import UserService
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
    """Create new user"""
    if request.method == 'POST':
        # Validate form data
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        is_admin = request.form.get('is_admin') == 'on'
        is_active = request.form.get('is_active') == 'on'
        
        # Validate password
        if not password or len(password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return render_template('core/users/create.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('core/users/create.html')
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('core/users/create.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('core/users/create.html')
        
        # Create new user
        user = User(
            username=username,
            email=email,
            is_admin=is_admin,
            is_active=is_active
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('User created successfully', 'success')
        return redirect(url_for('users.detail', user_id=user.id))
    
    return render_template('core/users/create.html')

# ROUTE_TYPE: SIMPLE_CRUD (EDIT)
# EXCEPTION: Direct ORM usage allowed for simple EDIT operations on User
# This route performs basic update operations with minimal business logic.
# Rationale: Simple user update doesn't require domain abstraction.
# NOTE: CREATE/DELETE operations should use domain managers - see create() and delete() routes
@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(user_id):
    """Edit user"""
    user = User.query.get_or_404(user_id)
    
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
            if len(password) < 8:
                flash('Password must be at least 8 characters long', 'error')
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
        
        # Check if username or email already exists (excluding current user)
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != user.id:
            flash('Username already exists', 'error')
            return render_template('core/users/edit.html', 
                                 user=user,
                                 Asset=Asset,
                                 Event=Event,
                                 MajorLocation=MajorLocation,
                                 AssetType=AssetType)
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != user.id:
            flash('Email already exists', 'error')
            return render_template('core/users/edit.html', 
                                 user=user,
                                 Asset=Asset,
                                 Event=Event,
                                 MajorLocation=MajorLocation,
                                 AssetType=AssetType)
        
        # Update user
        user.username = username
        user.email = email
        user.is_admin = is_admin
        user.is_active = is_active
        
        if password:
            user.set_password(password)
        
        db.session.commit()
        
        flash('User updated successfully', 'success')
        return redirect(url_for('users.detail', user_id=user.id))
    
    return render_template('core/users/edit.html', 
                         user=user,
                         Asset=Asset,
                         Event=Event,
                         MajorLocation=MajorLocation,
                         AssetType=AssetType)

@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete(user_id):
    """Delete user"""
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting system user or self
    if user.is_system:
        flash('System user cannot be deleted', 'error')
        return redirect(url_for('users.detail', user_id=user.id))
    
    if user.id == current_user.id:
        flash('Cannot delete your own account', 'error')
        return redirect(url_for('users.detail', user_id=user.id))
    
    # Check if user has created any entities
    if Asset.query.filter_by(created_by_id=user.id).count() > 0:
        flash('Cannot delete user with created assets', 'error')
        return redirect(url_for('users.detail', user_id=user.id))
    
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted successfully', 'success')
    return redirect(url_for('users.list')) 