"""
Kuzu-only Application Services.

This module provides service classes that use Kuzu as the primary database,
replacing the Redis approach with a proper graph database architecture.
"""

import os
import asyncio
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from dataclasses import asdict
from functools import wraps

from flask import current_app

from .domain.models import Book, User, Author, Publisher, Series, Category, UserBookRelationship, ReadingLog, ReadingStatus
from .infrastructure.kuzu_repositories import KuzuBookRepository, KuzuUserRepository, KuzuAuthorRepository
from .infrastructure.kuzu_graph import get_graph_storage
from app.domain.models import ImportMappingTemplate, ReadingStatus


def run_async(async_func):
    """Decorator to run async functions synchronously for Flask compatibility."""
    @wraps(async_func)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            # If we're already in an async context, create a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Create the coroutine in the executor thread
                def run_in_new_loop():
                    new_loop = asyncio.new_event_loop()
                    try:
                        return new_loop.run_until_complete(async_func(*args, **kwargs))
                    finally:
                        new_loop.close()
                future = executor.submit(run_in_new_loop)
                return future.result()
        else:
            return loop.run_until_complete(async_func(*args, **kwargs))
    return wrapper


class KuzuBookService:
    """Service for managing books using Kuzu as primary database."""
    
    def __init__(self):
        self.graph_storage = get_graph_storage()
        self.book_repo = KuzuBookRepository(self.graph_storage)
        self.author_repo = KuzuAuthorRepository(self.graph_storage)
        self.user_repo = KuzuUserRepository(self.graph_storage)
    
    @run_async
    async def create_book(self, domain_book: Book, user_id: str) -> Book:
        """Create a book in Kuzu."""
        try:
            # Debug logging
            print(f"create_book called with domain_book type: {type(domain_book)}")
            print(f"domain_book title: {getattr(domain_book, 'title', 'NO TITLE ATTR')}")
            print(f"user_id: {user_id}")
            
            # Ensure the book has an ID
            if not domain_book.id:
                domain_book.id = str(uuid.uuid4())
                print(f"Generated book ID: {domain_book.id}")
            
            # Set timestamps
            domain_book.created_at = datetime.utcnow()
            domain_book.updated_at = datetime.utcnow()
            
            print(f"About to call book_repo.create")
            # Create the book in Kuzu
            created_book = await self.book_repo.create(domain_book)
            print(f"book_repo.create returned: {created_book}")
            
            # Create user-book relationship
            relationship = UserBookRelationship(
                user_id=str(user_id),
                book_id=created_book.id,
                reading_status=ReadingStatus.PLAN_TO_READ,
                date_added=datetime.utcnow()
            )
            
            # Store the relationship in Kuzu
            rel_key = f"user_book:{user_id}:{created_book.id}"
            rel_data = asdict(relationship)
            
            # Serialize datetime and enum objects for JSON storage
            def serialize_for_json(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif hasattr(obj, 'value'):  # Enum
                    return obj.value
                elif isinstance(obj, dict):
                    return {k: serialize_for_json(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [serialize_for_json(item) for item in obj]
                else:
                    return obj
            
            rel_data = serialize_for_json(rel_data)
            print(f"Storing relationship data: {rel_data}")
            
            await self.graph_storage.set_json(rel_key, rel_data)
            print(f"Successfully stored relationship")
            
            print(f"Created book {created_book.id} for user {user_id} in Kuzu")
            return created_book
            
        except Exception as e:
            print(f"Error in create_book: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    @run_async
    async def get_book_by_id(self, book_id: str) -> Optional[Book]:
        """Get a book by ID."""
        return await self.book_repo.get_by_id(book_id)
    
    @run_async
    async def get_books_for_user(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Book]:
        """Get all books for a user with relationship data."""
        # Find all user-book relationships for this user
        pattern = f"user_book:{user_id}:*"
        relationship_keys = await self.graph_storage.scan_keys(pattern)
        
        books = []
        for rel_key in relationship_keys[offset:offset + limit]:
            # Extract book_id from the key
            book_id = rel_key.split(':')[-1]
            book = await self.book_repo.get_by_id(book_id)
            if book:
                # Get the user-book relationship data
                relationship_data = await self.graph_storage.get_json(rel_key)
                if relationship_data:
                    # Add user relationship attributes to the book object
                    book.reading_status = relationship_data.get('reading_status', 'plan_to_read')
                    book.ownership_status = relationship_data.get('ownership_status', 'owned')
                    book.start_date = relationship_data.get('start_date')
                    book.finish_date = relationship_data.get('finish_date')
                    book.user_rating = relationship_data.get('user_rating')
                    book.personal_notes = relationship_data.get('personal_notes')
                    book.date_added = relationship_data.get('date_added')
                    book.want_to_read = relationship_data.get('reading_status') == 'plan_to_read'
                    book.library_only = relationship_data.get('reading_status') == 'library_only'
                    book.uid = book.id  # Ensure uid is available
                    
                    # Convert date strings back to date objects if needed
                    if isinstance(book.start_date, str):
                        try:
                            book.start_date = datetime.fromisoformat(book.start_date).date()
                        except:
                            book.start_date = None
                    if isinstance(book.finish_date, str):
                        try:
                            book.finish_date = datetime.fromisoformat(book.finish_date).date()
                        except:
                            book.finish_date = None
                            
                books.append(book)
        
        return books
    
    @run_async
    async def search_books(self, query: str, user_id: str, limit: int = 50) -> List[Book]:
        """Search books for a user."""
        # Get all user books first
        user_books = await self.get_books_for_user(user_id, limit=1000)  # Get all books for filtering
        
        # Simple text search across title and authors
        query_lower = query.lower()
        filtered_books = []
        
        for book in user_books:
            if (query_lower in book.title.lower() or 
                any(query_lower in author.name.lower() for author in book.authors)):
                filtered_books.append(book)
                if len(filtered_books) >= limit:
                    break
        
        return filtered_books
    
    @run_async 
    async def update_book(self, book_id: str, updates: Dict[str, Any], user_id: str) -> Optional[Book]:
        """Update a book."""
        book = await self.book_repo.get_by_id(book_id)
        if not book:
            return None
        
        # Update fields
        for field, value in updates.items():
            if hasattr(book, field):
                setattr(book, field, value)
        
        book.updated_at = datetime.utcnow()
        return await self.book_repo.update(book)
    
    @run_async
    async def delete_book(self, book_id: str, user_id: str) -> bool:
        """Delete a book."""
        # Delete user-book relationship
        rel_key = f"user_book:{user_id}:{book_id}"
        await self.graph_storage.delete_key(rel_key)
        
        # Check if any other users have this book
        pattern = f"user_book:*:{book_id}"
        other_relationships = await self.graph_storage.scan_keys(pattern)
        
        # If no other users have this book, delete the book itself
        if not other_relationships:
            return await self.book_repo.delete(book_id)
        
        return True
    
    @run_async
    async def get_books_with_sharing_users(self, days_back: int = 30, limit: int = 20) -> List[Book]:
        """Get books from users who share reading activity, finished in the last N days."""
        # Get all users who share reading activity
        sharing_users = await self.user_repo.get_all()
        sharing_user_ids = [u.id for u in sharing_users if u.share_reading_activity and u.is_active]
        
        if not sharing_user_ids:
            return []
        
        # Get all books for sharing users
        all_books = []
        for user_id in sharing_user_ids:
            books = await self.book_repo.get_books_for_user(user_id)
            all_books.extend(books)
        
        # Filter for finished books in the specified time range
        cutoff_date = date.today() - timedelta(days=days_back)
        finished_books = [
            book for book in all_books 
            if book.finish_date and book.finish_date >= cutoff_date
        ]
        
        # Sort by finish date descending and limit
        finished_books.sort(key=lambda b: b.finish_date or date.min, reverse=True)
        return finished_books[:limit]
    
    @run_async
    async def get_currently_reading_shared(self, limit: int = 20) -> List[Book]:
        """Get currently reading books from users who share current reading."""
        # Get all users who share current reading
        sharing_users = await self.user_repo.get_all()
        sharing_user_ids = [u.id for u in sharing_users if u.share_current_reading and u.is_active]
        
        if not sharing_user_ids:
            return []
        
        # Get all books for sharing users
        all_books = []
        for user_id in sharing_user_ids:
            books = await self.book_repo.get_books_for_user(user_id)
            all_books.extend(books)
        
        # Filter for currently reading (has start_date but no finish_date)
        currently_reading = [
            book for book in all_books 
            if book.start_date and not book.finish_date
        ]
        
        # Sort by start date descending and limit
        currently_reading.sort(key=lambda b: b.start_date or date.min, reverse=True)
        return currently_reading[:limit]
    
    @run_async
    async def get_book_by_isbn_for_user(self, isbn: str, user_id: str) -> Optional[Book]:
        """Get a book by ISBN for a specific user."""
        books = await self.get_books_for_user(user_id, limit=1000)  # Get enriched books
        for book in books:
            if book.isbn == isbn:
                return book
        return None
    
    @run_async
    async def get_book_by_id_for_user(self, book_id: str, user_id: str) -> Optional[Book]:
        """Get a specific book for a user with relationship data."""
        book = await self.book_repo.get_by_id(book_id)
        if not book:
            return None
            
        # Check if user has this book
        relationship_key = f"user_book:{user_id}:{book_id}"
        relationship_data = await self.graph_storage.get_json(relationship_key)
        if not relationship_data:
            return None
            
        # Add user relationship attributes to the book object
        book.reading_status = relationship_data.get('reading_status', 'plan_to_read')
        book.ownership_status = relationship_data.get('ownership_status', 'owned')
        book.start_date = relationship_data.get('start_date')
        book.finish_date = relationship_data.get('finish_date')
        book.user_rating = relationship_data.get('user_rating')
        book.personal_notes = relationship_data.get('personal_notes')
        book.date_added = relationship_data.get('date_added')
        book.want_to_read = relationship_data.get('reading_status') == 'plan_to_read'
        book.library_only = relationship_data.get('reading_status') == 'library_only'
        book.uid = book.id  # Ensure uid is available
        
        # Convert date strings back to date objects if needed
        if isinstance(book.start_date, str):
            try:
                book.start_date = datetime.fromisoformat(book.start_date).date()
            except:
                book.start_date = None
        if isinstance(book.finish_date, str):
            try:
                book.finish_date = datetime.fromisoformat(book.finish_date).date()
            except:
                book.finish_date = None
        
        # Load custom metadata for this user-book combination
        try:
            custom_metadata = {}
            # Query for HAS_CUSTOM_FIELD relationships from this user for this book
            query = """
            MATCH (u:User {id: $user_id})-[r:HAS_CUSTOM_FIELD]->(cf:CustomField)
            WHERE r.book_id = $book_id
            RETURN cf.name, cf.value
            """
            
            results = self.graph_storage.query(query, {
                "user_id": user_id,
                "book_id": book_id
            })
            
            for result in results:
                # Extract field name and value from result
                if len(result) >= 2:
                    field_name = list(result.values())[0]  # First column
                    field_value = list(result.values())[1]  # Second column
                    if field_name and field_value:
                        custom_metadata[field_name] = field_value
                        
            book.custom_metadata = custom_metadata
            print(f"🔍 [LOAD_CUSTOM_META] Loaded {len(custom_metadata)} custom fields for book {book_id}, user {user_id}: {custom_metadata}")
        except Exception as e:
            print(f"❌ Error loading custom metadata for book {book_id}, user {user_id}: {e}")
            import traceback
            traceback.print_exc()
            book.custom_metadata = {}
                
        return book

    # Sync wrappers for Flask compatibility
    def create_book_sync(self, domain_book: Book, user_id: str) -> Book:
        """Sync wrapper for create_book."""
        # create_book already has @run_async decorator, so just call it directly
        return self.create_book(domain_book, user_id)
    
    def get_book_by_id_sync(self, book_id: str) -> Optional[Book]:
        """Sync wrapper for get_book_by_id."""
        # get_book_by_id already has @run_async decorator, so just call it directly
        return self.get_book_by_id(book_id)
    
    def get_book_by_uid_sync(self, uid: str, user_id: str) -> Optional[Book]:
        """Sync wrapper for get_book_by_id_for_user (uid is same as book_id)."""
        # get_book_by_id_for_user already has @run_async decorator, so just call it directly
        return self.get_book_by_id_for_user(uid, user_id)
    
    def get_user_book_sync(self, user_id: str, book_id: str) -> Optional[Dict[str, Any]]:
        """Get user's book by book ID - alias for get_book_by_uid_sync for compatibility."""
        result = self.get_book_by_uid_sync(book_id, user_id)
        if result:
            # Convert Book object to dictionary if needed
            if hasattr(result, '__dict__'):
                return result.__dict__
            elif isinstance(result, dict):
                return result
            else:
                # Try to convert to dict
                try:
                    return vars(result)
                except:
                    # Fallback - create basic dict
                    return {
                        'id': getattr(result, 'id', book_id),
                        'title': getattr(result, 'title', 'Unknown'),
                        'custom_metadata': getattr(result, 'custom_metadata', {})
                    }
        return None
    
    def get_user_books_sync(self, user_id: str) -> List[Book]:
        """Sync wrapper for get_books_for_user."""
        # get_books_for_user already has @run_async decorator, so just call it directly
        return self.get_books_for_user(user_id)
    
    def search_books_sync(self, query: str, user_id: str) -> List[Book]:
        """Sync wrapper for search_books."""
        # search_books already has @run_async decorator, so just call it directly
        return self.search_books(query, user_id)
    
    def update_book_sync(self, book_id: str, user_id: str, **kwargs) -> Optional[Book]:
        """Sync wrapper for update_book."""
        # update_book already has @run_async decorator, so just call it directly
        return self.update_book(book_id, kwargs, user_id)
    
    def delete_book_sync(self, book_id: str, user_id: str) -> bool:
        """Sync wrapper for delete_book."""
        # delete_book already has @run_async decorator, so just call it directly
        return self.delete_book(book_id, user_id)
    
    def get_books_with_sharing_users_sync(self, days_back: int = 30, limit: int = 20) -> List[Book]:
        """Sync wrapper for get_books_with_sharing_users."""
        return self.get_books_with_sharing_users(days_back, limit)
    
    def get_currently_reading_shared_sync(self, limit: int = 20) -> List[Book]:
        """Sync wrapper for get_currently_reading_shared."""
        return self.get_currently_reading_shared(limit)
    
    def get_book_by_isbn_for_user_sync(self, isbn: str, user_id: str) -> Optional[Book]:
        """Sync wrapper for get_book_by_isbn_for_user."""
        return self.get_book_by_isbn_for_user(isbn, user_id)
    
    def bulk_import_books_sync(self, user_id: str, csv_path: str, default_status: str) -> str:
        """Sync wrapper for bulk import books from CSV file.
        
        Args:
            user_id: The user ID to import books for
            csv_path: Path to the CSV file containing book data
            default_status: Default status to assign to imported books
            
        Returns:
            A task ID representing the bulk import operation
        """
        import uuid
        import csv
        import os
        
        task_id = str(uuid.uuid4())
        
        try:
            # Simple synchronous CSV processing for now
            books_imported = 0
            rows_processed = 0
            
            print(f"Starting bulk import from: {csv_path}")
            print(f"File exists: {os.path.exists(csv_path)}")
            
            if os.path.exists(csv_path):
                with open(csv_path, 'r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    print(f"CSV headers: {reader.fieldnames}")
                    
                    for row in reader:
                        rows_processed += 1
                        print(f"Processing row {rows_processed}: {row}")
                        
                        try:
                            # Handle different CSV formats
                            title = ''
                            author = ''
                            isbn = ''
                            
                            # Check if this is a headerless ISBN-only file
                            if len(reader.fieldnames) == 1 and reader.fieldnames[0].startswith('978'):
                                # This is likely an ISBN-only file where the "header" is actually the first ISBN
                                # Get the ISBN from the single column
                                first_col = list(row.values())[0] if row else reader.fieldnames[0]
                                if rows_processed == 1:
                                    # First row, use the "header" as the first ISBN
                                    isbn = reader.fieldnames[0]
                                else:
                                    # Subsequent rows
                                    isbn = first_col
                                print(f"ISBN-only format detected. ISBN: '{isbn}'")
                            else:
                                # Handle standard CSV with headers
                                # Try different column name variations for title
                                title = (row.get('Title') or row.get('title') or 
                                        row.get('Book Title') or row.get('book_title') or '').strip()
                                
                                # Try different column name variations for author
                                author = (row.get('Author') or row.get('author') or 
                                         row.get('Authors') or row.get('authors') or
                                         row.get('Author l-f') or '').strip()
                                
                                # Try different column name variations for ISBN
                                isbn = (row.get('ISBN') or row.get('isbn') or 
                                       row.get('ISBN13') or row.get('isbn13') or
                                       row.get('ISBN/UID') or row.get('isbn_uid') or '').strip()
                                
                                # Clean up ISBN (remove quotes and equals signs from Goodreads export)
                                if isbn:
                                    isbn = isbn.replace('="', '').replace('"', '').replace('=', '')
                            
                            print(f"Extracted - Title: '{title}', Author: '{author}', ISBN: '{isbn}'")
                            
                            # For ISBN-only imports, we'll try to fetch book data from external APIs
                            if isbn and not title:
                                print(f"ISBN-only import detected. Will try to fetch book data for ISBN: {isbn}")
                                # We have ISBN but no title/author, so we'll create a minimal book
                                # and let the system fetch metadata later
                                title = f"Book {isbn}"  # Temporary title
                                author = "Unknown Author"  # Temporary author
                            
                            if title:  # Only import if we have at least a title
                                # Create a basic Book object for import
                                book = Book(
                                    title=title,
                                    isbn13=isbn if len(isbn) == 13 else None,
                                    isbn10=isbn if len(isbn) == 10 else None,
                                    authors=[Author(name=author)] if author else []
                                )
                                
                                print(f"Created book object: {book}")
                                
                                # Use existing create_book method
                                created_book = self.create_book_sync(book, user_id)
                                if created_book:
                                    books_imported += 1
                                    print(f"Successfully created book: {created_book.id}")
                                else:
                                    print(f"Failed to create book: {book.title}")
                            else:
                                print(f"Skipping row - no title or ISBN found")
                        except Exception as e:
                            print(f"Error importing book row {rows_processed}: {e}")
                            import traceback
                            traceback.print_exc()
                            continue
            else:
                print(f"CSV file not found: {csv_path}")
            
            print(f"Bulk import completed. Processed {rows_processed} rows, imported {books_imported} books with task ID: {task_id}")
            return task_id
            
        except Exception as e:
            print(f"Bulk import error: {e}")
            import traceback
            traceback.print_exc()
            return task_id


# Create service instances
kuzu_book_service = KuzuBookService()

class KuzuImportMappingRepository:
    """Repository for managing import mapping templates in Kuzu."""
    
    def __init__(self, storage):
        self.storage = storage
    
    async def create(self, template: ImportMappingTemplate) -> ImportMappingTemplate:
        """Create a new import mapping template."""
        template.id = str(uuid.uuid4())  # Generate a new ID for the template
        template.created_at = datetime.utcnow()
        template.updated_at = datetime.utcnow()
        
        template_key = f"template:{template.id}"
        
        # Serialize the template data
        template_data = template.to_dict()
        
        # Save to Kuzu
        await self.storage.set_json(template_key, template_data)
        
        return template

    async def get_by_id(self, template_id: str) -> Optional[ImportMappingTemplate]:
        """Get an import mapping template by ID."""
        template_key = f"template:{template_id}"
        template_data = await self.storage.get_json(template_key)
        
        if not template_data:
            return None
        
        # Deserialize the template data
        template_data['id'] = template_id
        template = ImportMappingTemplate(**template_data)
        return template

    async def update(self, template: ImportMappingTemplate) -> ImportMappingTemplate:
        """Update an existing template."""
        template_key = f"template:{template.id}"
        
        # Check if the template exists
        if not await self.storage.exists(template_key):
            raise ValueError(f"Template with id {template.id} not found")

        # Serialize the updated template data
        template.updated_at = datetime.utcnow()
        template_data = template.to_dict()

        # Save the updated data to Kuzu
        await self.storage.set_json(template_key, template_data)
        
        return template

    async def delete(self, template_id: str) -> bool:
        """Delete an import mapping template by ID."""
        template_key = f"template:{template_id}"
        result = await self.storage.delete(template_key)
        return result

    async def get_all(self) -> List[ImportMappingTemplate]:
        """Get all import mapping templates."""
        template_keys = await self.storage.scan_keys("template:*")
        templates = []
        
        for key in template_keys:
            template_data = await self.storage.get_json(key)
            if template_data:
                template_data['id'] = key.split(':')[1]  # Extract ID from key
                template = ImportMappingTemplate(**template_data)
                templates.append(template)
        
        return templates


class KuzuJobService:
    """Service for managing import jobs using Kuzu graph database."""
    
    def __init__(self):
        self._storage = None
    
    @property
    def storage(self):
        """Lazy initialization of storage."""
        if self._storage is None:
            self._storage = get_graph_storage()
        return self._storage
    
    @run_async
    async def store_job(self, task_id: str, job_data: dict) -> bool:
        """Store import job data in Kuzu."""
        try:
            import json
            from datetime import datetime, timedelta
            
            # Set expiration time (24 hours from now)
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            # Prepare job data for Kuzu storage
            job_record = {
                'id': f"job_{task_id}",
                'task_id': task_id,
                'user_id': job_data.get('user_id', ''),
                'csv_file_path': job_data.get('csv_file_path', ''),
                'field_mappings': json.dumps(job_data.get('field_mappings', {})),
                'default_reading_status': job_data.get('default_reading_status', ''),
                'duplicate_handling': job_data.get('duplicate_handling', 'skip'),
                'custom_fields_enabled': job_data.get('custom_fields_enabled', False),
                'status': job_data.get('status', 'pending'),
                'processed': job_data.get('processed', 0),
                'success': job_data.get('success', 0),
                'errors': job_data.get('errors', 0),
                'total': job_data.get('total', 0),
                'start_time': datetime.fromisoformat(job_data['start_time']) if isinstance(job_data.get('start_time'), str) else job_data.get('start_time', datetime.utcnow()),
                'end_time': datetime.fromisoformat(job_data['end_time']) if job_data.get('end_time') and isinstance(job_data.get('end_time'), str) else job_data.get('end_time'),
                'current_book': job_data.get('current_book', ''),
                'error_messages': json.dumps(job_data.get('error_messages', [])),
                'recent_activity': json.dumps(job_data.get('recent_activity', [])),
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'expires_at': expires_at
            }
            
            # Use the store_node method to create the job
            success = self.storage.store_node('ImportJob', f"job_{task_id}", job_record)
            
            if success:
                print(f"✅ Stored job {task_id} in Kuzu")
            else:
                print(f"❌ Failed to store job {task_id} in Kuzu")
            return success
            
        except Exception as e:
            print(f"❌ Error storing job {task_id} in Kuzu: {e}")
            return False
    
    @run_async
    async def get_job(self, task_id: str) -> Optional[dict]:
        """Retrieve import job data from Kuzu."""
        try:
            import json
            
            # Get the job node by task_id
            job_record = self.storage.get_node('ImportJob', f"job_{task_id}")
            
            if job_record:
                # Check if the job has expired
                expires_at = job_record.get('expires_at')
                if expires_at and isinstance(expires_at, datetime) and expires_at < datetime.utcnow():
                    print(f"❌ Job {task_id} has expired")
                    return None
                
                # Convert back to the expected job data format
                job_data = {
                    'task_id': job_record.get('task_id'),
                    'user_id': job_record.get('user_id'),
                    'csv_file_path': job_record.get('csv_file_path'),
                    'field_mappings': json.loads(job_record.get('field_mappings', '{}')),
                    'default_reading_status': job_record.get('default_reading_status'),
                    'duplicate_handling': job_record.get('duplicate_handling'),
                    'custom_fields_enabled': job_record.get('custom_fields_enabled', False),
                    'status': job_record.get('status'),
                    'processed': job_record.get('processed', 0),
                    'success': job_record.get('success', 0),
                    'errors': job_record.get('errors', 0),
                    'total': job_record.get('total', 0),
                    'start_time': job_record.get('start_time').isoformat() if job_record.get('start_time') else None,
                    'end_time': job_record.get('end_time').isoformat() if job_record.get('end_time') else None,
                    'current_book': job_record.get('current_book'),
                    'error_messages': json.loads(job_record.get('error_messages', '[]')),
                    'recent_activity': json.loads(job_record.get('recent_activity', '[]'))
                }
                
                print(f"✅ Retrieved job {task_id} from Kuzu")
                return job_data
            else:
                print(f"❌ Job {task_id} not found in Kuzu")
                return None
                
        except Exception as e:
            print(f"❌ Error retrieving job {task_id} from Kuzu: {e}")
            return None
    
    @run_async
    async def update_job(self, task_id: str, updates: dict) -> bool:
        """Update specific fields in an import job stored in Kuzu."""
        try:
            import json
            from datetime import datetime
            
            # Prepare updates by filtering out system fields and serializing JSON fields
            clean_updates = {}
            
            # Define fields that should be datetime objects
            datetime_fields = {'start_time', 'end_time', 'created_at', 'updated_at', 'expires_at'}
            
            for key, value in updates.items():
                # Skip system fields
                if key in ['id', '_id']:
                    continue
                    
                # Handle JSON fields
                if key in ['error_messages', 'recent_activity', 'field_mappings']:
                    if isinstance(value, (list, dict)):
                        value = json.dumps(value)
                elif key in datetime_fields and isinstance(value, str) and value:
                    # Convert ISO timestamp strings to datetime objects
                    try:
                        if value.endswith('Z'):
                            value = value[:-1] + '+00:00'
                        value = datetime.fromisoformat(value)
                    except (ValueError, TypeError):
                        # If conversion fails, keep as string and let Kuzu handle it
                        pass
                        
                clean_updates[key] = value
            
            # Add updated timestamp
            clean_updates['updated_at'] = datetime.utcnow()
            
            # Use update_node method with only the clean updates
            success = self.storage.update_node('ImportJob', f"job_{task_id}", clean_updates)
            
            if success:
                print(f"✅ Updated job {task_id} in Kuzu with: {list(updates.keys())}")
            else:
                print(f"❌ Failed to update job {task_id} in Kuzu")
            return success
            
        except Exception as e:
            print(f"❌ Error updating job {task_id} in Kuzu: {e}")
            return False
    
    @run_async
    async def delete_expired_jobs(self) -> int:
        """Delete expired import jobs from Kuzu."""
        try:
            # Use execute_cypher to delete expired jobs
            query = """
            MATCH (j:ImportJob)
            WHERE j.expires_at < $current_time
            DELETE j
            """
            
            result = self.storage.execute_cypher(query, {
                'current_time': datetime.utcnow()
            })
            
            print(f"✅ Cleaned up expired jobs from Kuzu")
            return 0  # Kuzu doesn't return delete count easily
            
        except Exception as e:
            print(f"❌ Error cleaning up expired jobs from Kuzu: {e}")
            return 0


# Global service instances
job_service = KuzuJobService()

class KuzuUserBookService:
    """Service for managing user-book relationships in Kuzu."""
    
    def __init__(self):
        self.graph_storage = get_graph_storage()
    
    @run_async
    async def update_user_book(self, user_id: str, book_id: str, custom_metadata: Dict[str, Any] = None, **kwargs) -> bool:
        """Update user-book relationship with custom metadata."""
        try:
            if not custom_metadata:
                return True  # Nothing to update
            
            # For each custom field, create or update the HAS_CUSTOM_FIELD relationship
            for field_name, field_value in custom_metadata.items():
                if field_value is not None and field_value != '':
                    # Create a CustomField node for this field
                    field_node_id = f"custom_{user_id}_{book_id}_{field_name}"
                    
                    # Store the custom field
                    field_data = {
                        'id': field_node_id,
                        'name': field_name,
                        'field_type': 'text',  # Default to text for now
                        'value': str(field_value),
                        'created_at': datetime.utcnow()
                    }
                    
                    success = self.graph_storage.store_node('CustomField', field_node_id, field_data)
                    if success:
                        # Create the HAS_CUSTOM_FIELD relationship
                        rel_props = {
                            'book_id': book_id,
                            'field_name': field_name
                        }
                        self.graph_storage.create_relationship('User', user_id, 'HAS_CUSTOM_FIELD', 'CustomField', field_node_id, rel_props)
                        print(f"✅ Saved custom field {field_name} = {field_value} for user {user_id}, book {book_id}")
                    else:
                        print(f"❌ Failed to save custom field {field_name}")
                        
            return True
            
        except Exception as e:
            print(f"❌ Error updating user book custom metadata: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_user_book_sync(self, user_id: str, book_id: str, custom_metadata: Dict[str, Any] = None, **kwargs) -> bool:
        """Synchronous version of update_user_book."""
        try:
            print(f"🔍 [UPDATE_USER_BOOK] Called with user_id={user_id}, book_id={book_id}, custom_metadata={custom_metadata}")
            
            if not custom_metadata:
                print(f"🔍 [UPDATE_USER_BOOK] No custom metadata to update")
                return True  # Nothing to update
            
            # Verify user and book exist
            user_exists = self.graph_storage.get_node('User', user_id)
            book_exists = self.graph_storage.get_node('Book', book_id)
            print(f"🔍 [UPDATE_USER_BOOK] User exists: {user_exists is not None}, Book exists: {book_exists is not None}")
            
            if not user_exists:
                print(f"❌ [UPDATE_USER_BOOK] User {user_id} not found")
                return False
            if not book_exists:
                print(f"❌ [UPDATE_USER_BOOK] Book {book_id} not found")
                return False
            
            # For each custom field, create or update the HAS_CUSTOM_FIELD relationship
            for field_name, field_value in custom_metadata.items():
                print(f"🔍 [UPDATE_USER_BOOK] Processing field {field_name} = {field_value}")
                
                if field_value is not None and field_value != '':
                    # Create a CustomField node for this field
                    field_node_id = f"custom_{user_id}_{book_id}_{field_name}"
                    print(f"🔍 [UPDATE_USER_BOOK] Creating CustomField node with id: {field_node_id}")
                    
                    # Store the custom field
                    field_data = {
                        'id': field_node_id,
                        'name': field_name,
                        'field_type': 'text',  # Default to text for now
                        'value': str(field_value),
                        'created_at': datetime.utcnow()
                    }
                    
                    success = self.graph_storage.store_node('CustomField', field_node_id, field_data)
                    print(f"🔍 [UPDATE_USER_BOOK] CustomField node creation success: {success}")
                    
                    if success:
                        # Create the HAS_CUSTOM_FIELD relationship
                        rel_props = {
                            'book_id': book_id,
                            'field_name': field_name
                        }
                        rel_success = self.graph_storage.create_relationship('User', user_id, 'HAS_CUSTOM_FIELD', 'CustomField', field_node_id, rel_props)
                        print(f"🔍 [UPDATE_USER_BOOK] Relationship creation success: {rel_success}")
                        
                        if rel_success:
                            print(f"✅ Saved custom field {field_name} = {field_value} for user {user_id}, book {book_id}")
                        else:
                            print(f"❌ Failed to create relationship for custom field {field_name}")
                    else:
                        print(f"❌ Failed to save custom field {field_name}")
                else:
                    print(f"🔍 [UPDATE_USER_BOOK] Skipping empty field {field_name}")
                        
            print(f"🔍 [UPDATE_USER_BOOK] Completed processing all custom fields")
            return True
            
        except Exception as e:
            print(f"❌ Error updating user book custom metadata: {e}")
            import traceback
            traceback.print_exc()
            return False


# Global service instances
user_book_service = KuzuUserBookService()
