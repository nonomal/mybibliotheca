# Kuzu Migration Instructions for Virtual Environment

## Quick Start

If you're using a virtual environment (recommended), follow these steps:

### 1. Activate Your Virtual Environment
```bash
# If using venv
source venv/bin/activate

# If using conda
conda activate your-env-name

# If using virtualenv
source your-env/bin/activate
```

### 2. Install Migration Dependencies
```bash
./setup_kuzu_migration.sh
```

### 3. Run the Migration
```bash
./migrate_to_kuzu.sh
```

### 4. Start Your App
```bash
python run.py
```

## What the Scripts Do

### `setup_kuzu_migration.sh`
- Checks if you're in a virtual environment
- Installs Kuzu graph database package
- Updates existing dependencies
- Prepares for migration

### `migrate_to_kuzu.sh`
- Detects virtual environment automatically
- Uses the correct Python/pip from your venv
- Creates backup of your SQLite database
- Migrates all data to Kuzu graph format
- Verifies migration success

## Troubleshooting

### "No virtual environment detected"
- Make sure you've activated your virtual environment
- Check that `$VIRTUAL_ENV` is set: `echo $VIRTUAL_ENV`

### "Python/pip not found"
- Ensure your virtual environment is properly activated
- Try `which python` and `which pip` to verify paths

### "Permission denied"
- Make scripts executable: `chmod +x *.sh`

### Migration fails
- Check you're in the bibliotheca root directory
- Ensure `data/books.db` exists
- Verify virtual environment has write permissions

## Rollback (if needed)

If you need to rollback to SQLite:
1. Set `USE_KUZU = False` in `config.py`
2. Restore from backup in `data/backups/`
3. Restart your application

## Benefits of Kuzu

After migration, you'll have:
- ✅ Graph-based relationships between users, books, and reading logs
- ✅ More efficient queries for recommendations and analytics
- ✅ Better performance for complex relationship queries
- ✅ Scalable architecture for future features
