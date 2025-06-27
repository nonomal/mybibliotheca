import os
import shutil
from datetime import datetime
from flask import Flask, session
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config

# Kuzu is now required - app will not start without it
try:
    import kuzu
    from kuzu_config import kuzu_db
    from .graph_models import User, session as db_session
except ImportError as e:
    print("\n" + "="*80)
    print("❌ KUZU GRAPH DATABASE REQUIRED")
    print("="*80)
    print("MyBibliotheca now requires Kuzu graph database to run.")
    print("")
    print("🚀 Quick Setup:")
    print("  1. Run: ./setup_kuzu_migration.sh")
    print("  2. Run: ./migrate_to_kuzu.sh")
    print("  3. Restart your app")
    print("")
    print("📖 See VENV_MIGRATION_GUIDE.md for detailed instructions")
    print("="*80)
    raise ImportError(f"Kuzu is required but not available: {e}")

login_manager = LoginManager()
csrf = CSRFProtect()

@login_manager.user_loader
def load_user(user_id):
    return User.get(int(user_id))

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['SECRET_KEY'] = 'your-secret-key'

    # Initialize debug utilities
    from .debug_utils import setup_debug_logging, print_debug_banner, debug_middleware
    
    with app.app_context():
        setup_debug_logging()
        print_debug_banner()

    # Initialize extensions
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Initialize Kuzu Graph Database
    print("🔄 Initializing Kuzu Graph Database...")
    if not kuzu_db.connect():
        print("❌ Failed to connect to Kuzu database")
        print("🔧 Try running the migration: ./migrate_to_kuzu.sh")
        raise Exception("Failed to initialize Kuzu database")
    
    # Create schema if needed
    try:
        kuzu_db.create_schema()
        print("✅ Kuzu database initialized successfully")
    except Exception as e:
        print(f"⚠️ Schema may already exist: {e}")
    
    # Setup middleware for user checks
    @app.before_request
    def check_kuzu_setup():
        from flask import request, redirect, url_for
        from flask_login import current_user
        from .debug_utils import debug_middleware
        
        # Run debug middleware if enabled
        debug_middleware()
        
        # Check if setup is needed (no users exist)
        if User.query().count() == 0:
            # Skip for setup route and static files
            if request.endpoint in ['auth.setup', 'static'] or (request.endpoint and request.endpoint.startswith('static')):
                return
            # Redirect to setup page
            return redirect(url_for('auth.setup'))
        
        # Skip if user is not authenticated
        if not current_user.is_authenticated:
            return
        
        # Check if user must change password
        if hasattr(current_user, 'password_must_change') and current_user.password_must_change:
            if request.endpoint != 'auth.forced_password_change':
                return redirect(url_for('auth.forced_password_change'))

    # Register blueprints
    from .routes import bp
    from .auth import auth
    from .admin import admin
    app.register_blueprint(bp)
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(admin, url_prefix='/admin')

    return app

    # Database initialization based on configuration
    if app.config.get('USE_KUZU', True):
        # Initialize Kuzu Graph Database
        print("� Initializing Kuzu Graph Database...")
        if not kuzu_db.connect():
            print("❌ Failed to connect to Kuzu database")
            raise Exception("Failed to initialize Kuzu database")
        
        # Create schema if needed
        try:
            kuzu_db.create_schema()
            print("✅ Kuzu database initialized successfully")
        except Exception as e:
            print(f"⚠️ Schema may already exist: {e}")
        
        # Check if setup is needed
        with app.app_context():
            @app.before_request
            def check_kuzu_setup():
                from flask import request, redirect, url_for
                from flask_login import current_user
                from .debug_utils import debug_middleware
                
                # Run debug middleware if enabled
                debug_middleware()
                
                # Check if setup is needed (no users exist)
                if User.query().count() == 0:
                    # Skip for setup route and static files
                    if request.endpoint in ['auth.setup', 'static'] or (request.endpoint and request.endpoint.startswith('static')):
                        return
                    # Redirect to setup page
                    return redirect(url_for('auth.setup'))
                
                # Skip if user is not authenticated
                if not current_user.is_authenticated:
                    return
                
                # Check if user must change password
                if hasattr(current_user, 'password_must_change') and current_user.password_must_change:
                    if request.endpoint != 'auth.forced_password_change':
                        return redirect(url_for('auth.forced_password_change'))
    
    else:
        # Legacy SQLAlchemy initialization (for migration period)
        db.init_app(app)
        
        # Include existing migration logic for SQLAlchemy
        with app.app_context():
            # ... existing SQLAlchemy migration code ...
            pass

    # Register blueprints
    from .routes import bp
    from .auth import auth
    from .admin import admin
    app.register_blueprint(bp)
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(admin, url_prefix='/admin')

    return app
