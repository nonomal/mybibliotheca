import os
import kuzu
from pathlib import Path

def get_kuzu_db_path():
    """Get the path for Kuzu database"""
    basedir = os.path.abspath(os.path.dirname(__file__))
    data_dir = os.path.join(basedir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, 'bibliotheca_graph.db')

class KuzuDatabase:
    """Kuzu database manager"""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or get_kuzu_db_path()
        self.db = None
        self.conn = None
        
    def connect(self):
        """Establish connection to Kuzu database"""
        try:
            self.db = kuzu.Database(self.db_path)
            self.conn = kuzu.Connection(self.db)
            return True
        except Exception as e:
            print(f"Error connecting to Kuzu database: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn = None
        if self.db:
            self.db = None
    
    def execute_query(self, query, parameters=None):
        """Execute a Cypher query"""
        if not self.conn:
            self.connect()
        
        try:
            if parameters:
                result = self.conn.execute(query, parameters)
            else:
                result = self.conn.execute(query)
            return result
        except Exception as e:
            print(f"Error executing query: {e}")
            print(f"Query: {query}")
            raise
    
    def create_schema(self):
        """Create the graph schema for MyBibliotheca"""
        schema_queries = [
            # Create User node table
            """
            CREATE NODE TABLE User(
                id INT64,
                uid STRING,
                username STRING,
                email STRING,
                password_hash STRING,
                is_admin BOOLEAN,
                is_active BOOLEAN,
                created_at TIMESTAMP,
                failed_login_attempts INT64,
                locked_until TIMESTAMP,
                last_login TIMESTAMP,
                share_current_reading BOOLEAN,
                share_reading_activity BOOLEAN,
                share_library BOOLEAN,
                password_must_change BOOLEAN,
                password_changed_at TIMESTAMP,
                reading_streak_offset INT64,
                PRIMARY KEY(id)
            )
            """,
            
            # Create Book node table
            """
            CREATE NODE TABLE Book(
                id INT64,
                uid STRING,
                title STRING,
                author STRING,
                isbn STRING,
                start_date DATE,
                finish_date DATE,
                cover_url STRING,
                want_to_read BOOLEAN,
                library_only BOOLEAN,
                description STRING,
                published_date STRING,
                page_count INT64,
                categories STRING,
                publisher STRING,
                language STRING,
                average_rating DOUBLE,
                rating_count INT64,
                created_at TIMESTAMP,
                PRIMARY KEY(id)
            )
            """,
            
            # Create ReadingLog node table
            """
            CREATE NODE TABLE ReadingLog(
                id INT64,
                date DATE,
                created_at TIMESTAMP,
                PRIMARY KEY(id)
            )
            """,
            
            # Create relationships
            """
            CREATE REL TABLE OWNS(
                FROM User TO Book,
                created_at TIMESTAMP
            )
            """,
            
            """
            CREATE REL TABLE LOGGED(
                FROM User TO ReadingLog,
                created_at TIMESTAMP
            )
            """,
            
            """
            CREATE REL TABLE READ_ON(
                FROM Book TO ReadingLog,
                created_at TIMESTAMP
            )
            """
        ]
        
        for query in schema_queries:
            try:
                self.execute_query(query)
                print(f"✅ Schema query executed successfully")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"❌ Error executing schema query: {e}")
                    raise
                else:
                    print(f"⚠️ Table already exists, skipping...")
    
    def check_connection(self):
        """Test database connection"""
        try:
            result = self.execute_query("RETURN 'Connected' AS status")
            return True
        except:
            return False

# Global database instance
kuzu_db = KuzuDatabase()
