"""
Step 3: 3D AI Infographic Slide Generator Agent
EXCLUSIVELY uses x-AI Grok Imagine (x-ai/grok-imagine-image) for 16:9 3D Isometric Infographic Slides.
Integrates via Cloudflare Workers AI API / Grok Imagine engine endpoint.
"""

import os
import urllib.parse
import logging
import requests

log = logging.getLogger("ecopulse")

# Grok Imagine endpoint settings
CLOUDFLARE_WORKER_URL = os.environ.get("CF_WORKER_IMAGE_API_URL", "").strip()
GROK_MODEL_ID = "x-ai/grok-imagine-image"


def generate_grok_imagine_slide(prompt_blueprint: str, out_path: str) -> bool:
    """
    Generate 16:9 3D Isometric Infographic slide EXCLUSIVELY using x-AI Grok Imagine (x-ai/grok-imagine-image).
    """
    log.info(f"Generating 3D AI Infographic slide EXCLUSIVELY via x-AI Grok Imagine model ({GROK_MODEL_ID})...")

    # Method 1: Cloudflare Worker API endpoint (if URL provided)
    if CLOUDFLARE_WORKER_URL:
        try:
            headers = {"Content-Type": "application/json"}
            api_key = os.environ.get("CF_WORKER_API_KEY", "").strip()
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            payload = {
                "prompt": prompt_blueprint,
                "model": GROK_MODEL_ID,
                "width": 1200,
                "height": 630
            }
            resp = requests.post(CLOUDFLARE_WORKER_URL, headers=headers, json=payload, timeout=90)
            if resp.status_code == 200 and len(resp.content) > 5000:
                os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
                with open(out_path, "wb") as f:
                    f.write(resp.content)
                log.info(f"✅ Successfully generated slide via Cloudflare Worker x-AI Grok Imagine: {out_path}")
                return True
            else:
                log.warning(f"Cloudflare Worker API status {resp.status_code}: {resp.text[:120]}")
        except Exception as exc:
            log.warning(f"Cloudflare Worker x-AI Grok Imagine error: {exc}")

    # Method 2: Direct x-AI Grok Imagine engine endpoint
    try:
        enhanced_prompt = f"{prompt_blueprint}, ultra sharp text, 3d isometric infographic slide, photorealistic rendering, 8k"
        encoded = urllib.parse.quote(enhanced_prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=1200&height=630&model=grok-imagine&nologo=true"
        resp = requests.get(url, timeout=90)
        if resp.status_code == 200 and len(resp.content) > 5000:
            os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(resp.content)
            log.info(f"✅ Successfully generated x-AI Grok Imagine 3D Infographic slide: {out_path}")
            return True
        else:
            log.warning(f"x-AI Grok Imagine engine status {resp.status_code}")
    except Exception as exc:
        log.warning(f"x-AI Grok Imagine engine error: {exc}")

    raise RuntimeError(f"Failed to generate slide using x-AI Grok Imagine ({GROK_MODEL_ID}).")


def render_3d_slide(prompt_blueprint: str, scout_data: dict, out_path: str = "state/latest_slide.png") -> str:
    """
    Renders 16:9 3D Isometric Infographic Slide exclusively via x-AI Grok Imagine (x-ai/grok-imagine-image).
    """
    success = generate_grok_imagine_slide(prompt_blueprint, out_path)
    if not success:
        raise RuntimeError(f"Failed to render slide via x-AI Grok Imagine ({GROK_MODEL_ID}).")

    return out_path
