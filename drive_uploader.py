# Resumable upload ke Google Drive secara streaming per chunk (tanpa buffer besar)
import requests
import os
import json
from google.oauth2 import service_account # type: ignore
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
FOLDER_ID = os.getenv('DRIVE_FOLDER_ID')

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

class resumable_upload:
    @staticmethod
    def _get_access_token():
        creds.refresh(Request())
        return creds.token

    @staticmethod
    def init_session(filename, mime_type, size):
        access_token = resumable_upload._get_access_token()
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json; charset=UTF-8'
        }
        metadata = {
            'name': filename,
            'parents': [FOLDER_ID] if FOLDER_ID else []
        }
        params = {
            'uploadType': 'resumable'
        }
        url = 'https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable'
        response = requests.post(url, headers=headers, params=params, data=json.dumps(metadata))
        if response.status_code != 200:
            raise Exception(f'Gagal inisialisasi sesi upload: {response.text}')
        upload_url = response.headers['Location']
        return {
            'upload_url': upload_url,
            'mime_type': mime_type,
            'size': size,
            'sent_bytes': 0
        }

    @staticmethod
    def upload_chunk(session, chunk):
        access_token = resumable_upload._get_access_token()
        start = session['sent_bytes']
        end = start + len(chunk) - 1
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': session['mime_type'],
            'Content-Length': str(len(chunk)),
            'Content-Range': f'bytes {start}-{end}/{session["size"] if session["size"] else "*"}'
        }
        response = requests.put(session['upload_url'], headers=headers, data=chunk)
        if response.status_code in [200, 201]:
            session['sent_bytes'] = end + 1
            return True
        elif response.status_code == 308:
            session['sent_bytes'] = end + 1
            return True
        else:
            return False

    @staticmethod
    def finish_session(session):
        return 'Selesai (cek ID dari response terakhir upload_chunk)'