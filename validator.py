import requests
import os
from urllib.parse import urlparse

async def validate_url_and_file(url):
    """
    Validasi URL dan ambil info file (Nama, Size, Type).
    Mendukung bypass 403 dan logika penamaan file yang akurat.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Referer': 'https://sourceforge.net/'
        }

        # Gunakan GET stream agar tidak terkena 403 Forbidden
        resp = requests.get(url, headers=headers, stream=True, allow_redirects=True, timeout=15)
        
        if resp.status_code != 200:
            return False, f"URL tidak dapat diakses (Status: {resp.status_code})"

        content_type = resp.headers.get('Content-Type', 'application/octet-stream')
        content_length = resp.headers.get('Content-Length')

        # LOGIKA NAMA FILE
        filename = None
        
        # 1. Cek Content-Disposition (Tanpa modul cgi)
        cd = resp.headers.get('Content-Disposition')
        if cd and 'filename=' in cd:
            filename = cd.split('filename=')[-1].strip('"; ')

        # 2. Fallback: Logika urlparse + basename (Logika Anda)
        if not filename:
            final_url = resp.url.strip('/')
            path = urlparse(final_url).path
            filename = os.path.basename(path)

        if not filename:
            filename = "file_unduhan"

        if not content_length:
            return False, "Server tidak mengirimkan ukuran file (Content-Length)."
            
        size = int(content_length)
        if size > 7 * 1024 * 1024 * 1024:
            return False, "Ukuran file terlalu besar (Maksimal 7GB)."

        resp.close()
        return True, {'filename': filename, 'size': size, 'type': content_type}

    except Exception as e:
        return False, f"Error validasi: {str(e)}"
