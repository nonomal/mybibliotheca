#!/usr/bin/env python3
"""
Fix db.session calls for Kuzu graph models
Converts SQLAlchemy-style db.session calls to Kuzu graph model methods
"""

import os
import re

def fix_db_session_calls(filepath):
    """Fix db.session calls in a single file"""
    print(f"Fixing db.session calls in {filepath}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Common replacements for graph models
    replacements = [
        # db.session.add(model) -> model.save()
        (r'db\.session\.add\(([^)]+)\)\s*\n\s*db\.session\.commit\(\)', r'\1.save()'),
        
        # db.session.commit() -> model.update() (when context suggests update)
        # This is more complex and might need manual review
        
        # db.session.delete(model) -> model.delete()
        (r'db\.session\.delete\(([^)]+)\)\s*\n\s*db\.session\.commit\(\)', r'\1.delete()'),
        
        # Standalone db.session.commit() -> (usually remove or replace with update)
        # We'll comment these out for manual review
        (r'^(\s*)db\.session\.commit\(\)(.*)$', r'\1# TODO: Review - was db.session.commit()\2'),
        
        # Standalone db.session.add() 
        (r'^(\s*)db\.session\.add\(([^)]+)\)(.*)$', r'\1\2.save()  # Was db.session.add()\3'),
        
        # Standalone db.session.delete()
        (r'^(\s*)db\.session\.delete\(([^)]+)\)(.*)$', r'\1\2.delete()  # Was db.session.delete()\3'),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  ✅ Fixed db.session calls in {filepath}")
        return True
    else:
        print(f"  ⏭️  No db.session changes needed in {filepath}")
        return False

def main():
    """Fix all Python files in the app directory"""
    app_dir = "app"
    files_fixed = 0
    
    for filename in os.listdir(app_dir):
        if filename.endswith('.py'):
            filepath = os.path.join(app_dir, filename)
            if fix_db_session_calls(filepath):
                files_fixed += 1
    
    print(f"\n🎉 Fixed db.session calls in {files_fixed} files")
    print("\n⚠️  Please review files with '# TODO: Review' comments for manual fixes")

if __name__ == "__main__":
    main()
