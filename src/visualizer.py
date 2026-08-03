"""
Step 3: 3D AI Infographic Slide Generator Agent
Primary: Google Imagen 3 / Gemini Image Models (imagen-3.0-generate-002, gemini-2.5-flash-image).
Secondary: x-AI Grok Imagine (x-ai/grok-imagine-image).
"""

import os
import time
import base64
import logging
import urllib.parse
import requests

log = logging.getLogger("ecopulse")

IMAGEN_ENDPOINTS = [
    "https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent"
]


def generate_google_imagen_3_slide(prompt_blueprint: str, out_path: str, api_key: str) -> bool:
    """
    Generate 16:9 3D Isometric Infographic slide using Google Imagen 3 with rate limit retries.
    """
    log.info("Generating 3D AI Infographic slide via Google Imagen 3...")
    
    for endpoint in IMAGEN_ENDPOINTS:
        url = f"{endpoint}?key={api_key}"
        headers = {"Content-Type": "application/json"}
        
        if "predict" in endpoint:
            payload = {
                "instances": [{"prompt": prompt_blueprint}],
                "parameters": {"sampleCount": 1, "aspectRatio": "16:9"}
            }
        else:
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": f"Generate a 16:9 3D isometric visual infographic slide for LinkedIn: {prompt_blueprint}"
                            }
                        ]
                    }
                ]
            }

        for attempt in range(2):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=90)
                if resp.status_code == 200:
                    res_json = resp.json()
                    img_data = None
                    
                    predictions = res_json.get("predictions", [])
                    if predictions and "bytesBase64Encoded" in predictions[0]:
                        img_data = base64.b64decode(predictions[0]["bytesBase64Encoded"])
                    
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
                        log.info(f"✅ Successfully generated Google Imagen 3 3D Infographic slide ({endpoint.split('/')[-1]}): {out_path}")
                        return True
                elif resp.status_code == 429:
                    log.warning(f"Endpoint {endpoint.split('/')[-1]} rate limited (429). Waiting 6s before retry...")
                    time.sleep(6)
                else:
                    log.warning(f"Endpoint {endpoint.split('/')[-1]} status {resp.status_code}: {resp.text[:120]}")
                    break
            except Exception as exc:
                log.warning(f"Endpoint {endpoint.split('/')[-1]} exception: {exc}")
                break

    return False


def generate_grok_imagine_slide(prompt_blueprint: str, out_path: str) -> bool:
    """Generate 16:9 3D slide using x-AI Grok Imagine as fallback."""
    try:
        log.info("Google Imagen 3 quota exceeded. Generating via x-AI Grok Imagine (x-ai/grok-imagine-image)...")
        enhanced_prompt = f"{prompt_blueprint}, ultra sharp text, 3d isometric infographic slide, photorealistic rendering, 8k"
        encoded = urllib.parse.quote(enhanced_prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=1200&height=630&model=grok-imagine&nologo=true"
        resp = requests.get(url, timeout=90)
        if resp.status_code == 200 and len(resp.content) > 5000:
            os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(resp.content)
            log.info(f"✅ Successfully generated x-AI Grok Imagine slide: {out_path}")
            return True
    except Exception as exc:
        log.warning(f"x-AI Grok Imagine error: {exc}")
    return False


def render_3d_slide(prompt_blueprint: str, scout_data: dict, out_path: str = "state/latest_slide.png") -> str:
    """
    Renders 16:9 3D Isometric Infographic Slide.
    """
    gemini_key = (
        os.environ.get("GEMINI_API_KEY", "").strip() or
        os.environ.get("GOOGLE_API_KEY", "").strip()
    )

    if gemini_key:
        if generate_google_imagen_3_slide(prompt_blueprint, out_path, gemini_key):
            return out_path

    if generate_grok_imagine_slide(prompt_blueprint, out_path):
        return out_path

    raise RuntimeError("Failed to generate 3D slide.")
