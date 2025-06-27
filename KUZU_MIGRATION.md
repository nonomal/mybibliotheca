# Kuzu Graph Database Migration Guide

## 🚀 Complete Migration from SQL to Kuzu Graph Database

This guide will help you migrate your MyBibliotheca application from SQLite/SQLAlchemy to Kuzu graph database.

## 📋 Prerequisites

- Python 3.8+
- Your existing MyBibliotheca installation with data
- Backup of your current database (recommended)

## 🔧 Installation Steps

### Step 1: Install Kuzu

```bash
# Install Kuzu Python package
pip install kuzu

# Or if using the requirements.txt
pip install -r requirements.txt
```

### Step 2: Run the Migration Script

```bash
# Make the migration script executable
chmod +x migrate_to_kuzu.py

# Run the migration
python migrate_to_kuzu.py
```

The migration script will:
- ✅ Create a backup of your existing SQLite database
- 🏗️ Create the new Kuzu graph database schema
- 📊 Migrate all users, books, and reading logs
- 🔗 Establish proper graph relationships
- ✅ Verify the migration was successful

### Step 3: Update Configuration

The application will automatically use Kuzu by default. To switch back to SQLite (if needed), set:

```bash
export USE_KUZU=false
```

Or modify `config.py`:
```python
USE_KUZU = False
```

## 🎯 Key Benefits of Graph Database

### 1. **Enhanced Relationships**
- Direct relationships between users, books, and reading logs
- Efficient traversal of complex relationships
- Better performance for relationship queries

### 2. **Flexible Schema**
- Easy to add new node types and relationships
- No complex migrations for schema changes
- Natural representation of connected data

### 3. **Advanced Queries**
- Graph-based recommendations
- Social features and community analytics
- Complex book relationships (series, authors, genres)

### 4. **Performance**
- Faster relationship traversals
- Optimized for connected data patterns
- Better scalability for large datasets

## 📊 Database Schema Comparison

### Before (SQL):
```sql
-- Separate tables with foreign keys
Users (id, username, email, ...)
Books (id, title, author, user_id, ...)
ReadingLogs (id, book_id, user_id, date, ...)
```

### After (Graph):
```cypher
// Nodes and relationships
(User)-[:OWNS]->(Book)
(User)-[:LOGGED]->(ReadingLog)
(Book)-[:READ_ON]->(ReadingLog)
```

## 🔄 Migration Details

### What Gets Migrated:

1. **Users**: All user data including authentication and privacy settings
2. **Books**: Complete book metadata and reading status
3. **Reading Logs**: All reading activity with proper relationships
4. **Relationships**: 
   - User owns Book
   - User logged ReadingLog
   - Book read on ReadingLog

### Data Integrity:

- ✅ All data preserved
- ✅ Relationships maintained
- ✅ No data loss
- ✅ Automatic verification

## 🛠️ Troubleshooting

### Common Issues:

1. **Import Error**: `ModuleNotFoundError: No module named 'kuzu'`
   ```bash
   pip install kuzu
   ```

2. **Permission Error**: Database file permissions
   ```bash
   chmod 664 data/books.db
   chmod 755 data/
   ```

3. **Migration Verification Failed**:
   - Check the migration logs
   - Verify all source data is accessible
   - Ensure sufficient disk space

### Rollback Instructions:

If you need to rollback to SQLite:

1. Set `USE_KUZU = False` in config.py
2. Restore from backup if needed:
   ```bash
   cp data/backups/books_pre_kuzu_migration_*.db data/books.db
   ```
3. Restart the application

## 📈 Post-Migration Benefits

### New Features Enabled:

1. **Enhanced Community Features**:
   - Friend networks
   - Book recommendations based on connections
   - Reading group analytics

2. **Advanced Analytics**:
   - Reading pattern analysis
   - Book relationship discovery
   - Social reading insights

3. **Performance Improvements**:
   - Faster community queries
   - Efficient book discovery
   - Optimized user activity tracking

### Future Enhancements:

- 📚 Book series relationships
- 👥 User follow/friend systems
- 🎯 AI-powered recommendations
- 📊 Advanced reading analytics
- 🌐 Social reading features

## 🔒 Security Considerations

- All authentication data is preserved
- Password hashes remain secure
- Privacy settings are maintained
- Access control is unchanged

## 📝 Configuration Options

### Environment Variables:

```bash
# Use Kuzu database (default: true)
export USE_KUZU=true

# Kuzu database path (optional)
export KUZU_DATABASE_PATH=/path/to/graph.db

# Legacy SQLite path (for migration)
export DATABASE_URL=sqlite:///data/books.db
```

### Config File Options:

```python
class Config:
    USE_KUZU = True  # Enable Kuzu graph database
    KUZU_DATABASE_PATH = 'data/bibliotheca_graph.db'
    
    # Legacy settings (kept for migration)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///data/books.db'
```

## 🚦 Testing the Migration

After migration, test these key features:

1. ✅ User login/logout
2. ✅ Book creation and editing
3. ✅ Reading log functionality
4. ✅ Community features
5. ✅ Search and filtering
6. ✅ Admin functions

## 📞 Support

If you encounter issues during migration:

1. Check the migration logs
2. Verify your backup is intact
3. Ensure all prerequisites are met
4. Contact support with specific error messages

## 🎉 Congratulations!

You've successfully migrated to Kuzu graph database! Your MyBibliotheca installation now benefits from:

- 🚀 Enhanced performance
- 🔗 Rich relationship modeling
- 📊 Advanced analytics capabilities
- 🌟 Future-ready architecture

Happy reading! 📚
