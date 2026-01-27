import io
import os
from typing import Optional, Dict, Any
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
import httpx

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
            # Create credentials from refresh token
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
            
            # Build the service
            self.service = build('drive', 'v3', credentials=self.credentials)
            
        except Exception as e:
            raise Exception(f"Failed to initialize Google Drive service: {str(e)}")
    
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
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, follow_redirects=True, timeout=30.0)
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
    
    def check_quota(self) -> Dict[str, Any]:
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