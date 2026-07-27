"""
Shared LLM helper for all EcoPulse agents.
Supports both Anthropic Claude (via SDK) and Google Gemini (via REST API).
Requires ANTHROPIC_API_KEY or GEMINI_API_KEY in the environment.
"""
import os
import json
import re
import time
import logging
import requests

log = logging.getLogger("ecopulse")

# Load env variables from local .env if running locally
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k.strip()] = v.strip()

MODEL = os.environ.get("ECOPULSE_MODEL")


def _extract_json(text: str) -> dict:
    """Strip markdown code fences / stray prose and parse the first JSON object."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\n?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n?```$", "", text)
    text = text.strip()
    
    # Extract only the balanced/outermost JSON block to ignore stray prose
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        text = match.group(1)
        
    return json.loads(text)


def call_agent(system_prompt: str, user_content: str, use_web_search: bool = False,
                max_tokens: int = 4000, max_retries: int = 2) -> dict:
    """
    Call Claude (via SDK) or Gemini (via REST) depending on available API keys.
    Returns parsed JSON dict.
    """
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    if anthropic_key:
        from anthropic import Anthropic
        model_name = MODEL or "claude-3-5-sonnet-20241022"
        client = Anthropic(api_key=anthropic_key)
        tools = [{"type": "web_search_20250305", "name": "web_search"}] if use_web_search else None
        messages = [{"role": "user", "content": user_content}]

        for attempt in range(max_retries + 1):
            kwargs = dict(
                model=model_name,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
                frequency_penalty=0.75,
                presence_penalty=0.4,
            )
            if tools:
                kwargs["tools"] = tools
            try:
                response = client.messages.create(**kwargs)
                text_parts = [block.text for block in response.content if block.type == "text"]
                full_text = "\n".join(text_parts)
                return _extract_json(full_text)
            except Exception as e:
                if "frequency_penalty" in kwargs:
                    del kwargs["frequency_penalty"]
                    del kwargs["presence_penalty"]
                    try:
                        response = client.messages.create(**kwargs)
                        text_parts = [block.text for block in response.content if block.type == "text"]
                        full_text = "\n".join(text_parts)
                        return _extract_json(full_text)
                    except Exception as retry_err:
                        e = retry_err
                if attempt < max_retries:
                    messages.append({"role": "assistant", "content": full_text if 'full_text' in locals() else str(e)})
                    messages.append({
                        "role": "user",
                        "content": f"That was not valid JSON ({e}). Return ONLY the corrected "
                                    f"JSON object, nothing else — no prose, no code fences."
                    })
                    continue
                raise RuntimeError(f"Claude API failed after retries: {e}")

    elif gemini_key:
        models_to_try = [
            MODEL or "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash"
        ]
        
        last_error = None
        for model_name in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
            
            for attempt in range(3):
                payload = {
                    "contents": [{"role": "user", "parts": [{"text": user_content}]}],
                    "systemInstruction": {"parts": [{"text": system_prompt}]},
                    "generationConfig": {
                        "maxOutputTokens": max_tokens,
                        "temperature": 0.7 + (attempt * 0.1),
                    }
                }
                
                if use_web_search and attempt == 0:
                    payload["tools"] = [{"googleSearch": {}}]
                else:
                    payload["generationConfig"]["responseMimeType"] = "application/json"

                try:
                    resp = requests.post(url, json=payload, timeout=60)
                    if resp.status_code == 429:
                        wait_time = (attempt + 1) * 20
                        log.warning(f"Gemini API rate limit (429) on {model_name}. Sleeping {wait_time}s...")
                        time.sleep(wait_time)
                        resp = requests.post(url, json=payload, timeout=60)
                        
                    resp.raise_for_status()
                    res_data = resp.json()
                    
                    candidate = res_data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        text = candidate["content"]["parts"][0]["text"]
                        return _extract_json(text)
                    else:
                        reason = candidate.get("finishReason", "UNKNOWN")
                        raise KeyError(f"No content found (Finish Reason: {reason})")
                        
                except Exception as e:
                    last_error = e
                    if "429" in str(e) or "Too Many Requests" in str(e):
                        log.warning(f"429 rate limit on {model_name} (attempt {attempt+1}). Sleeping 20s...")
                        time.sleep(20)
                    else:
                        log.warning(f"Gemini API attempt {attempt+1} on {model_name} failed: {e}")
                        time.sleep(3)
                        
        raise RuntimeError(f"Gemini API failed across all models and retries: {last_error}")

    else:
        raise ValueError("Neither ANTHROPIC_API_KEY nor GEMINI_API_KEY found in the environment.")
