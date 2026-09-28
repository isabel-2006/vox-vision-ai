import sys
import asyncio
import httpx
import base64
from io import BytesIO
from PIL import Image
import os
import json
import websockets

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws/chat"

def create_sample_png(color=(79, 70, 229), size=(120, 120)):
    img = Image.new("RGB", size, color=color)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

def create_sample_jpg(color=(220, 38, 38), size=(120, 120)):
    img = Image.new("RGB", size, color=color)
    buf = BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.getvalue()

async def run_tests():
    print("==================================================")
    print(" VoxVision AI - Step 6 Automated Verification Tests")
    print("==================================================")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Health Check
        res = await client.get(f"{BASE_URL}/api/health")
        print(f"\n[1] Health Check: Status {res.status_code}")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        print(f"    Response: {res.json()}")

        # 2. Upload PNG Image with Vision Query
        png_bytes = create_sample_png((59, 130, 246)) # Blue PNG
        files = {"file": ("blue_box.png", png_bytes, "image/png")}
        data = {"prompt": "What color is this square image?"}
        res = await client.post(f"{BASE_URL}/api/vision", files=files, data=data)
        print(f"\n[2] Vision PNG Upload ('What color is this square image?'): Status {res.status_code}")
        assert res.status_code == 200, f"Vision PNG upload failed: {res.text}"
        res_json = res.json()
        print(f"    Provider: {res_json.get('provider')}")
        print(f"    Model: {res_json.get('model')}")
        print(f"    Reply: {repr(res_json.get('reply'))[:150]}...")

        # 3. Upload JPG Image with Vision Query
        jpg_bytes = create_sample_jpg((239, 68, 68)) # Red JPG
        files = {"file": ("red_box.jpg", jpg_bytes, "image/jpeg")}
        data = {"prompt": "Describe this image."}
        res = await client.post(f"{BASE_URL}/api/vision", files=files, data=data)
        print(f"\n[3] Vision JPG Upload ('Describe this image.'): Status {res.status_code}")
        assert res.status_code == 200, f"Vision JPG upload failed: {res.text}"
        res_json = res.json()
        print(f"    Provider: {res_json.get('provider')}")
        print(f"    Reply: {repr(res_json.get('reply'))[:150]}...")

        # 4. Invalid File Type Validation
        txt_bytes = b"Hello world text file"
        files = {"file": ("document.txt", txt_bytes, "text/plain")}
        res = await client.post(f"{BASE_URL}/api/vision", files=files, data={"prompt": "Analyze image"})
        print(f"\n[4] Invalid File Type (.txt): Status {res.status_code}")
        assert res.status_code == 400, f"Expected status 400 for invalid file type, got {res.status_code}"
        print(f"    Detail: {res.json().get('detail')}")

        # 5. Oversized File Validation (>10MB)
        # Create a dummy 10.5MB file
        large_bytes = b"0" * int(10.5 * 1024 * 1024)
        files = {"file": ("large_image.png", large_bytes, "image/png")}
        res = await client.post(f"{BASE_URL}/api/vision", files=files, data={"prompt": "Large image"})
        print(f"\n[5] Oversized File (10.5MB): Status {res.status_code}")
        assert res.status_code == 400, f"Expected status 400 for oversized file, got {res.status_code}"
        print(f"    Detail: {res.json().get('detail')}")

        # 6. Verify STT Speech-to-Text Endpoint
        dummy_audio = b"dummy audio content"
        files = {"file": ("test.webm", dummy_audio, "audio/webm")}
        res = await client.post(f"{BASE_URL}/api/stt", files=files)
        print(f"\n[6] STT Endpoint Check: Status {res.status_code}")
        assert res.status_code == 200, f"STT failed: {res.text}"
        print(f"    Response: {res.json()}")

        # 7. Verify TTS Text-to-Speech Endpoint
        res = await client.post(f"{BASE_URL}/api/tts", json={"text": "VoxVision AI Step 6 vision test."})
        print(f"\n[7] TTS Endpoint Check: Status {res.status_code}")
        assert res.status_code == 200, f"TTS failed: {res.text}"
        print(f"    Content-Type: {res.headers.get('content-type')}, Size: {len(res.content)} bytes")

    # 8. Verify WebSocket Text Chat
    print(f"\n[8] WebSocket Chat Verification ({WS_URL})...")
    async with websockets.connect(WS_URL) as ws:
        # Expect connection_ack
        ack = await ws.recv()
        print(f"    WS Received: {ack[:100]}")
        
        # Send text message
        msg_payload = {"type": "chat_message", "message": "What is VoxVision AI?", "session_id": "test_session"}
        await ws.send(json.dumps(msg_payload))
        reply = await ws.recv()
        print(f"    WS Chat Response: {reply[:150]}")
        reply_json = json.loads(reply)
        assert reply_json.get("type") == "chat_response", "Expected type chat_response"

    print("\n==================================================")
    print(" 🎉 ALL STEP 6 AUTOMATED API TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_tests())
