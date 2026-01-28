import os
import logging
from telegram import Update # type: ignore
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes # type: ignore
from dotenv import load_dotenv # type: ignore
import aria2p # type: ignore
from google.oauth2 import service_account # type: ignore
from googleapiclient.discovery import build # type: ignore
from googleapiclient.http import MediaFileUpload # type: ignore
import requests # type: ignore
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove # type: ignore
from telegram_handler import start, mirror, confirm

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Hapus integrasi aria2p dan gunakan httpx/requests untuk download streaming
# import aria2p # type: ignore
# Setup aria2
# aria2 = aria2p.API(aria2p.Client(host="http://localhost", port=6800, secret=""))

# Setup Google Drive API
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
credentials = service_account.Credentials.from_service_account_file(GOOGLE_APPLICATION_CREDENTIALS, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)
user_pending = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Kirimkan URL file yang ingin di-mirror ke Google Drive.")

async def mirror(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    chat_id = update.message.chat_id
    # Jika user sedang konfirmasi, cek jawaban
    if chat_id in user_pending:
        if url.lower() == 'ya':
            url, file_name, content_type, file_size = user_pending.pop(chat_id)
            await update.message.reply_text("Melanjutkan proses mirroring...")
            try:
                from downloader import stream_download_to_drive
                info = {'filename': file_name, 'size': file_size, 'type': content_type}
                result = await stream_download_to_drive(url, info)
                await update.message.reply_text(result)
            except Exception as e:
                logger.error(f"Error: {e}")
                await update.message.reply_text(f"Gagal memproses: {e}")
        else:
            user_pending.pop(chat_id)
            await update.message.reply_text("Proses mirroring dibatalkan.")
        return
    await update.message.reply_text(f"Memproses URL: {url}")
    try:
        response = requests.head(url, allow_redirects=True)
        if response.status_code != 200:
            await update.message.reply_text("URL tidak dapat diakses atau tidak ditemukan.")
            return
        file_name = url.split('/')[-1] or 'file_mirror'
        content_type = response.headers.get('Content-Type', 'Unknown')
        content_length = response.headers.get('Content-Length', None)
        file_size = int(content_length) if content_length else None
        info_msg = f"Info file:\nNama: {file_name}\nTipe: {content_type}\nUkuran: {file_size if file_size else 'Unknown'} bytes"
        await update.message.reply_text(info_msg)
        MAX_SIZE = 2 * 1024 * 1024 * 1024
        if file_size and file_size > MAX_SIZE:
            await update.message.reply_text("Ukuran file terlalu besar untuk di-mirror (maksimal 2GB).")
            return
        # Simpan status pending konfirmasi beserta info file
        user_pending[chat_id] = (url, file_name, content_type, file_size)
        reply_markup = ReplyKeyboardMarkup([["Ya", "Tidak"]], one_time_keyboard=True)
        await update.message.reply_text("Apakah ingin melanjutkan proses mirroring?", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"Gagal memproses: {e}")

if __name__ == "__main__":
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mirror))
    app.add_handler(MessageHandler(filters.Regex("^(Ya|Tidak)$"), confirm))
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        webhook_url=WEBHOOK_URL
    )