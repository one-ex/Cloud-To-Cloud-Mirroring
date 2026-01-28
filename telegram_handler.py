# Handler Telegram & konfirmasi user

from telegram import Update, ReplyKeyboardMarkup # type: ignore
from telegram.ext import ContextTypes # type: ignore
from validator import validate_url_and_file
from downloader import stream_download_to_drive

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
        result = await stream_download_to_drive(url, info)
        await update.message.reply_text(result)
    else:
        await update.message.reply_text("Proses mirroring dibatalkan.")
    user_pending.pop(user_id, None)