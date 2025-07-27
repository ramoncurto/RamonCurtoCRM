import logging
import os
import json
import random
import re
import html

from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    filters,
    MessageHandler,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

import whisper
from pydub import AudioSegment
from langdetect import detect, DetectorFactory
from openai import AsyncOpenAI

# =============================================================================
#                           CONFIGURACIONES INICIALES
# =============================================================================

load_dotenv(".env")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Para reproducibilidad de langdetect
DetectorFactory.seed = 0

# Directorio temporal para guardar audios
TEMP_AUDIO_DIR = Path("./temp_audio_files")
TEMP_AUDIO_DIR.mkdir(exist_ok=True)

# =============================================================================
#             LEER ARCHIVO DE EJEMPLOS (few-shot) PARA "RAMON"
# =============================================================================

EJEMPLES_FILE = Path("exemples_correus.json")
if not EJEMPLES_FILE.exists():
    raise FileNotFoundError(f"No se encontró el archivo {EJEMPLES_FILE} con los ejemplos.")

with open(EJEMPLES_FILE, "r", encoding="utf-8") as f:
    ejemplos_data = json.load(f)

# Limitar los ejemplos para evitar problemas de longitud
MAX_EXAMPLES = 3
training_examples = ejemplos_data[:MAX_EXAMPLES]

# =============================================================================
#                     CONFIGURACIÓN DE LA API DE OPENAI
# =============================================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Falta la variable de entorno OPENAI_API_KEY.")

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# =============================================================================
#                           ALMACÉN DE USUARIOS
# =============================================================================

USER_AUDIO_FILES: Dict[int, List[str]] = {}

# =============================================================================
#             CREAR LA LISTA DE MENSAJES (FEW-SHOT) DESDE EL JSON
# =============================================================================

def build_few_shot_messages(few_shot_data: List[dict]) -> List[Dict[str, str]]:
    """
    Convierte la estructura del JSON (cada item con "messages") 
    a una lista de dicts con 'role' y 'content' para usarlos como ejemplos.
    """
    final_messages = []
    for item in few_shot_data:
        messages_list = item.get("messages", [])
        for msg in messages_list:
            if "role" in msg and "content" in msg:
                final_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
    return final_messages

FEW_SHOT_MESSAGES = build_few_shot_messages(training_examples)

# =============================================================================
#                              LISTA DE EMOJIS
# =============================================================================

EMOJI_ARRAY = ["😀", "👌", "🔥", "🚀", "😘", "💪", "👍", "😊", "🤗", "❤️"]

# =============================================================================
#                             CLASES DE SERVICIO
# =============================================================================

class AudioService:
    """Maneja la concatenación y transcripción de audios con pydub y Whisper."""

    @staticmethod
    def concatenate_audio_files(audio_paths: List[str], output_path: Path) -> None:
        logging.info("Iniciando concatenación de archivos de audio.")
        combined_audio = None
        for file_name in audio_paths:
            audio = AudioSegment.from_file(file_name)
            combined_audio = audio if combined_audio is None else combined_audio + audio

        combined_audio.export(output_path, format="mp3")
        logging.info(f"Audio combinado guardado en: {output_path}")

    @staticmethod
    def transcribe_audio(file_path: Path, model_size: str = "small") -> str:
        logging.info("Cargando modelo Whisper para transcripción.")
        model = whisper.load_model(model_size)
        result = model.transcribe(str(file_path))
        transcript = result.get("text", "")
        logging.info("Transcripción finalizada.")
        return transcript


