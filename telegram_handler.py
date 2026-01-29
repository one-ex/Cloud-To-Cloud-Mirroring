import os
import logging
import threading
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from dotenv import load_dotenv
from validator import validate_url_and_file
from downloader import stream_download_to_drive
from utils import format_bytes

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8080))

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

user_pending = {}
user_processes = {}  # Track proses yang sedang berjalan

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
    
    # Gunakan format_bytes untuk menampilkan ukuran file
    file_size_formatted = format_bytes(info.get('size'))
    
    await update.message.reply_text(
        f"File: {info['filename']}\nUkuran: {file_size_formatted}\nTipe: {info['type']}\nLanjutkan mirroring?", reply_markup=kb)

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_pending:
        await update.message.reply_text("Tidak ada proses yang menunggu konfirmasi.")
        return
    
    if update.message.text.lower() == 'ya':
        url = user_pending[user_id]['url']
        info = user_pending[user_id]['info']
        
        # Buat cancellation event untuk proses ini
        cancellation_event = threading.Event()
        
        # Kirim pesan awal dengan tombol Stop
        keyboard = [[InlineKeyboardButton("⏹ Stop Mirroring", callback_data="stop_mirror")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        progress_message = await update.message.reply_text("Memulai proses mirroring...", reply_markup=reply_markup)

        # Simpan info proses yang sedang berjalan
        user_processes[user_id] = {
            'cancellation_event': cancellation_event,
            'progress_message': progress_message
        }

        async def progress_callback(percent, error=None, done=False):
            try:
                if error:
                    await progress_message.edit_text(f"❌ Error: {error}")
                    # Hapus dari proses yang sedang berjalan
                    user_processes.pop(user_id, None)
                elif done:
                    await progress_message.edit_text("✅ Proses mirroring selesai!")
                    # Hapus dari proses yang sedang berjalan
                    user_processes.pop(user_id, None)
                else:
                    # Buat progress bar sederhana dengan tombol stop
                    bar_length = 20
                    filled_length = int(bar_length * percent / 100)
                    bar = '█' * filled_length + '─' * (bar_length - filled_length)
                    keyboard = [[InlineKeyboardButton("⏹ Stop Mirroring", callback_data="stop_mirror")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await progress_message.edit_text(f"Progress: [{bar}] {percent}%", reply_markup=reply_markup)
            except Exception as e:
                logger.error(f"Gagal mengedit pesan progres: {e}")

        result = await stream_download_to_drive(url, info, progress_callback, cancellation_event)
        # Kirim hasil akhir sebagai pesan baru
        await update.message.reply_text(result)
    else:
        await update.message.reply_text("Proses mirroring dibatalkan.")
    
    user_pending.pop(user_id, None)

async def stop_mirror(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk tombol Stop Mirroring"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Jawab callback query
    await query.answer()
    
    # Cek apakah user memiliki proses yang sedang berjalan
    if user_id not in user_processes:
        await query.edit_message_text("Tidak ada proses mirroring yang sedang berjalan.")
        return
    
    # Tandai cancellation event
    process_info = user_processes[user_id]
    cancellation_event = process_info['cancellation_event']
    
    # Set event untuk memberhentikan proses
    cancellation_event.set()
    
    # Update pesan
    await query.edit_message_text("🛑 Proses mirroring dihentikan...")
    
    # Hapus dari daftar proses (akan dihapus sepenuhnya setelah proses berhenti)
    # Note: Proses akan dihapus dari user_processes di progress_callback saat error

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    # Handler konfirmasi harus diprioritaskan sebelum handler teks umum
    app.add_handler(MessageHandler(filters.Regex(r"(?i)^(Ya|Tidak)$"), confirm))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mirror))
    # Handler untuk tombol Stop
    app.add_handler(CallbackQueryHandler(stop_mirror, pattern="^stop_mirror$"))
    
    # Jalankan webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL
    )

if __name__ == "__main__":
    main()