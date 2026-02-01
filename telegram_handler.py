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

# Error handling helper functions
def handle_error(operation: str, error: Exception, level: str = "error", context_data: dict = None) -> None:
    """
    Standar error handling dengan logging yang konsisten
    
    Args:
        operation: Nama operasi yang gagal
        error: Exception yang terjadi
        level: Level logging (error/warning/info)
        context_data: Data tambahan untuk konteks error
    """
    error_msg = f"{operation} failed: {error}"
    
    if context_data:
        error_msg += f" | Context: {context_data}"
    
    if level == "error":
        logger.error(error_msg)
    elif level == "warning":
        logger.warning(error_msg)
    else:
        logger.info(error_msg)

def get_error_message(operation: str, default_msg: str = None) -> str:
    """
    Mendapatkan pesan error yang sesuai berdasarkan operasi
    
    Args:
        operation: Nama operasi
        default_msg: Pesan default jika tidak ada mapping khusus
    
    Returns:
        Pesan error yang sesuai
    """
    error_mapping = {
        "delete_message": ErrorMessages.PROCESSING_ERROR,
        "send_message": ErrorMessages.CONNECTION_ERROR,
        "edit_message": ErrorMessages.PROCESSING_ERROR,
        "upload": ErrorMessages.UPLOAD_FAILED,
        "drive_operation": ErrorMessages.DRIVE_ERROR,
        "mirror_process": ErrorMessages.PROCESSING_ERROR,
        "validation": ErrorMessages.VALIDATION_ERROR,
        "cancellation": ErrorMessages.CANCELLATION_FAILED,
        "confirmation": ErrorMessages.CONFIRMATION_ERROR,
    }
    
    return error_mapping.get(operation, default_msg or ErrorMessages.UNKNOWN_ERROR)

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
            handle_error("delete_message", e, "warning", {"message_id": message_id, "chat_id": chat_id})

