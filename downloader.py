# Download streaming dengan chunking 5MB dan upload ke Google Drive

import requests
import logging
from drive_uploader import resumable_upload

logger = logging.getLogger(__name__)
CHUNK_SIZE = 5 * 1024 * 1024  # 5MB

async def stream_download_to_drive(url, info, progress_callback=None):
    try:
        logger.info(f"Memulai stream download dari {url}")
        resp = requests.get(url, stream=True, allow_redirects=True)
        if resp.status_code != 200:
            error_msg = f"Gagal mengunduh file. Status: {resp.status_code}"
            logger.error(error_msg)
            if progress_callback:
                await progress_callback(0, error=error_msg)
            return error_msg

        filename = info['filename']
        size = info.get('size') 
        mime_type = info.get('type', 'application/octet-stream')
        
        session = resumable_upload.init_session(filename, mime_type, size)
        
        sent_bytes = 0
        last_percent_reported = 0
        final_response = None

        for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                success, result = resumable_upload.upload_chunk(session, chunk)
                if not success:
                    error_msg = f"Gagal upload chunk ke Google Drive: {result}"
                    logger.error(error_msg)
                    if progress_callback:
                        await progress_callback(0, error=error_msg)
                    return error_msg
                
                if result:
                    final_response = result

                sent_bytes += len(chunk)
                if size and size > 0:
                    percent = int((sent_bytes / size) * 100)
                    if percent >= last_percent_reported + 10 or percent == 100:
                        last_percent_reported = percent
                        logger.info(f"Progress: {percent}%")
                        if progress_callback:
                            await progress_callback(percent)
        
        if progress_callback:
            await progress_callback(100, done=True)
        
        file_id = final_response.get('id') if final_response else "Unknown"
        success_msg = f"Berhasil mirror ke Google Drive! File ID: {file_id}"
        logger.info(success_msg)
        return success_msg

    except Exception as e:
        error_msg = f"Error selama proses stream: {e}"
        logger.exception(error_msg)
        if progress_callback:
            await progress_callback(0, error=str(e))
        return error_msg