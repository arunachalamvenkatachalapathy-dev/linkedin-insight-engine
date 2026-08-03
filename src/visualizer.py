"""
Step 3: 3D AI Infographic Slide Generator Agent
Calls OpenAI DALL-E 3 / Pollinations Flux AI Engine to generate 16:9 3D Isometric Infographic Slides.
"""

import os
import logging
import urllib.parse
import requests
from pathlib import Path

log = logging.getLogger("ecopulse")


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
            "quality": "standard"
        }
        resp = requests.post("https://api.openai.com/v1/images/generations", headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            img_url = resp.json()["data"][0]["url"]
            img_data = requests.get(img_url, timeout=60).content
            os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(img_data)
            log.info(f"✅ Successfully generated DALL-E 3 slide: {out_path}")
            return True
        else:
            log.warning(f"DALL-E 3 status {resp.status_code}: {resp.text[:120]}")
    except Exception as exc:
        log.warning(f"DALL-E 3 error: {exc}")
    return False


def generate_pollinations_slide(prompt_blueprint: str, out_path: str) -> bool:
    """Generate 16:9 3D Isometric Infographic slide using Pollinations Flux AI Engine."""
    try:
        log.info("Generating 3D AI Infographic slide via Pollinations Flux AI Engine...")
        encoded = urllib.parse.quote(prompt_blueprint)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=1200&height=630&nologo=true&model=flux"
        resp = requests.get(url, timeout=45)
        if resp.status_code == 200 and len(resp.content) > 10000:
            os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(resp.content)
            log.info(f"✅ Successfully generated Pollinations AI slide: {out_path}")
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

    # Dark gradient background
    for y in range(height):
        r = int(11 + (y / height) * 15)
        g = int(19 + (y / height) * 22)
        b = int(43 + (y / height) * 35)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Borders and Text
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
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()

    # 1. Try DALL-E 3 if API Key present
    if openai_key:
        if generate_dalle_slide(prompt_blueprint, out_path, openai_key):
            return out_path

    # 2. Try Pollinations Flux AI Engine
    if generate_pollinations_slide(prompt_blueprint, out_path):
        return out_path

    # 3. Fallback to PIL card
    return generate_pil_fallback(scout_data, out_path)
