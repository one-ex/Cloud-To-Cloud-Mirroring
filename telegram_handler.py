import os
import logging
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

# Dictionary untuk menyimpan data user yang sedang menunggu konfirmasi
user_pending = {}
# Dictionary untuk melacak proses mirror yang sedang aktif (untuk fitur batal)
active_mirrors = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Kirimkan URL file yang ingin di-mirror ke Google Drive.")

async def mirror(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    await update.message.reply_text("🔍 Memvalidasi URL...")
    
    valid, info = await validate_url_and_file(url)
    if not valid:
        await update.message.reply_text(f"❌ URL/file tidak valid: {info}")
        return
    
    user_id = update.effective_user.id
    user_pending[user_id] = {'url': url, 'info': info}
    
    kb = ReplyKeyboardMarkup([['Ya', 'Tidak']], one_time_keyboard=True, resize_keyboard=True)
    
    file_info = (
        f"📝 *Informasi File:*\n"
        f"- *Nama:* `{info.get('filename')}`\n"
        f"- *Ukuran:* {format_bytes(info.get('size'))}\n"
        f"- *Tipe:* `{info.get('type')}`\n\n"
        f"Lanjutkan mirroring?"
    )
    
    await update.message.reply_text(file_info, parse_mode='Markdown', reply_markup=kb)

async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani klik pada tombol Batal"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    if user_id in active_mirrors:
        active_mirrors[user_id] = True # Set flag batal ke True
        await query.answer("Membatalkan proses...")
        await query.edit_message_text("🛑 *Proses dihentikan oleh pengguna.*", parse_mode='Markdown')
    else:
        await query.answer("Proses tidak ditemukan atau sudah selesai.")

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in user_pending:
        return

    if text.lower() == "ya":
        data = user_pending[user_id]
        url = data['url']
        info = data['info']
        
        # Inisialisasi status aktif (False berarti belum dibatalkan)
        active_mirrors[user_id] = False
        
        # Buat tombol Batal
        keyboard = [[InlineKeyboardButton("❌ Batal Mirroring", callback_query_data="cancel_mirror")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        progress_message = await update.message.reply_text(
            "🚀 *Memulai mirroring...*", 
            parse_mode='Markdown', 
            reply_markup=reply_markup
        )

        async def progress_callback(percent, done=False, error=None):
            # CEK FLAG BATAL: Jika user menekan tombol batal, hentikan proses
            if active_mirrors.get(user_id) is True:
                raise Exception("Proses dibatalkan oleh pengguna.")

            try:
                if error:
                    await progress_message.edit_text(f"❌ *Error:* {error}", parse_mode='Markdown')
                elif done:
                    await progress_message.edit_text("✅ *Proses mirroring selesai!*", parse_mode='Markdown')
                else:
                    bar_length = 10
                    filled_length = int(bar_length * percent / 100)
                    bar = '█' * filled_length + '─' * (bar_length - filled_length)
                    
                    # Update pesan progress tanpa menghilangkan tombol batal
                    await progress_message.edit_text(
                        f"📤 *Sedang Mengunggah...*\n\n"
                        f"Progress: `[{bar}] {percent}%`",
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
            except Exception as e:
                logger.error(f"Gagal update progress: {e}")

        # Jalankan proses download & upload
        result = await stream_download_to_drive(url, info, progress_callback)
        
        # Hapus dari daftar aktif setelah selesai/error/batal
        active_mirrors.pop(user_id, None)
        
        if "dibatalkan" not in result.lower():
            await update.message.reply_text(result)
            
    else:
        await update.message.reply_text("Proses mirroring dibatalkan.")
    
    user_pending.pop(user_id, None)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Register Handler
    app.add_handler(CommandHandler("start", start))
    
    # Handler untuk tombol Inline "Batal"
    app.add_handler(CallbackQueryHandler(cancel_callback, pattern="cancel_mirror"))
    
    # Handler untuk teks konfirmasi "Ya/Tidak"
    app.add_handler(MessageHandler(filters.Regex(r"(?i)^(Ya|Tidak)$"), confirm))
    
    # Handler untuk URL baru
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mirror))
    
    logger.info("Bot started...")
    
    # Sesuaikan dengan mode Render (Webhook/Polling)
    if WEBHOOK_URL:
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=f"{WEBHOOK_URL}/webhook"
        )
    else:
        app.run_polling()

if __name__ == "__main__":
    main()
