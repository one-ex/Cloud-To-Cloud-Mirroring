import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from validator import validate_url_and_file
from downloader import stream_download_to_drive

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8080))

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

user_pending = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Kirimkan URL file yang ingin di-mirror ke Google Drive.")

async def mirror(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    valid, info = await validate_url_and_file(url)
    if not valid:
        await update.message.reply_text(f"URL/file tidak valid: {info}")
        return
    # Simpan status pending user
    user_pending[update.effective_user.id] = {'url': url, 'info': info}
    kb = ReplyKeyboardMarkup([['Ya', 'Tidak']], one_time_keyboard=True)
    await update.message.reply_text(
        f"File: {info['filename']}\nUkuran: {info['size']} bytes\nTipe: {info['type']}\nLanjutkan mirroring?", reply_markup=kb)

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_pending:
        await update.message.reply_text("Tidak ada proses yang menunggu konfirmasi.")
        return
    if update.message.text.lower() == 'ya':
        url = user_pending[user_id]['url']
        info = user_pending[user_id]['info']
        await update.message.reply_text("Memulai proses mirroring...")
        async def progress_callback(percent, error=None, done=False):
            if error:
                await update.message.reply_text(f"❌ Error: {error}")
            elif done:
                await update.message.reply_text("✅ Proses mirroring selesai!")
            else:
                await update.message.reply_text(f"Progress: {percent}%")
        result = await stream_download_to_drive(url, info, progress_callback)
        await update.message.reply_text(result)
    else:
        await update.message.reply_text("Proses mirroring dibatalkan.")
    user_pending.pop(user_id, None)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    # Handler konfirmasi harus diprioritaskan sebelum handler teks umum
    app.add_handler(MessageHandler(filters.Regex(r"(?i)^(Ya|Tidak)$"), confirm))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mirror))
    
    # Jalankan webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL
    )

if __name__ == "__main__":
    main()