import requests
import os
import cgi
from urllib.parse import urlparse

async def validate_url_and_file(url):
    """
    Memvalidasi URL, mendapatkan nama file, ukuran, dan tipe konten.
    Menggunakan kombinasi logika Header HTTP dan URL Path untuk akurasi maksimal.
    """
    try:
        # Menambahkan Header agar tidak diblokir server (Anti-403)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Referer': 'https://sourceforge.net/'
        }

        # Menggunakan GET dengan stream=True agar lebih stabil daripada HEAD
        # allow_redirects=True sangat penting untuk mendapatkan final_url
        resp = requests.get(url, headers=headers, stream=True, allow_redirects=True, timeout=15)
        
        if resp.status_code != 200:
            return False, f"URL tidak dapat diakses. Status: {resp.status_code}"

        # 1. Mendapatkan Informasi dari Header
        content_type = resp.headers.get('Content-Type', 'application/octet-stream')
        content_length = resp.headers.get('Content-Length', None)
        
        # 2. Logika Nama File - Tahap 1: Cek Content-Disposition (Header)
        filename = None
        cd = resp.headers.get('Content-Disposition')
        if cd:
            _, params = cgi.parse_header(cd)
            filename = params.get('filename')

        # 3. Logika Nama File - Tahap 2: Gunakan logika Anda (urlparse + os.path.basename)
        # Jika nama file dari header tidak ada, gunakan logika URL Path
        if not filename:
            final_url = resp.url.strip('/') # Menggunakan URL akhir setelah redirect
            path = urlparse(final_url).path
            filename = os.path.basename(path)

        # Jika masih gagal mendapatkan nama (sangat jarang terjadi)
        if not filename:
            filename = "file_unduhan"

        # 4. Validasi Ukuran File
        if not content_length:
            return False, "Tidak dapat mengetahui ukuran file. Server tidak mengirimkan Content-Length."
            
        size = int(content_length)
        
        # Batasan ukuran (Contoh: 7GB)
        if size > 7 * 1024 * 1024 * 1024:
            return False, "Ukuran file terlalu besar (Maksimal 7GB)."

        # Pastikan koneksi ditutup karena kita hanya butuh informasi headernya saja
        resp.close()

        return True, {
            'filename': filename, 
            'size': size, 
            'type': content_type
        }

    except Exception as e:
        return False, f"Terjadi kesalahan saat validasi: {str(e)}"
