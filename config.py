"""
Konfigurasi aplikasi Cloud To Cloud Mirroring
Pendekatan OOP dengan pengelompokan yang rapi untuk skalabilitas
"""

import logging

class DownloadConfig:
    """Konfigurasi untuk download dan upload"""
    TIMEOUT = 30                  # detik - timeout untuk request HTTP
    MAX_RETRIES = 3               # kali - maksimal percobaan ulang
    CHUNK_SIZE_MB = 10            # MB - ukuran chunk untuk streaming
    MAX_SPEED_SAMPLES = 10        # jumlah sample untuk hitung kecepatan
    RETRY_DELAY_MULTIPLIER = 2    # exponential backoff multiplier

class UIConfig:
    """Konfigurasi untuk tampilan UI"""
    PROGRESS_BAR_LENGTH = 10      # karakter - panjang visual progress bar
    UPDATE_INTERVAL = 1           # detik - interval update pesan
    MAX_MESSAGE_LENGTH = 4096     # karakter - batas Telegram
    
    class Emoji:
        """Semua emoji untuk progress display"""
        # Progress emojis
        FILE = '📁'
        PROGRESS = '📊'
        TIME = '⏱️'
        SIZE = '📏'
        DOWNLOAD = '⬇️'
        SPEED = '⚡'
        ETA = '⏳'
        
        # Status emojis
        SUCCESS = '✅'
        ERROR = '❌'
        WARNING = '⚠️'
        INFO = 'ℹ️'
        
        # Action emojis
        STOP = '⏹️'
        CANCEL = '❌'
        CONFIRM = '✅'
        DENY = '❌'
        
        # Progress bar characters
        FILLED = '■'
        EMPTY = '□'

class TelegramConfig:
    """Konfigurasi untuk Telegram Bot"""
    MAX_FILE_SIZE_GB = 50         # GB - batas ukuran file Google Drive
    MESSAGE_EDIT_DELAY = 0.1      # detik - jeda edit pesan (anti-rate limit)
    CALLBACK_QUERY_TIMEOUT = 300  # detik - timeout untuk callback query

class ErrorMessages:
    """Pesan error yang distandarisasi"""
    # General errors
    TIMEOUT_ERROR = "⏱️ Timeout - server terlalu lambat"
    CONNECTION_ERROR = "🔗 Connection error - periksa koneksi internet"
    INVALID_URL = "❌ URL/file tidak valid"
    NO_ACTIVE_PROCESS = "ℹ️ Tidak ada proses mirroring yang sedang berjalan"
    CANCELLATION_FAILED = "❌ Gagal menghentikan proses mirroring"
    CONFIRMATION_ERROR = "❌ Terjadi kesalahan saat memproses konfirmasi"
    NO_PENDING_PROCESS = "ℹ️ Tidak ada proses yang menunggu konfirmasi"
    
    # Upload errors
    UPLOAD_FAILED = "📤 Gagal upload chunk ke Google Drive"
    DRIVE_ERROR = "☁️ Error Google Drive"
    
    # System errors
    UNKNOWN_ERROR = "🚨 Error tidak diketahui"
    PROCESSING_ERROR = "⚙️ Terjadi kesalahan saat memproses"
    VALIDATION_ERROR = "🔍 Error saat validasi file"

class SuccessMessages:
    """Pesan sukses yang distandarisasi"""
    MIRRORING_STARTED = "⌛ Memulai proses mirroring ⌛"
    MIRRORING_CANCELLED = "❌ Proses mirroring dibatalkan."
    MIRRORING_COMPLETED = "✅ Proses mirroring selesai!"
    CONFIRMATION_RECEIVED = "✅ Konfirmasi diterima"
    PROCESS_CANCELLED = "❌ Proses dibatalkan"

class LoggingConfig:
    """Konfigurasi untuk logging"""
    LEVEL = logging.INFO
    FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    class Colors:
        """Warna untuk terminal logging (opsional)"""
        RED = '\033[91m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        MAGENTA = '\033[95m'
        CYAN = '\033[96m'
        WHITE = '\033[97m'
        RESET = '\033[0m'

class GoogleDriveConfig:
    """Konfigurasi untuk Google Drive"""
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    TOKEN_FILE = 'token.json'
    FOLDER_ID_ENV = 'DRIVE_FOLDER_ID'
    UPLOAD_TIMEOUT = 300  # 5 menit untuk upload besar
    MAX_CHUNK_SIZE = 10 * 1024 * 1024  # 5MB per chunk (resumable upload)
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024 * 1024  # 7GB maksimal ukuran file

# Export semua config untuk kemudahan import
__all__ = [
    'DownloadConfig',
    'UIConfig', 
    'TelegramConfig',
    'ErrorMessages',
    'SuccessMessages',
    'LoggingConfig',
    'GoogleDriveConfig'
]