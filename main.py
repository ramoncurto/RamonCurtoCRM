import os
import sqlite3
import datetime
from datetime import datetime
import logging
from typing import Optional
import re
import json
import math
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# OpenAI imports for GPT-4o-mini integration
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Import transcription service
from transcription_service import transcription_service

# Import workflow system
from workflow_service import MessageEvent, WorkflowActions, workflow_service
from workflow_endpoints import add_workflow_endpoints

# Import GPT risk analyzer
from gpt_risk_analysis import GPTRiskAnalyzer

# Import AI outreach module
from ai_outreach import generate_outreach

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
AUTO_GPT_ENABLED = os.getenv("AUTO_GPT_ENABLED", "true").lower() == "true"

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

# ===== DATABASE INITIALIZATION (UNIFIED) =====
def init_unified_database():
    """Initialize the unified database schema"""
    with conn:
        # Athletes table (unchanged)
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
        
        # Conversations table (unified)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                athlete_id INTEGER NOT NULL,
                topic TEXT,
                channel TEXT DEFAULT 'unified',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (athlete_id) REFERENCES athletes(id)
            )
            """
        )
        
        # Messages table (unified - replaces records)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER,
                athlete_id INTEGER NOT NULL,
                source_channel TEXT NOT NULL DEFAULT 'manual',
                source_message_id TEXT,
                direction TEXT CHECK(direction IN ('in', 'out')) NOT NULL DEFAULT 'in',
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
                external_message_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id),
                FOREIGN KEY (athlete_id) REFERENCES athletes(id)
            )
            """
        )
        
        # Highlights table (unified)
        conn.execute(
            """
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
            """
        )
        
        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_athlete_id ON messages(athlete_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_highlights_athlete_id ON highlights(athlete_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_highlights_message_id ON highlights(message_id)")

# Initialize unified database
init_unified_database()

# ===== UTILITY FUNCTIONS (UNIFIED) =====
def get_or_create_conversation(athlete_id: int) -> int:
    """Get or create conversation for athlete"""
    with conn:
        cursor = conn.execute(
            "SELECT id FROM conversations WHERE athlete_id = ? ORDER BY updated_at DESC LIMIT 1",
            (athlete_id,)
        )
        result = cursor.fetchone()
        
        if result:
            conversation_id = result[0]
            # Update conversation timestamp
            conn.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (conversation_id,)
            )
        else:
            # Create new conversation
            cursor = conn.execute(
                "INSERT INTO conversations (athlete_id, channel) VALUES (?, 'unified')",
                (athlete_id,)
            )
            conversation_id = cursor.lastrowid
        
        return conversation_id

# Add new coach todos table
def init_coach_todos_table():
    """Initialize the coach todos table for global todo management"""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coach_todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER,
            text TEXT NOT NULL,
            priority TEXT CHECK(priority IN ('P1', 'P2', 'P3')) DEFAULT 'P2',
            status TEXT CHECK(status IN ('backlog', 'doing', 'done')) DEFAULT 'backlog',
            due_date DATE,
            created_by TEXT CHECK(created_by IN ('athlete', 'coach')) DEFAULT 'coach',
            source_record_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id)
        )
    """)
    
    # Create indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_coach_todos_athlete_id ON coach_todos(athlete_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_coach_todos_status ON coach_todos(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_coach_todos_priority ON coach_todos(priority)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_coach_todos_created_by ON coach_todos(created_by)")
    
    conn.commit()

# Add todos table for workflow
def init_todos_table():
    """Initialize the todos table for workflow todo management"""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            message_id INTEGER,
            title TEXT NOT NULL,
            details TEXT,
            status TEXT CHECK(status IN ('pending', 'in_progress', 'completed', 'cancelled')) DEFAULT 'pending',
            priority TEXT CHECK(priority IN ('low', 'medium', 'high')) DEFAULT 'medium',
            due_at DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id),
            FOREIGN KEY (message_id) REFERENCES messages(id)
        )
    """)
    
    # Check if priority column exists, if not add it
    cursor.execute("PRAGMA table_info(todos)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'priority' not in columns:
        cursor.execute("ALTER TABLE todos ADD COLUMN priority TEXT CHECK(priority IN ('low', 'medium', 'high')) DEFAULT 'medium'")
        print("✅ Added priority column to todos table")
    
    # Create indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_todos_athlete_id ON todos(athlete_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_todos_message_id ON todos(message_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_todos_status ON todos(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_todos_priority ON todos(priority)")
    
    conn.commit()

# Initialize coach todos table
init_coach_todos_table()

# Initialize todos table
init_todos_table()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add workflow endpoints
add_workflow_endpoints(app)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Redirect to athletes page."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/athletes")


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)) -> JSONResponse:
    """
    Recibir un archivo de audio, guardarlo localmente y transcribirlo.
    Versión mejorada con mejor manejo de errores y soporte para más formatos.

    Parameters
    ----------
    file : UploadFile
        El archivo de audio subido (e.g. .ogg, .opus, .m4a, .mp3, .wav) 
        desde WhatsApp/Telegram/manual.

    Returns
    -------
    JSONResponse
        JSON con la transcripción y información del archivo, o errores detallados.
    """
    # Verificar que el servicio de transcripción esté configurado
    if not transcription_service.client:
        return JSONResponse({
            "success": False,
            "error": "OpenAI API no configurada",
            "details": "Por favor configura OPENAI_API_KEY en tu archivo .env",
            "transcription": "❌ Error: OpenAI API no configurada. Configura OPENAI_API_KEY en .env",
            "filename": None
        }, status_code=500)
    
    # Validar el archivo
    if not file or not file.filename:
        return JSONResponse({
            "success": False,
            "error": "No se proporcionó archivo",
            "transcription": "❌ Error: No se proporcionó ningún archivo de audio",
            "filename": None
        }, status_code=400)
    
    # Verificar contenido del archivo
    try:
        contents = await file.read()
        if not contents:
            return JSONResponse({
                "success": False,
                "error": "Archivo vacío",
                "transcription": "❌ Error: El archivo está vacío",
                "filename": None
            }, status_code=400)
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": "Error leyendo archivo",
            "details": str(e),
            "transcription": f"❌ Error: No se pudo leer el archivo - {str(e)}",
            "filename": None
        }, status_code=400)
    
    # Obtener información del archivo
    file_extension = Path(file.filename).suffix.lower()
    file_size = len(contents)
    
    logger.info(f"📁 Archivo recibido: {file.filename} ({file_extension}, {file_size:,} bytes)")
    
    # Verificar tamaño del archivo
    if file_size > 25 * 1024 * 1024:  # 25MB limit
        return JSONResponse({
            "success": False,
            "error": "Archivo demasiado grande",
            "details": f"Tamaño: {file_size:,} bytes (máximo: 25MB)",
            "transcription": "❌ Error: El archivo es demasiado grande (>25MB). Por favor usa un archivo más pequeño.",
            "filename": None
        }, status_code=400)
    
    # Crear nombre de archivo único
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    safe_name = re.sub(r'[^\w\-_\.]', '_', file.filename)
    filename = f"{timestamp}_{safe_name}"
    
    # Usar ruta absoluta para el directorio uploads
    uploads_dir = os.path.abspath('uploads')
    file_path = os.path.join(uploads_dir, filename)
    
    # Asegurar que el directorio uploads existe
    os.makedirs(uploads_dir, exist_ok=True)
    
    try:
        # Guardar el archivo en disco
        logger.info(f"💾 Guardando archivo en: {file_path}")
        with open(file_path, 'wb') as out_file:
            out_file.write(contents)
        
        # Verificar que el archivo se guardó correctamente
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"El archivo no se creó: {file_path}")
        
        saved_size = os.path.getsize(file_path)
        if saved_size != file_size:
            raise ValueError(f"Tamaño incorrecto: esperado {file_size}, guardado {saved_size}")
            
        logger.info(f"✅ Archivo guardado exitosamente: {file_path} ({saved_size:,} bytes)")
        
        # Obtener información de formatos soportados
        format_info = transcription_service.get_supported_formats()
        
        # Determinar si el formato está soportado
        is_direct_format = file_extension in format_info['direct_formats']
        is_conversion_format = file_extension in format_info['conversion_formats']
        
        # Preparar información del formato para el usuario
        format_status = {
            "extension": file_extension,
            "is_direct_format": is_direct_format,
            "is_conversion_format": is_conversion_format,
            "ffmpeg_available": format_info['ffmpeg_available'],
            "processing_method": None
        }
        
        if is_direct_format:
            format_status["processing_method"] = "direct"
        elif is_conversion_format and format_info['ffmpeg_available']:
            format_status["processing_method"] = "conversion"
        elif is_conversion_format and not format_info['ffmpeg_available']:
            format_status["processing_method"] = "unsupported_no_ffmpeg"
        else:
            format_status["processing_method"] = "unsupported"
        
        # Transcribir usando el servicio mejorado
        logger.info(f"🎤 Iniciando transcripción...")
        transcription = await transcription_service.transcribe_audio(file_path)
        
        # Preparar respuesta
        response_data = {
            "success": True,
            "transcription": transcription,
            "filename": filename,
            "file_info": {
                "original_name": file.filename,
                "size_bytes": file_size,
                "size_mb": round(file_size / (1024 * 1024), 2),
                "format": format_status
            },
            "system_info": {
                "openai_configured": format_info['openai_configured'],
                "ffmpeg_available": format_info['ffmpeg_available']
            }
        }
        
        # Verificar si la transcripción fue exitosa
        if transcription and not transcription.startswith('❌'):
            logger.info(f"✅ Transcripción exitosa: {len(transcription)} caracteres")
            response_data["success"] = True
            response_data["character_count"] = len(transcription)
            
            # Agregar preview de la transcripción
            if len(transcription) > 100:
                response_data["preview"] = transcription[:100] + "..."
            else:
                response_data["preview"] = transcription
                
        else:
            logger.error(f"❌ Error en transcripción: {transcription}")
            response_data["success"] = False
            response_data["error"] = "Transcripción falló"
            response_data["details"] = transcription
        
        return JSONResponse(response_data)
        
    except Exception as e:
        # Limpiar archivo si existe
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"🗑️  Archivo limpiado después del error: {file_path}")
            except:
                pass
        
        error_msg = str(e)
        logger.error(f"❌ Error en transcripción: {error_msg}")
        
        # Proporcionar mensajes de error específicos
        if "Connection" in error_msg or "timeout" in error_msg.lower():
            user_error = "❌ Error de conexión. Verifica tu conexión a internet e inténtalo de nuevo."
        elif "api key" in error_msg.lower() or "authentication" in error_msg.lower():
            user_error = "❌ Error de autenticación OpenAI. Verifica tu OPENAI_API_KEY."
        elif "quota" in error_msg.lower() or "billing" in error_msg.lower():
            user_error = "❌ Cuota de OpenAI excedida. Verifica tu cuenta de facturación."
        elif "FFmpeg" in error_msg or "conversion" in error_msg.lower():
            user_error = f"❌ Error de conversión de audio. {error_msg}"
        else:
            user_error = f"❌ Error procesando audio: {error_msg}"
        
        return JSONResponse({
            "success": False,
            "error": "Error procesando archivo",
            "details": error_msg,
            "transcription": user_error,
            "filename": filename,
            "file_info": {
                "original_name": file.filename,
                "size_bytes": file_size,
                "format": file_extension
            }
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


@app.post("/generate-todo")
async def generate_todo(transcription: str = Form(...)) -> JSONResponse:
    """
    Generate a To-Do text based on the provided transcription using GPT-4o-mini.
    
    Parameters
    ----------
    transcription : str
        The input transcript for which a To-Do should be generated.
        
    Returns
    -------
    JSONResponse
        JSON containing the generated To-Do text.
    """
    try:
        # Use GPT-4o-mini to generate To-Do text
        prompt = f"""Analiza esta conversación del atleta y genera un To-Do corto y específico 
        para el entrenador. El To-Do debe ser:
        - Accionable (qué debe hacer el entrenador)
        - Específico (basado en lo que dice el atleta)
        - Corto (máximo 20 palabras)
        - Relevante para el entrenamiento
        
        Conversación del atleta: {transcription}
        
        Genera solo el texto del To-Do, sin explicaciones adicionales."""
        
        # Call OpenAI API
        try:
            import openai
            client = openai.OpenAI()
            
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un asistente especializado en generar To-Dos para entrenadores deportivos. Genera To-Dos cortos, específicos y accionables."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.3
            )
            
            # Get the generated To-Do text
            generated_todo = completion.choices[0].message.content.strip()
            
            return JSONResponse({
                "success": True,
                "generated_todo": generated_todo
            })
            
        except Exception as api_error:
            logger.error(f"OpenAI API error: {api_error}")
            # Fallback to simple To-Do
            fallback_todo = f"Revisar conversación del atleta: {transcription[:50]}..."
            return JSONResponse({
                "success": True,
                "generated_todo": fallback_todo
            })
            
    except Exception as e:
        logger.error(f"Error generating To-Do: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.post("/save")
async def save_unified(
    athlete_id: int = Form(...),
    filename: Optional[str] = Form(None),
    transcription: str = Form(...),
    generated_response: str = Form(...),
    final_response: str = Form(...),
    category: str = Form("general"),
    priority: str = Form("medium"),
    notes: str = Form(""),
    source: str = Form("manual"),
    external_message_id: Optional[str] = Form(None)
) -> JSONResponse:
    """Save conversation data using unified schema"""
    try:
        # Get or create conversation
        conversation_id = get_or_create_conversation(athlete_id)
        
        # Save the message
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO messages (
                    conversation_id, athlete_id, source_channel, source_message_id,
                    direction, transcription, generated_response, final_response,
                    category, priority, notes, status, filename, external_message_id,
                    metadata_json
                ) VALUES (?, ?, ?, ?, 'in', ?, ?, ?, ?, ?, ?, 'completed', ?, ?, ?)
                """,
                (
                    conversation_id, athlete_id, source, 
                    external_message_id or f"manual_{datetime.now().timestamp()}",
                    transcription, generated_response, final_response,
                    category, priority, notes, filename, external_message_id,
                    json.dumps({"saved_at": datetime.now().isoformat()})
                ),
            )
            message_id = cursor.lastrowid
        
        # Generate highlights from the conversation
        try:
            highlight_result = await generate_highlights_from_conversation_unified(
                athlete_id=athlete_id,
                message_id=message_id,
                transcription=transcription,
                response=final_response
            )
            
            return JSONResponse({
                "status": "saved",
                "message_id": message_id,
                "conversation_id": conversation_id,
                "highlights_generated": highlight_result.get("count", 0)
            })
        except Exception as e:
            logger.error(f"Error generating highlights: {e}")
            return JSONResponse({
                "status": "saved",
                "message_id": message_id,
                "conversation_id": conversation_id,
                "highlights_generated": 0,
                "highlight_error": str(e)
            })
            
    except Exception as e:
        logger.error(f"Error saving message: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)

# ===== HIGHLIGHTS FUNCTIONS (UNIFIED) =====
async def generate_highlights_from_conversation_unified(
    athlete_id: int, 
    message_id: int, 
    transcription: str, 
    response: str
) -> dict:
    """Generate highlights using unified schema"""
    if not AUTO_GPT_ENABLED:
        return {"status": "disabled", "count": 0}
    
    try:
        # Combine transcription and response for context
        full_context = f"Athlete: {transcription}\nCoach: {response}"
        
        # Use GPT-4o-mini to extract key points
        prompt = f"""Analiza esta conversación entre un atleta y su entrenador. 
        Genera 1-2 statements cortos y super resumidos (máximo 15 palabras cada uno) 
        que capturen lo más importante y relevante para el entrenamiento.
        
        Enfócate en:
        - Progreso del atleta
        - Problemas o dificultades mencionadas
        - Decisiones importantes sobre entrenamiento
        - Logros o mejoras
        - Aspectos que requieren atención
        
        Conversación:
        {full_context}
        
        Devuelve solo los statements como un array JSON de strings, ejemplo:
        ["Atleta reporta buen progreso en entrenamientos de monte", "Necesita mejorar técnica en subidas"]
        
        Si la conversación no contiene información relevante para el entrenamiento, devuelve un array vacío []."""
        
        try:
            import openai
            client = openai.OpenAI()
            
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un asistente especializado en análisis de conversaciones deportivas. Genera resúmenes cortos y precisos."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.3
            )
            
            ai_response = completion.choices[0].message.content.strip()
            
            try:
                highlights = json.loads(ai_response)
                if not isinstance(highlights, list):
                    highlights = []
            except:
                highlights = [f"Conversación relevante: {transcription[:50]}..."]
                
        except Exception as api_error:
            logger.error(f"OpenAI API error: {api_error}")
            highlights = [f"Conversación relevante: {transcription[:50]}..."]
        
        # Add highlights to unified database
        added_highlights = []
        with conn:
            for highlight in highlights:
                if highlight and len(highlight.strip()) > 0:
                    cursor = conn.execute(
                        """
                        INSERT INTO highlights (
                            athlete_id, message_id, highlight_text, category,
                            source, status, is_manual, is_active
                        ) VALUES (?, ?, ?, 'other', 'ai', 'accepted', 0, 1)
                        """,
                        (athlete_id, message_id, highlight.strip())
                    )
                    added_highlights.append(cursor.lastrowid)
        
        return {
            "status": "success",
            "highlights": added_highlights,
            "count": len(added_highlights)
        }
    except Exception as e:
        logger.error(f"Error generating highlights: {e}")
        return {"status": "error", "message": str(e)}

def get_athlete_highlights_unified(athlete_id: int, active_only: bool = True) -> list:
    """Get all highlights for an athlete using unified schema"""
    try:
        with conn:
            query = """
                SELECT h.id, h.highlight_text, h.category, h.created_at, 
                       h.updated_at, h.is_active, h.message_id, h.source, h.status,
                       m.transcription, m.final_response
                FROM highlights h
                LEFT JOIN messages m ON h.message_id = m.id
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
                "message_id": h[6],
                "source": h[7],
                "status": h[8],
                "source_transcription": h[9],
                "source_response": h[10]
            }
            for h in highlights
        ]
    except Exception as e:
        logger.error(f"Error getting highlights: {e}")
        return []

