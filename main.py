import os
import sqlite3
import datetime
import logging
from typing import Optional
import re
import json

from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# OpenAI imports for GPT-4o-mini integration
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Import transcription service
from transcription_service import transcription_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

"""
Simple dashboard web application for processing audio messages and generating
personalised responses.

This FastAPI application exposes endpoints that allow you to:

* Upload an audio file (e.g. WhatsApp or Telegram voice message). The file is
  stored locally and a placeholder transcription is returned. In a production
  environment you could replace the placeholder logic with a real speech
  recognition library (e.g. OpenAI Whisper or Vosk) to convert audio to text.

* Generate a response to the transcribed message. For demonstration purposes
  this implementation looks for similar past messages in a local SQLite
  database using fuzzy string matching. If a close match is found, the
  associated previous reply is used as the base response; otherwise a
  placeholder message is returned. In production you could call an external
  language model such as GPT‑4o using the OpenAI API.

* Save the final edited response. When you save, the original transcription,
  the automatically generated reply and your final edited reply are stored in
  an SQLite database. This growing knowledge base can then be used to improve
  future responses by supplying examples of how you like to communicate.

* View a history of past interactions via a simple HTML page.

* Automatic WhatsApp and Telegram integration via webhooks that match phone
  numbers to athletes and save conversations automatically.

Please note that this file alone does not provide a full working experience.
The HTML templates live in the ``templates`` directory and should be created
alongside this file. Additionally, to run the application locally you need
the ``fastapi``, ``uvicorn`` and ``python‑multipart`` packages installed in
your Python environment.
"""

# Initialise directories and database
os.makedirs('uploads', exist_ok=True)

DB_PATH = 'database.db'
conn = sqlite3.connect(DB_PATH, check_same_thread=False)

# Function to normalize phone numbers for matching
def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number by removing non-digits and handling international formats.
    
    Parameters
    ----------
    phone : str
        The phone number to normalize
        
    Returns
    -------
    str
        Normalized phone number (digits only)
    """
    if not phone:
        return ""
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Handle international formats - if it starts with country code, keep it
    # If it starts with 0, remove the leading 0 (common in many countries)
    if digits_only.startswith('0') and len(digits_only) > 9:
        digits_only = digits_only[1:]
    
    return digits_only

# Function to find athlete by phone number
def find_athlete_by_phone(phone: str) -> Optional[dict]:
    """
    Find an athlete by their phone number using fuzzy matching.
    
    Parameters
    ----------
    phone : str
        The phone number to search for
        
    Returns
    -------
    Optional[dict]
        Athlete data if found, None otherwise
    """
    normalized_input = normalize_phone_number(phone)
    if not normalized_input:
        return None
    
    with conn:
        cursor = conn.execute(
            "SELECT id, name, email, phone, sport, level, created_at FROM athletes WHERE phone IS NOT NULL AND phone != ''"
        )
        athletes = cursor.fetchall()
    
    for athlete in athletes:
        stored_phone = normalize_phone_number(athlete[3])
        # Check if the last 8-10 digits match (to handle different country code formats)
        if stored_phone and normalized_input:
            if (stored_phone[-8:] == normalized_input[-8:] or 
                stored_phone[-9:] == normalized_input[-9:] or
                stored_phone[-10:] == normalized_input[-10:]):
                return {
                    "id": athlete[0],
                    "name": athlete[1], 
                    "email": athlete[2],
                    "phone": athlete[3],
                    "sport": athlete[4],
                    "level": athlete[5],
                    "created_at": athlete[6]
                }
    return None

# Create the table for storing interactions if it doesn't already exist
with conn:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS athletes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            phone TEXT,
            sport TEXT,
            level TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER,
            timestamp TEXT,
            filename TEXT,
            transcription TEXT,
            generated_response TEXT,
            final_response TEXT,
            audio_duration REAL,
            category TEXT,
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'pending',
            notes TEXT,
            source TEXT DEFAULT 'manual',
            external_message_id TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes (id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS athlete_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER,
            metric_name TEXT,
            metric_value TEXT,
            recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (athlete_id) REFERENCES athletes (id)
        )
        """
    )
    
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
    
    # Add source column if it doesn't exist (for existing databases)
    try:
        conn.execute("ALTER TABLE records ADD COLUMN source TEXT DEFAULT 'manual'")
    except sqlite3.OperationalError:
        pass  # Column already exists
        
    try:
        conn.execute("ALTER TABLE records ADD COLUMN external_message_id TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists


app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Redirect root to dashboard."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard")


@app.get("/communication-hub", response_class=HTMLResponse)
async def communication_hub(request: Request) -> HTMLResponse:
    """Serve the omnichannel communication hub."""
    return templates.TemplateResponse("communication_hub.html", {"request": request})


@app.get("/communication-hub/athletes", response_class=JSONResponse)
async def get_communication_athletes() -> JSONResponse:
    """Get athletes for communication hub."""
    with conn:
        cursor = conn.execute(
            """
            SELECT a.id, a.name, a.email, a.phone, a.sport, a.level, a.created_at,
                   COUNT(r.id) as total_conversations,
                   MAX(r.timestamp) as last_conversation
            FROM athletes a
            LEFT JOIN records r ON a.id = r.athlete_id
            GROUP BY a.id
            ORDER BY a.name
            """
        )
        athletes = cursor.fetchall()
    
    return JSONResponse({
        "athletes": [
            {
                "id": a[0],
                "name": a[1],
                "email": a[2],
                "phone": a[3],
                "sport": a[4],
                "level": a[5],
                "created_at": a[6],
                "total_conversations": a[7],
                "last_conversation": a[8]
            }
            for a in athletes
        ]
    })


@app.get("/communication-hub/athletes/{athlete_id}/conversations", response_class=JSONResponse)
async def get_athlete_conversations(athlete_id: int) -> JSONResponse:
    """Get all conversations for an athlete."""
    with conn:
        cursor = conn.execute(
            """
            SELECT r.id, r.timestamp, r.transcription, r.final_response, 
                   r.category, r.priority, r.status, r.notes, r.source,
                   r.external_message_id
            FROM records r
            WHERE r.athlete_id = ?
            ORDER BY r.timestamp DESC
            """,
            (athlete_id,)
        )
        records = cursor.fetchall()
    
    return JSONResponse({
        "conversations": [
            {
                "id": r[0],
                "timestamp": r[1],
                "transcription": r[2],
                "final_response": r[3],
                "category": r[4],
                "priority": r[5],
                "status": r[6],
                "notes": r[7],
                "source": r[8] if len(r) > 8 else "manual",
                "external_message_id": r[9]
            }
            for r in records
        ]
    })


