import logging
import os
import json
from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes
import whisper
from dotenv import load_dotenv
from pathlib import Path
from langdetect import detect, DetectorFactory
import html
import random
from pydub import AudioSegment  # Import pydub for audio concatenation

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
json_file_path = 'data.json'

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
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Predefined array of emojis
emoji_array = ["😀", "👌", "💯", "🔥", "🚀", "😘",  "💪", "👍"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="Hola 👋 I can transcribe audio files for you or summarize text messages. Just send me an audio file or a text message."
    )

# Store audio files received from the user
user_audio_files = {}

async def received_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_audio(update, context)

async def received_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_audio(update, context)

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    text = update.message.text.lower()
    user_id = update.effective_user.id
    
    if text == "transcribe":
        if user_id in user_audio_files and user_audio_files[user_id]:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text="☕ Processing all audio files..."
            )
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
    try:
        # Concatenate all audio files
        combined_audio = None
        for file_name in audio_files:
            audio = AudioSegment.from_file(file_name)
            if combined_audio is None:
                combined_audio = audio
            else:
                combined_audio += audio
        
        combined_file_name = "./temp_audio_files/combined_audio.mp3"
        combined_audio.export(combined_file_name, format="mp3")

        # Load the Whisper model
        model = whisper.load_model("medium")  # Choose your desired model size

        # Transcribe the audio
        result = model.transcribe(combined_file_name)
        transcript = result["text"]

        # Process the transcribed text
        await process_text(update, context, transcript, transcript)

        # Delete the audio files
        os.remove(combined_file_name)
        for file_name in audio_files:
            os.remove(file_name)
    except Exception as e:
        logging.error(f"Error during audio processing: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Sorry, an error occurred while processing your audio."
        )

async def process_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, transcript: str = None):
    try:
        # Detect the language of the text
        language = detect(text)
        logging.info(f"Detected language: {language}")

        # Summarize the text
        summary = await summarize_text(text, language)

        # Generate personal coaching response
        personal_response = await personal_answer(update, context, text, summary, language)

        # Send the merged response in parts
        messages = [
            f"✍️ Text: {html.escape(text)}",
            f"❇️ Summary:\n{html.escape(summary)}",
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
async def summarize_text(text: str, language: str) -> str:
    try:
        # Use OpenAI to summarize the text
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a helpful assistant. Provide a summary of the following text in numbered points in {language}."},
                {"role": "user", "content": text}
            ],
            max_tokens=400
        )

        # Log the response for debugging
        logging.info(f"Summary response: {response}")

        # Ensure we handle the response correctly
        if not response.choices or not response.choices[0].message or not response.choices[0].message.content:
            raise ValueError("Invalid response structure from OpenAI API")

        summary = response.choices[0].message.content
        return summary

    except Exception as e:
        logging.error(f"Error in summarizing text: {e}")
        return "Sorry, I couldn't summarize the text."

def select_emojis(text: str, emoji_array: list) -> str:
    random_emojis = random.sample(emoji_array, 3)
    return " ".join(random_emojis)

async def personal_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, summary: str, language: str) -> str:
    response = None  # Initialize response variable
    try:
        # Prepare context from personal emails
        email_context = "\n\n".join([email['body'] for email in personal_emails])

        # Select emojis based on the text
        emojis = select_emojis(text, emoji_array)

        # Use OpenAI to generate a personal coaching response
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a personal coach called Ramon. Use the following context to provide a brief and close response that sounds like it is coming from the coach in {language}."},
                {"role": "system", "content": email_context},
                {"role": "user", "content": f"Here is the transcription: {text}\nHere is the summary: {summary}\nInclude these emojis: {emojis}"}
            ],
            max_tokens=400
        )

        # Log the full response for debugging
        logging.info(f"Personal answer response: {response}")

        # Ensure we handle the response correctly
        if not response.choices or not response.choices[0].message or not response.choices[0].message.content:
            raise ValueError("Invalid response structure from OpenAI API")

        coach_response = response.choices[0].message.content
        return f"{coach_response}\n{emojis}"

    except Exception as e:
        logging.error(f"Error in generating personal coaching response: {e}")
        if response:
            logging.error(f"Full response object: {response}")
        return "Sorry, I couldn't generate a personal response."

if __name__ == "__main__":
    application = ApplicationBuilder().token(os.environ.get("TELEGRAM_BOT_API_KEY")).build()

    start_handler = CommandHandler("start", start)
    audio_handler = MessageHandler(filters.AUDIO & (~filters.COMMAND), received_audio)
    voice_handler = MessageHandler(filters.VOICE & (~filters.COMMAND), received_voice)
    text_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), received_text)

    application.add_handler(start_handler)
    application.add_handler(audio_handler)
    application.add_handler(voice_handler)
    application.add_handler(text_handler)

    application.run_polling()