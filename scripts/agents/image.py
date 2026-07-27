"""
Image generation agent for EcoPulse.
Renders scroll-stopping visual assets using high-end AI engines:
1. Google Imagen 3 (Primary high-fidelity engine)
2. OpenAI DALL-E 3 HD (Secondary high-fidelity engine)
3. Stability AI SD3.5 Large (Tertiary engine)
4. Pollinations FLUX / SDXL (Fallback engines)
"""

import os
import json
import logging
import requests
import urllib.parse
import urllib.request
from llm import call_agent

try:
    from google import genai
except ImportError:
    genai = None

log = logging.getLogger("ecopulse")

SYSTEM_PROMPT = """You are an expert Visual Art Director specializing in scroll-stopping LinkedIn visuals for environmental engineering and climate tech.

YOUR JOB:
Create an evocative, dramatic, award-winning visual prompt based on the post text.

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
            
    style_suffix = ", photorealistic 8k, crisp architectural editorial photography, natural daylight, sharp focus, no text"
    if style_suffix not in prompt:
        prompt += style_suffix

    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    model_used = None
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    # Engine 1: Google Imagen 3 (Premium photorealistic rendering)
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key and genai and not model_used:
        try:
            log.info("Attempting image generation with Google Imagen 3...")
            client = genai.Client()
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
                model_used = "Google Imagen 3"
                log.info("Successfully generated image via Google Imagen 3")
        except Exception as e:
            log.warning(f"Google Imagen 3 failed: {e}")

    # Engine 2: OpenAI DALL-E 3 HD
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key and not model_used:
        try:
            log.info("Attempting image generation with OpenAI DALL-E 3...")
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
                model_used = "OpenAI DALL-E 3 HD"
                log.info("Successfully generated image via OpenAI DALL-E 3 HD")
        except Exception as e:
            log.warning(f"OpenAI DALL-E 3 failed: {e}")

    # Engine 3: Stability AI SD3.5 Large
    stability_key = os.environ.get("STABILITY_API_KEY")
    if stability_key and not model_used:
        try:
            log.info("Attempting image generation with Stability AI SD3.5...")
            response = requests.post(
                "https://api.stability.ai/v2beta/stable-image/generate/sd3",
                headers={
                    "Authorization": f"Bearer {stability_key}",
                    "Accept": "image/*"
                },
                files={"none": ""},
                data={
                    "prompt": prompt,
                    "output_format": "png",
                    "model": "sd3.5-large"
                },
                timeout=30
            )
            if response.status_code == 200:
                with open(out_path, 'wb') as f:
                    f.write(response.content)
                model_used = "Stability AI SD3.5"
                log.info("Successfully generated image via Stability AI SD3.5")
        except Exception as e:
            log.warning(f"Stability AI failed: {e}")

    # Engine 4: Pollinations FLUX Fallback
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

    # Engine 5: Pollinations SDXL Final Fallback
    if not model_used:
        try:
            log.info("Attempting image generation with Pollinations SDXL fallback...")
            sdxl_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?model=stable-diffusion-xl&width=1024&height=1024&nologo=true"
            resp = requests.get(sdxl_url, headers=headers, timeout=60)
            if resp.status_code == 200:
                with open(out_path, "wb") as f:
                    f.write(resp.content)
                model_used = "Pollinations SDXL"
                log.info("Successfully generated image via Pollinations SDXL")
        except Exception as e:
            log.warning(f"Pollinations SDXL failed: {e}")

    return {
        "agent": "image",
        "output": {
            "image_path": out_path if model_used else None,
            "image_prompt": prompt,
            "model_used": model_used
        }
    }
