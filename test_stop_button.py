#!/usr/bin/env python3
"""
Test script untuk verifikasi tombol Stop berfungsi
"""

import requests
import json
import time

def test_stop_button_flow():
    """Test apakah tombol stop bisa menghentikan proses"""
    
    print("🧪 Testing Stop Button Flow")
    print("=" * 50)
    
    # Test 1: Kirim URL untuk dimirror
    token = '8396168294:AAG61kS5vdlU0lNaHSJEE3DDU8xhyV4Uy5g'
    chat_id = '123456789'  # Ganti dengan chat ID Anda
    
    # URL test (file kecil untuk test cepat)
    test_url = "https://sample-videos.com/zip/10mb.zip"
    
    # Kirim pesan ke bot (simulasi)
    send_message_url = f"https://api.telegram.org/bot{token}/sendMessage"
    message_data = {
        "chat_id": chat_id,
        "text": test_url
    }
    
    try:
        # Cek webhook info dulu
        webhook_info_url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
        response = requests.get(webhook_info_url)
        webhook_data = response.json()
        
        if webhook_data.get('ok'):
            info = webhook_data['result']
            print(f"📡 Webhook Status Check:")
            print(f"   URL: {info.get('url', 'None')}")
            print(f"   Pending Updates: {info.get('pending_update_count', 0)}")
            print(f"   Last Sync: {info.get('last_synchronization_error_date', 'None')}")
            
            if info.get('pending_update_count', 0) > 0:
                print("   ⚠️  Ada update tertunda!")
            else:
                print("   ✅ Tidak ada update tertunda")
        
        print(f"\n📝 Test Instructions:")
        print(f"   1. Kirim URL ke bot: {test_url}")
        print(f"   2. Tunggu sampai proses mirroring dimulai")
        print(f"   3. Klik tombol '⏹ Stop Mirroring'")
        print(f"   4. Cek apakah proses berhenti")
        
        print(f"\n🔍 Monitoring Steps:")
        print(f"   - Cek logs di Render.com")
        print(f"   - Cek apakah muncul 'Proses dibatalkan oleh user'")
        print(f"   - Cek apakah bot membalas 'Proses mirroring dihentikan...'")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_recent_errors():
    """Cek apakah ada error baru di webhook"""
    token = '8396168294:AAG61kS5vdlU0lNaHSJEE3DDU8xhyV4Uy5g'
    url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get('ok'):
            info = data['result']
            
            print(f"\n🔍 Recent Error Check:")
            
            if 'last_error_date' in info:
                from datetime import datetime
                error_time = datetime.fromtimestamp(info['last_error_date'])
                print(f"   Last Error Time: {error_time}")
                print(f"   Error Message: {info.get('last_error_message', 'Unknown')}")
                
                # Cek apakah error baru (dalam 5 menit terakhir)
                current_time = datetime.now()
                time_diff = (current_time - error_time).total_seconds() / 60
                
                if time_diff < 5:
                    print(f"   ⚠️  Error BARU terdeteksi ({time_diff:.1f} menit lalu)")
                    return False
                else:
                    print(f"   ✅ Error lama ({time_diff:.1f} menit lalu)")
                    return True
            else:
                print("   ✅ Tidak ada error terdeteksi")
                return True
                
    except Exception as e:
        print(f"❌ Gagal cek error: {e}")
        return False

def main():
    print("🚀 Stop Button Functionality Test")
    print("=" * 60)
    
    # Cek status webhook
    success = test_stop_button_flow()
    
    if success:
        # Cek recent errors
        check_recent_errors()
        
        print(f"\n📝 Manual Test Steps:")
        print(f"1. Buka Telegram dan cari bot: @ex_mirror_bot")
        print(f"2. Kirim URL: https://sample-videos.com/zip/10mb.zip")
        print(f"3. Ketik 'Ya' untuk konfirmasi")
        print(f"4. Klik tombol '⏹ Stop Mirroring' saat proses berjalan")
        print(f"5. Cek apakah proses berhenti dan bot membalas pesan")
        
        print(f"\n📊 Expected Results:")
        print(f"✅ Bot membalas: 'Proses mirroring dihentikan...'")
        print(f"✅ Logs muncul: 'Proses dibatalkan oleh user'")
        print(f"✅ File tidak selesai di-upload ke Drive")
        
        print(f"\n🔧 Jika Tombol Stop TIDAK Berfungsi:")
        print(f"1. Cek logs di Render.com untuk error")
        print(f"2. Pastikan asyncio.Event() digunakan dengan benar")
        print(f"3. Cek apakah cancellation_event.set() dipanggil")
        print(f"4. Cek apakah await asyncio.sleep(0.001) ada di loop")
        
    else:
        print("❌ Webhook test gagal")

if __name__ == "__main__":
    main()