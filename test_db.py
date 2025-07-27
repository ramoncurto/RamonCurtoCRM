#!/usr/bin/env python3
import sqlite3

def check_database():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print("📋 Database Tables:", tables)
    
    # Check athletes table structure
    if 'athletes' in tables:
        cursor.execute("PRAGMA table_info(athletes)")
        print("\n👤 Athletes Table Structure:")
        for row in cursor.fetchall():
            print(f"  - {row[1]} ({row[2]})")
        
        # Check athletes data
        cursor.execute("SELECT * FROM athletes")
        athletes = cursor.fetchall()
        print(f"\n📊 Athletes Count: {len(athletes)}")
        for athlete in athletes:
            print(f"  - ID {athlete[0]}: {athlete[1]} ({athlete[4]})")
    
    # Check records table
    if 'records' in tables:
        cursor.execute("SELECT COUNT(*) FROM records")
        records_count = cursor.fetchone()[0]
        print(f"\n📝 Records Count: {records_count}")
    
    # Check athlete_metrics table
    if 'athlete_metrics' in tables:
        cursor.execute("SELECT COUNT(*) FROM athlete_metrics")
        metrics_count = cursor.fetchone()[0]
        print(f"\n📈 Metrics Count: {metrics_count}")
    
    conn.close()
    print("\n✅ Database check completed")

if __name__ == "__main__":
    check_database() 