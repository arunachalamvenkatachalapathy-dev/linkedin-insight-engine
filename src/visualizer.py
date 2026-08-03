"""
Step 3: 3D AI Infographic Slide Generator Agent
EXCLUSIVELY uses Google Imagen 3 (imagen-3.0-generate-002) for 16:9 3D Isometric Infographic Slides.
No other models or fallbacks are used per user instruction.
"""

import os
import base64
import logging
import requests

log = logging.getLogger("ecopulse")


def generate_imagen_3_slide(prompt_blueprint: str, out_path: str, api_key: str) -> bool:
    """
    Generate 16:9 3D Isometric Infographic slide using Google Imagen 3 exclusively.
    """
    log.info("Generating 3D AI Infographic slide EXCLUSIVELY via Google Imagen 3 (imagen-3.0-generate-002)...")
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
        else:
            raise RuntimeError(f"Google Imagen 3 returned empty predictions: {resp.text[:200]}")
    else:
        raise RuntimeError(f"Google Imagen 3 API Error (Status {resp.status_code}): {resp.text}")


def render_3d_slide(prompt_blueprint: str, scout_data: dict, out_path: str = "state/latest_slide.png") -> str:
    """
    Renders 16:9 3D Isometric Infographic Slide exclusively via Google Imagen 3.
    """
    gemini_key = (
        os.environ.get("GEMINI_API_KEY", "").strip() or
        os.environ.get("GOOGLE_API_KEY", "").strip()
    )

    if not gemini_key:
        raise ValueError("GEMINI_API_KEY / GOOGLE_API_KEY environment variable is required to generate Google Imagen 3 slides.")

    success = generate_imagen_3_slide(prompt_blueprint, out_path, gemini_key)
    if not success:
        raise RuntimeError("Failed to generate slide via Google Imagen 3.")

    return out_path