async def send_message_safely(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, **kwargs):
    """
    Helper function untuk mengirim pesan secara aman
    """
    try:
        return await context.bot.send_message(chat_id=chat_id, text=text, **kwargs)
    except Exception as e:
        handle_error("send_message", e, "error", {"chat_id": chat_id, "text_length": len(text)})
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /start"""
    try:
        await update.message.reply_text("Halo! Kirimkan URL file yang ingin di-mirror ke Google Drive.")
    except Exception as e:
        handle_error("start_command", e, "error", {"user_id": update.effective_user.id if update.effective_user else None})

async def mirror(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk menerima URL file dari user"""
    try:
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
        
    except Exception as e:
        handle_error("mirror_command", e, "error", {
            "user_id": update.effective_user.id if update.effective_user else None,
            "url": url[:100] if 'url' in locals() else None
        })
        await update.message.reply_text(ErrorMessages.PROCESSING_ERROR)
    
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

            # Simpan info proses yang sedang berjalan - optimalkan memory usage
            user_processes[user_id] = {
                'cancellation_event': cancellation_event,
                'progress_message_id': progress_message.message_id,  # Simpan hanya ID, bukan object
                'user_id': user_id,
                'info_message_id': info_message_id,
                'chat_id': query.message.chat_id,
                'bot': context.bot,  # Simpan hanya bot, bukan seluruh context (memory leak fix)
                'message_edited': False  # Flag untuk cegah duplikasi edit
            }

            async def progress_callback(percent, error=None, done=False, cancelled=False, message="", downloaded=0, total=0, speed=0, eta=None, elapsed=0, filename=""):
                try:
                    # Cek apakah pesan sudah pernah di-edit atau user sudah tidak ada di proses
                    if user_id not in user_processes or user_processes[user_id].get('message_edited', False):
                        return
                    
                    # Ambil process info sekali untuk digunakan di semua kondisi
                    process_info = user_processes[user_id]
                    
                    if cancelled:
                        # Tandai sebelum operasi async untuk mencegah race condition
                        user_processes[user_id]['message_edited'] = True
                        
                        # Hapus pesan info file yang dikirim sebelumnya menggunakan helper function
                        if 'info_message_id' in process_info:
                            await delete_messages_safely(
                                context, 
                                process_info['chat_id'], 
                                [process_info['info_message_id']]
                            )
                        
                        # Tampilkan pesan pembatalan
                        try:
                            await process_info['bot'].edit_message_text(
                                chat_id=process_info['chat_id'],
                                message_id=process_info['progress_message_id'],
                                text=SuccessMessages.MIRRORING_CANCELLED
                            )
                        except Exception as e:
                            handle_error("edit_message", e, "warning", {
                                "operation": "cancellation", 
                                "chat_id": process_info['chat_id'],
                                "message_id": process_info['progress_message_id']
                            })
                        
                        # Hapus dari proses setelah edit berhasil
                        user_processes.pop(user_id, None)
                    elif error:
                        # Tandai pesan sudah di-edit sebelum operasi async
                        user_processes[user_id]['message_edited'] = True
                        try:
                            # Untuk error sesungguhnya - pakai error message dari config
                            await process_info['bot'].edit_message_text(
                                chat_id=process_info['chat_id'],
                                message_id=process_info['progress_message_id'],
                                text=f"{UIConfig.Emoji.ERROR} Error: {error}"
                            )
                        except Exception as e:
                            handle_error("edit_message", e, "warning", {
                                "operation": "error_display", 
                                "chat_id": process_info['chat_id'],
                                "message_id": process_info['progress_message_id'],
                                "error_content": str(error)[:50]  # Batasi panjang error message
                            })
                        # Hapus dari proses yang sedang berjalan setelah edit berhasil/gagal
                        user_processes.pop(user_id, None)
                    elif done:
                        # Tandai pesan sudah di-edit sebelum operasi async
                        user_processes[user_id]['message_edited'] = True
                        try:
                            await process_info['bot'].edit_message_text(
                                chat_id=process_info['chat_id'],
                                message_id=process_info['progress_message_id'],
                                text=SuccessMessages.MIRRORING_COMPLETED
                            )
                        except Exception as e:
                            handle_error("edit_message", e, "warning", {
                                "operation": "completion", 
                                "chat_id": process_info['chat_id'],
                                "message_id": process_info['progress_message_id']
                            })
                        # Hapus dari proses yang sedang berjalan setelah edit berhasil/gagal
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

                        await process_info['bot'].edit_message_text(
                            chat_id=process_info['chat_id'],
                            message_id=process_info['progress_message_id'],
                            text=progress_info,
                            reply_markup=reply_markup
                        )
                except Exception as e:
                    handle_error("edit_message", e, "error", {
                        "operation": "progress_update", 
                        "user_id": user_id,
                        "percent": percent
                    })

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
                    handle_error("mirror_process", e, "error", {
                        "user_id": user_id,
                        "url": url[:100]  # Batasi panjang URL
                    })
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
        handle_error("confirmation", e, "error", {
            "user_id": user_id,
            "callback_data": query.data
        })
        # Coba edit message, tapi jika gagal (misalnya pesan sudah dihapus), kirim pesan baru
        try:
            await query.edit_message_text(ErrorMessages.CONFIRMATION_ERROR)
        except Exception:
            # Jika edit gagal, kirim pesan baru
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=ErrorMessages.CONFIRMATION_ERROR
            )
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
        handle_error("cancellation", e, "error", {
            "user_id": user_id,
            "has_active_process": user_id in user_processes
        })
        await query.edit_message_text(ErrorMessages.CANCELLATION_FAILED)

# Tambahkan middleware untuk logging request
async def log_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log semua update yang diterima untuk debugging"""
    try:
        logger.info(f"📨 Update diterima: {update.to_dict() if update else 'None'}")
    except Exception as e:
        # Untuk logging middleware, gunakan level warning agar tidak terlalu verbose
        handle_error("log_updates", e, "warning", {"update_id": update.update_id if update else None})

def main():
    """Fungsi utama untuk menjalankan bot"""
    try:
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
        
    except Exception as e:
        handle_error("main_startup", e, "error", {"port": PORT, "webhook_url": WEBHOOK_URL})
        logger.error("❌ Failed to start bot. Check configuration and network connectivity.")

if __name__ == "__main__":
    main()