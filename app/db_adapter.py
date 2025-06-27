"""
Database adapter for MyBibliotheca Kuzu Graph Database
Provides unified interface for Kuzu graph database operations
"""

from datetime import datetime, date

class DatabaseAdapter:
    """Adapter to provide unified interface for Kuzu database operations"""
    
    def __init__(self):
        # Always use Kuzu - SQL support removed
        self.use_kuzu = True
    
    def get_user_books_with_filters(self, user_id, search=None, category=None, publisher=None, language=None):
        """Get user books with various filters applied"""
        from .graph_models import Book
        
        # Build Kuzu query
        query_parts = ["MATCH (u:User {id: $user_id})-[:OWNS]->(b:Book)"]
        params = {'user_id': user_id}
        conditions = []
        
        if search:
            conditions.append("(b.title CONTAINS $search OR b.author CONTAINS $search OR b.description CONTAINS $search)")
            params['search'] = search
        
        if category:
            conditions.append("b.categories CONTAINS $category")
                params['category'] = category
            
            if publisher:
                conditions.append("b.publisher = $publisher")
                params['publisher'] = publisher
            
            if language:
                conditions.append("b.language = $language")
                params['language'] = language
            
            if conditions:
                query_parts.append("WHERE " + " AND ".join(conditions))
            
            query_parts.append("RETURN b ORDER BY b.title")
            query = " ".join(query_parts)
            
            from kuzu_config import kuzu_db
            result = kuzu_db.execute_query(query, params)
            
            books = []
            while result.has_next():
                book_data = result.get_next()[0]
                books.append(Book._from_dict(book_data, user_id))
            
            return books
        else:
            # SQLAlchemy implementation
            from .models import Book
            from sqlalchemy import or_
            
            query = Book.query().filter_by(user_id=user_id)
            
            if search:
                search_filter = or_(
                    Book.title.ilike(f'%{search}%'),
                    Book.author.ilike(f'%{search}%'),
                    Book.description.ilike(f'%{search}%'),
                    Book.categories.ilike(f'%{search}%'),
                    Book.publisher.ilike(f'%{search}%')
                )
                query = query.filter(search_filter)
            
            if category:
                query = query.filter(Book.categories.ilike(f'%{category}%'))
            
            if publisher:
                query = query.filter(Book.publisher == publisher)
            
            if language:
                query = query.filter(Book.language == language)
            
            return query.all()
    
    def get_user_book_filters(self, user_id):
        """Get unique filter values for user's books"""
        if self.use_kuzu:
            from kuzu_config import kuzu_db
            
            # Get all books for the user
            query = """
            MATCH (u:User {id: $user_id})-[:OWNS]->(b:Book)
            RETURN b.categories, b.publisher, b.language
            """
            
            result = kuzu_db.execute_query(query, {'user_id': user_id})
            
            categories = set()
            publishers = set()
            languages = set()
            
            while result.has_next():
                row = result.get_next()
                
                if row[0]:  # categories
                    categories.update([cat.strip() for cat in row[0].split(',')])
                
                if row[1]:  # publisher
                    publishers.add(row[1])
                
                if row[2]:  # language
                    languages.add(row[2])
            
            return sorted(categories), sorted(publishers), sorted(languages)
        
        else:
            # SQLAlchemy implementation
            from .models import Book
            
            all_books = Book.query().filter_by(user_id=user_id).all()
            categories = set()
            publishers = set()
            languages = set()

            for book in all_books:
                if book.categories:
                    categories.update([cat.strip() for cat in book.categories.split(',')])
                if book.publisher:
                    publishers.add(book.publisher)
                if book.language:
                    languages.add(book.language)
            
            return sorted(categories), sorted(publishers), sorted(languages)
    
    def get_books_finished_this_month(self, user_id, year, month):
        """Get books finished in a specific month"""
        if self.use_kuzu:
            from kuzu_config import kuzu_db
            
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1)
            else:
                end_date = date(year, month + 1, 1)
            
            query = """
            MATCH (u:User {id: $user_id})-[:OWNS]->(b:Book)
            WHERE b.finish_date >= $start_date AND b.finish_date < $end_date
            RETURN b
            ORDER BY b.finish_date DESC
            """
            
            params = {
                'user_id': user_id,
                'start_date': start_date,
                'end_date': end_date
            }
            
            result = kuzu_db.execute_query(query, params)
            
            books = []
            while result.has_next():
                book_data = result.get_next()[0]
                books.append(Book._from_dict(book_data, user_id))
            
            return books
        
        else:
            # SQLAlchemy implementation
            from .models import Book
            
            return Book.query().filter(
                Book.user_id == user_id,
                Book.finish_date.isnot(None),
                Book.finish_date >= datetime(year, month, 1),
                Book.finish_date < (
                    datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
                )
            ).all()
    
    def get_community_stats(self):
        """Get community statistics for sharing users"""
        if self.use_kuzu:
            from kuzu_config import kuzu_db
            
            # Get sharing users
            sharing_users_query = """
            MATCH (u:User)
            WHERE u.share_reading_activity = true AND u.is_active = true
            RETURN u
            """
            
            result = kuzu_db.execute_query(sharing_users_query)
            sharing_users = []
            
            while result.has_next():
                user_data = result.get_next()[0]
                sharing_users.append(User._from_dict(user_data))
            
            # Get recent finished books
            recent_books_query = """
            MATCH (u:User)-[:OWNS]->(b:Book)
            WHERE u.share_reading_activity = true AND u.is_active = true AND b.finish_date IS NOT NULL
            RETURN b, u.id as user_id
            ORDER BY b.finish_date DESC
            LIMIT 20
            """
            
            result = kuzu_db.execute_query(recent_books_query)
            recent_books = []
            
            while result.has_next():
                row = result.get_next()
                book_data = row[0]
                user_id = row[1]
                recent_books.append(Book._from_dict(book_data, user_id))
            
            # Get currently reading books
            currently_reading_query = """
            MATCH (u:User)-[:OWNS]->(b:Book)
            WHERE u.share_current_reading = true AND u.is_active = true 
                  AND b.start_date IS NOT NULL AND b.finish_date IS NULL
            RETURN b, u.id as user_id
            ORDER BY b.start_date DESC
            LIMIT 20
            """
            
            result = kuzu_db.execute_query(currently_reading_query)
            currently_reading = []
            
            while result.has_next():
                row = result.get_next()
                book_data = row[0]
                user_id = row[1]
                currently_reading.append(Book._from_dict(book_data, user_id))
            
            return {
                'sharing_users': sharing_users,
                'recent_finished_books': recent_books,
                'currently_reading': currently_reading
            }
        
        else:
            # SQLAlchemy implementation
            from .models import Book, User
            
            sharing_users = User.query().filter_by(
                share_reading_activity=True,
                is_active=True
            ).all()
            
            recent_finished_books = Book.query().join(User).filter(
                User.share_reading_activity == True,
                User.is_active == True,
                Book.finish_date.isnot(None)
            ).order_by(Book.finish_date.desc()).limit(20).all()
            
            currently_reading = Book.query().join(User).filter(
                User.share_current_reading == True,
                User.is_active == True,
                Book.start_date.isnot(None),
                Book.finish_date.is_(None)
            ).order_by(Book.start_date.desc()).limit(20).all()
            
            return {
                'sharing_users': sharing_users,
                'recent_finished_books': recent_finished_books,
                'currently_reading': currently_reading
            }
    
    def create_book_with_relationship(self, book_data, user_id):
        """Create a book and establish user relationship"""
        if self.use_kuzu:
            from .graph_models import Book
            
            book = Book(
                title=book_data['title'],
                author=book_data['author'],
                isbn=book_data['isbn'],
                user_id=user_id,
                **{k: v for k, v in book_data.items() if k not in ['title', 'author', 'isbn']}
            )
            
            return book.save()
        
        else:
            # SQLAlchemy implementation
            from .models import Book, db
            
            book = Book(
                title=book_data['title'],
                author=book_data['author'],
                isbn=book_data['isbn'],
                user_id=user_id,
                **{k: v for k, v in book_data.items() if k not in ['title', 'author', 'isbn']}
            )
            
            book.save()
            return book
    
    def delete_book_and_logs(self, book):
        """Delete a book and its associated reading logs"""
        if self.use_kuzu:
            from kuzu_config import kuzu_db
            
            # Delete reading logs for this book
            delete_logs_query = """
            MATCH (b:Book {id: $book_id})-[:READ_ON]->(rl:ReadingLog)
            DETACH DELETE rl
            """
            kuzu_db.execute_query(delete_logs_query, {'book_id': book.id})
            
            # Delete the book
            delete_book_query = """
            MATCH (b:Book {id: $book_id})
            DETACH DELETE b
            """
            kuzu_db.execute_query(delete_book_query, {'book_id': book.id})
        
        else:
            # SQLAlchemy implementation
            from .models import ReadingLog, db
            
            ReadingLog.query().filter_by(book_id=book.id).delete()
            book.delete()

# Create global adapter instance
db_adapter = DatabaseAdapter()
