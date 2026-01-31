# Download streaming dengan chunking dan upload ke Google Drive

import requests # type: ignore
import logging
import time
import asyncio
from drive_uploader import resumable_upload
from utils import format_bytes, format_time, format_speed, calculate_eta
from config import DownloadConfig, ErrorMessages

logger = logging.getLogger(__name__)  

async def stream_download_to_drive(url, info, progress_callback=None, cancellation_event=None):
    """
    Download streaming dengan chunking dan upload ke Google Drive
    cancellation_event: asyncio.Event untuk cancellation
    """
    # Implementasi retry mechanism
    resp = None
    for attempt in range(DownloadConfig.MAX_RETRIES):
        try:
            logger.info(f"Mencoba download dari {url} (attempt {attempt + 1}/{DownloadConfig.MAX_RETRIES})")
            resp = requests.get(
                url, 
                stream=True, 
                allow_redirects=True,
                timeout=DownloadConfig.TIMEOUT
            )
            
            if resp.status_code == 200:
                break  # Sukses, keluar dari loop retry
            elif resp.status_code in [503, 504, 429] and attempt < DownloadConfig.MAX_RETRIES - 1:
                # Server busy, tunggu dengan exponential backoff
                wait_time = DownloadConfig.RETRY_DELAY_MULTIPLIER ** attempt
                logger.warning(f"Server busy (status {resp.status_code}), tunggu {wait_time} detik...")
                time.sleep(wait_time)
                continue
            else:
                # Status error lain, langsung break
                break
                
        except requests.Timeout:
            if attempt < DownloadConfig.MAX_RETRIES - 1:
                logger.warning(f"Timeout pada attempt {attempt + 1}, coba lagi...")
                continue
            else:
                error_msg = ErrorMessages.TIMEOUT_ERROR
                logger.error(error_msg)
                if progress_callback:
                    await progress_callback(0, error=error_msg)
                return error_msg
                
        except requests.ConnectionError:
            if attempt < DownloadConfig.MAX_RETRIES - 1:
                logger.warning(f"Connection error pada attempt {attempt + 1}, coba lagi...")
                continue
            else:
                error_msg = ErrorMessages.CONNECTION_ERROR
                logger.error(error_msg)
                if progress_callback:
                    await progress_callback(0, error=error_msg)
                return error_msg
    
    if not resp or resp.status_code != 200:
        error_msg = f"Gagal mengunduh file setelah {DownloadConfig.MAX_RETRIES} percobaan. Status: {resp.status_code if resp else 'No response'}"
        logger.error(error_msg)
        if progress_callback:
            await progress_callback(0, error=error_msg)
        return error_msg
    
    filename = info.get('filename') or url.rstrip('/').split('/')[-1].split('?')[0]
    size = info.get('size') 
    mime_type = info.get('type', 'application/octet-stream')
    
    if not filename:
        error_msg = "Gagal mendapatkan nama file dari URL."
        logger.error(error_msg)
        if progress_callback:
            await progress_callback(0, error=error_msg)
        return error_msg
    
    session = resumable_upload.init_session(filename, mime_type, size)
    
    sent_bytes = 0
    last_percent_reported = 0
    final_response = None
    start_time = time.time()
    speed_samples = []
    
    # Gunakan chunk size dari config
    chunk_size_bytes = DownloadConfig.CHUNK_SIZE_MB * 1024 * 1024
    
    try:
        for chunk in resp.iter_content(chunk_size=chunk_size_bytes):
            # Cek apakah proses dibatalkan (async-safe)
            if cancellation_event and cancellation_event.is_set():
                logger.info("Proses dibatalkan oleh user - cancellation event detected")
                if progress_callback:
                    await progress_callback(0, cancelled=True, message="Proses dihentikan oleh user")
                return "Proses dihentikan oleh user"
            
            # Small delay untuk allow cancellation check
            await asyncio.sleep(0.001)
            
            if chunk:
                chunk_start_time = time.time()
                success, result = resumable_upload.upload_chunk(session, chunk)
                chunk_end_time = time.time()
                
                if not success:
                    error_msg = f"{ErrorMessages.UPLOAD_FAILED}: {result}"
                    logger.error(error_msg)
                    if progress_callback:
                        await progress_callback(0, error=error_msg)
                    return error_msg
                
                if result:
                    final_response = result

                sent_bytes += len(chunk)
                
                # Calculate speed
                chunk_time = chunk_end_time - chunk_start_time
                if chunk_time > 0:
                    chunk_speed = len(chunk) / chunk_time
                    speed_samples.append(chunk_speed)
                    if len(speed_samples) > DownloadConfig.MAX_SPEED_SAMPLES:
                        speed_samples.pop(0)
                
                avg_speed = sum(speed_samples) / len(speed_samples) if speed_samples else 0
                elapsed_time = time.time() - start_time
                eta_seconds = calculate_eta(sent_bytes, size, avg_speed) if size and avg_speed > 0 else None
                
                if size and size > 0:
                    percent = int((sent_bytes / size) * 100)
                    if percent >= last_percent_reported + 1 or percent == 100:
                        last_percent_reported = percent
                        logger.info(f"Progress: {percent}%")
                        if progress_callback:
                            await progress_callback(
                                    percent,
                                    downloaded=sent_bytes,
                                    total=size,
                                    speed=avg_speed,
                                    eta=eta_seconds,
                                    elapsed=elapsed_time,
                                    filename=filename
                                )
        
        if progress_callback:
            await progress_callback(100, done=True)
        
        file_id = final_response.get('id') if final_response else "Unknown"
        success_msg = f"Berhasil mirror ke Google Drive! File ID: {file_id}"
        logger.info(success_msg)
        return success_msg

    except Exception as e:
        error_msg = f"{ErrorMessages.PROCESSING_ERROR}: {e}"
        logger.exception(error_msg)
        if progress_callback:
            await progress_callback(0, error=str(e))
        return error_msg
    return error_msg