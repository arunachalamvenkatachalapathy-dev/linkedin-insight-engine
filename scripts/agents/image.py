"""
Image generation and curation agent for EcoPulse.
Uses Next-Generation HTML5/CSS3 & Playwright Headless Render Engine.
Compiles glassmorphic social graphics with embedded data telemetry cards.
"""

import os
import re
import json
import logging
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
                device_scale_factor=2  # High-DPI 2x scale factor for crisp 4K rendering
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


def generate_fallback_pil_card(headline: str, fact_text: str, out_path: str, funnel_stage: str = 'ToFU') -> str:
    """Fallback PIL card generator if Playwright browser is unavailable."""
    from PIL import Image, ImageDraw, ImageFont
    import textwrap

    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    width, height = 1200, 630
    img = Image.new('RGB', (width, height), color='#0B132B')
    draw = ImageDraw.Draw(img)

    font_title = ImageFont.load_default()
    draw.text((60, 60), f"ECOPULSE | {funnel_stage.upper()}", fill='#10B981', font=font_title)
    draw.text((60, 120), headline[:80], fill='#FFFFFF', font=font_title)
    draw.text((60, 200), fact_text[:180], fill='#CBD5E1', font=font_title)

    img.save(out_path, "PNG")
    log.info(f"Generated fallback PIL graphic card: {out_path}")
    return out_path


def run(copywriter_output: dict, out_path: str = 'state/latest_image.png', funnel_stage: str = 'ToFU') -> dict:
    """
    Run the image agent using Next-Gen Playwright HTML/CSS Headless Engine.
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
        log.info("Playwright headless render fallback triggered. Rendering PIL card...")
        generate_fallback_pil_card(headline, fact_text, out_path, funnel_stage)
        model_used = f"Fallback PIL Card Engine ({funnel_stage} layout)"

    return {
        "agent": "image",
        "output": {
            "image_path": out_path,
            "image_prompt": f"Playwright HTML5 Card: {headline} ({funnel_stage})",
            "model_used": model_used
        }
    }
