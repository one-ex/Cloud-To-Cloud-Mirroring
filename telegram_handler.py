import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup  # type: ignore
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, TypeHandler  # type: ignore
from dotenv import load_dotenv  # type: ignore
from validator import validate_url_and_file
from downloader import stream_download_to_drive
from utils import format_bytes, DownloadCancelled


# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8080))

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Kirimkan URL file yang ingin di-mirror ke Google Drive.")

async def mirror(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    valid, info = await validate_url_and_file(url)
    if not valid:
        await update.message.reply_text(f"URL/file tidak valid: {info}")
        return
    # Simpan info ke context.user_data untuk state management yang lebih baik
    context.user_data['url_info'] = {'url': url, 'info': info}
    kb = ReplyKeyboardMarkup([['Ya', 'Tidak']], one_time_keyboard=True)
    
    # Gunakan format_bytes untuk menampilkan ukuran file
    file_size_formatted = format_bytes(info.get('size'))
    
    await update.message.reply_text(
        f"File: {info['filename']}\nUkuran: {file_size_formatted}\nTipe: {info['type']}\nLanjutkan mirroring?", reply_markup=kb)

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    choice = update.message.text
    if choice.lower() == 'ya':
        url_info = context.user_data.get('url_info')
        if not url_info:
            await update.message.reply_text("Sesi kadaluwarsa, silakan mulai lagi dengan mengirimkan URL.")
            return

        url = url_info['url']
        info = url_info['info']
        
        # Kirim pesan awal yang akan diedit
        progress_message = await update.message.reply_text("Memulai proses mirroring...")

        last_reported_percentage = -1

        async def progress_callback(percent, error=None, done=False):
            nonlocal last_reported_percentage
            if context.user_data.get('cancel_requested'):
                raise DownloadCancelled("Proses dibatalkan oleh pengguna.")

            current_percentage = int(percent)
            if current_percentage <= last_reported_percentage and not done and not error:
                return
            
            last_reported_percentage = current_percentage

            try:
                if error:
                    await progress_message.edit_text(f"❌ Error: {error}")
                elif done:
                    await progress_message.edit_text("✅ Proses mirroring selesai!")
                else:
                    bar_length = 20
                    filled_length = int(bar_length * current_percentage / 100)
                    bar = '█' * filled_length + '─' * (bar_length - filled_length)
                    await progress_message.edit_text(
                        f"Progress: [{bar}] {current_percentage}%",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Batal", callback_data="cancel")]])
                    )
            except Exception as e:
                # Log "Message is not modified" errors at a lower level to avoid clutter
                if "Message is not modified" in str(e):
                    logger.debug(f"Pesan tidak diubah: {e}")
                else:
                    logger.error(f"Gagal mengedit pesan progres: {e}")

        context.user_data['cancel_requested'] = False
        download_task = asyncio.create_task(
            stream_download_to_drive(url, info, progress_callback)
        )
        context.user_data['download_task'] = download_task

        try:
            result = await download_task
            # Kirim hasil akhir sebagai pesan baru
            await update.message.reply_text(result)
        except (asyncio.CancelledError, DownloadCancelled):
            await progress_message.edit_text("🛑 Proses mirroring dibatalkan.")
        except Exception as e:
            await progress_message.edit_text(f"❌ Terjadi error tak terduga: {e}")
            logger.error(f"Error selama mirroring: {e}")
        finally:
            # Hapus data sesi setelah selesai
            for key in ['download_task', 'cancel_requested', 'url_info']:
                context.user_data.pop(key, None)

    elif choice.lower() == 'tidak':
        await update.message.reply_text("Proses mirroring dibatalkan.")
        context.user_data.pop('url_info', None)

async def cancel_mirror(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Mencoba membatalkan...")
    logger.info(f"User {query.from_user.id} menekan tombol batal.")

    context.user_data['cancel_requested'] = True
    
    download_task = context.user_data.get('download_task')
    if download_task and not download_task.done():
        download_task.cancel()
        logger.info(f"Tugas unduhan untuk user {query.from_user.id} telah diminta untuk dibatalkan.")
        # Pesan akan diupdate menjadi 'dibatalkan' oleh blok except di fungsi confirm
    else:
        logger.warning(f"Tidak ada tugas unduhan aktif untuk user {query.from_user.id} untuk dibatalkan.")
        await query.edit_message_text("Tidak ada proses yang aktif untuk dibatalkan atau proses sudah selesai.")

async def debug_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Pembaruan mentah diterima: {update.to_json()}")


async def set_webhook(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Secara manual mengatur webhook dan melaporkan hasilnya."""
    try:
        await context.bot.set_webhook(url=WEBHOOK_URL, allowed_updates=Update.ALL_TYPES)
        webhook_info = await context.bot.get_webhook_info()
        await update.message.reply_text(f"Webhook berhasil diatur ke: {webhook_info.url}\nInfo: {webhook_info}")
        logger.info(f"Webhook diatur secara manual ke {WEBHOOK_URL}")
    except Exception as e:
        await update.message.reply_text(f"Gagal mengatur webhook: {e}")
        logger.error(f"Gagal mengatur webhook: {e}")

async def info_webhook(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mendapatkan informasi webhook saat ini."""
    try:
        webhook_info = await context.bot.get_webhook_info()
        if webhook_info.url:
            await update.message.reply_text(f"URL Webhook saat ini: {webhook_info.url}\nDetail: {webhook_info}")
        else:
            await update.message.reply_text("Tidak ada webhook yang diatur.")
        logger.info(f"Info webhook diminta: {webhook_info}")
    except Exception as e:
        await update.message.reply_text(f"Gagal mendapatkan info webhook: {e}")
        logger.error(f"Gagal mendapatkan info webhook: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates."""
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)

from hypercorn.config import Config
from hypercorn.asyncio import serve
from asgiref.wsgi import WsgiToAsgi

async def main() -> None:
    """Set up the application and run the bot with a webhook server."""
    ptb_app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Daftarkan semua handler
    ptb_app.add_error_handler(error_handler)
    ptb_app.add_handler(TypeHandler(Update, debug_update_handler), group=-1)
    ptb_app.add_handler(CommandHandler("start", start))
    ptb_app.add_handler(CommandHandler("setwebhook", set_webhook))
    ptb_app.add_handler(CommandHandler("infowebhook", info_webhook))
    ptb_app.add_handler(MessageHandler(filters.Regex(r"(?i)^(Ya|Tidak)$"), confirm))
    ptb_app.add_handler(CallbackQueryHandler(cancel_mirror, pattern='^cancel$'))
    ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mirror))

    await ptb_app.initialize()

    webhook_path = TELEGRAM_TOKEN.split(':')[-1]
    full_webhook_url = f"{WEBHOOK_URL.rstrip('/')}/{webhook_path}"
    await ptb_app.bot.set_webhook(url=full_webhook_url, allowed_updates=Update.ALL_TYPES)
    logger.info(f"Webhook set to {full_webhook_url}")

    flask_app = Flask(__name__)

    @flask_app.post(f"/{webhook_path}")
    async def webhook() -> tuple[str, int]:
        try:
            update = Update.de_json(await request.get_json(force=True), ptb_app.bot)
            await ptb_app.process_update(update)
            return "ok", 200
        except Exception as e:
            logger.error(f"Error in webhook handler: {e}", exc_info=True)
            return "error", 500

    asgi_app = WsgiToAsgi(flask_app)

    config = Config()
    config.bind = [f"0.0.0.0:{PORT}"]
    
    logger.info(f"Starting Hypercorn server on {config.bind[0]}")
    await serve(asgi_app, config)

    await ptb_app.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")