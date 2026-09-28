import asyncio
import httpx
import os
import base64
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

load_dotenv("backend/.env")

groq_key = os.getenv("GROQ_API_KEY")

def create_test_image_b64():
    img = Image.new("RGB", (100, 100), color=(79, 70, 229))
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

async def test_groq_vision(model_name):
    url = "https://api.groq.com/openai/v1/chat/completions"
    img_b64 = create_test_image_b64()
    data_url = f"data:image/png;base64,{img_b64}"
    
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe the main color and shape of this image in one brief sentence."},
                    {"type": "image_url", "image_url": {"url": data_url}}
                ]
            }
        ],
        "max_tokens": 100
    }
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(url, json=payload, headers=headers)
        print(f"Model {model_name} -> Status {res.status_code}")
        if res.status_code == 200:
            print("Response:", res.json()["choices"][0]["message"]["content"])
        else:
            print("Error body:", res.text[:300])

async def main():
    models_to_test = [
        "qwen-2.5-vl-7b-instruct",
        "qwen/qwen3.8-27b",
        "llama-3.2-11b-vision-preview",
    ]
    for m in models_to_test:
        await test_groq_vision(m)

if __name__ == "__main__":
    asyncio.run(main())