@app.post("/communication-hub/send-message")
async def send_communication_message(
    athlete_id: int = Form(...),
    message: str = Form(...),
    platform: str = Form(...),
    subject: str = Form("")
) -> JSONResponse:
    """Send a message to an athlete via specified platform."""
    try:
        # Get athlete information
        with conn:
            cursor = conn.execute(
                "SELECT name, email, phone FROM athletes WHERE id = ?",
                (athlete_id,)
            )
            athlete = cursor.fetchone()
            
        if not athlete:
            return JSONResponse({"status": "error", "message": "Athlete not found"}, status_code=404)
            
        athlete_name, athlete_email, athlete_phone = athlete
        
        # Save the message to database
        timestamp = datetime.datetime.now().isoformat()
        
        with conn:
            conn.execute(
                """
                INSERT INTO records (
                    athlete_id, timestamp, transcription, generated_response,
                    final_response, category, priority, notes, status, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    athlete_id,
                    timestamp,
                    f"[OUTGOING via {platform.upper()}]: {message}",
                    message,
                    message,
                    "outgoing",
                    "medium",
                    f"Sent via {platform}",
                    "completed",
                    platform
                ),
            )
        
        # Smart platform selection based on available contact info
        if platform.lower() == "whatsapp" and athlete_phone:
            # Send via WhatsApp if phone number is available
            whatsapp_result = await send_whatsapp_message(athlete_phone, message)
            if whatsapp_result["status"] == "sent":
                return JSONResponse({
                    "status": "sent", 
                    "message": f"Message sent via WhatsApp to {athlete_name}",
                    "timestamp": timestamp,
                    "platform": "whatsapp"
                })
            elif whatsapp_result["status"] == "skipped":
                return JSONResponse({
                    "status": "saved", 
                    "message": f"Message saved (WhatsApp not configured) for {athlete_name}",
                    "timestamp": timestamp,
                    "platform": "whatsapp"
                })
            else:
                return JSONResponse({
                    "status": "error", 
                    "message": f"WhatsApp sending failed: {whatsapp_result.get('message', 'Unknown error')}"
                }, status_code=500)
        
        elif platform.lower() == "email" and athlete_email:
            # TODO: Implement email sending
            return JSONResponse({
                "status": "saved", 
                "message": f"Message queued for email to {athlete_name}",
                "timestamp": timestamp,
                "platform": "email"
            })
        
        elif platform.lower() == "sms" and athlete_phone:
            # TODO: Implement SMS sending
            return JSONResponse({
                "status": "saved", 
                "message": f"Message queued for SMS to {athlete_name}",
                "timestamp": timestamp,
                "platform": "sms"
            })
        
        # Auto-select best available platform if not specified or not available
        elif platform.lower() == "auto" or platform.lower() == "manual":
            if athlete_phone:
                # Try WhatsApp first
                whatsapp_result = await send_whatsapp_message(athlete_phone, message)
                if whatsapp_result["status"] == "sent":
                    return JSONResponse({
                        "status": "sent", 
                        "message": f"Message sent via WhatsApp to {athlete_name}",
                        "timestamp": timestamp,
                        "platform": "whatsapp"
                    })
                elif whatsapp_result["status"] == "skipped":
                    # WhatsApp not configured, save to database
                    return JSONResponse({
                        "status": "saved", 
                        "message": f"Message saved for {athlete_name} (WhatsApp not configured)",
                        "timestamp": timestamp,
                        "platform": "whatsapp"
                    })
                else:
                    # WhatsApp failed, save to database
                    return JSONResponse({
                        "status": "saved", 
                        "message": f"Message saved for {athlete_name} (WhatsApp failed)",
                        "timestamp": timestamp,
                        "platform": "whatsapp"
                    })
            elif athlete_email:
                # Try email
                return JSONResponse({
                    "status": "saved", 
                    "message": f"Message queued for email to {athlete_name}",
                    "timestamp": timestamp,
                    "platform": "email"
                })
            else:
                # No contact info available
                return JSONResponse({
                    "status": "saved", 
                    "message": f"Message saved for {athlete_name} (no contact info available)",
                    "timestamp": timestamp,
                    "platform": "manual"
                })
        
        else:
            # For other platforms or when contact info is missing, just save to database
            contact_info = "phone" if athlete_phone else "email" if athlete_email else "no contact info"
            return JSONResponse({
                "status": "saved", 
                "message": f"Message saved for {athlete_name} via {platform} ({contact_info})",
                "timestamp": timestamp,
                "platform": platform
            })
            
    except Exception as e:
        logger.error(f"Error sending communication message: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Error sending message: {str(e)}"
        }, status_code=500)


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)) -> JSONResponse:
    """
    Receive an audio file, save it locally and return a placeholder transcript.

    Parameters
    ----------
    file : UploadFile
        The uploaded audio file (e.g. .ogg, .m4a) from WhatsApp/Telegram.

    Returns
    -------
    JSONResponse
        JSON containing the generated (placeholder) transcription and stored
        filename.
    """
    # Read the uploaded file contents
    contents = await file.read()
    
    # Create a unique filename using timestamp to avoid collisions
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    safe_name = re.sub(r'[^\w\-_\.]', '_', file.filename)  # Sanitize filename
    filename = f"{timestamp}_{safe_name}"
    
    # Use absolute path for uploads directory
    uploads_dir = os.path.abspath('uploads')
    file_path = os.path.join(uploads_dir, filename)
    
    # Ensure uploads directory exists
    os.makedirs(uploads_dir, exist_ok=True)
    
    # Save the file to disk
    try:
        logger.info(f"Saving file to: {file_path}")
        with open(file_path, 'wb') as out_file:
            out_file.write(contents)
        
        # Verify file was created and is not empty
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not created: {file_path}")
        
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValueError("File is empty")
            
        logger.info(f"File saved successfully: {file_path} ({file_size} bytes)")
        
        # Use OpenAI Whisper API for actual transcription
        transcription = await transcription_service.transcribe_audio(file_path)
        
        if transcription is None:
            transcription = (
                f"[Error transcribing {file.filename}. Please check the audio format]"
            )
        
        return JSONResponse({"transcription": transcription, "filename": filename})
        
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        # Clean up file if it exists
        if os.path.exists(file_path):
            os.remove(file_path)
        return JSONResponse({
            "transcription": f"[Error: {str(e)}]",
            "filename": None
        }, status_code=500)


def find_best_match(transcription: str) -> Optional[str]:
    """
    Find the most similar past transcription using fuzzy matching.

    This helper searches through all saved records in the database and
    calculates a fuzzy match score between the new transcription and each
    stored transcription. If a match above a threshold (70) is found, the
    corresponding final response is returned. Otherwise returns None.

    Parameters
    ----------
    transcription : str
        The new transcription text to compare.

    Returns
    -------
    Optional[str]
        The best matching stored response or None if no sufficiently similar
        transcription exists.
    """
    try:
        from fuzzywuzzy import fuzz
    except ImportError:
        # If fuzzywuzzy isn't installed, skip matching
        return None
    best_response: Optional[str] = None
    best_score = 0
    with conn:
        cursor = conn.execute(
            "SELECT transcription, final_response FROM records"
        )
        for prev_trans, prev_resp in cursor.fetchall():
            if not prev_trans:
                continue
            # Compute token sort ratio to allow for different word orders
            score = fuzz.token_sort_ratio(transcription.lower(), prev_trans.lower())
            if score > best_score:
                best_score = score
                best_response = prev_resp
    if best_score >= 70:
        return best_response
    return None


async def generate_ai_response(transcription: str) -> str:
    """
    Generate AI response using GPT-4o-mini for athlete coaching context.
    
    Parameters
    ----------
    transcription : str
        The athlete's message transcription
        
    Returns
    -------
    str
        Generated response from GPT-4o-mini
    """
    try:
        system_prompt = """Eres un entrenador deportivo profesional especializado en atletismo de élite. 
        Respondes a mensajes de audio de tus atletas de manera empática, profesional y motivadora.
        
        Tus respuestas deben ser:
        - Personalizadas y empáticas
        - Técnicamente precisas
        - Motivadoras pero realistas
        - Enfocadas en el rendimiento y bienestar del atleta
        - Breves y directas (máximo 100 palabras)
        
        Siempre considera aspectos de:
        - Entrenamiento y técnica
        - Nutrición deportiva
        - Recuperación y descanso
        - Psicología deportiva
        - Prevención de lesiones"""
        
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Mensaje del atleta: {transcription}"}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        # Fallback response if OpenAI fails
        return f"Gracias por tu mensaje. Te responderé pronto con más detalles sobre: {transcription[:50]}..."


@app.post("/generate")
async def generate(transcription: str = Form(...)) -> JSONResponse:
    """
    Generate a reply based on the provided transcription using GPT-4o-mini.

    First attempts to find a similar past transcription in the database using 
    fuzzy matching. If a close match is found, the corresponding final response 
    is used as the base. If not, GPT-4o-mini generates a new personalized response
    for athlete coaching context.

    Parameters
    ----------
    transcription : str
        The input transcript for which a reply should be generated.

    Returns
    -------
    JSONResponse
        JSON containing the generated response text and a boolean flag
        indicating whether a similar response was found.
    """
    # Try to reuse a previous response if a similar transcription exists
    best_response = find_best_match(transcription)
    if best_response:
        generated = best_response
        reused = True
    else:
        # Generate new response using GPT-4o-mini
        generated = await generate_ai_response(transcription)
        reused = False
    
    return JSONResponse({"generated_response": generated, "reused": reused})


@app.post("/save")
async def save(
    athlete_id: int = Form(...),
    filename: Optional[str] = Form(None),
    transcription: str = Form(...),
    generated_response: str = Form(...),
    final_response: str = Form(...),
    category: str = Form("general"),
    priority: str = Form("medium"),
    notes: str = Form(""),
    source: str = Form("manual"),
) -> JSONResponse:
    """
    Persist the conversation data into the SQLite database with athlete association.

    Parameters
    ----------
    athlete_id : int
        ID of the athlete this conversation belongs to
    filename : Optional[str]
        Name of the saved audio file (if any).
    transcription : str
        Text transcribed from the audio message.
    generated_response : str
        The automatically generated response (before editing).
    final_response : str
        The final response after the user has edited it.
    category : str
        Category of the conversation (training, nutrition, recovery, etc.)
    priority : str
        Priority level (low, medium, high)
    notes : str
        Additional notes about the conversation
    source : str
        Source of the conversation (manual, whatsapp, telegram)

    Returns
    -------
    JSONResponse
        JSON confirming that the record has been saved.
    """
    timestamp = datetime.datetime.now().isoformat()
    with conn:
        conn.execute(
            """
            INSERT INTO records (
                athlete_id, timestamp, filename, transcription,
                generated_response, final_response, category, priority, notes, status, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                athlete_id,
                timestamp,
                filename,
                transcription,
                generated_response,
                final_response,
                category,
                priority,
                notes,
                "completed",
                source
            ),
        )
    return JSONResponse({"status": "saved"})


