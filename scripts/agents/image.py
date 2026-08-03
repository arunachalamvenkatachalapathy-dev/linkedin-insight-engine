"""
Image generation and curation agent for EcoPulse.
Uses Next-Generation HTML5/CSS3 & Playwright Headless Render Engine with high-res PIL card fallback.
Compiles glassmorphic social graphics with embedded data telemetry cards.
"""

import os
import re
import json
import logging
import textwrap
from pathlib import Path
from datetime import datetime, timezone
from jinja2 import Template

log = logging.getLogger("ecopulse")

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def render_html_template(headline: str, fact_text: str, funnel_stage: str = "ToFU") -> str:
    """Render HTML string from Jinja2 template based on funnel stage."""
    template_name = f"card_{funnel_stage.lower()}.html"
    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        template_path = TEMPLATES_DIR / "card_tofu.html"

    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    template = Template(template_content)
    date_str = datetime.now(timezone.utc).strftime("%B %Y")
    
    clean_headline = headline.strip()
    if len(clean_headline) > 95:
        clean_headline = clean_headline[:92] + "..."

    clean_fact = fact_text.strip()
    if len(clean_fact) > 220:
        clean_fact = clean_fact[:217] + "..."

    rendered_html = template.render(
        headline=clean_headline,
        fact_text=clean_fact,
        date_str=date_str
    )
    return rendered_html


def generate_playwright_image(html_content: str, out_path: str) -> bool:
    """Render HTML content to 1200x630 PNG using Playwright headless Chromium."""
    try:
        from playwright.sync_api import sync_playwright

        os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
        styles_path = (TEMPLATES_DIR / "styles.css").resolve().as_uri()

        # Inject absolute styles URI so Playwright loads CSS properly
        html_with_styles = html_content.replace(
            '<link rel="stylesheet" href="styles.css">',
            f'<link rel="stylesheet" href="{styles_path}">'
        )

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1200, "height": 630},
                device_scale_factor=2  # High-DPI 2x scale factor for crisp rendering
            )
            page = context.new_page()
            page.set_content(html_with_styles, wait_until="networkidle")
            page.screenshot(path=out_path, type="png")
            browser.close()

        log.info(f"Successfully rendered Playwright HTML/CSS graphic card: {out_path}")
        return True
    except Exception as exc:
        log.warning(f"Playwright rendering exception: {exc}")

    return False


def _get_truetype_font(size: int, bold: bool = False):
    """Load system truetype font with cross-platform fallbacks for crisp card rendering."""
    from PIL import ImageFont
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeuib.ttf" if bold else "C:\\Windows\\Fonts\\segoeui.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
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
    """Stunning high-resolution PIL card generator for EcoPulse executive social graphics."""
    from PIL import Image, ImageDraw

    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    width, height = 1200, 630
    
    # 1. Base dark gradient background
    img = Image.new('RGB', (width, height), color='#0B132B')
    draw = ImageDraw.Draw(img)

    # Draw dark slate gradient background lines
    for y in range(height):
        r = int(11 + (y / height) * 15)
        g = int(19 + (y / height) * 22)
        b = int(43 + (y / height) * 35)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Grid accent overlay
    grid_color = (22, 36, 71, 100)
    for x in range(0, width, 40):
        draw.line([(x, 0), (x, height)], fill='#162447', width=1)
    for y in range(0, height, 40):
        draw.line([(0, y), (width, y)], fill='#162447', width=1)

    # Stage color scheme
    badge_colors = {
        'TOFU': ('#059669', '#10B981'),
        'MOFU': ('#1D4ED8', '#3B82F6'),
        'BOFU': ('#B45309', '#F59E0B')
    }
    primary_color, accent_color = badge_colors.get(funnel_stage.upper(), ('#059669', '#10B981'))

    # Fonts
    font_badge = _get_truetype_font(18, bold=True)
    font_title = _get_truetype_font(34, bold=True)
    font_body = _get_truetype_font(22, bold=False)
    font_tag = _get_truetype_font(15, bold=True)
    font_footer = _get_truetype_font(14, bold=False)

    # 2. Header Bar
    # Pill background
    draw.rounded_rectangle([(50, 40), (190, 80)], radius=8, fill=primary_color)
    draw.text((68, 50), "ECOPULSE", fill='#FFFFFF', font=font_badge)

    # Stage Badge
    stage_text = f"{funnel_stage.upper()} | EXECUTIVE TECHNICAL BRIEFING"
    draw.text((215, 50), stage_text, fill=accent_color, font=font_badge)

    # 3. Main Headline
    clean_headline = headline.strip()
    wrapped_title = textwrap.fill(clean_headline, width=52)
    draw.text((50, 110), wrapped_title, fill='#FFFFFF', font=font_title)

    # 4. Central Glassmorphic Card Container
    card_top = 240
    card_bottom = 540
    draw.rounded_rectangle([(50, card_top), (width - 50, card_bottom)], radius=16, fill='#1E293B', outline=accent_color, width=2)

    # Card Tag
    draw.text((80, card_top + 24), f"{funnel_stage.upper()}  |  FIELD TELEMETRY & COMPLIANCE DATA", fill=accent_color, font=font_tag)

    # Card Fact Text
    clean_fact = fact_text.strip()
    wrapped_fact = textwrap.fill(clean_fact, width=65)
    draw.text((80, card_top + 65), wrapped_fact, fill='#CBD5E1', font=font_body)

    # 5. Footer Bar
    date_str = datetime.now(timezone.utc).strftime("%B %Y")
    draw.line([(50, 570), (width - 50, 570)], fill='#334155', width=1)
    draw.text((50, 585), "FRAMEWORKS: BRSR Core  •  CSRD ESRS E1  •  GRI Standards  •  GHG Protocol", fill='#64748B', font=font_footer)
    draw.text((width - 170, 585), date_str, fill='#94A3B8', font=font_footer)

    img.save(out_path, "PNG")
    log.info(f"Generated high-res executive PIL graphic card: {out_path}")
    return out_path


def run(copywriter_output: dict, out_path: str = 'state/latest_image.png', funnel_stage: str = 'ToFU') -> dict:
    """
    Run the image agent using Next-Gen Playwright HTML/CSS Headless Engine with high-res PIL fallback.
    """
    headline = (
        copywriter_output.get("headline") or
        copywriter_output.get("selected_idea", {}).get("headline") or
        "Senior Environmental Engineering Telemetry & Compliance"
    )

    supporting_facts = copywriter_output.get("supporting_facts") or copywriter_output.get("selected_idea", {}).get("supporting_facts", [])
    fact_text = supporting_facts[0] if supporting_facts else "Primary supplier telemetry reduces emission factor variance from +/-25% down to +/-3% under BRSR Core & CSRD."

    html_content = render_html_template(headline, fact_text, funnel_stage)
    success = generate_playwright_image(html_content, out_path)
    model_used = f"Playwright HTML/CSS Engine ({funnel_stage} layout)"

    if not success:
        log.info("Playwright headless render fallback triggered. Rendering high-res executive PIL card...")
        generate_fallback_pil_card(headline, fact_text, out_path, funnel_stage)
        model_used = f"High-Res Executive PIL Card Engine ({funnel_stage} layout)"

    return {
        "agent": "image",
        "output": {
            "image_path": out_path,
            "image_prompt": f"Executive Card: {headline} ({funnel_stage})",
            "model_used": model_used
        }
    }
