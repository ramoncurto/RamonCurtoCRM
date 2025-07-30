#!/usr/bin/env python3
"""
Database Schema Consolidation Script
Migrates from fragmented schema to unified workflow architecture
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseConsolidator:
    """Handles migration from old fragmented schema to new unified schema"""
    
    def __init__(self, db_path='database.db'):
        self.db_path = db_path
        self.backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def create_backup(self):
        """Create backup before migration"""
        try:
            import shutil
            shutil.copy2(self.db_path, self.backup_path)
            logger.info(f"✅ Backup created: {self.backup_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create backup: {e}")
            return False
    
    def check_current_schema(self):
        """Analyze current database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check existing tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        schema_info = {
            'has_records': 'records' in tables,
            'has_messages': 'messages' in tables,
            'has_conversations': 'conversations' in tables,
            'has_athlete_highlights': 'athlete_highlights' in tables,
            'has_highlights': 'highlights' in tables,
            'has_todos': 'todos' in tables,
            'all_tables': tables
        }
        
        # Count records in each table
        for table in ['records', 'messages', 'athlete_highlights', 'highlights']:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                schema_info[f'{table}_count'] = cursor.fetchone()[0]
        
        conn.close()
        return schema_info
    
    def create_unified_schema(self):
        """Create the unified schema tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        logger.info("🔧 Creating unified schema...")
        
        # 1. Conversations table (unified)
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
        
        # 2. Check if messages table exists and has the correct schema
        cursor.execute("PRAGMA table_info(messages)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        required_columns = [
            'id', 'conversation_id', 'athlete_id', 'source_channel', 'source_message_id',
            'direction', 'content_text', 'content_audio_url', 'transcription', 
            'generated_response', 'final_response', 'audio_duration', 'category', 
            'priority', 'status', 'notes', 'metadata_json', 'dedupe_hash', 'filename',
            'created_at', 'updated_at'
        ]
        
        missing_columns = [col for col in required_columns if col not in existing_columns]
        
        if missing_columns:
            logger.info(f"⚠️  Messages table missing columns: {missing_columns}")
            logger.info("🔄 Recreating messages table with complete schema...")
            
            # Drop existing messages table if it exists
            cursor.execute("DROP TABLE IF EXISTS messages")
            
            # Create messages table with complete schema
            cursor.execute("""
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER,
                    athlete_id INTEGER NOT NULL,
                    source_channel TEXT NOT NULL,
                    source_message_id TEXT,
                    direction TEXT CHECK(direction IN ('in', 'out')) NOT NULL,
                    content_text TEXT,
                    content_audio_url TEXT,
                    transcription TEXT,
                    generated_response TEXT,
                    final_response TEXT,
                    audio_duration REAL,
                    category TEXT,
                    priority TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'pending',
                    notes TEXT,
                    metadata_json TEXT,
                    dedupe_hash TEXT UNIQUE,
                    filename TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
                    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
                )
            """)
        else:
            # Messages table already has correct schema
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
                    generated_response TEXT,
                    final_response TEXT,
                    audio_duration REAL,
                    category TEXT,
                    priority TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'pending',
                    notes TEXT,
                    metadata_json TEXT,
                    dedupe_hash TEXT UNIQUE,
                    filename TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
                    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
                )
            """)
        
        # 3. Highlights table (unified)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS highlights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                athlete_id INTEGER NOT NULL,
                message_id INTEGER,
                highlight_text TEXT NOT NULL,
                category TEXT CHECK(category IN ('injury', 'schedule', 'performance', 'admin', 'nutrition', 'technical', 'psychology', 'other')) DEFAULT 'other',
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
        
        # 4. Keep existing todos table
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
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_athlete_id ON messages(athlete_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_highlights_athlete_id ON highlights(athlete_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_highlights_message_id ON highlights(message_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_highlights_status ON highlights(status)")
        
        conn.commit()
        conn.close()
        logger.info("✅ Unified schema created")
    
    def migrate_records_to_messages(self):
        """Migrate data from records table to messages table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        logger.info("🔄 Migrating records to messages...")
        
        # Get all records
        cursor.execute("""
            SELECT id, athlete_id, timestamp, filename, transcription, 
                   generated_response, final_response, audio_duration, 
                   category, priority, status, notes, source, external_message_id
            FROM records
            ORDER BY timestamp ASC
        """)
        records = cursor.fetchall()
        
        migrated_count = 0
        conversation_cache = {}  # Cache conversations per athlete
        
        for record in records:
            (record_id, athlete_id, timestamp, filename, transcription, 
             generated_response, final_response, audio_duration, 
             category, priority, status, notes, source, external_message_id) = record
            
            try:
                # Get or create conversation for athlete
                if athlete_id not in conversation_cache:
                    cursor.execute("""
                        SELECT id FROM conversations WHERE athlete_id = ? LIMIT 1
                    """, (athlete_id,))
                    conv_result = cursor.fetchone()
                    
                    if conv_result:
                        conversation_cache[athlete_id] = conv_result[0]
                    else:
                        cursor.execute("""
                            INSERT INTO conversations (athlete_id, channel, created_at)
                            VALUES (?, 'unified', ?)
                        """, (athlete_id, timestamp))
                        conversation_cache[athlete_id] = cursor.lastrowid
                
                conversation_id = conversation_cache[athlete_id]
                
                # Create message entry
                cursor.execute("""
                    INSERT INTO messages (
                        conversation_id, athlete_id, source_channel, source_message_id,
                        direction, transcription, generated_response, final_response,
                        audio_duration, category, priority, status, notes, filename,
                        created_at, metadata_json
                    ) VALUES (?, ?, ?, ?, 'in', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    conversation_id, athlete_id, source or 'manual', 
                    external_message_id or f"migrated_{record_id}",
                    transcription, generated_response, final_response,
                    audio_duration, category, priority, status, notes, filename,
                    timestamp, json.dumps({"migrated_from_record": record_id})
                ))
                
                migrated_count += 1
                
            except Exception as e:
                logger.error(f"❌ Error migrating record {record_id}: {e}")
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Migrated {migrated_count} records to messages")
        return migrated_count
    
    def migrate_athlete_highlights_to_highlights(self):
        """Migrate data from athlete_highlights to highlights table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        logger.info("🔄 Migrating athlete_highlights to highlights...")
        
        # Check if athlete_highlights table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='athlete_highlights'
        """)
        if not cursor.fetchone():
            logger.info("ℹ️  No athlete_highlights table found, skipping migration")
            conn.close()
            return 0
        
        # Get all athlete highlights
        cursor.execute("""
            SELECT id, athlete_id, highlight_text, category, 
                   source_conversation_id, created_at, updated_at, is_active
            FROM athlete_highlights
            ORDER BY created_at ASC
        """)
        highlights = cursor.fetchall()
        
        migrated_count = 0
        
        # Category mapping from old to new schema
        category_mapping = {
            'auto-generated': 'other',
            'general': 'other',
            'performance': 'performance',
            'training': 'performance',
            'injury': 'injury',
            'schedule': 'schedule',
            'admin': 'admin',
            'nutrition': 'nutrition',
            'technical': 'technical',
            'psychology': 'psychology'
        }
        
        for highlight in highlights:
            (old_id, athlete_id, highlight_text, category, 
             source_conversation_id, created_at, updated_at, is_active) = highlight
            
            try:
                # Map category to new schema
                new_category = category_mapping.get(category, 'other')
                
                # Try to find corresponding message_id from source_conversation_id
                message_id = None
                if source_conversation_id:
                    cursor.execute("""
                        SELECT id FROM messages 
                        WHERE metadata_json LIKE ?
                        LIMIT 1
                    """, (f'%"migrated_from_record": {source_conversation_id}%',))
                    result = cursor.fetchone()
                    if result:
                        message_id = result[0]
                
                # Insert into unified highlights table
                cursor.execute("""
                    INSERT INTO highlights (
                        athlete_id, message_id, highlight_text, category,
                        source, status, is_manual, is_active,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, 'manual', 'accepted', 1, ?, ?, ?)
                """, (
                    athlete_id, message_id, highlight_text, 
                    new_category, is_active, created_at, updated_at
                ))
                
                migrated_count += 1
                
            except Exception as e:
                logger.error(f"❌ Error migrating highlight {old_id}: {e}")
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Migrated {migrated_count} highlights")
        return migrated_count
    
    def cleanup_old_tables(self, confirm=False):
        """Remove old fragmented tables after successful migration"""
        if not confirm:
            logger.warning("⚠️  cleanup_old_tables called without confirmation")
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        logger.info("🗑️  Cleaning up old tables...")
        
        # Rename old tables instead of dropping (safer)
        old_tables = ['records', 'athlete_highlights']
        
        for table in old_tables:
            try:
                cursor.execute(f"""
                    ALTER TABLE {table} RENAME TO {table}_old_backup
                """)
                logger.info(f"✅ Renamed {table} to {table}_old_backup")
            except Exception as e:
                logger.error(f"❌ Error renaming {table}: {e}")
        
        conn.commit()
        conn.close()
        return True
    
    def run_full_migration(self):
        """Run complete migration process"""
        logger.info("🚀 Starting database consolidation...")
        
        # 1. Analyze current schema
        schema_info = self.check_current_schema()
        logger.info(f"📊 Current schema: {schema_info}")
        
        # 2. Create backup
        if not self.create_backup():
            logger.error("❌ Migration aborted - backup failed")
            return False
        
        # 3. Create unified schema
        self.create_unified_schema()
        
        # 4. Migrate data
        if schema_info['has_records']:
            records_migrated = self.migrate_records_to_messages()
            logger.info(f"✅ Records migration: {records_migrated} records")
        
        if schema_info['has_athlete_highlights']:
            highlights_migrated = self.migrate_athlete_highlights_to_highlights()
            logger.info(f"✅ Highlights migration: {highlights_migrated} highlights")
        
        # 5. Verify migration
        final_schema = self.check_current_schema()
        logger.info(f"📊 Final schema: {final_schema}")
        
        logger.info("🎉 Database consolidation completed!")
        logger.info(f"💾 Backup available at: {self.backup_path}")
        logger.info("⚠️  Run cleanup_old_tables(confirm=True) after verifying migration")
        
        return True

def main():
    """Main migration script"""
    consolidator = DatabaseConsolidator()
    
    print("🏥 Database Schema Consolidation Tool")
    print("=" * 50)
    
    # Show current status
    schema_info = consolidator.check_current_schema()
    print("\n📊 Current Database Status:")
    for key, value in schema_info.items():
        if key.endswith('_count'):
            table_name = key.replace('_count', '')
            print(f"   {table_name}: {value} records")
        elif key.startswith('has_') and value:
            table_name = key.replace('has_', '')
            print(f"   ✅ {table_name} table exists")
    
    # Ask for confirmation
    print("\n⚠️  This will:")
    print("   1. Create a backup of your database")
    print("   2. Create unified schema tables")
    print("   3. Migrate data from fragmented tables")
    print("   4. Keep old tables as backups")
    
    response = input("\nProceed with migration? (y/N): ")
    if response.lower() != 'y':
        print("❌ Migration cancelled")
        return
    
    # Run migration
    success = consolidator.run_full_migration()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("📋 Next steps:")
        print("   1. Test the application with the new schema")
        print("   2. Verify all data migrated correctly")
        print("   3. Run cleanup if everything works:")
        print(f"      consolidator.cleanup_old_tables(confirm=True)")
    else:
        print("\n❌ Migration failed!")

if __name__ == "__main__":
    main()