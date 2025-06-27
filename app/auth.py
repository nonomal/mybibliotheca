from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash

# Import Kuzu graph models
from .graph_models import User, session as db

from wtforms import IntegerField, SubmitField
from wtforms.validators import Optional, NumberRange
from flask_wtf import FlaskForm
from .forms import (LoginForm, RegistrationForm, UserProfileForm, ChangePasswordForm,
                   PrivacySettingsForm, ForcedPasswordChangeForm, SetupForm, ReadingStreakForm)
from .debug_utils import debug_route, debug_auth, debug_csrf, debug_session
from datetime import datetime, timezone

auth = Blueprint('auth', __name__)

@auth.route('/setup', methods=['GET', 'POST'])
@debug_route('SETUP')
def setup():
    """Initial setup route for creating the first admin user"""
    debug_auth("Setup route accessed")
    
    # Check if any users already exist
    if User.query().count() > 0:
        debug_auth("Users already exist, redirecting to login")
        flash('Setup has already been completed.', 'info')
        return redirect(url_for('auth.login'))
    
    form = SetupForm()
    debug_auth("Setup form created")
    
    if form.validate_on_submit():
        debug_auth("Setup form submitted and validated")
        try:
            # Create the first admin user
            admin_user = User(
                username=form.username.data,
                email=form.email.data,
                is_admin=True,
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            admin_user.set_password(form.password.data)
            
            admin_user.save()
            
            debug_auth(f"First admin user created: {admin_user.username}")
            
            # Automatically log in the new admin user
            login_user(admin_user)
            
            flash('Setup completed successfully! Welcome to MyBibliotheca.', 'success')
            return redirect(url_for('main.index'))
            
        except Exception as e:
            debug_auth(f"Setup failed: {e}")
            flash('Setup failed. Please try again.', 'error')
    else:
        if request.method == 'POST':
            debug_auth(f"Setup form validation failed: {form.errors}")
    
    return render_template('auth/setup.html', title='Initial Setup', form=form)

@auth.route('/login', methods=['GET', 'POST'])
@debug_route('AUTH')
def login():
    debug_auth("Login route accessed")
    
    if current_user.is_authenticated:
        debug_auth("User already authenticated, redirecting to index")
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    debug_auth(f"Form created, CSRF token should be generated")
    
    # Debug CSRF token generation
    from flask_wtf.csrf import generate_csrf
    try:
        csrf_token = generate_csrf()
        debug_csrf(f"Generated CSRF token: {csrf_token[:10]}...")
    except Exception as e:
        debug_csrf(f"Error generating CSRF token: {e}")
    
    if form.validate_on_submit():
        debug_auth(f"Login form submitted for user: {form.username.data}")
        debug_csrf("Form validation passed, checking CSRF")
        
        # Try to find user by username or email
        user = User.query().filter_by(username=form.username.data).first()
        if not user:
            user = User.query().filter_by(email=form.username.data).first()
        
        if user:
            debug_auth(f"User found: {user.username} (ID: {user.id})")
            # Check if account is locked
            if user.is_locked():
                debug_auth("Account is locked")
                flash('Account is temporarily locked due to too many failed login attempts. Please try again later.', 'error')
                return redirect(url_for('auth.login'))
            
            # Check if account is active
            if not user.is_active:
                debug_auth("Account is inactive")
                flash('Your account has been deactivated. Please contact an administrator.', 'error')
                return redirect(url_for('auth.login'))
            
            # Check password
            if user.check_password(form.password.data):
                debug_auth("Password check passed")
                # Successful login
                user.reset_failed_login()
                login_user(user, remember=form.remember_me.data)
                debug_auth(f"User logged in successfully: {user.username}")
                
                # Update user login time
                user.update()
                debug_session("User updated after login")
                
                # Check if user must change password
                if user.password_must_change:
                    debug_auth("User must change password - redirecting to forced password change")
                    flash('You must change your password before continuing.', 'warning')
                    return redirect(url_for('auth.forced_password_change'))
                
                next_page = request.args.get('next')
                if not next_page or not next_page.startswith('/'):
                    next_page = url_for('main.index')
                debug_auth(f"Redirecting to: {next_page}")
                flash(f'Welcome back, {user.username}!', 'success')
                return redirect(next_page)
            else:
                debug_auth("Password check failed")
                # Failed password
                user.increment_failed_login()
                attempts_left = max(0, 5 - user.failed_login_attempts)
                if attempts_left > 0:
                    flash(f'Invalid password. You have {attempts_left} attempts remaining.', 'error')
                else:
                    flash('Account locked due to too many failed attempts. Please try again in 30 minutes.', 'error')
        else:
            debug_auth("User not found")
            # User not found
            flash('Invalid username/email or password', 'error')
    
    return render_template('auth/login.html', title='Sign In', form=form)

@auth.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    
    # Clear the session to ensure CSRF tokens are regenerated
    from flask import session as flask_session
    flask_session.clear()
    
    flash(f'Goodbye, {username}!', 'info')
    return redirect(url_for('main.index'))

@auth.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    # Only admin users can create new users
    if not current_user.is_admin:
        flash('Access denied. Only administrators can create new users.', 'error')
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(
                username=form.username.data,
                email=form.email.data
            )
            user.set_password(form.password.data)
            
            # Check if this is the very first user in the system
            if User.query().count() == 0:
                user.is_admin = True
                # First admin must change password on first login
                user.password_must_change = True
                flash('Congratulations! As the first user, you have been granted admin privileges. You must change your password on first login.', 'info')
            else:
                # New users created by admin should change password on first login
                user.password_must_change = True
            
            user.save()
            
            flash(f'User {user.username} has been created successfully! They will be required to change their password on first login.', 'success')
            return redirect(url_for('admin.users'))
        except ValueError as e:
            flash(str(e), 'error')
    
    return render_template('auth/register.html', title='Create New User', form=form)

@auth.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = UserProfileForm(current_user.username, current_user.email)
    
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.update()
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('auth.profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    
    return render_template('auth/profile.html', title='Profile', form=form)

@auth.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            try:
                current_user.set_password(form.new_password.data)
                current_user.update()
                flash('Your password has been changed.', 'success')
                return redirect(url_for('auth.profile'))
            except ValueError as e:
                flash(str(e), 'error')
        else:
            flash('Current password is incorrect.', 'error')
    
    return render_template('auth/change_password.html', title='Change Password', form=form)

@auth.route('/forced_password_change', methods=['GET', 'POST'])
@login_required
@debug_route('AUTH')
def forced_password_change():
    debug_auth("Forced password change route accessed")
    
    # If user doesn't need to change password, redirect to main page
    if not current_user.password_must_change:
        debug_auth("User doesn't need to change password, redirecting to index")
        return redirect(url_for('main.index'))
    
    form = ForcedPasswordChangeForm()
    
    if form.validate_on_submit():
        debug_auth("Forced password change form submitted")
        debug_csrf("Form validation passed for forced password change")
        
        try:
            current_user.set_password(form.new_password.data)
            current_user.update()
            debug_auth("Password changed successfully")
            flash('Your password has been changed successfully. You can now continue using the application.', 'success')
            return redirect(url_for('main.index'))
        except ValueError as e:
            debug_auth(f"Password validation failed: {e}")
            flash(str(e), 'error')
    else:
        if request.method == 'POST':
            debug_csrf("Form validation failed for forced password change")
            debug_csrf(f"Form errors: {form.errors}")
    
    debug_auth("Rendering forced password change template")
    return render_template('auth/forced_password_change.html', title='Change Required Password', form=form)

@auth.route('/debug_info')
@login_required
def debug_info():
    """Debug route to display comprehensive debug information (only if debug mode enabled)"""
    from .debug_utils import get_debug_info
    from flask import current_app, jsonify
    
    if not current_app.config.get('DEBUG_MODE', False):
        flash('Debug mode is not enabled.', 'error')
        return redirect(url_for('main.index'))
    
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))
    
    debug_data = get_debug_info()
    return jsonify(debug_data)

