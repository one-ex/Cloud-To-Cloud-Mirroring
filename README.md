# Cloud Mirror Bot

Bot Telegram untuk mirror file dari berbagai sumber cloud ke Google Drive secara langsung (cloud-to-cloud).

## Fitur

- ✅ Mirror file dari SourceForge, MediaFire, PixelDrain ke Google Drive
- ✅ Proses cloud-to-cloud (tidak melalui perangkat lokal)
- ✅ Support file besar dengan resume capability
- ✅ Notifikasi real-time via Telegram
- ✅ Free tier friendly (Render + Google Drive free tier)
- ✅ Simple setup dengan environment variables

## Prasyarat

1. **Akun Telegram** dengan akses ke @BotFather
2. **Akun Google Cloud** dengan Google Drive API enabled
3. **Akun Render** untuk deployment

## Setup Langkah demi Langkah

### 1. Buat Bot Telegram

1. Buka Telegram dan cari @BotFather
2. Kirim `/newbot`
3. Ikuti instruksi untuk:
   - Beri nama bot (contoh: "Cloud Mirror Bot")
   - Beri username (contoh: "cloud_mirror_bot")
4. Simpan token yang diberikan (format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Setup Google Drive API

#### **Opsi A: Service Account (Recommended untuk Render)**

1. Buka [Google Cloud Console](https://console.cloud.google.com/)
2. Buat project baru atau pilih existing project
3. Enable **Google Drive API**
4. Buat Service Account:
   - IAM & Admin → Service Accounts → Create Service Account
   - Beri nama (contoh: "cloud-mirror-bot")
   - Role: "Editor" atau "Owner"
   - Create key → JSON format → Download
5. Konversi file JSON ke environment variable:
   ```bash
   python scripts/convert_service_account_to_env.py
   ```
6. Copy output dan paste ke environment variable `GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON` di Render

#### **Opsi B: OAuth 2.0 Credentials (Alternative)**

1. Buka [Google Cloud Console](https://console.cloud.google.com/)
2. Buat project baru atau pilih existing project
3. Enable **Google Drive API**
4. Buat OAuth 2.0 credentials:
   - Application type: "Desktop app"
   - Download credentials JSON (simpan sebagai `client_secrets.json`)
5. Dapatkan refresh token:
   ```bash
   python scripts/get_refresh_token.py
   ```

### 3. Konfigurasi Environment

1. Copy file `.env.example` ke `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` dengan informasi Anda:

   **Untuk Service Account (Opsi A):**
   ```env
   # Telegram Bot Configuration
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   TELEGRAM_WEBHOOK_SECRET=your_webhook_secret_here
   
   # Google Drive Configuration (Service Account)
   GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON={"type": "service_account","project_id": "your-project-id",...}
   GOOGLE_DRIVE_FOLDER_ID=your_google_drive_folder_id_here
   
   # Application Configuration
   APP_URL=https://your-render-app.onrender.com
   MAX_FILE_SIZE_MB=2048
   ```

   **Untuk OAuth 2.0 (Opsi B):**
   ```env
   # Telegram Bot Configuration
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   TELEGRAM_WEBHOOK_SECRET=your_webhook_secret_here
   
   # Google Drive Configuration (OAuth 2.0)
   GOOGLE_DRIVE_CLIENT_ID=your_google_client_id_here
   GOOGLE_DRIVE_CLIENT_SECRET=your_google_client_secret_here
   GOOGLE_DRIVE_REFRESH_TOKEN=your_google_refresh_token_here
   GOOGLE_DRIVE_FOLDER_ID=your_google_drive_folder_id_here
   
   # Application Configuration
   APP_URL=https://your-render-app.onrender.com
   MAX_FILE_SIZE_MB=2048
   ```

### 4. Deployment ke Render

1. Push code ke GitHub repository
2. Login ke [Render Dashboard](https://dashboard.render.com/)
3. Klik "New +" → "Web Service"
4. Connect GitHub repository
5. Render akan otomatis detect `render.yaml`
6. Klik "Create Web Service"

### 5. Beri Akses Folder Google Drive ke Service Account

Jika menggunakan Service Account (Opsi A), Anda perlu share folder dengan email Service Account:

1. Buka Google Drive
2. Pilih folder tujuan (atau buat folder baru)
3. Klik kanan → "Share"
4. Masukkan email Service Account: `mirror-bot-485421@appspot.gserviceaccount.com`
5. Set permission: "Editor"
6. Copy Folder ID dari URL:
   - Format: `https://drive.google.com/drive/folders/FOLDER_ID`
   - Contoh: Folder ID = `1AbCdEfGhIjKlMnOpQrStUvWxYz`

### 6. Setup Webhook Telegram

Setelah deployment selesai, setup webhook:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-render-app.onrender.com/webhook", "secret_token": "your_webhook_secret"}'
```

## Troubleshooting

### Error Build di Render

Jika terjadi error saat build di Render seperti:
```
error: failed to create directory `/usr/local/cargo/registry/cache/index.crates.io-...`
Caused by: Read-only file system (os error 30)
```

Ini disebabkan karena beberapa versi `pydantic` memerlukan toolchain Rust untuk kompilasi, yang tidak tersedia di lingkungan Render. Solusi:

1. **Environment Variable PYTHON_VERSION**: Atur environment variable `PYTHON_VERSION` di Render Dashboard dengan nilai `3.9.0`

2. **Update requirements.txt**: Pastikan requirements.txt berisi:
    ```txt
    fastapi==0.104.1
    uvicorn[standard]==0.24.0
    python-telegram-bot==20.6
    google-api-python-client==2.108.0
    google-auth-httplib2==0.1.1
    google-auth-oauthlib==1.1.0
    requests==2.31.0
    python-multipart==0.0.6
    python-dotenv==1.0.0
    cloudscraper==1.2.71
    beautifulsoup4==4.12.2
    pydantic==1.10.13
    httpx==0.25.1
    gunicorn==23.0.0
    ```
    Versi 1.10.13 tidak memerlukan pydantic-core dan menggunakan binary wheel yang tidak memerlukan Rust toolchain.

3. **Deploy ulang**: Setelah perubahan di-push ke GitHub, Render akan otomatis redeploy.

### Error "gunicorn: command not found"

Jika terjadi error saat start di Render:
```
bash: line 1: gunicorn: command not found
```

Pastikan `gunicorn==23.0.0` sudah ditambahkan ke requirements.txt dan build ulang.

### Error Lainnya

- **ModuleNotFoundError**: Pastikan semua dependencies terdaftar di requirements.txt
- **Environment variables missing**: Pastikan semua environment variables diatur di Render Dashboard
- **Port binding error**: Render menggunakan environment variable `PORT`, pastikan aplikasi menggunakan `os.getenv('PORT', '8000')`

## Penggunaan

### Via Telegram Bot

1. Cari username bot Anda di Telegram
2. Kirim `/start` untuk memulai
3. Kirim URL file yang ingin di-mirror
   - Contoh: `https://sourceforge.net/projects/...`
   - Contoh: `https://www.mediafire.com/...`
   - Contoh: `https://pixeldrain.com/u/...`

4. Bot akan memproses dan mengirim notifikasi ketika selesai

### Perintah yang Tersedia

- `/start` - Memulai bot dan melihat panduan
- `/help` - Menampilkan bantuan
- `/status` - Mengecek status sistem dan quota Google Drive



## Struktur Proyek

```
cloud-mirror-bot/
├── main.py              # FastAPI application
├── config.py            # Configuration settings
├── telegram_bot.py      # Telegram bot handler
├── downloader.py        # Cloud downloader
├── drive_manager.py     # Google Drive manager
├── requirements.txt     # Python dependencies
├── render.yaml          # Render deployment config
├── .env.example         # Environment template
├── README.md           # Documentation
└── scripts/            # Utility scripts
    └── get_refresh_token.py
```

## Troubleshooting

### Bot tidak merespon

1. Cek status webhook:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
   ```

2. Cek logs di Render dashboard

3. Verifikasi environment variables

### Upload ke Google Drive gagal

1. Cek refresh token masih valid
2. Cek quota Google Drive
3. Cek folder ID (default: "root")

### Download dari SourceForge/MediaFire gagal

1. URL mungkin memerlukan scraping khusus
2. Coba URL langsung ke file jika memungkinkan
3. File mungkin terlalu besar (>2GB)

## Biaya dan Limits

### Render Free Tier
- 750 hours/month (cukup untuk 24/7)
- 512 MB RAM
- Shared CPU
- Bandwidth included

### Google Drive Free Tier
- 15GB storage gratis
- Unlimited bandwidth untuk download/upload
- Rate limits apply

### Perkiraan Biaya

- **Render:** $0/month (free tier)
- **Google Drive:** $0/month (15GB free)
- **Total:** **GRATIS** untuk pemakaian ringan

## Kontribusi

1. Fork repository
2. Buat feature branch
3. Commit changes
4. Push ke branch
5. Buat Pull Request

## License

MIT License - lihat [LICENSE](LICENSE) file untuk detail.