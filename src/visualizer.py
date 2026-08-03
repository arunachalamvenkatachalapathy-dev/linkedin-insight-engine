"""
Step 3: 3D AI Infographic Slide Generator Agent
EXCLUSIVELY uses Google Gemini / Imagen Image Models (gemini-3.1-flash-image, gemini-2.5-flash-image, gemini-3-pro-image).
Includes smart quota handling and rate-limit retries.
"""

import os
import time
import base64
import logging
import requests

log = logging.getLogger("ecopulse")

GOOGLE_IMAGE_ENDPOINTS = [
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image:generateContent"
]


def generate_google_imagen_slide(prompt_blueprint: str, out_path: str, api_key: str) -> bool:
    """
    Generate 16:9 3D Isometric Infographic slide using Google Gemini / Imagen models.
    Handles rate limits with retries.
    """
    log.info("Generating 3D AI Infographic slide via Google Imagen / Gemini Image models...")
    
    for endpoint in GOOGLE_IMAGE_ENDPOINTS:
        url = f"{endpoint}?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"A high-quality 16:9 3D isometric visual infographic slide for LinkedIn: {prompt_blueprint}"
                        }
                    ]
                }
            ]
        }

        # Try up to 2 retries per endpoint for rate limits
        for attempt in range(2):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=90)
                if resp.status_code == 200:
                    res_json = resp.json()
                    img_data = None
                    
                    candidates = res_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        for part in parts:
                            inline = part.get("inlineData") or part.get("inline_data")
                            if inline and inline.get("data"):
                                img_data = base64.b64decode(inline["data"])
                                break

                    if img_data:
                        os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
                        with open(out_path, "wb") as f:
                            f.write(img_data)
                        log.info(f"✅ Successfully generated Google 3D Infographic slide ({endpoint.split('/')[-1]}): {out_path}")
                        return True
                elif resp.status_code == 429:
                    log.warning(f"Endpoint {endpoint.split('/')[-1]} rate limited (429). Retrying in 5s...")
                    time.sleep(5)
                else:
                    log.warning(f"Endpoint {endpoint.split('/')[-1]} status {resp.status_code}: {resp.text[:120]}")
                    break
            except Exception as exc:
                log.warning(f"Endpoint {endpoint.split('/')[-1]} exception: {exc}")
                break

    return False


def generate_pil_fallback(scout_data: dict, out_path: str) -> str:
    """High-Res PIL graphic card fallback if Google API quota is temporarily exhausted."""
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
    """
    gemini_key = (
        os.environ.get("GEMINI_API_KEY", "").strip() or
        os.environ.get("GOOGLE_API_KEY", "").strip()
    )

    if gemini_key:
        if generate_google_imagen_slide(prompt_blueprint, out_path, gemini_key):
            return out_path

    log.info("Google Gemini API quota temporarily exceeded. Rendering executive PIL graphic card...")
    return generate_pil_fallback(scout_data, out_path)
