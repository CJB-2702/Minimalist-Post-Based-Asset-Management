from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from app.data.core.user_info.user import User
from app import db, limiter
from app.logger import get_logger

logger = get_logger("asset_management.auth")
auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # Rate limit: max 5 login attempts per minute per IP
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
        
        # Check if account exists
        if user is None:
            logger.warning(f"Failed login attempt for non-existent username: {username}")
            flash('Invalid username or password', 'error')
            return render_template('auth/login.html')
        
        # Check if account is locked
        if user.is_locked():
            from datetime import datetime
            minutes_remaining = int((user.locked_until - datetime.utcnow()).total_seconds() / 60)
            logger.warning(f"Login attempt for locked account: {username}")
            flash(f'Account is locked due to multiple failed login attempts. Please try again in {minutes_remaining} minutes.', 'error')
            return render_template('auth/login.html')
        
        # Check if account is active
        if not user.is_active:
            logger.warning(f"Login attempt for disabled account: {username}")
            flash('Account is disabled', 'error')
            return render_template('auth/login.html')
        
        # Check password
        if not user.check_password(password):
            logger.warning(f"Failed login attempt for username: {username}")
            user.increment_failed_login()
            db.session.commit()
            
            remaining_attempts = 5 - user.failed_login_attempts
            if remaining_attempts > 0:
                flash(f'Invalid username or password. {remaining_attempts} attempts remaining before account lockout.', 'error')
            else:
                flash('Account locked due to multiple failed login attempts. Please contact an administrator.', 'error')
            
            return render_template('auth/login.html')
        
        # Check if password is expired
        if user.is_password_expired():
            logger.info(f"Login with expired password for user: {username}")
            flash('Your password has expired. Please change your password.', 'warning')
            # TODO: Redirect to password change page
            # For now, allow login but show warning
        else:
            # Check if password is expiring soon (within 7 days)
            days_remaining = user.days_until_password_expires()
            if days_remaining is not None and days_remaining <= 7:
                flash(f'Your password will expire in {days_remaining} days. Please change it soon.', 'warning')
        
        # Successful login - reset failed attempts
        user.reset_failed_login()
        login_user(user)
        db.session.commit()
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