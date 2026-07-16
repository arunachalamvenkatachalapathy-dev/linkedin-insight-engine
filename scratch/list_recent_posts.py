import os
import requests
import urllib.parse

# Load env
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k.strip()] = v.strip()

token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
author = os.environ.get("LINKEDIN_PERSON_URN")

# URL encode author URN
encoded_author = urllib.parse.quote(author)
url = f"https://api.linkedin.com/rest/posts?author={encoded_author}&q=author&count=5"
headers = {
    "Authorization": f"Bearer {token}",
    "LinkedIn-Version": "202606",
    "X-Restli-Protocol-Version": "2.0.0",
}

try:
    resp = requests.get(url, headers=headers, timeout=20)
    print("Status:", resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        print("Success! Elements count:", len(data.get("elements", [])))
        for idx, el in enumerate(data.get("elements", [])):
            print(f"\n--- Post {idx} ---")
            print("ID:", el.get("id"))
            print("Commentary:", repr(el.get("commentary", "")))
            print("Visibility:", el.get("visibility"))
            print("LifecycleState:", el.get("lifecycleState"))
    else:
        print("Response:", resp.text)
except Exception as e:
    print("Error:", e)
