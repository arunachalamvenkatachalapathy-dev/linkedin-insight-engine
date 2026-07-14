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
    """Generate an image rotating through DALL-E 3, Google Imagen 3, or Pollinations AI."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    image_file = output_path / "latest_image.jpg"

    # Select random style and model
    style_template = random.choice(STYLES)
    prompt = style_template.format(topic=topic)
    
    # 1. Try OpenAI DALL-E 3 if API Key is available
    openai_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")
    if openai_key:
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

    # 2. Try Google Imagen 3 if API Key is available
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            result = client.models.generate_images(
                model='imagen-4.0-generate-001',
                prompt=prompt,
                config=dict(
                    number_of_images=1,
                    output_mime_type="image/jpeg",
                    aspect_ratio="16:9"
                )
            )
            for generated_image in result.generated_images:
                with open(image_file, "wb") as f:
                    f.write(generated_image.image.image_bytes)
                log_event("image-generator", "imagen3-success", path=str(image_file))
                return str(image_file)
        except Exception as exc:
            log_event("image-generator", "imagen3-failed", error=type(exc).__name__, detail=str(exc)[:200])

    # 3. Fallback to Pollinations AI with model rotation
    models_to_try = list(MODELS)
    random.shuffle(models_to_try)

    for model in models_to_try:
        try:
            encoded_query = urllib.parse.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded_query}?width=1600&height=900&nologo=true&model={model}&seed={random.randint(1, 99999)}"
            
            log_event("image-generator", "pollinations-attempt", model=model, topic=topic)
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=25) as response:
                image_bytes = response.read()

            if image_bytes:
                with open(image_file, "wb") as f:
                    f.write(image_bytes)
                log_event("image-generator", "pollinations-success", path=str(image_file), model=model)
                return str(image_file)
        except Exception as exc:
            log_event("image-generator", "pollinations-model-failed", model=model, error=type(exc).__name__)

    return ""
