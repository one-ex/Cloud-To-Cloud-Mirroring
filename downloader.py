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
        request = resumable_upload.init_session(filename, mime_type, size)
        for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                success = resumable_upload.upload_chunk(request, chunk)
                if not success:
                    return "Gagal upload chunk ke Google Drive."
        # Selesaikan upload
        file_id = resumable_upload.finish_session(request)
        if file_id:
            return f"Berhasil mirror ke Google Drive! File ID: {file_id}"
        else:
            return "Gagal menyelesaikan upload ke Google Drive."
    except Exception as e:
        return f"Error: {str(e)}"