import io
import os
import json
from typing import Optional, Dict, Any, Generator
from google.oauth2 import service_account # type: ignore
from google.oauth2.credentials import Credentials # type: ignore
from google.auth.transport.requests import Request # type: ignore
from googleapiclient.discovery import build # type: ignore
from googleapiclient.http import MediaIoBaseUpload, MediaUpload # type: ignore
from googleapiclient.errors import HttpError # type: ignore
import httpx # type: ignore

from config import settings


class GoogleDriveManager:
    """Manager untuk mengelola upload file ke Google Drive"""
    
    def __init__(self):
        self.credentials = None
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Drive API service"""
        try:
            # Priority 1: Service Account from environment variable JSON string
            if settings.google_drive_service_account_json:
                try:
                    # Parse JSON string from environment variable
                    service_account_info = json.loads(settings.google_drive_service_account_json)
                    self.credentials = service_account.Credentials.from_service_account_info(
                        service_account_info,
                        scopes=['https://www.googleapis.com/auth/drive']
                    )
                    print("✓ Google Drive service initialized using Service Account from environment variable")
                except json.JSONDecodeError as e:
                    raise Exception(f"Invalid JSON in GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON: {str(e)}")
            
            # Priority 2: Legacy OAuth 2.0 credentials
            elif settings.google_drive_client_id and settings.google_drive_client_secret and settings.google_drive_refresh_token:
                self.credentials = Credentials(
                    token=None,
                    refresh_token=settings.google_drive_refresh_token,
                    client_id=settings.google_drive_client_id,
                    client_secret=settings.google_drive_client_secret,
                    token_uri="https://oauth2.googleapis.com/token"
                )
                
                # Refresh token if needed
                if self.credentials.expired:
                    self.credentials.refresh(Request())
                
                print("✓ Google Drive service initialized using OAuth 2.0 credentials")
            
            else:
                raise Exception("No valid Google Drive credentials found. Please set either GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON or OAuth 2.0 credentials.")
            
            # Build the service
            self.service = build('drive', 'v3', credentials=self.credentials)
            
        except Exception as e:
            raise Exception(f"Failed to initialize Google Drive service: {str(e)}")
    
    async def upload_from_url_streaming(self, url: str, filename: str, mime_type: str = None) -> Dict[str, Any]:
        """
        Download dan upload file dari URL dengan streaming langsung ke Google Drive
        menggunakan resumable upload dengan chunking tanpa menyimpan file di memory atau disk
        
        Args:
            url: URL file yang akan diupload
            filename: Nama untuk file yang diupload
            mime_type: Tipe MIME file
            
        Returns:
            Dictionary dengan hasil upload
        """
        try:
            # Tentukan MIME type jika tidak disediakan
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            # Buat metadata file
            file_metadata = {
                'name': filename,
                'parents': [settings.google_drive_folder_id]
            }
            
            print(f"Memulai streaming upload {filename} dari {url}...")
            
            # Dapatkan informasi ukuran file terlebih dahulu
            async with httpx.AsyncClient() as client:
                try:
                    head_response = await client.head(url, follow_redirects=True, timeout=10.0)
                    content_length = head_response.headers.get('content-length')
                    total_size = int(content_length) if content_length else None
                    
                    if total_size:
                        print(f"Ukuran file: {total_size} bytes ({total_size / (1024**2):.2f} MB)")
                        
                        # Validasi ukuran file
                        if total_size > settings.max_file_size_mb * 1024 * 1024:
                            raise Exception(f"File terlalu besar: {total_size} bytes (maks: {settings.max_file_size_mb} MB)")
                except Exception as e:
                    print(f"Tidak dapat mendapatkan ukuran file: {e}")
                    total_size = None
            
            # Buat buffer yang akan diisi secara bertahap
            buffer = io.BytesIO()
            
            # Buat media upload dengan buffer kosong untuk memulai session resumable
            media = MediaIoBaseUpload(buffer, 
                                     mimetype=mime_type,
                                     resumable=True)
            
            # Buat request upload
            request = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, size, webViewLink'
            )
            
            # Mulai upload resumable dan dapatkan session URI
            print(f"Memulai upload resumable untuk {filename}...")
            resumable_media = request.resumable_upload()
            upload_url = resumable_media.uri
            
            print(f"Session URI didapatkan, mulai streaming download dan upload...")
            
            # Download dan upload secara streaming
            chunk_size = 5 * 1024 * 1024  # 5MB per chunk
            uploaded_bytes = 0
            chunk_index = 0
            
            async with httpx.AsyncClient() as client:
                async with client.stream('GET', url, follow_redirects=True, timeout=300.0) as response:
                    response.raise_for_status()
                    
                    # Buffer untuk chunk saat ini
                    chunk_buffer = bytearray()
                    
                    async for chunk in response.aiter_bytes(chunk_size):
                        chunk_buffer.extend(chunk)
                        
                        # Jika buffer sudah mencapai atau melebihi chunk_size, upload
                        if len(chunk_buffer) >= chunk_size:
                            chunk_index += 1
                            print(f"Mengupload chunk {chunk_index} ({len(chunk_buffer)} bytes)...")
                            
                            # Upload chunk ini
                            chunk_io = io.BytesIO(chunk_buffer)
                            resumable_media.upload(chunk_io, len(chunk_buffer))
                            
                            uploaded_bytes += len(chunk_buffer)
                            chunk_buffer = bytearray()
                            
                            # Tampilkan progress
                            if total_size:
                                percent = (uploaded_bytes / total_size) * 100
                                print(f"Progress: {uploaded_bytes}/{total_size} bytes ({percent:.1f}%)")
                            else:
                                print(f"Progress: {uploaded_bytes} bytes uploaded")
                    
                    # Upload sisa data di buffer (chunk terakhir)
                    if chunk_buffer:
                        chunk_index += 1
                        print(f"Mengupload chunk terakhir {chunk_index} ({len(chunk_buffer)} bytes)...")
                        
                        chunk_io = io.BytesIO(chunk_buffer)
                        resumable_media.upload(chunk_io, len(chunk_buffer))
                        
                        uploaded_bytes += len(chunk_buffer)
                        
                        if total_size:
                            percent = (uploaded_bytes / total_size) * 100
                            print(f"Progress akhir: {uploaded_bytes}/{total_size} bytes ({percent:.1f}%)")
                        else:
                            print(f"Progress akhir: {uploaded_bytes} bytes uploaded")
                    
                    # Selesaikan upload
                    print(f"Menyelesaikan upload...")
                    file = resumable_media.finish()
                    
                    print(f"Upload berhasil: {file.get('name')} (ID: {file.get('id')})")
                    
                    return {
                        'success': True,
                        'file_id': file.get('id'),
                        'file_name': file.get('name'),
                        'file_size': file.get('size'),
                        'web_view_link': file.get('webViewLink'),
                        'message': f"File '{filename}' berhasil diupload ke Google Drive"
                    }
                    
        except httpx.RequestError as e:
            raise Exception(f"Failed to download file: {str(e)}")
        except HttpError as e:
            error_details = str(e)
            if 'quotaExceeded' in error_details or 'storageQuotaExceeded' in error_details:
                raise Exception("Google Drive quota exceeded")
            elif 'rateLimitExceeded' in error_details:
                raise Exception("Rate limit exceeded, please try again later")
            else:
                raise Exception(f"Google Drive API error: {error_details}")
        except Exception as e:
            raise Exception(f"Upload failed: {str(e)}")
    
    def upload_file_from_url(self, url: str, filename: str, mime_type: str = None) -> Dict[str, Any]:
        """
        Download file from URL and upload to Google Drive
        
        Args:
            url: URL of the file to download
            filename: Name for the uploaded file
            mime_type: MIME type of the file
            
        Returns:
            Dictionary with upload result
        """
        try:
            # Download file from URL
            print(f"Downloading file from {url}...")
            
            response = httpx.get(url, follow_redirects=True, timeout=30.0)
            response.raise_for_status()
            
            file_content = response.content
            file_size = len(file_content)
            
            print(f"Downloaded {file_size} bytes")
            
            # Upload to Google Drive
            return self._upload_to_drive(file_content, filename, mime_type)
                
        except httpx.RequestError as e:
            raise Exception(f"Failed to download file: {str(e)}")
        except Exception as e:
            raise Exception(f"Upload failed: {str(e)}")
    
    def _upload_to_drive(self, file_content: bytes, filename: str, mime_type: str = None) -> Dict[str, Any]:
        """Upload file content to Google Drive"""
        try:
            # Determine MIME type if not provided
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            # Create file metadata
            file_metadata = {
                'name': filename,
                'parents': [settings.google_drive_folder_id]
            }
            
            # Create media upload
            file_stream = io.BytesIO(file_content)
            media = MediaIoBaseUpload(file_stream, 
                                     mimetype=mime_type,
                                     resumable=True)
            
            # Execute upload
            print(f"Uploading {filename} to Google Drive...")
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, size, webViewLink'
            ).execute()
            
            print(f"Upload successful: {file.get('name')} (ID: {file.get('id')})")
            
            return {
                'success': True,
                'file_id': file.get('id'),
                'file_name': file.get('name'),
                'file_size': file.get('size'),
                'web_view_link': file.get('webViewLink'),
                'message': f"File '{filename}' berhasil diupload ke Google Drive"
            }
            
        except HttpError as e:
            error_details = str(e)
            if 'quotaExceeded' in error_details:
                raise Exception("Google Drive quota exceeded")
            elif 'rateLimitExceeded' in error_details:
                raise Exception("Rate limit exceeded, please try again later")
            else:
                raise Exception(f"Google Drive API error: {error_details}")
        except Exception as e:
            raise Exception(f"Upload failed: {str(e)}")
    
    async def check_quota(self) -> Dict[str, Any]:
        """Check Google Drive quota usage"""
        try:
            about = self.service.about().get(fields="storageQuota").execute()
            storage_quota = about.get('storageQuota', {})
            
            return {
                'limit': storage_quota.get('limit'),
                'usage': storage_quota.get('usage'),
                'usage_in_drive': storage_quota.get('usageInDrive'),
                'usage_in_drive_trash': storage_quota.get('usageInDriveTrash')
            }
        except Exception as e:
            raise Exception(f"Failed to check quota: {str(e)}")


# Create global instance
drive_manager = GoogleDriveManager()