import os
import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup # type: ignore
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler # type: ignore
from dotenv import load_dotenv # type: ignore
from validator import validate_url_and_file
from downloader import stream_download_to_drive
from utils import format_bytes, format_time, format_speed
from config import (
    DownloadConfig, UIConfig, TelegramConfig, 
    ErrorMessages, SuccessMessages
)

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8080))

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

user_pending = {}  # Simpan status pending user dengan inline keyboard
user_processes = {}  # Track proses yang sedang berjalan

async def delete_messages_safely(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_ids: list):
    """
    Helper function untuk menghapus pesan secara aman
    Mencegah duplikasi logika penghapusan pesan
    """
    for message_id in message_ids:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            logger.warning(f"Gagal menghapus pesan {message_id}: {e}")

async def send_message_safely(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, **kwargs):
    """
    Helper function untuk mengirim pesan secara aman
    """
    try:
        return await context.bot.send_message(chat_id=chat_id, text=text, **kwargs)
    except Exception as e:
        logger.error(f"Gagal mengirim pesan: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Kirimkan URL file yang ingin di-mirror ke Google Drive.")

async def mirror(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    valid, info = await validate_url_and_file(url)
    if not valid:
        await update.message.reply_text(f"URL/file tidak valid: {info}")
        return
    
    # Gunakan format_bytes untuk menampilkan ukuran file
    file_size_formatted = format_bytes(info.get('size'))
    
    # Kirim pesan pertama: Informasi file
    info_message = await update.message.reply_text(
        f"File: {info['filename']}\nUkuran: {file_size_formatted}\nTipe: {info['type']}"
    )
    
    # Buat inline keyboard untuk konfirmasi
    keyboard = [
        [InlineKeyboardButton("✅ Ya", callback_data="confirm_yes"),
         InlineKeyboardButton("❌ Tidak", callback_data="confirm_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Kirim pesan kedua: Konfirmasi dengan inline keyboard
    confirm_message = await update.message.reply_text(
        "Lanjutkan mirroring?",
        reply_markup=reply_markup
    )
    
    # Simpan status pending user dengan message_id untuk edit nanti
    user_pending[update.effective_user.id] = {
        'url': url, 
        'info': info,
        'info_message_id': info_message.message_id,
        'confirm_message_id': confirm_message.message_id,
        'chat_id': confirm_message.chat_id
    }

async def handle_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk tombol konfirmasi inline keyboard"""
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        # Jawab callback query
        await query.answer()
        
        # Cek apakah user memiliki proses yang menunggu konfirmasi
        if user_id not in user_pending:
            await query.edit_message_text(ErrorMessages.NO_PENDING_CONFIRMATION)
            return
        
        # Ambil data dari pending
        pending_data = user_pending[user_id]
        url = pending_data['url']
        info = pending_data['info']
        info_message_id = pending_data['info_message_id']
        
        if query.data == "confirm_yes":
            # Hapus pesan konfirmasi (pesan kedua), biarkan pesan info tetap ada
            await query.delete_message()
            
            # Buat cancellation event untuk proses ini (async-compatible)
            cancellation_event = asyncio.Event()
            
            # Kirim pesan awal dengan format yang diinginkan + tombol Stop
            keyboard = [[InlineKeyboardButton("⏹ Stop Mirroring", callback_data="stop_mirror")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            progress_message = await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=SuccessMessages.MIRRORING_STARTED,
                reply_markup=reply_markup
            )

            # Simpan info proses yang sedang berjalan
            user_processes[user_id] = {
                'cancellation_event': cancellation_event,
                'progress_message': progress_message,
                'user_id': user_id,
                'info_message_id': info_message_id,
                'chat_id': query.message.chat_id,
                'context': context,  # Simpan context untuk delete_message
                'message_edited': False  # Flag untuk cegah duplikasi edit
            }

            async def progress_callback(percent, error=None, done=False, cancelled=False, message="", downloaded=0, total=0, speed=0, eta=None, elapsed=0, filename=""):
                try:
                    # Cek apakah pesan sudah pernah di-edit atau user sudah tidak ada di proses
                    if user_id not in user_processes or user_processes[user_id].get('message_edited', False):
                        return
                    
                    if cancelled:
                        # Tandai sebelum edit untuk mencegah race condition
                        if user_id in user_processes:
                            user_processes[user_id]['message_edited'] = True
                        
                        # Hapus pesan info file yang dikirim sebelumnya
                        try:
                            if user_id in user_processes and 'info_message_id' in user_processes[user_id]:
                                await user_processes[user_id]['context'].bot.delete_message(
                                    chat_id=user_processes[user_id]['chat_id'],
                                    message_id=user_processes[user_id]['info_message_id']
                                )
                        except Exception as e:
                            logger.warning(f"Gagal menghapus pesan info: {e}")
                        
                        # Tampilkan pesan pembatalan
                        try:
                            await progress_message.edit_text(SuccessMessages.MIRRORING_CANCELLED)
                        except Exception as e:
                            logger.warning(f"Gagal mengedit pesan pembatalan: {e}")
                        
                        # Hapus dari proses setelah edit berhasil
                        if user_id in user_processes:
                            user_processes.pop(user_id, None)
                    elif error:
                        # Untuk error sesungguhnya - pakai error message dari config
                        await progress_message.edit_text(f"{UIConfig.Emoji.ERROR} Error: {error}")
                        # Tandai pesan sudah di-edit dan hapus dari proses yang sedang berjalan
                        user_processes[user_id]['message_edited'] = True
                        user_processes.pop(user_id, None)
                    elif done:
                        await progress_message.edit_text(SuccessMessages.MIRRORING_COMPLETED)
                        # Tandai pesan sudah di-edit dan hapus dari proses yang sedang berjalan
                        user_processes[user_id]['message_edited'] = True
                        user_processes.pop(user_id, None)
                    else:
                        # Buat progress bar sederhana dengan tombol stop
                        bar_length = UIConfig.PROGRESS_BAR_LENGTH
                        filled_length = int(bar_length * percent / 100)
                        bar = '■' * filled_length + '□' * (bar_length - filled_length)
                        keyboard = [[InlineKeyboardButton("⏹ Stop Mirroring", callback_data="stop_mirror")]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        # Format informasi detail dengan emoji dari config
                        progress_info = f"""{UIConfig.Emoji.FILE} File Name: {filename}
{UIConfig.Emoji.PROGRESS} Progress: [{bar}] {percent}%
{UIConfig.Emoji.TIME} Run Time: {format_time(elapsed)}
{UIConfig.Emoji.SIZE} Size: {format_bytes(total)}
{UIConfig.Emoji.DOWNLOAD} Downloaded: {format_bytes(downloaded)}
{UIConfig.Emoji.SPEED} Speed AVG: {format_speed(speed)}
{UIConfig.Emoji.ETA} Estimasi: {format_time(eta) if eta else "Menghitung..."}"""

                        await progress_message.edit_text(progress_info, reply_markup=reply_markup)
                except Exception as e:
                    logger.error(f"Gagal mengedit pesan progres: {e}")

            # Jalankan mirroring di background task
            async def run_mirror():
                try:
                    result = await stream_download_to_drive(url, info, progress_callback, cancellation_event)
                    # Kirim hasil akhir sebagai pesan baru jika belum di-handle di callback
                    if user_id in user_processes:  # Jika belum dihapus (tidak error/done)
                        await context.bot.send_message(
                            chat_id=query.message.chat_id,
                            text=result
                        )
                        user_processes.pop(user_id, None)
                except Exception as e:
                    logger.error(f"Error dalam proses mirroring: {e}")
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"🚨 Error: {str(e)} 🚨"
                    )
                    user_processes.pop(user_id, None)

            # Jalankan task secara async
            asyncio.create_task(run_mirror())
            
        elif query.data == "confirm_no":
            # Hapus kedua pesan menggunakan helper function (mencegah duplikasi)
            await delete_messages_safely(
                context, 
                pending_data['chat_id'], 
                [pending_data['confirm_message_id'], pending_data['info_message_id']]
            )
            # Kirim pesan pembatalan menggunakan helper function
            await send_message_safely(
                context,
                query.message.chat_id,
                SuccessMessages.CONFIRMATION_CANCELLED
            )
        
        # Hapus dari pending setelah diproses
        user_pending.pop(user_id, None)
        
    except Exception as e:
        logger.error(f"Error dalam handle_confirm_callback: {e}")
        await query.edit_message_text(ErrorMessages.CONFIRMATION_ERROR)
        user_pending.pop(user_id, None)

async def stop_mirror(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk tombol Stop Mirroring"""
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        # Jawab callback query
        await query.answer()
        
        # Cek apakah user memiliki proses yang sedang berjalan
        if user_id not in user_processes:
            await query.edit_message_text(ErrorMessages.NO_ACTIVE_PROCESS)
            return
        
        # Tandai cancellation event
        process_info = user_processes[user_id]
        cancellation_event = process_info['cancellation_event']
        
        # Set event untuk memberhentikan proses
        cancellation_event.set()
        
        # Pesan pembatalan akan ditangani oleh progress_callback di downloader.py
        # Tidak perlu edit manual di sini untuk menghindari duplikasi
        
        logger.info(f"User {user_id} menghentikan proses mirroring")
        logger.info(f"Cancellation event status: {cancellation_event.is_set()}")
        
    except Exception as e:
        logger.error(f"Error saat menghentikan mirroring: {e}")
        await query.edit_message_text(ErrorMessages.CANCELLATION_FAILED)

# Tambahkan middleware untuk logging request
async def log_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log semua update yang diterima untuk debugging"""
    logger.info(f"📨 Update diterima: {update.to_dict() if update else 'None'}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Tambahkan logging middleware
    app.add_handler(MessageHandler(filters.ALL, log_updates), group=-1)
    
    app.add_handler(CommandHandler("start", start))
    # Handler untuk konfirmasi inline keyboard
    app.add_handler(CallbackQueryHandler(handle_confirm_callback, pattern="^(confirm_yes|confirm_no)$"))
    # Handler untuk tombol Stop
    app.add_handler(CallbackQueryHandler(stop_mirror, pattern="^stop_mirror$"))
    # Handler umum untuk teks (URL)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mirror))
    
    # Jalankan webhook dengan path yang jelas
    logger.info(f"🚀 Starting webhook on port {PORT}")
    logger.info(f"🌐 Webhook URL: {WEBHOOK_URL}")
    
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL,
        drop_pending_updates=True  # Hapus update yang tertunda
    )

if __name__ == "__main__":
    main()