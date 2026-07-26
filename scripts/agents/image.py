"""
Image generation agent for EcoPulse.
Generates an image prompt and renders it via image generation APIs.
"""

import os
import json
import base64
import requests
import urllib.request
import urllib.parse
import logging
from llm import call_agent

try:
    from google import genai
except ImportError:
    genai = None

SYSTEM_PROMPT = """You are the Image prompt agent for EcoPulse.

Generate a DSLR-quality photographic image prompt based on the provided post content.
Style: crisp DSLR architectural/editorial photography, natural sunlight, real-world environmental engineering.
Quality keywords to include: DSLR photography, architectural editorial, natural sunlight, sharp focus, real-world engineering, environmental aesthetic, high detail, 8k.
AVOID: 3D renders, cartoons, illustrations, stock photo cliches, text overlays, watermarks, hands holding plants.

Return ONLY valid JSON with this schema:
{
  "image_prompt": "..."
}
"""

def run(copywriter_output: dict, out_path: str = 'state/latest_image.png') -> dict:
    """
    Run the image agent.
    """
    # Step 1: Call LLM to generate image prompt JSON
    user_content = json.dumps(copywriter_output)
    result = call_agent(
        system_prompt=SYSTEM_PROMPT,
        user_content=user_content,
        use_web_search=False
    )
    
    prompt = result.get("image_prompt", "")
    if not prompt:
        # Fallback if the LLM output didn't strictly follow JSON, or parsing failed inside call_agent
        if "output" in result and "image_prompt" in result["output"]:
            prompt = result["output"]["image_prompt"]
        else:
            prompt = str(result)
            
    # Step 2: Append photographic style suffix
    style_suffix = ", crisp DSLR architectural/editorial photography, natural sunlight, real-world environmental engineering, sharp focus, high detail, 8k"
    if style_suffix not in prompt:
        prompt += style_suffix

    # Step 3: Try rendering in fallback order
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    
    model_used = None
    
    # 1. Stability AI
    stability_key = os.environ.get("STABILITY_API_KEY")
    if stability_key and not model_used:
        try:
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
                model_used = "Stability AI sd3.5-large"
        except Exception as e:
            logging.warning(f"Stability AI failed: {e}")

    # 2. Pollinations SDXL (free fallback)
    if not model_used:
        try:
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?model=stable-diffusion-xl&width=1024&height=1024&nologo=true"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            resp = requests.get(url, headers=headers, timeout=60)
            if resp.status_code == 200:
                with open(out_path, "wb") as f:
                    f.write(resp.content)
                model_used = "Pollinations SDXL"
            else:
                logging.warning(f"Pollinations returned HTTP {resp.status_code}")
        except Exception as e:
            logging.warning(f"Pollinations SDXL failed: {e}")

    # 3. OpenAI DALL-E 3
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key and not model_used:
        try:
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
                    "size": "1024x1024"
                },
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                img_url = data['data'][0]['url']
                urllib.request.urlretrieve(img_url, out_path)
                model_used = "OpenAI DALL-E 3"
        except Exception as e:
            logging.warning(f"OpenAI DALL-E 3 failed: {e}")

    # 4. Google Imagen
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key and genai and not model_used:
        try:
            client = genai.Client()
            result_img = client.models.generate_images(
                model='imagen-3.0-generate-001',
                prompt=prompt,
                config=dict(
                    number_of_images=1,
                    output_mime_type="image/png",
                )
            )
            if result_img and result_img.generated_images:
                img_bytes = result_img.generated_images[0].image.image_bytes
                with open(out_path, 'wb') as f:
                    f.write(img_bytes)
                model_used = "Google Imagen"
        except Exception as e:
            logging.warning(f"Google Imagen failed: {e}")
            
    if not model_used:
        logging.error("All image generation methods failed.")
        
    return {
        "agent": "image",
        "output": {
            "image_path": out_path if model_used else None,
            "image_prompt": prompt,
            "model_used": model_used
        }
    }
