# Validasi URL dan file

import requests # type: ignore

async def validate_url_and_file(url):
    try:
        resp = requests.head(url, allow_redirects=True)
        if resp.status_code != 200:
            return False, "URL tidak dapat diakses."
        content_type = resp.headers.get('Content-Type', '')
        content_length = resp.headers.get('Content-Length', None)
        filename = url.split('/')[-1]
        if not content_length:
            return False, "Tidak dapat mengetahui ukuran file."
        size = int(content_length)
        if size > 7 * 1024 * 1024 * 1024:
            return False, "Ukuran file melebihi 7GB."
        return True, {'filename': filename, 'size': size, 'type': content_type}
    except Exception as e:
        return False, str(e)