# ===== RISK CALCULATION (UNIFIED) =====
def get_athlete_risk_factors_unified(athlete_id: int) -> dict:
    """Calculate risk factors using unified schema"""
    try:
        with conn:
            # Get athlete data
            cursor = conn.execute(
                "SELECT id, name, created_at FROM athletes WHERE id = ?",
                (athlete_id,)
            )
            athlete = cursor.fetchone()
            
            if not athlete:
                return None
            
            # Get recent messages (last 30 days) - using messages instead of records
            cursor.execute("""
                SELECT 
                    m.transcription,
                    m.final_response,
                    m.created_at,
                    m.category,
                    m.source_channel
                FROM messages m
                WHERE m.athlete_id = ?
                AND m.created_at >= datetime('now', '-30 days')
                ORDER BY m.created_at DESC
                LIMIT 10
            """, (athlete_id,))
            
            conversations = cursor.fetchall()
            
            # Get overdue todos (unchanged)
            cursor.execute("""
                SELECT 
                    t.id,
                    t.text,
                    t.due_date,
                    t.status,
                    t.created_at
                FROM coach_todos t
                WHERE t.athlete_id = ?
                AND t.status != 'done'
                AND (t.due_date IS NULL OR t.due_date < date('now'))
                ORDER BY t.due_date ASC
            """, (athlete_id,))
            
            overdue_todos = cursor.fetchall()
            
            # Get recent highlights using unified schema
            cursor.execute("""
                SELECT 
                    h.highlight_text,
                    h.category,
                    h.created_at
                FROM highlights h
                WHERE h.athlete_id = ?
                AND h.is_active = 1
                AND h.created_at >= datetime('now', '-14 days')
                ORDER BY h.created_at DESC
            """, (athlete_id,))
            
            recent_highlights = cursor.fetchall()
            
            # Rest of the risk calculation logic remains the same...
            # [Include the rest of the risk calculation from the original function]
            
            return {
                'athlete_id': athlete_id,
                'athlete_name': athlete[1],
                'score': 50,  # Placeholder - implement full calculation
                'level': 'verde',
                'color': 'success',
                'factors': {},
                'evidence': []
            }
            
    except Exception as e:
        logger.error(f"Error calculating risk factors: {e}")
        return None


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