@app.get("/api/athletes", response_class=JSONResponse)
async def get_athletes() -> JSONResponse:
    """Get all athletes."""
    with conn:
        cursor = conn.execute(
            "SELECT id, name, email, phone, sport, level, created_at FROM athletes ORDER BY name"
        )
        athletes = cursor.fetchall()
    return JSONResponse({
        "athletes": [
            {
                "id": a[0],
                "name": a[1],
                "email": a[2],
                "phone": a[3],
                "sport": a[4],
                "level": a[5],
                "created_at": a[6]
            }
            for a in athletes
        ]
    })


@app.post("/api/athletes", response_class=JSONResponse)
async def create_athlete(
    name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    sport: str = Form(""),
    level: str = Form("")
) -> JSONResponse:
    """Create a new athlete."""
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO athletes (name, email, phone, sport, level) VALUES (?, ?, ?, ?, ?)",
                (name, email, phone, sport, level)
            )
            athlete_id = cursor.lastrowid
        return JSONResponse({"status": "created", "athlete_id": athlete_id})
    except sqlite3.IntegrityError:
        return JSONResponse({"status": "error", "message": "Email already exists"})


@app.get("/api/athletes/{athlete_id}/history", response_class=JSONResponse)
async def get_athlete_history(athlete_id: int) -> JSONResponse:
    """Get conversation history for a specific athlete."""
    with conn:
        cursor = conn.execute(
            """
            SELECT id, timestamp, transcription, final_response, category, priority, status, notes, source
            FROM records
            WHERE athlete_id = ?
            ORDER BY timestamp DESC
            """,
            (athlete_id,)
        )
        records = cursor.fetchall()
    return JSONResponse({
        "history": [
            {
                "id": r[0],
                "timestamp": r[1],
                "transcription": r[2],
                "final_response": r[3],
                "category": r[4],
                "priority": r[5],
                "status": r[6],
                "notes": r[7],
                "source": r[8] if len(r) > 8 else "manual"
            }
            for r in records
        ]
    })


