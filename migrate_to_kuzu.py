#!/usr/bin/env python3
"""
Migration script from SQLite/SQLAlchemy to Kuzu Graph Database
This script will migrate all data from your existing SQL database to the new Kuzu graph database.

Note: This script requires SQLAlchemy which is an optional dependency.
Install it with: pip install flask-sqlalchemy
Or: uv add --optional migration flask-sqlalchemy
"""

import os
import sys
import sqlite3
import secrets
from datetime import datetime, timezone
from pathlib import Path

# Check for required migration dependencies
try:
    import sqlite3
except ImportError:
    print("❌ sqlite3 is required for migration but not available")
    sys.exit(1)

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from kuzu_config import kuzu_db
    from app.graph_models import User, Book, ReadingLog
except ImportError as e:
    print(f"❌ Error importing Kuzu models: {e}")
    print("Make sure Kuzu is installed: pip install kuzu")
    sys.exit(1)

def connect_sqlite():
    """Connect to the existing SQLite database"""
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'books.db')
    if not os.path.exists(db_path):
        print(f"❌ SQLite database not found at {db_path}")
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    except Exception as e:
        print(f"❌ Error connecting to SQLite database: {e}")
        return None

def migrate_users(sqlite_conn):
    """Migrate users from SQLite to Kuzu"""
    print("🔄 Migrating users...")
    
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM user ORDER BY id")
    users = cursor.fetchall()
    
    migrated_count = 0
    for user_row in users:
        try:
            # Helper function to safely get values from SQLite Row
            def get_value(row, key, default=None):
                try:
                    return row[key] if row[key] is not None else default
                except (IndexError, KeyError):
                    return default
            
            user = User(
                username=user_row['username'],
                email=user_row['email'],
                password_hash=user_row['password_hash'],
                is_admin=bool(get_value(user_row, 'is_admin', False)),
                id=user_row['id'],
                is_active=bool(get_value(user_row, 'is_active', True)),
                created_at=datetime.fromisoformat(user_row['created_at']) if user_row['created_at'] else datetime.now(timezone.utc),
                failed_login_attempts=get_value(user_row, 'failed_login_attempts', 0),
                locked_until=datetime.fromisoformat(get_value(user_row, 'locked_until')) if get_value(user_row, 'locked_until') else None,
                last_login=datetime.fromisoformat(get_value(user_row, 'last_login')) if get_value(user_row, 'last_login') else None,
                share_current_reading=bool(get_value(user_row, 'share_current_reading', True)),
                share_reading_activity=bool(get_value(user_row, 'share_reading_activity', True)),
                share_library=bool(get_value(user_row, 'share_library', True)),
                password_must_change=bool(get_value(user_row, 'password_must_change', False)),
                password_changed_at=datetime.fromisoformat(get_value(user_row, 'password_changed_at')) if get_value(user_row, 'password_changed_at') else None,
                reading_streak_offset=get_value(user_row, 'reading_streak_offset', 0)
            )
            
            user.save()
            migrated_count += 1
            print(f"  ✅ Migrated user: {user.username}")
            
        except Exception as e:
            print(f"  ❌ Error migrating user {user_row['username']}: {e}")
    
    print(f"✅ Migrated {migrated_count} users")
    return migrated_count

def migrate_books(sqlite_conn):
    """Migrate books from SQLite to Kuzu"""
    print("📚 Migrating books...")
    
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM book ORDER BY id")
    books = cursor.fetchall()
    
    migrated_count = 0
    for book_row in books:
        try:
            # Helper function to safely get values from SQLite Row
            def get_value(row, key, default=None):
                try:
                    return row[key] if row[key] is not None else default
                except (IndexError, KeyError):
                    return default
            
            # Convert date strings to date objects
            start_date = None
            finish_date = None
            
            if get_value(book_row, 'start_date'):
                try:
                    start_date = datetime.fromisoformat(book_row['start_date']).date()
                except:
                    start_date = None
            
            if get_value(book_row, 'finish_date'):
                try:
                    finish_date = datetime.fromisoformat(book_row['finish_date']).date()
                except:
                    finish_date = None
            
            book = Book(
                title=book_row['title'],
                author=book_row['author'],
                isbn=book_row['isbn'],
                user_id=book_row['user_id'],
                id=book_row['id'],
                uid=get_value(book_row, 'uid', f"book_{book_row['id']}"),
                start_date=start_date,
                finish_date=finish_date,
                cover_url=get_value(book_row, 'cover_url'),
                want_to_read=bool(get_value(book_row, 'want_to_read', False)),
                library_only=bool(get_value(book_row, 'library_only', False)),
                description=get_value(book_row, 'description'),
                published_date=get_value(book_row, 'published_date'),
                page_count=get_value(book_row, 'page_count'),
                categories=get_value(book_row, 'categories'),
                publisher=get_value(book_row, 'publisher'),
                language=get_value(book_row, 'language'),
                average_rating=get_value(book_row, 'average_rating'),
                rating_count=get_value(book_row, 'rating_count'),
                created_at=datetime.fromisoformat(get_value(book_row, 'created_at')) if get_value(book_row, 'created_at') else datetime.now(timezone.utc)
            )
            
            book.save()
            migrated_count += 1
            print(f"  ✅ Migrated book: {book.title}")
            
        except Exception as e:
            print(f"  ❌ Error migrating book {book_row['title']}: {e}")
    
    print(f"✅ Migrated {migrated_count} books")
    return migrated_count

