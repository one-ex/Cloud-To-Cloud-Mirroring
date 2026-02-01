# Validasi URL dan file

import requests # type: ignore
import mimetypes
import time
import asyncio
from urllib.parse import urlparse, unquote
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from config import DownloadConfig, ErrorMessages, GoogleDriveConfig
from utils import format_bytes
import logging

# Setup logger untuk validator
logger = logging.getLogger(__name__)

# Simple cache untuk hasil validasi
_validation_cache: Dict[str, Tuple[dict, datetime]] = {}
_circuit_breaker_failures: Dict[str, int] = {}
_circuit_breaker_last_failure: Dict[str, datetime] = {}

def _get_cache_key(url: str) -> str:
    """Generate cache key dari URL"""
    return url.strip().lower()

def _is_cache_valid(cache_time: datetime) -> bool:
    """Cek apakah cache masih valid (5 menit)"""
    return datetime.now() - cache_time < timedelta(minutes=5)

def _should_use_circuit_breaker(url: str) -> bool:
    """Circuit breaker untuk URL yang terlalu sering gagal"""
    domain = urlparse(url).netloc
    
    # Reset circuit breaker jika sudah 15 menit dari kegagalan terakhir
    if domain in _circuit_breaker_last_failure:
        if datetime.now() - _circuit_breaker_last_failure[domain] > timedelta(minutes=15):
            _circuit_breaker_failures[domain] = 0
            return False
    
    # Maksimal 5 kegagalan berturut-turut dalam 15 menit
    return _circuit_breaker_failures.get(domain, 0) >= 5

def _record_failure(url: str):
    """Record kegagalan untuk circuit breaker"""
    domain = urlparse(url).netloc
    _circuit_breaker_failures[domain] = _circuit_breaker_failures.get(domain, 0) + 1
    _circuit_breaker_last_failure[domain] = datetime.now()

def _record_success(url: str):
    """Reset circuit breaker saat sukses"""
    domain = urlparse(url).netloc
    _circuit_breaker_failures[domain] = 0
    logger.debug(f"Circuit breaker reset untuk domain: {domain}")

def get_validator_stats() -> dict:
    """Dapatkan statistik validator untuk monitoring"""
    return {
        'cache_size': len(_validation_cache),
        'circuit_breaker_domains': len(_circuit_breaker_failures),
        'circuit_breaker_active': sum(1 for count in _circuit_breaker_failures.values() if count >= 5)
    }

