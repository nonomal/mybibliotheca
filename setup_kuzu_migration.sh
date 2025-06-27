#!/bin/bash

# MyBibliotheca Kuzu Migration Setup Script
# Run this first to install dependencies for the migration

set -e  # Exit on any error

echo "🔧 MyBibliotheca Kuzu Migration Setup"
echo "====================================="
echo ""

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: No virtual environment detected!"
    echo "   It's highly recommended to activate your virtual environment first:"
    echo "   source venv/bin/activate  (or your venv path)"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled. Please activate your virtual environment and try again."
        exit 0
    fi
else
    echo "✅ Virtual environment detected: $(basename $VIRTUAL_ENV)"
fi

# Use the current Python (which should be from venv if activated)
PYTHON_CMD="python"
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
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

echo ""
echo "🔍 Environment Information:"
echo "  🐍 Python: $($PYTHON_CMD --version)"
echo "  📦 Pip: $($PIP_CMD --version | head -n1)"
echo ""

echo "📦 Installing Kuzu graph database..."
$PIP_CMD install kuzu

echo ""
echo "📦 Updating existing dependencies..."
$PIP_CMD install -r requirements.txt

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "🚀 Ready to migrate! Run the following command:"
echo "   ./migrate_to_kuzu.sh"
echo ""
echo "📋 What was installed:"
echo "  ✅ Kuzu graph database package"
echo "  ✅ Updated existing dependencies"
echo ""