def migrate_reading_logs(sqlite_conn):
    """Migrate reading logs from SQLite to Kuzu"""
    print("📖 Migrating reading logs...")
    
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM reading_log ORDER BY id")
    logs = cursor.fetchall()
    
    migrated_count = 0
    for log_row in logs:
        try:
            # Helper function to safely get values from SQLite Row
            def get_value(row, key, default=None):
                try:
                    return row[key] if row[key] is not None else default
                except (IndexError, KeyError):
                    return default
            
            # Convert date string to date object
            log_date = None
            if log_row['date']:
                try:
                    log_date = datetime.fromisoformat(log_row['date']).date()
                except:
                    log_date = None
            
            if log_date:  # Only migrate logs with valid dates
                reading_log = ReadingLog(
                    book_id=log_row['book_id'],
                    user_id=log_row['user_id'],
                    date=log_date,
                    id=log_row['id'],
                    created_at=datetime.fromisoformat(get_value(log_row, 'created_at')) if get_value(log_row, 'created_at') else datetime.now(timezone.utc)
                )
                
                reading_log.save()
                migrated_count += 1
                print(f"  ✅ Migrated reading log: {log_row['id']}")
            
        except Exception as e:
            print(f"  ❌ Error migrating reading log {log_row['id']}: {e}")
    
    print(f"✅ Migrated {migrated_count} reading logs")
    return migrated_count

def verify_migration(sqlite_conn):
    """Verify that migration was successful"""
    print("🔍 Verifying migration...")
    
    # Count records in SQLite
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM user")
    sqlite_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM book")
    sqlite_books = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM reading_log")
    sqlite_logs = cursor.fetchone()[0]
    
    # Count records in Kuzu
    kuzu_users = User.query().count()
    kuzu_books = Book.query().count()
    kuzu_logs = ReadingLog.query().count()
    
    print(f"Users: SQLite={sqlite_users}, Kuzu={kuzu_users}")
    print(f"Books: SQLite={sqlite_books}, Kuzu={kuzu_books}")
    print(f"Reading Logs: SQLite={sqlite_logs}, Kuzu={kuzu_logs}")
    
    success = (
        sqlite_users == kuzu_users and
        sqlite_books == kuzu_books and
        sqlite_logs == kuzu_logs
    )
    
    if success:
        print("✅ Migration verification successful!")
    else:
        print("❌ Migration verification failed!")
    
    return success

def backup_sqlite_db():
    """Create a backup of the original SQLite database"""
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'books.db')
    if not os.path.exists(db_path):
        return None
    
    backup_dir = os.path.join(os.path.dirname(__file__), 'data', 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"books_pre_kuzu_migration_{timestamp}.db")
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ SQLite backup created: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        return None

def main():
    """Main migration function"""
    print("🚀 Starting migration from SQLite to Kuzu Graph Database")
    print("=" * 60)
    
    # Create backup of original database
    backup_path = backup_sqlite_db()
    if not backup_path:
        print("⚠️  Could not create backup, proceeding anyway...")
    
    # Connect to SQLite database
    sqlite_conn = connect_sqlite()
    if not sqlite_conn:
        print("❌ Cannot connect to SQLite database. Aborting migration.")
        return False
    
    # Connect to Kuzu database
    if not kuzu_db.connect():
        print("❌ Cannot connect to Kuzu database. Aborting migration.")
        return False
    
    try:
        # Create Kuzu schema
        print("🏗️  Creating Kuzu schema...")
        kuzu_db.create_schema()
        print("✅ Kuzu schema created")
        
        # Migrate data
        users_migrated = migrate_users(sqlite_conn)
        books_migrated = migrate_books(sqlite_conn)
        logs_migrated = migrate_reading_logs(sqlite_conn)
        
        # Verify migration
        if verify_migration(sqlite_conn):
            print("\n🎉 Migration completed successfully!")
            print(f"📊 Migration Summary:")
            print(f"   Users: {users_migrated}")
            print(f"   Books: {books_migrated}")
            print(f"   Reading Logs: {logs_migrated}")
            
            if backup_path:
                print(f"💾 Original database backed up to: {backup_path}")
            
            return True
        else:
            print("\n❌ Migration verification failed. Please check the logs.")
            return False
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        sqlite_conn.close()
        kuzu_db.disconnect()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
