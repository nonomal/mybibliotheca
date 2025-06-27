# Migration from SQL to Kuzu

This guide helps you migrate your existing SQLite MyBibliotheca database to the new Kuzu graph database.

## Prerequisites

MyBibliotheca now uses Kuzu graph database exclusively. If you have an existing SQLite database (`books.db`), you can migrate it to Kuzu.

## Migration Steps

### 1. Install Migration Dependencies (Optional)

The migration script requires SQLAlchemy which is not installed by default:

```bash
# Using pip
pip install flask-sqlalchemy

# Using uv (if you're using uv)
uv add --optional migration flask-sqlalchemy
```

### 2. Run the Migration

```bash
python migrate_to_kuzu.py
```

This will:
- Create a backup of your original `books.db` file
- Convert all users, books, and reading logs to Kuzu format
- Verify the migration was successful

### 3. Start the Application

After successful migration, start your app normally:

```bash
python run.py
# or
gunicorn run:app
```

## What Gets Migrated

- **Users**: All user accounts with passwords, admin status, and privacy settings
- **Books**: All books with metadata, reading status, and dates
- **Reading Logs**: All reading activity and history
- **Relationships**: User-book ownership and reading log associations

## Troubleshooting

### "SQLAlchemy not found" Error

Install the migration dependencies:
```bash
pip install flask-sqlalchemy
```

### "books.db not found" Error

Make sure your SQLite database is located at `data/books.db`.

### Migration Verification Failed

Check the console output for specific errors. Common issues:
- Permissions on the data directory
- Corrupted SQLite database
- Missing required fields

## After Migration

Once migration is complete:
- Your original `books.db` is backed up in `data/backups/`
- The app now uses `data/bibliotheca_graph.db/` (Kuzu database)
- You can uninstall SQLAlchemy if you don't need it: `pip uninstall flask-sqlalchemy`

## Benefits of Kuzu

- **Better Performance**: Graph queries are optimized for relationship traversal
- **Scalability**: Better handling of complex book relationships and user interactions
- **Future Features**: Enables advanced features like book recommendations and social features