async def validate_url_and_file(url: str) -> Tuple[bool, dict]:
    """
    Validasi URL dan file dengan caching, circuit breaker, dan exponential backoff.
    
    Returns:
        Tuple[bool, dict]: (is_valid, result_data)
    """
    # Clean URL
    url = url.strip()
    if not url:
        return False, {"error": "URL kosong"}
    
    # Check circuit breaker
    if _should_use_circuit_breaker(url):
        domain = urlparse(url).netloc
        logger.warning(f"Circuit breaker aktif untuk domain: {domain}")
        return False, {"error": "Server terlalu sering gagal. Coba lagi nanti."}
    
    # Check cache
    cache_key = _get_cache_key(url)
    if cache_key in _validation_cache:
        cached_result, cache_time = _validation_cache[cache_key]
        if _is_cache_valid(cache_time):
            logger.info(f"Cache hit untuk URL: {url[:50]}...")
            return True, cached_result
    
    # Session untuk connection reuse
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    resp = None
    last_error = None
    
    for attempt in range(DownloadConfig.MAX_RETRIES):
        try:
            resp = session.head(
                url, 
                allow_redirects=True, 
                timeout=DownloadConfig.TIMEOUT
            )
            
            if resp.status_code == 200:
                logger.info(f"Success: URL valid setelah percobaan {attempt + 1}")
                _record_success(url)  # Reset circuit breaker untuk URL yang sukses
                break  # Sukses, keluar dari loop retry
            elif resp.status_code in [503, 504, 429] and attempt < DownloadConfig.MAX_RETRIES - 1:
                # Server busy, coba lagi dengan delay
                _record_failure(url)
                delay = (2 ** attempt) * DownloadConfig.RETRY_DELAY_MULTIPLIER
                logger.warning(f"Server busy (status {resp.status_code}) percobaan {attempt + 1}, menunggu {delay}s...")
                await asyncio.sleep(delay)
                continue
            else:
                # Status error lain, langsung return error
                error_msg = f"URL tidak dapat diakses. Status: {resp.status_code}"
                _record_failure(url)
                return False, {"error": error_msg}
                
        except requests.Timeout:
            last_error = ErrorMessages.TIMEOUT_ERROR
            _record_failure(url)
            if attempt < DownloadConfig.MAX_RETRIES - 1:
                # Exponential backoff: 2^attempt * base_delay seconds
                delay = (2 ** attempt) * DownloadConfig.RETRY_DELAY_MULTIPLIER
                logger.warning(f"Timeout percobaan {attempt + 1}, menunggu {delay}s sebelum retry...")
                await asyncio.sleep(delay)
                continue
            else:
                return False, last_error
                
        except requests.ConnectionError:
            last_error = ErrorMessages.CONNECTION_ERROR
            _record_failure(url)
            if attempt < DownloadConfig.MAX_RETRIES - 1:
                # Exponential backoff untuk connection error
                delay = (2 ** attempt) * DownloadConfig.RETRY_DELAY_MULTIPLIER
                logger.warning(f"Connection error percobaan {attempt + 1}, menunggu {delay}s sebelum retry...")
                await asyncio.sleep(delay)
                continue
            else:
                return False, last_error
        
        except Exception as e:
            last_error = f"{ErrorMessages.UNKNOWN_ERROR}: {str(e)}"
            _record_failure(url)
            if attempt < DownloadConfig.MAX_RETRIES - 1:
                # Exponential backoff untuk error umum
                delay = (2 ** attempt) * DownloadConfig.RETRY_DELAY_MULTIPLIER
                logger.warning(f"Error percobaan {attempt + 1}, menunggu {delay}s sebelum retry...")
                await asyncio.sleep(delay)
                continue
            else:
                return False, last_error
    
    # Cleanup session
    try:
        session.close()
    except:
        pass
    
    # Jika tidak ada response yang valid setelah semua retry
    if not resp or resp.status_code != 200:
        error_msg = last_error or f"Gagal validasi URL setelah {DownloadConfig.MAX_RETRIES} percobaan"
        return False, {"error": error_msg}
    
    # Proses response yang valid
    content_type = resp.headers.get('Content-Type', '')
    content_length = resp.headers.get('Content-Length', None)
    
    # Validasi konten berdasarkan header
    if content_length:
        try:
            file_size = int(content_length)
            if file_size > GoogleDriveConfig.MAX_FILE_SIZE_BYTES:
                max_size_formatted = format_bytes(GoogleDriveConfig.MAX_FILE_SIZE_BYTES)
                return False, {"error": f"File terlalu besar. Maksimal: {max_size_formatted}"}
            if file_size == 0:
                return False, {"error": "File kosong (0 bytes)"}
        except ValueError:
            return False, {"error": "Ukuran file tidak valid"}
    
    # Validasi tipe konten
    if content_type and not any(valid_type in content_type.lower() for valid_type in ['application/', 'video/', 'audio/', 'image/', 'text/']):
        # Cek apakah ini file yang valid (bukan halaman web)
        if 'text/html' in content_type.lower():
            return False, {"error": "URL mengarah ke halaman web, bukan file download"}
    
    # Ekstrak nama file dari URL dengan membersihkan parameter
    parsed_url = urlparse(url)
    filename = unquote(parsed_url.path.split('/')[-1])
    
    # Jika nama file kosong atau tidak valid, buat nama default
    if not filename or '.' not in filename:
        # Coba dapatkan nama dari Content-Disposition header
        content_disp = resp.headers.get('Content-Disposition', '')
        if 'filename=' in content_disp:
            try:
                filename = content_disp.split('filename=')[-1].strip('"\'')
            except:
                pass
        
        # Jika masih tidak ada nama file, buat nama default
        if not filename:
            ext = mimetypes.guess_extension(content_type.split(';')[0].strip()) if content_type else '.bin'
            filename = f"download{ext or '.unknown'}"
        
        # Jika masih tidak ada nama file, buat default berdasarkan tipe
        if not filename or '.' not in filename:
            ext = mimetypes.guess_extension(content_type.split(';')[0].strip()) or '.bin'
            filename = f"downloaded_file{ext}"
    
    # Perbaiki tipe konten jika generic
    if content_type == 'application/octet-stream' or not content_type:
        # Tebak tipe dari ekstensi file
        guessed_type, _ = mimetypes.guess_type(filename)
        if guessed_type:
            content_type = guessed_type
        else:
            content_type = 'application/octet-stream'
    
    # Validasi ukuran file
    if not content_length:
        return False, {"error": "Tidak dapat mengetahui ukuran file"}
    
    try:
        size = int(content_length)
        if size > GoogleDriveConfig.MAX_FILE_SIZE_BYTES:
            max_size_formatted = format_bytes(GoogleDriveConfig.MAX_FILE_SIZE_BYTES)
            return False, {"error": f"Ukuran file melebihi {max_size_formatted}"}
        if size == 0:
            return False, {"error": "File kosong (0 bytes)"}
    except ValueError:
        return False, {"error": "Ukuran file tidak valid"}
    
    # Buat hasil validasi
    result = {
        'filename': filename, 
        'size': size, 
        'type': content_type,
        'url': url  # Simpan URL asli untuk reference
    }
    
    # Simpan ke cache untuk optimasi berikutnya
    cache_key = _get_cache_key(url)
    _validation_cache[cache_key] = (result, datetime.now())
    logger.info(f"Validasi sukses untuk URL: {url[:50]}... | File: {filename} | Size: {format_bytes(size)}")
    
    # Record success untuk circuit breaker
    _record_success(url)
    
    return True, result