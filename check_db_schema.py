#!/usr/bin/env python3
"""
Check database schema to understand table structures
"""

import sqlite3

def check_schema():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    print("Database Schema Check")
    print("=" * 50)
    
    # Check athletes table
    print("\n1. Athletes table:")
    try:
        cursor.execute("PRAGMA table_info(athletes)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"   {col[1]} ({col[2]})")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Check conversations table
    print("\n2. Conversations table:")
    try:
        cursor.execute("PRAGMA table_info(conversations)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"   {col[1]} ({col[2]})")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Check records table (might be the actual conversations table)
    print("\n3. Records table:")
    try:
        cursor.execute("PRAGMA table_info(records)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"   {col[1]} ({col[2]})")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Check athlete_highlights table
    print("\n4. Athlete highlights table:")
    try:
        cursor.execute("PRAGMA table_info(athlete_highlights)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"   {col[1]} ({col[2]})")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Sample data from conversations/records
    print("\n5. Sample data from conversations:")
    try:
        cursor.execute("SELECT * FROM conversations LIMIT 1")
        row = cursor.fetchone()
        if row:
            print(f"   Found: {row}")
        else:
            print("   No data found")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n6. Sample data from records:")
    try:
        cursor.execute("SELECT * FROM records LIMIT 1")
        row = cursor.fetchone()
        if row:
            print(f"   Found: {row}")
        else:
            print("   No data found")
    except Exception as e:
        print(f"   Error: {e}")
    
    conn.close()

if __name__ == "__main__":
    check_schema()