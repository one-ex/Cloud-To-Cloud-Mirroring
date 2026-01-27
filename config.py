import os
import json
from typing import List, Optional
from pydantic import BaseSettings


class Settings(BaseSettings):
    # Telegram Bot Configuration
    telegram_bot_token: str
    telegram_webhook_secret: str = ""
    
    # Google Drive Configuration (Service Account)
    google_drive_service_account_json: Optional[str] = None
    google_drive_folder_id: str = "root"
    
    # Legacy OAuth 2.0 Configuration (for backward compatibility)
    google_drive_client_id: Optional[str] = None
    google_drive_client_secret: Optional[str] = None
    google_drive_refresh_token: Optional[str] = None
    
    # Application Configuration
    app_url: str = "http://localhost:8000"
    max_file_size_mb: int = 2048  # 2GB maximum
    allowed_domains: List[str] = ["sourceforge.net", "mediafire.com", "pixeldrain.com"]
    
    # Render/Server Configuration
    port: int = 8000
    debug: bool = False
    
    class Config:
        env_file = ".env"


# Create settings instance
settings = Settings()

# Calculate max file size in bytes
MAX_FILE_SIZE_BYTES = settings.max_file_size_mb * 1024 * 1024