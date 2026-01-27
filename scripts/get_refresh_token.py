#!/usr/bin/env python3
"""
Script untuk mendapatkan Google Drive refresh token.

Langkah-langkah:
1. Buat OAuth 2.0 credentials di Google Cloud Console
2. Download credentials JSON
3. Jalankan script ini
4. Ikuti instruksi di browser
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Scope untuk Google Drive API
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',  # Akses ke file yang dibuat/diakses oleh app
    'https://www.googleapis.com/auth/drive.metadata.readonly',  # Read metadata
]


def get_refresh_token():
    """Dapatkan refresh token untuk Google Drive API"""
    creds = None
    
    # File untuk menyimpan token
    token_file = 'token.json'
    
    # Load existing token jika ada
    if os.path.exists(token_file):
        with open(token_file, 'r') as f:
            creds_data = json.load(f)
            creds = Credentials(
                token=creds_data.get('token'),
                refresh_token=creds_data.get('refresh_token'),
                token_uri=creds_data.get('token_uri'),
                client_id=creds_data.get('client_id'),
                client_secret=creds_data.get('client_secret'),
                scopes=creds_data.get('scopes')
            )
    
    # Jika tidak ada credentials valid, buat yang baru
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Load client secrets
            client_secrets_file = 'client_secrets.json'
            
            if not os.path.exists(client_secrets_file):
                print("\n❌ File 'client_secrets.json' tidak ditemukan!")
                print("Langkah-langkah:")
                print("1. Buka https://console.cloud.google.com/")
                print("2. Buat project baru atau pilih existing")
                print("3. Enable 'Google Drive API'")
                print("4. Buat OAuth 2.0 credentials (Desktop app)")
                print("5. Download credentials JSON")
                print("6. Simpan sebagai 'client_secrets.json' di folder ini")
                return
            
            # Jalankan OAuth flow
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secrets_file,
                SCOPES
            )
            
            print("\n🔗 Membuka browser untuk autentikasi Google...")
            print("Jika browser tidak terbuka, buka link berikut secara manual:")
            
            creds = flow.run_local_server(
                port=8080,
                prompt='consent',
                authorization_prompt_message=''
            )
        
        # Simpan credentials
        creds_dict = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }
        
        with open(token_file, 'w') as f:
            json.dump(creds_dict, f, indent=2)
        
        print(f"\n✅ Token berhasil disimpan di '{token_file}'")
    
    # Tampilkan informasi
    print("\n📋 **INFORMASI CREDENTIALS:**")
    print(f"Client ID: {creds.client_id}")
    print(f"Client Secret: {creds.client_secret}")
    print(f"Refresh Token: {creds.refresh_token}")
    print(f"Scopes: {creds.scopes}")
    
    print("\n📝 **CARA MENGGUNAKAN DI .env:**")
    print(f"GOOGLE_DRIVE_CLIENT_ID={creds.client_id}")
    print(f"GOOGLE_DRIVE_CLIENT_SECRET={creds.client_secret}")
    print(f"GOOGLE_DRIVE_REFRESH_TOKEN={creds.refresh_token}")
    
    return creds


if __name__ == '__main__':
    try:
        get_refresh_token()
    except KeyboardInterrupt:
        print("\n\n❌ Dibatalkan oleh pengguna")
    except Exception as e:
        print(f"\n❌ Error: {e}")