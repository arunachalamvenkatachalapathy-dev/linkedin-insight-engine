import os
import json
import requests

# Load env
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k.strip()] = v.strip()

gemini_key = os.environ.get("GEMINI_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={gemini_key}"

payload = {
    "contents": [
        {
            "role": "user",
            "parts": [{"text": "Hello"}]
        }
    ]
}

try:
    resp = requests.post(url, json=payload, timeout=30)
    print("HTTP Status:", resp.status_code)
    print("Response:")
    print(resp.text)
except Exception as e:
    print("Error:", e)
