import os
import json
import logging
import requests
from google.oauth2.credentials import Credentials as UserCredentials
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

# Scope yang digunakan saat membuat token.json -- sebaiknya full drive untuk kemudahan
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Path ke token.json yang dihasilkan oleh flow OAuth (set di environment)
OAUTH_TOKEN_FILE = os.getenv('GOOGLE_OAUTH_TOKEN_FILE', 'token.json')
FOLDER_ID = os.getenv('DRIVE_FOLDER_ID')

# Muat kredensial user dari file token.json
user_creds = None
if OAUTH_TOKEN_FILE and os.path.exists(OAUTH_TOKEN_FILE):
    try:
        user_creds = UserCredentials.from_authorized_user_file(OAUTH_TOKEN_FILE, SCOPES)
        logger.info(f"Loaded OAuth token from {OAUTH_TOKEN_FILE}")
    except Exception as e:
        logger.error(f"Gagal memuat token OAuth dari {OAUTH_TOKEN_FILE}: {e}")
else:
    logger.error(f"Token OAuth tidak ditemukan di path: {OAUTH_TOKEN_FILE}. Pastikan file ada dan env var GOOGLE_OAUTH_TOKEN_FILE dikonfigurasi.")

class resumable_upload:
    @staticmethod
    def _get_access_token():
        """
        Pastikan credentials user valid, refresh jika perlu, dan simpan kembali token ke file jika terjadi refresh.
        """
        if not user_creds:
            raise Exception("Credentials OAuth user tidak tersedia. Set GOOGLE_OAUTH_TOKEN_FILE ke token.json.")

        creds = user_creds
        # Jika expired dan punya refresh token, refresh
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                try:
                    logger.info("Refreshing access token...")
                    creds.refresh(Request())
                    # Simpan kembali token yang sudah direfresh agar deployment memiliki token baru
                    try:
                        with open(OAUTH_TOKEN_FILE, 'w') as f:
                            f.write(creds.to_json())
                        logger.info(f"Token berhasil diperbarui dan disimpan ke {OAUTH_TOKEN_FILE}")
                    except Exception as e:
                        logger.warning(f"Gagal menyimpan token baru ke {OAUTH_TOKEN_FILE}: {e}")
                except Exception as e:
                    logger.exception(f"Gagal me-refresh token OAuth: {e}")
                    raise
            else:
                raise Exception("Credentials tidak valid dan tidak bisa di-refresh (tidak ada refresh_token).")

        return creds.token

    @staticmethod
    def init_session(filename, mime_type, size):
        """
        Meminta sesi resumable upload ke Drive API. Mengembalikan dict session berisi upload_url dsb.
        """
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
        logger.info(f"Inisialisasi sesi upload untuk file: {filename}")
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Headers: {json.dumps(headers)}")
        logger.debug(f"Metadata: {json.dumps(metadata)}")

        response = requests.post(url, headers=headers, data=json.dumps(metadata))
        logger.info(f"Init session response status: {response.status_code}")
        if response.status_code not in (200, 201):
            # Log body untuk debugging
            logger.error(f"Init session failed: {response.status_code} - {response.text}")
            raise Exception(f"Gagal inisialisasi sesi upload: {response.status_code} - {response.text}")

        upload_url = response.headers.get('Location')
        if not upload_url:
            logger.error("Header 'Location' tidak ditemukan pada response inisialisasi sesi.")
            raise Exception("Header 'Location' tidak ditemukan pada response inisialisasi sesi upload.")
        logger.info(f"Sesi upload berhasil. upload_url: {upload_url}")

        return {
            'upload_url': upload_url,
            'mime_type': mime_type,
            'size': size,
            'sent_bytes': 0
        }

    @staticmethod
    def upload_chunk(session, chunk):
        """
        Upload satu chunk ke upload_url sesi resumable.
        Mengembalikan (True, response_json) jika upload selesai (200/201),
        (True, None) jika accepted partial (308), atau (False, error_msg) jika gagal.
        """
        access_token = resumable_upload._get_access_token()
        start = session.get('sent_bytes', 0)
        end = start + len(chunk) - 1
        total_size = session.get('size')
        total_field = str(total_size) if total_size else '*'

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': session.get('mime_type', 'application/octet-stream'),
            'Content-Length': str(len(chunk)),
            'Content-Range': f'bytes {start}-{end}/{total_field}'
        }

        try:
            response = requests.put(session['upload_url'], headers=headers, data=chunk)
        except Exception as e:
            logger.exception(f"Network error saat upload chunk: {e}")
            return False, str(e)

        logger.debug(f"Upload chunk response status: {response.status_code}")
        if response.status_code in (200, 201):
            # Berhasil lengkap
            session['sent_bytes'] = end + 1
            try:
                return True, response.json()
            except Exception:
                return True, None
        elif response.status_code == 308:
            # Incomplete, chunk diterima
            session['sent_bytes'] = end + 1
            return True, None
        else:
            error_msg = f"Gagal upload chunk. Status: {response.status_code}, Response: {response.text}"
            logger.error(error_msg)
            return False, error_msg
