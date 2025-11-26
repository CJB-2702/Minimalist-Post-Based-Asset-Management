from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from app.data.core.user_info.user import User
from app import db
from app.logger import get_logger

logger = get_logger("asset_management.auth")
auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        logger.debug(f"User {current_user.username} already authenticated, redirecting to main")
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        logger.debug(f"Login attempt for username: {username}")
        
        if not username or not password:
            logger.warning(f"Login attempt with missing credentials for username: {username}")
            flash('Please enter both username and password', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user is None or not user.check_password(password):
            logger.warning(f"Failed login attempt for username: {username}")
            flash('Invalid username or password', 'error')
            return render_template('auth/login.html')
        
        if not user.is_active:
            logger.warning(f"Login attempt for disabled account: {username}")
            flash('Account is disabled', 'error')
            return render_template('auth/login.html')
        
        login_user(user)
        logger.info(f"Successful login for user: {username}")
        
        # Redirect to next page or home
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('main.index')
        
        flash(f'Welcome, {user.username}!', 'success')
        return redirect(next_page)
    
    logger.debug("Login page accessed")
    return render_template('auth/login.html')

@auth.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    logger.info(f"User logged out: {username}")
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login')) 