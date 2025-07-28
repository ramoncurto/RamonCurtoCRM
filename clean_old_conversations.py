#!/usr/bin/env python3
"""
Script to clean old WhatsApp conversations from the database.
This script allows you to remove old test conversations and clean up the database.
"""

import sqlite3
import datetime
import argparse
from typing import List, Dict

def connect_db():
    """Connect to the database."""
    return sqlite3.connect('database.db')

def get_conversation_stats():
    """Get statistics about conversations in the database."""
    conn = connect_db()
    cursor = conn.cursor()
    
    print("📊 Database Conversation Statistics")
    print("=" * 50)
    
    # Get total conversations by source
    cursor.execute("""
        SELECT source, COUNT(*) as count, 
               MIN(timestamp) as oldest,
               MAX(timestamp) as newest
        FROM records 
        GROUP BY source
        ORDER BY count DESC
    """)
    
    sources = cursor.fetchall()
    total_conversations = 0
    
    for source, count, oldest, newest in sources:
        total_conversations += count
        print(f"📱 {source.upper()}: {count} conversations")
        if oldest and newest:
            print(f"   📅 Date range: {oldest[:10]} to {newest[:10]}")
    
    print(f"\n📈 Total conversations: {total_conversations}")
    
    # Get athlete conversation counts
    cursor.execute("""
        SELECT a.name, COUNT(r.id) as conv_count
        FROM athletes a
        LEFT JOIN records r ON a.id = r.athlete_id
        GROUP BY a.id, a.name
        ORDER BY conv_count DESC
    """)
    
    athletes = cursor.fetchall()
    print(f"\n👤 Athlete Conversation Counts:")
    for name, count in athletes:
        print(f"   {name}: {count} conversations")
    
    conn.close()
    return sources

def list_old_conversations(days_old: int = 7, source: str = None):
    """List old conversations that can be cleaned."""
    conn = connect_db()
    cursor = conn.cursor()
    
    cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days_old)).isoformat()
    
    query = """
        SELECT r.id, r.timestamp, r.transcription, r.source, a.name
        FROM records r
        LEFT JOIN athletes a ON r.athlete_id = a.id
        WHERE r.timestamp < ?
    """
    params = [cutoff_date]
    
    if source:
        query += " AND r.source = ?"
        params.append(source)
    
    query += " ORDER BY r.timestamp DESC"
    
    cursor.execute(query, params)
    conversations = cursor.fetchall()
    
    print(f"🗑️  Old conversations (older than {days_old} days):")
    print("=" * 50)
    
    if not conversations:
        print("   ✅ No old conversations found")
        return []
    
    for conv_id, timestamp, transcription, source, athlete_name in conversations:
        date = timestamp[:10] if timestamp else "Unknown"
        preview = transcription[:60] + "..." if len(transcription) > 60 else transcription
        print(f"   📱 ID {conv_id}: {date} [{source}] - {athlete_name}")
        print(f"      💬 {preview}")
        print()
    
    conn.close()
    return conversations

