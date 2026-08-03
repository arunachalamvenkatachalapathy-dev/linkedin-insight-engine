"""
Step 3: 3D AI Infographic Slide Generator Agent
EXCLUSIVELY uses Google Imagen 3 / Gemini Image Models (gemini-2.5-flash-image, imagen-3.0-generate-002).
No third-party models or fallbacks are used per user instruction.
"""

import os
import base64
import logging
import requests

log = logging.getLogger("ecopulse")

IMAGEN_ENDPOINTS = [
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent",
    "https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict",
    "https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-fast-generate-001:predict"
]


def generate_google_imagen_slide(prompt_blueprint: str, out_path: str, api_key: str) -> bool:
    """
    Generate 16:9 3D Isometric Infographic slide EXCLUSIVELY using Google Imagen 3 / Gemini Image models.
    """
    log.info("Generating 3D AI Infographic slide EXCLUSIVELY via Google Imagen 3...")
    
    # 1. Try Gemini 2.5 Flash Image / Imagen endpoints
    for endpoint in IMAGEN_ENDPOINTS:
        url = f"{endpoint}?key={api_key}"
        headers = {"Content-Type": "application/json"}
        
        if "generateContent" in endpoint:
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": f"Generate a 16:9 3D isometric infographic slide for LinkedIn: {prompt_blueprint}"
                            }
                        ]
                    }
                ]
            }
        else:
            payload = {
                "instances": [{"prompt": prompt_blueprint}],
                "parameters": {"sampleCount": 1, "aspectRatio": "16:9"}
            }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=90)
            if resp.status_code == 200:
                res_json = resp.json()
                img_data = None
                
                # Check predict response
                predictions = res_json.get("predictions", [])
                if predictions and "bytesBase64Encoded" in predictions[0]:
                    img_data = base64.b64decode(predictions[0]["bytesBase64Encoded"])
                
                # Check generateContent response
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
            else:
                log.warning(f"Endpoint {endpoint.split('/')[-1]} status {resp.status_code}: {resp.text[:120]}")
        except Exception as exc:
            log.warning(f"Endpoint {endpoint.split('/')[-1]} error: {exc}")

    raise RuntimeError("Failed to generate slide using Google Imagen 3. Please check your GEMINI_API_KEY billing/quota.")


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

    success = generate_google_imagen_slide(prompt_blueprint, out_path, gemini_key)
    if not success:
        raise RuntimeError("Failed to generate slide via Google Imagen 3.")

    return out_path
