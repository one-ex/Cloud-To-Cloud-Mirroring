# Download streaming dengan chunking 5MB dan upload ke Google Drive

import requests # type: ignore
from drive_uploader import resumable_upload

CHUNK_SIZE = 5 * 1024 * 1024  # 5MB

async def stream_download_to_drive(url, info):
    try:
        resp = requests.get(url, stream=True)
        if resp.status_code != 200:
            return "Gagal mengunduh file."
        filename = info['filename']
        size = info['size']
        mime_type = info['type']
        # Mulai sesi upload ke Google Drive
        session = resumable_upload.init_session(filename, mime_type, size)
        for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                success = resumable_upload.upload_chunk(session, chunk)
                if not success:
                    return "Gagal upload chunk ke Google Drive."
        # Selesaikan upload
        result = resumable_upload.finish_session(session)
        return f"Berhasil mirror ke Google Drive! {result}"
    except Exception as e:
        return f"Error: {str(e)}"