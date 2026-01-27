#!/usr/bin/env python3
"""
Script untuk mengkonversi file Service Account JSON ke format environment variable
untuk digunakan di Render.

Cara menggunakan:
1. Jalankan script: python convert_service_account_to_env.py
2. Masukkan path ke file Service Account JSON
3. Copy output dan paste ke environment variable di Render
"""

import os
import json
import sys

def convert_to_env_format(json_file_path):
    """Konversi file JSON Service Account ke format environment variable"""
    try:
        # Baca file JSON
        with open(json_file_path, 'r') as f:
            service_account_data = json.load(f)
        
        # Validasi struktur dasar
        required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 
                          'client_email', 'client_id']
        
        for field in required_fields:
            if field not in service_account_data:
                print(f"❌ Field '{field}' tidak ditemukan dalam file JSON")
                return None
        
        # Konversi ke JSON string dengan escaping yang tepat
        # Perlu escape newlines dalam private key
        service_account_data['private_key'] = service_account_data['private_key'].replace('\n', '\\n')
        
        # Konversi ke string JSON
        json_string = json.dumps(service_account_data, separators=(',', ':'))
        
        return json_string
        
    except FileNotFoundError:
        print(f"❌ File tidak ditemukan: {json_file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Format JSON tidak valid: {e}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    print("🔧 Konverter Service Account JSON ke Environment Variable\n")
    
    # Tentukan file JSON
    if len(sys.argv) > 1:
        json_file_path = sys.argv[1]
    else:
        # Default: cari file JSON di folder project
        default_files = [
            'mirror-bot-485421-669ab9c67658.json',
            'service_account.json',
            'credentials.json'
        ]
        
        json_file_path = None
        for file_name in default_files:
            if os.path.exists(file_name):
                json_file_path = file_name
                print(f"✓ File ditemukan: {file_name}")
                break
        
        if not json_file_path:
            json_file_path = input("Masukkan path ke file Service Account JSON: ").strip()
    
    # Konversi
    env_value = convert_to_env_format(json_file_path)
    
    if env_value:
        print("\n✅ KONVERSI BERHASIL!\n")
        print("📋 **COPY PASTE KE RENDER:**\n")
        
        # Tampilkan dalam format yang mudah di-copy
        print(f"GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON={env_value}\n")
        
        print("📝 **PETUNJUK PENGGUNAAN DI RENDER:**")
        print("1. Buka dashboard Render")
        print("2. Pilih aplikasi Anda")
        print("3. Klik 'Environment'")
        print("4. Tambah environment variable:")
        print("   - Key: GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON")
        print(f"   - Value: {env_value[:50]}...")
        print("5. Simpan dan redeploy")
        
        # Simpan ke file untuk referensi
        output_file = 'service_account_env.txt'
        with open(output_file, 'w') as f:
            f.write(f"GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON={env_value}")
        
        print(f"\n📄 Output juga disimpan di: {output_file}")
        
        # Tampilkan info penting
        print("\n⚠️  **CATATAN PENTING:**")
        print("1. Pastikan Service Account memiliki akses ke Google Drive folder")
        print("2. Share folder dengan email: mirror-bot-485421@appspot.gserviceaccount.com")
        print("3. Environment variable ini mengandung private key, jangan share!")
        
    else:
        print("\n❌ Konversi gagal. Periksa file JSON Anda.")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Dibatalkan oleh pengguna")
    except Exception as e:
        print(f"\n❌ Error: {e}")