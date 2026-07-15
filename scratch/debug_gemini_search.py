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

openai_key = os.environ.get("OPENAI_API_KEY")
print("Using OpenAI key starting with:", openai_key[:15] if openai_key else "None")

resp = requests.post(
    "https://api.openai.com/v1/images/generations",
    headers={"Authorization": f"Bearer {openai_key}"},
    json={
        "model": "dall-e-3",
        "prompt": "A professional 3D corporate graphic illustration of wind turbines on a clean background, professional LinkedIn graphic",
        "size": "1024x1024",
    },
    timeout=60,
)
print("OpenAI status:", resp.status_code)
if resp.status_code == 200:
    print("Success! DALL-E 3 works.")
    print("URL:", resp.json()["data"][0]["url"])
else:
    print("Response:", resp.text[:400])