@app.get("/api/athletes/enhanced", response_class=JSONResponse)
async def get_athletes_enhanced() -> JSONResponse:
    """Get all athletes with enhanced data including last contact and todos count."""
    with conn:
        # Get athletes with last contact and todos count
        cursor = conn.execute(
            """
            SELECT 
                a.id, 
                a.name, 
                a.email, 
                a.phone, 
                a.sport, 
                a.level, 
                a.created_at,
                MAX(m.created_at) as last_contact,
                COUNT(CASE WHEN ct.status IN ('backlog', 'doing') THEN 1 END) as open_todos
            FROM athletes a
            LEFT JOIN messages m ON a.id = m.athlete_id
            LEFT JOIN coach_todos ct ON a.id = ct.athlete_id
            GROUP BY a.id, a.name, a.email, a.phone, a.sport, a.level, a.created_at
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
                "last_contact": a[7],
                "open_todos": a[8] or 0
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
async def get_athlete_history_unified(athlete_id: int) -> JSONResponse:
    """Get conversation history for a specific athlete using unified schema"""
    with conn:
        cursor = conn.execute(
            """
            SELECT m.id, m.created_at, m.transcription, m.final_response, 
                   m.category, m.priority, m.status, m.notes, m.source_channel,
                   m.filename, m.audio_duration, c.id as conversation_id
            FROM messages m
            LEFT JOIN conversations c ON m.conversation_id = c.id
            WHERE m.athlete_id = ?
            ORDER BY m.created_at DESC
            """,
            (athlete_id,)
        )
        messages = cursor.fetchall()
    
    return JSONResponse({
        "history": [
            {
                "id": m[0],
                "timestamp": m[1],
                "transcription": m[2],
                "final_response": m[3],
                "category": m[4],
                "priority": m[5],
                "status": m[6],
                "notes": m[7],
                "source": m[8],
                "filename": m[9],
                "audio_duration": m[10],
                "conversation_id": m[11]
            }
            for m in messages
        ]
    })


@app.get("/athletes", response_class=HTMLResponse)
async def athletes(request: Request) -> HTMLResponse:
    """Serve the athletes management page."""
    return templates.TemplateResponse("athletes.html", {"request": request})


@app.get("/athletes/{athlete_id}/workspace", response_class=HTMLResponse)
async def athlete_workspace(request: Request, athlete_id: int) -> HTMLResponse:
    """Serve the athlete workspace page."""
    # Get athlete data for the page
    with conn:
        cursor = conn.execute(
            "SELECT id, name, email, phone, sport, level FROM athletes WHERE id = ?",
            (athlete_id,)
        )
        athlete = cursor.fetchone()
    
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    
    return templates.TemplateResponse("athlete_workspace.html", {
        "request": request,
        "athlete_id": athlete_id,
        "athlete_name": athlete[1] if athlete else "Atleta"
    })


@app.get("/coach/todos", response_class=HTMLResponse)
async def coach_todo_board(request: Request) -> HTMLResponse:
    """Serve the coach todo board page."""
    return templates.TemplateResponse("coach_todo_board.html", {"request": request})


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
            conn.execute("DELETE FROM highlights WHERE athlete_id = ?", (athlete_id,))
            conn.execute("DELETE FROM athlete_metrics WHERE athlete_id = ?", (athlete_id,))
            
            # Delete the athlete
            conn.execute("DELETE FROM athletes WHERE id = ?", (athlete_id,))
            
            return JSONResponse({"status": "deleted", "message": "Athlete and all associated data deleted successfully"})
                
    except Exception as e:
        logger.error(f"Error deleting athlete: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


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
            "whatsapp_sending": "enabled if whatsapp_configured else disabled",
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
                INSERT INTO highlights 
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
                       m.transcription, m.final_response
                FROM highlights h
                LEFT JOIN messages m ON h.source_conversation_id = m.id
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
                UPDATE highlights 
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
                "DELETE FROM highlights WHERE id = ?",
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
    Generate highlights from a conversation using GPT-4o-mini.
    
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
        
        # Use GPT-4o-mini to extract key points
        prompt = f"""Analiza esta conversación entre un atleta y su entrenador. 
        Genera 1-2 statements cortos y super resumidos (máximo 15 palabras cada uno) 
        que capturen lo más importante y relevante para el entrenamiento.
        
        Enfócate en:
        - Progreso del atleta
        - Problemas o dificultades mencionadas
        - Decisiones importantes sobre entrenamiento
        - Logros o mejoras
        - Aspectos que requieren atención
        
        Conversación:
        {full_context}
        
        Devuelve solo los statements como un array JSON de strings, ejemplo:
        ["Atleta reporta buen progreso en entrenamientos de monte", "Necesita mejorar técnica en subidas"]
        
        Si la conversación no contiene información relevante para el entrenamiento, devuelve un array vacío []."""
        
        # Call OpenAI API
        try:
            import openai
            client = openai.OpenAI()
            
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un asistente especializado en análisis de conversaciones deportivas. Genera resúmenes cortos y precisos."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.3
            )
            
            # Parse the response
            ai_response = completion.choices[0].message.content.strip()
            
            # Try to parse as JSON
            try:
                import json
                highlights = json.loads(ai_response)
                if not isinstance(highlights, list):
                    highlights = []
            except:
                # If JSON parsing fails, create a simple highlight
                highlights = [f"Conversación relevante: {transcription[:50]}..."]
                
        except Exception as api_error:
            logger.error(f"OpenAI API error: {api_error}")
            # Fallback to simple highlight
            highlights = [f"Conversación relevante: {transcription[:50]}..."]
        
        # Add highlights to database
        added_highlights = []
        for highlight in highlights:
            if highlight and len(highlight.strip()) > 0:
                result = add_athlete_highlight(
                    athlete_id=athlete_id,
                    highlight_text=highlight.strip(),
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
        logger.error(f"Error generating highlights: {e}")
        return {
            "status": "error",
            "message": f"Error generating highlights: {str(e)}"
        }


# API endpoints for athlete highlights

@app.post("/api/athletes/{athlete_id}/highlights", response_class=JSONResponse)
async def create_athlete_highlight_enhanced(
    athlete_id: int,
    highlight_text: str = Form(...),
    categories: Optional[str] = Form(""),  # JSON array or CSV
    category: str = Form("general"),
    source_conversation_id: Optional[int] = Form(None)
) -> JSONResponse:
    """Create a new highlight for an athlete"""
    try:
        cursor = conn.cursor()
        
        # Validate athlete exists
        cursor.execute("SELECT id FROM athletes WHERE id = ?", (athlete_id,))
        if not cursor.fetchone():
            return JSONResponse({
                "success": False,
                "error": "Athlete not found"
            }, status_code=404)
        
        # Process categories
        categories_json = "[]"
        if categories:
            try:
                # If it's already JSON, validate it
                if categories.startswith('['):
                    json.loads(categories)
                    categories_json = categories
                else:
                    # Convert CSV to JSON array
                    cats = [c.strip() for c in categories.split(',') if c.strip()]
                    categories_json = json.dumps(cats)
            except:
                categories_json = "[]"
        
        cursor.execute("""
            INSERT INTO highlights (
                athlete_id, highlight_text, category, categories, 
                source_conversation_id, is_manual, is_active
            ) VALUES (?, ?, ?, ?, ?, 1, 1)
        """, (athlete_id, highlight_text, category, categories_json, source_conversation_id))
        
        highlight_id = cursor.lastrowid
        conn.commit()
        
        # Get the created highlight
        cursor.execute("""
            SELECT h.*, a.name as athlete_name
            FROM highlights h
            LEFT JOIN athletes a ON h.athlete_id = a.id
            WHERE h.id = ?
        """, (highlight_id,))
        
        row = cursor.fetchone()
        if row:
            # Parse categories
            categories_str = row[4] if row[4] else "[]"
            try:
                categories_list = json.loads(categories_str)
            except:
                categories_list = []
            
            highlight = {
                "id": row[0],
                "athlete_id": row[1],
                "highlight_text": row[2],
                "category": row[3],
                "categories": categories_list,
                "score": row[5],
                "source": row[6],
                "status": row[7],
                "reviewed_by": row[8],
                "is_manual": bool(row[9]),
                "is_active": bool(row[10]),
                "created_at": row[11],
                "updated_at": row[12],
                "athlete_name": row[13],
                "source_conversation_id": row[14] if len(row) > 14 else None
            }
            
            return JSONResponse({
                "success": True,
                "highlight": highlight
            })
        
        return JSONResponse({
            "success": False,
            "error": "Failed to create highlight"
        }, status_code=500)
        
    except Exception as e:
        logger.error(f"Error creating athlete highlight: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.put("/api/highlights/{highlight_id}", response_class=JSONResponse)
async def update_highlight_enhanced(
    highlight_id: int,
    highlight_text: Optional[str] = Form(None),
    categories: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(None)
) -> JSONResponse:
    """Update a highlight"""
    try:
        cursor = conn.cursor()
        
        # Get current highlight
        cursor.execute("SELECT * FROM highlights WHERE id = ?", (highlight_id,))
        current = cursor.fetchone()
        
        if not current:
            return JSONResponse({
                "success": False,
                "error": "Highlight not found"
            }, status_code=404)
        
        # Build update query
        update_fields = []
        params = []
        
        if highlight_text is not None:
            update_fields.append("highlight_text = ?")
            params.append(highlight_text)
            
        if categories is not None:
            # Process categories
            try:
                if categories.startswith('['):
                    json.loads(categories)  # Validate JSON
                    categories_json = categories
                else:
                    cats = [c.strip() for c in categories.split(',') if c.strip()]
                    categories_json = json.dumps(cats)
            except:
                categories_json = "[]"
            
            update_fields.append("categories = ?")
            params.append(categories_json)
            
        if category is not None:
            update_fields.append("category = ?")
            params.append(category)
            
        if is_active is not None:
            update_fields.append("is_active = ?")
            params.append(1 if is_active else 0)
        
        if not update_fields:
            return JSONResponse({
                "success": False,
                "error": "No fields to update"
            }, status_code=400)
        
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(highlight_id)
        
        query = f"UPDATE highlights SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
        
        # Get updated highlight
        cursor.execute("""
            SELECT h.*, a.name as athlete_name
            FROM highlights h
            LEFT JOIN athletes a ON h.athlete_id = a.id
            WHERE h.id = ?
        """, (highlight_id,))
        
        row = cursor.fetchone()
        if row:
            # Parse categories
            categories_str = row[4] if row[4] else "[]"
            try:
                categories_list = json.loads(categories_str)
            except:
                categories_list = []
            
            highlight = {
                "id": row[0],
                "athlete_id": row[1],
                "highlight_text": row[2],
                "category": row[3],
                "categories": categories_list,
                "score": row[5],
                "source": row[6],
                "status": row[7],
                "reviewed_by": row[8],
                "is_manual": bool(row[9]),
                "is_active": bool(row[10]),
                "created_at": row[11],
                "updated_at": row[12],
                "athlete_name": row[13],
                "source_conversation_id": row[14] if len(row) > 14 else None
            }
            
            return JSONResponse({
                "success": True,
                "highlight": highlight
            })
        
        return JSONResponse({
            "success": False,
            "error": "Failed to update highlight"
        }, status_code=500)
        
    except Exception as e:
        logger.error(f"Error updating highlight: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.delete("/api/highlights/{highlight_id}", response_class=JSONResponse)
async def delete_highlight_enhanced(highlight_id: int) -> JSONResponse:
    """Delete a highlight"""
    try:
        cursor = conn.cursor()
        
        # Check if highlight exists
        cursor.execute("SELECT id FROM highlights WHERE id = ?", (highlight_id,))
        if not cursor.fetchone():
            return JSONResponse({
                "success": False,
                "error": "Highlight not found"
            }, status_code=404)
        
        cursor.execute("DELETE FROM highlights WHERE id = ?", (highlight_id,))
        conn.commit()
        
        return JSONResponse({
            "success": True,
            "message": "Highlight deleted successfully"
        })
        
    except Exception as e:
        logger.error(f"Error deleting highlight: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.post("/api/athletes/{athlete_id}/highlights/generate", response_class=JSONResponse)
async def generate_highlights_enhanced(
    athlete_id: int,
    conversation_id: Optional[int] = Form(None),
    transcription: Optional[str] = Form(""),
    response: Optional[str] = Form("")
) -> JSONResponse:
    """Generate highlights from conversation using GPT-4o-mini"""
    
    # Check if automatic GPT is enabled
    if not AUTO_GPT_ENABLED:
        return JSONResponse({
            "success": True,
            "highlights": [],
            "count": 0,
            "message": "Automatic GPT highlights generation is disabled"
        })
    
    try:
        # Get athlete info for context
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name, sport, level FROM athletes WHERE id = ?", (athlete_id,))
        athlete = cursor.fetchone()
        conn.close()
        
        if not athlete:
            return JSONResponse({
                "success": False,
                "error": "Athlete not found"
            }, status_code=404)
        
        athlete_name, sport, level = athlete
        
        # Prepare context for GPT
        context = f"""
        Atleta: {athlete_name} ({sport}, nivel {level})
        Mensaje: {transcription}
        Respuesta: {response}
        """
        
        prompt = f"""
        Analiza esta conversación entre un entrenador y su atleta.
        
        {context}
        
        Genera 2-3 highlights relevantes que capturen:
        - Progreso del atleta
        - Problemas o preocupaciones
        - Objetivos o planes
        - Aspectos técnicos importantes
        - Factores de riesgo (lesiones, fatiga, etc.)
        
        Responde solo con un array JSON de strings, por ejemplo:
        ["Highlight 1", "Highlight 2", "Highlight 3"]
        """
        
        try:
            response_ai = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300
            )
            
            highlights_text = response_ai.choices[0].message.content.strip()
            
            # Try to parse as JSON array
            try:
                highlights = json.loads(highlights_text)
                if not isinstance(highlights, list):
                    highlights = [highlights_text]
            except:
                # If not valid JSON, split by lines or commas
                highlights = [h.strip() for h in highlights_text.replace('\n', ',').split(',') if h.strip()]
            
            # Create highlights in database
            created_highlights = []
            for highlight_text in highlights[:3]:  # Limit to 3 highlights
                cursor.execute("""
                    INSERT INTO highlights (
                        athlete_id, highlight_text, category, categories,
                        source_conversation_id, is_manual, is_active, source
                    ) VALUES (?, ?, ?, ?, ?, 0, 1, 'ai')
                """, (athlete_id, highlight_text, "general", "[]", conversation_id))
                
                highlight_id = cursor.lastrowid
                created_highlights.append({
                    "id": highlight_id,
                    "text": highlight_text,
                    "category": "general",
                    "categories": [],
                    "source": "ai"
                })
            
            conn.commit()
            
            return JSONResponse({
                "success": True,
                "highlights": created_highlights,
                "count": len(created_highlights)
            })
            
        except Exception as api_error:
            logger.error(f"OpenAI API error: {api_error}")
            return JSONResponse({
                "success": False,
                "error": f"Error generating highlights: {str(api_error)}"
            }, status_code=500)
            
    except Exception as e:
        logger.error(f"Error generating highlights: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

# Add routes for the new HTML interfaces
@app.get("/athletes/{athlete_id}/workspace", response_class=HTMLResponse)
async def athlete_workspace(request: Request, athlete_id: int) -> HTMLResponse:
    """Serve the athlete workspace page."""
    # Get athlete data for the page
    with conn:
        cursor = conn.execute(
            "SELECT id, name, email, phone, sport, level FROM athletes WHERE id = ?",
            (athlete_id,)
        )
        athlete = cursor.fetchone()
    
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    
    return templates.TemplateResponse("athlete_workspace.html", {
        "request": request,
        "athlete_id": athlete_id,
        "athlete_name": athlete[1] if athlete else "Atleta"
    })

@app.get("/coach/todos", response_class=HTMLResponse)
async def coach_todo_board(request: Request) -> HTMLResponse:
    """Serve the coach todo board page."""
    return templates.TemplateResponse("coach_todo_board.html", {"request": request})

# Add migration for highlights table
def migrate_athlete_highlights():
    """Add missing columns to highlights if they don't exist"""
    cursor = conn.cursor()
    
    # Check if categories column exists
    cursor.execute("PRAGMA table_info(highlights)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # Add missing columns
    missing_columns = []
    
    if 'categories' not in columns:
        missing_columns.append("categories TEXT DEFAULT '[]'")
    
    if 'source_conversation_id' not in columns:
        missing_columns.append("source_conversation_id INTEGER")
    
    if 'is_manual' not in columns:
        missing_columns.append("is_manual BOOLEAN DEFAULT 0")
    
    if 'is_active' not in columns:
        missing_columns.append("is_active BOOLEAN DEFAULT 1")
    
    if 'score' not in columns:
        missing_columns.append("score REAL DEFAULT 0.0")
    
    if 'source' not in columns:
        missing_columns.append("source TEXT DEFAULT 'manual'")
    
    if 'status' not in columns:
        missing_columns.append("status TEXT DEFAULT 'accepted'")
    
    if 'reviewed_by' not in columns:
        missing_columns.append("reviewed_by TEXT")
    
    # Add missing columns
    for column_def in missing_columns:
        try:
            column_name = column_def.split()[0]
            cursor.execute(f"ALTER TABLE highlights ADD COLUMN {column_def}")
            logger.info(f"✅ Added {column_name} column to highlights table")
        except Exception as e:
            logger.error(f"Error adding {column_def}: {e}")
    
    conn.commit()

# Run migration
migrate_athlete_highlights()

# Coach Todos endpoints (global todo management)
@app.get("/api/todos", response_class=JSONResponse)
async def get_coach_todos(
    athlete_id: Optional[int] = Query(None, description="Filter by athlete ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    q: Optional[str] = Query("", description="Search query"),
    due_from: Optional[str] = Query(None, description="Due date from (YYYY-MM-DD)"),
    due_to: Optional[str] = Query(None, description="Due date to (YYYY-MM-DD)")
) -> JSONResponse:
    """Get all coach todos with optional filtering"""
    try:
        cursor = conn.cursor()
        
        # Build query with filters
        query = """
            SELECT ct.*, a.name as athlete_name 
            FROM coach_todos ct 
            LEFT JOIN athletes a ON ct.athlete_id = a.id 
            WHERE 1=1
        """
        params = []
        
        if athlete_id is not None:
            query += " AND ct.athlete_id = ?"
            params.append(athlete_id)
            
        if status:
            query += " AND ct.status = ?"
            params.append(status)
            
        if priority:
            query += " AND ct.priority = ?"
            params.append(priority)
            
        if q:
            query += " AND (ct.text LIKE ? OR a.name LIKE ?)"
            search_term = f"%{q}%"
            params.extend([search_term, search_term])
            
        if due_from:
            query += " AND ct.due_date >= ?"
            params.append(due_from)
            
        if due_to:
            query += " AND ct.due_date <= ?"
            params.append(due_to)
            
        query += " ORDER BY ct.created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        todos = []
        for row in rows:
            todos.append({
                "id": row[0],
                "athlete_id": row[1],
                "text": row[2],
                "priority": row[3],
                "status": row[4],
                "due_date": row[5],
                "created_by": row[6],
                "source_record_id": row[7],
                "created_at": row[8],
                "updated_at": row[9],
                "athlete_name": row[10]
            })
            
        return JSONResponse({
            "success": True,
            "todos": todos,
            "count": len(todos)
        })
        
    except Exception as e:
        logger.error(f"Error getting coach todos: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.post("/api/todos", response_class=JSONResponse)
async def create_coach_todo(
    athlete_id: Optional[int] = Form(None),
    text: str = Form(...),
    priority: str = Form("P2"),
    due: Optional[str] = Form(None),
    status: str = Form("backlog"),
    created_by: str = Form("coach"),
    source_record_id: Optional[int] = Form(None)
) -> JSONResponse:
    """Create a new coach todo"""
    try:
        cursor = conn.cursor()
        
        # Validate priority
        if priority not in ['P1', 'P2', 'P3']:
            return JSONResponse({
                "success": False,
                "error": "Invalid priority. Must be P1, P2, or P3"
            }, status_code=400)
            
        # Validate status
        if status not in ['backlog', 'doing', 'done']:
            return JSONResponse({
                "success": False,
                "error": "Invalid status. Must be backlog, doing, or done"
            }, status_code=400)
            
        # Validate created_by
        if created_by not in ['athlete', 'coach']:
            return JSONResponse({
                "success": False,
                "error": "Invalid created_by. Must be athlete or coach"
            }, status_code=400)
        
        cursor.execute("""
            INSERT INTO coach_todos (athlete_id, text, priority, status, due_date, created_by, source_record_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (athlete_id, text, priority, status, due, created_by, source_record_id))
        
        todo_id = cursor.lastrowid
        conn.commit()
        
        # Get the created todo with athlete name
        cursor.execute("""
            SELECT ct.*, a.name as athlete_name 
            FROM coach_todos ct 
            LEFT JOIN athletes a ON ct.athlete_id = a.id 
            WHERE ct.id = ?
        """, (todo_id,))
        
        row = cursor.fetchone()
        if row:
            todo = {
                "id": row[0],
                "athlete_id": row[1],
                "text": row[2],
                "priority": row[3],
                "status": row[4],
                "due_date": row[5],
                "created_by": row[6],
                "source_record_id": row[7],
                "created_at": row[8],
                "updated_at": row[9],
                "athlete_name": row[10]
            }
            
            return JSONResponse({
                "success": True,
                "todo": todo
            })
        
        return JSONResponse({
            "success": False,
            "error": "Failed to create todo"
        }, status_code=500)
        
    except Exception as e:
        logger.error(f"Error creating coach todo: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.put("/api/todos/{todo_id}", response_class=JSONResponse)
async def update_coach_todo(
    todo_id: int,
    text: Optional[str] = Form(None),
    priority: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    due: Optional[str] = Form(None),
    athlete_id: Optional[int] = Form(None)
) -> JSONResponse:
    """Update a coach todo"""
    try:
        cursor = conn.cursor()
        
        # Get current todo
        cursor.execute("SELECT * FROM coach_todos WHERE id = ?", (todo_id,))
        current = cursor.fetchone()
        
        if not current:
            return JSONResponse({
                "success": False,
                "error": "Todo not found"
            }, status_code=404)
        
        # Build update query with only provided fields
        update_fields = []
        params = []
        
        if text is not None:
            update_fields.append("text = ?")
            params.append(text)
            
        if priority is not None:
            if priority not in ['P1', 'P2', 'P3']:
                return JSONResponse({
                    "success": False,
                    "error": "Invalid priority. Must be P1, P2, or P3"
                }, status_code=400)
            update_fields.append("priority = ?")
            params.append(priority)
            
        if status is not None:
            if status not in ['backlog', 'doing', 'done']:
                return JSONResponse({
                    "success": False,
                    "error": "Invalid status. Must be backlog, doing, or done"
                }, status_code=400)
            update_fields.append("status = ?")
            params.append(status)
            
        if due is not None:
            update_fields.append("due_date = ?")
            params.append(due)
            
        if athlete_id is not None:
            update_fields.append("athlete_id = ?")
            params.append(athlete_id)
        
        if not update_fields:
            return JSONResponse({
                "success": False,
                "error": "No fields to update"
            }, status_code=400)
        
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(todo_id)
        
        query = f"UPDATE coach_todos SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
        
        # Get updated todo
        cursor.execute("""
            SELECT ct.*, a.name as athlete_name 
            FROM coach_todos ct 
            LEFT JOIN athletes a ON ct.athlete_id = a.id 
            WHERE ct.id = ?
        """, (todo_id,))
        
        row = cursor.fetchone()
        if row:
            todo = {
                "id": row[0],
                "athlete_id": row[1],
                "text": row[2],
                "priority": row[3],
                "status": row[4],
                "due_date": row[5],
                "created_by": row[6],
                "source_record_id": row[7],
                "created_at": row[8],
                "updated_at": row[9],
                "athlete_name": row[10]
            }
            
            return JSONResponse({
                "success": True,
                "todo": todo
            })
        
        return JSONResponse({
            "success": False,
            "error": "Failed to update todo"
        }, status_code=500)
        
    except Exception as e:
        logger.error(f"Error updating coach todo: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.delete("/api/todos/{todo_id}", response_class=JSONResponse)
async def delete_coach_todo(todo_id: int) -> JSONResponse:
    """Delete a coach todo"""
    try:
        cursor = conn.cursor()
        
        # Check if todo exists
        cursor.execute("SELECT id FROM coach_todos WHERE id = ?", (todo_id,))
        if not cursor.fetchone():
            return JSONResponse({
                "success": False,
                "error": "Todo not found"
            }, status_code=404)
        
        cursor.execute("DELETE FROM coach_todos WHERE id = ?", (todo_id,))
        conn.commit()
        
        return JSONResponse({
            "success": True,
            "message": "Todo deleted successfully"
        })
        
    except Exception as e:
        logger.error(f"Error deleting coach todo: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

# Enhanced highlights endpoints
@app.get("/api/athletes/{athlete_id}/highlights", response_class=JSONResponse)
async def get_athlete_highlights_enhanced(
    athlete_id: int,
    active_only: bool = Query(True, description="Only return active highlights"),
    manual_only: bool = Query(False, description="Only return manual highlights")
) -> JSONResponse:
    """Get highlights for a specific athlete with enhanced filtering"""
    try:
        cursor = conn.cursor()
        
        query = """
            SELECT 
                h.id,
                h.athlete_id,
                h.highlight_text,
                h.category,
                h.categories,
                h.score,
                h.source,
                h.status,
                h.reviewed_by,
                h.is_manual,
                h.is_active,
                h.created_at,
                h.updated_at,
                a.name as athlete_name,
                h.source_conversation_id
            FROM highlights h
            LEFT JOIN athletes a ON h.athlete_id = a.id
            WHERE h.athlete_id = ?
        """
        params = [athlete_id]
        
        if active_only:
            query += " AND h.is_active = 1"
            
        if manual_only:
            query += " AND h.is_manual = 1"
            
        query += " ORDER BY h.created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        highlights = []
        for row in rows:
            # Parse categories from JSON or CSV
            categories_str = row[4] if len(row) > 4 and row[4] else ""
            categories = []
            if categories_str:
                try:
                    # Ensure categories_str is a string
                    if isinstance(categories_str, str):
                        # Try to parse as JSON first
                        categories = json.loads(categories_str)
                    else:
                        # If it's not a string, use empty array
                        categories = []
                except:
                    # Fallback to CSV only if it's a string
                    if isinstance(categories_str, str):
                        categories = [c.strip() for c in categories_str.split(',') if c.strip()]
                    else:
                        categories = []
            
            # Safely access row elements with bounds checking
            row_length = len(row)
            
            highlights.append({
                "id": row[0] if row_length > 0 else None,
                "athlete_id": row[1] if row_length > 1 else None,
                "highlight_text": row[2] if row_length > 2 else "",
                "category": row[3] if row_length > 3 else "general",
                "categories": categories,
                "score": row[5] if row_length > 5 else 0.0,
                "source": row[6] if row_length > 6 else "manual",
                "status": row[7] if row_length > 7 else "accepted",
                "reviewed_by": row[8] if row_length > 8 else None,
                "is_manual": bool(row[9]) if row_length > 9 else False,
                "is_active": bool(row[10]) if row_length > 10 else True,
                "created_at": row[11] if row_length > 11 else None,
                "updated_at": row[12] if row_length > 12 else None,
                "athlete_name": row[13] if row_length > 13 else None,
                "source_conversation_id": row[14] if row_length > 14 else None
            })
            
        return JSONResponse({
            "success": True,
            "highlights": highlights,
            "count": len(highlights)
        })
        
    except Exception as e:
        logger.error(f"Error getting athlete highlights: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.post("/ai/highlights", response_class=JSONResponse)
async def generate_ai_highlights_with_tags(
    text: str = Form(...),
    athlete_id: Optional[int] = Form(None)
) -> JSONResponse:
    """Generate AI highlights with tags from text"""
    
    # Check if automatic GPT is enabled
    if not AUTO_GPT_ENABLED:
        return JSONResponse({
            "success": True,
            "highlights": [],
            "message": "Automatic GPT highlights generation is disabled"
        })
    
    try:
        # Get athlete context if available
        athlete_context = ""
        if athlete_id:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name, sport, level FROM athletes WHERE id = ?", (athlete_id,))
            athlete = cursor.fetchone()
            conn.close()
            
            if athlete:
                athlete_name, sport, level = athlete
                athlete_context = f"Atleta: {athlete_name} ({sport}, nivel {level})\n"
        
        prompt = f"""
        {athlete_context}
        Analiza el siguiente texto y genera 2-3 highlights relevantes con etiquetas apropiadas.
        
        Texto: {text}
        
        Genera highlights que capturen:
        - Progreso del atleta
        - Problemas o preocupaciones
        - Objetivos o planes
        - Aspectos técnicos importantes
        - Factores de riesgo (lesiones, fatiga, etc.)
        
        Etiquetas disponibles: Técnica, Nutrición, Psicología, Lesiones, Planificación, Objetivos, Problemas, Progreso, General
        
        Responde con un array JSON de objetos, cada uno con "text" y "tags":
        [
            {{"text": "Highlight 1", "tags": ["Técnica", "Progreso"]}},
            {{"text": "Highlight 2", "tags": ["Psicología"]}}
        ]
        """
        
        try:
            response_ai = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=400
            )
            
            highlights_text = response_ai.choices[0].message.content.strip()
            
            # Try to parse as JSON array
            try:
                highlights = json.loads(highlights_text)
                if not isinstance(highlights, list):
                    highlights = [{"text": highlights_text, "tags": ["General"]}]
            except:
                # If not valid JSON, create simple highlights
                highlights = [
                    {"text": f"Conversación relevante: {text[:100]}...", "tags": ["General"]}
                ]
            
            # Validate and clean highlights
            valid_highlights = []
            valid_tags = ["Técnica", "Nutrición", "Psicología", "Lesiones", "Planificación", "Objetivos", "Problemas", "Progreso", "General"]
            
            for highlight in highlights[:3]:  # Limit to 3 highlights
                if isinstance(highlight, dict) and "text" in highlight:
                    # Clean and validate tags
                    tags = highlight.get("tags", [])
                    if isinstance(tags, list):
                        valid_tags_for_highlight = [tag for tag in tags if tag in valid_tags]
                        if not valid_tags_for_highlight:
                            valid_tags_for_highlight = ["General"]
                    else:
                        valid_tags_for_highlight = ["General"]
                    
                    valid_highlights.append({
                        "text": highlight["text"].strip(),
                        "tags": valid_tags_for_highlight
                    })
            
            return JSONResponse({
                "success": True,
                "highlights": valid_highlights,
                "count": len(valid_highlights)
            })
            
        except Exception as api_error:
            logger.error(f"OpenAI API error: {api_error}")
            return JSONResponse({
                "success": False,
                "error": f"Error generating highlights: {str(api_error)}"
            }, status_code=500)
            
    except Exception as e:
        logger.error(f"Error generating AI highlights: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.get("/api/athletes/{athlete_id}/risk", response_class=JSONResponse)
async def get_athlete_risk(athlete_id: int) -> JSONResponse:
    """Get risk assessment for an athlete using GPT-4o-mini analysis."""
    try:
        # Check if automatic GPT is enabled
        if not AUTO_GPT_ENABLED:
            # Return simple risk assessment without GPT
            risk_data = get_athlete_risk_factors(athlete_id)
            
            if not risk_data:
                return JSONResponse({
                    "status": "error",
                    "message": "Athlete not found"
                }, status_code=404)
            
            return JSONResponse({
                "athlete_id": risk_data['athlete_id'],
                "athlete_name": risk_data['athlete_name'],
                "score": risk_data['score'],
                "level": risk_data['level'],
                "color": risk_data['color'],
                "factors": risk_data['factors'],
                "evidence": risk_data.get('evidence', []),
                "raw_score": risk_data.get('raw_score', 0),
                "smoothed_score": risk_data.get('smoothed_score', 0),
                "last_contact": risk_data.get('last_contact'),
                "days_since_contact": risk_data.get('days_since_contact', 0),
                "overdue_count": risk_data.get('overdue_count', 0),
                "gpt_analysis": {}
            })
        
        # Calculate risk factors using GPT analysis
        risk_data = await get_athlete_risk_factors_gpt(athlete_id)
        
        if not risk_data:
            return JSONResponse({
                "status": "error",
                "message": "Athlete not found"
            }, status_code=404)
        
        # Save to history table
        try:
            with conn:
                conn.execute("""
                    INSERT INTO athlete_risk_history 
                    (athlete_id, score, level, factors_json) 
                    VALUES (?, ?, ?, ?)
                """, (
                    athlete_id,
                    risk_data['score'],
                    risk_data['level'],
                    json.dumps(risk_data['factors'])
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving risk history: {e}")
        
        # Return the risk assessment
        return JSONResponse({
            "athlete_id": risk_data['athlete_id'],
            "athlete_name": risk_data['athlete_name'],
            "score": risk_data['score'],
            "level": risk_data['level'],
            "color": risk_data['color'],
            "factors": risk_data['factors'],
            "evidence": risk_data['evidence'],
            "raw_score": risk_data['raw_score'],
            "smoothed_score": risk_data['smoothed_score'],
            "last_contact": risk_data['last_contact'],
            "days_since_contact": risk_data['days_since_contact'],
            "overdue_count": risk_data['overdue_count'],
            "gpt_analysis": risk_data.get('gpt_analysis', {})
        })
        
    except Exception as e:
        logger.error(f"Error calculating risk for athlete {athlete_id}: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Error calculating risk: {str(e)}"
        }, status_code=500)

def init_risk_history_table():
    """Initialize the athlete risk history table."""
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS athlete_risk_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    athlete_id INTEGER NOT NULL,
                    score REAL NOT NULL,
                    level TEXT NOT NULL,
                    factors_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (athlete_id) REFERENCES athletes (id)
                )
            """)
            conn.commit()
            logger.info("Risk history table initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing risk history table: {e}")

# Risk Radar Configuration
RISK_WEIGHTS = {
    'inactivity': 0.30,
    'overdue': 0.20, 
    'neg_high': 0.25,
    'sentiment': 0.15,
    'pain': 0.10
}

RISK_KEYWORDS = {
    'sleep': ["sueño", "dormir", "cansado", "fatiga", "descanso", "insomnio", "despertar", "no duermo", "mal sueño"],
    'pain': ["dolor", "lesión", "molestia", "herida", "inflamación", "contractura", "tirón", "duele", "inflamado"],
    'negative': ["no puedo", "imposible", "difícil", "problema", "mal", "terrible", "horrible", "frustrado", "estresado", "ansioso", "deprimido"],
    'psychology': ["psicología", "mental", "motivación", "ánimo", "estado de ánimo", "depresión", "ansiedad"]
}

def normalize_inactivity(days):
    """Normalize inactivity days using exponential decay."""
    x = max(0, days - 3)
    return 1 - math.exp(-x / 3)

async def get_athlete_risk_factors_gpt(athlete_id: int) -> dict:
    """Calculate risk factors for an athlete using GPT-4o-mini analysis."""
    try:
        with conn:
            # Get athlete data
            cursor = conn.execute(
                "SELECT id, name, created_at FROM athletes WHERE id = ?",
                (athlete_id,)
            )
            athlete = cursor.fetchone()
            
            if not athlete:
                return None
            
            # Get recent conversations (last 30 days)
            cursor.execute("""
                SELECT 
                    m.transcription,
                    m.final_response,
                    r.timestamp,
                    r.category,
                    r.source
                FROM records r
                WHERE r.athlete_id = ?
                AND r.timestamp >= datetime('now', '-30 days')
                ORDER BY r.timestamp DESC
                LIMIT 10
            """, (athlete_id,))
            
            conversations = cursor.fetchall()
            
            # Get overdue todos
            cursor.execute("""
                SELECT 
                    t.id,
                    t.text,
                    t.due_date,
                    t.status,
                    t.created_at
                FROM coach_todos t
                WHERE t.athlete_id = ?
                AND t.status != 'done'
                AND (t.due_date IS NULL OR t.due_date < date('now'))
                ORDER BY t.due_date ASC
            """, (athlete_id,))
            
            overdue_todos = cursor.fetchall()
            
            # Get recent highlights (last 14 days)
            cursor.execute("""
                SELECT 
                    h.highlight_text,
                    h.categories,
                    h.created_at
                FROM highlights h
                WHERE h.athlete_id = ?
                AND h.is_active = 1
                AND h.created_at >= datetime('now', '-14 days')
                ORDER BY h.created_at DESC
            """, (athlete_id,))
            
            recent_highlights = cursor.fetchall()
            
            # Calculate S1: Inactivity (same as before)
            last_contact = None
            if conversations:
                last_contact = conversations[0][2]
            
            days_since_contact = 0
            if last_contact:
                from datetime import datetime
                last_contact_date = datetime.fromisoformat(last_contact.replace('Z', '+00:00'))
                now = datetime.now()
                days_since_contact = (now - last_contact_date).days
            else:
                days_since_contact = 30
            
            s1 = normalize_inactivity(days_since_contact)
            
            # Calculate S2: Overdue todos (same as before)
            overdue_count = len(overdue_todos)
            very_overdue_count = 0
            
            for todo in overdue_todos:
                if todo[2]:  # due_date
                    try:
                        due_date = datetime.fromisoformat(todo[2])
                        days_overdue = (datetime.now() - due_date).days
                        if days_overdue > 7:
                            very_overdue_count += 1
                    except (ValueError, TypeError):
                        continue
            
            s2 = min(1, (0.5 * overdue_count + 1.0 * very_overdue_count) / 5)
            
            # Calculate S3-S5 using GPT analysis
            gpt_analyzer = GPTRiskAnalyzer(openai_client)
            
            # Analyze conversations with GPT
            conversation_data = [(conv[0] or "", conv[1] or "") for conv in conversations[:7]]
            gpt_results = await gpt_analyzer.analyze_conversation_batch(conversation_data)
            
            # Calculate sentiment moving average (S4)
            sentiment_scores = gpt_results['sentiment']
            sentiment_mm7 = sum(sentiment_scores) / max(1, len(sentiment_scores))
            s4 = max(0, min(1, (0 - sentiment_mm7) / 1.0))  # Negative sentiment increases risk
            
            # Calculate pain/injury mentions (S5)
            pain_scores = gpt_results['pain_injury']
            pain_matches = sum(1 for score in pain_scores if score > 0.3)
            s5 = min(1, pain_matches / 3)
            
            # Analyze highlights with GPT
            highlight_texts = [h[0] for h in recent_highlights]
            highlight_analysis = await gpt_analyzer.analyze_highlights(highlight_texts)
            
            # Calculate negative highlights ratio (S3)
            s3 = highlight_analysis['negative_ratio']
            
            # Calculate raw score
            raw_score = 100 * (
                RISK_WEIGHTS['inactivity'] * s1 +
                RISK_WEIGHTS['overdue'] * s2 +
                RISK_WEIGHTS['neg_high'] * s3 +
                RISK_WEIGHTS['sentiment'] * s4 +
                RISK_WEIGHTS['pain'] * s5
            )
            
            # Get previous score for smoothing
            cursor.execute("""
                SELECT score FROM athlete_risk_history 
                WHERE athlete_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (athlete_id,))
            
            prev_score_result = cursor.fetchone()
            prev_score = prev_score_result[0] if prev_score_result else raw_score
            
            # Apply exponential smoothing
            alpha = 0.5
            final_score = alpha * raw_score + (1 - alpha) * prev_score
            
            # Determine risk level
            if final_score >= 65:
                level = "rojo"
                color = "danger"
            elif final_score >= 35:
                level = "ámbar"
                color = "warning"
            else:
                level = "verde"
                color = "success"
            
            # Build evidence list with GPT insights
            evidence = []
            
            if days_since_contact > 0:
                evidence.append(f"Último contacto: {last_contact or 'Nunca'} ({days_since_contact} días)")
            
            if overdue_count > 0:
                todo_list = ", ".join([f"'{todo[1]}'" for todo in overdue_todos[:3]])
                evidence.append(f"{overdue_count} vencidos: {todo_list}")
            
            if s3 > 0:
                evidence.append(f"{s3:.1%} highlights negativos (GPT analysis)")
            
            if sentiment_mm7 < 0:
                evidence.append(f"Sentimiento GPT mm7 = {sentiment_mm7:.2f}")
            
            if pain_matches > 0:
                evidence.append(f"Dolor/lesión detectado por GPT ({pain_matches} veces en 7d)")
            
            # Additional GPT insights
            if highlight_analysis['pain_injury_ratio'] > 0:
                evidence.append(f"GPT detectó {highlight_analysis['pain_injury_ratio']:.1%} highlights con dolor/lesión")
            
            if highlight_analysis['sleep_fatigue_ratio'] > 0:
                evidence.append(f"GPT detectó {highlight_analysis['sleep_fatigue_ratio']:.1%} highlights con problemas de sueño")
            
            # Build factors JSON with GPT analysis
            factors = {
                'inactivity': {
                    'value': s1,
                    'weight': RISK_WEIGHTS['inactivity'],
                    'contribution': s1 * RISK_WEIGHTS['inactivity'] * 100,
                    'evidence': evidence[0] if evidence else "Sin evidencia"
                },
                'overdue': {
                    'value': s2,
                    'weight': RISK_WEIGHTS['overdue'],
                    'contribution': s2 * RISK_WEIGHTS['overdue'] * 100,
                    'evidence': evidence[1] if len(evidence) > 1 else "Sin evidencia"
                },
                'neg_high': {
                    'value': s3,
                    'weight': RISK_WEIGHTS['neg_high'],
                    'contribution': s3 * RISK_WEIGHTS['neg_high'] * 100,
                    'evidence': evidence[2] if len(evidence) > 2 else "Sin evidencia"
                },
                'sentiment': {
                    'value': s4,
                    'weight': RISK_WEIGHTS['sentiment'],
                    'contribution': s4 * RISK_WEIGHTS['sentiment'] * 100,
                    'evidence': evidence[3] if len(evidence) > 3 else "Sin evidencia"
                },
                'pain': {
                    'value': s5,
                    'weight': RISK_WEIGHTS['pain'],
                    'contribution': s5 * RISK_WEIGHTS['pain'] * 100,
                    'evidence': evidence[4] if len(evidence) > 4 else "Sin evidencia"
                }
            }
            
            return {
                'athlete_id': athlete_id,
                'athlete_name': athlete[1],
                'score': round(final_score, 1),
                'level': level,
                'color': color,
                'factors': factors,
                'evidence': evidence,
                'raw_score': round(raw_score, 1),
                'smoothed_score': round(final_score, 1),
                'last_contact': last_contact,
                'days_since_contact': days_since_contact,
                'overdue_count': overdue_count,
                'gpt_analysis': {
                    'sentiment_mm7': round(sentiment_mm7, 2),
                    'pain_matches': pain_matches,
                    'highlight_analysis': highlight_analysis
                }
            }
            
    except Exception as e:
        logger.error(f"Error calculating GPT risk factors for athlete {athlete_id}: {e}")
        return None

@app.post("/api/risk/recompute", response_class=JSONResponse)
async def recompute_all_risks() -> JSONResponse:
    """Recalculate risk scores for all athletes and save to history."""
    try:
        with conn:
            # Get all athletes
            cursor = conn.execute("SELECT id, name FROM athletes")
            athletes = cursor.fetchall()
            
            results = []
            total_processed = 0
            
            for athlete in athletes:
                athlete_id = athlete[0]
                athlete_name = athlete[1]
                
                try:
                    # Calculate risk factors
                    risk_data = get_athlete_risk_factors(athlete_id)
                    
                    if risk_data:
                        # Save to history
                        conn.execute("""
                            INSERT INTO athlete_risk_history 
                            (athlete_id, score, level, factors_json) 
                            VALUES (?, ?, ?, ?)
                        """, (
                            athlete_id,
                            risk_data['score'],
                            risk_data['level'],
                            json.dumps(risk_data['factors'])
                        ))
                        
                        results.append({
                            'athlete_id': athlete_id,
                            'athlete_name': athlete_name,
                            'score': risk_data['score'],
                            'level': risk_data['level'],
                            'color': risk_data['color']
                        })
                        
                        total_processed += 1
                        
                except Exception as e:
                    logger.error(f"Error processing athlete {athlete_id}: {e}")
                    results.append({
                        'athlete_id': athlete_id,
                        'athlete_name': athlete_name,
                        'error': str(e)
                    })
            
            conn.commit()
            
            return JSONResponse({
                "status": "success",
                "message": f"Processed {total_processed} athletes",
                "total_athletes": len(athletes),
                "processed": total_processed,
                "results": results
            })
            
    except Exception as e:
        logger.error(f"Error in batch risk recalculation: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Error in batch recalculation: {str(e)}"
        }, status_code=500)

# Initialize tables
init_coach_todos_table()
init_risk_history_table()

def get_athlete_risk_factors(athlete_id: int) -> dict:
    """Calculate risk factors for an athlete using the improved algorithm."""
    try:
        with conn:
            # Get athlete data
            cursor = conn.execute(
                "SELECT id, name, created_at FROM athletes WHERE id = ?",
                (athlete_id,)
            )
            athlete = cursor.fetchone()
            
            if not athlete:
                return None
            
            # Get recent conversations (last 30 days)
            cursor.execute("""
                SELECT 
                    m.transcription,
                    m.final_response,
                    r.timestamp,
                    r.category,
                    r.source
                FROM records r
                WHERE r.athlete_id = ?
                AND r.timestamp >= datetime('now', '-30 days')
                ORDER BY r.timestamp DESC
                LIMIT 10
            """, (athlete_id,))
            
            conversations = cursor.fetchall()
            
            # Get overdue todos
            cursor.execute("""
                SELECT 
                    t.id,
                    t.text,
                    t.due_date,
                    t.status,
                    t.created_at
                FROM coach_todos t
                WHERE t.athlete_id = ?
                AND t.status != 'done'
                AND (t.due_date IS NULL OR t.due_date < date('now'))
                ORDER BY t.due_date ASC
            """, (athlete_id,))
            
            overdue_todos = cursor.fetchall()
            
            # Get recent highlights (last 14 days)
            cursor.execute("""
                SELECT 
                    h.highlight_text,
                    h.categories,
                    h.created_at
                FROM highlights h
                WHERE h.athlete_id = ?
                AND h.is_active = 1
                AND h.created_at >= datetime('now', '-14 days')
                ORDER BY h.created_at DESC
            """, (athlete_id,))
            
            recent_highlights = cursor.fetchall()
            
            # Calculate S1: Inactivity
            last_contact = None
            if conversations:
                last_contact = conversations[0][2]  # timestamp of most recent conversation
            
            days_since_contact = 0
            if last_contact:
                from datetime import datetime
                last_contact_date = datetime.fromisoformat(last_contact.replace('Z', '+00:00'))
                now = datetime.now()
                days_since_contact = (now - last_contact_date).days
            else:
                days_since_contact = 30  # Default if no contact
            
            s1 = normalize_inactivity(days_since_contact)
            
            # Calculate S2: Overdue todos
            overdue_count = len(overdue_todos)
            very_overdue_count = 0
            
            for todo in overdue_todos:
                if todo[2]:  # due_date
                    try:
                        due_date = datetime.fromisoformat(todo[2])
                        days_overdue = (datetime.now() - due_date).days
                        if days_overdue > 7:
                            very_overdue_count += 1
                    except (ValueError, TypeError):
                        # Skip if date format is invalid
                        continue
            
            s2 = min(1, (0.5 * overdue_count + 1.0 * very_overdue_count) / 5)
            
            # Calculate S3: Negative highlights ratio
            negative_highlights = 0
            total_highlights = len(recent_highlights)
            
            negative_tags = ['lesión', 'dolor', 'problema', 'fatiga', 'psicología_negativa']
            
            for highlight in recent_highlights:
                highlight_text = highlight[0].lower()
                categories = highlight[1] or ""
                
                # Check for negative keywords in text
                for keyword in RISK_KEYWORDS['pain'] + RISK_KEYWORDS['negative'] + RISK_KEYWORDS['psychology']:
                    if keyword in highlight_text:
                        negative_highlights += 1
                        break
                
                # Check for negative tags
                for tag in negative_tags:
                    if tag in categories.lower():
                        negative_highlights += 1
                        break
            
            s3 = negative_highlights / max(1, total_highlights)
            
            # Calculate S4: Sentiment (simple moving average 7 days)
            sentiment_scores = []
            recent_conversations = conversations[:7]  # Last 7 conversations
            
            for conv in recent_conversations:
                transcription = (conv[0] or "").lower()
                response = (conv[1] or "").lower()
                
                # Simple sentiment analysis
                positive_words = ["bien", "genial", "excelente", "perfecto", "mejor", "progreso", "feliz", "contento"]
                negative_words = RISK_KEYWORDS['negative']
                
                positive_count = sum(transcription.count(word) + response.count(word) for word in positive_words)
                negative_count = sum(transcription.count(word) + response.count(word) for word in negative_words)
                
                if positive_count > negative_count:
                    sentiment_scores.append(1)
                elif negative_count > positive_count:
                    sentiment_scores.append(-1)
                else:
                    sentiment_scores.append(0)
            
            sentiment_mm7 = sum(sentiment_scores) / max(1, len(sentiment_scores))
            s4 = max(0, min(1, (0 - sentiment_mm7) / 1.0))  # Negative sentiment increases risk
            
            # Calculate S5: Pain/injury keywords in last 7 days
            pain_matches = 0
            recent_text = ""
            
            for conv in recent_conversations:
                recent_text += " " + (conv[0] or "") + " " + (conv[1] or "")
            
            recent_text = recent_text.lower()
            
            for keyword in RISK_KEYWORDS['pain']:
                pain_matches += recent_text.count(keyword)
            
            s5 = min(1, pain_matches / 3)
            
            # Calculate raw score
            raw_score = 100 * (
                RISK_WEIGHTS['inactivity'] * s1 +
                RISK_WEIGHTS['overdue'] * s2 +
                RISK_WEIGHTS['neg_high'] * s3 +
                RISK_WEIGHTS['sentiment'] * s4 +
                RISK_WEIGHTS['pain'] * s5
            )
            
            # Get previous score for smoothing
            cursor.execute("""
                SELECT score FROM athlete_risk_history 
                WHERE athlete_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (athlete_id,))
            
            prev_score_result = cursor.fetchone()
            prev_score = prev_score_result[0] if prev_score_result else raw_score
            
            # Apply exponential smoothing
            alpha = 0.5
            final_score = alpha * raw_score + (1 - alpha) * prev_score
            
            # Determine risk level
            if final_score >= 65:
                level = "rojo"
                color = "danger"
            elif final_score >= 35:
                level = "ámbar"
                color = "warning"
            else:
                level = "verde"
                color = "success"
            
            # Build evidence list
            evidence = []
            
            if days_since_contact > 0:
                evidence.append(f"Último contacto: {last_contact or 'Nunca'} ({days_since_contact} días)")
            
            if overdue_count > 0:
                todo_list = ", ".join([f"'{todo[1]}'" for todo in overdue_todos[:3]])
                evidence.append(f"{overdue_count} vencidos: {todo_list}")
            
            if negative_highlights > 0:
                evidence.append(f"{negative_highlights}/{total_highlights} highlights negativos")
            
            if sentiment_mm7 < 0:
                evidence.append(f"Sentimiento mm7 = {sentiment_mm7:.2f}")
            
            if pain_matches > 0:
                evidence.append(f"Palabras clave dolor/lesión ({pain_matches} veces en 7d)")
            
            # Build factors JSON
            factors = {
                'inactivity': {
                    'value': s1,
                    'weight': RISK_WEIGHTS['inactivity'],
                    'contribution': s1 * RISK_WEIGHTS['inactivity'] * 100,
                    'evidence': evidence[0] if evidence else "Sin evidencia"
                },
                'overdue': {
                    'value': s2,
                    'weight': RISK_WEIGHTS['overdue'],
                    'contribution': s2 * RISK_WEIGHTS['overdue'] * 100,
                    'evidence': evidence[1] if len(evidence) > 1 else "Sin evidencia"
                },
                'neg_high': {
                    'value': s3,
                    'weight': RISK_WEIGHTS['neg_high'],
                    'contribution': s3 * RISK_WEIGHTS['neg_high'] * 100,
                    'evidence': evidence[2] if len(evidence) > 2 else "Sin evidencia"
                },
                'sentiment': {
                    'value': s4,
                    'weight': RISK_WEIGHTS['sentiment'],
                    'contribution': s4 * RISK_WEIGHTS['sentiment'] * 100,
                    'evidence': evidence[3] if len(evidence) > 3 else "Sin evidencia"
                },
                'pain': {
                    'value': s5,
                    'weight': RISK_WEIGHTS['pain'],
                    'contribution': s5 * RISK_WEIGHTS['pain'] * 100,
                    'evidence': evidence[4] if len(evidence) > 4 else "Sin evidencia"
                }
            }
            
            return {
                'athlete_id': athlete_id,
                'athlete_name': athlete[1],
                'score': round(final_score, 1),
                'level': level,
                'color': color,
                'factors': factors,
                'evidence': evidence,
                'raw_score': round(raw_score, 1),
                'smoothed_score': round(final_score, 1),
                'last_contact': last_contact,
                'days_since_contact': days_since_contact,
                'overdue_count': overdue_count,
                'negative_highlights': negative_highlights,
                'total_highlights': total_highlights,
                'sentiment_mm7': round(sentiment_mm7, 2),
                'pain_matches': pain_matches
            }
            
    except Exception as e:
        logger.error(f"Error calculating risk factors for athlete {athlete_id}: {e}")
        return None

# Outreach endpoints
@app.post("/api/outreach/generate", response_class=JSONResponse)
async def generate_outreach_message(body: dict) -> JSONResponse:
    """
    Generate outreach messages using GPT-4o-mini based on athlete context
    """
    try:
        # Validate required fields
        if not body.get("athlete") or not body.get("risk"):
            raise HTTPException(status_code=400, detail="Missing required fields: athlete and risk")
        
        # Generate outreach messages
        result = generate_outreach(body)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Error generating outreach: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/outreach/generate/{athlete_id}", response_class=JSONResponse)
async def generate_outreach_for_athlete(athlete_id: int, body: dict = {}) -> JSONResponse:
    """
    Generate outreach messages for a specific athlete using their context
    """
    try:
        # Get athlete data
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, email, phone, sport, level
            FROM athletes 
            WHERE id = ?
        """, (athlete_id,))
        
        athlete_data = cursor.fetchone()
        if not athlete_data:
            raise HTTPException(status_code=404, detail="Athlete not found")
        
        # Get athlete risk data
        risk_data = get_athlete_risk_factors(athlete_id)
        if not risk_data:
            risk_data = {
                "score": 50,
                "level": "yellow",
                "factors": []
            }
        
        # Get recent highlights
        highlights = get_athlete_highlights(athlete_id, active_only=True)
        
        # Get recent conversation excerpt
        cursor.execute("""
            SELECT transcription, final_response 
            FROM records 
            WHERE athlete_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        """, (athlete_id,))
        
        conversation = cursor.fetchone()
        conversation_excerpt = ""
        if conversation:
            conversation_excerpt = f"{conversation[0]} {conversation[1]}"[:800]
        
        # Build payload
        payload = {
            "athlete": {
                "id": athlete_data[0],
                "first_name": athlete_data[1].split()[0] if athlete_data[1] else "Atleta",
                "locale": "es-ES",  # Default to Spanish
                "sport": athlete_data[4] or "Running",
                "goal": "Mejorar rendimiento"
            },
            "risk": {
                "score": risk_data.get("score", 50),
                "level": risk_data.get("level", "yellow"),
                "factors": risk_data.get("factors", {})
            },
            "highlights_recent": [
                {"category": h.get("category", "general"), "text": h.get("text", "")}
                for h in highlights[:5]
            ],
            "conversation_excerpt": conversation_excerpt,
            "channel_pref": body.get("channel_pref", ["whatsapp", "email"]),
            "coach": {
                "name": "Ramon",
                "calendar_url": "https://calendly.com/ramon"
            }
        }
        
        # Generate outreach
        result = generate_outreach(payload)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Error generating outreach for athlete {athlete_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== ENDPOINTS DE TRANSCRIPCIÓN MEJORADOS =====

@app.get("/transcription/status")
async def transcription_status() -> JSONResponse:
    """
    Obtener el estado del sistema de transcripción.
    Útil para diagnóstico y verificación de configuración.
    """
    try:
        status = transcription_service.get_system_status()
        format_info = transcription_service.get_supported_formats()
        
        return JSONResponse({
            "status": "success",
            "system_status": status,
            "supported_formats": {
                "direct_formats": format_info['direct_formats'],
                "conversion_formats": format_info['conversion_formats']
            },
            "configuration": {
                "openai_configured": format_info['openai_configured'],
                "ffmpeg_available": format_info['ffmpeg_available']
            },
            "recommendations": status['recommendations']
        })
        
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.get("/transcription/formats")
async def supported_formats() -> JSONResponse:
    """
    Obtener información detallada sobre formatos de audio soportados.
    """
    try:
        format_info = transcription_service.get_supported_formats()
        
        # Información detallada sobre cada formato
        format_details = {
            "whatsapp_formats": {
                "common": [".ogg", ".opus"],
                "description": "WhatsApp usa principalmente OGG con codec OPUS",
                "requires_ffmpeg": True
            },
            "telegram_formats": {
                "common": [".ogg", ".m4a", ".oga"],
                "description": "Telegram usa OGG, M4A y otros formatos",
                "requires_ffmpeg": True
            },
            "direct_formats": {
                "formats": format_info['direct_formats'],
                "description": "Formatos soportados directamente por OpenAI Whisper",
                "requires_ffmpeg": False
            },
            "conversion_formats": {
                "formats": format_info['conversion_formats'],
                "description": "Formatos que requieren conversión con FFmpeg",
                "requires_ffmpeg": True,
                "available": format_info['ffmpeg_available']
            }
        }
        
        return JSONResponse({
            "status": "success",
            "format_details": format_details,
            "system_capabilities": {
                "openai_whisper": format_info['openai_configured'],
                "ffmpeg_conversion": format_info['ffmpeg_available'],
                "full_support": format_info['openai_configured'] and format_info['ffmpeg_available']
            }
        })
        
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