@app.get("/athletes", response_class=HTMLResponse)
async def athletes(request: Request) -> HTMLResponse:
    """Serve the athletes management page."""
    return templates.TemplateResponse("athletes.html", {"request": request})


@app.get("/athletes/manage", response_class=HTMLResponse)
async def manage_athletes(request: Request) -> HTMLResponse:
    """Serve the athletes management page (legacy route)."""
    return templates.TemplateResponse("athletes.html", {"request": request})


@app.get("/api/athletes/{athlete_id}", response_class=JSONResponse)
async def get_athlete(athlete_id: int) -> JSONResponse:
    """Get athlete details."""
    with conn:
        cursor = conn.execute(
            "SELECT id, name, email, phone, sport, level, created_at FROM athletes WHERE id = ?",
            (athlete_id,)
        )
        athlete = cursor.fetchone()
    if athlete:
        return JSONResponse({
            "id": athlete[0],
            "name": athlete[1],
            "email": athlete[2],
            "phone": athlete[3],
            "sport": athlete[4],
            "level": athlete[5],
            "created_at": athlete[6]
        })
    return JSONResponse({"status": "error", "message": "Athlete not found"}, status_code=404)


@app.put("/api/athletes/{athlete_id}", response_class=JSONResponse)
async def update_athlete(
    athlete_id: int,
    name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    sport: str = Form(""),
    level: str = Form("")
) -> JSONResponse:
    """Update an existing athlete."""
    try:
        with conn:
            cursor = conn.execute(
                """
                UPDATE athletes 
                SET name = ?, email = ?, phone = ?, sport = ?, level = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (name, email, phone, sport, level, athlete_id)
            )
            
            if cursor.rowcount > 0:
                return JSONResponse({"status": "updated", "message": "Athlete updated successfully"})
            else:
                return JSONResponse({"status": "error", "message": "Athlete not found"}, status_code=404)
                
    except sqlite3.IntegrityError:
        return JSONResponse({"status": "error", "message": "Email already exists"}, status_code=400)
    except Exception as e:
        logger.error(f"Error updating athlete: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.delete("/api/athletes/{athlete_id}", response_class=JSONResponse)
async def delete_athlete(athlete_id: int) -> JSONResponse:
    """Delete an athlete and all associated records."""
    try:
        with conn:
            # First check if athlete exists
            cursor = conn.execute("SELECT id FROM athletes WHERE id = ?", (athlete_id,))
            if not cursor.fetchone():
                return JSONResponse({"status": "error", "message": "Athlete not found"}, status_code=404)
            
            # Delete associated records
            conn.execute("DELETE FROM records WHERE athlete_id = ?", (athlete_id,))
            conn.execute("DELETE FROM athlete_highlights WHERE athlete_id = ?", (athlete_id,))
            conn.execute("DELETE FROM athlete_metrics WHERE athlete_id = ?", (athlete_id,))
            
            # Delete the athlete
            conn.execute("DELETE FROM athletes WHERE id = ?", (athlete_id,))
            
            return JSONResponse({"status": "deleted", "message": "Athlete and all associated data deleted successfully"})
                
    except Exception as e:
        logger.error(f"Error deleting athlete: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Serve the enhanced dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/history", response_class=HTMLResponse)
async def history(request: Request) -> HTMLResponse:
    """
    Display a simple table containing all past saved responses.

    Returns
    -------
    HTMLResponse
        The rendered history page with a table of records.
    """
    with conn:
        cursor = conn.execute(
            "SELECT id, timestamp, transcription, final_response, source FROM records ORDER BY id DESC"
        )
        rows = cursor.fetchall()
    return templates.TemplateResponse(
        "history.html", {"request": request, "records": rows}
    )


@app.get("/athletes/{athlete_id}/history/view", response_class=HTMLResponse)
async def view_athlete_history(request: Request, athlete_id: int) -> HTMLResponse:
    """
    Display history page filtered for a specific athlete.

    Parameters
    ----------
    athlete_id : int
        The ID of the athlete to show history for.

    Returns
    -------
    HTMLResponse
        The rendered history page with athlete-specific records.
    """
    # Get athlete details
    with conn:
        cursor = conn.execute(
            "SELECT id, name, email, phone, sport, level, created_at FROM athletes WHERE id = ?",
            (athlete_id,)
        )
        athlete = cursor.fetchone()
        
        if not athlete:
            # If athlete not found, redirect to general history
            cursor = conn.execute(
                "SELECT id, timestamp, transcription, final_response, source FROM records ORDER BY id DESC"
            )
            rows = cursor.fetchall()
            return templates.TemplateResponse(
                "history.html", {"request": request, "records": rows}
            )
        
        # Get records for this specific athlete
        cursor = conn.execute(
            "SELECT id, timestamp, transcription, final_response, source FROM records WHERE athlete_id = ? ORDER BY id DESC",
            (athlete_id,)
        )
        rows = cursor.fetchall()
    
    athlete_data = {
        "id": athlete[0],
        "name": athlete[1],
        "email": athlete[2],
        "phone": athlete[3],
        "sport": athlete[4],
        "level": athlete[5],
        "created_at": athlete[6]
    }
    
    return templates.TemplateResponse(
        "history.html", {
            "request": request, 
            "records": rows,
            "athlete": athlete_data
        }
    )


# WhatsApp and Telegram Integration Endpoints

def extract_whatsapp_events(payload: dict) -> list[dict]:
    """Extrae eventos de mensajes del payload de WhatsApp de Meta."""
    events = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                phone = msg.get("from", "")
                # obtener cuerpo según el tipo de mensaje
                msg_type = msg.get("type")
                if msg_type == "text":
                    text = msg.get("text", {}).get("body", "")
                elif msg_type == "image":
                    text = "[Imagen recibida]"
                elif msg_type == "audio":
                    text = "[Audio recibido]"
                elif msg_type == "document":
                    text = "[Documento recibido]"
                else:
                    text = msg.get(msg_type, {}).get("body", "") if msg_type else ""
                events.append({"phone": phone, "text": text, "id": msg.get("id")})
    return events

async def send_whatsapp_message(phone: str, message: str) -> dict:
    """Envía un mensaje por WhatsApp usando Twilio o Meta API."""
    
    # Try Twilio first (if configured)
    twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
    
    if twilio_account_sid and twilio_auth_token and twilio_whatsapp_number:
        return await send_whatsapp_via_twilio(phone, message)
    
    # Fallback to Meta API
    phone_id = os.getenv("WHATSAPP_PHONE_ID")
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    
    if not phone_id or not access_token:
        logger.warning("No se configuraron credenciales de WhatsApp (Twilio o Meta); mensaje no enviado")
        return {"status": "skipped", "message": "WhatsApp credentials not configured"}
    
    return await send_whatsapp_via_meta(phone, message)


async def send_whatsapp_via_twilio(phone: str, message: str) -> dict:
    """Envía un mensaje por WhatsApp usando Twilio API directamente."""
    try:
        import httpx
        
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
        
        if not account_sid or not auth_token or not from_number:
            return {"status": "error", "message": "Twilio credentials not configured"}
        
        # Ensure phone number has whatsapp: prefix
        to_number = phone if phone.startswith("whatsapp:") else f"whatsapp:{phone}"
        from_number = from_number if from_number.startswith("whatsapp:") else f"whatsapp:{from_number}"
        
        # Twilio API endpoint
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        
        # Request payload
        payload = {
            "Body": message,
            "From": from_number,
            "To": to_number
        }
        
        # Basic auth with account SID and auth token
        auth = (account_sid, auth_token)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=payload, auth=auth)
            
            if response.status_code == 201:
                data = response.json()
                logger.info(f"Twilio WhatsApp message sent: {data.get('sid')}")
                return {"status": "sent", "data": {"sid": data.get('sid')}}
            else:
                logger.error(f"Twilio API error: {response.status_code} - {response.text}")
                return {"status": "error", "message": f"Twilio API error: {response.status_code}"}
        
    except Exception as e:
        logger.error(f"Error sending Twilio WhatsApp message: {e}")
        return {"status": "error", "message": str(e)}


async def send_whatsapp_via_meta(phone: str, message: str) -> dict:
    """Envía un mensaje por WhatsApp usando la API de Meta."""
    phone_id = os.getenv("WHATSAPP_PHONE_ID")
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    
    if not phone_id or not access_token:
        return {"status": "skipped", "message": "Meta WhatsApp credentials not configured"}
    
    url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": message}
    }
    headers = {
        "Authorization": f"Bearer {access_token}", 
        "Content-Type": "application/json"
    }
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                return {"status": "sent", "data": resp.json()}
            else:
                logger.error(f"Meta WhatsApp API error: {resp.status_code} - {resp.text}")
                return {"status": "error", "data": resp.json()}
    except Exception as e:
        logger.error(f"Error sending Meta WhatsApp message: {e}")
        return {"status": "error", "message": str(e)}

async def process_incoming_message(phone: str, message: str, source: str, external_id: str = None) -> dict:
    """
    Process an incoming message from WhatsApp or Telegram.
    
    Parameters
    ----------
    phone : str
        Phone number of the sender
    message : str
        The message content
    source : str
        Source of the message ('whatsapp' or 'telegram')
    external_id : str, optional
        External message ID for tracking
        
    Returns
    -------
    dict
        Processing result with status and response
    """
    # Find athlete by phone number
    athlete = find_athlete_by_phone(phone)
    if not athlete:
        return {
            "status": "error",
            "message": f"No athlete found for phone number {phone}",
            "response": None
        }
    
    try:
        # Generate AI response
        ai_response = await generate_ai_response(message)
        
        # Save the conversation automatically
        timestamp = datetime.datetime.now().isoformat()
        with conn:
            conn.execute(
                """
                INSERT INTO records (
                    athlete_id, timestamp, transcription, generated_response, 
                    final_response, category, priority, notes, status, source, external_message_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    athlete["id"],
                    timestamp,
                    message,
                    ai_response,
                    ai_response,  # Use AI response as final response initially
                    "general",    # Default category
                    "medium",     # Default priority
                    f"Auto-processed {source} message",
                    "completed",
                    source,
                    external_id
                ),
            )
        
        return {
            "status": "success",
            "message": f"Message processed for athlete {athlete['name']}",
            "athlete": athlete,
            "response": ai_response
        }
    
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Error processing message: {str(e)}",
            "response": None
        }


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request) -> JSONResponse:
    """
    WhatsApp webhook endpoint for receiving messages.
    
    Supports both Meta API and Twilio formats.
    
    Returns
    -------
    JSONResponse
        Response status and any reply message
    """
    try:
        payload = await request.json()
        logger.info(f"WhatsApp webhook received: {payload}")
        
        # Meta API format
        if "entry" in payload:
            events = extract_whatsapp_events(payload)
            for ev in events:
                if ev["phone"] and ev["text"]:
                    result = await process_incoming_message(
                        phone=ev["phone"],
                        message=ev["text"],
                        source="whatsapp",
                        external_id=ev["id"]
                    )
                    if result["status"] == "success":
                        # Send automatic response if configured
                        if result.get("response"):
                            await send_whatsapp_message(ev["phone"], result["response"])
                        return JSONResponse({
                            "status": "processed",
                            "athlete": result["athlete"]["name"],
                            "response": result["response"]
                        })
                    else:
                        return JSONResponse({"status": "error", "message": result["message"]}, status_code=400)
        
        # Twilio format (legacy)
        elif "messages" in payload:
            for message_data in payload["messages"]:
                phone = message_data.get("from", "").replace("whatsapp:", "")
                message_text = message_data.get("text", {}).get("body", "")
                message_id = message_data.get("id", "")
                
                if phone and message_text:
                    result = await process_incoming_message(
                        phone=phone, 
                        message=message_text, 
                        source="whatsapp", 
                        external_id=message_id
                    )
                    if result["status"] == "success":
                        # Send automatic response if configured
                        if result.get("response"):
                            await send_whatsapp_message(phone, result["response"])
                        return JSONResponse({
                            "status": "processed", 
                            "athlete": result["athlete"]["name"], 
                            "response": result["response"]
                        })
                    else:
                        return JSONResponse({"status": "error", "message": result["message"]}, status_code=400)
        
        return JSONResponse({"status": "no_message_found"})
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Webhook processing error: {str(e)}"
        }, status_code=500)


