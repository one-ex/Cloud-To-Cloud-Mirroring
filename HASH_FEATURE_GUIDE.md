# Contoh Penggunaan Fitur Hash SourceForge

## Cara Kerja Fitur Hash

Setelah modifikasi, aplikasi Telegram bot Anda sekarang memiliki kemampuan untuk:

1. **Mendapatkan informasi hash** dari file SourceForge sebelum mendownload
2. **Menampilkan hash** kepada user dalam pesan konfirmasi
3. **Verifikasi hash** secara otomatis selama proses download/upload
4. **Memberikan laporan** hasil verifikasi setelah selesai

## Contoh URL SourceForge yang Didukung

Bot akan otomatis mendeteksi dan mendapatkan hash untuk URL seperti:

```
https://sourceforge.net/projects/project-name/files/filename.zip/download
https://sourceforge.net/projects/libreoffice/stable/7.4.3/x86_64/LibreOffice_7.4.3_Linux_x86-64_deb.tar.gz/download
https://sourceforge.net/projects/audacity/files/audacity/3.2.4/audacity-macos-3.2.4.dmg/download
```

## Contoh Output

**Sebelum download (informasi hash ditampilkan):**
```
File: LibreOffice_7.4.3_Linux_x86-64_deb.tar.gz
Ukuran: 234.5 MB
Tipe: application/x-gzip
Hash: MD5: a1b2c3d4...e5f6g7h8, SHA1: i9j0k1l2...m3n4o5p6, SHA256: q7r8s9t0...u1v2w3x4
Lanjutkan mirroring?
```

**Setelah download (hasil verifikasi):**
```
Berhasil mirror ke Google Drive! File ID: 1a2B3c4D5e6F7g8H9i0J
✅ Semua hash valid (md5, sha1, sha256)
```

atau jika ada hash yang tidak valid:

```
Berhasil mirror ke Google Drive! File ID: 1a2B3c4D5e6F7g8H9i0J
⚠️ Verifikasi hash: 2 valid, 1 invalid
```

## Testing

Untuk testing, Anda bisa menggunakan URL SourceForge yang valid:

```bash
# Contoh dengan file yang memiliki hash
https://sourceforge.net/projects/sevenzip/files/7-Zip/22.01/7z2201.exe/download

# Kirim URL ini ke bot Anda
```

## Keuntungan Fitur Ini

1. **Keamanan**: Memastikan file yang didownload tidak mengalami korupsi
2. **Integritas**: Memverifikasi bahwa file tidak dimodifikasi
3. **Transparansi**: User mendapat informasi hash sebelum memutuskan untuk download
4. **Otomatis**: Semua proses terjadi secara otomatis tanpa intervensi user