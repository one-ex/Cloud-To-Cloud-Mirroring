# Download streaming dengan chunking 5MB dan upload ke Google Drive

import requests # type: ignore
import logging
import time
from drive_uploader import resumable_upload
from utils import format_bytes, format_time, format_speed, calculate_eta
from validator import verify_file_hash
import hashlib

logger = logging.getLogger(__name__)
CHUNK_SIZE = 10 * 1024 * 1024  

async def stream_download_to_drive(url, info, progress_callback=None, cancellation_event=None):
    """
    Download streaming dengan chunking 5MB dan upload ke Google Drive
    cancellation_event: asyncio.Event untuk cancellation
    """
    import asyncio
    try:
        logger.info(f"Memulai stream download dari {url}")
        resp = requests.get(url, stream=True, allow_redirects=True)
        if resp.status_code != 200:
            error_msg = f"Gagal mengunduh file. Status: {resp.status_code}"
            logger.error(error_msg)
            if progress_callback:
                await progress_callback(0, error=error_msg)
            return error_msg

        filename = info.get('filename') or url.rstrip('/').split('/')[-1].split('?')[0]
        size = info.get('size') 
        mime_type = info.get('type', 'application/octet-stream')
        
        if not filename:
            error_msg = "Gagal mendapatkan nama file dari URL."
            logger.error(error_msg)
            if progress_callback:
                await progress_callback(0, error=error_msg)
            return error_msg
        
        session = resumable_upload.init_session(filename, mime_type, size)
        
        sent_bytes = 0
        last_percent_reported = 0
        final_response = None
        start_time = time.time()
        speed_samples = []
        
        # Siapkan hash calculators jika hash info tersedia
        hash_calculators = {}
        if 'hash' in info and info['hash']:
            if 'md5' in info['hash']:
                hash_calculators['md5'] = hashlib.md5()
            if 'sha1' in info['hash']:
                hash_calculators['sha1'] = hashlib.sha1()
            if 'sha256' in info['hash']:
                hash_calculators['sha256'] = hashlib.sha256()
        
        for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
            # Cek apakah proses dibatalkan (async-safe)
            if cancellation_event and cancellation_event.is_set():
                logger.info("Proses dibatalkan oleh user - cancellation event detected")
                if progress_callback:
                    await progress_callback(0, cancelled=True, message="Proses dihentikan oleh user")
                return "Proses dihentikan oleh user"
            
            # Small delay untuk allow cancellation check
            await asyncio.sleep(0.001)
            
            if chunk:
                chunk_start_time = time.time()
                
                # Update hash calculators jika tersedia
                for hash_name, hash_calc in hash_calculators.items():
                    hash_calc.update(chunk)
                
                success, result = resumable_upload.upload_chunk(session, chunk)
                chunk_end_time = time.time()
                
                if not success:
                    error_msg = f"Gagal upload chunk ke Google Drive: {result}"
                    logger.error(error_msg)
                    if progress_callback:
                        await progress_callback(0, error=error_msg)
                    return error_msg
                
                if result:
                    final_response = result

                sent_bytes += len(chunk)
                
                # Calculate speed
                chunk_time = chunk_end_time - chunk_start_time
                if chunk_time > 0:
                    chunk_speed = len(chunk) / chunk_time
                    speed_samples.append(chunk_speed)
                    if len(speed_samples) > 10:
                        speed_samples.pop(0)
                
                avg_speed = sum(speed_samples) / len(speed_samples) if speed_samples else 0
                elapsed_time = time.time() - start_time
                eta_seconds = calculate_eta(sent_bytes, size, avg_speed) if size and avg_speed > 0 else None
                
                if size and size > 0:
                    percent = int((sent_bytes / size) * 100)
                    if percent >= last_percent_reported + 1 or percent == 100:
                        last_percent_reported = percent
                        logger.info(f"Progress: {percent}%")
                        if progress_callback:
                            await progress_callback(
                                percent,
                                downloaded=sent_bytes,
                                total=size,
                                speed=avg_speed,
                                eta=eta_seconds,
                                elapsed=elapsed_time,
                                filename=filename
                            )
        
        if progress_callback:
            await progress_callback(100, done=True)
        
        file_id = final_response.get('id') if final_response else "Unknown"
        
        # Lakukan verifikasi hash jika tersedia
        hash_status = ""
        if hash_calculators:
            logger.info("Memulai verifikasi hash file...")
            
            # Bandingkan hash yang dihitung dengan hash yang diharapkan
            hash_verification = {}
            for hash_type, hash_calc in hash_calculators.items():
                calculated_hash = hash_calc.hexdigest()
                expected_hash = info['hash'][hash_type].lower()
                
                hash_verification[hash_type] = {
                    'status': 'valid' if calculated_hash == expected_hash else 'invalid',
                    'calculated': calculated_hash,
                    'expected': expected_hash
                }
            
            if hash_verification:
                valid_hashes = [h for h, result in hash_verification.items() if result['status'] == 'valid']
                invalid_hashes = [h for h, result in hash_verification.items() if result['status'] == 'invalid']
                
                if valid_hashes:
                    logger.info(f"Hash tervalidasi: {', '.join(valid_hashes)}")
                if invalid_hashes:
                    logger.warning(f"Hash tidak valid: {', '.join(invalid_hashes)}")
                    hash_status = f"⚠️ Verifikasi hash: {len(valid_hashes)} valid, {len(invalid_hashes)} invalid"
                else:
                    hash_status = f"✅ Semua hash valid ({', '.join(valid_hashes)})"
            else:
                hash_status = "⚠️ Gagal melakukan verifikasi hash"
                logger.warning("Gagal melakukan verifikasi hash")
        
        # Siapkan pesan sukses dengan informasi hash
        success_msg = f"Berhasil mirror ke Google Drive! File ID: {file_id}"
        if hash_status:
            success_msg += f"\n{hash_status}"
            
        logger.info(success_msg)
        return success_msg

    except Exception as e:
        error_msg = f"Error selama proses stream: {e}"
        logger.exception(error_msg)
        if progress_callback:
            await progress_callback(0, error=str(e))
        return error_msg