import os
import json
import base64
import requests
import urllib.request
import urllib.parse
from llm import call_agent

SYSTEM_PROMPT = """You are the Visualizer subagent for EcoPulse. You receive the Copywriter's \
post_text and image_brief. Generate an image prompt for a professional, editorial-style \
visual — think infographic-adjacent or clean photography, NOT stock-photo cliché (no generic \
"hands holding a small plant in soil" imagery).

Prefer: clean data visualizations, engineering diagrams, real-world infrastructure \
photography style, or minimal editorial illustration matching LinkedIn's professional tone.

Return ONLY valid JSON:
{
  "agent": "visualizer",
  "output": {
    "image_prompt": "...",
    "aspect_ratio": "1:1",
    "style_notes": "...",
    "text_overlay": null
  }
}"""


def _generate_prompt(copywriter_output: dict) -> dict:
    user_content = f"Post + brief:\n{json.dumps(copywriter_output, indent=2)}"
    return call_agent(SYSTEM_PROMPT, user_content, use_web_search=False)


def _render_image_openai(prompt: str, out_path: str) -> str:
    """Render via OpenAI Images API (dall-e-3). Set OPENAI_API_KEY to use this."""
    resp = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        json={
            "model": "dall-e-3",
            "prompt": prompt,
            "size": "1024x1024",
            "response_format": "b64_json"
        },
        timeout=120,
    )
    resp.raise_for_status()
    b64 = resp.json()["data"][0]["b64_json"]
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(b64))
    return out_path


def _render_image_stability(prompt: str, out_path: str) -> str:
    """Render via Stability AI. Set STABILITY_API_KEY to use this instead."""
    resp = requests.post(
        "https://api.stability.ai/v2beta/stable-image/generate/core",
        headers={
            "Authorization": f"Bearer {os.environ['STABILITY_API_KEY']}",
            "Accept": "image/*",
        },
        files={"none": ""},
        data={"prompt": prompt, "output_format": "png"},
        timeout=120,
    )
    resp.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(resp.content)
    return out_path


def _render_image_pollinations(prompt: str, out_path: str) -> str:
    """Free fallback image generator using Pollinations AI."""
    encoded_query = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_query}?width=1024&height=1024&nologo=true&model=flux"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=45) as response:
        image_bytes = response.read()
    with open(out_path, "wb") as f:
        f.write(image_bytes)
    return out_path


def run(copywriter_output: dict, out_path: str = "state/latest_image.png") -> dict:
    result = _generate_prompt(copywriter_output)
    prompt = result["output"]["image_prompt"]

    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        raise ValueError("OPENAI_API_KEY environment variable is required for strict DALL-E 3 image generation.")

    image_path = _render_image_openai(prompt, out_path)
    result["output"]["image_path"] = image_path
    return result
