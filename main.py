import os
import logging
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from config import settings
from telegram_bot import telegram_bot
from downloader import downloader

# Setup logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the application"""
    # Startup
    logger.info("Starting Cloud Mirror Bot...")
    
    # Setup webhook if in production
    if not settings.debug:
        try:
            await telegram_bot.setup_webhook()
            logger.info("Webhook setup completed")
        except Exception as e:
            logger.error(f"Failed to setup webhook: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Cloud Mirror Bot...")
    await downloader.close()


# Create FastAPI app
app = FastAPI(
    title="Cloud Mirror Bot API",
    description="API untuk mirror file dari berbagai cloud ke Google Drive via Telegram Bot",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Cloud Mirror Bot",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "webhook": "/webhook (POST)",
            "status": "/status"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "cloud-mirror-bot",
        "timestamp": "2024-01-01T00:00:00Z"  # This would be dynamic in real implementation
    }


@app.get("/status")
async def system_status():
    """System status endpoint"""
    try:
        # Import here to avoid circular imports
        from drive_manager import drive_manager
        
        quota_info = drive_manager.check_quota()
        
        return {
            "status": "operational",
            "google_drive": {
                "quota": quota_info
            },
            "telegram_bot": {
                "webhook_setup": not settings.debug
            }
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {
            "status": "degraded",
            "error": str(e)
        }


@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Webhook endpoint for Telegram"""
    try:
        # Verify secret token if in production
        if not settings.debug and settings.telegram_webhook_secret:
            secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if secret_token != settings.telegram_webhook_secret:
                raise HTTPException(status_code=403, detail="Invalid secret token")
        
        # Process the update
        update_data = await request.json()
        update = Update.de_json(update_data, telegram_bot.application.bot)
        
        # Process update
        await telegram_bot.application.process_update(update)
        
        return JSONResponse(content={"status": "ok"})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/mirror")
async def mirror_file(request: Request):
    """API endpoint untuk mirror file (alternatif selain Telegram)"""
    try:
        data = await request.json()
        url = data.get("url")
        
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")
        
        # Process mirror request
        result = await telegram_bot._process_mirror_request(url, "api_user")
        
        if result['success']:
            return {
                "success": True,
                "message": "File mirrored successfully",
                "data": {
                    "file_name": result['file_name'],
                    "file_size": result['file_size'],
                    "web_view_link": result['web_view_link']
                }
            }
        else:
            raise HTTPException(status_code=400, detail=result['message'])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API mirror failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    
    # Run in development mode (polling)
    if settings.debug:
        logger.info("Running in development mode (polling)")
        # Start bot polling in background
        import asyncio
        from threading import Thread
        
        def run_bot():
            telegram_bot.run_polling()
        
        bot_thread = Thread(target=run_bot, daemon=True)
        bot_thread.start()
    
    # Run FastAPI server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug
    )