def clean_old_conversations(days_old: int = 7, source: str = None, dry_run: bool = True):
    """Clean old conversations from the database."""
    conn = connect_db()
    cursor = conn.cursor()
    
    cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days_old)).isoformat()
    
    # First, get the conversations that would be deleted
    query = """
        SELECT r.id, r.timestamp, r.transcription, r.source, a.name
        FROM records r
        LEFT JOIN athletes a ON r.athlete_id = a.id
        WHERE r.timestamp < ?
    """
    params = [cutoff_date]
    
    if source:
        query += " AND r.source = ?"
        params.append(source)
    
    cursor.execute(query, params)
    conversations_to_delete = cursor.fetchall()
    
    if not conversations_to_delete:
        print("✅ No old conversations to clean")
        conn.close()
        return
    
    print(f"🗑️  {'DRY RUN - ' if dry_run else ''}Cleaning old conversations:")
    print(f"   📅 Older than: {days_old} days")
    print(f"   📱 Source filter: {source if source else 'All sources'}")
    print(f"   📊 Conversations to delete: {len(conversations_to_delete)}")
    print()
    
    # Show what would be deleted
    for conv_id, timestamp, transcription, source, athlete_name in conversations_to_delete:
        date = timestamp[:10] if timestamp else "Unknown"
        preview = transcription[:50] + "..." if len(transcription) > 50 else transcription
        print(f"   ❌ ID {conv_id}: {date} [{source}] - {athlete_name}")
        print(f"      💬 {preview}")
    
    if dry_run:
        print(f"\n🔍 This was a DRY RUN. No conversations were actually deleted.")
        print(f"   To actually delete, run with --execute flag")
        conn.close()
        return
    
    # Actually delete the conversations
    delete_query = "DELETE FROM records WHERE timestamp < ?"
    delete_params = [cutoff_date]
    
    if source:
        delete_query += " AND source = ?"
        delete_params.append(source)
    
    cursor.execute(delete_query, delete_params)
    deleted_count = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Successfully deleted {deleted_count} old conversations")

def clean_test_conversations():
    """Clean test conversations (those with 'test' in external_message_id)."""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Find test conversations
    cursor.execute("""
        SELECT r.id, r.timestamp, r.transcription, r.source, r.external_message_id, a.name
        FROM records r
        LEFT JOIN athletes a ON r.athlete_id = a.id
        WHERE r.external_message_id LIKE '%test%'
        ORDER BY r.timestamp DESC
    """)
    
    test_conversations = cursor.fetchall()
    
    if not test_conversations:
        print("✅ No test conversations found")
        conn.close()
        return
    
    print("🧪 Test conversations found:")
    print("=" * 50)
    
    for conv_id, timestamp, transcription, source, external_id, athlete_name in test_conversations:
        date = timestamp[:10] if timestamp else "Unknown"
        preview = transcription[:50] + "..." if len(transcription) > 50 else transcription
        print(f"   🧪 ID {conv_id}: {date} [{source}] - {athlete_name}")
        print(f"      🆔 External ID: {external_id}")
        print(f"      💬 {preview}")
        print()
    
    # Ask for confirmation
    response = input("Do you want to delete these test conversations? (y/N): ")
    if response.lower() != 'y':
        print("❌ Cancelled")
        conn.close()
        return
    
    # Delete test conversations
    cursor.execute("DELETE FROM records WHERE external_message_id LIKE '%test%'")
    deleted_count = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"✅ Successfully deleted {deleted_count} test conversations")

def main():
    parser = argparse.ArgumentParser(description='Clean old conversations from the database')
    parser.add_argument('--stats', action='store_true', help='Show conversation statistics')
    parser.add_argument('--list', action='store_true', help='List old conversations')
    parser.add_argument('--clean', action='store_true', help='Clean old conversations')
    parser.add_argument('--clean-tests', action='store_true', help='Clean test conversations')
    parser.add_argument('--days', type=int, default=7, help='Days old threshold (default: 7)')
    parser.add_argument('--source', type=str, help='Filter by source (whatsapp, telegram, manual)')
    parser.add_argument('--execute', action='store_true', help='Actually execute the deletion (default is dry run)')
    
    args = parser.parse_args()
    
    print("🧹 Conversation Cleanup Tool")
    print("=" * 50)
    
    if args.stats:
        get_conversation_stats()
    
    if args.list:
        list_old_conversations(args.days, args.source)
    
    if args.clean:
        clean_old_conversations(args.days, args.source, not args.execute)
    
    if args.clean_tests:
        clean_test_conversations()
    
    if not any([args.stats, args.list, args.clean, args.clean_tests]):
        print("No action specified. Use --help for options.")
        print("\nExample usage:")
        print("  python clean_old_conversations.py --stats")
        print("  python clean_old_conversations.py --list --days 30")
        print("  python clean_old_conversations.py --clean --days 7 --source whatsapp --execute")
        print("  python clean_old_conversations.py --clean-tests")

if __name__ == "__main__":
    main() 