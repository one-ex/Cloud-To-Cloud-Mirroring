import re
import httpx # type: ignore
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import cloudscraper # type: ignore
from bs4 import BeautifulSoup # type: ignore

from config import settings, MAX_FILE_SIZE_BYTES


class CloudDownloader:
    """Downloader untuk berbagai sumber cloud"""
    
    def __init__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        self.cloud_scraper = cloudscraper.create_scraper()
    
    async def download_file(self, url: str) -> Dict[str, Any]:
        """
        Download file dari URL
        
        Args:
            url: URL file yang akan didownload
            
        Returns:
            Dictionary dengan hasil download
        """
        try:
            # Validasi URL
            self._validate_url(url)
            
            # Dapatkan informasi file
            file_info = await self._get_file_info(url)
            
            # Download file
            return await self._download_file_content(url, file_info)
            
        except Exception as e:
            raise Exception(f"Download failed: {str(e)}")
    
    def _validate_url(self, url: str):
        """Validasi URL"""
        parsed_url = urlparse(url)
        
        if not parsed_url.scheme in ['http', 'https']:
            raise ValueError("URL harus menggunakan HTTP atau HTTPS")
        
        # Tidak ada validasi domain - semua domain diizinkan
    
    async def _get_file_info(self, url: str) -> Dict[str, Any]:
        """Dapatkan informasi file dari URL"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Handle berbagai sumber cloud
        if 'sourceforge.net' in domain:
            return await self._get_sourceforge_info(url)
        elif 'mediafire.com' in domain:
            return await self._get_mediafire_info(url)
        elif 'pixeldrain.com' in domain:
            return await self._get_pixeldrain_info(url)
        else:
            # Fallback untuk URL langsung
            return await self._get_direct_file_info(url)
    
    async def _get_sourceforge_info(self, url: str) -> Dict[str, Any]:
        """Get file info from SourceForge"""
        try:
            # SourceForge sering memerlukan scraping
            response = self.cloud_scraper.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Cari informasi file
            filename = ""
            file_size = ""
            
            # Coba berbagai pola untuk SourceForge
            download_link = soup.find('a', {'id': 'downloadButton'})
            if download_link:
                filename = download_link.get('download', '')
                
            # Jika tidak ditemukan, gunakan URL sebagai referensi
            if not filename:
                filename = url.split('/')[-1] or "sourceforge_file.bin"
            
            return {
                'filename': filename,
                'direct_url': url,  # SourceForge biasanya redirect
                'source': 'sourceforge'
            }
            
        except Exception as e:
            raise Exception(f"Failed to get SourceForge info: {str(e)}")
    
    async def _get_mediafire_info(self, url: str) -> Dict[str, Any]:
        """Get file info from MediaFire"""
        try:
            response = self.cloud_scraper.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Cari download button
            download_button = soup.find('a', {'class': 'input popsok', 'id': 'downloadButton'})
            if download_button:
                direct_url = download_button.get('href')
                
                # Dapatkan filename dari URL atau konten
                filename = ""
                filename_div = soup.find('div', {'class': 'filename'})
                if filename_div:
                    filename = filename_div.text.strip()
                
                if not filename and direct_url:
                    filename = direct_url.split('/')[-1].split('?')[0]
                
                return {
                    'filename': filename or "mediafire_file.bin",
                    'direct_url': direct_url,
                    'source': 'mediafire'
                }
            else:
                raise Exception("Download button not found on MediaFire page")
                
        except Exception as e:
            raise Exception(f"Failed to get MediaFire info: {str(e)}")
    
    async def _get_pixeldrain_info(self, url: str) -> Dict[str, Any]:
        """Get file info from PixelDrain"""
        try:
            # PixelDrain API
            file_id = url.split('/')[-1]
            api_url = f"https://pixeldrain.com/api/file/{file_id}/info"
            
            response = await self.session.get(api_url)
            if response.status_code == 200:
                data = response.json()
                
                direct_url = f"https://pixeldrain.com/api/file/{file_id}"
                
                return {
                    'filename': data.get('name', 'pixeldrain_file.bin'),
                    'direct_url': direct_url,
                    'file_size': data.get('size'),
                    'mime_type': data.get('mime_type'),
                    'source': 'pixeldrain'
                }
            else:
                raise Exception(f"PixelDrain API error: {response.status_code}")
                
        except Exception as e:
            raise Exception(f"Failed to get PixelDrain info: {str(e)}")
    
    async def _get_direct_file_info(self, url: str) -> Dict[str, Any]:
        """Get info for direct file URLs"""
        try:
            # HEAD request untuk mendapatkan headers
            response = await self.session.head(url, follow_redirects=True)
            
            if response.status_code != 200:
                raise Exception(f"URL returned status {response.status_code}")
            
            # Dapatkan filename dari Content-Disposition atau URL
            filename = ""
            content_disposition = response.headers.get('content-disposition', '')
            
            if 'filename=' in content_disposition:
                # Extract filename from Content-Disposition
                match = re.search(r'filename="?([^";]+)"?', content_disposition)
                if match:
                    filename = match.group(1)
            
            if not filename:
                # Extract from URL
                filename = url.split('/')[-1].split('?')[0] or "downloaded_file.bin"
            
            # Dapatkan file size
            content_length = response.headers.get('content-length')
            file_size = int(content_length) if content_length else None
            
            # Dapatkan MIME type
            mime_type = response.headers.get('content-type', '').split(';')[0]
            
            return {
                'filename': filename,
                'direct_url': url,
                'file_size': file_size,
                'mime_type': mime_type,
                'source': 'direct'
            }
            
        except Exception as e:
            raise Exception(f"Failed to get direct file info: {str(e)}")
    
    async def download_file_streaming(self, url: str) -> Dict[str, Any]:
        """
        Download file dengan streaming chunking untuk menghindari penyimpanan di RAM
        
        Args:
            url: URL file yang akan didownload
            
        Returns:
            Dictionary dengan informasi file dan generator untuk chunk data
        """
        try:
            # Validasi URL
            self._validate_url(url)
            
            # Dapatkan informasi file
            file_info = await self._get_file_info(url)
            direct_url = file_info.get('direct_url', url)
            
            # Periksa ukuran file dari header
            async with httpx.AsyncClient() as client:
                head_response = await client.head(direct_url, follow_redirects=True, timeout=30.0)
                head_response.raise_for_status()
                
                content_length = head_response.headers.get('content-length')
                if content_length:
                    file_size = int(content_length)
                    if file_size > MAX_FILE_SIZE_BYTES:
                        raise Exception(f"File too large: {file_size} bytes (max: {MAX_FILE_SIZE_BYTES} bytes)")
                    file_info['file_size'] = file_size
                
                # Buat generator untuk streaming chunk
                async def chunk_generator():
                    """Generator untuk menghasilkan chunk data"""
                    async with httpx.AsyncClient() as download_client:
                        async with download_client.stream(
                            'GET', 
                            direct_url, 
                            follow_redirects=True, 
                            timeout=60.0
                        ) as response:
                            response.raise_for_status()
                            
                            chunk_size = 10 * 1024 * 1024  # 10MB per chunk
                            total_downloaded = 0
                            
                            async for chunk in response.aiter_bytes(chunk_size):
                                total_downloaded += len(chunk)
                                
                                # Validasi ukuran saat streaming
                                if total_downloaded > MAX_FILE_SIZE_BYTES:
                                    raise Exception(f"File too large: {total_downloaded} bytes (max: {MAX_FILE_SIZE_BYTES} bytes)")
                                
                                yield chunk
                
                return {
                    'success': True,
                    'filename': file_info.get('filename'),
                    'chunk_generator': chunk_generator(),
                    'size': file_info.get('file_size'),
                    'mime_type': file_info.get('mime_type'),
                    'source': file_info.get('source')
                }
                
        except httpx.RequestError as e:
            raise Exception(f"Download request failed: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise Exception(f"Download failed with status {e.response.status_code}")
        except Exception as e:
            raise Exception(f"Download failed: {str(e)}")
    
    async def download_file(self, url: str) -> Dict[str, Any]:
        """
        Download file dari URL (legacy method untuk kompatibilitas)
        
        Args:
            url: URL file yang akan didownload
            
        Returns:
            Dictionary dengan hasil download
        """
        try:
            # Validasi URL
            self._validate_url(url)
            
            # Dapatkan informasi file
            file_info = await self._get_file_info(url)
            
            # Download file dengan streaming
            result = await self.download_file_streaming(url)
            
            # Kumpulkan semua chunk ke memory (untuk kompatibilitas)
            content = b''
            async for chunk in result['chunk_generator']:
                content += chunk
            
            return {
                'success': True,
                'filename': file_info.get('filename'),
                'content': content,
                'size': len(content),
                'mime_type': file_info.get('mime_type'),
                'source': file_info.get('source')
            }
            
        except Exception as e:
            raise Exception(f"Download failed: {str(e)}")
    
    async def close(self):
        """Close session"""
        await self.session.aclose()


# Create global instance
downloader = CloudDownloader()