@auth.route('/privacy_settings', methods=['GET', 'POST'])
@login_required
def privacy_settings():
    from app.forms import PrivacySettingsForm, ReadingStreakForm
    
    form = PrivacySettingsForm()
    streak_form = ReadingStreakForm()
    
    # Populate forms with current values
    if request.method == 'GET':
        form.share_current_reading.data = current_user.share_current_reading
        form.share_reading_activity.data = current_user.share_reading_activity
        form.share_library.data = current_user.share_library
        streak_form.reading_streak_offset.data = current_user.reading_streak_offset
    
    if form.validate_on_submit():
        current_user.share_current_reading = form.share_current_reading.data
        current_user.share_reading_activity = form.share_reading_activity.data
        current_user.share_library = form.share_library.data
        current_user.update()
        flash('Privacy settings updated successfully!', 'success')
        return redirect(url_for('auth.privacy_settings'))
    
    return render_template('auth/privacy_settings.html', 
                         title='Privacy Settings', 
                         form=form, 
                         streak_form=streak_form)

@auth.route('/my_activity')
@login_required
def my_activity():
    from .graph_models import Book, ReadingLog
    
    # Get user's reading statistics
    total_books = Book.query().filter_by(user_id=current_user.id).count()
    
    # Get reading logs count
    reading_logs = ReadingLog.query().filter_by(user_id=current_user.id).count()
    
    # Get books added this year (simplified for Kuzu)
    current_year = datetime.now(timezone.utc).year
    all_books = Book.query().filter_by(user_id=current_user.id).all()
    books_this_year = len([b for b in all_books if b.created_at and b.created_at.year == current_year])
    
    # Get recent books (last 10)
    recent_books = Book.query().filter_by(user_id=current_user.id).limit(10).all()
    
    # Get recent reading logs (last 10)
    recent_logs = ReadingLog.query().filter_by(user_id=current_user.id).limit(10).all()
    
    return render_template('auth/my_activity.html', 
                         title='My Activity',
                         total_books=total_books,
                         reading_logs=reading_logs,
                         books_this_year=books_this_year,
                         recent_books=recent_books,
                         recent_logs=recent_logs)

@auth.route('/update_streak_settings', methods=['POST'])
@login_required
def update_streak_settings():
    form = ReadingStreakForm()
    
    if form.validate_on_submit():
        current_user.reading_streak_offset = form.reading_streak_offset.data or 0
        current_user.update()
        flash('Reading streak settings updated successfully!', 'success')
    else:
        flash('Error updating streak settings. Please try again.', 'danger')
    
    return redirect(url_for('auth.privacy_settings'))
