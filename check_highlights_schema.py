#!/usr/bin/env python3
"""
Check highlights table schema and fix category issues
"""

import sqlite3

def check_highlights_schema():
    """Check the highlights table schema"""
    conn = sqlite3.connect('database.db')
    cursor = conn.execute("PRAGMA table_info(highlights)")
    columns = cursor.fetchall()
    
    print("📋 Highlights table schema:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'}")
    
    # Check category constraint
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='highlights'")
    create_sql = cursor.fetchone()[0]
    
    if 'CHECK' in create_sql:
        print("\n🔍 Category constraint found:")
        check_match = re.search(r'CHECK\s*\(\s*category\s+IN\s*\(([^)]+)\)', create_sql, re.IGNORECASE)
        if check_match:
            categories = check_match.group(1).split(',')
            categories = [cat.strip().strip("'\"") for cat in categories]
            print(f"  Allowed categories: {categories}")
    
    # Check current categories in use
    cursor.execute("SELECT DISTINCT category FROM highlights")
    current_categories = [row[0] for row in cursor.fetchall()]
    print(f"\n📊 Current categories in use: {current_categories}")
    
    conn.close()

def fix_category_issues():
    """Fix category issues by mapping old categories to new ones"""
    conn = sqlite3.connect('database.db')
    
    # Category mapping from old to new
    category_mapping = {
        'tech': 'performance',
        'nutri': 'nutrition', 
        'recov': 'performance',
        'psy': 'performance',
        'injury': 'injury',
        'performance': 'performance',
        'training': 'performance',
        'progress': 'performance',
        'issue': 'injury',
        'planning': 'schedule',
        'general': 'other',
        'admin': 'admin'
    }
    
    print("🔄 Fixing category issues...")
    
    for old_cat, new_cat in category_mapping.items():
        cursor = conn.execute(
            "UPDATE highlights SET category = ? WHERE category = ?",
            (new_cat, old_cat)
        )
        if cursor.rowcount > 0:
            print(f"  ✅ Updated {cursor.rowcount} highlights: {old_cat} → {new_cat}")
    
    conn.commit()
    conn.close()
    print("✅ Category issues fixed!")

if __name__ == "__main__":
    import re
    check_highlights_schema()
    print("\n" + "="*50 + "\n")
    fix_category_issues() 