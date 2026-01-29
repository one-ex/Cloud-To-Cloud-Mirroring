#!/usr/bin/env python3
"""Test script untuk validator"""

import asyncio
from validator import validate_url_and_file

async def test_validator():
    # Test URL-URL berbeda
    test_urls = [
        "https://sample-videos.com/zip/10mb.zip",
        "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
        "https://filesamples.com/samples/document/docx/sample1.docx",
        "https://sample-videos.com/zip/50mb.zip",
    ]
    
    print("🧪 Testing validator...")
    
    for url in test_urls:
        print(f"\n📁 Testing: {url}")
        valid, result = await validate_url_and_file(url)
        
        if valid:
            print(f"✅ Valid!")
            print(f"   File: {result['filename']}")
            print(f"   Ukuran: {result['size']} bytes")
            print(f"   Tipe: {result['type']}")
        else:
            print(f"❌ Error: {result}")

if __name__ == "__main__":
    asyncio.run(test_validator())