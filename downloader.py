# Download streaming dengan chunking 5MB dan upload ke Google Drive

import requests # type: ignore
from drive_uploader import resumable_upload

CHUNK_SIZE = 5 * 1024 * 1024  # 5MB

async def stream_download_to_drive(url, info, progress_callback=None):
    try:
        resp = requests.get(url, stream=True)
        if resp.status_code != 200:
            return "Gagal mengunduh file."
        filename = info['filename']
        size = info['size']
        mime_type = info['type']
        session = resumable_upload.init_session(filename, mime_type, size)
        sent_bytes = 0
        last_percent_reported = 0
        for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                success = resumable_upload.upload_chunk(session, chunk)
                if not success:
                    if progress_callback:
                        await progress_callback(0, error="Gagal upload chunk ke Google Drive.")
                    return "Gagal upload chunk ke Google Drive."
                sent_bytes += len(chunk)
                percent = int((sent_bytes / size) * 100) if size else 0
                if percent >= last_percent_reported + 5 or percent == 100:
                    last_percent_reported = percent
                    if progress_callback:
                        await progress_callback(percent)
        result = resumable_upload.finish_session(session)
        if progress_callback:
            await progress_callback(100, done=True)
        return f"Berhasil mirror ke Google Drive! {result}"
    except Exception as e:
        if progress_callback:
            await progress_callback(0, error=str(e))
        return f"Error: {str(e)}"