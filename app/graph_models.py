from datetime import datetime, timezone, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import re
from kuzu_config import kuzu_db

class BaseGraphModel:
    """Base class for all graph models"""
    
    @classmethod
    def get_next_id(cls, table_name):
        """Get next available ID for a table"""
        query = f"MATCH (n:{table_name}) RETURN MAX(n.id) AS max_id"
        try:
            result = kuzu_db.execute_query(query)
            max_id = result.get_next()[0] if result.has_next() else 0
            return (max_id or 0) + 1
        except:
            return 1

class User(UserMixin, BaseGraphModel):
    """Graph-based User model"""
    
    def __init__(self, username=None, email=None, password_hash=None, is_admin=False, **kwargs):
        self.id = kwargs.get('id')
        self.uid = kwargs.get('uid', secrets.token_urlsafe(8))
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.is_admin = is_admin
        self._is_active = kwargs.get('is_active', True)
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
        self.failed_login_attempts = kwargs.get('failed_login_attempts', 0)
        self.locked_until = kwargs.get('locked_until')
        self.last_login = kwargs.get('last_login')
        self.share_current_reading = kwargs.get('share_current_reading', True)
        self.share_reading_activity = kwargs.get('share_reading_activity', True)
        self.share_library = kwargs.get('share_library', True)
        self.password_must_change = kwargs.get('password_must_change', False)
        self.password_changed_at = kwargs.get('password_changed_at')
        self.reading_streak_offset = kwargs.get('reading_streak_offset', 0)
    
    @property
    def is_active(self):
        """Override Flask-Login's is_active property"""
        return self._is_active
    
    @is_active.setter
    def is_active(self, value):
        """Setter for is_active"""
        self._is_active = value
    
    def save(self):
        """Save user to graph database"""
        if not self.id:
            self.id = self.get_next_id('User')
        
        query = """
        CREATE (u:User {
            id: $id,
            uid: $uid,
            username: $username,
            email: $email,
            password_hash: $password_hash,
            is_admin: $is_admin,
            is_active: $is_active,
            created_at: $created_at,
            failed_login_attempts: $failed_login_attempts,
            locked_until: $locked_until,
            last_login: $last_login,
            share_current_reading: $share_current_reading,
            share_reading_activity: $share_reading_activity,
            share_library: $share_library,
            password_must_change: $password_must_change,
            password_changed_at: $password_changed_at,
            reading_streak_offset: $reading_streak_offset
        })
        """
        
        params = {
            'id': self.id,
            'uid': self.uid,
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'is_admin': self.is_admin,
            'is_active': self._is_active,
            'created_at': self.created_at,
            'failed_login_attempts': self.failed_login_attempts,
            'locked_until': self.locked_until,
            'last_login': self.last_login,
            'share_current_reading': self.share_current_reading,
            'share_reading_activity': self.share_reading_activity,
            'share_library': self.share_library,
            'password_must_change': self.password_must_change,
            'password_changed_at': self.password_changed_at,
            'reading_streak_offset': self.reading_streak_offset
        }
        
        kuzu_db.execute_query(query, params)
        return self
    
    def update(self):
        """Update existing user"""
        query = """
        MATCH (u:User {id: $id})
        SET u.username = $username,
            u.email = $email,
            u.password_hash = $password_hash,
            u.is_admin = $is_admin,
            u.is_active = $is_active,
            u.failed_login_attempts = $failed_login_attempts,
            u.locked_until = $locked_until,
            u.last_login = $last_login,
            u.share_current_reading = $share_current_reading,
            u.share_reading_activity = $share_reading_activity,
            u.share_library = $share_library,
            u.password_must_change = $password_must_change,
            u.password_changed_at = $password_changed_at,
            u.reading_streak_offset = $reading_streak_offset
        """
        
        params = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'is_admin': self.is_admin,
            'is_active': self._is_active,
            'failed_login_attempts': self.failed_login_attempts,
            'locked_until': self.locked_until,
            'last_login': self.last_login,
            'share_current_reading': self.share_current_reading,
            'share_reading_activity': self.share_reading_activity,
            'share_library': self.share_library,
            'password_must_change': self.password_must_change,
            'password_changed_at': self.password_changed_at,
            'reading_streak_offset': self.reading_streak_offset
        }
        
        kuzu_db.execute_query(query, params)
        return self
    
    @classmethod
    def query(cls):
        """Return a UserQuery object for building queries"""
        return UserQuery()
    
    @classmethod
    def get(cls, user_id):
        """Get user by ID"""
        query = "MATCH (u:User {id: $id}) RETURN u"
        result = kuzu_db.execute_query(query, {'id': user_id})
        
        if result.has_next():
            user_data = result.get_next()[0]
            return cls._from_dict(user_data)
        return None
    
    @classmethod
    def _from_dict(cls, data):
        """Create User instance from dictionary"""
        return cls(
            id=data.get('id'),
            uid=data.get('uid'),
            username=data.get('username'),
            email=data.get('email'),
            password_hash=data.get('password_hash'),
            is_admin=data.get('is_admin', False),
            is_active=data.get('is_active', True),
            created_at=data.get('created_at'),
            failed_login_attempts=data.get('failed_login_attempts', 0),
            locked_until=data.get('locked_until'),
            last_login=data.get('last_login'),
            share_current_reading=data.get('share_current_reading', True),
            share_reading_activity=data.get('share_reading_activity', True),
            share_library=data.get('share_library', True),
            password_must_change=data.get('password_must_change', False),
            password_changed_at=data.get('password_changed_at'),
            reading_streak_offset=data.get('reading_streak_offset', 0)
        )
    
    def set_password(self, password, validate=True):
        """Set password hash"""
        if validate and not self.is_password_strong(password):
            raise ValueError("Password does not meet security requirements")
        
        self.password_hash = generate_password_hash(password)
        self.password_changed_at = datetime.now(timezone.utc)
        if validate:
            self.password_must_change = False
    
    def check_password(self, password):
        """Check if password is correct"""
        return check_password_hash(self.password_hash, password)
    
    @staticmethod
    def is_password_strong(password):
        """Validate password strength"""
        if len(password) < 8:
            return False
        if not re.search(r"[A-Z]", password):
            return False
        if not re.search(r"[a-z]", password):
            return False
        if not re.search(r"\d", password):
            return False
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
            return False
        return True
    
    def is_account_locked(self):
        """Check if account is locked"""
        if self.locked_until and self.locked_until > datetime.now(timezone.utc):
            return True
        return False
    
    def get_id(self):
        """Return user ID as string for Flask-Login"""
        return str(self.id)
    
    def delete(self):
        """Delete user from graph database"""
        query = "MATCH (u:User {id: $id}) DELETE u"
        kuzu_db.execute_query(query, {'id': self.id})
        return True
    
    def reset_failed_login(self):
        """Reset failed login attempts"""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login = datetime.now(timezone.utc)
        
    def increment_failed_login(self):
        """Increment failed login attempts and lock if needed"""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
    
    def is_locked(self):
        """Check if account is currently locked"""
        return self.is_account_locked()
        
    def unlock_account(self):
        """Unlock the account"""
        self.failed_login_attempts = 0
        self.locked_until = None
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'uid': self.uid,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'share_current_reading': self.share_current_reading,
            'share_reading_activity': self.share_reading_activity,
            'share_library': self.share_library,
            'reading_streak_offset': self.reading_streak_offset
        }
    
    def get_reading_streak(self):
        """Calculate user's reading streak"""
        from datetime import date, timedelta
        
        # Get all books with finish dates for this user
        books = Book.query().filter_by(user_id=self.id).all()
        
        if not books:
            return 0 + (self.reading_streak_offset or 0)
        
        # Find consecutive days of reading
        current_date = date.today()
        streak = 0
        
        # Get unique finish dates (in case of multiple books per day)
        finish_dates = set()
        for book in books:
            if book.finish_date:
                if isinstance(book.finish_date, str):
                    try:
                        finish_date = date.fromisoformat(book.finish_date)
                    except ValueError:
                        continue
                else:
                    finish_date = book.finish_date
                finish_dates.add(finish_date)
        
        # Sort dates in descending order
        sorted_dates = sorted(finish_dates, reverse=True)
        
        if not sorted_dates:
            return 0 + (self.reading_streak_offset or 0)
        
        # Check if the streak is current (finished a book today or yesterday)
        most_recent = sorted_dates[0]
        days_since_last = (current_date - most_recent).days
        
        if days_since_last > 1:
            return 0 + (self.reading_streak_offset or 0)
        
        # Count consecutive days
        expected_date = most_recent
        for finish_date in sorted_dates:
            if finish_date == expected_date:
                streak += 1
                expected_date = finish_date - timedelta(days=1)
            else:
                break
        
        return streak + (self.reading_streak_offset or 0)


