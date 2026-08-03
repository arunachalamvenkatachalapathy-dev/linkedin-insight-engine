"""
Step 3: 3D AI Infographic Slide Generator Agent
Renders 16:9 3D Isometric Infographic Slides using Google Imagen 3 (imagen-3.0-generate-002).
"""

import os
import base64
import logging
import requests

log = logging.getLogger("ecopulse")


def generate_google_imagen_slide(prompt_blueprint: str, out_path: str, api_key: str) -> bool:
    """
    Generate 16:9 3D Isometric Infographic slide using Google Imagen 3.
    """
    log.info("Generating 3D AI Infographic slide via Google Imagen 3...")
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

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=90)
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
        log.warning(f"Google Imagen 3 exception: {exc}")

    return False


def generate_pil_fallback(scout_data: dict, out_path: str) -> str:
    """High-Res PIL graphic card fallback."""
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
    Renders 16:9 3D Isometric Infographic Slide via Google Imagen 3.
    """
    gemini_key = (
        os.environ.get("GEMINI_API_KEY", "").strip() or
        os.environ.get("GOOGLE_API_KEY", "").strip()
    )

    if gemini_key:
        if generate_google_imagen_slide(prompt_blueprint, out_path, gemini_key):
            return out_path

    log.info("Rendering executive PIL graphic card fallback...")
    return generate_pil_fallback(scout_data, out_path)
