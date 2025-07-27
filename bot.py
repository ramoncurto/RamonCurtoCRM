import logging
import os
import json
import asyncio
from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes
import whisper
from dotenv import load_dotenv
from pathlib import Path
from langdetect import detect, DetectorFactory
import html
import random
from pydub import AudioSegment

# Fix the seed for reproducibility of language detection
DetectorFactory.seed = 0

# Remove desktop.ini if it exists in langdetect profiles
profiles_path = 'G:/Mi unidad/RUN TO LIVE/RAMON-BOT/.venv/Lib/site-packages/langdetect/profiles'
desktop_ini_path = os.path.join(profiles_path, 'desktop.ini')
if os.path.exists(desktop_ini_path):
    os.remove(desktop_ini_path)
    print("Removed desktop.ini")

load_dotenv(".env")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

os.makedirs("./temp_audio_files", exist_ok=True)

# Use a relative path to the JSON file
json_file_path = 'exemples_correus.json'

# Check if the file exists before attempting to open
if not os.path.exists(json_file_path):
    raise FileNotFoundError(f"The file {json_file_path} does not exist.")

# Open the file safely using a relative path
with open(json_file_path, 'r') as file:
    personal_emails = json.load(file)

# Ensure personal_emails is a list of dictionaries
if not isinstance(personal_emails, list) or not all(isinstance(email, dict) for email in personal_emails):
    raise ValueError("The JSON file must contain a list of dictionaries.")

# Set OpenAI API key
try:
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    logging.error(f"Error initializing OpenAI client: {e}")
    openai_client = None  # Set to None if initialization fails

# Predefined array of emojis
emoji_array = ["😀", "👌", "🔥", "🚀", "😘", "💪", "👍"]

# Global loading of Whisper model to avoid repeated load times
try:
    whisper_model = whisper.load_model("small")
except Exception as e:
    logging.error(f"Error loading Whisper model: {e}")
    whisper_model = None

# Dictionary to store audio files received from each user
user_audio_files = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /start command. Greets the user and explains basic functionalities of the bot.
    """
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Hola 👋 I can transcribe audio files for you or summarize text messages. Just send me an audio file or a text message."
    )

async def received_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback for received voice messages. Delegates to handle_audio.
    """
    await handle_audio(update, context)

async def received_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback for received audio messages. Delegates to handle_audio.
    """
    await handle_audio(update, context)

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the reception of audio files. Downloads the audio, stores it temporarily,
    and waits for the user to request transcription or send more files.
    """
    user_id = update.effective_user.id

    # Create a list for the user's audio files if it doesn't exist
    if user_id not in user_audio_files:
        user_audio_files[user_id] = []

    # Download the audio file
    new_file = await update.message.effective_attachment.get_file()
    new_file_name = f"./temp_audio_files/{new_file.file_id}.ogg"
    await new_file.download_to_drive(new_file_name)

    # Add the file to the user's list of audio files
    user_audio_files[user_id].append(new_file_name)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Audio file received. Send more files or type 'transcribe' to process all received audio files."
    )

