# Validasi URL dan file

import requests # type: ignore
import mimetypes
from urllib.parse import urlparse, unquote

async def validate_url_and_file(url):
    try:
        resp = requests.head(url, allow_redirects=True)
        if resp.status_code != 200:
            return False, "URL tidak dapat diakses."
        
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
        if size > 7 * 1024 * 1024 * 1024:
            return False, "Ukuran file melebihi 7GB."
        
        return True, {'filename': filename, 'size': size, 'type': content_type}
    
    except Exception as e:
        return False, str(e)