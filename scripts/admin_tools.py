#!/usr/bin/env python3
"""
MyBibliotheca Admin Tools
Command-line utilities for administrative tasks

Available commands:
- reset-admin-password: Reset the admin user password
- create-admin: Create a new admin user
- promote-user: Grant admin privileges to a user
- list-users: List all users in the system
- system-stats: Display system statistics
"""

import os
import sys
import argparse
import getpass
from datetime import datetime, timezone

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    from app.domain.models import User
    from app.services import user_service
    from config import Config
except ImportError as e:
    print(f"❌ Error importing application modules: {e}")
    print("🔧 Make sure you're running this from the MyBibliotheca directory")
    sys.exit(1)

def validate_password(password):
    """Validate password meets security requirements"""
    return User.is_password_strong(password), "Password meets security requirements" if User.is_password_strong(password) else "Password does not meet security requirements"

def get_secure_password(prompt="Enter new password: "):
    """Get a password from user input with validation"""
    print("\n📋 Password Requirements:")
    for req in User.get_password_requirements():
        print(f"  • {req}")
    print()
    
    while True:
        password = getpass.getpass(prompt)
        
        if not password:
            print("❌ Password cannot be empty")
            continue
            
        is_valid, message = validate_password(password)
        if not is_valid:
            print(f"❌ {message}")
            continue
            
        # Confirm password
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("❌ Passwords do not match")
            continue
            
        return password

def reset_admin_password(args):
    """Reset the admin user password"""
    app = create_app()
    
    with app.app_context():
        # Use the Kuzu-based user service
        
        # Find admin user
        all_users = user_service.get_all_users_sync()
        admin_users = [u for u in all_users if u.is_admin]
        
        if not admin_users:
            print("❌ No admin user found in the database")
            print("💡 Use 'create-admin' command to create an admin user first")
            return False
        
        admin_user = admin_users[0]  # Use first admin user
        print(f"🔧 Resetting password for admin user: {admin_user.username}")
        
        if args.password:
            # Use provided password
            password = args.password
            is_valid, message = validate_password(password)
            if not is_valid:
                print(f"❌ {message}")
                return False
        else:
            # Get password interactively
            password = get_secure_password()
        
        # Update password
        try:
            updated_user = User(
                id=admin_user.id,
                username=admin_user.username,
                email=admin_user.email,
                is_admin=admin_user.is_admin,
                is_active=admin_user.is_active,
                password_hash=User.hash_password(password),
                created_at=admin_user.created_at,
                last_login=admin_user.last_login
            )
            
            user_service.update_user_sync(updated_user)
            
            print(f"✅ Password reset successful for admin user: {admin_user.username}")
            print(f"📧 Email: {admin_user.email}")
            print("🔒 Please store the new password securely")
            
            return True
        except Exception as e:
            print(f"❌ Password validation failed: {e}")
            return False

def create_admin(args):
    """Create a new admin user"""
    app = create_app()
    
    with app.app_context():
        # Import Kuzu services
        from werkzeug.security import generate_password_hash
        
        try:
            # Use the Kuzu-based user service
            
            # Check if admin already exists
            user_count = user_service.get_user_count_sync()
            # Note: we can't easily check for existing admin in Redis without getting all users
            # So we'll check if any users exist and warn accordingly
            if user_count > 0 and not args.force:
                print(f"❌ Users already exist in the system ({user_count} total)")
                print("💡 Use --force to create additional admin user")
                print("💡 Use 'promote-user' to make existing user an admin")
                return False
            
            # Get user details
            if args.username:
                username = args.username
            else:
                username = input("Enter admin username: ").strip()
                
            if args.email:
                email = args.email
            else:
                email = input("Enter admin email: ").strip()
            
            # Validate username and email
            if not username or len(username) < 3:
                print("❌ Username must be at least 3 characters long")
                return False
                
            if not email or '@' not in email:
                print("❌ Please provide a valid email address")
                return False
            
            # Check for existing user
            existing_user = user_service.get_user_by_username_sync(username)
            if existing_user:
                print(f"❌ Username '{username}' already exists")
                return False
                
            existing_email = user_service.get_user_by_email_sync(email)
            if existing_email:
                print(f"❌ Email '{email}' already exists")
                return False
            
            # Get password
            if args.password:
                password = args.password
                is_valid, message = validate_password(password)
                if not is_valid:
                    print(f"❌ {message}")
                    return False
            else:
                password = get_secure_password("Enter admin password: ")
            
            # Create admin user using Redis service - explicitly set is_admin=True
            password_hash = generate_password_hash(password)
            
            admin_user = user_service.create_user_sync(
                username=username,
                email=email,
                password_hash=password_hash,
                is_admin=True,
                is_active=True
            )
            
            print(f"✅ Created admin user: {username}")
            print(f"📧 Email: {email}")
            print("🔒 Please store the password securely")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating admin user: {e}")
            return False

