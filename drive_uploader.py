# Resumable upload ke Google Drive secara streaming per chunk (tanpa buffer besar)
import requests
import os
import json
import logging
from google.oauth2 import service_account
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
FOLDER_ID = os.getenv('DRIVE_FOLDER_ID')

creds = None
if SERVICE_ACCOUNT_FILE and os.path.exists(SERVICE_ACCOUNT_FILE):
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    except Exception as e:
        logger.error(f"Gagal memuat credentials dari {SERVICE_ACCOUNT_FILE}: {e}")
else:
    logger.error(f"File credentials '{SERVICE_ACCOUNT_FILE}' tidak ditemukan atau env var GOOGLE_APPLICATION_CREDENTIALS tidak di-set.")


class resumable_upload:
    @staticmethod
    def _get_access_token():
        if not creds:
            raise Exception("Credentials Google tidak terkonfigurasi.")
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
        url = 'https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&supportsAllDrives=true'
        
        logger.info(f"Menginisiasi sesi upload untuk: {filename}")
        logger.info(f"Request URL: {url}")
        logger.info(f"Request Headers: {json.dumps(headers, indent=2)}")
        logger.info(f"Request Body (Metadata): {json.dumps(metadata, indent=2)}")
        response = requests.post(url, headers=headers, data=json.dumps(metadata))
        
        if response.status_code != 200:
            error_msg = f'Gagal inisialisasi sesi upload: {response.status_code} - {response.text}'
            logger.error(error_msg)
            raise Exception(error_msg)
            
        upload_url = response.headers['Location']
        logger.info(f"Sesi upload berhasil dibuat. URL: {upload_url}")
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
            logger.info("Upload chunk berhasil dan selesai.")
            return True, response.json()
        elif response.status_code == 308:
            session['sent_bytes'] = end + 1
            return True, None
        else:
            error_message = f"Gagal upload chunk. Status: {response.status_code}, Response: {response.text}"
            logger.error(error_message)
            return False, error_message