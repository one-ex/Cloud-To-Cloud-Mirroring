import logging
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup  # type: ignore
from telegram.ext import ( # type: ignore
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from telegram.error import TelegramError # type: ignore

from config import settings
from downloader import downloader
from drive_manager import drive_manager

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TelegramBot:
    """Handler untuk bot Telegram"""
    
    def __init__(self):
        self.application = None
        self._initialize_bot()
    
    def _initialize_bot(self):
        """Initialize Telegram bot"""
        try:
            self.application = Application.builder()\
                .token(settings.telegram_bot_token)\
                .build()
            
            # Register handlers
            self._register_handlers()
            
            logger.info("Telegram bot initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            raise
    
    def _register_handlers(self):
        """Register command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Message handler for URLs
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_message
        ))
        
        # Callback query handler
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        welcome_message = (
            f"Halo {user.first_name}! 👋\n"
            f"Saya adalah Cloud Mirror Bot.\n\n"
            "Saya dapat membantu Anda mirror file dari berbagai sumber cloud "
            "ke Google Drive Anda.\n\n"
            "**Cara penggunaan:**\n"
            "1. Kirim URL file yang ingin di-mirror\n"
            "2. Saya akan mendownload file tersebut\n"
            "3. Saya akan upload ke Google Drive Anda\n\n"
            "**Sumber yang didukung:**\n"
            "• SourceForge\n"
            "• MediaFire\n"
            "• PixelDrain\n"
            "• Dan lainnya\n\n"
            "Gunakan /help untuk bantuan lebih lanjut."
        )
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = (
            "**Cloud Mirror Bot - Bantuan**\n\n"
            "**Perintah yang tersedia:**\n"
            "• /start - Memulai bot dan melihat panduan\n"
            "• /help - Menampilkan pesan bantuan ini\n"
            "• /status - Mengecek status sistem\n\n"
            "**Cara mirror file:**\n"
            "1. Kirim URL file ke chat ini\n"
            "2. Contoh URL:\n"
            "   • https://sourceforge.net/projects/...\n"
            "   • https://www.mediafire.com/...\n"
            "   • https://pixeldrain.com/u/...\n\n"
            "**Batasan:**\n"
            f"• Ukuran maksimal: {settings.max_file_size_mb} MB\n"
            "• Format file: Semua jenis file\n\n"
            "Bot akan mengirim notifikasi ketika proses selesai."
        )
        
        await update.message.reply_text(help_message, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            # Check Google Drive quota
            quota_info = await drive_manager.check_quota()
            
            status_message = (
                "**Status Sistem**\n\n"
                "✅ Bot berjalan normal\n\n"
                "**Google Drive Quota:**\n"
            )
            
            if quota_info.get('limit'):
                limit_gb = int(quota_info['limit']) / (1024**3)
                usage_gb = int(quota_info.get('usage', 0)) / (1024**3)
                usage_percent = (usage_gb / limit_gb) * 100
                
                status_message += (
                    f"• Total: {limit_gb:.2f} GB\n"
                    f"• Digunakan: {usage_gb:.2f} GB ({usage_percent:.1f}%)\n"
                )
            else:
                status_message += "• Quota: Unlimited\n"
            
            status_message += "\n**Sistem siap digunakan!**"
            
            await update.message.reply_text(status_message, parse_mode='Markdown')
            
        except Exception as e:
            error_message = f"Gagal memeriksa status: {str(e)}"
            await update.message.reply_text(error_message)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages (URLs)"""
        message_text = update.message.text.strip()
        user = update.effective_user
        
        # Check if message looks like a URL
        if not (message_text.startswith('http://') or message_text.startswith('https://')):
            await update.message.reply_text(
                "Silakan kirim URL yang valid (dimulai dengan http:// atau https://)"
            )
            return
        
        # Send processing message
        processing_msg = await update.message.reply_text(
            "⏳ Memproses URL...\n"
            "Saya akan mendownload dan mengupload file ke Google Drive Anda."
        )
        
        try:
            # Process the URL
            result = await self._process_mirror_request(message_text, user.id)
            
            # Update message with result
            if result['success']:
                success_message = (
                    f"✅ **Mirror Berhasil!**\n\n"
                    f"**File:** {result['file_name']}\n"
                    f"**Ukuran:** {result['file_size_human']}\n"
                    f"**Google Drive:** [Buka File]({result['web_view_link']})\n\n"
                    f"File telah berhasil diupload ke Google Drive Anda."
                )
                
                await processing_msg.edit_text(
                    success_message, 
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
            else:
                await processing_msg.edit_text(
                    f"❌ Gagal: {result['message']}"
                )
            
        except Exception as e:
            logger.error(f"Mirror failed for user {user.id}: {e}")
            error_message = (
                f"❌ **Gagal Memproses**\n\n"
                f"Terjadi kesalahan: {str(e)}\n\n"
                f"Pastikan URL valid dan file tidak melebihi {settings.max_file_size_mb} MB."
            )
            
            await processing_msg.edit_text(error_message)
    
    async def _process_mirror_request(self, url: str, user_id: int) -> dict:
        """Process mirror request dengan streaming untuk menghindari penyimpanan di RAM"""
        try:
            # Step 1: Dapatkan informasi file
            file_info = await downloader._get_file_info(url)
            filename = file_info.get('filename', 'downloaded_file.bin')
            mime_type = file_info.get('mime_type')
            file_size = file_info.get('file_size')
            
            # Validasi ukuran file
            if file_size and file_size > settings.max_file_size_mb * 1024 * 1024:
                return {
                    'success': False,
                    'message': f"File terlalu besar: {file_size} bytes (maks: {settings.max_file_size_mb} MB)"
                }
            
            # Step 2: Upload langsung dari URL dengan streaming
            upload_result = await drive_manager.upload_from_url_streaming(
                url, filename, mime_type
            )
            
            # Format file size untuk display
            if file_size:
                if file_size >= 1024**3:  # GB
                    file_size_human = f"{file_size / (1024**3):.2f} GB"
                elif file_size >= 1024**2:  # MB
                    file_size_human = f"{file_size / (1024**2):.2f} MB"
                elif file_size >= 1024:  # KB
                    file_size_human = f"{file_size / 1024:.2f} KB"
                else:
                    file_size_human = f"{file_size} bytes"
            else:
                file_size_human = "Unknown size"
            
            return {
                'success': True,
                'file_name': filename,
                'file_size': file_size,
                'file_size_human': file_size_human,
                'web_view_link': upload_result['web_view_link'],
                'message': 'Mirror completed successfully'
            }
            
        except Exception as e:
            logger.error(f"Process failed: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries"""
        query = update.callback_query
        await query.answer()
        
        # Handle different callback data
        callback_data = query.data
        
        if callback_data == 'status':
            await self.status_command(update, context)
        
        await query.edit_message_reply_markup(reply_markup=None)
    
    def run_polling(self):
        """Run bot in polling mode (for development)"""
        logger.info("Starting bot in polling mode...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    async def setup_webhook(self):
        """Setup webhook for production"""
        webhook_url = f"{settings.app_url}/webhook"
        
        try:
            await self.application.bot.set_webhook(
                url=webhook_url,
                secret_token=settings.telegram_webhook_secret
            )
            logger.info(f"Webhook set to: {webhook_url}")
        except TelegramError as e:
            logger.error(f"Failed to set webhook: {e}")
            raise


# Create global instance
telegram_bot = TelegramBot()