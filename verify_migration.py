#!/usr/bin/env python3
"""
Post-Migration Verification Tool
Verifies that database consolidation was successful
"""

import sqlite3
import json
import requests
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MigrationVerifier:
    """Verifies successful database migration"""
    
    def __init__(self, db_path='database.db', server_url='http://localhost:8000'):
        self.db_path = db_path
        self.server_url = server_url
        self.issues = []
        self.warnings = []
    
    def check_database_structure(self):
        """Verify database structure is correct"""
        logger.info("🔍 Checking database structure...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check required tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['athletes', 'conversations', 'messages', 'highlights', 'todos']
        for table in required_tables:
            if table not in tables:
                self.issues.append(f"❌ Missing required table: {table}")
            else:
                logger.info(f"✅ Table exists: {table}")
        
        # Check old tables are renamed (not dropped)
        old_tables = ['records_old_backup', 'athlete_highlights_old_backup']
        for table in old_tables:
            if table in tables:
                logger.info(f"✅ Backup table exists: {table}")
            else:
                self.warnings.append(f"⚠️ Backup table not found: {table}")
        
        conn.close()
    
    def verify_data_migration(self):
        """Verify data was migrated correctly"""
        logger.info("🔍 Verifying data migration...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check messages table has data
        cursor.execute("SELECT COUNT(*) FROM messages")
        message_count = cursor.fetchone()[0]
        
        # Check for migrated records
        cursor.execute("""
            SELECT COUNT(*) FROM messages 
            WHERE metadata_json LIKE '%migrated_from_record%'
        """)
        migrated_count = cursor.fetchone()[0]
        
        logger.info(f"📊 Total messages: {message_count}")
        logger.info(f"📊 Migrated from records: {migrated_count}")
        
        if message_count == 0:
            self.issues.append("❌ No messages found in database")
        
        # Check highlights migration
        cursor.execute("SELECT COUNT(*) FROM highlights")
        highlight_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM highlights WHERE source = 'manual'")
        manual_highlights = cursor.fetchone()[0]
        
        logger.info(f"📊 Total highlights: {highlight_count}")
        logger.info(f"📊 Manual highlights: {manual_highlights}")
        
        # Check relationships
        cursor.execute("""
            SELECT COUNT(*) FROM messages m 
            LEFT JOIN conversations c ON m.conversation_id = c.id 
            WHERE c.id IS NULL
        """)
        orphaned_messages = cursor.fetchone()[0]
        
        if orphaned_messages > 0:
            self.issues.append(f"❌ {orphaned_messages} messages without conversation")
        
        conn.close()
    
    def test_api_endpoints(self):
        """Test critical API endpoints"""
        logger.info("🔍 Testing API endpoints...")
        
        try:
            # Test athletes endpoint
            response = requests.get(f"{self.server_url}/api/athletes", timeout=10)
            if response.status_code == 200:
                athletes = response.json().get('athletes', [])
                logger.info(f"✅ Athletes endpoint: {len(athletes)} athletes")
                
                if athletes:
                    # Test athlete history
                    athlete_id = athletes[0]['id']
                    response = requests.get(
                        f"{self.server_url}/api/athletes/{athlete_id}/history", 
                        timeout=10
                    )
                    if response.status_code == 200:
                        history = response.json().get('history', [])
                        logger.info(f"✅ History endpoint: {len(history)} messages")
                    else:
                        self.issues.append(f"❌ History endpoint failed: {response.status_code}")
                    
                    # Test highlights
                    response = requests.get(
                        f"{self.server_url}/api/athletes/{athlete_id}/highlights",
                        timeout=10
                    )
                    if response.status_code == 200:
                        highlights = response.json().get('highlights', [])
                        logger.info(f"✅ Highlights endpoint: {len(highlights)} highlights")
                    else:
                        self.issues.append(f"❌ Highlights endpoint failed: {response.status_code}")
                    
                    # Test risk assessment
                    response = requests.get(
                        f"{self.server_url}/api/athletes/{athlete_id}/risk",
                        timeout=10
                    )
                    if response.status_code == 200:
                        risk = response.json()
                        logger.info(f"✅ Risk endpoint: {risk.get('level', 'unknown')} risk")
                    else:
                        self.issues.append(f"❌ Risk endpoint failed: {response.status_code}")
                
            else:
                self.issues.append(f"❌ Athletes endpoint failed: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            self.issues.append("❌ Cannot connect to server - is it running?")
        except Exception as e:
            self.issues.append(f"❌ API test error: {e}")
    
    def check_data_integrity(self):
        """Check data integrity constraints"""
        logger.info("🔍 Checking data integrity...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check foreign key constraints
        checks = [
            ("Messages without athletes", """
                SELECT COUNT(*) FROM messages m 
                LEFT JOIN athletes a ON m.athlete_id = a.id 
                WHERE a.id IS NULL
            """),
            ("Highlights without athletes", """
                SELECT COUNT(*) FROM highlights h 
                LEFT JOIN athletes a ON h.athlete_id = a.id 
                WHERE a.id IS NULL
            """),
            ("Highlights without messages", """
                SELECT COUNT(*) FROM highlights h 
                LEFT JOIN messages m ON h.message_id = m.id 
                WHERE h.message_id IS NOT NULL AND m.id IS NULL
            """),
            ("Conversations without athletes", """
                SELECT COUNT(*) FROM conversations c 
                LEFT JOIN athletes a ON c.athlete_id = a.id 
                WHERE a.id IS NULL
            """)
        ]
        
        for check_name, query in checks:
            cursor.execute(query)
            count = cursor.fetchone()[0]
            if count > 0:
                self.issues.append(f"❌ {check_name}: {count} records")
            else:
                logger.info(f"✅ {check_name}: OK")
        
        conn.close()
    
    def run_full_verification(self):
        """Run complete verification suite"""
        logger.info("🔍 Starting post-migration verification...")
        
        self.check_database_structure()
        self.verify_data_migration()
        self.check_data_integrity()
        self.test_api_endpoints()
        
        # Report results
        print("\n" + "="*50)
        print("📋 MIGRATION VERIFICATION REPORT")
        print("="*50)
        
        if not self.issues and not self.warnings:
            print("🎉 ✅ MIGRATION SUCCESSFUL!")
            print("   All checks passed - system ready for production")
        else:
            if self.issues:
                print("🚨 ❌ ISSUES FOUND:")
                for issue in self.issues:
                    print(f"   {issue}")
            
            if self.warnings:
                print("\n⚠️ WARNINGS:")
                for warning in self.warnings:
                    print(f"   {warning}")
            
            if self.issues:
                print("\n🆘 ACTION REQUIRED:")
                print("   1. Review issues above")
                print("   2. Consider rollback if critical")
                print("   3. Fix issues and re-run verification")
            else:
                print("\n✅ MIGRATION SUCCESSFUL (with warnings)")
                print("   Warnings can be addressed later")
        
        print("\n📊 Summary:")
        print(f"   Issues: {len(self.issues)}")
        print(f"   Warnings: {len(self.warnings)}")
        print(f"   Status: {'FAILED' if self.issues else 'PASSED'}")
        
        return len(self.issues) == 0

def main():
    """Main verification script"""
    print("🔍 Post-Migration Verification Tool")
    print("="*40)
    
    verifier = MigrationVerifier()
    success = verifier.run_full_verification()
    
    if success:
        print("\n✅ Migration verification completed successfully!")
        print("🚀 System is ready for use")
    else:
        print("\n❌ Migration verification failed!")
        print("🆘 Please review issues and take corrective action")
        exit(1)

if __name__ == "__main__":
    main()