class TextService:
    """
    Servicio para procesar texto y generar la mejor respuesta empática:
      1. Detección de idioma
      2. Detección de emoción (sentimiento) usando un sub-prompt
      3. Resumen del texto
      4. Respuesta final con técnicas psicológicas y hasta 3 emojis
    """

    def __init__(self, openai_client: AsyncOpenAI) -> None:
        self.openai_client = openai_client

    async def detect_language(self, text: str) -> str:
        """Detecta el idioma del texto con langdetect."""
        language = detect(text)
        logging.info(f"Idioma detectado: {language}")
        return language

    async def detect_emotion(self, text: str, language: str) -> str:
        """
        Detecta la emoción o estado emocional principal del usuario. 
        Utiliza un prompt específico para 'sentiment/emotion analysis'.
        """
        try:
            logging.info("Solicitando detección de emoción a OpenAI...")
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # o el que uses
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"Eres un psicólogo experto y tu tarea es detectar en {language} "
                            "la emoción o estado anímico predominante en el texto del usuario. "
                            "Provee un resultado breve y conciso (ej: 'tristeza', 'preocupación', "
                            "'alegría', 'ansiedad', 'esperanza', etc.). Si hay varias, elige la más dominante."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Texto del usuario:\n{text}"
                    }
                ],
                max_tokens=40,
                temperature=0.0,
                n=1
            )

            if (not response.choices or
                not response.choices[0].message or
                not response.choices[0].message.content):
                raise ValueError("Respuesta de OpenAI con estructura inválida.")

            emotion = response.choices[0].message.content.strip()
            logging.info(f"Emoción detectada: {emotion}")
            return emotion
        except Exception as e:
            logging.error(f"Error al detectar emoción: {e}")
            # Como fallback, usamos 'neutra' si falla
            return "neutra"

    async def summarize_text(
        self,
        text: str,
        language: str,
        format: str = "numbered points",
        detail_level: str = "concise"
    ) -> str:
        """
        Llama a OpenAI para producir un resumen breve.
        """
        try:
            logging.info("Solicitando resumen a OpenAI.")
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"Eres un experto en resumir textos en {language}. "
                            f"Tu tarea es producir un resumen {detail_level} y en formato {format}. "
                            "No añadas información extra ni opiniones personales."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Texto a resumir:\n{text}"
                    }
                ],
                max_tokens=400,
                temperature=0.3,
                n=1,
            )
            if (not response.choices or
                not response.choices[0].message or
                not response.choices[0].message.content):
                raise ValueError("Respuesta de OpenAI con estructura inválida.")

            summary = response.choices[0].message.content.strip()
            return summary
        except Exception as e:
            logging.error(f"Error al resumir texto: {e}")
            return "No pude generar un resumen en este momento."

    async def personal_answer(
        self,
        user_text: str,
        summary: str,
        language: str,
        emotion: str
    ) -> str:
        """
        Genera la respuesta final usando:
          - Ejemplos (few-shot)
          - Instrucciones de empatía/psicología
          - Emoción detectada
          - Hasta 3 emojis
        """
        try:
            # Seleccionar como máximo 3 emojis
            emojis = select_emojis(user_text, EMOJI_ARRAY, max_emojis=3)

            # Mensaje system adicional con enfoque psicológico avanzado
            advanced_system_msg = {
                "role": "system",
                "content": (
                    f"Responde en {language} como si fueras Ramon, un entrenador personal "
                    "que integra técnicas avanzadas de psicología emocional (entrevista motivacional, "
                    "refuerzo positivo, validación emocional, reformulación empática). "
                    "Reconoce la emoción principal del usuario, descrita aquí: "
                    f"{emotion}. Ofrece una respuesta cálida y cercana, "
                    "evitando sonar robótico o genérico. Sé genuino, humano y empático. "
                    "Usa un máximo de 3 emojis en total. "
                    "Puedes usar frases como 'veo que te sientes...', 'estoy aquí para acompañarte...' "
                    "para demostrar cercanía. "
                    "Al final, anima con un cierre positivo, pero realista."
                )
            }

            # Mensaje user con el resumen y el texto original
            new_user_message = {
                "role": "user",
                "content": (
                    f"Resumen del texto del usuario:\n{summary}\n\n"
                    f"Texto completo:\n{user_text}\n\n"
                    "Recuerda que la emoción principal detectada es: "
                    f"{emotion}. Ajusta tu respuesta empática y motivadora en consecuencia."
                )
            }

            # Armamos la lista final de mensajes
            messages = []
            messages.extend(FEW_SHOT_MESSAGES)   # Ejemplos “Ramon”
            messages.append(advanced_system_msg) # Indicaciones de psicología avanzada
            messages.append(new_user_message)    # Caso actual

            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=700,
                temperature=0.8,
                n=1,
            )

            if (not response.choices or
                not response.choices[0].message or
                not response.choices[0].message.content):
                raise ValueError("Respuesta de OpenAI con estructura inválida.")

            final_answer = response.choices[0].message.content.strip()

            # Paso extra: si la IA excedió 3 emojis, los recortamos
            final_answer = limit_emojis_in_text(final_answer, max_emoji_count=3)

            return final_answer
        except Exception as e:
            logging.error(f"Error al generar respuesta personal: {e}")
            return "Lo siento, no pude generar una respuesta personalizada en este momento."


# =============================================================================
#                          FUNCIONES AUXILIARES
# =============================================================================

def select_emojis(text: str, emoji_array: List[str], max_emojis: int = 3) -> str:
    """Selecciona aleatoriamente hasta max_emojis."""
    if max_emojis > len(emoji_array):
        max_emojis = len(emoji_array)
    random_emojis = random.sample(emoji_array, max_emojis)
    return " ".join(random_emojis)

def limit_emojis_in_text(text: str, max_emoji_count: int = 3) -> str:
    """Detecta y limita los emojis a max_emoji_count."""
    emoji_pattern = re.compile(
        "[\U0001F300-\U0001F5FF"
        "\U0001F600-\U0001F64F"
        "\U0001F680-\U0001F6FF"
        "\U0001F700-\U0001F77F"
        "\U0001F780-\U0001F7FF"
        "\U0001F800-\U0001F8FF"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\u200d"
        "\u2640-\u2642"
        "\u2600-\u2B55]+",
        flags=re.UNICODE
    )

    found_emojis = list(emoji_pattern.finditer(text))
    if len(found_emojis) <= max_emoji_count:
        return text

    keep_indexes = [m.span() for m in found_emojis[:max_emoji_count]]
    result = []
    last_idx = 0
    count = 0

    for match in emoji_pattern.finditer(text):
        start, end = match.span()
        if count < max_emoji_count:
            result.append(text[last_idx:start])
            result.append(text[start:end])
            last_idx = end
            count += 1
        else:
            result.append(text[last_idx:start])
            last_idx = end

    result.append(text[last_idx:])
    return "".join(result)

