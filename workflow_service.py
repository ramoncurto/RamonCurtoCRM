#!/usr/bin/env python3
"""
Core workflow service for processing incoming messages and generating actions
"""

import sqlite3
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import os

# OpenAI imports
from openai import AsyncOpenAI

# Configuration
AUTO_GPT_ENABLED = os.getenv("AUTO_GPT_ENABLED", "true").lower() == "true"

logger = logging.getLogger(__name__)

@dataclass
class MessageEvent:
    """Incoming message event from any channel"""
    source_channel: str
    source_message_id: str
    athlete_id: int
    content_text: Optional[str] = None
    content_audio_url: Optional[str] = None
    transcription: Optional[str] = None
    metadata: Optional[Dict] = None

@dataclass
class WorkflowActions:
    """Configuration for which actions to perform on a message"""
    save_to_history: bool = True
    generate_highlights: bool = False
    suggest_reply: bool = False
    maybe_todo: bool = False

class WorkflowService:
    """Core service for processing messages through the workflow"""
    
    def __init__(self, db_path: str = 'database.db'):
        self.db_path = db_path
        self.openai_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
    
    def _get_db_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def _generate_dedupe_hash(self, event: MessageEvent) -> str:
        """Generate deduplication hash for idempotency"""
        content = f"{event.source_channel}:{event.source_message_id}:{event.athlete_id}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _is_duplicate(self, dedupe_hash: str) -> bool:
        """Check if message is duplicate"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM messages WHERE dedupe_hash = ?",
            (dedupe_hash,)
        )
        result = cursor.fetchone()
        conn.close()
        return result is not None
    
    def _get_or_create_conversation(self, athlete_id: int) -> int:
        """Get or create conversation for athlete"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        # Try to get existing conversation
        cursor.execute(
            "SELECT id FROM conversations WHERE athlete_id = ? ORDER BY created_at DESC LIMIT 1",
            (athlete_id,)
        )
        result = cursor.fetchone()
        
        if result:
            conversation_id = result[0]
        else:
            # Create new conversation
            cursor.execute(
                "INSERT INTO conversations (athlete_id, channel) VALUES (?, 'unified')",
                (athlete_id,)
            )
            conversation_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return conversation_id
    
    def _persist_message(self, event: MessageEvent, dedupe_hash: str) -> int:
        """Persist message to database"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        conversation_id = self._get_or_create_conversation(event.athlete_id)
        
        cursor.execute("""
            INSERT INTO messages (
                conversation_id, athlete_id, source_channel, source_message_id,
                direction, content_text, content_audio_url, transcription,
                metadata_json, dedupe_hash
            ) VALUES (?, ?, ?, ?, 'in', ?, ?, ?, ?, ?)
        """, (
            conversation_id, event.athlete_id, event.source_channel,
            event.source_message_id, event.content_text, event.content_audio_url,
            event.transcription, json.dumps(event.metadata or {}), dedupe_hash
        ))
        
        message_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return message_id
    
    async def _generate_highlights(self, message_id: int, athlete_id: int) -> List[Dict]:
        """Generate highlights from message using GPT-4o-mini"""
        try:
            # Get recent messages for context
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT content_text, transcription 
                FROM messages 
                WHERE athlete_id = ? 
                ORDER BY created_at DESC 
                LIMIT 10
            """, (athlete_id,))
            recent_messages = cursor.fetchall()
            conn.close()
            
            # Prepare context
            context = []
            for msg in recent_messages:
                text = msg[0] or msg[1] or ""
                if text:
                    context.append(text)
            
            # Get the current message
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT content_text, transcription 
                FROM messages 
                WHERE id = ?
            """, (message_id,))
            current_msg = cursor.fetchone()
            conn.close()
            
            if not current_msg:
                return []
            
            current_text = current_msg[0] or current_msg[1] or ""
            
            # Prepare prompt for highlight extraction
            prompt = f"""
            Extract key highlights from this athlete message. Focus on actionable insights, important information, or notable points.
            
            Recent context:
            {' '.join(context[-5:])}
            
            Current message:
            {current_text}
            
            Extract up to 5 highlights in this JSON format:
            {{
                "highlights": [
                    {{
                        "text": "highlight text",
                        "category": "injury|schedule|performance|admin|nutrition|other",
                        "score": 0.0-1.0
                    }}
                ]
            }}
            
            Categories:
            - injury: health issues, injuries, recovery
            - schedule: training times, appointments, availability
            - performance: goals, achievements, progress
            - admin: logistics, payments, paperwork
            - nutrition: diet, supplements, hydration
            - other: anything else
            """
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            result = response.choices[0].message.content
            highlights_data = json.loads(result)
            
            # Store highlights
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            for highlight in highlights_data.get("highlights", []):
                cursor.execute("""
                    INSERT INTO highlights (
                        athlete_id, message_id, highlight_text, category, score, 
                        source, status, is_manual
                    ) VALUES (?, ?, ?, ?, ?, 'ai', 'suggested', 0)
                """, (
                    athlete_id, message_id, highlight["text"],
                    highlight["category"], highlight["score"]
                ))
            
            conn.commit()
            conn.close()
            
            return highlights_data.get("highlights", [])
            
        except Exception as e:
            logger.error(f"Error generating highlights: {e}")
            return []
    
    async def _suggest_reply(self, message_id: int, athlete_id: int) -> Optional[str]:
        """Suggest a reply using GPT-4o-mini"""
        # Check if automatic GPT is enabled
        if not AUTO_GPT_ENABLED:
            return None
            
        try:
            # Get conversation context
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT content_text, transcription, direction
                FROM messages 
                WHERE athlete_id = ? 
                ORDER BY created_at DESC 
                LIMIT 6
            """, (athlete_id,))
            conversation = cursor.fetchall()
            conn.close()
            
            # Prepare conversation history
            history = []
            for msg in conversation:
                text = msg[0] or msg[1] or ""
                direction = msg[2]
                if text:
                    role = "athlete" if direction == "in" else "coach"
                    history.append(f"{role}: {text}")
            
            # Get athlete info for personalization
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name, sport, level FROM athletes WHERE id = ?", (athlete_id,))
            athlete = cursor.fetchone()
            conn.close()
            
            athlete_name = athlete[0] if athlete else "the athlete"
            sport = athlete[1] if athlete else "sport"
            level = athlete[2] if athlete else "level"
            
            prompt = f"""
            You are a professional sports coach responding to {athlete_name}, a {level} {sport} athlete.
            
            Recent conversation:
            {chr(10).join(history)}
            
            Generate a brief, empathetic, and actionable reply. Consider:
            - Be encouraging and supportive
            - Provide clear next steps if needed
            - Keep it concise (under 200 words)
            - Match the tone of the conversation
            - If they asked a question, answer it
            - If they shared progress, acknowledge it
            - If they have concerns, address them
            
            Reply:
            """
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error suggesting reply: {e}")
            return None
    
    async def _detect_todo(self, message_id: int, athlete_id: int) -> Optional[Dict]:
        """Detect if message contains actionable request"""
        # Check if automatic GPT is enabled
        if not AUTO_GPT_ENABLED:
            return None
            
        try:
            # Get the message content
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT content_text, transcription 
                FROM messages 
                WHERE id = ?
            """, (message_id,))
            message = cursor.fetchone()
            conn.close()
            
            if not message:
                return None
            
            text = message[0] or message[1] or ""
            
            prompt = f"""
            Analyze this athlete message to detect if they're requesting something actionable.
            
            Message: "{text}"
            
            If they're asking for something specific (appointment, information, action), respond with:
            {{
                "has_request": true,
                "title": "Brief task title",
                "details": "Detailed description of what needs to be done",
                "due_at": "YYYY-MM-DD" (optional, if they mentioned a date)
            }}
            
            If they're just sharing information or general conversation, respond with:
            {{
                "has_request": false
            }}
            """
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            
            result = response.choices[0].message.content
            todo_data = json.loads(result)
            
            if todo_data.get("has_request"):
                # Create todo
                conn = self._get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO todos (
                        athlete_id, message_id, title, details, due_at
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    athlete_id, message_id, todo_data["title"],
                    todo_data["details"], todo_data.get("due_at")
                ))
                conn.commit()
                conn.close()
                
                return todo_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting todo: {e}")
            return None
    
    async def process_incoming_message(
        self, 
        event: MessageEvent, 
        actions: WorkflowActions = None
    ) -> Dict[str, Any]:
        """
        Process incoming message through the complete workflow
        
        Returns:
            Dict with results of each action performed
        """
        if actions is None:
            actions = WorkflowActions()
        
        # Generate dedupe hash
        dedupe_hash = self._generate_dedupe_hash(event)
        
        # Check for duplicates
        if self._is_duplicate(dedupe_hash):
            logger.info(f"Duplicate message detected: {dedupe_hash}")
            return {"status": "duplicate", "message": "Message already processed"}
        
        # Persist message
        message_id = self._persist_message(event, dedupe_hash)
        
        results = {
            "status": "success",
            "message_id": message_id,
            "dedupe_hash": dedupe_hash,
            "actions_performed": {}
        }
        
        # Perform configured actions
        if actions.generate_highlights:
            highlights = await self._generate_highlights(message_id, event.athlete_id)
            results["actions_performed"]["highlights"] = highlights
        
        if actions.suggest_reply:
            reply = await self._suggest_reply(message_id, event.athlete_id)
            results["actions_performed"]["suggested_reply"] = reply
        
        if actions.maybe_todo:
            todo = await self._detect_todo(message_id, event.athlete_id)
            results["actions_performed"]["todo"] = todo
        
        logger.info(f"Message processed successfully: {message_id}")
        return results
    
    async def generate_highlights_for_message(self, message_id: int, max_items: int = 5, overwrite: bool = False) -> List[Dict]:
        """Generate AI-suggested highlights for a specific message"""
        try:
            # Check if highlights already exist for this message
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM highlights 
                WHERE message_id = ? AND source = 'ai' AND status = 'suggested'
            """, (message_id,))
            existing = cursor.fetchall()
            conn.close()
            
            if existing and not overwrite:
                # Return existing suggestions
                return await self._get_highlights_for_message(message_id)
            
            # Get the athlete_id for this message
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT athlete_id FROM messages WHERE id = ?", (message_id,))
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return []
            
            athlete_id = result[0]
            
            # Generate new highlights
            highlights = await self._generate_highlights(message_id, athlete_id)
            return highlights
            
        except Exception as e:
            logger.error(f"Error generating highlights for message: {e}")
            return []
    
    async def _get_highlights_for_message(self, message_id: int) -> List[Dict]:
        """Get highlights for a specific message"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, highlight_text, category, score, source, status
            FROM highlights 
            WHERE message_id = ?
            ORDER BY created_at DESC
        """, (message_id,))
        highlights = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": h[0],
                "text": h[1],
                "category": h[2],
                "score": h[3],
                "source": h[4],
                "status": h[5]
            }
            for h in highlights
        ]
    
    async def update_highlight(self, highlight_id: int, text: str = None, category: str = None, 
                              status: str = None, reviewed_by: str = None) -> bool:
        """Update a highlight (for HIL workflow)"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if text is not None:
                updates.append("highlight_text = ?")
                params.append(text)
            
            if category is not None:
                updates.append("category = ?")
                params.append(category)
            
            if status is not None:
                updates.append("status = ?")
                params.append(status)
            
            if reviewed_by is not None:
                updates.append("reviewed_by = ?")
                params.append(reviewed_by)
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(highlight_id)
            
            query = f"""
                UPDATE highlights 
                SET {', '.join(updates)}
                WHERE id = ?
            """
            
            cursor.execute(query, params)
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating highlight: {e}")
            return False
    
    async def bulk_update_highlights(self, highlight_ids: List[int], status: str, reviewed_by: str = None) -> bool:
        """Bulk update highlights (for Accept All / Reject All)"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            placeholders = ','.join(['?' for _ in highlight_ids])
            params = [status, reviewed_by] + highlight_ids
            
            cursor.execute(f"""
                UPDATE highlights 
                SET status = ?, reviewed_by = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id IN ({placeholders})
            """, params)
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error bulk updating highlights: {e}")
            return False
    
    async def get_athlete_highlights(self, athlete_id: int, status: str = "all", source: str = "all") -> List[Dict]:
        """Get highlights for an athlete with filtering"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT id, highlight_text, category, score, source, status, created_at
                FROM highlights 
                WHERE athlete_id = ?
            """
            params = [athlete_id]
            
            if status != "all":
                query += " AND status = ?"
                params.append(status)
            
            if source != "all":
                query += " AND source = ?"
                params.append(source)
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            highlights = cursor.fetchall()
            conn.close()
            
            return [
                {
                    "id": h[0],
                    "text": h[1],
                    "category": h[2],
                    "score": h[3],
                    "source": h[4],
                    "status": h[5],
                    "created_at": h[6]
                }
                for h in highlights
            ]
            
        except Exception as e:
            logger.error(f"Error getting athlete highlights: {e}")
            return []

# Global workflow service instance
workflow_service = WorkflowService() 