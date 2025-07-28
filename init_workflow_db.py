#!/usr/bin/env python3
"""
Initialize database tables for the complete workflow system
"""

import sqlite3
import os
from datetime import datetime

def init_workflow_database():
    """Initialize the database with new workflow tables"""
    
    DB_PATH = 'database.db'
    
    # Create database connection
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("🔧 Initializing workflow database...")
    
    # Drop existing highlights table if it exists to update schema
    cursor.execute("DROP TABLE IF EXISTS highlights")
    
    # 1. Conversations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            topic TEXT,
            channel TEXT DEFAULT 'unified',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id)
        )
    """)
    
    # 2. Messages table (core entity)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            athlete_id INTEGER NOT NULL,
            source_channel TEXT NOT NULL,
            source_message_id TEXT,
            direction TEXT CHECK(direction IN ('in', 'out')) NOT NULL,
            content_text TEXT,
            content_audio_url TEXT,
            transcription TEXT,
            metadata_json TEXT,
            dedupe_hash TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id),
            FOREIGN KEY (athlete_id) REFERENCES athletes(id)
        )
    """)
    
    # 3. Highlights table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS highlights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            message_id INTEGER,
            highlight_text TEXT NOT NULL,
            category TEXT CHECK(category IN ('injury', 'schedule', 'performance', 'admin', 'nutrition', 'other')) DEFAULT 'other',
            score REAL DEFAULT 0.0,
            source TEXT CHECK(source IN ('ai', 'manual')) DEFAULT 'manual',
            status TEXT CHECK(status IN ('suggested', 'accepted', 'rejected')) DEFAULT 'accepted',
            reviewed_by TEXT,
            is_manual BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id),
            FOREIGN KEY (message_id) REFERENCES messages(id)
        )
    """)
    
    # 4. Todos table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            message_id INTEGER,
            title TEXT NOT NULL,
            details TEXT,
            status TEXT CHECK(status IN ('open', 'in_progress', 'done', 'cancelled')) DEFAULT 'open',
            due_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id),
            FOREIGN KEY (message_id) REFERENCES messages(id)
        )
    """)
    
    # 5. Outbox table (for reliable integrations)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS outbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            status TEXT CHECK(status IN ('pending', 'sent', 'failed', 'retry')) DEFAULT 'pending',
            retry_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP
        )
    """)
    
    # 6. Audit log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            action TEXT NOT NULL,
            resource_type TEXT,
            resource_id INTEGER,
            details_json TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_athlete_id ON messages(athlete_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_dedupe_hash ON messages(dedupe_hash)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_highlights_athlete_id ON highlights(athlete_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_highlights_category ON highlights(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_highlights_source ON highlights(source)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_highlights_status ON highlights(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_todos_athlete_id ON todos(athlete_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_todos_status ON todos(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_outbox_status ON outbox(status)")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print("✅ Workflow database initialized successfully!")
    print("📊 Tables created:")
    print("   - conversations")
    print("   - messages")
    print("   - highlights") 
    print("   - todos")
    print("   - outbox")
    print("   - audit_log")

if __name__ == "__main__":
    init_workflow_database() 