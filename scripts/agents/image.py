"""
Image generation and curation agent for EcoPulse.
Generates stunning AI Infographic social graphics matching high-end executive 3D slide visual aesthetics.
Primary: OpenAI DALL-E 3 / Pollinations AI Infographic Generator.
Fallback: High-Res Glassmorphic Playwright & PIL Card Engine.
"""

import os
import re
import json
import logging
import urllib.parse
import requests
from pathlib import Path
from datetime import datetime, timezone

log = logging.getLogger("ecopulse")

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def generate_dalle_image(prompt: str, out_path: str, api_key: str) -> bool:
    """Generate high-impact 3D infographic slide using OpenAI DALL-E 3."""
    try:
        log.info("Attempting AI Infographic generation via OpenAI DALL-E 3...")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "dall-e-3",
            "prompt": prompt,
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
            log.info(f"Successfully generated DALL-E 3 AI Infographic: {out_path}")
            return True
        else:
            log.warning(f"DALL-E 3 API error ({resp.status_code}): {resp.text[:150]}")
    except Exception as exc:
        log.warning(f"DALL-E 3 exception: {exc}")
    return False


def generate_pollinations_image(prompt: str, out_path: str) -> bool:
    """Generate high-quality 3D infographic slide using Pollinations AI Engine (Free & Instant)."""
    try:
        log.info("Attempting AI Infographic generation via Pollinations AI Engine...")
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1200&height=630&nologo=true&model=flux"
        resp = requests.get(url, timeout=45)
        if resp.status_code == 200 and len(resp.content) > 10000:
            os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(resp.content)
            log.info(f"Successfully generated Pollinations AI Infographic: {out_path}")
            return True
        else:
            log.warning(f"Pollinations AI returned status {resp.status_code}")
    except Exception as exc:
        log.warning(f"Pollinations AI exception: {exc}")
    return False


def _get_truetype_font(size: int, bold: bool = False):
    from PIL import ImageFont
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "DejaVuSans.ttf"
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def generate_fallback_pil_card(headline: str, fact_text: str, out_path: str, funnel_stage: str = 'ToFU') -> str:
    from PIL import Image, ImageDraw
    import textwrap

    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    width, height = 1200, 630
    img = Image.new('RGB', (width, height), color='#090D16')
    draw = ImageDraw.Draw(img)

    for y in range(height):
        r = int(9 + (y / height) * 15)
        g = int(13 + (y / height) * 22)
        b = int(22 + (y / height) * 35)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    for x in range(0, width, 44):
        draw.line([(x, 0), (x, height)], fill='#162447', width=1)
    for y in range(0, height, 44):
        draw.line([(0, y)], fill='#162447', width=1)

    badge_colors = {
        'TOFU': ('#059669', '#10B981'),
        'MOFU': ('#1D4ED8', '#3B82F6'),
        'BOFU': ('#B45309', '#F59E0B')
    }
    primary_color, accent_color = badge_colors.get(funnel_stage.upper(), ('#059669', '#10B981'))

    font_badge = _get_truetype_font(18, bold=True)
    font_title = _get_truetype_font(36, bold=True)
    font_body = _get_truetype_font(24, bold=False)
    font_tag = _get_truetype_font(16, bold=True)
    font_footer = _get_truetype_font(14, bold=False)

    draw.rounded_rectangle([(50, 40), (190, 82)], radius=8, fill=primary_color)
    draw.text((68, 50), "ECOPULSE", fill='#FFFFFF', font=font_badge)
    draw.text((215, 50), f"{funnel_stage.upper()} | EXECUTIVE TECHNICAL BRIEFING", fill=accent_color, font=font_badge)

    clean_headline = headline.strip()
    wrapped_title = textwrap.fill(clean_headline, width=50)
    draw.text((50, 110), wrapped_title, fill='#FFFFFF', font=font_title)

    draw.rounded_rectangle([(50, 240), (width - 50, 540)], radius=18, fill='#1E293B', outline=accent_color, width=2)
    draw.text((80, 265), f"{funnel_stage.upper()}  |  FIELD TELEMETRY & COMPLIANCE DATA", fill=accent_color, font=font_tag)

    clean_fact = fact_text.strip()
    wrapped_fact = textwrap.fill(clean_fact, width=62)
    draw.text((80, 310), wrapped_fact, fill='#CBD5E1', font=font_body)

    date_str = datetime.now(timezone.utc).strftime("%B %Y")
    draw.line([(50, 570), (width - 50, 570)], fill='#334155', width=1)
    draw.text((50, 585), "FRAMEWORKS: BRSR Core  •  CSRD ESRS E1  •  GRI Standards  •  GHG Protocol", fill='#64748B', font=font_footer)
    draw.text((width - 170, 585), date_str, fill='#94A3B8', font=font_footer)

    img.save(out_path, "PNG")
    return out_path


def run(copywriter_output: dict, out_path: str = 'state/latest_image.png', funnel_stage: str = 'ToFU') -> dict:
    """
    Run the Image agent to produce a 3D AI Infographic social graphic slide.
    """
    headline = (
        copywriter_output.get("headline") or
        copywriter_output.get("selected_idea", {}).get("headline") or
        "Senior Environmental Engineering Telemetry & Compliance"
    )

    supporting_facts = copywriter_output.get("supporting_facts") or copywriter_output.get("selected_idea", {}).get("supporting_facts", [])
    fact_text = supporting_facts[0] if supporting_facts else "Primary supplier telemetry reduces emission factor variance from +/-25% down to +/-3% under BRSR Core & CSRD."

    # Craft detailed prompt matching 3D isometric infographic slide aesthetics
    ai_prompt = (
        f"A modern, high-tech digital infographic card for LinkedIn titled '{headline}'. "
        f"Dark theme aesthetic with deep indigo navy background and glowing cyan and emerald glassmorphic cards. "
        f"Displays a clean comparison or 3D isometric technology diagram comparing key metrics side-by-side: "
        f"'{fact_text[:180]}'. "
        f"Includes glowing 3D isometric rendering of engineering hardware, server racks, or green energy systems, "
        f"vibrant cyan data graphs, sharp modern sans-serif typography, clean visual hierarchy, hyper-detailed executive presentation slide style, 16:9 ratio."
    )

    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()

    # 1. Try DALL-E 3 if API Key is available
    if openai_key:
        if generate_dalle_image(ai_prompt, out_path, openai_key):
            return {
                "agent": "image",
                "output": {
                    "image_path": out_path,
                    "image_prompt": ai_prompt,
                    "model_used": "OpenAI DALL-E 3 AI Infographic Generator"
                }
            }

    # 2. Try Pollinations AI Engine (Free & Instant AI Infographic)
    if generate_pollinations_image(ai_prompt, out_path):
        return {
            "agent": "image",
            "output": {
                "image_path": out_path,
                "image_prompt": ai_prompt,
                "model_used": "Pollinations Flux AI Infographic Generator"
            }
        }

    # 3. Fallback to High-Res PIL Card
    generate_fallback_pil_card(headline, fact_text, out_path, funnel_stage)
    return {
        "agent": "image",
        "output": {
            "image_path": out_path,
            "image_prompt": ai_prompt,
            "model_used": "High-Res Executive PIL Card Engine"
        }
    }
