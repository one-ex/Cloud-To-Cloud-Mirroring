#!/usr/bin/env python3
"""
Contoh penggunaan Cloud Mirror Bot.

File ini berisi contoh URL yang bisa digunakan untuk testing.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from downloader import downloader


# Contoh URL untuk testing
TEST_URLS = {
    "sourceforge": "https://sourceforge.net/projects/sevenzip/files/7-Zip/23.01/7z2301-x64.exe/download",
    "mediafire": "https://www.mediafire.com/file/2v6v3v5v6v7v8v9/test_file.zip/file",
    "pixeldrain": "https://pixeldrain.com/api/file/abc123",
    "direct": "https://example.com/sample_file.pdf",
}


async def test_download(url: str, description: str):
    """Test download dari URL"""
    print(f"\n🔍 Testing {description}...")
    print(f"URL: {url}")
    
    try:
        result = await downloader.download_file(url)
        
        if result['success']:
            print(f"✅ Success!")
            print(f"   Filename: {result['filename']}")
            print(f"   Size: {result['size']} bytes")
            print(f"   MIME Type: {result.get('mime_type', 'unknown')}")
            print(f"   Source: {result.get('source', 'unknown')}")
            return True
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


async def main():
    """Main testing function"""
    print("🚀 Cloud Mirror Bot - Testing Tool")
    print("=" * 50)
    
    # Pilih URL untuk testing
    print("\nPilih URL untuk testing:")
    for i, (key, url) in enumerate(TEST_URLS.items(), 1):
        print(f"  {i}. {key}: {url}")
    
    print(f"  {len(TEST_URLS) + 1}. Custom URL")
    
    try:
        choice = input("\nPilihan (1-5): ").strip()
        
        if choice == "5":
            custom_url = input("Masukkan custom URL: ").strip()
            await test_download(custom_url, "Custom URL")
        elif choice.isdigit() and 1 <= int(choice) <= len(TEST_URLS):
            idx = int(choice) - 1
            key = list(TEST_URLS.keys())[idx]
            url = TEST_URLS[key]
            await test_download(url, key)
        else:
            print("❌ Pilihan tidak valid")
            
    except KeyboardInterrupt:
        print("\n\n❌ Testing dibatalkan")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        await downloader.close()


if __name__ == "__main__":
    asyncio.run(main())