import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """Eres un asistente de coaching deportivo que escribe mensajes
breves, empáticos y accionables. SIEMPRE escribe en el idioma objetivo.
No inventes datos. Mantén tono profesional cercano, frases cortas, y un CTA claro.
Devuelve SIEMPRE un JSON con el esquema:
{
  "language": "<BCP47>",
  "email": {"subject":"...", "text":"...", "html":"..."},
  "messaging": {
    "whatsapp_short":"...", "whatsapp_long":"...", "telegram_short":"..."
  },
  "notes": {"tone":"...", "cta":"...", "reasoning":["..."]}
}"""

def detect_target_language(athlete_locale: str, conversation_excerpt: str) -> str:
    """Detect target language from athlete profile or conversation"""
    if athlete_locale: 
        return athlete_locale
    # Fallback to Spanish if no locale provided
    return "es-ES"

def _cache_key(payload: dict) -> str:
    """Generate cache key from payload"""
    base = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(base.encode("utf-8")).hexdigest()

# Simple in-memory cache (replace with Redis in production)
CACHE = {}

def generate_outreach(payload: dict) -> dict:
    """
    Generate outreach messages using GPT-4o-mini
    
    Args:
        payload: Dictionary containing athlete info, risk data, highlights, etc.
        
    Returns:
        Dictionary with generated messages for different channels
    """
    target_lang = detect_target_language(
        payload.get("athlete", {}).get("locale"),
        payload.get("conversation_excerpt", "")
    )

    # Create cache key
    key = _cache_key({**payload, "target_lang": target_lang})
    if key in CACHE: 
        return CACHE[key]

    # Prepare user prompt with context
    user_prompt = {
        "athlete": payload["athlete"],
        "risk": payload["risk"],
        "highlights_recent": payload.get("highlights_recent", [])[:5],
        "conversation_excerpt": payload.get("conversation_excerpt", "")[:800],
        "channel_pref": payload.get("channel_pref", ["email"]),
        "coach": payload.get("coach", {}),
        "format_requirements": {
            "language": target_lang,
            "email": {
                "subject_max_chars": 78,
                "body_words": [120, 180],
                "tone": "empático, claro, específico, sin plantillas rígidas"
            },
            "messaging": {
                "short_words": [35, 60],
                "long_words": [70, 110],
                "include_quick_reply": True,
            }
        }
    }

    # Generate with GPT-4o-mini
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.6,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)}
            ],
        )

        data = json.loads(resp.choices[0].message.content)

        # Post-process: insert calendar links if available
        cal = payload.get("coach", {}).get("calendar_url")
        if cal and data.get("email", {}).get("html"):
            data["email"]["html"] = data["email"]["html"].replace("{{calendar}}", cal)
            data["email"]["text"] = data["email"]["text"].replace("{{calendar}}", cal)

        # Anti-abuse: trim and sanitize lengths
        for k in ["whatsapp_short", "whatsapp_long", "telegram_short"]:
            if data["messaging"].get(k, ""):
                data["messaging"][k] = data["messaging"][k].strip()[:900]

        # Cache the result
        CACHE[key] = data
        return data

    except Exception as e:
        # Fallback response in case of API error
        return {
            "language": target_lang,
            "email": {
                "subject": "¿Cómo te sientes esta semana?",
                "text": "Hola, quería saber cómo va todo con tu entrenamiento. ¿Hay algo en lo que pueda ayudarte?",
                "html": "<p>Hola, quería saber cómo va todo con tu entrenamiento. ¿Hay algo en lo que pueda ayudarte?</p>"
            },
            "messaging": {
                "whatsapp_short": "Hola 👋 ¿Cómo va todo con el entrenamiento?",
                "whatsapp_long": "Hola 👋 ¿Cómo va todo con el entrenamiento? ¿Hay algo en lo que pueda ayudarte?",
                "telegram_short": "Hola 👋 ¿Cómo va todo con el entrenamiento?"
            },
            "notes": {
                "tone": "empático, claro",
                "cta": "Responder o agendar 15'",
                "reasoning": ["Mensaje de seguimiento"]
            }
        }

def get_athlete_context(athlete_id: int) -> dict:
    """
    Get athlete context for outreach generation
    
    Args:
        athlete_id: ID of the athlete
        
    Returns:
        Dictionary with athlete context
    """
    # This would typically query your database
    # For now, return a sample structure
    return {
        "athlete": {
            "id": athlete_id,
            "first_name": "Atleta",
            "locale": "es-ES",
            "sport": "Running",
            "goal": "Mejorar resistencia"
        },
        "risk": {
            "score": 50,
            "level": "yellow",
            "factors": []
        },
        "highlights_recent": [],
        "conversation_excerpt": "",
        "channel_pref": ["whatsapp", "email"],
        "coach": {
            "name": "Ramon",
            "calendar_url": "https://calendly.com/ramon"
        }
    }