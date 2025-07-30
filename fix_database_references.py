#!/usr/bin/env python3
"""
Script to fix database references after migration
"""

import re
import os

def fix_file(filepath):
    """Fix athlete_highlights references in a file"""
    print(f"🔧 Fixing {filepath}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace athlete_highlights with highlights
    content = re.sub(r'\bathlete_highlights\b', 'highlights', content)
    
    # Fix specific queries that need different column names
    content = re.sub(r'FROM highlights h\s+LEFT JOIN records r', 'FROM highlights h\n                LEFT JOIN messages m', content)
    content = re.sub(r'r\.transcription', 'm.transcription', content)
    content = re.sub(r'r\.final_response', 'm.final_response', content)
    content = re.sub(r'r\.id', 'm.id', content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Fixed {filepath}")

def main():
    """Main function to fix all files"""
    files_to_fix = [
        'main.py',
        'workflow_service.py',
        'workflow_endpoints.py',
        'verify_migration.py',
        'database_consolidation.py',
        'check_db_schema.py'
    ]
    
    for filepath in files_to_fix:
        if os.path.exists(filepath):
            fix_file(filepath)
        else:
            print(f"⚠️  File {filepath} not found, skipping...")
    
    print("\n🎉 Database references fixed!")

if __name__ == "__main__":
    main() 