@app.get("/webhook/whatsapp")
async def whatsapp_webhook_verify(request: Request) -> JSONResponse:
    """WhatsApp webhook verification endpoint."""
    try:
        # Handle webhook verification
        challenge = request.query_params.get("hub.challenge")
        verify_token = request.query_params.get("hub.verify_token")
        
        # You should verify the token matches your configured webhook token
        expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "your_verify_token")
        
        if verify_token == expected_token and challenge:
            return JSONResponse({"hub.challenge": challenge})
        else:
            return JSONResponse({"error": "Invalid verification"}, status_code=403)
            
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": f"Verification error: {str(e)}"
        }, status_code=500)


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request) -> JSONResponse:
    """
    Telegram webhook endpoint for receiving messages.
    
    This endpoint should be configured with Telegram Bot API using setWebhook.
    
    Returns
    -------
    JSONResponse
        Response status and any reply message
    """
    try:
        payload = await request.json()
        
        # Extract message data from Telegram webhook payload
        if "message" in payload:
            message_data = payload["message"]
            
            # Extract phone number from user contact info if available
            # Note: Telegram doesn't always provide phone numbers
            phone = None
            message_text = message_data.get("text", "")
            message_id = message_data.get("message_id", "")
            user_data = message_data.get("from", {})
            
            # Try to get phone from contact info
            if "contact" in message_data:
                phone = message_data["contact"].get("phone_number", "")
            
            # If no phone in contact, try to match by Telegram username or ID
            # This requires you to manually map Telegram users to athletes
            telegram_id = user_data.get("id", "")
            telegram_username = user_data.get("username", "")
            
            if not phone:
                # You could implement a mapping table for Telegram users to athletes
                # For now, we'll include this info in the error message
                return JSONResponse({
                    "status": "error",
                    "message": f"No phone number available for Telegram user {telegram_username} (ID: {telegram_id})",
                    "suggestion": "User needs to share contact or manually map Telegram ID to athlete"
                }, status_code=400)
            
            if phone and message_text:
                result = await process_incoming_message(
                    phone=phone,
                    message=message_text,
                    source="telegram",
                    external_id=str(message_id)
                )
                
                if result["status"] == "success":
                    return JSONResponse({
                        "status": "processed",
                        "athlete": result["athlete"]["name"],
                        "response": result["response"]
                    })
                else:
                    return JSONResponse({
                        "status": "error",
                        "message": result["message"]
                    }, status_code=400)
        
        return JSONResponse({"status": "no_message_found"})
        
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": f"Telegram webhook processing error: {str(e)}"
        }, status_code=500)


