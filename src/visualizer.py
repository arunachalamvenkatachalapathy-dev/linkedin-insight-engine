"""
Step 3: 3D AI Infographic Slide Generator Agent
Renders 16:9 3D Isometric Infographic Slides using:
1. Google Imagen 3 (imagen-3.0-generate-002) via GEMINI_API_KEY / GOOGLE_API_KEY
2. OpenAI DALL-E 3 (dall-e-3) via OPENAI_API_KEY
3. Pollinations Enhanced AI Engine
4. High-Res PIL Card Fallback
"""

import os
import base64
import logging
import urllib.parse
import requests

log = logging.getLogger("ecopulse")


def generate_imagen_slide(prompt_blueprint: str, out_path: str, api_key: str) -> bool:
    """Generate 16:9 3D Isometric Infographic slide using Google Imagen 3."""
    try:
        log.info("Generating 3D AI Infographic slide via Google Imagen 3 (imagen-3.0-generate-002)...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "instances": [
                {
                    "prompt": prompt_blueprint
                }
            ],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": "16:9",
                "outputOptions": {
                    "mimeType": "image/png"
                }
            }
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            predictions = resp.json().get("predictions", [])
            if predictions and "bytesBase64Encoded" in predictions[0]:
                b64_str = predictions[0]["bytesBase64Encoded"]
                img_data = base64.b64decode(b64_str)
                os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
                with open(out_path, "wb") as f:
                    f.write(img_data)
                log.info(f"✅ Successfully generated Google Imagen 3 3D Infographic slide: {out_path}")
                return True
        log.warning(f"Google Imagen 3 status {resp.status_code}: {resp.text[:140]}")
    except Exception as exc:
        log.warning(f"Google Imagen 3 error: {exc}")
    return False


def generate_dalle_slide(prompt_blueprint: str, out_path: str, api_key: str) -> bool:
    """Generate 16:9 3D Isometric Infographic slide using OpenAI DALL-E 3."""
    try:
        log.info("Generating 3D AI Infographic slide via OpenAI DALL-E 3...")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "dall-e-3",
            "prompt": prompt_blueprint,
            "n": 1,
            "size": "1792x1024",
            "quality": "hd"
        }
        resp = requests.post("https://api.openai.com/v1/images/generations", headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            img_url = resp.json()["data"][0]["url"]
            img_data = requests.get(img_url, timeout=60).content
            os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(img_data)
            log.info(f"✅ Successfully generated HD DALL-E 3 3D Infographic slide: {out_path}")
            return True
        else:
            log.warning(f"DALL-E 3 status {resp.status_code}: {resp.text[:120]}")
    except Exception as exc:
        log.warning(f"DALL-E 3 error: {exc}")
    return False


def generate_pollinations_slide(prompt_blueprint: str, out_path: str) -> bool:
    """Generate 16:9 3D Isometric Infographic slide using Pollinations Enhanced AI Engine."""
    try:
        log.info("Generating 3D AI Infographic slide via Pollinations Enhanced Engine...")
        enhanced_prompt = (
            f"{prompt_blueprint}, high quality 3d isometric infographic slide, "
            f"ultra sharp text layout, frosted glass cards, dark mode UI, 8k resolution, photorealistic 3d rendering"
        )
        encoded = urllib.parse.quote(enhanced_prompt)
        seed = int(os.urandom(2).hex(), 16)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=1200&height=630&nologo=true&seed={seed}"
        resp = requests.get(url, timeout=60)
        if resp.status_code == 200 and len(resp.content) > 10000:
            os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(resp.content)
            log.info(f"✅ Successfully generated Pollinations 3D Infographic slide: {out_path}")
            return True
        else:
            log.warning(f"Pollinations status {resp.status_code}")
    except Exception as exc:
        log.warning(f"Pollinations error: {exc}")
    return False


def generate_pil_fallback(scout_data: dict, out_path: str) -> str:
    """Fallback PIL executive graphic card if AI image endpoints are unreachable."""
    from PIL import Image, ImageDraw, ImageFont

    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    width, height = 1200, 630
    img = Image.new('RGB', (width, height), color='#0B132B')
    draw = ImageDraw.Draw(img)

    for y in range(height):
        r = int(11 + (y / height) * 15)
        g = int(19 + (y / height) * 22)
        b = int(43 + (y / height) * 35)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    font_title = ImageFont.load_default()
    draw.text((60, 50), "ECOPULSE | 3D EXECUTIVE BRIEFING", fill='#10B981', font=font_title)
    draw.text((60, 110), scout_data['headline'], fill='#FFFFFF', font=font_title)
    draw.rounded_rectangle([(50, 200), (width - 50, 540)], radius=16, fill='#1E293B', outline='#10B981', width=2)
    draw.text((80, 240), f"LEFT METRIC: {scout_data['metric_left']}", fill='#3B82F6', font=font_title)
    draw.text((80, 340), f"RIGHT METRIC: {scout_data['metric_right']}", fill='#10B981', font=font_title)

    img.save(out_path, "PNG")
    log.info(f"Generated PIL fallback slide: {out_path}")
    return out_path


def render_3d_slide(prompt_blueprint: str, scout_data: dict, out_path: str = "state/latest_slide.png") -> str:
    """
    Renders 16:9 3D Isometric Infographic Slide.
    Priority 1: Google Imagen 3 (GEMINI_API_KEY / GOOGLE_API_KEY)
    Priority 2: OpenAI DALL-E 3 (OPENAI_API_KEY)
    Priority 3: Pollinations Enhanced Engine
    Priority 4: PIL Fallback Card
    """
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("GOOGLE_API_KEY", "").strip()
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()

    # 1. Try Google Imagen 3 if GEMINI_API_KEY / GOOGLE_API_KEY present
    if gemini_key:
        if generate_imagen_slide(prompt_blueprint, out_path, gemini_key):
            return out_path

    # 2. Try OpenAI DALL-E 3 if OPENAI_API_KEY present
    if openai_key:
        if generate_dalle_slide(prompt_blueprint, out_path, openai_key):
            return out_path

    # 3. Try Pollinations Enhanced Engine
    if generate_pollinations_slide(prompt_blueprint, out_path):
        return out_path

    # 4. Fallback to PIL card
    return generate_pil_fallback(scout_data, out_path)
