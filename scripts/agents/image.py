"""
Image generation agent for EcoPulse.
Exclusively uses official OpenAI DALL-E (ChatGPT) and Google Imagen (Gemini) image models.
Pollinations FLUX is completely disabled per user preference.
"""

import os
import json
import logging
import requests
import urllib.parse
import urllib.request

log = logging.getLogger("ecopulse")

# Ensure .env variables are loaded
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k.strip()] = v.strip()


def run(copywriter_output: dict, out_path: str = 'state/latest_image.png') -> dict:
    """
    Run the image agent using ONLY OpenAI DALL-E (ChatGPT) or Google Imagen (Gemini).
    """
    headline = copywriter_output.get("headline") or copywriter_output.get("topic_summary") or "Environmental Engineering Infrastructure"
    
    prompt = f"Cinematic wide-angle architectural photograph of high-tech environmental engineering infrastructure for {headline}, photorealistic 8k, crisp architectural editorial photography, natural daylight, sharp focus, no text overlays"

    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    model_used = None

    # Engine 1: OpenAI DALL-E 3 / DALL-E 2 (ChatGPT Image Generator)
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if openai_key and not model_used:
        for oai_model in ["dall-e-3", "dall-e-2"]:
            try:
                log.info(f"Attempting image generation with OpenAI {oai_model} (ChatGPT)...")
                payload = {
                    "model": oai_model,
                    "prompt": prompt[:900],
                    "n": 1,
                    "size": "1024x1024"
                }
                if oai_model == "dall-e-3":
                    payload["quality"] = "hd"

                response = requests.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {openai_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=45
                )
                if response.status_code == 200:
                    data = response.json()
                    img_url = data['data'][0]['url']
                    urllib.request.urlretrieve(img_url, out_path)
                    model_used = f"OpenAI {oai_model} (ChatGPT)"
                    log.info(f"Successfully generated image via OpenAI {oai_model} (ChatGPT)")
                    break
                else:
                    log.warning(f"OpenAI {oai_model} status {response.status_code}: {response.text[:150]}")
            except Exception as e:
                log.warning(f"OpenAI {oai_model} failed: {e}")

    # Engine 2: Google Imagen 3 (Gemini Image API via google-genai SDK)
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if gemini_key and not model_used:
        try:
            from google import genai
            log.info("Attempting image generation with Google Imagen 3 (Gemini)...")
            client = genai.Client(api_key=gemini_key)
            result_img = client.models.generate_images(
                model='imagen-3.0-generate-002',
                prompt=prompt,
                config=dict(
                    number_of_images=1,
                    output_mime_type="image/png",
                    aspect_ratio="16:9"
                )
            )
            if result_img and result_img.generated_images:
                img_bytes = result_img.generated_images[0].image.image_bytes
                with open(out_path, 'wb') as f:
                    f.write(img_bytes)
                model_used = "Google Imagen 3 (Gemini)"
                log.info("Successfully generated image via Google Imagen 3 (Gemini)")
        except Exception as e:
            log.warning(f"Google Imagen 3 failed: {e}")

    if not model_used:
        log.error("Image generation failed: Neither OpenAI DALL-E nor Google Imagen 3 produced an image.")

    return {
        "agent": "image",
        "output": {
            "image_path": out_path if model_used else None,
            "image_prompt": prompt,
            "model_used": model_used
        }
    }
