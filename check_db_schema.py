#!/usr/bin/env python3
import sqlite3

def check_database():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Check all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("Tables in database:")
    for table in tables:
        print(f"  {table[0]}")
    
    # Check athlete_highlights table if it exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='athlete_highlights'")
    if cursor.fetchone():
        print("\nathlete_highlights table exists")
        cursor.execute("SELECT DISTINCT category FROM athlete_highlights")
        categories = cursor.fetchall()
        print("Categories in athlete_highlights:")
        for cat in categories:
            print(f"  {cat[0]}")
    else:
        print("\nathlete_highlights table does not exist")
    
    # Check messages table schema
    cursor.execute("PRAGMA table_info(messages)")
    columns = cursor.fetchall()
    print("\nMessages table columns:")
    for col in columns:
        print(f"  {col[1]} {col[2]}")
    
    conn.close()

if __name__ == "__main__":
    check_database()