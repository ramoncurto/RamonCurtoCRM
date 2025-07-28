#!/usr/bin/env python3
"""
Initialize the database with the athlete_highlights table.
Run this script once to add the new table to existing databases.
"""

import sqlite3
import os

DB_PATH = 'database.db'

def init_highlights_table():
    """Initialize the athlete_highlights table."""
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Create the athlete_highlights table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS athlete_highlights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                athlete_id INTEGER,
                highlight_text TEXT NOT NULL,
                category TEXT,
                source_conversation_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (athlete_id) REFERENCES athletes (id),
                FOREIGN KEY (source_conversation_id) REFERENCES records (id)
            )
            """
        )
        
        # Add indexes for better performance
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_highlights_athlete ON athlete_highlights(athlete_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_highlights_category ON athlete_highlights(category)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_highlights_active ON athlete_highlights(is_active)"
        )
        
        conn.commit()
        print("✅ athlete_highlights table created successfully!")
        
        # Verify table creation
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='athlete_highlights'"
        )
        if cursor.fetchone():
            print("✅ Table verification passed")
            
            # Show table structure
            cursor = conn.execute("PRAGMA table_info(athlete_highlights)")
            columns = cursor.fetchall()
            print("\n📋 Table structure:")
            for col in columns:
                print(f"  - {col[1]}: {col[2]}")
        else:
            print("❌ Table creation failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    init_highlights_table()
