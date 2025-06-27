#!/bin/bash

# MyBibliotheca Kuzu Migration Script
# This script automates the complete migration from SQLite to Kuzu graph database

set -e  # Exit on any error

echo "🚀 MyBibliotheca Kuzu Migration"
echo "================================"
echo ""

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: No virtual environment detected."
    echo "   It's recommended to run this inside a virtual environment."
    echo ""
fi

# Use the current Python (which should be from venv if activated)
PYTHON_CMD="python"
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
fi

# Check if Python is available
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "❌ Python is required but not found."
    exit 1
fi

# Use pip from the current environment
PIP_CMD="pip"
if ! command -v pip &> /dev/null; then
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
    else
        echo "❌ pip is required but not found."
        exit 1
    fi
fi

# Show environment info
echo "🔍 Environment Information:"
if [ -n "$VIRTUAL_ENV" ]; then
    echo "  📁 Virtual Environment: $(basename $VIRTUAL_ENV)"
fi
echo "  🐍 Python: $($PYTHON_CMD --version)"
echo "  📦 Pip: $($PIP_CMD --version | head -n1)"
echo ""

echo "📦 Installing Kuzu dependencies..."
$PIP_CMD install kuzu

echo "✅ Dependencies installed successfully!"
echo ""

# Check if data directory exists
if [ ! -d "data" ]; then
    echo "❌ Data directory not found. Please run this script from your MyBibliotheca root directory."
    exit 1
fi

# Check if SQLite database exists
if [ ! -f "data/books.db" ]; then
    echo "❌ SQLite database (data/books.db) not found."
    echo "   Make sure you're running this from your MyBibliotheca installation directory."
    exit 1
fi

echo "📋 Pre-migration checklist:"
if [ -n "$VIRTUAL_ENV" ]; then
    echo "  ✅ Virtual environment active"
else
    echo "  ⚠️  No virtual environment (consider using one)"
fi
echo "  ✅ Python available"
echo "  ✅ Kuzu package installed"
echo "  ✅ Data directory found"
echo "  ✅ SQLite database found"
echo ""

# Ask for confirmation
read -p "🤔 Ready to migrate to Kuzu graph database? This will create a backup first. (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Migration cancelled."
    exit 0
fi

echo ""
echo "🔄 Starting migration process..."
echo ""

# Run the migration script
$PYTHON_CMD migrate_to_kuzu.py

# Check if migration was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Migration completed successfully!"
    echo ""
    echo "📊 What happened:"
    echo "  ✅ Created backup of original SQLite database"
    echo "  ✅ Created new Kuzu graph database"
    echo "  ✅ Migrated all users, books, and reading logs"
    echo "  ✅ Established graph relationships"
    echo "  ✅ Verified data integrity"
    echo ""
    echo "🚀 Your application is now using Kuzu graph database!"
    echo ""
    echo "📋 Next steps:"
    echo "  1. Restart your application: $PYTHON_CMD run.py"
    echo "  2. Test login and basic functionality"
    echo "  3. Explore new graph-powered features"
    echo ""
    echo "📁 Backup location: data/backups/"
    echo "📖 For details, see: KUZU_MIGRATION.md"
    echo ""
    echo "🔄 To rollback (if needed):"
    echo "  1. Set USE_KUZU=False in config.py"
    echo "  2. Restore from backup in data/backups/"
    echo ""
else
    echo ""
    echo "❌ Migration failed!"
    echo ""
    echo "🔍 Troubleshooting:"
    echo "  1. Check the error messages above"
    echo "  2. Verify all files are in place"
    echo "  3. Ensure proper permissions on data directory"
    echo "  4. Check KUZU_MIGRATION.md for detailed help"
    echo ""
    echo "💾 Your original database is safe and unchanged."
    exit 1
fi
