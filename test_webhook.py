#!/usr/bin/env python3
"""
Test script untuk memeriksa webhook dan konektivitas bot Telegram
"""

import requests
import json
from datetime import datetime

def test_bot_token():
    """Test apakah bot token valid"""
    token = "8396168294:AAG61kS5vdlU0lNaHSJEE3DDU8xhyV4Uy5g"
    url = f"https://api.telegram.org/bot{token}/getMe"
    
    try:
        response = requests.get(url, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            bot_info = result['result']
            print(f"✅ Bot valid:")
            print(f"   - ID: {bot_info['id']}")
            print(f"   - Nama: {bot_info['first_name']}")
            print(f"   - Username: @{bot_info['username']}")
            return True
        else:
            print(f"❌ Bot tidak valid: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error test bot: {e}")
        return False

def test_webhook_info():
    """Test webhook info"""
    token = "8396168294:AAG61kS5vdlU0lNaHSJEE3DDU8xhyV4Uy5g"
    url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
    
    try:
        response = requests.get(url, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            webhook_info = result['result']
            print(f"\n📡 Webhook Info:")
            print(f"   - URL: {webhook_info.get('url', 'None')}")
            print(f"   - Pending updates: {webhook_info.get('pending_update_count', 0)}")
            print(f"   - Max connections: {webhook_info.get('max_connections', 40)}")
            print(f"   - IP Address: {webhook_info.get('ip_address', 'Unknown')}")
            
            if 'last_error_date' in webhook_info:
                error_date = datetime.fromtimestamp(webhook_info['last_error_date'])
                print(f"   - Last error: {error_date}")
                print(f"   - Error message: {webhook_info.get('last_error_message', 'Unknown')}")
            
            return webhook_info
        else:
            print(f"❌ Gagal get webhook info: {result}")
            return None
            
    except Exception as e:
        print(f"❌ Error test webhook: {e}")
        return None

def test_webhook_endpoint():
    """Test apakah webhook endpoint bisa diakses"""
    webhook_url = "https://cloud-to-cloud-mirroring.onrender.com"
    
    try:
        # Test dengan HEAD request
        response = requests.head(webhook_url, timeout=10)
        print(f"\n🌐 Webhook Endpoint Test:")
        print(f"   - Status Code: {response.status_code}")
        print(f"   - Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("   ✅ Endpoint aktif")
        elif response.status_code == 404:
            print("   ⚠️  Endpoint tidak ditemukan (404)")
        else:
            print(f"   ⚠️  Status tidak normal: {response.status_code}")
            
        return response.status_code
        
    except requests.exceptions.SSLError as e:
        print(f"❌ SSL Error: {e}")
        print("   💡 Mungkin sertifikat SSL bermasalah")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection Error: {e}")
        print("   💡 Server mungkin down atau tidak bisa diakses")
        return None
    except Exception as e:
        print(f"❌ Error lain: {e}")
        return None

def simulate_telegram_update():
    """Simulasikan update dari Telegram untuk test webhook"""
    webhook_url = "https://cloud-to-cloud-mirroring.onrender.com"
    
    # Sample Telegram update
    test_update = {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser"
            },
            "chat": {
                "id": 123456789,
                "first_name": "Test",
                "username": "testuser",
                "type": "private"
            },
            "date": 1640995200,
            "text": "/start"
        }
    }
    
    try:
        response = requests.post(
            webhook_url,
            json=test_update,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"\n📨 Telegram Update Test:")
        print(f"   - Status Code: {response.status_code}")
        print(f"   - Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            print("   ✅ Webhook menerima update dengan baik")
        else:
            print(f"   ❌ Webhook error: {response.status_code}")
            
        return response.status_code
        
    except Exception as e:
        print(f"❌ Error kirim test update: {e}")
        return None

def main():
    print("🔍 Testing Bot Telegram & Webhook")
    print("=" * 50)
    
    # Test 1: Bot Token
    bot_valid = test_bot_token()
    
    if bot_valid:
        # Test 2: Webhook Info
        webhook_info = test_webhook_info()
        
        # Test 3: Webhook Endpoint
        endpoint_status = test_webhook_endpoint()
        
        # Test 4: Simulate Telegram Update (hanya jika endpoint aktif)
        if endpoint_status and endpoint_status < 500:
            simulate_telegram_update()
    
    print("\n" + "=" * 50)
    print("✅ Testing selesai!")
    
    # Rekomendasi
    print("\n💡 Rekomendasi:")
    print("   - Jika webhook error: Cek logs di Render.com")
    print("   - Jika SSL error: Pastikan domain valid")
    print("   - Jika connection error: Cek apakah app running di Render")
    print("   - Gunakan /start command untuk test bot")

if __name__ == "__main__":
    main()