def promote_user(args):
    """Grant admin privileges to an existing user"""
    app = create_app()
    
    with app.app_context():
        if not args.username:
            print("❌ Username is required")
            print("💡 Usage: promote-user --username <username>")
            return False
        
        # Import Kuzu services
        
        try:
            # Use the Kuzu-based user service
            
            user = user_service.get_user_by_username_sync(args.username)
            if not user:
                print(f"❌ User '{args.username}' not found")
                return False
            
            if user.is_admin:
                print(f"ℹ️  User '{args.username}' is already an admin")
                return True
            
            # Update user to admin
            user.is_admin = True
            updated_user = user_service.update_user_sync(user)
            
            print(f"✅ Granted admin privileges to user: {args.username}")
            return True
            
        except Exception as e:
            print(f"❌ Error promoting user: {e}")
            return False

def list_users(args):
    """List all users in the system"""
    app = create_app()
    
    with app.app_context():
        # Import Kuzu services
        
        try:
            # Use the Kuzu-based user service
            users = user_service.get_all_users_sync()
            
            if not users:
                print("📭 No users found in the database")
                return True
            
            print(f"👥 Found {len(users)} user(s):")
            print("-" * 80)
            print(f"{'Username':<20} {'Email':<30} {'Admin':<8} {'Active':<8} {'Created'}")
            print("-" * 80)
            
            # Sort users by created_at in descending order
            sorted_users = sorted(users, key=lambda u: u.created_at if u.created_at else datetime.min, reverse=True)
            
            for user in sorted_users:
                admin_status = "Yes" if user.is_admin else "No"
                active_status = "Yes" if user.is_active else "No"
                created_date = user.created_at.strftime('%Y-%m-%d') if user.created_at else "Unknown"
                
                print(f"{user.username:<20} {user.email:<30} {admin_status:<8} {active_status:<8} {created_date}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error listing users: {e}")
            return False

def system_stats(args):
    """Display system statistics"""
    app = create_app()
    
    with app.app_context():
        # Use the Kuzu-based user service
        all_users = user_service.get_all_users_sync()
        
        total_users = len(all_users)
        admin_users = len([u for u in all_users if u.is_admin])
        active_users = len([u for u in all_users if u.is_active])
        
        print("📊 MyBibliotheca System Statistics")
        print("=" * 40)
        print(f"👥 Users:")
        print(f"   Total: {total_users}")
        print(f"   Admin: {admin_users}")
        print(f"   Active: {active_users}")
        print()
        print(f"📚 Data:")
        print(f"   Books: (Redis service not implemented)")
        print(f"   Reading Logs: (Redis service not implemented)")
        print()
        
        # Database file info for migration reference
        db_path = "/app/data/books.db"
        if os.path.exists(db_path):
            db_size = os.path.getsize(db_path)
            db_size_mb = round(db_size / 1024 / 1024, 2)
            print(f"💾 SQLite Database (for migration):")
            print(f"   File: {db_path}")
            print(f"   Size: {db_size_mb} MB")
        
        print("✅ System status: Operational (Redis-only mode)")
        
        return True

def main():
    parser = argparse.ArgumentParser(
        description="MyBibliotheca Admin Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 admin_tools.py reset-admin-password
  python3 admin_tools.py reset-admin-password --password newpass123
  python3 admin_tools.py create-admin --username newadmin --email admin@example.com
  python3 admin_tools.py promote-user --username johndoe
  python3 admin_tools.py list-users
  python3 admin_tools.py system-stats
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Reset admin password
    reset_parser = subparsers.add_parser('reset-admin-password', help='Reset admin user password')
    reset_parser.add_argument('--password', help='New password (if not provided, will prompt securely)')
    
    # Create admin
    create_parser = subparsers.add_parser('create-admin', help='Create a new admin user')
    create_parser.add_argument('--username', help='Admin username')
    create_parser.add_argument('--email', help='Admin email')
    create_parser.add_argument('--password', help='Admin password (if not provided, will prompt securely)')
    create_parser.add_argument('--force', action='store_true', help='Create admin even if one exists')
    
    # Promote user
    promote_parser = subparsers.add_parser('promote-user', help='Grant admin privileges to user')
    promote_parser.add_argument('--username', required=True, help='Username to promote')
    
    # List users
    list_parser = subparsers.add_parser('list-users', help='List all users')
    
    # System stats
    stats_parser = subparsers.add_parser('system-stats', help='Display system statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    try:
        command_map = {
            'reset-admin-password': reset_admin_password,
            'create-admin': create_admin,
            'promote-user': promote_user,
            'list-users': list_users,
            'system-stats': system_stats,
        }
        
        command_func = command_map.get(args.command)
        if command_func:
            success = command_func(args)
            return 0 if success else 1
        else:
            print(f"❌ Unknown command: {args.command}")
            parser.print_help()
            return 1
            
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
