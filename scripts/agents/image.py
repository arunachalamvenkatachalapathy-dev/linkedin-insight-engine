"""
Image generation and curation agent for EcoPulse.
Uses HuggingFace SDXL / Cloudflare Workers AI Text-to-Image API tier with failover to Unsplash High-Res Real Photography.
Creates photorealistic, high-impact visuals tailored to corporate ESG & Environmental Engineering posts.
"""

import os
import re
import json
import logging
import requests
import random
from datetime import datetime, timezone

log = logging.getLogger("ecopulse")

UNSPLASH_FALLBACK_COLLECTION = [
    "https://images.unsplash.com/photo-1497435334941-8c899ee9e8e9?q=80&w=1200&auto=format&fit=crop", # Renewable solar energy
    "https://images.unsplash.com/photo-1466611653911-95081537e5b7?q=80&w=1200&auto=format&fit=crop", # Wind turbine infrastructure
    "https://images.unsplash.com/photo-1513836279014-a89f7a76ae86?q=80&w=1200&auto=format&fit=crop", # Forest & nature conservation
    "https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?q=80&w=1200&auto=format&fit=crop", # Environmental eco technology
    "https://images.unsplash.com/photo-1532996122724-e3c354a0b15b?q=80&w=1200&auto=format&fit=crop", # Industrial recycling & waste management
    "https://images.unsplash.com/photo-1500382017468-9049fed747ef?q=80&w=1200&auto=format&fit=crop", # Water management & hydrology
    "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?q=80&w=1200&auto=format&fit=crop", # Engineering lab & testing
    "https://images.unsplash.com/photo-1509391365360-2e959784a276?q=80&w=1200&auto=format&fit=crop"  # Clean energy grid infrastructure
]


def _build_sdxl_prompt(headline: str, fact_text: str) -> tuple[str, str]:
    """Construct an institutional, photorealistic prompt for SDXL / Workers AI."""
    topic_keywords = re.findall(r"\b[A-Za-z]{4,}\b", headline)
    clean_topic = " ".join(topic_keywords[:5]) if topic_keywords else "industrial environmental engineering"
    
    prompt = (
        f"High-resolution, ultra-detailed architectural photography of {clean_topic}, "
        f"modern industrial environmental facility, clean equipment, daylight, photorealistic, 8k, "
        f"corporate ESG sustainability report visual style, professional engineering photograph."
    )
    negative_prompt = "blurry, cartoon, low quality, distorted, text, watermark, draft, ugly, overexposed, low resolution"
    return prompt, negative_prompt


def fetch_unsplash_photo(headline: str, out_path: str) -> bool:
    """Fetch high-resolution real photography from Unsplash matching topic."""
    try:
        # Extract 2 core search keywords
        words = [w for w in re.findall(r"\b[A-Za-z]{4,}\b", headline.lower()) if w not in {"engineering", "analysis", "field", "telemetry"}]
        query = "%20".join(words[:2]) if words else "environment"
        url = f"https://source.unsplash.com/1200x630/?{query}"
        
        resp = requests.get(url, timeout=12, allow_redirects=True)
        if resp.status_code == 200 and len(resp.content) > 10000:
            os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(resp.content)
            log.info(f"Successfully fetched real Unsplash photo for topic '{query}' to {out_path}")
            return True
    except Exception as exc:
        log.warning(f"Unsplash query fetch failed: {exc}")
    
    # Fallback to curated static high-res photo URL
    try:
        fallback_url = random.choice(UNSPLASH_FALLBACK_COLLECTION)
        resp = requests.get(fallback_url, timeout=12)
        if resp.status_code == 200:
            os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(resp.content)
            log.info(f"Successfully downloaded curated high-res Unsplash photo to {out_path}")
            return True
    except Exception as exc:
        log.warning(f"Unsplash curated fallback download failed: {exc}")
        
    return False


def generate_sdxl_image(prompt: str, negative_prompt: str, out_path: str) -> bool:
    """
    Generate an AI image using HuggingFace SDXL / Cloudflare Workers AI free inference tier.
    """
    hf_token = os.environ.get("HUGGINGFACE_TOKEN", "").strip()
    headers = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}
    
    models = [
        "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0",
        "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
    ]
    
    for model_url in models:
        try:
            log.info(f"Attempting SDXL image generation via HuggingFace model: {model_url.split('/')[-1]}...")
            resp = requests.post(
                model_url,
                headers=headers,
                json={"inputs": prompt, "parameters": {"negative_prompt": negative_prompt}},
                timeout=25
            )
            if resp.status_code == 200 and len(resp.content) > 10000:
                os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
                with open(out_path, "wb") as f:
                    f.write(resp.content)
                log.info(f"Successfully generated SDXL AI image: {out_path}")
                return True
            else:
                log.warning(f"SDXL generation status {resp.status_code}: {resp.text[:120]}")
        except Exception as exc:
            log.warning(f"SDXL generation exception: {exc}")
            
    return False


def run(copywriter_output: dict, out_path: str = 'state/latest_image.png', funnel_stage: str = 'ToFU') -> dict:
    """
    Run the image agent with Cloudflare Workers AI / HuggingFace SDXL engine and Unsplash real photography failover.
    """
    headline = (
        copywriter_output.get("headline") or
        copywriter_output.get("selected_idea", {}).get("headline") or
        "Senior Environmental Engineering Telemetry & Compliance"
    )

    supporting_facts = copywriter_output.get("supporting_facts") or copywriter_output.get("selected_idea", {}).get("supporting_facts", [])
    fact_text = supporting_facts[0] if supporting_facts else "Primary supplier telemetry reduces emission factor variance from +/-25% down to +/-3% under BRSR Core & CSRD."

    prompt, neg_prompt = _build_sdxl_prompt(headline, fact_text)
    
    # 1. Try HuggingFace SDXL / Cloudflare Workers AI Text-to-Image Tier
    success = generate_sdxl_image(prompt, neg_prompt, out_path)
    model_used = "HuggingFace SDXL Text-to-Image AI Engine"

    # 2. Fallback to Unsplash Real High-Res Photography
    if not success:
        log.info("SDXL API quota unavailable. Falling back to Unsplash Real High-Res Engineering Photography...")
        success = fetch_unsplash_photo(headline, out_path)
        model_used = "Unsplash Real High-Res Engineering Photography API"

    return {
        "agent": "image",
        "output": {
            "image_path": out_path,
            "image_prompt": prompt,
            "model_used": model_used
        }
    }
