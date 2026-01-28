# Upload ke Google Drive dengan resumable upload

from googleapiclient.discovery import build # type: ignore
from googleapiclient.http import MediaIoBaseUpload # type: ignore
from google.oauth2 import service_account # type: ignore
import io
import os

SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
FOLDER_ID = os.getenv('DRIVE_FOLDER_ID')

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

class resumable_upload:
    @staticmethod
    def init_session(filename, mime_type, size):
        file_metadata = {
            'name': filename,
            'parents': [FOLDER_ID] if FOLDER_ID else []
        }
        media = MediaIoBaseUpload(io.BytesIO(), mimetype=mime_type, chunksize=5*1024*1024, resumable=True)
        request = drive_service.files().create(body=file_metadata, media_body=media)
        request._buffer = io.BytesIO()  # Custom buffer untuk chunk
        return request

    @staticmethod
    def upload_chunk(request, chunk):
        try:
            request._buffer.write(chunk)
            request._buffer.seek(0)
            media = MediaIoBaseUpload(request._buffer, mimetype=request.media_body.mimetype, chunksize=5*1024*1024, resumable=True)
            request.media_body = media
            status, response = request.next_chunk()
            request._buffer = io.BytesIO()  # Reset buffer setelah upload
            return response is not None
        except Exception:
            return False

    @staticmethod
    def finish_session(request):
        try:
            file = request.execute()
            return file.get('id')
        except Exception:
            return None