class UserQuery:
    """Query builder for User model"""
    
    def __init__(self):
        self.conditions = []
        self.params = {}
        self.order_by = None
        self.limit_val = None
    
    def filter_by(self, **kwargs):
        """Add filter conditions"""
        for key, value in kwargs.items():
            param_name = f"param_{len(self.params)}"
            self.conditions.append(f"u.{key} = ${param_name}")
            self.params[param_name] = value
        return self
    
    def filter(self, condition):
        """Add custom filter condition"""
        if hasattr(condition, 'conditions'):
            self.conditions.extend(condition.conditions)
            self.params.update(condition.params)
        else:
            self.conditions.append(str(condition))
        return self
    
    def order_by(self, field):
        """Add order by clause"""
        self.order_by_field = field
        return self
    
    def limit(self, count):
        """Add limit clause"""
        self.limit_val = count
        return self
    
    def count(self):
        """Get count of matching records"""
        where_clause = " AND ".join(self.conditions) if self.conditions else "true"
        query = f"MATCH (u:User) WHERE {where_clause} RETURN COUNT(u) AS count"
        
        result = kuzu_db.execute_query(query, self.params)
        return result.get_next()[0] if result.has_next() else 0
    
    def first(self):
        """Get first matching record"""
        where_clause = " AND ".join(self.conditions) if self.conditions else "true"
        query = f"MATCH (u:User) WHERE {where_clause} RETURN u LIMIT 1"
        
        result = kuzu_db.execute_query(query, self.params)
        if result.has_next():
            user_data = result.get_next()[0]
            return User._from_dict(user_data)
        return None
    
    def all(self):
        """Get all matching records"""
        where_clause = " AND ".join(self.conditions) if self.conditions else "true"
        query = f"MATCH (u:User) WHERE {where_clause} RETURN u"
        
        if self.order_by_field:
            query += f" ORDER BY u.{self.order_by_field}"
        if self.limit_val:
            query += f" LIMIT {self.limit_val}"
        
        result = kuzu_db.execute_query(query, self.params)
        users = []
        while result.has_next():
            user_data = result.get_next()[0]
            users.append(User._from_dict(user_data))
        return users


