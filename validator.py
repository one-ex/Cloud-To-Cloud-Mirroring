# Validasi URL dan file

import requests # type: ignore
import mimetypes
from urllib.parse import urlparse, unquote
from config import DownloadConfig, ErrorMessages, GoogleDriveConfig

async def validate_url_and_file(url):
    # Implementasi retry mechanism untuk validasi URL
    resp = None
    
    for attempt in range(DownloadConfig.MAX_RETRIES):
        try:
            resp = requests.head(
                url, 
                allow_redirects=True, 
                timeout=DownloadConfig.TIMEOUT
            )
            
            if resp.status_code == 200:
                break  # Sukses, keluar dari loop retry
            elif resp.status_code in [503, 504, 429] and attempt < DownloadConfig.MAX_RETRIES - 1:
                # Server busy, coba lagi dengan delay
                continue
            else:
                # Status error lain, langsung return error
                return False, f"URL tidak dapat diakses. Status: {resp.status_code}"
                
        except requests.Timeout:
            if attempt < DownloadConfig.MAX_RETRIES - 1:
                continue
            else:
                return False, ErrorMessages.TIMEOUT_ERROR
                
        except requests.ConnectionError:
            if attempt < DownloadConfig.MAX_RETRIES - 1:
                continue
            else:
                return False, ErrorMessages.CONNECTION_ERROR
        
        except Exception as e:
            if attempt < DownloadConfig.MAX_RETRIES - 1:
                continue
            else:
                return False, f"{ErrorMessages.UNKNOWN_ERROR}: {str(e)}"
    
    # Jika tidak ada response yang valid setelah semua retry
    if not resp or resp.status_code != 200:
        return False, f"Gagal validasi URL setelah {DownloadConfig.MAX_RETRIES} percobaan"
    
    # Proses response yang valid
    content_type = resp.headers.get('Content-Type', '')
    content_length = resp.headers.get('Content-Length', None)
    
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
    
    if not content_length:
        return False, "Tidak dapat mengetahui ukuran file."
    
    size = int(content_length)
    if size > GoogleDriveConfig.MAX_FILE_SIZE_BYTES:
        max_size_gb = GoogleDriveConfig.MAX_FILE_SIZE_BYTES / (1024 * 1024 * 1024)
        return False, f"Ukuran file melebihi {max_size_gb}GB."
    
    return True, {'filename': filename, 'size': size, 'type': content_type}