@app.post("/test/webhook")
async def test_webhook(request: Request) -> JSONResponse:
    """
    Test endpoint for webhook functionality.
    
    Use this to test the phone number matching and message processing.
    
    Expected JSON payload:
    {
        "phone": "+1234567890",
        "message": "Test message",
        "source": "test"
    }
    """
    try:
        payload = await request.json()
        phone = payload.get("phone", "")
        message = payload.get("message", "")
        source = payload.get("source", "test")
        
        if not phone or not message:
            return JSONResponse({
                "status": "error",
                "message": "Phone and message are required"
            }, status_code=400)
        
        result = await process_incoming_message(
            phone=phone,
            message=message,
            source=source,
            external_id="test_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        )
        
        return JSONResponse(result)
        
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": f"Test webhook error: {str(e)}"
        }, status_code=500)


@app.get("/test/whatsapp-config")
async def test_whatsapp_config() -> JSONResponse:
    """Test endpoint to check WhatsApp configuration (Twilio or Meta)."""
    
    # Check Twilio configuration
    twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
    
    # Check Meta configuration
    meta_phone_id = os.getenv("WHATSAPP_PHONE_ID")
    meta_access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    
    config_status = {
        "twilio": {
            "configured": bool(twilio_account_sid and twilio_auth_token and twilio_whatsapp_number),
            "account_sid": twilio_account_sid[:10] + "..." if twilio_account_sid else None,
            "auth_token": twilio_auth_token[:10] + "..." if twilio_auth_token else None,
            "whatsapp_number": twilio_whatsapp_number
        },
        "meta": {
            "configured": bool(meta_phone_id and meta_access_token),
            "phone_id": meta_phone_id[:10] + "..." if meta_phone_id else None,
            "access_token": meta_access_token[:10] + "..." if meta_access_token else None
        },
        "system_status": "working" if (twilio_account_sid and twilio_auth_token and twilio_whatsapp_number) or (meta_phone_id and meta_access_token) else "limited",
        "message": "WhatsApp configured (Twilio or Meta)" if (twilio_account_sid and twilio_auth_token and twilio_whatsapp_number) or (meta_phone_id and meta_access_token) else "WhatsApp not configured - messages will be saved to database"
    }
    
    # Test sending a message if any provider is configured
    if config_status["system_status"] == "working":
        try:
            test_result = await send_whatsapp_message("+1234567890", "Test message from Elite CRM")
            config_status["test_send_result"] = test_result
        except Exception as e:
            config_status["test_send_error"] = str(e)
    else:
        config_status["test_send_result"] = {"status": "skipped", "message": "No WhatsApp credentials configured"}
    
    return JSONResponse(config_status)


