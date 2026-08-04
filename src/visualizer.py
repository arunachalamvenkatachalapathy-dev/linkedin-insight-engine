"""
Step 3: 3D AI Infographic Slide Generator Agent
Primary Engine: Google Imagen 3 (imagen-3.0-generate-002)
Secondary Engine: Playwright Headless Chromium HTML5/CSS3 Engine with Inlined Styles
Guarantees full-bleed, high-res dark glassmorphic 1200x630 cards without file URL resolution failures.
"""

import os
import base64
import logging
import requests
from pathlib import Path
from datetime import datetime, timezone
from jinja2 import Template

log = logging.getLogger("ecopulse")

TEMPLATES_DIR = Path(__file__).parent / "templates"


def generate_google_imagen_3_slide(prompt_blueprint: str, out_path: str, api_key: str) -> bool:
    """Generate 16:9 3D Isometric Infographic slide using Google Imagen 3."""
    log.info("Generating 3D AI Infographic slide via Google Imagen 3...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "instances": [{"prompt": prompt_blueprint}],
        "parameters": {"sampleCount": 1, "aspectRatio": "16:9"}
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
        log.warning(f"Google Imagen 3 status {resp.status_code}: {resp.text[:120]}")
    except Exception as exc:
        log.warning(f"Google Imagen 3 exception: {exc}")

    return False


def generate_playwright_html_slide(scout_data: dict, out_path: str) -> bool:
    """Render crisp 1200x630 glassmorphic HTML5 slide using Playwright with inlined CSS."""
    try:
        from playwright.sync_api import sync_playwright

        log.info("Rendering high-res glassmorphic HTML5 slide via Playwright Headless Chromium...")
        template_path = TEMPLATES_DIR / "slide.html"
        styles_path = TEMPLATES_DIR / "styles.css"

        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        css_content = ""
        if os.path.exists(styles_path):
            with open(styles_path, "r", encoding="utf-8") as f:
                css_content = f.read()

        template = Template(template_content)
        date_str = datetime.now(timezone.utc).strftime("%B %Y")

        html_rendered = template.render(
            headline=scout_data.get("headline", ""),
            metric_left=scout_data.get("metric_left", ""),
            metric_right=scout_data.get("metric_right", ""),
            date_str=date_str
        )

        # Inline CSS directly to bypass local file URI security restrictions in Chromium
        html_final = html_rendered.replace("/* INLINE_STYLES */", css_content)

        os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--allow-file-access-from-files"]
            )
            context = browser.new_context(
                viewport={"width": 1200, "height": 630},
                device_scale_factor=2
            )
            page = context.new_page()
            page.set_content(html_final, wait_until="load")
            page.screenshot(path=out_path, type="png")
            browser.close()

        log.info(f"✅ Successfully rendered Playwright glassmorphic slide: {out_path} ({os.path.getsize(out_path)} bytes)")
        return True
    except Exception as exc:
        log.warning(f"Playwright rendering error: {exc}")

    return False


def render_3d_slide(prompt_blueprint: str, scout_data: dict, out_path: str = "state/latest_slide.png") -> str:
    """
    Renders 16:9 3D Isometric Infographic Slide.
    """
    gemini_key = (
        os.environ.get("GEMINI_API_KEY", "").strip() or
        os.environ.get("GOOGLE_API_KEY", "").strip()
    )

    # 1. Primary: Google Imagen 3
    if gemini_key:
        if generate_google_imagen_3_slide(prompt_blueprint, out_path, gemini_key):
            return out_path

    # 2. Secondary: Playwright High-Res HTML5 Glassmorphic Card (Inlined CSS)
    if generate_playwright_html_slide(scout_data, out_path):
        return out_path

    raise RuntimeError("Failed to generate slide.")