class Book(BaseGraphModel):
    """Graph-based Book model"""
    
    def __init__(self, title, author, isbn, user_id, **kwargs):
        self.id = kwargs.get('id')
        self.uid = kwargs.get('uid', secrets.token_urlsafe(6))
        self.title = title
        self.author = author
        self.isbn = isbn
        self.user_id = user_id
        self.start_date = kwargs.get('start_date')
        self.finish_date = kwargs.get('finish_date')
        self.cover_url = kwargs.get('cover_url')
        self.want_to_read = kwargs.get('want_to_read', False)
        self.library_only = kwargs.get('library_only', False)
        self.description = kwargs.get('description')
        self.published_date = kwargs.get('published_date')
        self.page_count = kwargs.get('page_count')
        self.categories = kwargs.get('categories')
        self.publisher = kwargs.get('publisher')
        self.language = kwargs.get('language')
        self.average_rating = kwargs.get('average_rating')
        self.rating_count = kwargs.get('rating_count')
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
    
    def save(self):
        """Save book and create relationship with user"""
        if not self.id:
            self.id = self.get_next_id('Book')
        
        # Create book node
        book_query = """
        CREATE (b:Book {
            id: $id,
            uid: $uid,
            title: $title,
            author: $author,
            isbn: $isbn,
            start_date: $start_date,
            finish_date: $finish_date,
            cover_url: $cover_url,
            want_to_read: $want_to_read,
            library_only: $library_only,
            description: $description,
            published_date: $published_date,
            page_count: $page_count,
            categories: $categories,
            publisher: $publisher,
            language: $language,
            average_rating: $average_rating,
            rating_count: $rating_count,
            created_at: $created_at
        })
        """
        
        book_params = {
            'id': self.id,
            'uid': self.uid,
            'title': self.title,
            'author': self.author,
            'isbn': self.isbn,
            'start_date': self.start_date,
            'finish_date': self.finish_date,
            'cover_url': self.cover_url,
            'want_to_read': self.want_to_read,
            'library_only': self.library_only,
            'description': self.description,
            'published_date': self.published_date,
            'page_count': self.page_count,
            'categories': self.categories,
            'publisher': self.publisher,
            'language': self.language,
            'average_rating': self.average_rating,
            'rating_count': self.rating_count,
            'created_at': self.created_at
        }
        
        kuzu_db.execute_query(book_query, book_params)
        
        # Create ownership relationship
        rel_query = """
        MATCH (u:User {id: $user_id}), (b:Book {id: $book_id})
        CREATE (u)-[:OWNS {created_at: $created_at}]->(b)
        """
        
        rel_params = {
            'user_id': self.user_id,
            'book_id': self.id,
            'created_at': self.created_at
        }
        
        kuzu_db.execute_query(rel_query, rel_params)
        return self
    
    @classmethod
    def query(cls):
        """Return a BookQuery object"""
        return BookQuery()
    
    @classmethod
    def _from_dict(cls, data, user_id=None):
        """Create Book instance from dictionary"""
        return cls(
            title=data.get('title'),
            author=data.get('author'),
            isbn=data.get('isbn'),
            user_id=user_id or data.get('user_id'),
            id=data.get('id'),
            uid=data.get('uid'),
            start_date=data.get('start_date'),
            finish_date=data.get('finish_date'),
            cover_url=data.get('cover_url'),
            want_to_read=data.get('want_to_read', False),
            library_only=data.get('library_only', False),
            description=data.get('description'),
            published_date=data.get('published_date'),
            page_count=data.get('page_count'),
            categories=data.get('categories'),
            publisher=data.get('publisher'),
            language=data.get('language'),
            average_rating=data.get('average_rating'),
            rating_count=data.get('rating_count'),
            created_at=data.get('created_at')
        )
    
    @property
    def secure_cover_url(self):
        """Return HTTPS version of cover URL"""
        if self.cover_url and self.cover_url.startswith('http://'):
            return self.cover_url.replace('http://', 'https://')
        return self.cover_url
    
    def delete(self):
        """Delete book from graph database"""
        query = "MATCH (b:Book {id: $id}) DELETE b"
        kuzu_db.execute_query(query, {'id': self.id})
        return True
    
    def to_dict(self):
        """Convert book to dictionary"""
        return {
            'id': self.id,
            'uid': self.uid,
            'title': self.title,
            'author': self.author,
            'isbn': self.isbn,
            'user_id': self.user_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'finish_date': self.finish_date.isoformat() if self.finish_date else None,
            'cover_url': self.cover_url,
            'want_to_read': self.want_to_read,
            'library_only': self.library_only,
            'description': self.description,
            'published_date': self.published_date,
            'page_count': self.page_count,
            'categories': self.categories,
            'publisher': self.publisher,
            'language': self.language,
            'average_rating': self.average_rating,
            'rating_count': self.rating_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    


class BookQuery:
    """Query builder for Book model"""
    
    def __init__(self):
        self.conditions = []
        self.params = {}
        self.order_by_field = None
        self.limit_val = None
        self.user_filter = None
    
    def filter_by(self, **kwargs):
        """Add filter conditions"""
        for key, value in kwargs.items():
            if key == 'user_id':
                self.user_filter = value
            else:
                param_name = f"param_{len(self.params)}"
                self.conditions.append(f"b.{key} = ${param_name}")
                self.params[param_name] = value
        return self
    
    def filter(self, condition):
        """Add custom filter condition"""
        self.conditions.append(str(condition))
        return self
    
    def order_by(self, field):
        """Add order by clause"""
        self.order_by_field = field
        return self
    
    def limit(self, count):
        """Add limit clause"""
        self.limit_val = count
        return self
    
    def all(self):
        """Get all matching records"""
        if self.user_filter:
            base_query = """
            MATCH (u:User {id: $user_id})-[:OWNS]->(b:Book)
            """
            self.params['user_id'] = self.user_filter
        else:
            base_query = "MATCH (b:Book)"
        
        where_clause = " AND ".join(self.conditions) if self.conditions else ""
        if where_clause:
            base_query += f" WHERE {where_clause}"
        
        query = base_query + " RETURN b"
        
        if self.order_by_field:
            query += f" ORDER BY b.{self.order_by_field}"
        if self.limit_val:
            query += f" LIMIT {self.limit_val}"
        
        result = kuzu_db.execute_query(query, self.params)
        books = []
        while result.has_next():
            book_data = result.get_next()[0]
            books.append(Book._from_dict(book_data, self.user_filter))
        return books
    
    def first(self):
        """Get first matching record"""
        books = self.limit(1).all()
        return books[0] if books else None
    
    def count(self):
        """Get count of matching records"""
        if self.user_filter:
            base_query = """
            MATCH (u:User {id: $user_id})-[:OWNS]->(b:Book)
            """
            self.params['user_id'] = self.user_filter
        else:
            base_query = "MATCH (b:Book)"
        
        where_clause = " AND ".join(self.conditions) if self.conditions else ""
        if where_clause:
            base_query += f" WHERE {where_clause}"
        
        query = base_query + " RETURN COUNT(b) AS count"
        
        result = kuzu_db.execute_query(query, self.params)
        return result.get_next()[0] if result.has_next() else 0


class ReadingLog(BaseGraphModel):
    """Graph-based ReadingLog model"""
    
    def __init__(self, book_id, user_id, date, **kwargs):
        self.id = kwargs.get('id')
        self.book_id = book_id
        self.user_id = user_id
        self.date = date
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
    
    def save(self):
        """Save reading log and create relationships"""
        if not self.id:
            self.id = self.get_next_id('ReadingLog')
        
        # Create reading log node
        log_query = """
        CREATE (rl:ReadingLog {
            id: $id,
            date: $date,
            created_at: $created_at
        })
        """
        
        log_params = {
            'id': self.id,
            'date': self.date,
            'created_at': self.created_at
        }
        
        kuzu_db.execute_query(log_query, log_params)
        
        # Create relationships
        user_rel_query = """
        MATCH (u:User {id: $user_id}), (rl:ReadingLog {id: $log_id})
        CREATE (u)-[:LOGGED {created_at: $created_at}]->(rl)
        """
        
        book_rel_query = """
        MATCH (b:Book {id: $book_id}), (rl:ReadingLog {id: $log_id})
        CREATE (b)-[:READ_ON {created_at: $created_at}]->(rl)
        """
        
        user_rel_params = {
            'user_id': self.user_id,
            'log_id': self.id,
            'created_at': self.created_at
        }
        
        book_rel_params = {
            'book_id': self.book_id,
            'log_id': self.id,
            'created_at': self.created_at
        }
        
        kuzu_db.execute_query(user_rel_query, user_rel_params)
        kuzu_db.execute_query(book_rel_query, book_rel_params)
        
        return self
    
    @classmethod
    def query(cls):
        """Return a ReadingLogQuery object"""
        return ReadingLogQuery()
    
    def delete(self):
        """Delete reading log from graph database"""
        query = "MATCH (r:ReadingLog {id: $id}) DELETE r"
        kuzu_db.execute_query(query, {'id': self.id})
        return True
    


class ReadingLogQuery:
    """Query builder for ReadingLog model"""
    
    def __init__(self):
        self.conditions = []
        self.params = {}
        self.order_by_field = None
        self.limit_val = None
        self.user_filter = None
        self.book_filter = None
    
    def filter_by(self, **kwargs):
        """Add filter conditions"""
        for key, value in kwargs.items():
            if key == 'user_id':
                self.user_filter = value
            elif key == 'book_id':
                self.book_filter = value
            else:
                param_name = f"param_{len(self.params)}"
                self.conditions.append(f"rl.{key} = ${param_name}")
                self.params[param_name] = value
        return self
    
    def order_by(self, field):
        """Add order by clause"""
        self.order_by_field = field
        return self
    
    def limit(self, count):
        """Add limit clause"""
        self.limit_val = count
        return self
    
    def all(self):
        """Get all matching records"""
        query_parts = ["MATCH"]
        
        if self.user_filter and self.book_filter:
            query_parts.append("(u:User {id: $user_id})-[:LOGGED]->(rl:ReadingLog)<-[:READ_ON]-(b:Book {id: $book_id})")
            self.params['user_id'] = self.user_filter
            self.params['book_id'] = self.book_filter
        elif self.user_filter:
            query_parts.append("(u:User {id: $user_id})-[:LOGGED]->(rl:ReadingLog)")
            self.params['user_id'] = self.user_filter
        elif self.book_filter:
            query_parts.append("(b:Book {id: $book_id})-[:READ_ON]->(rl:ReadingLog)")
            self.params['book_id'] = self.book_filter
        else:
            query_parts.append("(rl:ReadingLog)")
        
        where_clause = " AND ".join(self.conditions) if self.conditions else ""
        if where_clause:
            query_parts.append(f"WHERE {where_clause}")
        
        query_parts.append("RETURN rl")
        
        if self.order_by_field:
            query_parts.append(f"ORDER BY rl.{self.order_by_field}")
        if self.limit_val:
            query_parts.append(f"LIMIT {self.limit_val}")
        
        query = " ".join(query_parts)
        
        result = kuzu_db.execute_query(query, self.params)
        logs = []
        while result.has_next():
            log_data = result.get_next()[0]
            logs.append(ReadingLog(
                book_id=self.book_filter,
                user_id=self.user_filter,
                date=log_data.get('date'),
                id=log_data.get('id'),
                created_at=log_data.get('created_at')
            ))
        return logs
    
    def first(self):
        """Get first matching record"""
        logs = self.limit(1).all()
        return logs[0] if logs else None
    
    def count(self):
        """Get count of matching records"""
        query_parts = ["MATCH"]
        
        if self.user_filter and self.book_filter:
            query_parts.append("(u:User {id: $user_id})-[:LOGGED]->(rl:ReadingLog)<-[:READ_ON]-(b:Book {id: $book_id})")
            self.params['user_id'] = self.user_filter
            self.params['book_id'] = self.book_filter
        elif self.user_filter:
            query_parts.append("(u:User {id: $user_id})-[:LOGGED]->(rl:ReadingLog)")
            self.params['user_id'] = self.user_filter
        elif self.book_filter:
            query_parts.append("(b:Book {id: $book_id})-[:READ_ON]->(rl:ReadingLog)")
            self.params['book_id'] = self.book_filter
        else:
            query_parts.append("(rl:ReadingLog)")
        
        where_clause = " AND ".join(self.conditions) if self.conditions else ""
        if where_clause:
            query_parts.append(f"WHERE {where_clause}")
        
        query_parts.append("RETURN COUNT(rl) AS count")
        query = " ".join(query_parts)
        
        result = kuzu_db.execute_query(query, self.params)
        return result.get_next()[0] if result.has_next() else 0


# Compatibility functions for session management
class GraphSession:
    """Mock session object for compatibility"""
    
    @staticmethod
    def add(obj):
        """Add object to session (no-op for graph DB)"""
        pass
    
    @staticmethod
    def commit():
        """Commit transaction (no-op for graph DB)"""
        pass
    
    @staticmethod
    def rollback():
        """Rollback transaction (no-op for graph DB)"""
        pass
    
    @staticmethod
    def delete(obj):
        """Delete object (implement as needed)"""
        pass

# Create global session object for compatibility
session = GraphSession()
