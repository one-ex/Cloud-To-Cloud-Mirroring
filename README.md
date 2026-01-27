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
4. **Python 3.9+** untuk development lokal

## Setup Langkah demi Langkah

### 1. Buat Bot Telegram

1. Buka Telegram dan cari @BotFather
2. Kirim `/newbot`
3. Ikuti instruksi untuk:
   - Beri nama bot (contoh: "Cloud Mirror Bot")
   - Beri username (contoh: "cloud_mirror_bot")
4. Simpan token yang diberikan (format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Setup Google Drive API

1. Buka [Google Cloud Console](https://console.cloud.google.com/)
2. Buat project baru atau pilih existing project
3. Enable **Google Drive API**
4. Buat OAuth 2.0 credentials:
   - Application type: "Desktop app"
   - Download credentials JSON
5. Dapatkan refresh token:
   ```bash
   python scripts/get_refresh_token.py
   ```
   (Script akan disediakan)

### 3. Konfigurasi Environment

1. Copy file `.env.example` ke `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` dengan informasi Anda:
   ```env
   # Telegram Bot Configuration
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   TELEGRAM_WEBHOOK_SECRET=your_webhook_secret_here
   
   # Google Drive Configuration
   GOOGLE_DRIVE_CLIENT_ID=your_google_client_id_here
   GOOGLE_DRIVE_CLIENT_SECRET=your_google_client_secret_here
   GOOGLE_DRIVE_REFRESH_TOKEN=your_google_refresh_token_here
   GOOGLE_DRIVE_FOLDER_ID=your_google_drive_folder_id_here
   
   # Application Configuration
   APP_URL=https://your-render-app.onrender.com
   MAX_FILE_SIZE_MB=2048
   ```

### 4. Deployment ke Render

#### Metode 1: Via GitHub (Recommended)

1. Push code ke GitHub repository
2. Login ke [Render Dashboard](https://dashboard.render.com/)
3. Klik "New +" → "Web Service"
4. Connect GitHub repository
5. Render akan otomatis detect `render.yaml`
6. Klik "Create Web Service"

#### Metode 2: Manual Upload

1. Login ke [Render Dashboard](https://dashboard.render.com/)
2. Klik "New +" → "Web Service"
3. Pilih "Build and deploy from a Git repository"
4. Upload repository atau connect via Git
5. Configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
   - **Plan:** Free

### 5. Setup Webhook Telegram

Setelah deployment selesai, setup webhook:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-render-app.onrender.com/webhook", "secret_token": "your_webhook_secret"}'
```

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

## Development Lokal

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Development Server

```bash
# Copy environment file
cp .env.example .env
# Edit .env dengan konfigurasi lokal

# Run in development mode
python main.py
```

Development mode akan:
1. Run FastAPI server di `http://localhost:8000`
2. Run bot Telegram dalam polling mode
3. Enable auto-reload pada code changes

### Testing

```bash
# Test API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/status

# Test mirror via API
curl -X POST http://localhost:8000/api/mirror \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/file.zip"}'
```

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