@app.get("/system/status")
async def system_status() -> JSONResponse:
    """Get overall system status including WhatsApp configuration."""
    phone_id = os.getenv("WHATSAPP_PHONE_ID")
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    
    # Check database connection
    try:
        with conn:
            cursor = conn.execute("SELECT COUNT(*) FROM athletes")
            athlete_count = cursor.fetchone()[0]
        db_status = "connected"
    except Exception as e:
        db_status = "error"
        athlete_count = 0
    
    # Check WhatsApp configuration (Twilio or Meta)
    twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
    
    meta_phone_id = os.getenv("WHATSAPP_PHONE_ID")
    meta_access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    
    whatsapp_configured = (twilio_account_sid and twilio_auth_token and twilio_whatsapp_number) or (meta_phone_id and meta_access_token)
    
    status = {
        "system": {
            "status": "operational",
            "version": "1.0.0",
            "database": db_status,
            "athletes_count": athlete_count
        },
        "whatsapp": {
            "configured": whatsapp_configured,
            "twilio_configured": bool(twilio_account_sid and twilio_auth_token and twilio_whatsapp_number),
            "meta_configured": bool(meta_phone_id and meta_access_token),
            "status": "ready" if whatsapp_configured else "not_configured",
            "message": "WhatsApp configured (Twilio or Meta)" if whatsapp_configured else "WhatsApp not configured - messages will be saved to database"
        },
        "features": {
            "communication_hub": "enabled",
            "athlete_management": "enabled",
            "message_storage": "enabled",
            "whatsapp_sending": "enabled" if whatsapp_configured else "disabled",
            "email_sending": "planned",
            "sms_sending": "planned"
        },
        "recommendations": []
    }
    
    # Add recommendations based on current status
    if not whatsapp_configured:
        status["recommendations"].append({
            "type": "whatsapp_setup",
            "priority": "medium",
            "message": "Configure WhatsApp (Twilio or Meta) for real message sending",
            "action": "Follow the WhatsApp setup guide in WHATSAPP_SETUP_GUIDE.md"
        })
    
    if athlete_count == 0:
        status["recommendations"].append({
            "type": "add_athletes",
            "priority": "high",
            "message": "Add your first athlete to start using the system",
            "action": "Go to /athletes and add an athlete"
        })
    
    return JSONResponse(status)


@app.get("/api/athletes/phone/{phone}")
async def find_athlete_by_phone_endpoint(phone: str) -> JSONResponse:
    """
    Find an athlete by phone number endpoint.
    
    Parameters
    ----------
    phone : str
        Phone number to search for
        
    Returns
    -------
    JSONResponse
        Athlete data if found, error if not found
    """
    athlete = find_athlete_by_phone(phone)
    if athlete:
        return JSONResponse({
            "status": "found",
            "athlete": athlete
        })
    else:
        return JSONResponse({
            "status": "not_found",
            "message": f"No athlete found for phone number {phone}"
        }, status_code=404)


# Functions for managing athlete highlights

def add_athlete_highlight(
    athlete_id: int, 
    highlight_text: str, 
    category: str = "general", 
    source_conversation_id: Optional[int] = None
) -> dict:
    """
    Add a new highlight for an athlete.
    
    Parameters
    ----------
    athlete_id : int
        ID of the athlete
    highlight_text : str
        The key point or summary to highlight
    category : str
        Category of the highlight (training, nutrition, recovery, etc.)
    source_conversation_id : int, optional
        ID of the conversation this highlight was derived from
        
    Returns
    -------
    dict
        Result with status and highlight ID
    """
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO athlete_highlights 
                (athlete_id, highlight_text, category, source_conversation_id)
                VALUES (?, ?, ?, ?)
                """,
                (athlete_id, highlight_text, category, source_conversation_id)
            )
            highlight_id = cursor.lastrowid
        return {
            "status": "success",
            "highlight_id": highlight_id,
            "message": "Highlight added successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error adding highlight: {str(e)}"
        }


def get_athlete_highlights(athlete_id: int, active_only: bool = True) -> list:
    """
    Get all highlights for an athlete.
    
    Parameters
    ----------
    athlete_id : int
        ID of the athlete
    active_only : bool
        Whether to return only active highlights
        
    Returns
    -------
    list
        List of highlights for the athlete
    """
    try:
        with conn:
            query = """
                SELECT h.id, h.highlight_text, h.category, h.created_at, 
                       h.updated_at, h.is_active, h.source_conversation_id,
                       r.transcription, r.final_response
                FROM athlete_highlights h
                LEFT JOIN records r ON h.source_conversation_id = r.id
                WHERE h.athlete_id = ?
            """
            if active_only:
                query += " AND h.is_active = 1"
            query += " ORDER BY h.created_at DESC"
            
            cursor = conn.execute(query, (athlete_id,))
            highlights = cursor.fetchall()
        
        return [
            {
                "id": h[0],
                "highlight_text": h[1],
                "category": h[2],
                "created_at": h[3],
                "updated_at": h[4],
                "is_active": bool(h[5]),
                "source_conversation_id": h[6],
                "source_transcription": h[7],
                "source_response": h[8]
            }
            for h in highlights
        ]
    except Exception as e:
        return []


def update_highlight_status(highlight_id: int, is_active: bool) -> dict:
    """
    Update the active status of a highlight.
    
    Parameters
    ----------
    highlight_id : int
        ID of the highlight to update
    is_active : bool
        Whether the highlight should be active
        
    Returns
    -------
    dict
        Result with status
    """
    try:
        with conn:
            conn.execute(
                """
                UPDATE athlete_highlights 
                SET is_active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (is_active, highlight_id)
            )
        return {
            "status": "success",
            "message": "Highlight updated successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error updating highlight: {str(e)}"
        }


