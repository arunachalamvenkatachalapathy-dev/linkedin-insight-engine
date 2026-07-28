"""
Image generation agent for EcoPulse.
Renders scroll-stopping visual assets using high-end AI engines:
1. OpenAI DALL-E 3 (ChatGPT Image Generator - via OPENAI_API_KEY)
2. Google Imagen 3 (Gemini Image Generator - via GEMINI_API_KEY)
3. Pollinations FLUX (Free High-Fidelity Photorealistic Engine)
"""

import os
import json
import base64
import logging
import requests
import urllib.parse
import urllib.request
from llm import call_agent

log = logging.getLogger("ecopulse")

SYSTEM_PROMPT = """You are an expert Visual Art Director specializing in scroll-stopping LinkedIn visuals for environmental engineering and climate tech.

YOUR JOB:
Create an evocative, dramatic visual prompt based on the post text.

PROMPT DESIGN RULES:
1. VISUAL STYLE: Crisp 35mm architectural photograph, cinematic wide-angle aerial view, high-contrast natural daylight, editorial National Geographic quality photo.
2. COMPOSITION: Dramatic perspective, clean environmental engineering infrastructure, realistic water/sky/landscape rendering.
3. SUBJECT MATTER: Real-world infrastructure, satellite monitoring arrays, constructed wetlands, clean energy grids, high-tech environmental monitoring equipment.
4. QUALITY KEYWORDS: Photorealistic, 8k resolution, crisp focus, natural lighting, architectural editorial photo.
5. NO CLICHÉS: NO hands holding plants, NO cartoon globes, NO fake 3D graphics, NO text overlays, NO watermarks.

Return ONLY valid JSON:
{
  "image_prompt": "Cinematic wide-angle architectural photo of..."
}
"""

def run(copywriter_output: dict, out_path: str = 'state/latest_image.png') -> dict:
    """Run the image agent with multi-engine priority."""
    user_content = json.dumps(copywriter_output)
    try:
        result = call_agent(
            system_prompt=SYSTEM_PROMPT,
            user_content=user_content,
            use_web_search=False
        )
        prompt = result.get("image_prompt", "")
        if not prompt:
            if "output" in result and "image_prompt" in result["output"]:
                prompt = result["output"]["image_prompt"]
            else:
                prompt = str(result)
    except Exception as err:
        log.warning(f"Image prompt LLM call failed ({err}). Using direct copywriter fallback prompt.")
        headline = copywriter_output.get("headline", "Environmental Engineering Infrastructure")
        prompt = f"Cinematic wide-angle architectural photograph of high-tech environmental engineering infrastructure for {headline}"
            
    style_suffix = ", photorealistic 8k, crisp architectural editorial photography, natural daylight, sharp focus, no text overlays"
    if style_suffix not in prompt:
        prompt += style_suffix

    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    model_used = None
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    # Engine 1: OpenAI DALL-E 3 (ChatGPT Image Generator)
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if openai_key and not model_used:
        try:
            log.info("Attempting image generation with OpenAI DALL-E 3 (ChatGPT)...")
            response = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "dall-e-3",
                    "prompt": prompt,
                    "n": 1,
                    "size": "1024x1024",
                    "quality": "hd"
                },
                timeout=45
            )
            if response.status_code == 200:
                data = response.json()
                img_url = data['data'][0]['url']
                urllib.request.urlretrieve(img_url, out_path)
                model_used = "OpenAI DALL-E 3 (ChatGPT)"
                log.info("Successfully generated image via OpenAI DALL-E 3 (ChatGPT)")
        except Exception as e:
            log.warning(f"OpenAI DALL-E 3 failed: {e}")

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

    # Engine 3: Pollinations FLUX (Free High-Fidelity Engine)
    if not model_used:
        try:
            log.info("Attempting image generation with Pollinations FLUX...")
            flux_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?model=flux&width=1200&height=630&nologo=true&enhance=true"
            resp = requests.get(flux_url, headers=headers, timeout=60)
            if resp.status_code == 200 and len(resp.content) > 10000:
                with open(out_path, "wb") as f:
                    f.write(resp.content)
                model_used = "Pollinations FLUX"
                log.info("Successfully generated image via Pollinations FLUX")
        except Exception as e:
            log.warning(f"Pollinations FLUX failed: {e}")

    return {
        "agent": "image",
        "output": {
            "image_path": out_path if model_used else None,
            "image_prompt": prompt,
            "model_used": model_used
        }
    }
