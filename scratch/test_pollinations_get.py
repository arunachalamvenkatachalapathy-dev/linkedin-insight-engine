import requests, urllib.parse

prompt = "Respond ONLY with JSON: {\"status\": \"ok\", \"headline\": \"Clean Tech Breakthrough\"}"
url = f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}"
try:
    r = requests.get(url, timeout=20)
    print("Status:", r.status_code)
    print("Output:", r.text)
except Exception as e:
    print("Error:", e)
