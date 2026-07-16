import urllib.request
import urllib.parse

prompt = (
    "Modern waste-to-energy facility with advanced robotic sorting arm, high-tech industrial recycling, "
    "professional editorial corporate photography, architectural digest style, clean industrial design, "
    "volumetric lighting, award-winning composition, shot on 35mm lens, hyper-realistic, 8k resolution, "
    "no text, no watermark"
)

encoded_query = urllib.parse.quote(prompt)
url = f"https://image.pollinations.ai/prompt/{encoded_query}?width=1024&height=1024&nologo=true&model=flux"

try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    print("Downloading from Pollinations...")
    with urllib.request.urlopen(req, timeout=45) as response:
        image_bytes = response.read()
    with open("scratch/test_pollinations.png", "wb") as f:
        f.write(image_bytes)
    print("Success! Saved to scratch/test_pollinations.png")
except Exception as e:
    print("Error:", e)
