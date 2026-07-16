import os
import requests

# Load env
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k.strip()] = v.strip()

token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
post_id = "urn:li:share:7482981577648414720"

# LinkedIn REST Posts API GET endpoint
url = f"https://api.linkedin.com/rest/posts/{post_id}"
headers = {
    "Authorization": f"Bearer {token}",
    "LinkedIn-Version": "202606",
    "X-Restli-Protocol-Version": "2.0.0",
}

try:
    resp = requests.get(url, headers=headers, timeout=20)
    print("Status:", resp.status_code)
    print("Response JSON:")
    print(resp.text)
except Exception as e:
    print("Error:", e)
