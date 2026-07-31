"""
Image generation and curation agent for EcoPulse.
Programmatically generates clean, custom, branded LinkedIn visual graphic cards
using Python's Pillow (PIL) library (Quote2Image / Infographic Card Canvas).
No generic AI prompts, no Pollinations, no FLUX rate limits. 100% reliable, ultra-fast.
"""

import os
import json
import logging
import textwrap
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger("ecopulse")


def _get_font(size: int, bold: bool = False):
    """Load default font with fallback."""
    font_names = [
        "arialbd.ttf" if bold else "arial.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "SegoeUI-Bold.ttf" if bold else "SegoeUI.ttf"
    ]
    for font_name in font_names:
        try:
            return ImageFont.truetype(font_name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def generate_linkedin_infographic_card(headline: str, fact_text: str, out_path: str = 'state/latest_image.png', funnel_stage: str = 'ToFU') -> str:
    """
    Generate a high-end, corporate branded LinkedIn graphic card using Pillow.
    Dimensions: 1200x630 (standard 16:9 LinkedIn ratio).
    """
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)

    # Theme colors based on funnel stage
    if funnel_stage == 'BoFU':
        theme_fill = '#B45309'     # Amber/Gold for BoFU (Pilot / Proof)
        theme_badge = '#F59E0B'
        badge_title = "BOTTOM OF FUNNEL  |  SAMR FIELD CASE STUDY"
        border_color = '#F59E0B'
    elif funnel_stage == 'MoFU':
        theme_fill = '#1D4ED8'     # Blue for MoFU (Benchmarks / Technical)
        theme_badge = '#3B82F6'
        badge_title = "MIDDLE OF FUNNEL  |  BENCHMARKS & METHODOLOGY"
        border_color = '#3B82F6'
    else:
        theme_fill = '#059669'     # Emerald Green for ToFU (Regulatory / Policy)
        theme_badge = '#10B981'
        badge_title = "TOP OF FUNNEL  |  REGULATORY BRIEFING"
        border_color = '#10B981'

    # Canvas dimensions & dark mode theme
    width, height = 1200, 630
    img = Image.new('RGB', (width, height), color='#0B132B')
    draw = ImageDraw.Draw(img)

    # 1. Subtle background grid pattern
    grid_color = '#162447'
    for y in range(0, height, 40):
        draw.line([(0, y), (width, y)], fill=grid_color, width=1)
    for x in range(0, width, 40):
        draw.line([(x, 0), (x, height)], fill=grid_color, width=1)

    # 2. Header Brand Pill Box
    draw.rounded_rectangle([60, 45, 620, 92], radius=10, fill=theme_fill)
    font_brand = _get_font(20, bold=True)
    draw.text((78, 57), f"ECOPULSE  |  {funnel_stage.upper()} ENGINE", fill='#FFFFFF', font=font_brand)

    # 3. Main Post Title (Wrapped)
    font_title = _get_font(34, bold=True)
    title_text = headline.strip()
    if len(title_text) > 95:
        title_text = title_text[:92] + "..."

    wrapped_title = textwrap.fill(title_text, width=48)
    draw.text((60, 125), wrapped_title, fill='#F8FAFC', font=font_title)

    # 4. Highlighted Empirical Metric Card Box
    card_top = 265
    card_height = 220
    draw.rounded_rectangle([60, card_top, width - 60, card_top + card_height], radius=16, fill='#1E293B', outline=border_color, width=2)

    font_badge = _get_font(18, bold=True)
    draw.text((90, card_top + 25), badge_title, fill=theme_badge, font=font_badge)

    # Wrap metric fact text inside the card box
    font_fact = _get_font(22, bold=False)
    clean_fact = fact_text.strip()
    if len(clean_fact) > 220:
        clean_fact = clean_fact[:217] + "..."
    wrapped_fact = textwrap.fill(clean_fact, width=68)
    draw.text((90, card_top + 65), wrapped_fact, fill='#E2E8F0', font=font_fact)

    # 5. Footer Branding & Category Tags
    font_footer = _get_font(16, bold=False)
    today_str = datetime.now(timezone.utc).strftime("%B %Y")
    footer_text = f"FRAMEWORKS: BRSR Core  •  CSRD ESRS E1  •  GRI Standards  •  GHG Protocol   |   {today_str}"
    draw.text((60, 545), footer_text, fill='#64748B', font=font_footer)

    img.save(out_path, "PNG")
    log.info(f"Successfully generated custom Pillow graphic card: {out_path} ({funnel_stage})")
    return out_path


def run(copywriter_output: dict, out_path: str = 'state/latest_image.png', funnel_stage: str = 'ToFU') -> dict:
    """Run the image agent with custom Pillow graphic card generator."""
    headline = (
        copywriter_output.get("headline") or
        copywriter_output.get("selected_idea", {}).get("headline") or
        "Senior Environmental Engineering Telemetry & Compliance"
    )

    supporting_facts = copywriter_output.get("supporting_facts") or copywriter_output.get("selected_idea", {}).get("supporting_facts", [])
    fact_text = supporting_facts[0] if supporting_facts else "Primary supplier telemetry reduces emission factor variance from +/-25% down to +/-3% under BRSR Core & CSRD."

    generated_path = generate_linkedin_infographic_card(headline, fact_text, out_path, funnel_stage)

    return {
        "agent": "image",
        "output": {
            "image_path": generated_path,
            "image_prompt": f"Custom Pillow Canvas Graphic Card: {headline} ({funnel_stage})",
            "model_used": f"Pillow Canvas Graphic Card ({funnel_stage} layout)"
        }
    }