def split_in_chunks(text: str, max_size: int = 4096) -> List[str]:
    """
    Divide el texto en trozos de tamaño máximo `max_size`,
    para que no falle al enviar mensajes largos por Telegram.
    """
    return [text[i : i + max_size] for i in range(0, len(text), max_size)]


# =============================================================================
#                       HANDLERS DE TELEGRAM
# =============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /start."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "Hola, soy Ramon, tu entrenador personal virtual con un toque psicológico y empático. "
            "Puedo transcribir audios y responder a tus mensajes con consejos personalizados. "
            "¡Envíame un audio o un mensaje de texto!"
        ),
    )


async def handle_audio_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler genérico para mensajes de audio/voz."""
    user_id = update.effective_user.id
    if user_id not in USER_AUDIO_FILES:
        USER_AUDIO_FILES[user_id] = []

    new_file = await update.message.effective_attachment.get_file()
    file_path = TEMP_AUDIO_DIR / f"{new_file.file_id}.ogg"
    await new_file.download_to_drive(str(file_path))

    USER_AUDIO_FILES[user_id].append(str(file_path))

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Audio recibido. Envía más o escribe 'transcribe' para procesarlos."
    )


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para mensajes de texto."""
    text = update.message.text.strip()
    user_id = update.effective_user.id

    text_service = TextService(openai_client=openai_client)

    if text.lower() == "transcribe":
        # Procesar audios del usuario
        if user_id in USER_AUDIO_FILES and USER_AUDIO_FILES[user_id]:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Procesando tus audios..."
            )
            await process_audio_files(update, context, text_service)
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="No tienes audios pendientes."
            )
    else:
        # Procesar directamente el texto
        await process_text(update, context, text_service, text)


async def process_audio_files(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text_service: TextService
) -> None:
    """
    Concatena los audios del usuario, transcribe y luego procesa el texto resultante.
    """
    user_id = update.effective_user.id
    audio_paths = USER_AUDIO_FILES.get(user_id, [])
    if not audio_paths:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="No hay archivos de audio para procesar."
        )
        return

    combined_path = TEMP_AUDIO_DIR / "combined_audio.mp3"
    try:
        AudioService.concatenate_audio_files(audio_paths, combined_path)
        transcript = AudioService.transcribe_audio(combined_path)
        await process_text(update, context, text_service, transcript)
    except Exception as e:
        logging.error(f"Error procesando audio: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Lo siento, ocurrió un error procesando tu audio."
        )
    finally:
        # Limpieza de archivos
        if combined_path.exists():
            combined_path.unlink(missing_ok=True)
        for path_str in audio_paths:
            p = Path(path_str)
            if p.exists():
                p.unlink(missing_ok=True)
        USER_AUDIO_FILES[user_id] = []


async def process_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text_service: TextService,
    user_text: str
) -> None:
    """
    1. Detecta idioma.
    2. Detecta emoción.
    3. Genera resumen.
    4. Crea respuesta final con técnicas psicológicas y máximo 3 emojis.
    """
    try:
        # 1. Idioma
        language = await text_service.detect_language(user_text)
        
        # 2. Emoción
        emotion = await text_service.detect_emotion(user_text, language)

        # 3. Resumen
        summary = await text_service.summarize_text(user_text, language)

        # 4. Respuesta final
        personal_response = await text_service.personal_answer(
            user_text=user_text,
            summary=summary,
            language=language,
            emotion=emotion
        )

        # Enviamos todo en partes
        responses = [
            f"<b>Texto original:</b> {html.escape(user_text)}",
            f"<b>Emoción detectada:</b> {html.escape(emotion)}",
            f"<b>Resumen del texto:</b>\n{html.escape(summary)}",
            f"<b>Respuesta de Ramon (con empatía):</b>\n{html.escape(personal_response)}",
        ]

        for resp in responses:
            for chunk in split_in_chunks(resp):
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=chunk,
                    parse_mode="HTML"
                )

    except Exception as e:
        logging.error(f"Error procesando texto: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Lo siento, ocurrió un error procesando tu mensaje."
        )


# =============================================================================
#                           FUNCIÓN PRINCIPAL
# =============================================================================

def main() -> None:
    """Punto de entrada para ejecutar el bot de Telegram."""
    telegram_token = os.getenv("TELEGRAM_BOT_API_KEY")
    if not telegram_token:
        raise ValueError("Falta la variable TELEGRAM_BOT_API_KEY.")

    application = ApplicationBuilder().token(telegram_token).build()

    start_handler = CommandHandler("start", start)
    audio_handler = MessageHandler(filters.AUDIO & (~filters.COMMAND), handle_audio_message)
    voice_handler = MessageHandler(filters.VOICE & (~filters.COMMAND), handle_audio_message)
    text_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text_message)

    application.add_handler(start_handler)
    application.add_handler(audio_handler)
    application.add_handler(voice_handler)
    application.add_handler(text_handler)

    logging.info("Iniciando bot con polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
