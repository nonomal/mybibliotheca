#!/usr/bin/env python3
"""
Fix query syntax for Kuzu graph models
Converts SQLAlchemy-style queries to Kuzu graph model queries
"""

import os
import re

def fix_file(filepath):
    """Fix query syntax in a single file"""
    print(f"Fixing {filepath}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Fix User.query.xxx to User.query().xxx
    content = re.sub(r'User\.query\.(?!filter|all|first|count|get)', 'User.query().', content)
    content = re.sub(r'User\.query\.filter', 'User.query().filter', content)
    content = re.sub(r'User\.query\.all', 'User.query().all', content)
    content = re.sub(r'User\.query\.first', 'User.query().first', content)
    content = re.sub(r'User\.query\.count', 'User.query().count', content)
    content = re.sub(r'User\.query\.get', 'User.query().get', content)
    
    # Fix Book.query.xxx to Book.query().xxx
    content = re.sub(r'Book\.query\.(?!filter|all|first|count|get)', 'Book.query().', content)
    content = re.sub(r'Book\.query\.filter', 'Book.query().filter', content)
    content = re.sub(r'Book\.query\.all', 'Book.query().all', content)
    content = re.sub(r'Book\.query\.first', 'Book.query().first', content)
    content = re.sub(r'Book\.query\.count', 'Book.query().count', content)
    content = re.sub(r'Book\.query\.get', 'Book.query().get', content)
    
    # Fix ReadingLog.query.xxx to ReadingLog.query().xxx
    content = re.sub(r'ReadingLog\.query\.(?!filter|all|first|count|get)', 'ReadingLog.query().', content)
    content = re.sub(r'ReadingLog\.query\.filter', 'ReadingLog.query().filter', content)
    content = re.sub(r'ReadingLog\.query\.all', 'ReadingLog.query().all', content)
    content = re.sub(r'ReadingLog\.query\.first', 'ReadingLog.query().first', content)
    content = re.sub(r'ReadingLog\.query\.count', 'ReadingLog.query().count', content)
    content = re.sub(r'ReadingLog\.query\.get', 'ReadingLog.query().get', content)
    
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  ✅ Fixed {filepath}")
        return True
    else:
        print(f"  ⏭️  No changes needed in {filepath}")
        return False

def main():
    """Fix all Python files in the app directory"""
    app_dir = "app"
    files_fixed = 0
    
    for filename in os.listdir(app_dir):
        if filename.endswith('.py'):
            filepath = os.path.join(app_dir, filename)
            if fix_file(filepath):
                files_fixed += 1
    
    print(f"\n🎉 Fixed {files_fixed} files")

if __name__ == "__main__":
    main()
