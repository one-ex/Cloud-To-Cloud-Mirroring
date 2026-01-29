# Render Deployment Setup Guide

## Environment Variables yang Dibutuhkan

Tambahkan environment variables berikut di Render dashboard:

### Wajib:
```
TELEGRAM_TOKEN=8396168294:AAG61kS5vdlU0lNaHSJEE3DDU8xhyV4Uy5g
WEBHOOK_URL=https://cloud-to-cloud-mirroring.onrender.com
PORT=8080
```

### Optional (jika Google Drive digunakan):
```
GOOGLE_APPLICATION_CREDENTIALS=mirror-bot-485421-669ab9c67658.json
DRIVE_FOLDER_ID=1zqbIiZW-pr4nWEjCwe4D7fPCUhmBkOlG
```

## Cara Setting di Render

1. **Login ke Render Dashboard**
2. **Pilih Web Service Anda**
3. **Klik Tab "Environment"**
4. **Klik "Add Environment Variable"**
5. **Masukkan Key-Value pairs di atas**

## Port Configuration

- **Port default**: 8080 (bisa diganti)
- **Render akan otomatis**: expose port ini ke internet
- **Pastikan**: aplikasi mendengar di 0.0.0.0 (bukan localhost)

## Troubleshooting Port

### Cek apakah PORT sudah ter-set:
```bash
echo $PORT
```

### Cek apakah aplikasi mendengar:
```bash
netstat -tulpn | grep :8080
```

### Test koneksi lokal:
```bash
curl http://localhost:8080
```

## Important Notes

1. **PORT wajib di-set** agar webhook bisa menerima request
2. **Gunakan 0.0.0.0** bukan 127.0.0.1 atau localhost
3. **Render akan otomatis** handle SSL/https
4. **Webhook URL** harus https untuk Telegram