def delete_highlight(highlight_id: int) -> dict:
    """
    Delete a highlight.
    
    Parameters
    ----------
    highlight_id : int
        ID of the highlight to delete
        
    Returns
    -------
    dict
        Result with status
    """
    try:
        with conn:
            conn.execute(
                "DELETE FROM athlete_highlights WHERE id = ?",
                (highlight_id,)
            )
        return {
            "status": "success",
            "message": "Highlight deleted successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error deleting highlight: {str(e)}"
        }


def generate_highlights_from_conversation(
    athlete_id: int, 
    conversation_id: int, 
    transcription: str, 
    response: str
) -> dict:
    """
    Generate highlights from a conversation using AI.
    
    Parameters
    ----------
    athlete_id : int
        ID of the athlete
    conversation_id : int
        ID of the conversation
    transcription : str
        The athlete's message
    response : str
        The coach's response
        
    Returns
    -------
    dict
        Result with generated highlights
    """
    try:
        # Combine transcription and response for context
        full_context = f"Athlete: {transcription}\nCoach: {response}"
        
        # Use AI to extract key points
        prompt = f"""Extract the 2-3 most important key points from this conversation between an athlete and coach. 
        Focus on actionable insights, important decisions, or significant updates.
        
        Conversation:
        {full_context}
        
        Return only the key points as a JSON array of strings, like:
        ["Key point 1", "Key point 2", "Key point 3"]"""
        
        # For now, return a simple implementation
        # In production, this would use the OpenAI API
        highlights = [
            f"Conversation about: {transcription[:50]}...",
            f"Coach response focused on: {response[:50]}..."
        ]
        
        # Add highlights to database
        added_highlights = []
        for highlight in highlights:
            result = add_athlete_highlight(
                athlete_id=athlete_id,
                highlight_text=highlight,
                category="auto-generated",
                source_conversation_id=conversation_id
            )
            if result["status"] == "success":
                added_highlights.append(result["highlight_id"])
        
        return {
            "status": "success",
            "highlights": added_highlights,
            "count": len(added_highlights)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error generating highlights: {str(e)}"
        }


# API endpoints for athlete highlights

@app.post("/api/athletes/{athlete_id}/highlights", response_class=JSONResponse)
async def create_highlight(
    athlete_id: int,
    highlight_text: str = Form(...),
    category: str = Form("general"),
    source_conversation_id: Optional[int] = Form(None)
) -> JSONResponse:
    """
    Create a new highlight for an athlete.
    
    Parameters
    ----------
    athlete_id : int
        ID of the athlete
    highlight_text : str
        The key point or summary to highlight
    category : str
        Category of the highlight
    source_conversation_id : int, optional
        ID of the conversation this highlight was derived from
        
    Returns
    -------
    JSONResponse
        Result with status and highlight ID
    """
    result = add_athlete_highlight(
        athlete_id=athlete_id,
        highlight_text=highlight_text,
        category=category,
        source_conversation_id=source_conversation_id
    )
    return JSONResponse(result)


@app.get("/api/athletes/{athlete_id}/highlights", response_class=JSONResponse)
async def get_highlights(
    athlete_id: int,
    active_only: bool = True,
    manual_only: bool = False
) -> JSONResponse:
    """
    Get all highlights for an athlete.
    
    Parameters
    ----------
    athlete_id : int
        ID of the athlete
    active_only : bool
        Whether to return only active highlights
    manual_only : bool
        Whether to return only manual highlights (not AI-generated)
        
    Returns
    -------
    JSONResponse
        List of highlights for the athlete
    """
    highlights = get_athlete_highlights(athlete_id, active_only)
    
    if manual_only:
        # Filter to only manual highlights (those without source_conversation_id)
        highlights = [h for h in highlights if not h.get('source_conversation_id')]
    
    return JSONResponse({"highlights": highlights})


@app.put("/highlights/{highlight_id}", response_class=JSONResponse)
async def update_highlight(
    highlight_id: int,
    is_active: bool = Form(...)
) -> JSONResponse:
    """
    Update the active status of a highlight.
    
    Parameters
    ----------
    highlight_id : int
        ID of the highlight to update
    is_active : bool
        Whether the highlight should be active
        
    Returns
    -------
    JSONResponse
        Result with status
    """
    result = update_highlight_status(highlight_id, is_active)
    return JSONResponse(result)


@app.put("/highlights/{highlight_id}/content", response_class=JSONResponse)
async def update_highlight_content(
    highlight_id: int,
    highlight_text: str = Form(...),
    category: str = Form(...)
) -> JSONResponse:
    """
    Update the content of a highlight.
    
    Parameters
    ----------
    highlight_id : int
        ID of the highlight to update
    highlight_text : str
        The new highlight text
    category : str
        The new category
        
    Returns
    -------
    JSONResponse
        Result with status
    """
    try:
        with conn:
            cursor = conn.execute("""
                UPDATE athlete_highlights 
                SET highlight_text = ?, category = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (highlight_text, category, highlight_id))
            
            if cursor.rowcount > 0:
                return JSONResponse({"status": "success", "message": "Highlight updated successfully"})
            else:
                return JSONResponse({"status": "error", "message": "Highlight not found"}, status_code=404)
                
    except Exception as e:
        logger.error(f"Error updating highlight content: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.delete("/highlights/{highlight_id}", response_class=JSONResponse)
async def delete_highlight_endpoint(highlight_id: int) -> JSONResponse:
    """
    Delete a highlight.
    
    Parameters
    ----------
    highlight_id : int
        ID of the highlight to delete
        
    Returns
    -------
    JSONResponse
        Result with status
    """
    result = delete_highlight(highlight_id)
    return JSONResponse(result)


@app.post("/api/athletes/{athlete_id}/highlights/generate", response_class=JSONResponse)
async def generate_highlights(
    athlete_id: int,
    conversation_id: int = Form(...),
    transcription: str = Form(...),
    response: str = Form(...)
) -> JSONResponse:
    """
    Generate highlights from a conversation using AI.
    
    Parameters
    ----------
    athlete_id : int
        ID of the athlete
    conversation_id : int
        ID of the conversation
    transcription : str
        The athlete's message
    response : str
        The coach's response
        
    Returns
    -------
    JSONResponse
        Result with generated highlights
    """
    result = generate_highlights_from_conversation(
        athlete_id=athlete_id,
        conversation_id=conversation_id,
        transcription=transcription,
        response=response
    )
    return JSONResponse(result)