async def received_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the reception of text messages. If text == 'transcribe', processes audio.
    Otherwise, processes text through summarization and personal answer generation.
    """
    text = update.message.text.lower()
    user_id = update.effective_user.id

    if text == "transcribe":
        if user_id in user_audio_files and user_audio_files[user_id]:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="☕ Processing all audio files..."
            )
            # Process the audio in an async task
            await process_audio(update, context, user_audio_files[user_id])
            # Clear the list after processing
            user_audio_files[user_id] = []
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="No audio files to process."
            )
    else:
        await process_text(update, context, text)

async def process_audio(update: Update, context: ContextTypes.DEFAULT_TYPE, audio_files: list):
    """
    Concatenates received audio files, exports them to a single file, and transcribes.
    In parallel, it cleans up temporary files and processes the transcribed text.
    """
    if not whisper_model:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, the transcription model could not be loaded."
        )
        return

    try:
        # Concatenate all audio files in series
        combined_audio = None
        for file_name in audio_files:
            audio = AudioSegment.from_file(file_name)
            if combined_audio is None:
                combined_audio = audio
            else:
                combined_audio += audio

        combined_file_name = "./temp_audio_files/combined_audio.mp3"
        combined_audio.export(combined_file_name, format="mp3")

        # Transcribe the audio
        # Running the transcribe in a separate thread to avoid blocking
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, whisper_model.transcribe, combined_file_name)
        transcript = result["text"]

        # Parallel tasks:
        # 1) Clean up and remove files
        # 2) Process the transcribed text
        await asyncio.gather(
            process_text(update, context, transcript),
            cleanup_audio_files([combined_file_name] + audio_files)
        )
    except Exception as e:
        logging.error(f"Error during audio processing: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, an error occurred while processing your audio."
        )

async def cleanup_audio_files(file_paths):
    """
    Removes temporary audio files from the file system.
    """
    for file_path in file_paths:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as ex:
                logging.error(f"Error deleting file {file_path}: {ex}")

async def process_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """
    Detects the language of the text, summarizes it, then generates a personal response.
    """
    try:
        # Detect the language of the text
        language = detect(text)
        logging.info(f"Detected language: {language}")

        # Summarize text
        summary_task = asyncio.create_task(summarize_text(text, language))
        summary = await summary_task

        # Generate personal answer
        personal_answer_task = asyncio.create_task(personal_answer(update, context, text, summary, language))
        personal_response = await personal_answer_task

        # Send the merged response in parts
        messages = [
            f"✍️ Text: {html.escape(text)}",
            f"❇ Summary:\n{html.escape(summary)}",
            f"🤖 Personal Answer:\n{html.escape(personal_response)}"
        ]

        for message in messages:
            if len(message) > 4096:
                parts = [message[i:i+4096] for i in range(0, len(message), 4096)]
                for part in parts:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=part,
                        parse_mode="HTML"
                    )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    parse_mode="HTML"
                )
    except Exception as e:
        logging.error(f"Error during text processing: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, an error occurred while processing your text."
        )

async def summarize_text(text: str, language: str, format: str = "numbered points", detail_level: str = "concise") -> str:
    """
    Summarizes the given text in the specified language, format, and detail level.
    """
    if openai_client is None:
        logging.error("OpenAI client is not initialized.")
        return "Sorry, I couldn't summarize the text at this time."

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Eres un experto en resumir textos en {language}.\n\n"
                        f"Tu tarea es producir un resumen {detail_level} en formato {format} del texto proporcionado.\n\n"
                        "Sigue estos pasos:\n"
                        "1. Lee el texto cuidadosamente.\n"
                        "2. Identifica las ideas principales y puntos clave, enfocándote en la información más importante.\n"
                        "3. Organiza los puntos clave lógicamente, agrupando ideas relacionadas para mayor claridad.\n"
                        f"4. Escribe un resumen claro y conciso en {language}, utilizando el formato especificado {format}.\n\n"
                        "Asegúrate de que:\n"
                        "- El resumen capture la esencia del texto con precisión.\n"
                        "- El lenguaje sea claro y fácil de entender.\n"
                        "- No añadas opiniones personales ni información adicional.\n\n"
                        "No menciones los pasos en tu resumen final."
                    )
                },
                {"role": "user", "content": f"Texto a resumir:\n{text}"}
            ],
            max_tokens=400,
            temperature=0.3,
            n=1
        )
        logging.info(f"Summary response: {response}")

        if not response.choices or not response.choices[0].message or not response.choices[0].message.content:
            raise ValueError("Invalid response structure from OpenAI API")

        summary = response.choices[0].message.content
        return summary

    except Exception as e:
        logging.error(f"Error in summarizing text: {e}")
        return "Sorry, I couldn't summarize the text at this time."

def select_emojis(text: str, emoji_array: list) -> str:
    """
    Selects three random emojis from the emoji_array based on the provided text.
    """
    random_emojis = random.sample(emoji_array, 3)
    return " ".join(random_emojis)

async def personal_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, summary: str, language: str) -> str:
    """
    Uses OpenAI to generate a personal, empathetic, and motivational answer based on
    the user text, the summary, and additional email context.
    """
    # Limit the number of emails for context
    email_contexts = []
    for email in personal_emails[:5]:
        body = email.get('body', '').strip()
        if body:
            email_contexts.append(body)

    email_context = "\n\n".join(email_contexts)
    emojis = select_emojis(text, emoji_array)

    try:
        logging.info(f"Sending text to OpenAI: {text[:500]}...")
        logging.info(f"Sending summary to OpenAI: {summary[:500]}...")

        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Eres Ramón, un coach personal experimentado en fisiología del ejercicio, entrenamiento deportivo y coaching personal.\n\n"
                        "Tu objetivo es proporcionar una respuesta personalizada, empática y motivacional al usuario.\n\n"
                        "Sigue estos pasos:\n"
                        "1. **Entiende el mensaje del usuario:**\n"
                        "   - Lee cuidadosamente el mensaje y el resumen.\n"
                        "   - Identifica los logros, emociones y necesidades del usuario.\n"
                        "2. **Planifica tu respuesta de manera concisa:**\n"
                        "   - Enfócate en felicitar sus logros y mostrar entusiasmo.\n"
                        "   - Ofrece apoyo en sus próximos pasos de forma breve.\n"
                        f"3. **Redacta tu respuesta en {language}:**\n"
                        "   - Utiliza un tono informal, amigable y alentador.\n"
                        f"   - Incorpora de manera natural los siguientes emojis {emojis}.\n"
                        "   - Mantén la respuesta breve y al grano, evitando detalles innecesarios.\n\n"
                        "Asegúrate de que tu respuesta esté adaptada a la situación del usuario y sea concisa.\n"
                        "No menciones tus pasos de reflexión o razonamiento."
                    )
                },
                {"role": "system", "content": f"**Contexto:**\n{email_context}"},
                {"role": "user", "content": f"**Mensaje del usuario:**\n{text}\n\n**Resumen:**\n{summary}"}
            ],
            max_tokens=200,
            temperature=0.7,
            n=1
        )

        if not response.choices or not response.choices[0].message or not response.choices[0].message.content:
            raise ValueError("Invalid response structure from OpenAI API")

        coach_response = response.choices[0].message.content
        return f"{coach_response}\n{emojis}"

    except Exception as e:
        logging.error(f"Error in generating personal coaching response: {e}")
        return "Sorry, I couldn't generate a personal response."

def main():
    """
    Main entry point for the Telegram bot. It sets up the application with the required handlers
    and runs it in polling mode.
    """
    application = ApplicationBuilder().token(os.environ.get("TELEGRAM_BOT_API_KEY")).concurrent_updates(True).build()
    start_handler = CommandHandler("start", start)
    audio_handler = MessageHandler(filters.AUDIO & (~filters.COMMAND), received_audio)
    voice_handler = MessageHandler(filters.VOICE & (~filters.COMMAND), received_voice)
    text_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), received_text)

    application.add_handler(start_handler)
    application.add_handler(audio_handler)
    application.add_handler(voice_handler)
    application.add_handler(text_handler)

    application.run_polling()

if __name__ == "__main__":
    main()
    
  