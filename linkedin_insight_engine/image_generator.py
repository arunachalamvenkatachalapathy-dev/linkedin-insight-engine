from __future__ import annotations

import json
import os
import random
import urllib.parse
import urllib.request
from pathlib import Path

from .config import settings
from .logger import log_event


STYLES = (
    "Breathtaking, professional, cinematic nature photography of {topic}, ultra high resolution, beautiful natural lighting, award winning, National Geographic style, no text, no watermarks",
    "Modern minimalist flat vector illustration of {topic}, clean lines, vibrant curated colors, artistic design, flat art style, no text",
    "Atmospheric dramatic oil painting of {topic}, textured canvas, expressive brush strokes, artistic lighting, fine art style, no text",
    "Macro detailed outdoor photography of {topic}, morning dew, shallow depth of field, crisp focus, soft lighting, no text",
)

MODELS = (
    "flux",
    "flux-realism",
    "turbo",
)


def generate_image(topic: str, api_key: str, output_dir: str = "data") -> str:
    """Generate an image strictly using OpenAI DALL-E 3."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    image_file = output_path / "latest_image.jpg"

    # Select random style and model
    style_template = random.choice(STYLES)
    prompt = style_template.format(topic=topic)
    
    openai_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")
    if not openai_key:
        raise ValueError("OPENAI_API_KEY environment variable is required for strict DALL-E 3 image generation.")

    try:
        log_event("image-generator", "openai-dalle3-attempt", topic=topic)
        payload = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024"
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/images/generations",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read())
            image_url = res_data["data"][0]["url"]
            
        # Download the image
        image_req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(image_req, timeout=20) as img_res:
            image_bytes = img_res.read()
            
        if image_bytes:
            with open(image_file, "wb") as f:
                f.write(image_bytes)
            log_event("image-generator", "openai-dalle3-success", path=str(image_file))
            return str(image_file)
    except Exception as exc:
        log_event("image-generator", "openai-dalle3-failed", error=type(exc).__name__, detail=str(exc)[:200])
        raise RuntimeError(f"DALL-E 3 image generation failed: {exc}")

    return ""
