#!/usr/bin/env python3
"""
New endpoints for the workflow system
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from workflow_service import MessageEvent, WorkflowActions, workflow_service

logger = logging.getLogger(__name__)

# Pydantic models for request validation
class ManualIngestRequest(BaseModel):
    athlete_id: int
    content_text: Optional[str] = None
    content_audio_url: Optional[str] = None
    transcription: Optional[str] = None
    source_channel: str = "manual"
    source_message_id: Optional[str] = None
    generate_highlights: bool = False
    suggest_reply: bool = False
    maybe_todo: bool = False

class SendMessageRequest(BaseModel):
    athlete_id: int
    message: str
    channel: str  # whatsapp, telegram, email
    reply_to_message_id: Optional[int] = None

def add_workflow_endpoints(app: FastAPI, db_path: str = 'database.db'):
    """Add workflow endpoints to the FastAPI app"""
    
    def get_db_connection():
        return sqlite3.connect(db_path)
    
    @app.post("/ingest/manual")
    async def manual_ingest(request: ManualIngestRequest):
        """Manual message ingestion from UI"""
        try:
            # Create message event
            event = MessageEvent(
                source_channel=request.source_channel,
                source_message_id=request.source_message_id or f"manual_{datetime.now().timestamp()}",
                athlete_id=request.athlete_id,
                content_text=request.content_text,
                content_audio_url=request.content_audio_url,
                transcription=request.transcription
            )
            
            # Configure actions
            actions = WorkflowActions(
                save_to_history=True,
                generate_highlights=request.generate_highlights,
                suggest_reply=request.suggest_reply,
                maybe_todo=request.maybe_todo
            )
            
            # Process message
            result = await workflow_service.process_incoming_message(event, actions)
            
            return JSONResponse({
                "status": "success",
                "result": result
            })
            
        except Exception as e:
            logger.error(f"Error in manual ingest: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/communication-hub/conversations/{athlete_id}")
    async def get_athlete_conversations(athlete_id: int):
        """Get all conversations for an athlete"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT c.id, c.topic, c.created_at, c.updated_at,
                       COUNT(m.id) as message_count,
                       MAX(m.created_at) as last_message_at
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.athlete_id = ?
                GROUP BY c.id
                ORDER BY c.updated_at DESC
            """, (athlete_id,))
            
            conversations = cursor.fetchall()
            conn.close()
            
            return JSONResponse({
                "conversations": [
                    {
                        "id": conv[0],
                        "topic": conv[1],
                        "created_at": conv[2],
                        "updated_at": conv[3],
                        "message_count": conv[4],
                        "last_message_at": conv[5]
                    }
                    for conv in conversations
                ]
            })
            
        except Exception as e:
            logger.error(f"Error getting conversations: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/communication-hub/conversations/{conversation_id}/messages")
    async def get_conversation_messages(conversation_id: int):
        """Get all messages in a conversation"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT m.id, m.direction, m.content_text, m.transcription,
                       m.source_channel, m.created_at, m.metadata_json
                FROM messages m
                WHERE m.conversation_id = ?
                ORDER BY m.created_at ASC
            """, (conversation_id,))
            
            messages = cursor.fetchall()
            conn.close()
            
            return JSONResponse({
                "messages": [
                    {
                        "id": msg[0],
                        "direction": msg[1],
                        "content_text": msg[2],
                        "transcription": msg[3],
                        "source_channel": msg[4],
                        "created_at": msg[5],
                        "metadata": json.loads(msg[6]) if msg[6] else {}
                    }
                    for msg in messages
                ]
            })
            
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/messages/{message_id}/highlights/generate")
    async def generate_highlights_for_message(message_id: int):
        """Generate highlights for a specific message"""
        try:
            # Get message info
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT athlete_id FROM messages WHERE id = ?
            """, (message_id,))
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                raise HTTPException(status_code=404, detail="Message not found")
            
            athlete_id = result[0]
            
            # Generate highlights
            highlights = await workflow_service._generate_highlights(message_id, athlete_id)
            
            return JSONResponse({
                "status": "success",
                "highlights": highlights
            })
            
        except Exception as e:
            logger.error(f"Error generating highlights: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/messages/{message_id}/reply/suggest")
    async def suggest_reply_for_message(message_id: int):
        """Suggest a reply for a specific message"""
        try:
            # Get message info
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT athlete_id FROM messages WHERE id = ?
            """, (message_id,))
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                raise HTTPException(status_code=404, detail="Message not found")
            
            athlete_id = result[0]
            
            # Suggest reply
            reply = await workflow_service._suggest_reply(message_id, athlete_id)
            
            return JSONResponse({
                "status": "success",
                "suggested_reply": reply
            })
            
        except Exception as e:
            logger.error(f"Error suggesting reply: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/messages/{message_id}/todo")
    async def create_todo_from_message(message_id: int):
        """Create a todo from a specific message"""
        try:
            # Get message info
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT athlete_id FROM messages WHERE id = ?
            """, (message_id,))
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                raise HTTPException(status_code=404, detail="Message not found")
            
            athlete_id = result[0]
            
            # Detect and create todo
            todo = await workflow_service._detect_todo(message_id, athlete_id)
            
            return JSONResponse({
                "status": "success",
                "todo": todo
            })
            
        except Exception as e:
            logger.error(f"Error creating todo: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/athletes/{athlete_id}/todos")
    async def get_athlete_todos(athlete_id: int, status: Optional[str] = None):
        """Get todos for an athlete"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT t.id, t.title, t.details, t.status, t.due_at, t.created_at,
                       m.content_text, m.source_channel
                FROM todos t
                LEFT JOIN messages m ON t.message_id = m.id
                WHERE t.athlete_id = ?
            """
            params = [athlete_id]
            
            if status:
                query += " AND t.status = ?"
                params.append(status)
            
            query += " ORDER BY t.created_at DESC"
            
            cursor.execute(query, params)
            todos = cursor.fetchall()
            conn.close()
            
            return JSONResponse({
                "todos": [
                    {
                        "id": todo[0],
                        "title": todo[1],
                        "details": todo[2],
                        "status": todo[3],
                        "due_at": todo[4],
                        "created_at": todo[5],
                        "source_message": todo[6],
                        "source_channel": todo[7]
                    }
                    for todo in todos
                ]
            })
            
        except Exception as e:
            logger.error(f"Error getting todos: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/athletes/{athlete_id}/todos")
    async def create_athlete_todo(
        athlete_id: int,
        title: str = Form(...),
        details: str = Form(""),
        due_at: Optional[str] = Form(None),
        message_id: Optional[int] = Form(None)
    ):
        """Create a manual todo for an athlete"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO todos (athlete_id, message_id, title, details, due_at)
                VALUES (?, ?, ?, ?, ?)
            """, (athlete_id, message_id, title, details, due_at))
            
            todo_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return JSONResponse({
                "status": "success",
                "todo_id": todo_id
            })
            
        except Exception as e:
            logger.error(f"Error creating todo: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.patch("/todos/{todo_id}")
    async def update_todo(
        todo_id: int,
        status: str = Form(...),
        title: Optional[str] = Form(None),
        details: Optional[str] = Form(None),
        due_at: Optional[str] = Form(None)
    ):
        """Update a todo"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Build update query dynamically
            updates = ["status = ?"]
            params = [status]
            
            if title is not None:
                updates.append("title = ?")
                params.append(title)
            
            if details is not None:
                updates.append("details = ?")
                params.append(details)
            
            if due_at is not None:
                updates.append("due_at = ?")
                params.append(due_at)
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(todo_id)
            
            query = f"UPDATE todos SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            
            conn.commit()
            conn.close()
            
            return JSONResponse({
                "status": "success",
                "todo_id": todo_id
            })
            
        except Exception as e:
            logger.error(f"Error updating todo: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/send/{channel}")
    async def send_message(
        channel: str,
        athlete_id: int = Form(...),
        message: str = Form(...),
        reply_to_message_id: Optional[int] = Form(None)
    ):
        """Send message through specified channel"""
        try:
            # Validate channel
            if channel not in ["whatsapp", "telegram", "email"]:
                raise HTTPException(status_code=400, detail="Invalid channel")
            
            # Get athlete info
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name, phone, email FROM athletes WHERE id = ?
            """, (athlete_id,))
            athlete = cursor.fetchone()
            conn.close()
            
            if not athlete:
                raise HTTPException(status_code=404, detail="Athlete not found")
            
            # Send message based on channel
            result = {}
            if channel == "whatsapp":
                # Use existing WhatsApp sending logic
                from main import send_whatsapp_message
                result = await send_whatsapp_message(athlete[1], message)
            elif channel == "telegram":
                # TODO: Implement Telegram sending
                result = {"status": "not_implemented", "message": "Telegram sending not implemented yet"}
            elif channel == "email":
                # TODO: Implement email sending
                result = {"status": "not_implemented", "message": "Email sending not implemented yet"}
            
            # Record outgoing message
            if result.get("status") == "success":
                event = MessageEvent(
                    source_channel=channel,
                    source_message_id=f"outgoing_{datetime.now().timestamp()}",
                    athlete_id=athlete_id,
                    content_text=message
                )
                
                # Create outgoing message record
                conn = get_db_connection()
                cursor = conn.cursor()
                conversation_id = workflow_service._get_or_create_conversation(athlete_id)
                
                cursor.execute("""
                    INSERT INTO messages (
                        conversation_id, athlete_id, source_channel, source_message_id,
                        direction, content_text
                    ) VALUES (?, ?, ?, ?, 'out', ?)
                """, (conversation_id, athlete_id, channel, event.source_message_id, message))
                
                conn.commit()
                conn.close()
            
            return JSONResponse({
                "status": "success",
                "result": result
            })
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/highlights/{athlete_id}")
    async def get_athletes_highlights(
        athlete_id: int,
        status: str = "all",
        source: str = "all",
        category: Optional[str] = None
    ):
        """Get highlights for an athlete with HIL filtering"""
        try:
            highlights = await workflow_service.get_athlete_highlights(athlete_id, status, source)
            
            # Filter by category if specified
            if category:
                highlights = [h for h in highlights if h["category"] == category]
            
            return JSONResponse({"highlights": highlights})
            
        except Exception as e:
            logger.error(f"Error getting highlights: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/messages/{message_id}/highlights/generate")
    async def generate_highlights_for_message(
        message_id: int, 
        max_items: int = 5, 
        overwrite: bool = False
    ):
        """Generate AI-suggested highlights for a specific message"""
        try:
            highlights = await workflow_service.generate_highlights_for_message(
                message_id, max_items, overwrite
            )
            return JSONResponse({"highlights": highlights})
        except Exception as e:
            logger.error(f"Error generating highlights: {e}")
            raise HTTPException(status_code=500, detail="Error generating highlights")
    
    @app.patch("/highlights/{highlight_id}")
    async def update_highlight(highlight_id: int, request: dict):
        """Update a highlight (for HIL workflow)"""
        try:
            text = request.get("text")
            category = request.get("category")
            status = request.get("status")
            reviewed_by = request.get("reviewed_by")
            
            success = await workflow_service.update_highlight(
                highlight_id, text, category, status, reviewed_by
            )
            if success:
                return JSONResponse({"ok": True, "message": "Highlight updated successfully"})
            else:
                raise HTTPException(status_code=500, detail="Failed to update highlight")
        except Exception as e:
            logger.error(f"Error updating highlight: {e}")
            raise HTTPException(status_code=500, detail="Error updating highlight")
    
    @app.post("/highlights/bulk")
    async def bulk_update_highlights(request: dict):
        """Bulk update highlights (for Accept All / Reject All)"""
        try:
            highlight_ids = request.get("highlight_ids", [])
            status = request.get("status")
            reviewed_by = request.get("reviewed_by")
            
            if not highlight_ids or not status:
                raise HTTPException(status_code=400, detail="highlight_ids and status are required")
            
            success = await workflow_service.bulk_update_highlights(
                highlight_ids, status, reviewed_by
            )
            if success:
                return JSONResponse({"ok": True, "message": f"Updated {len(highlight_ids)} highlights"})
            else:
                raise HTTPException(status_code=500, detail="Failed to bulk update highlights")
        except Exception as e:
            logger.error(f"Error bulk updating highlights: {e}")
            raise HTTPException(status_code=500, detail="Error bulk updating highlights")
    
    logger.info("✅ Workflow endpoints added successfully") 