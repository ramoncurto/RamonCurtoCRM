#!/usr/bin/env python3
"""
Test script for the athlete highlights functionality.
This script tests the highlights API endpoints and database operations.
"""

import sqlite3
import datetime

# Test configuration
DB_PATH = 'database.db'

def test_highlights_functionality():
    """Test the highlights functionality directly with database operations."""
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Test 1: Create a test athlete
        print("=== Test 1: Creating test athlete ===")
        import uuid
        test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        with conn:
            cursor = conn.execute(
                "INSERT INTO athletes (name, email, phone, sport, level) VALUES (?, ?, ?, ?, ?)",
                ("Test Athlete", test_email, "+1234567890", "Running", "Advanced")
            )
            athlete_id = cursor.lastrowid
        print(f"Created athlete with ID: {athlete_id}")
        
        # Test 2: Create a test conversation
        print("\n=== Test 2: Creating test conversation ===")
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO records (athlete_id, timestamp, transcription, generated_response, final_response, category)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    athlete_id,
                    datetime.datetime.now().isoformat(),
                    "I need help with my training plan for the marathon",
                    "Let's focus on building your endurance gradually",
                    "Let's focus on building your endurance gradually with a structured plan",
                    "training"
                )
            )
            conversation_id = cursor.lastrowid
        print(f"Created conversation with ID: {conversation_id}")
        
        # Test 3: Add highlights manually
        print("\n=== Test 3: Adding highlights manually ===")
        with conn:
            highlights = [
                ("Athlete preparing for marathon - needs structured training plan", "training", conversation_id),
                ("Focus on gradual endurance building", "training", conversation_id),
                ("Priority: marathon preparation", "goals", None)
            ]
            
            added_highlights = []
            for text, category, source_id in highlights:
                cursor = conn.execute(
                    "INSERT INTO athlete_highlights (athlete_id, highlight_text, category, source_conversation_id) VALUES (?, ?, ?, ?)",
                    (athlete_id, text, category, source_id)
                )
                added_highlights.append(cursor.lastrowid)
        
        print(f"Added {len(added_highlights)} highlights: {added_highlights}")
        
        # Test 4: Retrieve highlights
        print("\n=== Test 4: Retrieving highlights ===")
        with conn:
            cursor = conn.execute(
                """
                SELECT h.id, h.highlight_text, h.category, h.created_at, h.is_active,
                       r.transcription as source_transcription
                FROM athlete_highlights h
                LEFT JOIN records r ON h.source_conversation_id = r.id
                WHERE h.athlete_id = ?
                ORDER BY h.created_at DESC
                """,
                (athlete_id,)
            )
            highlights = cursor.fetchall()
        
        print(f"Found {len(highlights)} highlights for athlete {athlete_id}:")
        for h in highlights:
            print(f"  - ID: {h[0]}")
            print(f"    Text: {h[1]}")
            print(f"    Category: {h[2]}")
            print(f"    Active: {bool(h[4])}")
            print(f"    Source: {h[5][:50] if h[5] else 'Manual'}")
            print()
        
        # Test 5: Update highlight status
        print("=== Test 5: Updating highlight status ===")
        if highlights:
            highlight_id = highlights[0][0]
            with conn:
                conn.execute(
                    "UPDATE athlete_highlights SET is_active = 0 WHERE id = ?",
                    (highlight_id,)
                )
            print(f"Deactivated highlight {highlight_id}")
        
        # Test 6: Get only active highlights
        print("\n=== Test 6: Active highlights only ===")
        with conn:
            cursor = conn.execute(
                """
                SELECT id, highlight_text, category 
                FROM athlete_highlights 
                WHERE athlete_id = ? AND is_active = 1
                """,
                (athlete_id,)
            )
            active_highlights = cursor.fetchall()
        
        print(f"Found {len(active_highlights)} active highlights")
        
        # Test 7: Clean up test data
        print("\n=== Test 7: Cleanup ===")
        with conn:
            conn.execute("DELETE FROM athlete_highlights WHERE athlete_id = ?", (athlete_id,))
            conn.execute("DELETE FROM records WHERE athlete_id = ?", (athlete_id,))
            conn.execute("DELETE FROM athletes WHERE id = ?", (athlete_id,))
        print("Cleaned up test data")
        
        print("\n=== All tests completed successfully! ===")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    test_highlights_functionality()
