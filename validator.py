# Validasi URL dan file

import requests # type: ignore
import mimetypes
import re
import hashlib
from urllib.parse import urlparse, unquote

def get_sourceforge_hash_info(url):
    """
    Mendapatkan informasi hash dari SourceForge untuk file yang akan didownload.
    Mengembalikan dict dengan hash MD5, SHA1, SHA256 jika tersedia.
    """
    try:
        # Parse URL SourceForge
        parsed = urlparse(url)
        
        # Pattern URL SourceForge: https://sourceforge.net/projects/PROJECT/files/FILENAME/download
        if 'sourceforge.net' not in parsed.netloc:
            return None
            
        # Ekstrak project name dan file path dari URL
        path_parts = parsed.path.split('/')
        if len(path_parts) < 4 or path_parts[1] != 'projects':
            return None
            
        project_name = path_parts[2]
        file_path = '/'.join(path_parts[3:-1])  # Exclude 'download' at the end
        
        # Construct hash URL
        # Contoh: https://sourceforge.net/projects/PROJECT/files/FILENAME.md5
        hash_url = f"https://sourceforge.net/projects/{project_name}/files/{file_path}.md5"
        
        # Coba dapatkan MD5 hash
        hash_info = {}
        
        # Request MD5 hash
        try:
            md5_resp = requests.get(hash_url, timeout=10)
            if md5_resp.status_code == 200:
                md5_content = md5_resp.text.strip()
                # MD5 hash biasanya format: "hash  filename"
                if ' ' in md5_content:
                    md5_hash = md5_content.split()[0]
                    if len(md5_hash) == 32 and re.match(r'^[a-fA-F0-9]{32}$', md5_hash):
                        hash_info['md5'] = md5_hash.lower()
        except:
            pass
            
        # Coba SHA1 hash
        sha1_url = f"https://sourceforge.net/projects/{project_name}/files/{file_path}.sha1"
        try:
            sha1_resp = requests.get(sha1_url, timeout=10)
            if sha1_resp.status_code == 200:
                sha1_content = sha1_resp.text.strip()
                if ' ' in sha1_content:
                    sha1_hash = sha1_content.split()[0]
                    if len(sha1_hash) == 40 and re.match(r'^[a-fA-F0-9]{40}$', sha1_hash):
                        hash_info['sha1'] = sha1_hash.lower()
        except:
            pass
            
        # Coba SHA256 hash  
        sha256_url = f"https://sourceforge.net/projects/{project_name}/files/{file_path}.sha256"
        try:
            sha256_resp = requests.get(sha256_url, timeout=10)
            if sha256_resp.status_code == 200:
                sha256_content = sha256_resp.text.strip()
                if ' ' in sha256_content:
                    sha256_hash = sha256_content.split()[0]
                    if len(sha256_hash) == 64 and re.match(r'^[a-fA-F0-9]{64}$', sha256_hash):
                        hash_info['sha256'] = sha256_hash.lower()
        except:
            pass
            
        return hash_info if hash_info else None
         
    except Exception as e:
        return None

def verify_file_hash(file_path, expected_hash_info):
    """
    Memverifikasi hash file yang sudah didownload dengan hash yang diharapkan.
    Mengembalikan dict dengan status verifikasi untuk setiap tipe hash.
    """
    if not expected_hash_info:
        return None
        
    verification_result = {}
    
    try:
        # Baca file dalam chunk untuk file besar
        def calculate_hash(hash_type):
            hash_func = None
            if hash_type == 'md5':
                hash_func = hashlib.md5()
            elif hash_type == 'sha1':
                hash_func = hashlib.sha1()
            elif hash_type == 'sha256':
                hash_func = hashlib.sha256()
            else:
                return None
                
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    hash_func.update(chunk)
            return hash_func.hexdigest()
        
        # Verifikasi setiap tipe hash yang tersedia
        for hash_type in ['md5', 'sha1', 'sha256']:
            if hash_type in expected_hash_info:
                calculated_hash = calculate_hash(hash_type)
                expected_hash = expected_hash_info[hash_type].lower()
                
                if calculated_hash and calculated_hash.lower() == expected_hash:
                    verification_result[hash_type] = {
                        'status': 'valid',
                        'calculated': calculated_hash,
                        'expected': expected_hash
                    }
                else:
                    verification_result[hash_type] = {
                        'status': 'invalid',
                        'calculated': calculated_hash,
                        'expected': expected_hash
                    }
                    
        return verification_result if verification_result else None
        
    except Exception as e:
        return None
 
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
        
        # Siapkan informasi file
        file_info = {
            'filename': filename, 
            'size': size, 
            'type': content_type
        }
        
        # Coba dapatkan hash info jika URL dari SourceForge
        hash_info = get_sourceforge_hash_info(url)
        if hash_info:
            file_info['hash'] = hash_info
        
        return True, file_info
    
    except Exception as e:
        return False, str(e)